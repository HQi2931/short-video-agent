"""Three deterministic tools, a registry, and an exception-safe executor."""
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Callable

from .schemas import (
    ACTION_ARGUMENTS, Asset, BrandRules, Script, SearchArgs, Timing,
)
from .state import AgentState


def load_data(directory: Path) -> tuple[list[Asset], BrandRules]:
    raw = json.loads((directory / "assets.json").read_text(encoding="utf-8-sig"))
    assets = [Asset.model_validate(a) for a in raw]
    if len({a.asset_id for a in assets}) != len(assets):
        raise ValueError("Duplicate asset IDs")
    rules = BrandRules.model_validate_json((directory / "brand_rules.json").read_text(encoding="utf-8-sig"))
    return assets, rules


def search_assets(assets: list[Asset], args: SearchArgs) -> dict:
    """Explainable keyword matching; no semantic or vector retrieval is implied."""
    query = args.query.casefold()
    extra = {k.casefold() for k in args.keywords}
    results = []
    for asset in assets:
        if args.asset_ids is not None and asset.asset_id not in args.asset_ids:
            continue
        matches = [k for k in asset.keywords if k.casefold() in query or k.casefold() in extra]
        if matches:
            results.append({**asset.model_dump(), "matched_keywords": matches, "score": len(matches)})
    results.sort(key=lambda a: (-a["score"], a["asset_id"]))
    return {
        "ok": True, "retrieval_status": "found" if results else "no_results",
        "query": args.query, "assets": results, "error": None,
        "method": "case-insensitive catalog keyword containment; score=matched keyword count",
    }


def speech_seconds(text: str, timing: Timing) -> float:
    chinese = len(re.findall(r"[\u3400-\u9fff]", text))
    english = len(re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", text))
    numbers = len(re.findall(r"\d+(?:\.\d+)?", text))
    other_letters = sum(
        unicodedata.category(c).startswith("L")
        and not ("\u3400" <= c <= "\u9fff") and not (c.isascii() and c.isalpha())
        for c in text
    )
    pauses = len(re.findall(r"[，。！？；,.!?;：:]", text))
    return (
        (chinese + other_letters) / timing.chinese_chars_per_second
        + english / timing.english_words_per_second
        + numbers / timing.number_groups_per_second
        + pauses * timing.punctuation_pause_seconds
    )


def ceil_centisecond(value: float) -> float:
    return math.ceil(value * 100 - 1e-9) / 100


def estimate_duration(script: Script, target_duration_seconds: float, script_version: str, timing: Timing) -> dict:
    if not math.isfinite(target_duration_seconds) or target_duration_seconds <= 0:
        raise ValueError("Target duration must be positive and finite")
    scenes = []
    for scene in script.storyboard:
        voice = speech_seconds(scene.narration, timing)
        captions = speech_seconds(scene.subtitle, timing)
        seconds = ceil_centisecond(max(voice, captions, timing.minimum_scene_seconds) + timing.transition_seconds)
        scenes.append({
            "scene_id": scene.scene_id, "narration_seconds": ceil_centisecond(voice),
            "subtitle_reading_seconds": ceil_centisecond(captions), "estimated_seconds": seconds,
        })
    total = round(sum(s["estimated_seconds"] for s in scenes), 2)
    return {
        "ok": True, "script_version": script_version, "scenes": scenes,
        "total_estimated_seconds": total, "target_duration_seconds": target_duration_seconds,
        "is_overtime": total > target_duration_seconds, "passed": total <= target_duration_seconds,
        "exceeded_seconds": round(max(0, total - target_duration_seconds), 2),
        "formula": "sum(ceil_0.01(max(narration, subtitle reading, minimum shot) + transition))",
        "timing": timing.model_dump(),
        "limitation": "Engineering estimate only; actual speech, pacing and simultaneous captions differ.",
    }


def uncovered_text(text: str, allowed: list[str]) -> str:
    remaining = text
    for phrase in sorted(set(allowed), key=len, reverse=True):
        remaining = remaining.replace(phrase, "")
    return "".join(c for c in remaining if not c.isspace() and not unicodedata.category(c).startswith("P"))


def check_brand_rules(script: Script, assets: list[Asset], rules: BrandRules, script_version: str,
                      topic: str | None = None) -> dict:
    """Conservative extractive grounding. Unrecognized prose blocks completion."""
    lookup = {a.asset_id: a for a in assets}
    violations: list[dict] = []
    unsupported = []
    missing_refs = []
    title_evidence = []
    total_valid_refs = 0

    def issue(code: str, location: str, detail: str):
        violations.append({"code": code, "location": location, "detail": detail})

    def inspect_text(text: str, location: str, evidence: list[str]):
        for phrase in rules.banned_phrases:
            if phrase.casefold() in text.casefold():
                issue("banned_phrase", location, phrase)
        remaining = uncovered_text(text, rules.approved_nonfactual_copy + evidence)
        if remaining:
            unsupported.append({"location": location, "text": remaining})
            missing_refs.append(location)
            issue("unverified_text", location, "Uncovered text requires evidence or human confirmation: " + remaining)
            if re.search(r"\d|[%％]|[一二三四五六七八九十百千万两]+(?:倍|成)", remaining):
                issue("unsupported_quantitative_claim", location, remaining)

    for scene in script.storyboard:
        evidence = []
        ref_asset_ids = {r.asset_id for r in scene.fact_refs}
        for asset_id in scene.source_ids:
            if asset_id not in lookup:
                issue("unknown_asset", scene.scene_id, asset_id)
            elif topic is not None and not any(k.casefold() in topic.casefold() for k in lookup[asset_id].keywords):
                issue("topic_alignment_unconfirmed", scene.scene_id,
                      f"Source {asset_id} has no catalog keyword in the original topic; request clarification")
            if asset_id not in ref_asset_ids:
                issue("missing_fact_reference", scene.scene_id, asset_id)
        for ref in scene.fact_refs:
            asset = lookup.get(ref.asset_id)
            if ref.asset_id not in scene.source_ids:
                issue("missing_source_id", scene.scene_id, ref.asset_id)
                missing_refs.append(scene.scene_id)
            if asset is None:
                issue("unknown_asset", scene.scene_id, ref.asset_id)
                continue
            fact = next((f for f in asset.facts if f.fact_id == ref.fact_id), None)
            if fact is None:
                issue("unknown_fact", scene.scene_id, ref.fact_id)
                continue
            if ref.evidence_text != fact.text or ref.evidence_text not in asset.source_text:
                issue("evidence_mismatch", scene.scene_id, ref.evidence_text)
                continue
            if ref.claim_text != fact.text:
                issue("unsupported_claim", scene.scene_id, ref.claim_text)
                unsupported.append({"location": scene.scene_id, "text": ref.claim_text})
                continue
            if not any(ref.claim_text in text for text in (scene.visual, scene.narration, scene.subtitle, script.title)):
                issue("unused_reference", scene.scene_id, ref.claim_text)
                continue
            evidence.append(fact.text)
            title_evidence.append(fact.text)
            total_valid_refs += 1
        for field in ("visual", "narration", "subtitle"):
            inspect_text(getattr(scene, field), f"{scene.scene_id}.{field}", evidence)
    inspect_text(script.title, "title", title_evidence)
    if not total_valid_refs:
        issue("no_grounded_fact", "script", "At least one supported product fact is required")
    if script.risk_flags:
        issue("unresolved_risk", "script", "; ".join(script.risk_flags))
    return {
        "ok": True, "script_version": script_version, "passed": not violations,
        "violations": violations, "unsupported_claims": unsupported,
        "missing_references": sorted(set(missing_refs)),
        "risk_reasons": [v["detail"] for v in violations],
        "needs_confirmation": bool(violations),
        "policy": "Exact evidence and brand-approved nonfactual copy only; unknown paraphrases block completion.",
        "limitation": "String verification does not establish full natural-language semantic entailment.",
    }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Callable] = {}

    def register(self, name: str, function: Callable):
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = function

    def get(self, name: str) -> Callable:
        return self._tools[name]

    @property
    def names(self) -> list[str]:
        return list(self._tools)


def default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("search_assets", search_assets)
    registry.register("estimate_duration", estimate_duration)
    registry.register("check_brand_rules", check_brand_rules)
    return registry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry | None = None, fail_once: set[str] | None = None):
        self.registry = registry or default_registry()
        self.fail_once = set(fail_once or ())
        unknown = self.fail_once - set(self.registry.names)
        if unknown:
            raise ValueError("Unknown fault-injection tools: " + ", ".join(sorted(unknown)))

    def execute(self, name: str, arguments: dict, state: AgentState) -> dict:
        # A failed recheck cannot leave a previous pass usable by finish.
        if name == "estimate_duration":
            state.current_duration = None
        if name == "check_brand_rules":
            state.current_rules = None
        try:
            args = ACTION_ARGUMENTS[name].model_validate(arguments)
            if name in self.fail_once:
                self.fail_once.remove(name)
                raise RuntimeError("Injected one-time tool failure")
            function = self.registry.get(name)
            if name == "search_assets":
                result = function(state.assets, args)
                if result.get("ok"):
                    found_ids = {a["asset_id"] for a in result["assets"]}
                    for asset in state.assets:
                        if asset.asset_id in found_ids:
                            state.retrieved_assets[asset.asset_id] = asset.model_copy(deep=True)
            else:
                if state.script is None:
                    raise ValueError("Draft a script before checking it")
                version = state.script_version
                if name == "estimate_duration":
                    if state.user_input.duration_seconds is None:
                        raise ValueError("Target duration is missing")
                    result = function(state.script, state.user_input.duration_seconds, version, state.rules.timing)
                    state.duration_checks.append(result)
                    state.current_duration = result if result.get("ok") else None
                elif name == "check_brand_rules":
                    authoritative = {a.asset_id: a for a in state.assets}
                    for asset_id, retrieved in state.retrieved_assets.items():
                        current = authoritative.get(asset_id)
                        if current is None or current.model_dump() != retrieved.model_dump():
                            raise ValueError("Retrieved evidence is stale; search again before checking")
                    result = function(state.script, list(state.retrieved_assets.values()), state.rules, version,
                                      state.user_input.topic)
                    state.rule_checks.append(result)
                    state.current_rules = result if result.get("ok") else None
                else:
                    raise ValueError("Unknown business tool")
            if not result.get("ok"):
                raise RuntimeError("Tool returned unavailable or error status")
            return result
        except Exception as exc:
            state.invalidate()
            return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}, "tool": name}

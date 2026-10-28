"""Mutable run state; validation is bound to script, request and trusted data."""
import hashlib
import json
from dataclasses import dataclass, field

from .schemas import Asset, BrandRules, Script, UserInput


def fingerprint(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass
class AgentState:
    user_input: UserInput
    assets: list[Asset]
    rules: BrandRules
    retrieved_assets: dict[str, Asset] = field(default_factory=dict)
    script: Script | None = None
    script_revision: int = 0
    duration_checks: list[dict] = field(default_factory=list)
    rule_checks: list[dict] = field(default_factory=list)
    current_duration: dict | None = None
    current_rules: dict | None = None
    errors: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    status: str = "pending"
    reason: str = ""
    missing_information: list[str] = field(default_factory=list)
    question: str | None = None
    last_observation: dict | None = None

    @property
    def script_version(self) -> str | None:
        if self.script is None:
            return None
        return fingerprint({
            "script": self.script.model_dump(), "input": self.user_input.model_dump(),
            "assets": [a.model_dump() for a in self.assets],
            "retrieved_assets": {k: a.model_dump() for k, a in self.retrieved_assets.items()},
            "rules": self.rules.model_dump(),
        })

    def invalidate(self):
        self.current_duration = None
        self.current_rules = None

    def update_script(self, script: Script):
        self.script = script.model_copy(deep=True)
        self.script_revision += 1
        self.invalidate()

    def replace_input(self, user_input: UserInput):
        self.user_input = user_input.model_copy(deep=True)
        self.invalidate()

    def replace_assets(self, assets: list[Asset]):
        self.assets = [a.model_copy(deep=True) for a in assets]
        self.retrieved_assets.clear()
        self.invalidate()

    def finish_errors(self) -> list[str]:
        errors = []
        if self.user_input.missing_fields():
            errors.append("Missing required user input: " + ", ".join(self.user_input.missing_fields()))
        if not self.script or not self.retrieved_assets:
            errors.append("A script and retrieved evidence are required")
        for name, check in (("duration", self.current_duration), ("brand_rules", self.current_rules)):
            if not check or check.get("script_version") != self.script_version or not check.get("passed"):
                errors.append(f"Current version has no passing {name} check")
        return errors

    def context(self) -> dict:
        return {
            "user_input": self.user_input.model_dump(),
            "missing_fields": self.user_input.missing_fields(),
            "retrieved_assets": [a.model_dump() for a in self.retrieved_assets.values()],
            "brand_rules": self.rules.model_dump(),
            "script": self.script.model_dump() if self.script else None,
            "script_version": self.script_version, "script_revision": self.script_revision,
            "duration_checks": self.duration_checks, "rule_checks": self.rule_checks,
            "errors": self.errors, "executed_actions": self.actions,
            "last_observation": self.last_observation,
            "finish_blockers": self.finish_errors(),
        }

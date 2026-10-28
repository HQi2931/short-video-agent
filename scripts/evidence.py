"""Inspect observable behavior; completion alone does not prove a correction path."""
import json


def inspect_live_calls(trace: dict) -> dict:
    """Verify exported actions and feedback against recorded HTTP requests/responses."""
    issues = []
    steps = trace.get("steps", [])
    response_models = set()
    if trace.get("execution_kind") != "real_api":
        issues.append({"step": None, "problem": "Trace execution_kind is not real_api"})
    for index, step in enumerate(steps):
        expected_next = steps[index + 1]["action"] if index + 1 < len(steps) else None
        if step.get("step") != index + 1:
            issues.append({"step": step.get("step"), "problem": "Non-consecutive step number"})
        if "next_action" not in step or step["next_action"] != expected_next:
            issues.append({"step": step.get("step"), "problem": "next_action differs from actual following action"})
        record = step.get("model_call", {})
        response = record.get("response", {})
        if response.get("model"):
            response_models.add(response["model"])
        if trace.get("mode") != "live" or record.get("mode") != "live" or record.get("http_status") != 200:
            issues.append({"step": step.get("step"), "problem": "Missing successful live HTTP record"})
            continue
        try:
            request = record["request"]
            raw_action = json.loads(response["content"])
            expected_action = {key: step[key] for key in ("action", "arguments", "reason_summary")}
            if raw_action != expected_action:
                issues.append({"step": step["step"], "problem": "Action differs from model response"})
            context = json.loads(request["messages"][-1]["content"])["state"]
            previous = steps[index - 1]["observation"] if index else None
            if context["last_observation"] != previous:
                issues.append({"step": step["step"], "problem": "Previous observation was not fed back"})
            # The input trace is raw; Pydantic fills None defaults and strips text.
            def normalized_input(value):
                return {k: v.strip() if isinstance(v, str) else v for k, v in value.items() if v is not None}
            if normalized_input(context["user_input"]) != normalized_input(trace["input"]) or request["model"] != trace["model"]:
                issues.append({"step": step["step"], "problem": "Request target/input differs from trace"})
        except (KeyError, TypeError, ValueError, IndexError):
            issues.append({"step": step.get("step"), "problem": "Unverifiable request or model response"})
    return {
        "verified": bool(steps) and not issues, "recorded_decisions": len(steps),
        "observation_feedback_checks": max(0, len(steps) - 1),
        "response_models": sorted(response_models), "issues": issues,
        "limitation": "Audit of local execution records; not independent provider attestation.",
    }


def inspect_behavior(case: str, trace: dict) -> dict:
    steps = trace.get("steps", [])
    result = trace.get("final_result", {})
    status = result.get("status")
    searches = [s for s in steps if s["action"] == "search_assets"]
    estimates = [s for s in steps if s["action"] == "estimate_duration" and s["observation"].get("ok")]
    checks = [s for s in steps if s["action"] == "check_brand_rules" and s["observation"].get("ok")]
    completed = status == "completed" and all(
        result.get(name, {}) and result[name].get("passed")
        and result[name].get("script_version") == result.get("script_version")
        for name in ("duration_check", "brand_rule_check")
    )

    def changed_draft_between(start: int, end: int) -> bool:
        before = [s for s in steps[:start + 1] if s["action"] == "draft_script" and s["observation"].get("ok")]
        revised = [s for s in steps[start + 1:end] if s["action"] == "draft_script" and s["observation"].get("ok")]
        return bool(before and revised and before[-1]["observation"].get("script") is not None
                    and revised[-1]["observation"].get("script") is not None
                    and before[-1]["observation"]["script"] != revised[-1]["observation"]["script"])

    corrections = []
    for i, step in enumerate(steps):
        obs = step["observation"]
        later = steps[i + 1:]
        if step["action"] == "search_assets" and obs.get("retrieval_status") == "no_results":
            if any(s["action"] == "search_assets" and s["arguments"].get("query") != step["arguments"].get("query") for s in later):
                corrections.append("query_rewrite")
        if not obs.get("ok") and step["action"] in {"search_assets", "estimate_duration", "check_brand_rules"}:
            if any(s["action"] == step["action"] and s["observation"].get("ok") for s in later):
                corrections.append("tool_retry")
        if step["action"] == "estimate_duration" and obs.get("is_overtime"):
            if any(s["action"] == "estimate_duration" and s["observation"].get("passed")
                   and s["observation"].get("target_duration_seconds") == obs.get("target_duration_seconds")
                   and s["observation"].get("script_version") != obs.get("script_version")
                   and changed_draft_between(i, j) for j, s in enumerate(steps[i + 1:], i + 1)):
                corrections.append("duration_revision")
        if step["action"] == "check_brand_rules" and obs.get("ok") and not obs.get("passed"):
            if any(s["action"] == "check_brand_rules" and s["observation"].get("passed")
                   and s["observation"].get("script_version") != obs.get("script_version")
                   and changed_draft_between(i, j) for j, s in enumerate(steps[i + 1:], i + 1)):
                corrections.append("rule_revision")
    corrections = sorted(set(corrections))
    if case == "missing_info":
        verified = status == "needs_info" and "duration_seconds" in result.get("missing_information", [])
    elif case == "no_assets":
        empty = [s for s in searches if s["observation"].get("retrieval_status") == "no_results"]
        verified = len(empty) >= 2 and "query_rewrite" in corrections and status in {"needs_info", "failed"}
    elif case == "tool_failure":
        verified = completed and "tool_retry" in corrections
    elif case == "overtime":
        verified = completed and "duration_revision" in corrections
    elif case == "unsupported_claim":
        verified = status != "completed" and any(
            v["code"] == "unsupported_quantitative_claim" for s in checks for v in s["observation"]["violations"]
        ) and any(s.get("error", {}).get("type") == "FinishBlocked" for s in steps if s.get("error"))
    elif case == "max_steps":
        verified = status == "incomplete" and "max_steps=" in result.get("reason", "") and bool(steps)
    elif case == "rule_repair":
        verified = completed and "rule_revision" in corrections
    else:
        verified = bool(completed)
    return {"behavior_verified": bool(verified), "observed_adaptations": corrections,
            "duration_estimates": [s["observation"]["total_estimated_seconds"] for s in estimates]}


def inspect_trace_events(trace: dict, events: list[dict]) -> dict:
    """Rebuild the JSON snapshot from the append-only event stream."""
    issues, rebuilt = [], []
    if not events or events[0].get("event") != "run_started" or events[-1].get("event") != "run_finished":
        return {"verified": False, "issues": ["Missing run boundaries"]}
    for entry in events:
        if entry.get("run_id") != trace.get("run_id"):
            issues.append("Event run_id mismatch")
        kind = entry.get("event")
        if kind == "run_started":
            if any(entry.get(key) != trace.get(key) for key in ("input", "mode", "model", "execution_kind")):
                issues.append("Run header differs from final snapshot")
        elif kind == "configuration":
            config = {k: v for k, v in entry.items() if k not in {"event", "timestamp_utc", "run_id"}}
            if config != trace.get("configuration"):
                issues.append("Configuration snapshot mismatch")
        elif kind == "step_executed":
            step = {k: v for k, v in entry.items() if k not in {"event", "timestamp_utc", "run_id"}}
            if step.get("step") != len(rebuilt) + 1 or step.get("next_action") is not None:
                issues.append("Invalid original step event")
            rebuilt.append(step)
        elif kind == "next_action_observed":
            index = entry.get("step", 0) - 1
            if index != len(rebuilt) - 1 or index < 0 or rebuilt[index].get("next_action") is not None:
                issues.append("Invalid next-action event")
            else:
                rebuilt[index]["next_action"] = entry.get("next_action")
    if rebuilt != trace.get("steps"):
        issues.append("JSONL steps differ from final JSON")
    for index, step in enumerate(rebuilt):
        expected = rebuilt[index + 1]["action"] if index + 1 < len(rebuilt) else None
        if step.get("next_action") != expected:
            issues.append("next_action differs from following executed action")
    if any(events[-1].get(key) != trace.get(key) for key in ("final_status", "final_result")):
        issues.append("Final event differs from final JSON")
    return {"verified": not issues, "issues": issues, "step_events": len(rebuilt)}

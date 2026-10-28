"""Inspect observable behavior; completion alone does not prove a correction path."""


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
                   and s["observation"].get("script_version") != obs.get("script_version") for s in later):
                corrections.append("duration_revision")
        if step["action"] == "check_brand_rules" and obs.get("ok") and not obs.get("passed"):
            if any(s["action"] == "check_brand_rules" and s["observation"].get("passed")
                   and s["observation"].get("script_version") != obs.get("script_version") for s in later):
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

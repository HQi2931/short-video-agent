"""Native agent loop. Only the adapter chooses actions; runtime enforces truth gates."""
from .llm_adapter import Adapter, ModelError
from .schemas import ACTION_ARGUMENTS, action_catalog
from .state import AgentState, fingerprint
from .tools import ToolExecutor
from .tracing import TraceLogger


class AgentRunner:
    def __init__(self, state: AgentState, adapter: Adapter, trace: TraceLogger,
                 executor: ToolExecutor | None = None, max_steps: int = 12, policy_version: int = 2):
        if type(max_steps) is not int or not 1 <= max_steps <= 100:
            raise ValueError("max_steps must be an integer in [1, 100]")
        if trace.trace["mode"] != adapter.mode:
            raise ValueError("Trace mode must match adapter mode")
        self.state, self.adapter, self.trace = state, adapter, trace
        self.executor = executor or ToolExecutor()
        self.max_steps = max_steps
        self.policy_version = policy_version

    def decision_context(self, step: int) -> dict:
        context = self.state.context()
        remaining = self.max_steps - step + 1
        context.update(step=step, max_steps=self.max_steps, remaining_steps=remaining)
        if self.policy_version >= 2:
            state = self.state
            checks = {name: check for name, check in (
                ("estimate_duration", state.current_duration), ("check_brand_rules", state.current_rules))
                if check and check.get("script_version") == state.script_version}
            pending = [name for name in ("estimate_duration", "check_brand_rules")
                       if not checks.get(name, {}).get("passed")]
            context["decision_progress"] = {
                "current_checks": checks, "pending_checks": pending,
                "completed_checks": [name for name, check in checks.items() if check.get("passed")],
                "minimum_steps_to_finish_current": len(pending) + 1,
                "steps_required_for_draft_checks_finish": 4,
                "can_draft_and_verify": remaining >= 4,
                "historical_feedback_notice": "Only current_checks applies to this script_version. Historical failures are not current failures.",
            }
        return context

    def run(self) -> dict:
        state = self.state
        if state.status != "pending":
            raise ValueError("A run state cannot be reused; create a fresh state")
        state.status = "running"
        configuration = {
            "decision_policy_version": self.policy_version,
            "max_steps": self.max_steps, "tools": self.executor.registry.names,
            "fault_injection_once": sorted(self.executor.fail_once),
            "data_fingerprint": fingerprint({
                "assets": [a.model_dump() for a in state.assets], "rules": state.rules.model_dump(),
            }),
            "asset_snapshot": [a.model_dump() for a in state.assets], "rules_snapshot": state.rules.model_dump(),
        }
        self.trace.trace["configuration"] = configuration
        self.trace.event("configuration", configuration)
        for step in range(1, self.max_steps + 1):
            context = self.decision_context(step)
            version_before = state.script_version
            model_record, arguments, reason = {}, {}, ""
            fatal = False
            try:
                decision = self.adapter.decide(context, action_catalog())
                model_record = decision.record
                action = decision.action.action
                arguments = decision.action.arguments
                reason = decision.action.reason_summary
                observation = self._execute_action(action, arguments)
            except ModelError as exc:
                action, model_record, fatal = "model_error", exc.record, exc.fatal
                observation = {"ok": False, "error": {"type": "ModelError", "message": str(exc)}}
            except Exception as exc:
                action = "runtime_error"
                observation = {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}
            if not observation.get("ok"):
                state.errors.append({"step": step, "action": action, "error": observation.get("error")})
            state.last_observation = observation
            state.actions.append({"step": step, "action": action, "arguments": arguments, "observation": observation})
            self.trace.step({
                "step": step, "action": action, "arguments": arguments, "observation": observation,
                "reason_summary": reason, "model_call": model_record,
                "error": observation.get("error"), "script_version_before": version_before,
                "script_version_after": state.script_version,
            })
            if fatal:
                state.status = "incomplete"
                state.reason = observation["error"]["message"]
            if state.status in {"completed", "needs_info", "failed", "incomplete"}:
                break
        else:
            state.status = "incomplete"
            state.reason = f"Reached max_steps={self.max_steps} without a verified result"
        return self.trace.finish(self.result())

    def _execute_action(self, action: str, arguments: dict) -> dict:
        state = self.state
        # Validate arguments before any mutation; business tools validate once more at their boundary.
        try:
            args = ACTION_ARGUMENTS[action].model_validate(arguments)
        except Exception as exc:
            # Tool errors, including rejected arguments, require renewed validation.
            if action in {"search_assets", "estimate_duration", "check_brand_rules"}:
                state.invalidate()
            return {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}}
        if action in {"search_assets", "estimate_duration", "check_brand_rules"}:
            observation = self.executor.execute(action, arguments, state)
            if self.policy_version >= 2 and action != "search_assets" and observation.get("ok"):
                observation["revision_feedback"] = {
                    "script_version": state.script_version,
                    "current_seconds": (observation if action == "estimate_duration" else state.current_duration or {}).get("total_estimated_seconds"),
                    "target_seconds": state.user_input.duration_seconds,
                    "exceeded_seconds": (observation if action == "estimate_duration" else state.current_duration or {}).get("exceeded_seconds"),
                    "violations": observation.get("violations", []),
                    "scenes": [s.model_dump() for s in state.script.storyboard],
                    "revalidate_after_edit": ["estimate_duration", "check_brand_rules"],
                    "guidance": "Fix reported scenes; preserve supported facts/source IDs. Check the new version before further edits.",
                }
            return observation
        if action == "draft_script":
            if state.user_input.missing_fields():
                return {"ok": False, "error": {"type": "MissingInput", "message": "Request required fields before drafting"}}
            if not state.retrieved_assets:
                return {"ok": False, "error": {"type": "MissingEvidence", "message": "Retrieve evidence before drafting"}}
            if self.policy_version >= 2:
                if state.script and args.script.model_dump() == state.script.model_dump():
                    return {"ok": False, "error": {"type": "UnchangedScript", "message": "Identical script rejected; use current checks or run pending checks"}}
                drafts = [i for i, item in enumerate(state.actions)
                          if item["action"] == "draft_script" and item["observation"].get("ok")]
                if drafts and not any(item["action"] in {"search_assets", "estimate_duration", "check_brand_rules"}
                                      and item["observation"].get("ok") for item in state.actions[drafts[-1]+1:]):
                    return {"ok": False, "error": {"type": "FeedbackRequired", "message": "No new successful tool feedback since last draft; check current script before editing again"}}
                remaining = self.max_steps - len(state.actions)
                if remaining < 4:
                    state.status = "incomplete"
                    state.reason = "Insufficient steps for draft, two fresh checks and finish"
                    return {"ok": False, "error": {"type": "InsufficientBudget", "message": state.reason},
                            "remaining_steps": remaining, "required_steps": 4}
            state.update_script(args.script)
            return {"ok": True, "script_revision": state.script_revision, "script_version": state.script_version,
                    "script": state.script.model_dump(), "checks_invalidated": True}
        if action == "request_info":
            state.status = "needs_info"
            state.missing_information = list(dict.fromkeys(state.user_input.missing_fields() + args.fields))
            state.question = args.question
            state.reason = "User input or reliable evidence is required"
            return {"ok": True, "fields": state.missing_information, "question": args.question}
        if action == "finish":
            blockers = state.finish_errors()
            if blockers:
                return {"ok": False, "error": {"type": "FinishBlocked", "message": "; ".join(blockers)}, "blockers": blockers}
            state.status = "completed"
            state.reason = "Current script passed deterministic duration and conservative evidence/brand checks"
            return {"ok": True, "status": state.status, "script_version": state.script_version}
        if action == "stop":
            state.status, state.reason = "failed", args.reason
            return {"ok": True, "status": state.status, "reason": args.reason}
        return {"ok": False, "error": {"type": "UnknownAction", "message": action}}

    def result(self) -> dict:
        state = self.state
        # Export is a second boundary: direct object edits must never retain success.
        if state.status == "completed":
            blockers = state.finish_errors()
            if blockers:
                state.status = "incomplete"
                state.reason = "Completion invalidated before export: " + "; ".join(blockers)
        version = state.script_version
        duration = state.current_duration
        if duration and duration.get("script_version") != version:
            duration = None
        rules = state.current_rules
        if rules and rules.get("script_version") != version:
            rules = None
        script = state.script.model_dump() if state.script else {"title": None, "storyboard": [], "risk_flags": []}
        duration_scenes = {s["scene_id"]: s for s in duration["scenes"]} if duration else {}
        used_ids = set()
        for scene in script["storyboard"]:
            scene["estimated_seconds"] = duration_scenes.get(scene["scene_id"], {}).get("estimated_seconds")
            used_ids.update(scene["source_ids"])
        return {
            "run_id": self.trace.run_id, "mode": self.adapter.mode, "model": self.adapter.model,
            "status": state.status, "reason": state.reason,
            "title": script["title"], "topic": state.user_input.topic, "audience": state.user_input.audience,
            "platform": state.user_input.platform, "style": state.user_input.style,
            "target_duration_seconds": state.user_input.duration_seconds,
            "script_version": version, "script_revision": state.script_revision,
            "storyboard": script["storyboard"],
            "total_estimated_seconds": duration["total_estimated_seconds"] if duration else None,
            "used_asset_ids": sorted(used_ids),
            "sources": [a.model_dump() for asset_id, a in state.retrieved_assets.items() if asset_id in used_ids],
            "duration_check": duration, "brand_rule_check": rules,
            "risk_flags": script["risk_flags"] + (rules["risk_reasons"] if rules else []),
            "missing_information": state.missing_information or state.user_input.missing_fields(),
            "question": state.question, "errors": state.errors,
            "completed_steps": [{"step": a["step"], "action": a["action"], "ok": a["observation"].get("ok")} for a in state.actions],
            "last_observation": state.last_observation,
            "limitations": ["合成素材，仅用于工程验证。", "时长是工程估算，需要真人口播复核。",
                            "仅通过原文和批准文案核验，未知改写会被阻断。"],
        }

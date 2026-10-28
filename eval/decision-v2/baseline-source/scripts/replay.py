"""Recompute recorded actions offline. This never calls a model or writes a Trace."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import AgentRunner
from src.schemas import Action, Asset, BrandRules, UserInput
from src.state import AgentState, fingerprint
from src.tools import ToolExecutor

if __package__:
    from .evidence import inspect_trace_events
else:
    from evidence import inspect_trace_events


def replay_trace(trace: dict, events: list[dict], output: dict) -> dict:
    issues = []
    event_check = inspect_trace_events(trace, events)
    if not event_check["verified"]:
        issues.extend({"step": None, "phase": "events", "problem": text} for text in event_check["issues"])
    if output != trace.get("final_result"):
        issues.append({"step": None, "phase": "output", "problem": "Output differs from final Trace"})
    evaluated = 0
    try:
        config = trace["configuration"]
        state = AgentState(
            UserInput.model_validate(trace["input"]),
            [Asset.model_validate(a) for a in config["asset_snapshot"]],
            BrandRules.model_validate(config["rules_snapshot"]),
        )
        data_hash = fingerprint({"assets": [a.model_dump() for a in state.assets], "rules": state.rules.model_dump()})
        if data_hash != config["data_fingerprint"]:
            issues.append({"step": None, "phase": "configuration", "problem": "Data fingerprint mismatch"})
        # Only _execute_action/result are invoked. No adapter.decide or TraceLogger exists here.
        runner = AgentRunner(
            state, SimpleNamespace(mode=trace["mode"], model=trace["model"]),
            SimpleNamespace(trace={"mode": trace["mode"]}, run_id=trace["run_id"]),
            ToolExecutor(fail_once=set(config["fault_injection_once"])), config["max_steps"],
        )
        state.status = "running"
        if len(trace["steps"]) > config["max_steps"]:
            issues.append({"step": None, "phase": "limit", "problem": "Recorded steps exceed max_steps"})
        for index, step in enumerate(trace["steps"], 1):
            if state.status != "running":
                issues.append({"step": index, "phase": "control", "problem": "Action recorded after terminal state"})
                break
            selected = Action.model_validate({key: step[key] for key in ("action", "arguments", "reason_summary")})
            if state.script_version != step["script_version_before"]:
                issues.append({"step": index, "phase": "version", "problem": "Wrong version before action"})
            if trace["mode"] == "live":
                context = json.loads(step["model_call"]["request"]["messages"][-1]["content"])["state"]
                expected = state.context()
                expected.update({"step": index, "max_steps": config["max_steps"], "remaining_steps": config["max_steps"] - index + 1})
                if context != expected:
                    different = sorted(key for key in set(context) | set(expected) if context.get(key) != expected.get(key))
                    issues.append({"step": index, "phase": "context", "problem": "Request state differs from recomputation", "fields": different})
            observation = runner._execute_action(selected.action, selected.arguments)
            if observation != step["observation"]:
                issues.append({"step": index, "phase": "tool", "problem": "Observation differs from deterministic execution"})
            if state.script_version != step["script_version_after"]:
                issues.append({"step": index, "phase": "version", "problem": "Wrong version after action"})
            if not observation.get("ok"):
                state.errors.append({"step": index, "action": selected.action, "error": observation.get("error")})
            state.last_observation = observation
            state.actions.append({"step": index, "action": selected.action, "arguments": selected.arguments, "observation": observation})
            evaluated += 1
        if state.status == "running" and evaluated == config["max_steps"]:
            state.status = "incomplete"
            state.reason = f"Reached max_steps={config['max_steps']} without a verified result"
        recomputed = runner.result()
        if recomputed != trace["final_result"]:
            different = sorted(key for key in set(recomputed) | set(trace["final_result"])
                               if recomputed.get(key) != trace["final_result"].get(key))
            issues.append({"step": None, "phase": "result", "problem": "Final result differs from recomputation", "fields": different})
    except Exception as exc:
        issues.append({"step": evaluated + 1, "phase": "unsupported_or_invalid_record", "problem": type(exc).__name__})
    return {
        "verified": not issues, "method": "offline_replay_no_model_calls", "model_calls_made": 0,
        "recomputed_steps": evaluated, "event_log": event_check, "issues": issues,
    }


def replay_files(trace_path: Path, root: Path = ROOT) -> dict:
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    events = [json.loads(line) for line in trace_path.with_suffix(".jsonl").read_text(encoding="utf-8").splitlines()]
    output = json.loads((root / "examples/outputs" / trace_path.name).read_text(encoding="utf-8"))
    return replay_trace(trace, events, output)

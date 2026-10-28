"""Synthetic records test audit tamper detection, not remote model capability."""
from copy import deepcopy
import json

from scripts.evidence import inspect_live_calls


def trace_fixture():
    trace = {"mode": "live", "execution_kind": "real_api", "model": "transport-fixture", "input": {"topic": "字幕"}, "steps": []}
    for index, name in enumerate(("search_assets", "stop")):
        selected = {"action": name, "arguments": {}, "reason_summary": "transport fixture"}
        context = {"user_input": trace["input"],
                   "last_observation": trace["steps"][-1]["observation"] if index else None}
        trace["steps"].append({
            "step": index + 1, **selected, "observation": {"ok": True, "sequence": index},
            "model_call": {"mode": "live", "http_status": 200,
                           "request": {"model": trace["model"], "messages": [{"role": "user", "content": json.dumps({"state": context})}]},
                           "response": {"model": "transport-fixture", "content": json.dumps(selected)}},
        })
    for index, step in enumerate(trace["steps"]):
        step["next_action"] = trace["steps"][index + 1]["action"] if index + 1 < len(trace["steps"]) else None
    return trace


def test_record_integrity_checks_actions_and_feedback():
    result = inspect_live_calls(trace_fixture())
    assert result["verified"] and result["recorded_decisions"] == 2
    assert result["observation_feedback_checks"] == 1


def test_http_success_alone_cannot_validate_tampered_action():
    trace = trace_fixture()
    trace["steps"][0]["arguments"] = {"query": "伪造参数"}
    result = inspect_live_calls(trace)
    assert not result["verified"] and result["issues"][0]["problem"] == "Action differs from model response"


def test_missing_observation_feedback_is_detected():
    trace = deepcopy(trace_fixture())
    request = trace["steps"][1]["model_call"]["request"]
    payload = json.loads(request["messages"][-1]["content"])
    payload["state"]["last_observation"] = None
    request["messages"][-1]["content"] = json.dumps(payload)
    result = inspect_live_calls(trace)
    assert not result["verified"] and result["issues"][0]["problem"] == "Previous observation was not fed back"


def test_input_defaults_and_whitespace_normalization_are_not_tampering():
    trace = trace_fixture()
    trace["input"] = {"topic": " 字幕 "}
    for step in trace["steps"]:
        message = step["model_call"]["request"]["messages"][-1]
        payload = json.loads(message["content"])
        payload["state"]["user_input"] = {"topic": "字幕", "duration_seconds": None}
        message["content"] = json.dumps(payload)
    assert inspect_live_calls(trace)["verified"]

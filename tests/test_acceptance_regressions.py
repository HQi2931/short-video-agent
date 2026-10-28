"""Adversarial acceptance regressions; synthetic fixtures are not live evidence."""
from types import SimpleNamespace

import pytest

from src.agent import AgentRunner
from src.llm_adapter import MockAdapter
from scripts.evidence import inspect_behavior, inspect_live_calls
from test_evidence import trace_fixture


@pytest.mark.parametrize("change", ["script", "input", "assets", "direct_mutation"])
def test_result_cannot_remain_completed_after_verified_state_changes(run_fixture, change):
    result, _, state = run_fixture()
    assert result["status"] == "completed"
    if change == "script":
        edited = state.script.model_copy(deep=True)
        edited.title = "记录此刻"
        state.update_script(edited)
    elif change == "input":
        updated = state.user_input.model_copy(deep=True)
        updated.duration_seconds = 1
        state.replace_input(updated)
    elif change == "assets":
        state.replace_assets([])
    else:
        state.script.storyboard[0].narration += "效率提升80%。"
    runner = AgentRunner(state, MockAdapter([]), SimpleNamespace(trace={"mode": "mock"}, run_id="diagnostic_after_edit"))
    output = runner.result()
    assert output["status"] != "completed"


def test_live_integrity_rejects_wrong_next_action():
    trace = trace_fixture()
    trace["steps"][0]["next_action"] = "finish"
    trace["steps"][1]["next_action"] = None
    assert not inspect_live_calls(trace)["verified"]


def test_live_integrity_rejects_explicit_mock_execution_kind():
    trace = trace_fixture()
    trace["execution_kind"] = "scripted_mock"
    assert not inspect_live_calls(trace)["verified"]


def test_overtime_evidence_requires_actual_changed_model_draft():
    trace = {
        "steps": [
            {"action": "estimate_duration", "observation": {"ok": True, "passed": False, "is_overtime": True,
                                                          "script_version": "before", "total_estimated_seconds": 40}},
            {"action": "estimate_duration", "observation": {"ok": True, "passed": True, "is_overtime": False,
                                                          "script_version": "after", "total_estimated_seconds": 20}},
        ],
        "final_result": {"status": "completed", "script_version": "after",
                         "duration_check": {"passed": True, "script_version": "after"},
                         "brand_rule_check": {"passed": True, "script_version": "after"}},
    }
    assert not inspect_behavior("overtime", trace)["behavior_verified"]

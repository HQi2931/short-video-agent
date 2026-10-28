import json

import pytest

from src.mock_fixtures import action


@pytest.mark.parametrize(("scenario", "status"), [
    ("normal", "completed"), ("missing_info", "needs_info"), ("no_assets", "needs_info"),
    ("tool_failure", "completed"), ("overtime", "completed"), ("unsupported_claim", "failed"),
    ("changed_duration", "completed"), ("changed_assets", "completed"), ("sparse", "completed"),
    ("rule_repair", "completed"),
])
def test_mock_scenarios(run_fixture, scenario, status):
    result, trace, state = run_fixture(scenario)
    assert result["status"] == trace["final_status"] == status
    assert trace["mode"] == result["mode"] == "mock"
    assert trace["execution_kind"] == "scripted_mock"
    assert trace["real_model_responses"] == 0
    if status == "completed":
        assert result["duration_check"]["passed"] and result["brand_rule_check"]["passed"]
        assert result["total_estimated_seconds"] <= result["target_duration_seconds"]
        assert result["sources"] and result["used_asset_ids"]
        assert not state.finish_errors()
        assert all(s["estimated_seconds"] is not None and s["fact_refs"] for s in result["storyboard"])


def test_overtime_has_actual_distinct_revisions_and_rechecks(run_fixture):
    _, trace, state = run_fixture("overtime")
    checks = [s["observation"] for s in trace["steps"] if s["action"] == "estimate_duration"]
    assert len(checks) == 2
    assert checks[0]["is_overtime"] and checks[1]["passed"]
    assert checks[0]["total_estimated_seconds"] > checks[1]["total_estimated_seconds"]
    assert checks[0]["script_version"] != checks[1]["script_version"]
    assert state.script_revision == 2


def test_no_results_has_two_actual_queries_then_requests_evidence(run_fixture):
    result, trace, _ = run_fixture("no_assets")
    searches = [s for s in trace["steps"] if s["action"] == "search_assets"]
    assert len(searches) == 2
    assert searches[0]["arguments"]["query"] != searches[1]["arguments"]["query"]
    assert all(s["observation"]["retrieval_status"] == "no_results" for s in searches)
    assert result["missing_information"] == ["assets"]
    assert result["storyboard"] == []


def test_rule_repair_revalidates_both_checks(run_fixture):
    result, trace, state = run_fixture("rule_repair")
    assert not state.rule_checks[0]["passed"] and state.rule_checks[1]["passed"]
    assert len(state.duration_checks) == len(state.rule_checks) == 2
    assert state.rule_checks[0]["script_version"] != result["script_version"]
    assert "保证涨粉" not in json.dumps(result["storyboard"], ensure_ascii=False)


def test_unfounded_effect_cannot_finish(run_fixture):
    result, trace, _ = run_fixture("unsupported_claim")
    finish = next(s for s in trace["steps"] if s["action"] == "finish")
    assert not finish["observation"]["ok"] and finish["error"]["type"] == "FinishBlocked"
    assert result["status"] == "failed"
    assert result["brand_rule_check"]["unsupported_claims"]


def test_trace_auto_records_arguments_observations_next_action_and_events(run_fixture, tmp_path):
    result, trace, _ = run_fixture()
    steps = trace["steps"]
    for before, after in zip(steps, steps[1:]):
        assert before["next_action"] == after["action"]
    assert steps[-1]["next_action"] is None
    disk = json.loads((tmp_path / (trace["run_id"] + ".json")).read_text(encoding="utf-8"))
    events = [json.loads(s) for s in (tmp_path / (trace["run_id"] + ".jsonl")).read_text(encoding="utf-8").splitlines()]
    assert disk["final_result"] == result
    assert sum(e["event"] == "step_executed" for e in events) == len(steps)
    assert events[-1]["event"] == "run_finished"
    assert all("reason_summary" in s and "arguments" in s and "observation" in s for s in steps)


def test_missing_input_is_not_guessed(run_fixture):
    result, trace, _ = run_fixture("missing_info")
    assert result["target_duration_seconds"] is None
    assert result["missing_information"] == ["duration_seconds"]
    assert [s["action"] for s in trace["steps"]] == ["request_info"]


def test_runtime_rejects_premature_finish_and_draft(run_fixture, script):
    actions = [action("finish"), action("draft_script", {"script": script.model_dump()}),
               action("stop", {"reason": "未检索到证据"})]
    result, trace, _ = run_fixture(actions=actions)
    assert all(not s["observation"]["ok"] for s in trace["steps"][:2])
    assert result["status"] == "failed"

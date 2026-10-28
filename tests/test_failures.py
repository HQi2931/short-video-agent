import pytest

from src.agent import AgentRunner
from src.mock_fixtures import action, mock_plan
from src.tools import ToolExecutor, default_registry
from src.tracing import TraceLogger


def test_tool_failure_is_observed_and_retry_is_recorded(run_fixture):
    result, trace, _ = run_fixture("tool_failure")
    estimates = [s for s in trace["steps"] if s["action"] == "estimate_duration"]
    assert not estimates[0]["observation"]["ok"] and estimates[0]["error"]
    assert estimates[1]["observation"]["ok"]
    assert estimates[0]["next_action"] == "estimate_duration"
    assert result["errors"] and result["status"] == "completed"


def test_error_cannot_be_skipped_by_finish(run_fixture, user_input, catalog):
    plan = mock_plan("normal", user_input, catalog[0]) + [action("stop", {"reason": "工具失败，验证未完成"})]
    result, trace, _ = run_fixture(actions=plan, executor=ToolExecutor(fail_once={"estimate_duration"}))
    finish = next(s for s in trace["steps"] if s["action"] == "finish")
    assert not finish["observation"]["ok"]
    assert result["status"] == "failed" and result["duration_check"] is None


@pytest.mark.parametrize("tool", ["estimate_duration", "check_brand_rules"])
def test_failed_recheck_discards_a_previous_pass(state, script, tool):
    from test_validation import prime_state
    executor = prime_state(state, script)
    executor.fail_once.add(tool)
    failure = executor.execute(tool, {}, state)
    assert not failure["ok"] and state.finish_errors()
    assert (state.current_duration if tool == "estimate_duration" else state.current_rules) is None


def test_search_error_after_passes_requires_new_validation(state, script):
    from test_validation import prime_state
    executor = prime_state(state, script)
    executor.fail_once.add("search_assets")
    assert not executor.execute("search_assets", {"query": "字幕"}, state)["ok"]
    assert state.current_duration is None and state.current_rules is None and state.finish_errors()


def test_removed_tool_cannot_leave_old_pass_usable(run_fixture, catalog, user_input):
    registry = default_registry()
    registry._tools.pop("estimate_duration")
    result, trace, _ = run_fixture(executor=ToolExecutor(registry))
    assert result["status"] != "completed"
    assert next(s for s in trace["steps"] if s["action"] == "estimate_duration")["error"]["type"] == "KeyError"


@pytest.mark.parametrize("failure_type", ["exception", "unavailable"])
def test_tool_exceptions_and_unavailable_status(state, failure_type):
    registry = default_registry()
    def broken(*args):
        if failure_type == "exception":
            raise OSError("Fixture storage unavailable")
        return {"ok": False, "error": "unavailable"}
    registry._tools["search_assets"] = broken
    observation = ToolExecutor(registry).execute("search_assets", {"query": "轻剪"}, state)
    assert not observation["ok"] and observation["error"]
    assert not state.retrieved_assets


def test_search_failure_can_be_retried_without_guessing(run_fixture, catalog, user_input):
    plan = mock_plan("normal", user_input, catalog[0])
    plan.insert(1, action("search_assets", {"query": "字幕"}, "离线预设重试"))
    result, trace, _ = run_fixture(actions=plan, executor=ToolExecutor(fail_once={"search_assets"}))
    assert result["status"] == "completed"
    assert not trace["steps"][0]["observation"]["ok"]
    assert trace["steps"][1]["observation"]["ok"]


def test_max_steps_returns_incomplete_and_last_observation(run_fixture):
    result, trace, _ = run_fixture("max_steps", max_steps=3)
    assert result["status"] == "incomplete"
    assert "max_steps=3" in result["reason"]
    assert len(result["completed_steps"]) == len(trace["steps"]) == 3
    assert result["last_observation"] == trace["steps"][-1]["observation"]


def test_mock_exhaustion_is_not_completed(run_fixture):
    result, trace, _ = run_fixture(actions=[action("search_assets", {"query": "轻剪"})])
    assert result["status"] == "incomplete" and "exhausted" in result["reason"]
    assert trace["steps"][-1]["action"] == "model_error"


def test_invalid_action_parameters_are_observed_not_executed(run_fixture):
    result, trace, _ = run_fixture(actions=[
        action("search_assets", {"query": "轻剪", "unknown": True}),
        action("stop", {"reason": "非法参数测试"}),
    ])
    assert not trace["steps"][0]["observation"]["ok"]
    assert result["sources"] == []


def test_trace_refuses_overwrite_and_unsafe_run_id(tmp_path):
    TraceLogger(tmp_path, "mock", "fixture", {}, run_id="kept")
    with pytest.raises(FileExistsError):
        TraceLogger(tmp_path, "mock", "fixture", {}, run_id="kept")
    with pytest.raises(ValueError):
        TraceLogger(tmp_path, "mock", "fixture", {}, run_id="../escape")


def test_trace_redacts_exact_key_in_nested_error_and_requests(tmp_path):
    trace = TraceLogger(tmp_path, "mock", "fixture", {}, secrets=["fixture-secret"])
    trace.event("error", {"nested": ["echo fixture-secret", {"Authorization": "Bearer fixture-secret"}]})
    text = trace.events_path.read_text(encoding="utf-8")
    assert "fixture-secret" not in text and "[REDACTED]" in text


def test_invalid_max_steps_rejected(state, tmp_path):
    from src.llm_adapter import MockAdapter
    trace = TraceLogger(tmp_path, "mock", "fixture", {})
    with pytest.raises(ValueError):
        AgentRunner(state, MockAdapter([]), trace, max_steps=0)

import pytest
from pydantic import ValidationError

from src.mock_fixtures import action, mock_plan
from src.schemas import Script, UserInput
from src.tools import ToolExecutor


@pytest.mark.parametrize("patch", [
    {"duration_seconds": -1}, {"duration_seconds": 0}, {"duration_seconds": "30"},
    {"duration_seconds": True}, {"duration_seconds": float("inf")},
    {"topic": ""}, {"topic": "   "}, {"unknown": 1},
])
def test_input_rejects_invalid_values(user_input, patch):
    with pytest.raises(ValidationError):
        UserInput.model_validate({**user_input.model_dump(), **patch})


def test_script_cannot_accept_model_supplied_estimates_or_status(script):
    raw = script.model_dump()
    raw["total_estimated_seconds"] = 1
    with pytest.raises(ValidationError):
        Script.model_validate(raw)
    raw.pop("total_estimated_seconds")
    raw["storyboard"][0]["estimated_seconds"] = 1
    with pytest.raises(ValidationError):
        Script.model_validate(raw)


def prime_state(state, script):
    executor = ToolExecutor()
    executor.execute("search_assets", {"query": "轻剪字幕"}, state)
    state.update_script(script)
    assert executor.execute("estimate_duration", {}, state)["passed"]
    assert executor.execute("check_brand_rules", {}, state)["passed"]
    assert not state.finish_errors()
    return executor


@pytest.mark.parametrize("field", ["title", "visual", "narration", "subtitle", "source_ids", "fact_refs", "risk_flags"])
def test_any_script_edit_invalidates_old_checks(state, script, field):
    prime_state(state, script)
    version = state.script_version
    edited = script.model_copy(deep=True)
    if field == "title":
        edited.title = "记录此刻"
    elif field == "risk_flags":
        edited.risk_flags = ["需要确认"]
    elif field == "source_ids":
        edited.storyboard[0].source_ids = []
    elif field == "fact_refs":
        edited.storyboard[0].fact_refs = []
    else:
        setattr(edited.storyboard[0], field, "一起看看")
    state.update_script(edited)
    assert state.script_version != version
    assert state.current_duration is None and state.current_rules is None
    assert state.finish_errors()


def test_identical_explicit_revision_still_requires_rechecks(state, script):
    prime_state(state, script)
    state.update_script(script)
    assert state.current_duration is None and state.current_rules is None
    assert state.finish_errors()


@pytest.mark.parametrize("change", ["duration", "audience", "assets", "rules", "retrieved_assets", "direct_script_edit"])
def test_context_changes_make_stale_checks_unusable(state, script, change):
    prime_state(state, script)
    previous = state.script_version
    if change == "duration":
        updated = state.user_input.model_copy(deep=True)
        updated.duration_seconds = 1
        state.replace_input(updated)
    elif change == "audience":
        state.user_input.audience = "另一个受众"
    elif change == "assets":
        assets = [a.model_copy(deep=True) for a in state.assets]
        assets[0].source_text += "版本已更新。"
        state.replace_assets(assets)
        assert not state.retrieved_assets
    elif change == "rules":
        state.rules.banned_phrases.append("轻剪")
    elif change == "retrieved_assets":
        state.retrieved_assets.clear()
    else:
        state.script.storyboard[0].subtitle += "新的文字。"
    assert state.script_version != previous
    assert state.finish_errors()


def test_corpus_changed_in_place_cannot_revalidate_using_old_retrieval(state, script):
    executor = prime_state(state, script)
    state.assets[0].source_text += "素材已更新。"
    result = executor.execute("check_brand_rules", {}, state)
    assert not result["ok"] and "stale" in result["error"]["message"]
    assert state.finish_errors()


def test_repeated_same_script_check_records_real_identical_result(state, script):
    executor = prime_state(state, script)
    first = state.current_duration.copy()
    second = executor.execute("estimate_duration", {}, state)
    assert first == second
    assert len(state.duration_checks) == 2
    assert state.duration_checks[0]["script_version"] == state.duration_checks[1]["script_version"]


def test_model_cannot_check_another_script_or_override_target(state, script):
    executor = prime_state(state, script)
    assert not executor.execute("estimate_duration", {"target_duration_seconds": 999}, state)["ok"]
    assert state.current_duration is None and state.finish_errors()
    assert not executor.execute("check_brand_rules", {"script": script.model_dump()}, state)["ok"]
    assert state.current_rules is None


def test_edit_after_checks_cannot_reuse_passes_to_finish(run_fixture, user_input, catalog):
    plan = mock_plan("normal", user_input, catalog[0])
    replacement = plan[1]["arguments"]["script"].copy()
    replacement["title"] = "记录此刻"
    plan = plan[:-1] + [action("draft_script", {"script": replacement}), action("finish"),
                        action("stop", {"reason": "修改后没有重新验证"})]
    result, trace, _ = run_fixture(actions=plan)
    assert result["status"] == "failed" and result["total_estimated_seconds"] is None
    assert result["brand_rule_check"] is None
    assert trace["steps"][-2]["error"]["type"] == "FinishBlocked"

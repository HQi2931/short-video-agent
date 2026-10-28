from copy import deepcopy

from src.mock_fixtures import action, mock_plan
from src.agent import AgentRunner
from src.llm_adapter import MockAdapter
from src.tracing import TraceLogger


def plan(catalog, user_input):
    return mock_plan('normal', user_input, catalog[0])


def test_reject_changed_draft_without_feedback(run_fixture, catalog, user_input):
    steps = plan(catalog, user_input)
    changed = deepcopy(steps[1])
    changed['arguments']['script']['title'] += '。'
    steps.insert(2, changed)
    result, trace, state = run_fixture(actions=steps)
    assert trace['steps'][2]['observation']['error']['type'] == 'FeedbackRequired'
    assert state.script_revision == 1
    assert result['status'] == 'completed'


def test_identical_draft_does_not_invalidate_valid_checks(run_fixture, catalog, user_input):
    steps = plan(catalog, user_input)
    steps.insert(-1, deepcopy(steps[1]))
    result, trace, state = run_fixture(actions=steps)
    assert trace['steps'][-2]['observation']['error']['type'] == 'UnchangedScript'
    assert state.script_revision == 1 and result['status'] == 'completed'


def test_revision_budget_returns_incomplete_before_mutation(run_fixture, catalog, user_input):
    steps = plan(catalog, user_input)
    changed = deepcopy(steps[1])
    changed['arguments']['script']['title'] += '。'
    steps = steps[:4] + [changed]
    result, trace, state = run_fixture(actions=steps, max_steps=7)
    assert result['status'] == 'incomplete'
    assert trace['steps'][-1]['observation']['error']['type'] == 'InsufficientBudget'
    assert state.script_revision == 1


def test_revision_invalidates_both_checks_and_new_risk_blocks_finish(run_fixture, catalog, user_input):
    steps = plan(catalog, user_input)
    changed = deepcopy(steps[1])
    changed['arguments']['script']['storyboard'][0]['narration'] += '保证涨粉'
    steps = steps[:4] + [changed, action('finish'), action('estimate_duration'),
                           action('check_brand_rules'), action('finish')]
    result, trace, state = run_fixture(actions=steps, max_steps=9)
    assert state.script_revision == 2
    assert len(trace['steps'][5]['observation']['blockers']) == 2
    assert not state.current_rules['passed']
    assert result['status'] == 'incomplete'
    assert trace['steps'][-1]['observation']['error']['type'] == 'FinishBlocked'


def test_normal_and_exact_budget_path(run_fixture):
    result, _, _ = run_fixture(max_steps=5)
    assert result['status'] == 'completed'


def test_maximum_steps_remains_incomplete(run_fixture, catalog, user_input):
    steps = plan(catalog, user_input)[:4]
    result, trace, _ = run_fixture(actions=steps, max_steps=4)
    assert result['status'] == 'incomplete'
    assert len(trace['steps']) == 2  # Draft requires four remaining steps; only three remain.
    assert trace['steps'][-1]['observation']['error']['type'] == 'InsufficientBudget'


def test_budget_exhausted_after_valid_draft(run_fixture, catalog, user_input):
    steps = plan(catalog, user_input)
    steps[-1] = action('estimate_duration')
    result, trace, _ = run_fixture(actions=steps, max_steps=5)
    assert len(trace['steps']) == 5 and result['status'] == 'incomplete'


def test_current_feedback_and_budget_are_version_bound(tmp_path, state, script):
    runner = AgentRunner(state, MockAdapter([]), TraceLogger(tmp_path, 'mock', 'deterministic-fixture', state.user_input.model_dump()))
    state.update_script(script)
    runner._execute_action('estimate_duration', {})
    current = runner.decision_context(3)['decision_progress']
    assert current['completed_checks'] == ['estimate_duration']
    assert current['pending_checks'] == ['check_brand_rules']
    assert current['steps_required_for_draft_checks_finish'] == 4
    state.update_script(script)
    assert not runner.decision_context(4)['decision_progress']['current_checks']


def test_structured_feedback_contains_references_and_revalidation(run_fixture):
    _, trace, _ = run_fixture('overtime')
    obs = next(s['observation'] for s in trace['steps'] if s['action'] == 'estimate_duration')
    feedback = obs['revision_feedback']
    assert feedback['exceeded_seconds'] > 0
    assert feedback['current_seconds'] > feedback['target_seconds']
    assert feedback['scenes'][0]['fact_refs']
    assert feedback['revalidate_after_edit'] == ['estimate_duration', 'check_brand_rules']

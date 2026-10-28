"""Offline evaluation-contract tests. These are not live model evidence."""
import json
from types import SimpleNamespace

import pytest

from eval.dataset import ROOT, load_dataset
from eval.metrics import aggregate, evaluate, ratio
from eval.run import BudgetAdapter
from src.llm_adapter import ModelError


def test_holdout_is_fixed_separate_and_has_explicit_acceptance():
    data = load_dataset()
    assert len(data['cases']) == 20
    assert {a['asset_id'] for a in data['assets']}.isdisjoint({'P01','P02','P03','P04'})
    assert {s: sum(c['scenario']==s for c in data['cases']) for s in
            ('normal','duration','no_assets','tool_failure','unsupported','brand')} == dict(
                normal=4,duration=4,no_assets=3,tool_failure=3,unsupported=3,brand=3)


@pytest.mark.parametrize('used,tools', [(2,0),(0,3)])
def test_budget_blocks_before_remote_call_and_is_fatal(used, tools):
    def forbidden(*args):
        pytest.fail('Budget check must happen before network')
    adapter = BudgetAdapter(SimpleNamespace(model='unit-test',decide=forbidden),dict(used=used,max_requests=2),3)
    with pytest.raises(ModelError) as exc:
        adapter.decide({'executed_actions':[{'action':'search_assets'}]*tools},{})
    assert exc.value.fatal and exc.value.record['budget_stop']


def test_budget_counts_failed_transport_attempts():
    def fail(*args):
        raise ModelError('offline transport fixture')
    budget=dict(used=0,max_requests=2)
    adapter=BudgetAdapter(SimpleNamespace(model='unit-test',decide=fail),budget,3)
    with pytest.raises(ModelError):
        adapter.decide({'executed_actions':[]},{})
    assert budget['used']==1


def test_no_executions_never_becomes_perfect_score():
    rows=[dict(executed=False,scenario='duration')]*4
    result=aggregate(rows,20)
    assert result['task_completion_rate']==ratio(0,20)
    assert result['duration_correction_success_rate']==ratio(0,4)
    assert result['evidence_traceability_rate']['value'] is None
    assert result['average_agent_steps']['value'] is None


def historical_case(name, scenario):
    path=ROOT/'examples/traces'/name
    trace=json.loads(path.read_text(encoding='utf-8'))
    events=[json.loads(line) for line in path.with_suffix('.jsonl').read_text(encoding='utf-8').splitlines()]
    return evaluate(dict(id='offline-audit-fixture',scenario=scenario),trace,events),trace,events


def test_completed_without_actual_correction_is_not_duration_success():
    row,_,_=historical_case('live_overtime_round1.json','duration')
    assert row['task_completed']
    assert not row['duration_triggered'] and not row['case_pass']
    assert 'D' in row['failure_categories']


def test_revised_trace_passes_but_tampered_observation_does_not():
    row,trace,events=historical_case('live_overtime_tight_round1.json','duration')
    assert row['case_pass'] and row['duration_corrected']
    trace['steps'][0]['observation']['query']='tampered offline fixture'
    row=evaluate(dict(id='tamper-test',scenario='duration'),trace,events)
    assert not row['task_completed'] and not row['case_pass']
    assert 'G' in row['failure_categories']


def test_missing_references_cannot_be_hidden_by_traceability_percentage():
    row,_,_=historical_case('live_normal_round1.json','normal')
    assert row['total_refs']>0 and row['valid_refs']==row['total_refs']
    assert row['human_review']['status']=='NOT VERIFIED'
    assert row['human_review']['semantic_claims_supported'] is None


def test_consecutive_revisions_are_visible_without_deducting_tool_rate(run_fixture, catalog, user_input):
    from src.mock_fixtures import mock_plan
    plan=mock_plan('normal',user_input,catalog[0])
    plan.insert(2,plan[1])
    _,trace,_=run_fixture(actions=plan)
    # Mock trace is a contract fixture only, so live audit correctly rejects completion.
    row=evaluate(dict(id='offline-repeat-fixture',scenario='normal'),trace,[])
    assert row['unchecked_consecutive_draft_steps']==[3]
    assert 'C' in row['observed_categories']
    assert row['repeated_steps']==[]


def test_error_aware_replay_verifies_recovery_and_rejects_tampering(tmp_path, state):
    """Scripted protocol fixture, zero network calls; not a live result."""
    from src.agent import AgentRunner
    from src.llm_adapter import Decision
    from src.schemas import Action
    from src.tracing import TraceLogger
    from eval.audit import audit_error_run

    class ProtocolFixture:
        mode='live'
        model='offline-protocol-fixture'
        count=0

        def decide(self, context, catalog):
            self.count+=1
            content='malformed JSON' if self.count==1 else json.dumps(dict(
                action='request_info',arguments={'fields':['assets'],'question':'请补充素材'},reason_summary='离线协议测试'))
            record=dict(mode='live',request={'model':self.model,'messages':[{'role':'user','content':json.dumps(
                {'state':context,'action_catalog':catalog},ensure_ascii=False)}]},http_status=200,
                response={'content':content,'finish_reason':'stop'})
            if self.count==1:
                record['parse_or_transport_error']='JSONDecodeError: offline fixture'
                raise ModelError('Invalid model response or transport failure: JSONDecodeError',record)
            return Decision(Action.model_validate_json(content),record)

    trace=TraceLogger(tmp_path,'live',ProtocolFixture.model,state.user_input.model_dump())
    AgentRunner(state,ProtocolFixture(),trace).run()
    events=[json.loads(line) for line in trace.events_path.read_text(encoding='utf-8').splitlines()]
    assert audit_error_run(trace.trace,events)['verified']
    trace.trace['steps'][1]['model_call']['request']['model']='tampered'
    assert not audit_error_run(trace.trace,events)['verified']

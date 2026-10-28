"""Replay error-bearing runs without changing the historical audit tools."""
import json
from types import SimpleNamespace

from scripts.evidence import inspect_trace_events
from src.agent import AgentRunner
from src.llm_adapter import parse_action
from src.schemas import Asset, BrandRules, UserInput, action_catalog
from src.state import AgentState, fingerprint
from src.tools import ToolExecutor


def audit_error_run(trace, events):
    issues=[]
    config=trace['configuration']
    state=AgentState(UserInput.model_validate(trace['input']),
                     [Asset.model_validate(a) for a in config['asset_snapshot']], BrandRules.model_validate(config['rules_snapshot']))
    runner=AgentRunner(state,SimpleNamespace(mode='live',model=trace['model']),
                       SimpleNamespace(trace={'mode':'live'},run_id=trace['run_id']),
                       ToolExecutor(fail_once=set(config['fault_injection_once'])),config['max_steps'])
    state.status='running'
    if fingerprint({'assets':[a.model_dump() for a in state.assets],'rules':state.rules.model_dump()}) != config['data_fingerprint']:
        issues.append('Configuration fingerprint mismatch')
    for i,s in enumerate(trace['steps'],1):
        try:
            assert state.status=='running'
            assert i==s['step'] and i<=config['max_steps']
            assert s['script_version_before']==state.script_version
            record=s['model_call']
            if not record.get('budget_stop'):
                req=record['request']
                context=state.context() | dict(step=i,max_steps=config['max_steps'],remaining_steps=config['max_steps']-i+1)
                assert json.loads(req['messages'][-1]['content'])=={'state':context,'action_catalog':action_catalog()}
                assert req['model']==trace['model'] and record['mode']=='live'
            if s['action']=='model_error':
                response=record.get('response') or {}
                invalid=False
                if response.get('content') is not None:
                    try:
                        parse_action(response['content'])
                    except Exception:
                        invalid=True
                assert (record.get('budget_stop') or record.get('parse_or_transport_error') or
                        record.get('http_status',200)!=200 or response.get('refusal') or
                        response.get('finish_reason') in {'length','content_filter'} or invalid)
                assert not s['observation']['ok'] and s['observation']['error']['type']=='ModelError'
                obs=s['observation']
                fatal=record.get('budget_stop') or record.get('http_status') in {400,401,403,404} or 300<=record.get('http_status',200)<400
                if fatal:
                    state.status='incomplete'
                    state.reason=obs['error']['message']
            else:
                assert record.get('http_status')==200
                action=parse_action(record['response']['content'])
                assert action.model_dump()=={k:s[k] for k in ('action','arguments','reason_summary')}
                obs=runner._execute_action(action.action,action.arguments)
                assert obs==s['observation']
            assert s['script_version_after']==state.script_version
            if not obs.get('ok'):
                state.errors.append({'step':i,'action':s['action'],'error':obs.get('error')})
            state.last_observation=obs
            state.actions.append({'step':i,'action':s['action'],'arguments':s['arguments'],'observation':obs})
        except Exception as exc:
            issues.append(f'Step {i}: {type(exc).__name__}')
            break
    if state.status=='running' and len(trace['steps'])==config['max_steps']:
        state.status='incomplete'
        state.reason=f'Reached max_steps={config["max_steps"]} without a verified result'
    if runner.result()!=trace['final_result']:
        issues.append('Final result differs from replay')
    event_check=inspect_trace_events(trace,events)
    issues += event_check['issues']
    return dict(verified=not issues, method='offline_error_aware_replay_no_model_calls', model_calls_made=0,
                issues=issues,event_log=event_check)

"""Deterministic checks are proxies, never human semantic labels."""
from collections import Counter

from src.schemas import Asset, BrandRules, Script, UserInput
from src.state import AgentState
from src.tools import check_brand_rules, estimate_duration
from scripts.evidence import inspect_behavior, inspect_live_calls
from scripts.replay import replay_trace
from .audit import audit_error_run

TOOLS = {'search_assets', 'estimate_duration', 'check_brand_rules'}
CATEGORIES = dict(A='检索问题', B='工具选择问题', C='无效重复调用', D='时长估算或修改问题',
                  E='事实幻觉/未核实文本代理', F='规则校验问题', G='状态管理问题', H='模型服务错误')


def ratio(n, d):
    return {'numerator': n, 'denominator': d, 'value': n / d if d else None}


def evaluate(case, trace, events):
    steps, result = trace['steps'], trace['final_result']
    config = trace['configuration']
    assets = [Asset.model_validate(a) for a in config['asset_snapshot']]
    rules = BrandRules.model_validate(config['rules_snapshot'])
    script = Script.model_validate({k: result[k] for k in ('title', 'storyboard', 'risk_flags')}
                                  | {'storyboard': [{k: v for k, v in s.items() if k != 'estimated_seconds'}
                                                   for s in result['storyboard']], 'risk_flags': []}) if result['storyboard'] else None
    # Result risk_flags includes derived rule messages; use last accepted draft's actual flags.
    drafts = [s for s in steps if s['action'] == 'draft_script' and s['observation'].get('ok')]
    if script and drafts:
        script = Script.model_validate(drafts[-1]['observation']['script'])
    state = AgentState(UserInput.model_validate(trace['input']), assets, rules)
    state.script = script
    state.script_revision = result['script_revision']
    state.retrieved_assets = {a['asset_id']: Asset.model_validate(a) for a in result['sources']}
    checked = check_brand_rules(script, list(state.retrieved_assets.values()), rules, state.script_version,
                               state.user_input.topic) if script else None
    timing = estimate_duration(script, state.user_input.duration_seconds, state.script_version, rules.timing) if script else None
    replay = replay_trace(trace, events, result)
    calls = inspect_live_calls(trace)
    if any(s['action'] == 'model_error' for s in steps):
        replay = audit_error_run(trace, events)
        calls = {'verified': replay['verified'], 'method': 'error_aware_request_response_audit', 'issues': replay['issues']}
    replay_applicable = all(s['action'] != 'runtime_error' for s in steps)
    complete = bool(result['status'] == 'completed' and checked and checked['passed'] and timing['passed']
                    and replay_applicable and replay['verified'] and calls['verified'])
    behavior = inspect_behavior('overtime' if case['scenario'] == 'duration' else case['scenario'], trace)
    searches = [s for s in steps if s['action'] == 'search_assets']
    forbidden = any(t in str(script.model_dump()) for t in case.get('forbidden', [])) if script else False
    safe = complete and not forbidden
    if result['status'] in {'needs_info', 'failed'}:
        # Safe terminal refusal requires no usable script; residual unsafe drafts are not passed.
        safe = not script and bool(searches) and bool(result.get('question') or result.get('reason'))
    passed = complete
    if case['scenario'] == 'duration':
        passed = complete and 'duration_revision' in behavior['observed_adaptations']
    elif case['scenario'] == 'no_assets':
        passed = (result['status'] == 'needs_info' and not script and len({s['arguments'].get('query') for s in searches}) >= 2
                  and all(s['observation'].get('retrieval_status') == 'no_results' for s in searches)
                  and bool(result.get('question')) and bool(result.get('missing_information')))
    elif case['scenario'] == 'tool_failure':
        passed = complete and 'tool_retry' in behavior['observed_adaptations'] and any(
            s['action'] in case['fail_once'] and not s['observation'].get('ok') for s in steps)
    elif case['scenario'] in {'unsupported', 'brand'}:
        passed = safe
    passed = passed and calls['verified'] and replay_applicable and replay['verified']

    inappropriate, repeats, violations = [], [], []
    unchecked_drafts = [s['step'] for previous,s in zip(steps,steps[1:]) if
                        previous['action'] == s['action'] == 'draft_script' and
                        previous['observation'].get('ok') and s['observation'].get('ok')]
    seen_checks, seen_searches = set(), set()
    for s in steps:
        a, obs = s['action'], s['observation']
        if a in TOOLS and not obs.get('ok') and 'Injected one-time' not in str(obs):
            inappropriate.append(s['step'])
        if a in {'estimate_duration', 'check_brand_rules'} and obs.get('ok'):
            key = (a, s['script_version_before'])
            if key in seen_checks:
                repeats.append(s['step'])
            seen_checks.add(key)
        if a == 'search_assets' and obs.get('ok'):
            key = str(s['arguments'])
            if key in seen_searches:
                repeats.append(s['step'])
            seen_searches.add(key)
        if a == 'check_brand_rules':
            violations += obs.get('violations', [])
    categories = set()
    if any(s['action'] == 'model_error' and not s['model_call'].get('budget_stop') for s in steps): categories.add('H')
    if any(s['action'] == 'runtime_error' for s in steps): categories.add('G')
    if any(s['action'] == 'draft_script' and not s['observation'].get('ok') for s in steps): categories.add('F')
    if inappropriate or any(s['action'] == 'finish' and not s['observation'].get('ok') for s in steps): categories.add('B')
    if repeats or unchecked_drafts: categories.add('C')
    if not complete and any(s['action']=='estimate_duration' and s['observation'].get('is_overtime') for s in steps): categories.add('D')
    if any(v['code'] in {'unverified_text', 'unsupported_claim', 'unsupported_quantitative_claim', 'evidence_mismatch', 'unknown_fact'} for v in violations): categories.add('E')
    if any(v['code'] not in {'unverified_text', 'unsupported_claim', 'unsupported_quantitative_claim'} for v in violations): categories.add('F')
    if not passed:
        if case['scenario'] == 'duration': categories.add('D')
        if case['scenario'] == 'no_assets': categories.add('A')
        if case['scenario'] == 'unsupported': categories.add('E')
        if case['scenario'] == 'brand': categories.add('F')
        if replay_applicable and not replay['verified']: categories.add('G')
        if not categories: categories.add('B')
    refs = [r for scene in (script.storyboard if script else []) for r in scene.fact_refs]
    valid_refs = 0
    lookup = {a.asset_id: a for a in state.retrieved_assets.values()}
    for scene in script.storyboard if script else []:
        for ref in scene.fact_refs:
            a = lookup.get(ref.asset_id)
            f = next((f for f in a.facts if f.fact_id == ref.fact_id), None) if a else None
            valid_refs += int(bool(f and ref.asset_id in scene.source_ids and ref.evidence_text == f.text == ref.claim_text
                                  and f.text in a.source_text and any(f.text in text for text in
                                      (scene.visual, scene.narration, scene.subtitle, script.title))))
    return dict(case_id=case['id'], scenario=case['scenario'], status=result['status'], case_pass=bool(passed),
                task_completed=complete, duration_triggered=any(s['observation'].get('is_overtime') for s in steps if s['action']=='estimate_duration'),
                duration_corrected=complete and 'duration_revision' in behavior['observed_adaptations'],
                steps=len(steps), tool_calls=sum(s['action'] in TOOLS for s in steps),
                inappropriate_tool_steps=inappropriate, repeated_steps=repeats,
                unchecked_consecutive_draft_steps=unchecked_drafts,
                valid_refs=valid_refs, total_refs=len(refs), final_script=bool(script),
                unsupported_final=bool(checked and checked['unsupported_claims']),
                observed_categories=sorted(categories), failure_categories=sorted(categories) if not passed else [],
                behavior=behavior, replay=replay, replay_applicable=replay_applicable, live_calls=calls,
                final_rule_recheck=checked, final_duration_recheck=timing,
                human_review={'status': 'NOT VERIFIED', 'reviewer': None, 'reviewed_at': None,
                              'topic_preserved': None, 'tool_decisions_appropriate': None, 'semantic_claims_supported': None,
                              'creative_quality_1_to_5': None, 'refusal_explanation_adequate': None, 'notes': None})


def aggregate(rows, planned):
    executed = [r for r in rows if r.get('executed')]
    tools = sum(r['tool_calls'] for r in executed)
    refs = sum(r['total_refs'] for r in executed)
    scripts = sum(r['final_script'] for r in executed)
    durations = [r for r in executed if r['scenario'] == 'duration']
    return dict(planned=planned, executed=len(executed), skipped=planned-len(executed),
        case_acceptance_rate=ratio(sum(r['case_pass'] for r in executed), planned),
        task_completion_rate=ratio(sum(r['task_completed'] for r in executed), planned),
        duration_correction_success_rate=ratio(sum(r['duration_corrected'] for r in durations), sum(r.get('scenario')=='duration' for r in rows)),
        duration_triggered=sum(r['duration_triggered'] for r in durations),
        tool_decision_appropriateness_proxy=ratio(tools-sum(len(set(r['inappropriate_tool_steps']) | set(r['repeated_steps'])) for r in executed), tools),
        evidence_traceability_rate=ratio(sum(r['valid_refs'] for r in executed), refs),
        unsupported_claim_rate_proxy=ratio(sum(r['unsupported_final'] for r in executed), scripts),
        average_agent_steps=ratio(sum(r['steps'] for r in executed), len(executed)),
        average_tool_calls=ratio(tools, len(executed)),
        average_end_to_end_latency_seconds=ratio(sum(r['latency_seconds'] for r in executed), len(executed)),
        failure_case_frequency={c: sum(c in r['failure_categories'] for r in executed) for c in CATEGORIES},
        observed_issue_case_frequency={c: sum(c in r['observed_categories'] for r in executed) for c in CATEGORIES},
        human_semantic_metrics='NOT VERIFIED')

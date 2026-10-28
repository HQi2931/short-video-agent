"""Offline, repeatable comparison of immutable live batches; no model requests."""
import argparse
import hashlib
import json
from pathlib import Path

from src.schemas import Asset, BrandRules, Script
from src.tools import check_brand_rules, estimate_duration


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def batch(path):
    rows = read(path / 'results.json')
    first = []
    first_submission_errors = []
    for row in rows:
        if not row.get('executed'):
            continue
        trace_path = path / row['trace']
        if not trace_path.exists():  # Rescores retain relative paths into their immutable parent batch.
            trace_path = path.parent / row['trace']
        trace = read(trace_path)
        submissions = [s for s in trace['steps'] if s['action'] == 'draft_script']
        if submissions and not submissions[0]['observation'].get('ok'):
            first_submission_errors.append(dict(case=row['case_id'], step=submissions[0]['step'],
                                                error=submissions[0]['observation'].get('error')))
        drafts = [s for s in trace['steps'] if s['action'] == 'draft_script' and s['observation'].get('ok')]
        if not drafts:
            continue
        script = Script.model_validate(drafts[0]['observation']['script'])
        rules = BrandRules.model_validate(trace['configuration']['rules_snapshot'])
        assets = [Asset.model_validate(a) for a in trace['configuration']['asset_snapshot']]
        duration = estimate_duration(script, trace['input']['duration_seconds'], 'offline-first', rules.timing)
        checks = check_brand_rules(script, assets, rules, 'offline-first', trace['input']['topic'])
        first.append(dict(case=row['case_id'], seconds=duration['total_estimated_seconds'],
                          target=duration['target_duration_seconds'], overtime=duration['is_overtime'],
                          scenes=len(script.storyboard), unreferenced_scenes=sum(not s.fact_refs for s in script.storyboard),
                          violations=checks['violations'],
                          missing_fields=[f'{s["scene_id"]}.{key}' for s in drafts[0]['arguments']['script']['storyboard']
                                          for key in ('scene_id', 'visual', 'narration', 'subtitle', 'source_ids', 'fact_refs') if key not in s]))
    return dict(path=str(path), summary=read(path/'summary.json'), first_drafts=first,
                first_submission_errors=first_submission_errors,
                failures=[dict(case=r['case_id'], status=r.get('status'), categories=r.get('failure_categories'),
                               replay_issues=r.get('replay', {}).get('issues'), reason=r.get('reason'))
                          for r in rows if not r.get('case_pass')],
                evidence_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [path/'results.json', path/'summary.json', path/'environment.json']})


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--baseline-fixed', type=Path, required=True)
    parser.add_argument('--optimized-fixed', type=Path, required=True)
    parser.add_argument('--baseline-holdout', type=Path, required=True)
    parser.add_argument('--optimized-holdout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = {name: batch(getattr(args, name)) for name in
            ('baseline_fixed', 'optimized_fixed', 'baseline_holdout', 'optimized_holdout')}
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for name, value in data.items():
        summary = value['summary']
        print(name, {key: summary[key] for key in (
            'case_acceptance_rate', 'task_completion_rate', 'duration_correction_success_rate',
            'average_agent_steps', 'average_tool_calls', 'average_end_to_end_latency_seconds',
            'unsupported_claim_rate_proxy')})


if __name__ == '__main__':
    main()

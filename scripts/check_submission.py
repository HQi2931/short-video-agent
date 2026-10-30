"""Verify the selected current-prompt evidence offline; never calls a model."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.final_audit import audit_trace, check_runtime_sources
from src.llm_adapter import SYSTEM_PROMPT


def verify():
    rows = json.loads((ROOT / 'examples/acceptance-current/manifest.json').read_text(encoding='utf-8'))
    results = []
    for row in rows:
        path = ROOT / row['trace']
        trace = json.loads(path.read_text(encoding='utf-8'))
        steps = trace['steps']
        checks = {
            'replay': audit_trace(path, ROOT)['verified'],
            'original_bytes': hashlib.sha256(path.read_bytes()).hexdigest() == row['trace_sha256'],
            'current_prompt': all(s['model_call']['request']['messages'][0]['content'] == SYSTEM_PROMPT for s in steps),
            'input_matches': json.loads((ROOT / row['input']).read_text(encoding='utf-8')) == trace['input'],
            'output_matches': json.loads((ROOT / row['output']).read_text(encoding='utf-8')) == trace['final_result'],
        }
        case = row['case']
        status = trace['final_status']
        if case == 'missing_info':
            behavior = status == 'needs_info' and 'duration_seconds' in trace['final_result']['missing_information']
        elif case == 'no_assets':
            searches = [s for s in steps if s['action'] == 'search_assets']
            behavior = status == 'needs_info' and len({s['arguments']['query'] for s in searches}) > 1 and all(s['observation'].get('retrieval_status') == 'no_results' for s in searches)
        elif case == 'tool_failure':
            failed = next((s for s in steps if not s['observation'].get('ok') and s['action'] == 'estimate_duration'), None)
            behavior = status == 'completed' and failed is not None and any(s['step'] > failed['step'] and s['action'] == 'estimate_duration' and s['observation'].get('passed') for s in steps)
        elif case in {'overtime', 'rule_repair'}:
            tool = 'estimate_duration' if case == 'overtime' else 'check_brand_rules'
            failed = next((s for s in steps if s['action'] == tool and s['observation'].get('passed') is False), None)
            later_drafts = [s for s in steps if failed and s['step'] > failed['step'] and s['action'] == 'draft_script' and s['observation'].get('ok')]
            behavior = status == 'completed' and bool(later_drafts) and any(s['step'] > later_drafts[0]['step'] and s['action'] == tool and s['observation'].get('passed') and s['observation'].get('script_version') != failed['observation'].get('script_version') for s in steps)
        else:
            behavior = case == 'normal' and status == 'completed'
        checks['behavior'] = behavior
        results.append({'case': case, 'status': status, 'checks': checks, 'verified': all(checks.values())})
    covered = {r['case'] for r in results} == {'normal', 'missing_info', 'no_assets', 'tool_failure', 'overtime', 'rule_repair'}
    version = check_runtime_sources(ROOT)
    return {'model_calls_made': 0, 'verified': version['verified'] and covered and all(r['verified'] for r in results), 'version': version, 'cases': results}


if __name__ == '__main__':
    report = verify()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['verified'] else 1)

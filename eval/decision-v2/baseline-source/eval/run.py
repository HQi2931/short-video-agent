"""Run: python -m eval.run --live (otherwise validate only, zero model calls)."""
import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from src.agent import AgentRunner
from src.llm_adapter import LiveAdapter, ModelError
from src.schemas import Asset, BrandRules, UserInput
from src.state import AgentState, fingerprint
from src.tools import ToolExecutor
from src.tracing import TraceLogger
from .dataset import ROOT, load_dataset
from .metrics import aggregate, evaluate


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


class BudgetAdapter:
    mode = 'live'

    def __init__(self, inner, budget, max_tools):
        self.inner, self.budget, self.max_tools = inner, budget, max_tools
        self.model = inner.model

    def decide(self, context, catalog):
        tools = sum(a['action'] in {'search_assets', 'estimate_duration', 'check_brand_rules'} for a in context['executed_actions'])
        if self.budget['used'] >= self.budget['max_requests'] or tools >= self.max_tools:
            raise ModelError('Evaluation request/tool budget exhausted', {'budget_stop': True}, fatal=True)
        self.budget['used'] += 1  # transport errors also consume budget; no hidden retries
        return self.inner.decide(context, catalog)


def main(argv=None):
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--live', action='store_true')
    p.add_argument('--dataset', type=Path)
    p.add_argument('--max-steps', type=int, default=12)
    p.add_argument('--max-tool-calls', type=int, default=9)
    p.add_argument('--max-requests', type=int, default=240)
    p.add_argument('--timeout', type=float, default=45)
    p.add_argument('--output-root', type=Path, default=ROOT/'eval/runs')
    args = p.parse_args(argv)
    if not (1 <= args.max_steps <= 100 and 1 <= args.max_tool_calls <= 100 and args.max_requests > 0 and 0 < args.timeout <= 300):
        p.error('Budgets must be positive; steps/tools <=100, timeout <=300')
    data = load_dataset(args.dataset)
    out = args.output_root / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_')+uuid4().hex[:8])
    out.mkdir(parents=True, exist_ok=False)
    save(out/'dataset.json', data)
    load_dotenv(ROOT/'.env', override=False)
    config = dict(python=sys.version, platform=platform.platform(), model=os.getenv('LLM_MODEL') or None,
                  base_url=os.getenv('LLM_BASE_URL') or None, response_format=os.getenv('LLM_RESPONSE_FORMAT','json_object'),
                  max_steps=args.max_steps, max_tool_calls=args.max_tool_calls, max_requests=args.max_requests,
                  timeout=args.timeout, dataset_sha256=fingerprint(data), started_at_utc=datetime.now(timezone.utc).isoformat(),
                  source_sha256={str(f.relative_to(ROOT)): fingerprint(f.read_text(encoding='utf-8')) for f in
                                 sorted(list((ROOT/'src').glob('*.py'))+list((ROOT/'eval').glob('*.py')))},
                  live_requested=args.live, key_present=bool(os.getenv('LLM_API_KEY')))
    # No credentials, request headers, or dotenv contents are exported.
    save(out/'environment.json', config)
    rows=[]
    budget={'used':0, 'max_requests':args.max_requests}
    inner=None
    unavailable=None
    if args.live:
        try:
            inner=LiveAdapter(os.getenv('LLM_API_KEY',''), os.getenv('LLM_BASE_URL',''), os.getenv('LLM_MODEL',''),
                              timeout=args.timeout, response_format=config['response_format'])
        except ValueError:
            unavailable='Live configuration unavailable/invalid; no request made'
    for case in data['cases']:
        if inner is None or budget['used'] >= args.max_requests:
            rows.append(dict(case_id=case['id'], scenario=case['scenario'], executed=False,
                             reason=unavailable or ('request_budget_exhausted' if args.live else 'offline_validation_only')))
            continue
        state=AgentState(UserInput.model_validate(case['input']), [Asset.model_validate(a) for a in data['assets']],
                         BrandRules.model_validate(data['rules']))
        trace=TraceLogger(out/'traces', 'live', inner.model, case['input'], run_id=case['id'], secrets=[os.getenv('LLM_API_KEY','')])
        start=time.perf_counter()
        result=AgentRunner(state, BudgetAdapter(inner,budget,args.max_tool_calls), trace,
                           ToolExecutor(fail_once=set(case.get('fail_once',[]))), args.max_steps).run()
        latency=time.perf_counter()-start
        save(out/(case['id']+'-output.json'), result)
        events=[json.loads(line) for line in trace.events_path.read_text(encoding='utf-8').splitlines()]
        row=evaluate(case, trace.trace, events)
        usage=[s['model_call'].get('response',{}).get('usage') for s in trace.trace['steps'] if s['model_call'].get('request')]
        row.update(executed=True, latency_seconds=latency, usage_records=usage,
                   reported_total_tokens=sum(u.get('total_tokens',0) for u in usage if u),
                   usage_complete=bool(usage) and all(u and 'total_tokens' in u for u in usage),
                   trace='traces/'+case['id']+'.json', output=case['id']+'-output.json')
        rows.append(row)
        save(out/'results.partial.json', rows)
        print(json.dumps(dict(case=case['id'],status=result['status'],passed=row['case_pass'],requests=budget['used']), ensure_ascii=False),flush=True)
        # Auth/config failures should not spend the remaining budget on identical failures.
        if any(s['model_call'].get('http_status') in {400,401,403,404} for s in trace.trace['steps']):
            inner=None
            unavailable='Provider rejected configuration/authentication; remaining cases skipped'
    summary=aggregate(rows,len(data['cases']))
    summary.update(requests_attempted=budget['used'], reported_total_tokens=sum(r.get('reported_total_tokens',0) for r in rows),
                   live_completed=summary['executed']==len(data['cases']) and all(r.get('live_calls',{}).get('verified') for r in rows),
                   offline_dataset_valid=True)
    save(out/'results.json',rows)
    save(out/'summary.json',summary)
    from .report import render
    (out/'report.md').write_text(render(out,data,config,rows,summary),encoding='utf-8')
    print(str(out),flush=True)
    return 0 if not args.live or (summary['live_completed'] and all(r.get('case_pass') for r in rows)) else 1


if __name__=='__main__':
    raise SystemExit(main())

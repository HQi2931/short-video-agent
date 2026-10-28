"""Offline rescore into a NEW directory; preserves original run and scoring."""
import argparse
import json
from datetime import datetime, timezone
from uuid import uuid4

from .dataset import ROOT
from .metrics import evaluate, aggregate
from .report import render
from .run import save
from src.state import fingerprint


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('run_dir')
    args=p.parse_args()
    source=(ROOT/args.run_dir).resolve()
    data=json.loads((source/'dataset.json').read_text(encoding='utf-8'))
    original=json.loads((source/'results.json').read_text(encoding='utf-8'))
    summary=json.loads((source/'summary.json').read_text(encoding='utf-8'))
    config=json.loads((source/'environment.json').read_text(encoding='utf-8'))
    out=source/('rescore_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_')+uuid4().hex[:6])
    out.mkdir(exist_ok=False)
    rows=[]
    for case,old in zip(data['cases'],original,strict=True):
        if not old['executed']:
            rows.append(old)
            continue
        trace=json.loads((source/old['trace']).read_text(encoding='utf-8'))
        events=[json.loads(line) for line in (source/old['trace']).with_suffix('.jsonl').read_text(encoding='utf-8').splitlines()]
        scored=evaluate(case,trace,events)
        rows.append(old | scored | {'trace':'../'+old['trace'],'output':'../'+old['output']})
    config.update(rescore_source='../',rescore_model_calls=0,
                  scoring_sha256={f.name:fingerprint(f.read_text(encoding='utf-8')) for f in (ROOT/'eval').glob('*.py')})
    metrics=aggregate(rows,len(data['cases']))
    metrics.update(requests_attempted=summary['requests_attempted'],reported_total_tokens=summary['reported_total_tokens'],
                   offline_dataset_valid=True,live_completed=len([r for r in rows if r['executed']])==20 and all(r.get('live_calls',{}).get('verified') for r in rows))
    for name,obj in [('dataset',data),('environment',config),('results',rows),('summary',metrics)]:
        save(out/(name+'.json'),obj)
    (out/'report.md').write_text(render(out,data,config,rows,metrics),encoding='utf-8')
    print(out)


if __name__=='__main__':
    main()

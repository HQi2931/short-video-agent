"""Frozen v1 holdout cases. Do not tune agent prompts against this set."""
import json
from pathlib import Path

from src.schemas import UserInput, Asset, BrandRules

ROOT = Path(__file__).resolve().parents[1]


def load_dataset(path=None):
    data = json.loads((Path(path) if path else ROOT / 'eval/dataset-v1.json').read_text(encoding='utf-8'))
    assert data['cases']
    assert len({c['id'] for c in data['cases']}) == len(data['cases'])
    if path is None:
        assert len(data['cases']) == 20
    for a in data['assets']:
        Asset.model_validate(a)
    BrandRules.model_validate(data['rules'])
    old = [json.loads(p.read_text(encoding='utf-8-sig')) for p in (ROOT / 'examples/inputs').glob('*.json')]
    for c in data['cases']:
        UserInput.model_validate(c['input'])
        assert c['input'] not in old, 'Development sample leaked into holdout'
        assert c['expected'] and c['criteria']
        assert c['scenario'] in {'normal', 'duration', 'no_assets', 'tool_failure', 'unsupported', 'brand'}
    return data

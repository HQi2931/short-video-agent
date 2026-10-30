"""Synthetic engineering cases; these never make real model requests."""
from pathlib import Path

import pytest

from eval.production_contracts import check
from src.schemas import Script, Timing
from src.tools import check_brand_rules, estimate_duration, load_data

ROOT = Path(__file__).resolve().parents[1]


def production_script():
    assets, rules = load_data(ROOT / "data/production-demo")
    asset = assets[0]
    fact = asset.facts[0]
    directions = ("景别：近景。机位：桌面俯拍。动作：双手将产品放到桌面中央。"
                  "字幕：下方居中，避开产品文字。剪辑：动作结束后切到下一镜。"
                  "声音：保留现场轻触声，音乐压低，旁白优先。")
    script = Script.model_validate({"title": "桌面开箱记录", "storyboard": [{
        "scene_id": "S1", "visual": directions, "narration": fact.text, "subtitle": fact.text,
        "source_ids": [asset.asset_id], "fact_refs": [{"asset_id": asset.asset_id, "fact_id": fact.fact_id,
        "evidence_text": fact.text, "claim_text": fact.text}]}], "risk_flags": []})
    return assets, rules, script


def test_detailed_directions_use_same_unchanged_fact_gate():
    assets, rules, script = production_script()
    assert check_brand_rules(script, assets, rules, "v1", "晨栖随行杯")["passed"]
    simple = script.model_copy(deep=True)
    simple.storyboard[0].visual = "镜头展示产品。"
    assert estimate_duration(script, 20, "v1", rules.timing)["total_estimated_seconds"] == estimate_duration(simple, 20, "v1", rules.timing)["total_estimated_seconds"]


@pytest.mark.parametrize("field", ["visual", "narration", "subtitle"])
def test_production_copy_does_not_whitelist_unsupported_product_claims(field):
    assets, rules, script = production_script()
    scene = script.storyboard[0]
    setattr(scene, field, getattr(scene, field) + "效率提升80%，保证防漏。")
    report = check_brand_rules(script, assets, rules, "v1", "晨栖随行杯")
    assert not report["passed"] and report["unsupported_claims"]


def test_production_contract_rejects_fact_hidden_only_in_visual():
    _, _, script = production_script()
    scene = script.storyboard[0]
    scene.visual += scene.narration
    scene.narration = scene.subtitle = "一起看看"
    trace = {"final_result": {"status": "completed", "storyboard": script.model_dump()["storyboard"]}, "steps": []}
    result = check({"id": "fixture", "production_contract": {"required_facts": ["R11:F1"]}}, trace, True)
    assert not result["accepted"] and "required_facts_not_spoken" in result["issues"]


def test_production_contract_cannot_replace_original_failure():
    _, _, script = production_script()
    trace = {"final_result": {"status": "completed", "storyboard": script.model_dump()["storyboard"]}, "steps": []}
    assert not check({"id": "fixture", "production_contract": {"detail": True}}, trace, False)["accepted"]

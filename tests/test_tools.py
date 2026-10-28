from copy import deepcopy

import pytest
from pydantic import ValidationError

from src.mock_fixtures import make_script
from src.schemas import Script, SearchArgs, Timing
from src.tools import check_brand_rules, estimate_duration, search_assets, speech_seconds


def test_search_returns_source_and_explains_score(catalog):
    assets, _ = catalog
    result = search_assets(assets, SearchArgs(query="轻剪的字幕短视频"))
    assert result["ok"] and result["retrieval_status"] == "found"
    assert result["assets"][0]["asset_id"] == "P01"
    assert result["assets"][0]["score"] == len(result["assets"][0]["matched_keywords"])
    assert result["assets"][0]["facts"][0]["text"] in result["assets"][0]["source_text"]


def test_query_rewrite_and_no_results(catalog):
    assets, _ = catalog
    assert search_assets(assets, SearchArgs(query="月球采矿雷达"))["assets"] == []
    assert search_assets(assets, SearchArgs(query="自动文字识别"))["retrieval_status"] == "no_results"
    assert search_assets(assets, SearchArgs(query="字幕"))["retrieval_status"] == "found"


def test_filters_keywords_and_sparse_material(catalog):
    assets, _ = catalog
    result = search_assets(assets, SearchArgs(query="音乐", asset_ids=["P02"]))
    assert len(result["assets"]) == len(result["assets"][0]["facts"]) == 1
    assert search_assets(assets, SearchArgs(query="无关", keywords=["字幕"], asset_ids=["P01"]))["assets"]
    assert not search_assets(assets, SearchArgs(query="字幕", asset_ids=["P03"]))["assets"]


def test_duration_is_deterministic_and_bound_to_version(script, catalog):
    timing = catalog[1].timing
    first = estimate_duration(script, 30, "version-a", timing)
    second = estimate_duration(script, 30, "version-a", timing)
    assert first == second
    assert first["script_version"] == "version-a"
    assert first["total_estimated_seconds"] == round(sum(s["estimated_seconds"] for s in first["scenes"]), 2)
    assert first["passed"] and not first["is_overtime"]
    assert all(s["estimated_seconds"] >= timing.minimum_scene_seconds + timing.transition_seconds for s in first["scenes"])


def test_duration_changes_with_text_and_target(script, catalog):
    timing = catalog[1].timing
    original = estimate_duration(script, 30, "original", timing)
    long = script.model_copy(deep=True)
    long.storyboard[0].narration *= 20
    extended = estimate_duration(long, 30, "long", timing)
    assert extended["total_estimated_seconds"] > original["total_estimated_seconds"]
    assert extended["is_overtime"] and not extended["passed"] and extended["exceeded_seconds"] > 0
    shorter_target = estimate_duration(script, 1, "new-target", timing)
    assert shorter_target["is_overtime"]


def test_long_subtitles_are_not_ignored(script, catalog):
    script.storyboard[0].narration = ""
    script.storyboard[0].subtitle *= 20
    assert estimate_duration(script, 30, "v", catalog[1].timing)["is_overtime"]


def test_speech_formula_counts_multiple_writing_systems():
    timing = Timing()
    assert speech_seconds("你好 hello 500", timing) == pytest.approx(2 / 4.5 + 1 / 2.5 + 1 / 2)
    assert speech_seconds("你好。", timing) > speech_seconds("你好", timing)
    assert speech_seconds("안녕", timing) > 0


@pytest.mark.parametrize("target", [0, -1, float("nan"), float("inf")])
def test_duration_rejects_invalid_target(script, catalog, target):
    with pytest.raises(ValueError):
        estimate_duration(script, target, "v", catalog[1].timing)


def test_supported_script_and_supported_number_pass(script, catalog):
    assets, rules = catalog
    assert check_brand_rules(script, assets, rules, "v")["passed"]
    cup = Script.model_validate(make_script(assets[2]))
    assert "500" in cup.storyboard[1].narration
    assert check_brand_rules(cup, assets, rules, "v")["passed"]


@pytest.mark.parametrize(("mutation", "code"), [
    ("unknown_asset", "unknown_asset"), ("unknown_fact", "unknown_fact"),
    ("evidence", "evidence_mismatch"), ("claim", "unsupported_claim"),
    ("source", "missing_source_id"), ("no_refs", "unverified_text"),
    ("quantitative", "unsupported_quantitative_claim"), ("banned", "banned_phrase"),
    ("paraphrase", "unverified_text"), ("risk", "unresolved_risk"),
    ("visual", "unverified_text"), ("subtitle", "unsupported_quantitative_claim"),
    ("title", "unverified_text"), ("unused", "unused_reference"),
])
def test_fact_and_brand_adversarial_checks(script, catalog, mutation, code):
    assets, rules = catalog
    scene = script.storyboard[0]
    if mutation == "unknown_asset":
        scene.source_ids = ["P999"]
        scene.fact_refs[0].asset_id = "P999"
    elif mutation == "unknown_fact":
        scene.fact_refs[0].fact_id = "F999"
    elif mutation == "evidence":
        scene.fact_refs[0].evidence_text = "轻剪支持人工翻译。"
    elif mutation == "claim":
        scene.fact_refs[0].claim_text = "效率提升80%。"
    elif mutation == "source":
        scene.source_ids = []
    elif mutation == "no_refs":
        scene.fact_refs = []
    elif mutation == "quantitative":
        scene.narration += "效率提升80%。"
    elif mutation == "banned":
        scene.narration += "保证涨粉。"
    elif mutation == "paraphrase":
        scene.narration = "能自动生成所有语言的字幕。"
    elif mutation == "risk":
        script.risk_flags = ["素材版权待确认"]
    elif mutation == "visual":
        scene.visual = "展示效率提升的对比图。"
    elif mutation == "subtitle":
        scene.subtitle += "准确率99%。"
    elif mutation == "title":
        script.title = "全球最优秀的字幕工具"
    elif mutation == "unused":
        scene.narration = scene.subtitle = "一起看看"
    result = check_brand_rules(script, assets, rules, "v")
    assert not result["passed"] and result["needs_confirmation"]
    assert code in {v["code"] for v in result["violations"]}


def test_scene_evidence_cannot_be_borrowed_from_other_scene(script, catalog):
    script.storyboard[0].narration += script.storyboard[1].narration
    result = check_brand_rules(script, *catalog, "v")
    assert not result["passed"]


def test_rewriting_query_cannot_silently_switch_to_unrelated_product(script, catalog):
    result = check_brand_rules(script, *catalog, "v", topic="月球采矿激光雷达")
    assert not result["passed"]
    assert "topic_alignment_unconfirmed" in {v["code"] for v in result["violations"]}


def test_data_model_rejects_facts_absent_from_source(catalog):
    raw = deepcopy(catalog[0][0].model_dump())
    raw["facts"][0]["text"] = "未提供的能力。"
    with pytest.raises(ValidationError):
        type(catalog[0][0]).model_validate(raw)

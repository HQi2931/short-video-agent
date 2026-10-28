"""Deterministic mock plans. These plans are test data, never the live policy."""
from copy import deepcopy

from .schemas import Asset, UserInput

SCENARIOS = (
    "normal", "missing_info", "no_assets", "tool_failure", "overtime", "unsupported_claim",
    "max_steps", "changed_duration", "changed_assets", "sparse", "rule_repair",
)


def action(name: str, arguments: dict | None = None, reason: str = "离线预设测试动作") -> dict:
    return {"action": name, "arguments": arguments or {}, "reason_summary": reason}


def make_script(asset: Asset, *, compact: bool = False) -> dict:
    facts = asset.facts[:1] if compact else asset.facts[:3]
    return {
        "title": "用画面讲述灵感", "risk_flags": [],
        "storyboard": [{
            "scene_id": f"S{i:02d}", "visual": "镜头展示产品。",
            "narration": fact.text, "subtitle": fact.text, "source_ids": [asset.asset_id],
            "fact_refs": [{"asset_id": asset.asset_id, "fact_id": fact.fact_id,
                           "evidence_text": fact.text, "claim_text": fact.text}],
        } for i, fact in enumerate(facts, 1)],
    }


def mock_plan(scenario: str, user_input: UserInput, assets: list[Asset], max_steps: int = 12) -> list[dict]:
    if scenario not in SCENARIOS:
        raise ValueError("Unknown mock scenario")
    missing = user_input.missing_fields()
    if missing:
        return [action("request_info", {"fields": missing, "question": "请补充：" + "、".join(missing)}, "缺少必要输入")]
    query = user_input.topic
    if scenario == "no_assets":
        return [
            action("search_assets", {"query": query}, "检索指定产品"),
            action("search_assets", {"query": query + " 技术规格说明"}, "首次无结果，尝试改写查询"),
            action("request_info", {"fields": ["assets"], "question": "请提供该产品的可靠素材与事实原文。"}, "两次检索均无证据"),
        ]
    if scenario == "max_steps":
        return [action("search_assets", {"query": query}, "上限验证：重复检索") for _ in range(max_steps)]
    candidates = sorted(assets, key=lambda a: -sum(k.casefold() in query.casefold() for k in a.keywords))
    if not candidates:
        return [action("request_info", {"fields": ["assets"], "question": "请提供素材。"})]
    script = make_script(candidates[0], compact=scenario in {"changed_duration", "sparse"})
    prefix = [action("search_assets", {"query": query}, "先获取可追溯的事实")]
    if scenario == "overtime":
        long_script = make_script(candidates[0], compact=True)
        long_script["storyboard"][0]["narration"] *= 22
        prefix += [
            action("draft_script", {"script": long_script}, "离线测试：故意构造冗长首稿"),
            action("estimate_duration", reason="获得首稿实际估时"),
            action("draft_script", {"script": script}, "离线预设修订：删除重复旁白并减少长度"),
        ]
    elif scenario in {"unsupported_claim", "rule_repair"}:
        bad = deepcopy(script)
        bad["storyboard"][0]["narration"] += "效率提升80%。" if scenario == "unsupported_claim" else "保证涨粉。"
        prefix += [action("draft_script", {"script": bad}), action("estimate_duration"), action("check_brand_rules")]
        if scenario == "unsupported_claim":
            return prefix + [action("finish", reason="离线对抗测试：尝试绕过未通过的检查"),
                             action("stop", {"reason": "效果声明缺少事实依据，不能交付。"})]
        prefix += [action("draft_script", {"script": script}, "离线预设修订：删除品牌禁用表述")]
    else:
        prefix += [action("draft_script", {"script": script}, "依据素材原文组织分镜")]
    prefix += [action("estimate_duration", reason="以确定性工具检查时长")]
    if scenario == "tool_failure":
        prefix += [action("estimate_duration", reason="离线预设重试：首次估时被注入失败")]
    return prefix + [action("check_brand_rules", reason="检查引用和品牌约束"),
                     action("finish", reason="请求 Runtime 核验当前版本的两项检查")]

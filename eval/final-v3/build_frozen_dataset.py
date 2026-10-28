"""Author the pre-run v3 test contract; never consumes model outputs or traces."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def asset(asset_id, name, keywords, texts):
    return dict(asset_id=asset_id, name=name, keywords=keywords,
                facts=[dict(fact_id=f"F{i}", text=text) for i, text in enumerate(texts, 1)],
                source_text="".join(texts))


ASSETS = [
    asset("N31", "石珠", ["石珠", "出行二件", "桌面三件"], [
        "石珠为圆形。", "石珠直径为18毫米。"]),
    asset("N32", "栖沙布袋", ["栖沙布袋", "出行二件"], [
        "栖沙布袋含两格。", "栖沙布袋配有拉绳。", "栖沙布袋采用棉布材质。"]),
    asset("N33", "Nivo灯", ["Nivo灯", "桌面三件"], [
        "Nivo灯有USB口。", "Nivo灯额定功率为3.2W，配有USB接口。"]),
    asset("N34", "行墨本", ["行墨本", "桌面三件"], [
        "行墨本共有64页。", "行墨本采用方格内页。"]),
    asset("N35", "澄野收纳箱", ["澄野收纳箱"], [
        "澄野收纳箱内含一块可取出的隔板，箱盖内侧印有分类提示，箱体附带两张空白标签。",
        "澄野收纳箱外部标注长32厘米、宽21厘米、高16厘米，底部印有型号CY-07。",
        "澄野收纳箱附有标签。"]),
]

COMMON = [
    "最终completed须真实模型记录、完整Trace重放、当前版本时长检查和事实规则检查全部通过；不接受模型自报通过。",
    "所有最终引用可核对asset_id、fact_id、source_ids、事实原文与使用位置；当前完成门禁保持不变。",
    "素材数量、平台和风格属于输入覆盖维度；自动场景评分不声称已验证创作质量、平台适配或全部素材实际使用。",
]


def case(number, scenario, topic, audience, platform, duration, style, relevant, **extra):
    criteria = list(COMMON)
    if scenario == "duration":
        criteria.append("必须实际观察超时、不同脚本的修订及后续同目标时长通过；首稿已合格而未触发修订也计场景失败。")
    if scenario == "tool_failure":
        criteria.append("指定工具须真实发生一次注入失败，模型后续重试成功且最终完成；失败观察须进入后续模型请求。")
    if scenario in {"unsupported", "brand"}:
        criteria.append("最终脚本不得含forbidden文本；保留未核实事实的稿件不能通过。安全拒绝仅在无残留稿且有解释时通过场景，不计任务完成。")
    if scenario == "no_assets":
        criteria.append("至少两次不同查询都无结果，随后needs_info；无稿且具备question和missing_information，禁止换成目录内其他产品。")
    return dict(id=f"fresh-{number:02}", scenario=scenario,
                input=dict(topic=topic, audience=audience, platform=platform,
                           duration_seconds=duration, style=style),
                expected=["needs_info"] if scenario == "no_assets" else ["completed"],
                criteria=criteria, expected_relevant_asset_ids=relevant, **extra)


CASES = [
    case(1, "normal", "石珠", "手作爱好者", "抖音", 2.5,
         "极短单品介绍，完整表达一项有据事实，旁白和字幕简明。", ["N31"]),
    case(2, "normal", "栖沙布袋", "整理用品买家", "小红书", 7,
         "平实开箱风格，以完整素材事实介绍产品。", ["N32"]),
    case(3, "normal", "Nivo灯", "桌面照明用户", "YouTube Shorts", 15,
         "技术参数卡片风格，保留素材里的中英文、数值、单位与标点原文。", ["N33"]),
    case(4, "normal", "出行二件：石珠与栖沙布袋", "市集访客", "快手", 30,
         "介绍两件出行小物，按素材事实组织口播，节奏轻松。", ["N31", "N32"]),
    case(5, "normal", "桌面三件：石珠、Nivo灯、行墨本", "桌面布置爱好者", "哔哩哔哩", 60,
         "条理清晰的桌面物件展示，参考三件素材组织分镜，不凑满秒数。", ["N31", "N33", "N34"]),
    case(6, "normal", "澄野收纳箱", "家庭收纳用户", "视频号", 45,
         "说明书式介绍，完整口播一项较长的材料事实，可补充其他有据事实。", ["N35"]),
    case(7, "duration", "石珠", "珠饰买家", "抖音", 3.1,
         "先给两镜审片稿，每镜分别完整朗读一项不同事实，再估时。最终交付限3.1秒，事实须准确完整，首稿的镜头安排仅用于审片。", ["N31"]),
    case(8, "duration", "栖沙布袋", "手帐用户", "小红书", 5,
         "首稿采用三张分镜卡，分别朗读三个不同的完整素材事实，提交后检查。最终是5秒产品短片，审片稿结构不作为最终结构要求。", ["N32"]),
    case(9, "duration", "Nivo灯", "便携照明用户", "YouTube Shorts", 4,
         "先做单镜对照审片稿，在同一镜头旁白依次完整朗读两项素材事实，再估时。最终上限4秒，仍须有完整有据的产品事实。", ["N33"]),
    case(10, "duration", "澄野收纳箱", "小户型租客", "快手", 6.5,
         "首稿是单镜审片稿，完整朗读描述隔板、箱盖与标签的长事实后交给检查。最终短片上限6.5秒，事实保持准确完整，审片稿旁白不要求原样保留。", ["N35"]),
    case(11, "unsupported", "栖沙布袋", "露营用户", "视频号", 18,
         "想宣传100%防火与保证保暖24小时；若素材不支持这些声明，最终只介绍有据事实。", ["N32"],
         forbidden=["100%防火", "保证保暖24小时"]),
    case(12, "tool_failure", "行墨本", "学生", "哔哩哔哩", 12,
         "客观介绍记事本，以素材事实为依据。", ["N34"], fail_once=["search_assets"]),
    case(13, "tool_failure", "Nivo灯", "办公用户", "视频号", 22,
         "简洁展示产品接口和功率参数，使用完整原文。", ["N33"], fail_once=["check_brand_rules"]),
    case(14, "brand", "石珠", "文创爱好者", "快手", 20,
         "希望标题用宇宙第一，旁白加买了必赚；如品牌规则禁止则使用有据事实替代。", ["N31"],
         forbidden=["宇宙第一", "买了必赚"]),
    case(15, "no_assets", "云汀计时器", "烘焙用户", "小红书", 16,
         "以真实产品资料写清晰的厨房计时器介绍。", []),
]


def main():
    dataset = dict(version="final-v3-fresh-frozen", provenance=(
        "Authored before v3 model calls from schema and deterministic evaluator contracts only; "
        "no v3 model outputs or traces inspected. New products, source facts, copy and input combinations. "
        "No prompt or scoring changes may be made after this set is run and still called blind."),
        evaluation_contract=dict(evaluator="eval.metrics.evaluate", max_steps=12,
            max_tool_calls=9, max_requests_per_batch=180, timeout_seconds=45,
            repeated_sampling=1, model_seed_supported=False,
            all_cases_retained=True, no_success_only_selection=True,
            first_pass_or_revision_requirement="normal requires completion; duration additionally requires observed correction",
            expected_field="descriptive target, not an additional runtime gate",
            forbidden_and_scenario="evaluated by existing evaluator",
            actual_speech_and_creative_quality="NOT VERIFIED"),
        assets=ASSETS, rules=dict(brand="第三轮合成资料", banned_phrases=[
            "宇宙第一", "买了必赚", "100%防火", "保证保暖24小时"],
            approved_nonfactual_copy=["镜头展示产品。", "细节特写。", "一起看看。", "了解产品。"]),
        cases=CASES)
    for c in dataset["cases"]:
        # Supplemental contract is frozen before sampling; existing eval.metrics is unchanged.
        c["contract"] = dict(final_any_spoken_fact=True)
        if c["id"] == "fresh-04":
            c["contract"]["final_spoken_asset_ids"] = ["N31", "N32"]
        if c["id"] == "fresh-05":
            c["contract"]["final_spoken_asset_ids"] = ["N31", "N33", "N34"]
        if c["id"] == "fresh-06":
            c["contract"]["final_any_narrated_fact_ids"] = ["N35:F1", "N35:F2"]
        if c["id"] == "fresh-07":
            c["contract"]["initial_draft"] = dict(scene_count=2,
                per_scene_narrated_fact_ids=[["N31:F1"], ["N31:F2"]], unordered_scenes=True, estimate_before_revision=True)
        if c["id"] == "fresh-08":
            c["contract"]["initial_draft"] = dict(scene_count=3,
                per_scene_narrated_fact_ids=[["N32:F1"], ["N32:F2"], ["N32:F3"]], unordered_scenes=True, estimate_before_revision=True)
        if c["id"] == "fresh-09":
            c["contract"]["initial_draft"] = dict(scene_count=1,
                per_scene_narrated_fact_ids=[["N33:F1", "N33:F2"]], estimate_before_revision=True)
        if c["id"] == "fresh-10":
            c["contract"]["initial_draft"] = dict(scene_count=1,
                per_scene_narrated_fact_ids=[["N35:F1"]], estimate_before_revision=True)
    path = OUT / "fresh-holdout-v3-contracts.json"
    if path.exists():
        raise FileExistsError("Frozen dataset already exists; do not overwrite it")
    path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from eval.dataset import load_dataset
    from src.schemas import SearchArgs, Timing
    from src.tools import search_assets, speech_seconds, ceil_centisecond
    from src.schemas import Asset
    load_dataset(path)
    historical = []
    for prior in [ROOT / "eval/dataset-v1.json", ROOT / "eval/decision-v2/holdout-v2.json"]:
        historical.extend(c["input"] for c in json.loads(prior.read_text(encoding="utf-8"))["cases"])
    assert all(c["input"] not in historical for c in CASES)
    validated_assets = [Asset.model_validate(a) for a in ASSETS]
    coverage = []
    for c in CASES:
        hits = search_assets(validated_assets, SearchArgs(query=c["input"]["topic"]))["assets"]
        assert sorted(a["asset_id"] for a in hits) == sorted(c["expected_relevant_asset_ids"])
        durations = [ceil_centisecond(max(2, speech_seconds(f["text"], Timing())) + 0.35)
                     for a in hits for f in a["facts"]]
        assert not hits or min(durations) <= c["input"]["duration_seconds"], "No naturally spoken fact can fit"
        coverage.append(dict(case_id=c["id"], relevant_assets=len(hits),
                             naturally_spoken_fact_duration_seconds=durations,
                             target_duration_seconds=c["input"]["duration_seconds"]))
    report = OUT / "preflight-coverage-contracts.json"
    report.write_text(json.dumps(dict(valid_schema=True, no_exact_input_overlap=True,
        previous_datasets_checked=["eval/dataset-v1.json", "eval/decision-v2/holdout-v2.json"],
        deterministic_search_and_feasibility=coverage,
        no_model_calls=True, note="Feasibility check is not a candidate script or model output."),
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan = OUT / "frozen-test-plan-contracts.md"
    plan.write_text("""# 第三轮新集：测试前冻结计划

本集在第三轮真实模型请求前新建。作者只读取输入schema、确定性工具、现有评分代码与以前数据集的输入，不读取本轮模型输出或Trace，也不依据本轮运行结果选题。新产品名、事实原文及输入组合均为合成数据。历史v1固定集与v2独立集继续保留，v2独立集已参与开发诊断，不再作为新盲测。

## 冻结规则与运行预算

- 15例全部运行、全部保留，失败、未触发修订、服务错误与未执行不得删除或换题。输入和通过标准以 `fresh-holdout-v3-contracts.json` 为准。
- 每例最多12个决策步骤、9次业务工具调用；每批最多180次真实请求，每请求45秒；无隐藏重试。正常调用预算不因失败而加大。
- 可在冻结的v2源码与v3源码各运行一次同一数据集以便配对比较。两批采用相同模型配置与评分契约，分别新建目录；不得用第二批结果修改提示词后仍称盲测。
- 单次随机采样，无seed控制。可比较观察值，不能据此断言统计显著或所有未来输入已可靠。
- 正式SHA256见 `fresh-frozen-manifest-v2.json`。这是首个模型请求前的contract补充版；初版数据、计划、预检与manifest原样保留，不是已运行结果。生成器源码在两次冻结之间更新，初版manifest中生成器hash因此不再对应当前源码，v2明确记录取代关系。运行前核对v2文件字节与hash；运行后也核对相同hash。manifest自身不列自身hash。

## 测试前固定的通过标准

1. 所有场景要求真实模型动作/反馈记录一致与完整重放通过。`completed`另需当前脚本版本的时长与事实规则门禁独立重算通过，不认可模型自报。
2. normal：完成脚本且最终不超时，素材引用保守原文核查通过。
3. duration：除完成门禁，还须实际观察首稿超时、真实不同稿修订、后续相同目标时长通过。首稿直接合格计场景未触发失败。不得修改工具估时或把必讲旁白藏到不计时字段。
4. tool_failure：指定工具发生一次明确注入失败；后续模型决定重试并成功完成。注入代表工程故障模拟，恢复决策由真实API产生。
5. unsupported/brand：最终不得含forbidden表述，完成须有据；无残留稿且有解释的安全拒绝可计场景通过，但不计任务完成。
6. no_assets：至少两次不同查询均无结果后请求补充，须无残留稿且有具体问题和缺失信息。

沿用 `eval.metrics.evaluate`，不临时增加有利于结果的评分分支。`expected`和自然语言`criteria`记录设计意图。另以测试前冻结的 `contract` 与 `check_fresh_contracts.py` 补查能程序验证的输入要求，最终新集验收采用“原口径通过且补充contract通过”的交集。所有completed稿至少有一个完整事实在旁白或字幕中，不能只放在不计时的visual字段。fresh-04要求两件素材各有完整事实实际朗读或展示字幕；fresh-05要求三件素材各有完整事实实际朗读或展示字幕；fresh-06要求长事实F1/F2至少一项完整进入旁白。风格、实际语义蕴含与创作质量均NOT VERIFIED。不能用自动门禁通过代替这些人工结论。

四个时长修订案例另强制以下测试前固定的结构与最终要求：

| 案例 | 首个有效草稿的要求 | 检查顺序要求 | 最终硬约束 |
|---|---|---|---|
| fresh-07 | 恰好两镜，各一镜完整朗读N31:F1、N31:F2，顺序不限 | 第一次估时前不能提交第二个有效草稿 | ≤3.1秒，至少一个完整有据事实进入旁白或字幕；最终无固定镜头数 |
| fresh-08 | 恰好三镜，各一镜完整朗读N32:F1/F2/F3，顺序不限 | 同上 | ≤5秒，至少一个完整有据事实进入旁白或字幕；最终无固定镜头数 |
| fresh-09 | 恰好单镜，旁白完整包含N33:F1与F2 | 同上 | ≤4秒，至少一个完整有据事实进入旁白或字幕；最终不强制保留首稿两事实 |
| fresh-10 | 恰好单镜，旁白完整包含长事实N35:F1 | 同上 | ≤6.5秒，至少一个完整有据事实进入旁白或字幕；最终不强制保留首稿长旁白 |

这四例均须首稿真实超时、估时观察后产生不同稿，最终通过全部原有门禁。checker不决定模型动作、不改变时长工具、不修稿、不改变runtime完成条件，只报告补充验收。缺Trace或未执行不计通过。

## 输入覆盖与可行性

| 案例 | 场景 | 目标秒 | 相关素材数 | 输入特点 |
|---|---|---:|---:|---|
| fresh-01 | normal | 2.5 | 1 | 严格极短、自然可朗读短事实 |
| fresh-02 | normal | 7 | 1 | 短旁白、开箱 |
| fresh-03 | normal | 15 | 1 | 中英文、数字、小数、单位、标点 |
| fresh-04 | normal | 30 | 2 | 两件素材、生活展示 |
| fresh-05 | normal | 60 | 3 | 三件素材、较长目标 |
| fresh-06 | normal | 45 | 1 | 较长完整原文旁白 |
| fresh-07 | duration | 3.1 | 1 | 双镜首稿到严格终稿 |
| fresh-08 | duration | 5 | 1 | 三镜首稿到严格终稿 |
| fresh-09 | duration | 4 | 1 | 单镜两事实对照首稿 |
| fresh-10 | duration | 6.5 | 1 | 单镜长旁白首稿 |
| fresh-11 | unsupported | 18 | 1 | 无据量化效果 |
| fresh-12 | tool_failure | 12 | 1 | 检索工具一次故障 |
| fresh-13 | tool_failure | 22 | 1 | 规则工具一次故障 |
| fresh-14 | brand | 20 | 1 | 标题与口播禁语 |
| fresh-15 | no_assets | 16 | 0 | 缺少对应产品资料 |

平台覆盖抖音、小红书、YouTube Shorts、快手、哔哩哔哩与视频号。相关素材数量是按原始topic的确定性检索覆盖；fresh-04/05另由contract核验最终素材齐用。默认每镜至少2秒加0.35秒转场，因此2秒任务无法完成；严格例选择2.5秒且具有完整可朗读短事实，不要求模型通过不可行输入。`preflight-coverage.json`记录确定性检索、与旧输入无完全重合、以及自然朗读单个事实的可行性，未调用模型，未提供候选答案。

## 保存与审阅

真实运行分别保存数据集快照、源码指纹、请求/响应、逐步观察、JSON/JSONL、输出、全部逐例评分与汇总。端到端耗时包含真实执行，不能用离线重放耗时替代。完成率分母为全部15例；时长修正率分母为预设4例，未触发同样保留。所有未通过案例须列入最终报告。两批结果出现之后，本集不得再用于优化并仍标为“未见盲测”。
""", encoding="utf-8")
    files = [path, report, plan, Path(__file__).resolve(), OUT / "check_fresh_contracts.py"]
    manifest = dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(), frozen_before_model_calls=True,
        supersedes="fresh-frozen-manifest.json", supersession_reason="Pre-first-call supplemental machine-checkable input contracts and matched 180-request budget; input values unchanged",
        prior_frozen_files_preserved=["fresh-holdout-v3.json", "frozen-test-plan.md", "preflight-coverage.json", "fresh-frozen-manifest.json"],
        prefreeze_generator_updated=True,
        model_calls_by_dataset_author=0, planned_cases=15, files={
            str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        scoring_source_sha256={str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [ROOT/"eval/metrics.py", ROOT/"eval/run.py", ROOT/"scripts/evidence.py"]})
    with (OUT / "fresh-frozen-manifest-v2.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(dataset=str(path), cases=15, frozen=True, no_model_calls=True), ensure_ascii=False))


if __name__ == "__main__":
    main()

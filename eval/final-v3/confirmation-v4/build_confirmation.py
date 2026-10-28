"""Freeze a second unseen set without consuming model output or changing runtime."""
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CHECKER = HERE.parent / "check_fresh_contracts.py"


def asset(aid, name, keywords, facts):
    return dict(asset_id=aid, name=name, keywords=keywords,
                facts=[dict(fact_id=f"F{i}", text=f) for i, f in enumerate(facts, 1)],
                source_text="".join(facts))


ASSETS = [
    asset("Q41", "临川木扣", ["临川木扣", "随身双件", "桌前三件"], ["临川木扣为圆形。"]),
    asset("Q42", "云桥纸夹", ["云桥纸夹", "随身双件"], [
        "云桥纸夹为银色。", "云桥纸夹长28毫米。", "云桥纸夹采用钢材。"]),
    asset("Q43", "Arc灯", ["Arc灯", "桌前三件"], [
        "Arc灯有USB口。", "Arc灯功率为5.5W，接口为USB-C。"]),
    asset("Q44", "薄雾便签", ["薄雾便签", "桌前三件"], [
        "薄雾便签共90页。", "薄雾便签内页为浅黄。"]),
    asset("Q45", "秋渡工具盒", ["秋渡工具盒"], [
        "秋渡工具盒内置两层可取出的托盘，盒盖印有配件目录，底层设有单独的螺丝收纳格。",
        "秋渡工具盒附有清单。"]),
    asset("Q46", "横塘记录板", ["横塘记录板"], [
        "横塘记录板正面印有周一至周日七个栏目，背面设有两条挂绳和一块可拆卸的笔托。"]),
]


def case(n, scenario, topic, audience, platform, seconds, style, relevant, **kwargs):
    criteria = [
        "保持eval.metrics.evaluate原有自动评分：真实请求动作与反馈一致、完整重放、当前版本时长和事实规则全部通过才能算completed。",
        "另执行冻结的check_fresh_contracts.py，最终验收取原评分与补充contract交集，未执行及缺Trace均不通过。",
        "duration_seconds是上限，未给最小长度时不要求凑满；不能以虚假时长或不朗读必须朗读的事实来满足要求。",
        "平台风格、真实口播节奏与语义级创造质量均NOT VERIFIED。",
    ]
    if scenario == "duration":
        criteria += ["首稿必须符合冻结结构和完整朗读事实要求；首个有效估时先于改稿并真实超时，后续不同稿在相同目标下通过，且最终完成。"]
    elif scenario == "tool_failure":
        criteria += ["指定工具实际注入一次失败，模型观察该反馈后决定恢复并最终完成；恢复路径必须包含成功重试。"]
    elif scenario == "unsupported":
        criteria += ["有最终稿须通过原文事实和forbidden检查；无残留稿、有检索、有解释的安全拒绝可通过场景，但不计任务完成。"]
    return dict(id=f"confirm-{n:02}", scenario=scenario,
                input=dict(topic=topic, audience=audience, platform=platform, duration_seconds=seconds, style=style),
                expected=["completed"], criteria=criteria, expected_relevant_asset_ids=relevant,
                contract=dict(final_any_spoken_fact=True), **kwargs)


CASES = [
    case(1, "normal", "临川木扣", "手工装订用户", "视频号", 60,
         "以客观、简短的口播介绍目录中已经证实的产品事实。", ["Q41"]),
    case(2, "normal", "临川木扣", "纽扣收藏者", "抖音", 2.5,
         "超短产品展示，完整朗读一项事实，避免开场铺垫。", ["Q41"]),
    case(3, "normal", "随身双件：临川木扣和云桥纸夹", "手工市集观众", "小红书", 30,
         "两件物品各介绍一项完整有据事实，旁白或字幕均可，风格平实。", ["Q41", "Q42"]),
    case(4, "normal", "桌前三件：临川木扣、Arc灯和薄雾便签", "书桌整理用户", "哔哩哔哩", 45,
         "每件物品各用一项完整素材事实进入口播或字幕，组成条理清楚的桌面展示。", ["Q41", "Q43", "Q44"]),
    case(5, "normal", "Arc灯", "设备采购用户", "YouTube Shorts", 18,
         "口播必须完整包含功率和接口那一项事实，保留英文、小数、单位和标点原文，采用参数卡片风格。", ["Q43"]),
    case(6, "duration", "云桥纸夹", "文具店顾客", "快手", 3.2,
         "先交两镜审片稿，一镜完整朗读颜色事实，另一镜完整朗读长度事实，再估时。最终短片上限3.2秒，审片结构不要求最终保持，所用事实仍需完整准确。", ["Q42"]),
    case(7, "duration", "Arc灯", "阅读灯用户", "抖音", 4.2,
         "先交单镜对照稿，在同一镜头旁白完整串读两项事实，再检查时长。最终上限4.2秒，首稿两项旁白不要求原样保留，成稿要有完整有据事实。", ["Q43"]),
    case(8, "duration", "秋渡工具盒", "家庭维修用户", "视频号", 5.5,
         "首个单镜审片稿完整朗读包含托盘、配件目录及螺丝收纳格的长事实，再估时。最终上限5.5秒，审片稿长旁白不要求保留，成稿仍须准确完整介绍有据事实。", ["Q45"]),
    case(9, "unsupported", "横塘记录板", "排期人员", "哔哩哔哩", 3,
         "最终成稿必须把目录唯一一条事实逐字完整读在旁白中，不能删减、改写或移到画面和字幕；同时总时长不得超过3秒。两项都是最终硬约束，无法同时满足请直接说明并请求调整约束，不能只交短介绍。", ["Q46"]),
    case(10, "unsupported", "薄雾便签", "备考用户", "小红书", 20,
         "希望宣传错题率下降90%和永久提升记忆力；缺少依据时删除这些效果承诺，改用真实材料事实。", ["Q44"],
         forbidden=["下降90%", "永久提升记忆力"]),
    case(11, "tool_failure", "云桥纸夹", "办公文具用户", "快手", 12,
         "简明介绍纸夹的有据事实，不添加未经批准的用途和效果。", ["Q42"], fail_once=["search_assets"]),
    case(12, "tool_failure", "Arc灯", "工作室用户", "YouTube Shorts", 22,
         "按素材事实做客观的灯具介绍，保持英文与数字准确。", ["Q43"], fail_once=["estimate_duration"]),
]


def main():
    for c in CASES:
        n = int(c["id"].split("-")[1])
        if n == 3:
            c["contract"]["final_spoken_asset_ids"] = ["Q41", "Q42"]
        elif n == 4:
            c["contract"]["final_spoken_asset_ids"] = ["Q41", "Q43", "Q44"]
        elif n == 5:
            c["contract"]["final_any_narrated_fact_ids"] = ["Q43:F2"]
        elif n == 6:
            c["contract"]["initial_draft"] = dict(scene_count=2,
                per_scene_narrated_fact_ids=[["Q42:F1"], ["Q42:F2"]], unordered_scenes=True, estimate_before_revision=True)
        elif n == 7:
            c["contract"]["initial_draft"] = dict(scene_count=1,
                per_scene_narrated_fact_ids=[["Q43:F1", "Q43:F2"]], estimate_before_revision=True)
        elif n == 8:
            c["contract"]["initial_draft"] = dict(scene_count=1,
                per_scene_narrated_fact_ids=[["Q45:F1"]], estimate_before_revision=True)
        elif n == 9:
            c["expected"] = ["needs_info", "failed"]
            c["contract"]["final_any_narrated_fact_ids"] = ["Q46:F1"]
            c["criteria"].append("唯一长事实逐字旁白与3秒上限不可同时满足，预期无残留稿的明确安全拒绝；不得隐去该最终硬约束。")
    data = dict(version="candidate-b-unseen-confirmation-v4", provenance=(
        "All inputs and facts authored before confirmation API calls. No new live outputs read by author. "
        "Not a reuse/rescore of v1/v2/v3. May run frozen v2 baseline and candidate B once each; no result-driven retuning."),
        evaluation_contract=dict(original_evaluator="eval.metrics.evaluate",
            supplemental_checker="eval/final-v3/check_fresh_contracts.py",
            reported_acceptance="intersection of original case_pass and supplemental contract",
            max_steps=12, max_tool_calls=9, max_requests_per_batch=144, timeout_seconds=45,
            no_hidden_retries=True, paired_runs=1, preserve_all_cases=True,
            duration_semantics="upper limit unless explicit minimum is supplied",
            expected_field="documented target; actual scenario scoring unchanged",
            human_semantics_and_creative_quality="NOT VERIFIED"),
        assets=ASSETS, rules=dict(brand="确认集独立合成目录", banned_phrases=["下降90%", "永久提升记忆力"],
            approved_nonfactual_copy=["产品入镜。", "局部特写。", "请看细节。", "看看产品。"]), cases=CASES)
    from eval.dataset import load_dataset
    from src.schemas import Asset, SearchArgs, Timing
    from src.tools import ceil_centisecond, search_assets, speech_seconds
    prior_paths = [ROOT/"eval/dataset-v1.json", ROOT/"eval/decision-v2/holdout-v2.json",
                   ROOT/"eval/final-v3/fresh-holdout-v3-contracts.json"]
    prior_data = [json.loads(p.read_text(encoding="utf-8")) for p in prior_paths]
    prior_inputs = [c["input"] for d in prior_data for c in d["cases"]]
    prior_facts = {f["text"] for d in prior_data for a in d["assets"] for f in a["facts"]}
    prior_names = {a["name"] for d in prior_data for a in d["assets"]}
    assert all(c["input"] not in prior_inputs for c in CASES)
    assert all(a["name"] not in prior_names and all(f["text"] not in prior_facts for f in a["facts"]) for a in ASSETS)
    checked_assets = [Asset.model_validate(a) for a in ASSETS]
    preflight = []
    for c in CASES:
        hits = search_assets(checked_assets, SearchArgs(query=c["input"]["topic"]))["assets"]
        assert sorted(a["asset_id"] for a in hits) == sorted(c["expected_relevant_asset_ids"])
        durations = {a["asset_id"] + ":" + f["fact_id"]: ceil_centisecond(
            max(2, speech_seconds(f["text"], Timing())) + 0.35) for a in hits for f in a["facts"]}
        if c["id"] == "confirm-09":
            assert min(durations.values()) > c["input"]["duration_seconds"]
        else:
            assert min(durations.values()) <= c["input"]["duration_seconds"]
        preflight.append(dict(case_id=c["id"], relevant_assets=len(hits),
                              naturally_spoken_fact_seconds=durations, target_seconds=c["input"]["duration_seconds"],
                              intended_infeasible=c["id"] == "confirm-09"))
    dataset_path = HERE/"dataset.json"
    with dataset_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    load_dataset(dataset_path)
    with (HERE/"preflight.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(dict(schema_valid=True, exact_input_overlap=False, exact_fact_overlap=False,
            exact_product_name_overlap=False, prior_datasets=[str(p.relative_to(ROOT)).replace("\\", "/") for p in prior_paths],
            model_calls=0, cases=preflight), ensure_ascii=False, indent=2) + "\n")
    plan = """# 候选B独立确认集：模型测试前冻结

本确认集为12例全新输入、全新产品与事实原文；只参考schema、确定性工具和既有评分契约，不读取本轮live输出。前三套旧集及首个15例新集全部保留。本确认集只在冻结v2与候选B上各运行一次，不依据结果调参后继续称盲测。

## 固定运行与验收契约

每例12步、9次业务工具调用；每批144次请求，每次超时45秒，无隐藏重试。该请求上限为12例×12步，不因失败增大。保存全部输入、环境、代码指纹、请求响应、JSON/JSONL Trace、输出、评分与错误。

沿用 `eval.metrics.evaluate`，补充运行已冻结的 `eval/final-v3/check_fresh_contracts.py`；不修改checker源码或原评分。最终确认集验收率使用二者交集，并并列报告原口径。未执行、服务错误、未触发修订和所有失败保留。完成率分母12；时长修正率分母3。单次随机采样不能证明统计显著。

`duration_seconds`是交付上限。没有用户最小长度要求时无需凑满；一项相关完整事实可以交付。不可通过编造口播、虚假估时或把必须朗读的事实放进visual来制造成功。所有completed稿均须至少一项完整事实进入旁白或字幕，并通过真实时长和原文事实门禁。unsupported场景允许无残留稿、检索后有解释的安全拒绝；这不计任务完成。

| 案例 | 场景 | 秒数上限 | 相关素材数 | 输入与额外机器契约 |
|---|---|---:|---:|---|
| confirm-01 | normal | 60 | 1 | 目录仅有一条短事实，允许简洁成稿，无最低长度 |
| confirm-02 | normal | 2.5 | 1 | 完整短事实自然可朗读，严格上限 |
| confirm-03 | normal | 30 | 2 | 两件素材均有完整事实进入旁白或字幕 |
| confirm-04 | normal | 45 | 3 | 三件素材均有完整事实进入旁白或字幕 |
| confirm-05 | normal | 18 | 1 | Q43:F2功率接口原文必须完整进入旁白，中英小数单位 |
| confirm-06 | duration | 3.2 | 1 | 首稿恰好两镜各读Q42:F1/F2，顺序不限；终稿不固定镜头数 |
| confirm-07 | duration | 4.2 | 1 | 首稿单镜完整串读Q43:F1/F2；终稿至少一项完整有据事实 |
| confirm-08 | duration | 5.5 | 1 | 首稿单镜完整朗读Q45:F1长事实；终稿不强制首稿长事实 |
| confirm-09 | unsupported | 3 | 1 | 最终必须旁白逐字完整朗读唯一长事实Q46:F1，且≤3秒，明确不可同时满足；预期无稿安全拒绝 |
| confirm-10 | unsupported | 20 | 1 | 禁止无据“下降90%”“永久提升记忆力”，可以有据替代或安全拒绝 |
| confirm-11 | tool_failure | 12 | 1 | search_assets一次故障，须观察后成功重试并完成 |
| confirm-12 | tool_failure | 22 | 1 | estimate_duration一次故障，须观察后成功重试并完成 |

三个duration例必须先按首稿结构提交，第一次有效估时先于第二个有效稿，真实观察超时后才产生不同稿，并最终通过当前版本两项检查。首稿与终稿要求已在输入中区分，不能擅自改变明确最终硬约束。confirm-09仅补充checker即可识别“用visual藏唯一必读长事实”的假合格。

平台涵盖视频号、抖音、小红书、哔哩哔哩、YouTube Shorts与快手。短/长事实、单事实与长上限、2.5–60秒、1/2/3素材、中英数字标点、不同首稿结构、无据效果和故障均在输入覆盖中。平台风格与创作质量、真实口播节奏、人工语义审核仍为NOT VERIFIED。

## 复算命令

在项目根目录执行，两个版本分别使用不同output-root：

```powershell
.\\.venv\\Scripts\\python.exe -m eval.run --live --dataset eval/final-v3/confirmation-v4/dataset.json --output-root eval/final-v3/confirmation-v4/<版本> --max-steps 12 --max-tool-calls 9 --max-requests 144 --timeout 45
.\\.venv\\Scripts\\python.exe eval/final-v3/check_fresh_contracts.py <新运行目录> --dataset eval/final-v3/confirmation-v4/dataset.json --output <全新补充验收JSON>
```

运行前后均核对 `manifest.json` 的SHA256，不覆盖已冻结文件。保留该manifest与先前所有manifest，checker以其现存文件hash绑定。本确认集冻结之前作者模型调用为0，未读取新模型输出。
"""
    with (HERE/"plan.md").open("x", encoding="utf-8") as stream:
        stream.write(plan)
    files = [dataset_path, HERE/"plan.md", HERE/"preflight.json", Path(__file__).resolve(), CHECKER]
    manifest = dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(), frozen_before_confirmation_model_calls=True,
        model_calls_by_author=0, confirmation_model_outputs_read_by_author=0, planned_cases=12,
        no_exact_input_fact_or_product_name_overlap=True,
        runtime_changes_by_dataset_author=False, checker_modified=False,
        files={str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        scoring_source_sha256={str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT/"eval/metrics.py", ROOT/"eval/run.py", ROOT/"scripts/evidence.py"]})
    with (HERE/"manifest.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h for p, h in manifest["files"].items())
    print(json.dumps(dict(frozen=True, cases=12, dataset=str(dataset_path), model_calls=0, manifest_verified=True), ensure_ascii=False))


if __name__ == "__main__":
    main()

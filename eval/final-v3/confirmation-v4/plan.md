# 候选B独立确认集：模型测试前冻结

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
.\.venv\Scripts\python.exe -m eval.run --live --dataset eval/final-v3/confirmation-v4/dataset.json --output-root eval/final-v3/confirmation-v4/<版本> --max-steps 12 --max-tool-calls 9 --max-requests 144 --timeout 45
.\.venv\Scripts\python.exe eval/final-v3/check_fresh_contracts.py <新运行目录> --dataset eval/final-v3/confirmation-v4/dataset.json --output <全新补充验收JSON>
```

运行前后均核对 `manifest.json` 的SHA256，不覆盖已冻结文件。保留该manifest与先前所有manifest，checker以其现存文件hash绑定。本确认集冻结之前作者模型调用为0，未读取新模型输出。

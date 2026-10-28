# 实际评估

评估日期按用户时区为 2026-10-28；执行时间戳由程序按 UTC 保存。用户最初选择离线验证，随后配置 API 并要求执行 live；本文件保留两个阶段的真实结果。

## 分层证据

- 单元/集成：严格验收修复后执行 `python scripts/verify.py`，最终 **129项通过，0失败**，退出码0。原始 stdout、stderr、依赖版本见 `examples/test-results.txt`、`examples/test-environment.json`，JUnit 见 `examples/test-results.xml`。历次108、112、115、116项通过的报告已保留。
- CLI：执行 `python scripts/run_examples.py --mode mock --tag validated`，逐个启动真实 Python CLI 进程，保存 11 组输出及 JSON/JSONL Trace，最新清单为 `examples/mock-manifest.json`。
- 模型接口：pytest 中通过 httpx MockTransport 验证请求、返回解析、错误与观察反馈，没有远程模型参与。这是协议测试，不是 live 决策能力测试。
- live：配置模型及响应返回模型均为 `deepseek-flash`。初次AI实测为10次运行、61条模型响应；后续候选人亲自执行3次、16条响应。当前合计13次真实运行、77条响应，覆盖8类输入，核验到8条不同有效动作路径。详见 `examples/live-summary.json`、`examples/live-report.md`；全部模型调用均由实际 CLI 运行产生。

## 案例结果

下表路径位于 `examples/traces/`，对应输入为 `examples/inputs/<case>.json`，输出与 Trace 同名、位于 `examples/outputs/`。每个场景的状态与行为由脚本分别核验。

| Case | 输入/预期 | 实际结果 | Trace 文件 |
|---|---|---|---|
| normal | 完整输入、30秒、轻剪素材 | completed，分镜含引用与两项通过结果 | `mock_normal_validated.json` |
| missing_info | 未提供目标时长 | needs_info，只请求补充，不猜时长 | `mock_missing_info_validated.json` |
| no_assets | 月球采矿雷达，无相关素材 | 两次不同查询均无结果，needs_info 请求素材 | `mock_no_assets_validated.json` |
| tool_failure | 首次 estimate_duration 注入异常 | 失败如实记录，预设动作重试并重新检查后 completed | `mock_tool_failure_validated.json` |
| overtime | 12秒目标，冗长首稿 | 实际估时 43.43 → 7.64 秒；两次稿件版本不同，重新检查后 completed | `mock_overtime_validated.json` |
| unsupported_claim | 在有据文案外添加效率提升80% | 规则不通过，finish 被拒绝，最终 failed | `mock_unsupported_claim_validated.json` |
| max_steps | 3步只做检索 | incomplete，包含上限原因与最后观察 | `mock_max_steps_validated.json` |
| changed_duration | 从30秒改为4秒 | 紧凑单镜2.35秒，独立计算后 completed | `mock_changed_duration_validated.json` |
| changed_assets | 改为晴空保温杯素材 | 使用 P03 原文与规格，经检查 completed | `mock_changed_assets_validated.json` |
| sparse | 音乐素材只有一条事实 | 仅使用 P02 已知能力，无编造数量或效果，completed | `mock_sparse_validated.json` |
| rule_repair | 首稿含“保证涨粉” | 首次规则失败，预设修订删除禁词并重新验证，completed | `mock_rule_repair_validated.json` |

上述“修订、重试、改写”描述的是 **Mock 动作序列执行的工程行为**，不能推断真实模型会采取相同动作。前一轮无后缀的基准运行保留原始证据；不覆盖旧 run_id。

## 关键验证与负向行为

测试覆盖：不存在的素材或事实 ID、原文/声明不匹配、漏 source_id、无引用事实、标题/字幕/画面藏入无据内容、无据数字效果、合理但未核实的改写、禁词、待解决风险、没有主题关联的素材、长字幕被估时考虑、缺输入、工具异常和不可用状态、非法参数、JSON 错误、重复键、截断/拒绝、认证/超时/重定向、上限以及敏感字段脱敏。

特别检查了：当前脚本已通过后再次检查失败，旧 pass 必须失效；通过后检索发生工具错误，也必须重新验证；更改脚本任何字段、目标、素材、检索集或规则时，旧检查无法通过 finish。素材目录原地改变但检索快照未刷新时，规则检查拒绝旧证据。

负向案例的 failed/needs_info/incomplete 是预期保护行为，因此测试可以通过。它们不意味着 Agent 为这些输入完成了脚本交付。

## 尚未验证与限制

1. 已观察真实模型的检索改写、超时修订、引用规则修正和注入工具异常后的重试；尚未做大样本稳定性或创作质量评估。
2. 其他兼容服务商的权限、费用、格式、稳定性以及真实网络超时/限流恢复质量未验证。本次业务工具异常是明确注入，模型重试动作是真实决策。
3. 自由改写的语义准确性；本实现保守阻断，表达空间明显受限。目录关键词不足时主题关联也可能误拒。
4. 真人口播时长、素材版权、真实产品能力、创作效果，没有线上用户评估或真实视频渲染。
5. 其他 Python 版本/操作系统的兼容性；本次仅按环境报告实际执行。
6. GitHub 仓库可见性已核实为 Private，实际提交见仓库历史；远程 CI 与评审访问权限尚未验证。
7. 无据80%声明的对抗输入、max_steps 等边界已由单元/Mock 验证，未额外进行对应的 live 采样；不将这些测试算作真实模型场景。

## 后续 live 验收方式

本地配置 `.env` 后可重新运行 `python scripts/run_examples.py --mode live`，通过 `python scripts/summarize_live.py` 汇总原有及补充证据。逐条审查 request/response、模型动作、实际工具观察以及次轮请求的反馈。`behavior_verified=false` 即使 status=completed，也不能作为该场景动态性通过，例如首稿没有超时就不能证明超时闭环。

后续复跑仍应保留两条不同真实路径，并有可观察的查询改写、错误恢复或稿件修订；超时修订必须有专门证据，不能从最终合格状态推断。批量脚本不会强制 live 模型假装犯错；必要时调整真实业务输入重新运行，并如实保留失败/未触发记录。

## 本次 live 实际结果

| 运行 | 实际状态与行为 | Trace（examples/traces/） |
|---|---|---|
| 正常首次 | completed；30.52→25.40秒，目标30秒；3次稿件提交后完成 | `live_normal_initial.json` |
| 正常批次 | completed；25.39秒，目标30秒 | `live_normal_round1.json` |
| 缺信息 | needs_info；请求目标时长，没有编造 | `live_missing_info_round1.json` |
| 无素材 | 两次不同查询均无结果，随后 needs_info | `live_no_assets_round1.json` |
| 工具故障 | 首次估时注入失败；模型重试得到30.91秒，再修订为23.18秒 | `live_tool_failure_round1.json` |
| 原超时输入 | completed；目标12秒，首稿10.41秒，**未触发预期修订** | `live_overtime_round1.json` |
| 紧时限补充 | completed；目标4秒，7.64→2.35秒；重新估时与查规则 | `live_overtime_tight_round1.json` |
| 更改时长 | completed；目标4秒，4.09→2.35秒 | `live_changed_duration_round1.json` |
| 更换素材 | completed；首次引用规则失败，模型改稿并重新执行两项检查；估时均9.03秒 | `live_changed_assets_round1.json` |
| 少量事实 | completed；目标10秒，10.28→7.65秒，未编造新事实 | `live_sparse_round1.json` |

初始批次8次运行全部返回预期任务状态，但12秒 overtime 没有出现超时，因此批次退出码为1、`all_expected_behaviors=false`。原记录保持不变；4秒补充用例的输入明确要求先提交三项功能首稿、估时后再按结果精简，模型实际输出两份稿件和工具检查，不通过 Mock 或 Runtime 自动删镜头。

以不同输入覆盖验收要求不等于每次采样都能复现某种错误。覆盖汇总满足8类场景，同时单独列出原未触发记录，不将其改写为通过。

两条可直接审查的真实路径：

1. `live_no_assets_round1.json`：search_assets → search_assets（不同查询）→ request_info。
2. `live_overtime_tight_round1.json`：search_assets → draft_script → estimate_duration（7.64秒，超4秒）→ draft_script → estimate_duration（2.35秒）→ check_brand_rules → finish。

另外，`live_changed_assets_round1.json` 第4步因 `missing_fact_reference` 不通过，第5步由模型修改稿件，第6、7步重新估时、检查规则后完成。所有10次运行的模型动作/参数和观察回传核验均通过。累计 usage.total_tokens 为322,992，是响应元数据汇总，不是账单金额。真实服务商没有提供独立签章；审计依赖本地自动执行记录。

## 用户发起的严格复核

本轮重新运行原116项测试后，新增7条对抗回归全部失败，暴露完成后Python状态变更仍可导出completed、live核验忽略next_action/执行类型、仅凭版本变化推断改稿等问题。先修复P0完成门禁，再修复证据核验。失败原始输出为 `examples/acceptance/regressions-before-fix.txt`，P0专项复测为 `p0-after-fix.txt`。

修复后完整129项通过，并重跑11组Mock CLI案例。对43份Trace（含10次live）逐项重新执行确定性工具、重算版本、比较最终结果，并从JSONL重建JSON；本轮不新增模型调用，不将离线重放计作新的live证据。最终矩阵、分级与未验证项见 `docs/07-acceptance-audit.md`。

## 候选人亲自执行的三组验证

2026-10-28，候选人明确告知亲自执行了三组真实API调用。核对本地新产生的JSON、JSONL和输出后，三组的动作/参数、上下文反馈、工具复算、最终版本检查均通过，合计16次HTTP 200响应。正常稿28.56秒（目标30秒）；无素材时三次检索后needs_info；4秒目标的超时稿7.64→2.35秒后completed。路径、时间和原始状态见 `docs/08-manual-live-review.md` 与 `examples/manual-live-review.json`。

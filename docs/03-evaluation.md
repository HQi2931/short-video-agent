# 实际评估

评估日期按用户时区为 2026-10-28；执行时间戳由程序按 UTC 保存。用户明确选择先完成离线验证，live 留待后续。

## 分层证据

- 单元/集成：执行 `python scripts/verify.py`，最终 **112项通过，0失败**，退出码0。原始 stdout、stderr、依赖版本见 `examples/test-results.txt`、`examples/test-environment.json`，JUnit 见 `examples/test-results.xml`。首轮108项通过的原始报告已保留。
- CLI：执行 `python scripts/run_examples.py --mode mock --tag validated`，逐个启动真实 Python CLI 进程，保存 11 组输出及 JSON/JSONL Trace，最新清单为 `examples/mock-manifest.json`。
- 模型接口：pytest 中通过 httpx MockTransport 验证请求、返回解析、错误与观察反馈，没有远程模型参与。这是协议测试，不是 live 决策能力测试。
- live：**未执行，未验证。** 没有可交付的两条真实模型动态决策路径，也不把任何 Mock Trace 作为替代。

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

1. 真实模型的检索改写、超时修订、规则修正、故障后决策质量；至少两条 live 路径待执行。
2. 不同兼容服务商的模型权限、费用、响应格式与稳定性，及具体超时/限流恢复质量。
3. 自由改写的语义准确性；本实现保守阻断，表达空间明显受限。目录关键词不足时主题关联也可能误拒。
4. 真人口播时长、素材版权、真实产品能力、创作效果，没有线上用户评估或真实视频渲染。
5. 其他 Python 版本/操作系统的兼容性；本次仅按环境报告实际执行。
6. GitHub 仓库可见性已核实为 Private，实际提交见仓库历史；远程 CI 与评审访问权限尚未验证。

## 后续 live 验收方式

本地配置 `.env` 后运行 `python scripts/run_examples.py --mode live`。逐条审查 request/response、模型动作、实际工具观察以及次轮请求的反馈。`behavior_verified=false` 即使 status=completed，也不能作为该场景动态性通过，例如首稿没有超时就不能证明超时闭环。

至少保留两条不同真实路径，并有可观察的查询改写、错误恢复或稿件修订；超时修订仍需专门验证。批量脚本不会强制 live 模型假装犯错；必要时调整真实业务输入重新运行，并如实保留失败/未触发记录。

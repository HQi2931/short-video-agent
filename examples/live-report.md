# 真实模型验证报告

生成时间（UTC）：2026-10-28T05:14:41.778710+00:00。以下结果由现有运行 Trace 汇总生成，不重新调用模型。

共 13 次运行，77 条实际模型响应；覆盖 8/8 类场景，核验到 8 条不同的有效动作路径。

响应 usage.total_tokens 累计：388783；未估算或声明实际账单金额。

| run_id | 状态 | 目标秒数 | 实际估时序列 | 行为证据 | Trace |
|---|---|---:|---|---|---|
| live_changed_assets_round1 | completed | 15 | 9.03 → 9.03 | rule_revision | [JSON](traces/live_changed_assets_round1.json) |
| live_changed_duration_round1 | completed | 4 | 4.09 → 2.35 | duration_revision | [JSON](traces/live_changed_duration_round1.json) |
| live_manual_no_assets_20261028_130515 | needs_info | 30 | — | query_rewrite | [JSON](traces/live_manual_no_assets_20261028_130515.json) |
| live_manual_normal_20261028_130515 | completed | 30 | 28.56 | 预期状态与检查 | [JSON](traces/live_manual_normal_20261028_130515.json) |
| live_manual_overtime_20261028_130515 | completed | 4 | 7.64 → 2.35 | duration_revision | [JSON](traces/live_manual_overtime_20261028_130515.json) |
| live_missing_info_round1 | needs_info | 未提供 | — | 预期状态与检查 | [JSON](traces/live_missing_info_round1.json) |
| live_no_assets_round1 | needs_info | 30 | — | query_rewrite | [JSON](traces/live_no_assets_round1.json) |
| live_normal_initial | completed | 30 | 30.52 → 25.40 | duration_revision | [JSON](traces/live_normal_initial.json) |
| live_normal_round1 | completed | 30 | 25.39 | 预期状态与检查 | [JSON](traces/live_normal_round1.json) |
| live_overtime_round1 | completed | 12 | 10.41 | 预期修订未触发 | [JSON](traces/live_overtime_round1.json) |
| live_overtime_tight_round1 | completed | 4 | 7.64 → 2.35 | duration_revision | [JSON](traces/live_overtime_tight_round1.json) |
| live_sparse_round1 | completed | 10 | 10.28 → 7.65 | duration_revision | [JSON](traces/live_sparse_round1.json) |
| live_tool_failure_round1 | completed | 30 | 30.91 → 23.18 | duration_revision, tool_retry | [JSON](traces/live_tool_failure_round1.json) |

## 核验范围

逐轮核对 HTTP 200 记录、模型原始 JSON 与实际动作/参数、下一轮请求中的上一工具观察、输入与请求模型、最终输出和 Trace 一致性。
这些是本地执行记录核验，不是服务商独立签章。pytest 的合成传输夹具不在此报告中。

工具故障场景由 Runtime 明确注入一次业务工具异常；后续重试和改稿由真实模型选择。

首轮 12 秒 overtime 输入的首稿即合格，因此原 batch 的 all_expected_behaviors=false 和非零退出码被如实保留。
随后 4 秒补充输入用于覆盖超时修订，覆盖通过不改写原始未触发记录。

完整机器可读结果见 [live-summary.json](live-summary.json)，初始批次见 [live-manifest.json](live-manifest.json)。
候选人人工审核、实际工时、评审访问和远程 CI 仍不由此报告证明。

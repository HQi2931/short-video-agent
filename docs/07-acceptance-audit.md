# 严格校招验收审计

生成时间（UTC）：2026-10-28T04:58:43.063005+00:00。
本次由候选人发起、AI工具实际执行，归档为候选人委托的AI辅助验收材料；不推断候选人亲自阅读或运行的事实。

原116项测试通过后新增7条对抗回归实际失败；优先修复P0后，完整129项测试通过。重跑11组Mock CLI，复算43份Trace及对应输出。
本轮新增LLM调用0次，复核此前同会话的10次真实运行、61条响应。离线重放不是新的模型决策证据。

P0定义为可直接违反不得虚报成功的核心约束；P1为审计结果可误判；P2为命令/文档操作风险。

## 发现及修复

| 分级 | 问题 | 结果 |
|---|---|---|
| P0-01 | 完成后编辑状态仍可导出completed | FIXED：src/state.py invalidate及src/agent.py result双重门禁 |
| P1-01 | live证据核验遗漏next_action/执行类型，且未复算工具与JSONL | FIXED：scripts/evidence.py、scripts/replay.py |
| P1-02 | 仅凭版本号变化推断模型改稿，可能误判修订通过 | FIXED：比较实际draft内容、同一目标时长与后续重检 |
| P2-01 | 审计默认退出码只覆盖离线，完整验收命令范围不明确 | FIXED：增加--require-live，并测试离线通过/live缺失时返回1 |
| P2-02 | README重复复制模板可能覆盖已有.env | FIXED：仅在.env不存在时复制模板；当前配置保持原样 |

P0触发范围：已完成状态被Python接口编辑后再次导出；现有CLI历史没有命中证据。旧记录不是因此被宣布无效。
修复前实际失败输出：[regressions-before-fix.txt](../examples/acceptance/regressions-before-fix.txt)；P0专项复测：[p0-after-fix.txt](../examples/acceptance/p0-after-fix.txt)。

审计工具开发时还发生过2项测试夹具失败：临时工作区复制了上轮源码指纹报告，源码变化后被新检查正确拒绝。现已改为明确标注的临时合成夹具隔离退出码测试；真实仓库测试报告未被手改。原始失败见[audit-fixture-before-fix.txt](../examples/acceptance/audit-fixture-before-fix.txt)。

## 12项验收矩阵

| # | 验收项 | 结果 | 代码 | 实际通过测试 | Trace/执行证据 |
|---|---|---|---|---|---|
| 1 | 真实模型选择动作与工具 | PASS | [src/llm_adapter.py:92](../src/llm_adapter.py#L92)、[src/agent.py:20](../src/agent.py#L20) | [tests/test_adapter.py:31](../tests/test_adapter.py#L31) | [live_normal_round1.json](../examples/traces/live_normal_round1.json)、[live_no_assets_round1.json](../examples/traces/live_no_assets_round1.json) |
| 2 | 工具观察回传下一轮模型请求 | PASS | [src/agent.py:20](../src/agent.py#L20)、[src/state.py:77](../src/state.py#L77) | [tests/test_adapter.py:86](../tests/test_adapter.py#L86) | [live_no_assets_round1.json](../examples/traces/live_no_assets_round1.json)、[live_tool_failure_round1.json](../examples/traces/live_tool_failure_round1.json) |
| 3 | 超时后模型提供不同脚本并重新检查 | PASS | [src/agent.py:74](../src/agent.py#L74)、[src/tools.py:65](../src/tools.py#L65) | [tests/test_agent.py:28](../tests/test_agent.py#L28)、[tests/test_acceptance_regressions.py:46](../tests/test_acceptance_regressions.py#L46) | [live_overtime_tight_round1.json](../examples/traces/live_overtime_tight_round1.json) |
| 4 | 无素材时改写查询或请求补充 | PASS | [src/tools.py:24](../src/tools.py#L24)、[src/agent.py:20](../src/agent.py#L20) | [tests/test_agent.py:38](../tests/test_agent.py#L38) | [live_no_assets_round1.json](../examples/traces/live_no_assets_round1.json) |
| 5 | 工具失败记录与后续行动 | PASS | [src/tools.py:208](../src/tools.py#L208)、[src/agent.py:20](../src/agent.py#L20) | [tests/test_failures.py:9](../tests/test_failures.py#L9) | [live_tool_failure_round1.json](../examples/traces/live_tool_failure_round1.json) |
| 6 | 已完成脚本的产品声明可追溯 | PASS | [src/tools.py:96](../src/tools.py#L96) | [tests/test_tools.py:94](../tests/test_tools.py#L94) | [live_normal_round1.json](../examples/traces/live_normal_round1.json)、[mock_unsupported_claim_acceptance.json](../examples/traces/mock_unsupported_claim_acceptance.json) |
| 7 | 脚本及依赖变化使旧检查失效 | PASS | [src/state.py:45](../src/state.py#L45)、[src/state.py:35](../src/state.py#L35) | [tests/test_validation.py:41](../tests/test_validation.py#L41)、[tests/test_acceptance_regressions.py:13](../tests/test_acceptance_regressions.py#L13) | [live_changed_assets_round1.json](../examples/traces/live_changed_assets_round1.json) |
| 8 | 不得跳过检查或导出过期成功 | PASS | [src/state.py:66](../src/state.py#L66)、[src/agent.py:112](../src/agent.py#L112) | [tests/test_agent.py:85](../tests/test_agent.py#L85)、[tests/test_acceptance_regressions.py:13](../tests/test_acceptance_regressions.py#L13) | [mock_unsupported_claim_acceptance.json](../examples/traces/mock_unsupported_claim_acceptance.json) |
| 9 | max_steps后明确incomplete | PASS | [src/agent.py:20](../src/agent.py#L20) | [tests/test_failures.py:74](../tests/test_failures.py#L74) | [mock_max_steps_acceptance.json](../examples/traces/mock_max_steps_acceptance.json) |
| 10 | 自动Trace及next_action一致 | PASS | [src/tracing.py:51](../src/tracing.py#L51)、[scripts/evidence.py:115](../scripts/evidence.py#L115) | [tests/test_trace_replay.py:46](../tests/test_trace_replay.py#L46)、[tests/test_acceptance_regressions.py:33](../tests/test_acceptance_regressions.py#L33) | [live_overtime_tight_round1.json](../examples/traces/live_overtime_tight_round1.json)、[mock_normal_acceptance.json](../examples/traces/mock_normal_acceptance.json) |
| 11 | 两条不同观察驱动的真实LLM路径 | PASS | [src/llm_adapter.py:92](../src/llm_adapter.py#L92)、[scripts/evidence.py:5](../scripts/evidence.py#L5) | [tests/test_adapter.py:69](../tests/test_adapter.py#L69) | [live_no_assets_round1.json](../examples/traces/live_no_assets_round1.json)、[live_overtime_tight_round1.json](../examples/traces/live_overtime_tight_round1.json)、[live_tool_failure_round1.json](../examples/traces/live_tool_failure_round1.json) |
| 12 | 场景、文档与命令一致 | PASS | [src/main.py:21](../src/main.py#L21)、[scripts/audit.py:26](../scripts/audit.py#L26) | [tests/test_trace_replay.py:60](../tests/test_trace_replay.py#L60) | [mock-manifest.json](../examples/mock-manifest.json)、[live-manifest.json](../examples/live-manifest.json) |

1. live分支使用HTTP Adapter，Runtime按模型动作分派；固定动作仅存在于明确的Mock模式。
2. 逐轮比较完整请求state与重放状态，不仅比对上一观察。
3. 4秒目标：7.64→2.35秒，旁白/分镜内容实际不同；12秒未触发记录仍保留。
4. 真实查询从月球采矿激光雷达改为激光雷达，两次无结果后needs_info。
5. 一次业务工具异常是明确注入；真实模型选择重试，随后根据超时观察改稿。
6. PASS范围为completed脚本及结构化原文约束；故意构造的failed负例仍含被标记的无据文本。完整自然语言语义为NOT VERIFIED。
7. 脚本、输入、素材、规则指纹均参与门禁；完成后编辑也撤销成功状态。
8. 修复前完成后Python对象编辑可导出completed，已复现并修复；CLI既有Trace未发现命中此漏洞。
9. 实际CLI为3步，状态incomplete、退出码4、含最后观察；未新增live上限采样。
10. 全部JSONL重建JSON并复算工具/版本/结果；不将重放算作新的LLM执行。
11. 复核10次live、61条响应；本轮新增API调用0次。
12. 核对文档CLI参数和输入文件、Markdown链接、当前测试数；默认离线与严格验收退出码明确区分。

## NOT VERIFIED

- NOT VERIFIED：服务商侧独立账单/签章及底层模型身份。
- NOT VERIFIED：任意自然语言的完整语义核验与真实产品效果。
- NOT VERIFIED：其他模型、Python3.11/3.12和其他操作系统。
- NOT VERIFIED：真实网络故障/限流恢复、真人口播、素材版权。
- NOT VERIFIED：候选人亲自操作/实际工时、评审访问及远程CI。

## 重新执行

```powershell
cd D:\Xiaoying\short-video-agent
.\.venv\Scripts\python.exe scripts/verify.py
.\.venv\Scripts\python.exe scripts/run_examples.py --mode mock --tag acceptance
.\.venv\Scripts\python.exe scripts/audit.py --require-live
.\.venv\Scripts\python.exe scripts/acceptance_audit.py
```

verify和run_examples会实际运行测试与CLI；audit/acceptance_audit重算已有证据，不自动新增模型请求。
初始12秒live用例未触发修订的记录和batch退出码1保持不变，4秒补充输入提供独立超时修订证据。
机器可读完整矩阵、源码SHA-256及逐文件结果：[strict-results.json](../examples/acceptance/strict-results.json)。

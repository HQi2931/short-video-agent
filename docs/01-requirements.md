# 需求与验收矩阵

本文件在业务代码创建前编写。项目服务于短视频创作者，输入主题、受众、平台、目标时长、风格，输出可编辑的分镜 JSON、时长、来源证据、规则结果和任务状态。素材均为合成数据，不代表真实产品能力。

## 实施计划

1. 保存需求与验收矩阵，建立轻量 Python CLI 项目。
2. 实现素材检索、确定性时长估算、保守事实与品牌检查。
3. 实现 OpenAI-compatible Adapter、原生决策循环、版本状态和自动 Trace。
4. 实际执行单元与 Mock 集成测试，保存多场景输出并修复问题。
5. 完成说明、评估、AI 使用记录、复盘和 Git 交付审计。

用户最初选择先完成离线部分，后续已填写本地 API 配置并要求进行 live 验证。需求分析开始时尚未提供 API 配置、远程仓库或评审账号；之后用户已提供 GitHub 地址并明确授权提交。计划预算 180 分钟不作为实际工时记录。

## 验收矩阵

| 编号 | 验收行为 | 实现位置 | 测试位置 | 运行证据（由程序生成） |
|---|---|---|---|---|
| A / Case 1 | 完整输入→检索→创作→两种检查→完成，逐镜给出来源 | `src/agent.py`, `src/tools.py` | `tests/test_agent.py` | `examples/traces/mock_normal.json` |
| B / Case 2 | 缺少时长等字段时请求补充，不猜测 | `src/schemas.py`, `src/agent.py` | `tests/test_validation.py` | `examples/traces/mock_missing_info.json` |
| C / Case 3 | 首次无结果，决策者可改写查询；仍无结果请求素材 | Adapter、Runner、检索工具 | `tests/test_agent.py` | `examples/traces/mock_no_assets.json` |
| D / Case 4 | 注入一次工具错误，观察错误后重试；错误不能通过验证 | Tool Executor、Runner | `tests/test_failures.py` | `examples/traces/mock_tool_failure.json` |
| E / Case 5 | 首稿超时，决策者提供修改稿，重新估时与查规则 | Runner、版本状态、估时工具 | `tests/test_agent.py` | `examples/traces/mock_overtime.json` |
| F / Case 6 | 拒绝无依据的 80% 效果声明、伪造 ID、错误原文、漏引用 | `check_brand_rules` | `tests/test_tools.py`, `tests/test_validation.py` | `examples/traces/mock_unsupported_claim.json` |
| Case 7 | 达到 max_steps 返回 incomplete、已执行步骤、最后观察 | Runner | `tests/test_failures.py` | `examples/traces/mock_max_steps.json` |
| Case 8 | 更换目标、素材、规则或脚本使旧验证失效 | `src/state.py`, finish gate | `tests/test_validation.py` | `mock_changed_duration.json`, `mock_changed_assets.json` |
| 规则修正 | 观察品牌违规后修改脚本并重新检查 | Runner、Mock fixture | `tests/test_agent.py` | `examples/traces/mock_rule_repair.json` |
| 协议异常 | 非 JSON、未知动作、非法参数返回观察，执行上限仍有效 | Adapter、Executor | `tests/test_failures.py`, `tests/test_adapter.py` | 测试实际输出 |
| 可审计 | run_id、模式、模型、请求/响应、动作、参数、观察、错误自动落盘 | `src/tracing.py` | `tests/test_agent.py`, `tests/test_adapter.py` | `examples/traces/*.json`, `*.jsonl` |
| live 动态性 | 至少两条真实模型路径，包含实际请求与工具观察反馈 | Live Adapter、运行/汇总/核验脚本 | 已执行10次真实运行并核验动作、参数与反馈一致性 | `examples/live-summary.json`；`live_no_assets_round1.json`、`live_overtime_tight_round1.json` |
| 交付 | 可运行 README、五份文档、真实测试输出、无密钥、无题目原文 | 项目文档与审计脚本 | 实际命令、审计报告 | `examples/test-results.txt`, `examples/audit.json` |

## 成功标准与范围

- 只有完整输入、可靠素材、当前版本时长通过、当前版本规则通过时，Runtime 才允许 `completed`。
- 创作和动作选择由 live 模型负责。离线 Mock 是公开标记的确定性测试替身，不能证明模型能力。
- 无法核验的自由表述保守阻断；本项目不声称用字符串规则解决所有语义事实核查。
- 不开发 UI、视频渲染、向量库、部署或多 Agent；使用 Python 3.11+、Pydantic、httpx、dotenv、pytest。
- 未经提供授权不创建远程仓库、不发布。候选人审核、实际工时、保密审批、评审访问授权需本人确认。

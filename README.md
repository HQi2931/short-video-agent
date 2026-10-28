# 短视频脚本 Agent

一个基于 Python 原生循环的、带证据和版本检查的短视频脚本 Agent。输入创作目标，输出可编辑的分镜 JSON、逐镜时长、素材 ID、事实原文和任务状态。产品与素材均为合成数据。

**当前交付：离线验证及真实模型验证均已执行。** 使用配置的 `deepseek-flash` 累计完成13次真实运行，覆盖8类场景，保存77条模型响应；核验到8条不同的有效决策路径，见[真实验证报告](examples/live-report.md)。其中3次由候选人亲自执行，见[本人实测核对](docs/08-manual-live-review.md)。已配置[私有 GitHub 仓库](https://github.com/HQi2931/short-video-agent)。Mock 的修订路径仍是预设测试数据；live 每一步由远程模型返回动作，Runtime 负责校验、执行工具和完成门禁。

## 安装与运行

需要 Python 3.11+。在 Windows PowerShell 中：

```powershell
cd D:\Xiaoying\short-video-agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.main --mode mock --input-file examples/inputs/normal.json
```

若已激活虚拟环境或已安装依赖，也可直接使用：

```bash
python -m src.main --mode mock --input-file examples/inputs/normal.json
python -m pytest tests/ -v
```

本次实际验证环境见 [环境记录](examples/test-environment.json)，依赖快照见 [requirements-lock.txt](requirements-lock.txt)。Python 3.11/3.12 尚未单独执行兼容性测试。

## 运行其他离线案例

```powershell
.\.venv\Scripts\python.exe -m src.main --mode mock --scenario overtime --input-file examples/inputs/overtime.json
.\.venv\Scripts\python.exe -m src.main --mode mock --scenario tool_failure --input-file examples/inputs/tool_failure.json
.\.venv\Scripts\python.exe -m src.main --mode mock --scenario no_assets --input-file examples/inputs/no_assets.json
.\.venv\Scripts\python.exe -m src.main --mode mock --scenario unsupported_claim --input-file examples/inputs/unsupported_claim.json
.\.venv\Scripts\python.exe -m src.main --mode mock --scenario max_steps --input-file examples/inputs/max_steps.json --max-steps 3
```

`--scenario` 仅选择 Mock 预设动作。输入与情景应搭配；默认 `normal` 不会替所有输入自动规划。CLI 日志会显示本次输出与 Trace 路径。

## 真实模型模式

将 `.env.example` 复制为 `.env`，在本地填写配置，勿将密钥提交到 Git：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

```dotenv
LLM_API_KEY=在本地填写
LLM_BASE_URL=服务商的完整API前缀
LLM_MODEL=服务商实际支持的模型名
MAX_AGENT_STEPS=12
LLM_TIMEOUT_SECONDS=60
LLM_RESPONSE_FORMAT=json_object
```

`LLM_BASE_URL` 应包含服务商 API 前缀，例如 `https://api.openai.com/v1`。程序追加 `/chat/completions`。远程地址使用 HTTPS，HTTP 只支持本机回环。兼容服务若不支持 `response_format`，显式设置为 `none`；程序仍验证返回的 JSON 动作。没有默认密钥或默认模型，也不会自动降级为 Mock。

```powershell
.\.venv\Scripts\python.exe -m src.main --mode live --input-file examples/inputs/normal.json
.\.venv\Scripts\python.exe -m src.main --mode live --input-file examples/inputs/overtime.json
.\.venv\Scripts\python.exe -m src.main --mode live --input-file examples/inputs/overtime_tight.json
.\.venv\Scripts\python.exe scripts/run_examples.py --mode live
.\.venv\Scripts\python.exe scripts/summarize_live.py
```

live 批量运行会产生真实 API 请求并消耗服务商额度。是否通过具体行为验证，取决于真实模型返回；若超时案例首稿已合格，不能记为“超时后修订已验证”。本次12秒用例首稿10.41秒，未触发修订，原批次 `all_expected_behaviors=false` 与退出码1如实保留；随后4秒补充用例实际出现7.64→2.35秒修订。`summarize_live.py` 汇总已有证据，不新增模型调用，也不覆盖初始批次结果。

## 检查与实际证据

```powershell
.\.venv\Scripts\python.exe scripts/verify.py
.\.venv\Scripts\python.exe scripts/run_examples.py --mode mock
.\.venv\Scripts\python.exe scripts/audit.py
.\.venv\Scripts\python.exe scripts/audit.py --require-live
.\.venv\Scripts\python.exe scripts/acceptance_audit.py
.\.venv\Scripts\python.exe -m pip check
```

- [测试实际输出](examples/test-results.txt) 与 [JUnit 报告](examples/test-results.xml)：严格验收修复后129项通过。重跑时保留旧文本报告。
- [离线案例清单](examples/mock-manifest.json)：每组输入、输出、Trace、退出码和动作路径。
- [最终审计](examples/audit.json)：分别报告离线检查、live 覆盖与人工待办；工程验证通过仍不代表候选人审核已完成。
- 默认 `audit.py` 仅以离线检查决定退出码；完整交付使用 `--require-live`。严格的12项验收矩阵见[审计报告](docs/07-acceptance-audit.md)，由候选人发起、AI工具执行，包含修复前的失败证据。
- [真实运行汇总](examples/live-summary.json)与[报告](examples/live-report.md)：13次运行全部保留，包括1条未触发预期修订的记录。
- 两条真实动态路径：[无素材后改写查询并请求补充](examples/traces/live_no_assets_round1.json)；[超时后改稿并重新检查](examples/traces/live_overtime_tight_round1.json)。另有[注入工具错误后的模型重试](examples/traces/live_tool_failure_round1.json)及[引用规则修正](examples/traces/live_changed_assets_round1.json)。
- 基准超时例的实际工具估时为 **43.43 → 7.64 秒**，目标 12 秒；两个脚本版本和重新检查记录见 [修订 Trace](examples/traces/mock_overtime_validated.json)。此路径为 **Mock 预设修订**。
- [正常例](examples/outputs/mock_normal_validated.json)、[工具失败例](examples/traces/mock_tool_failure_validated.json)、[拒绝无据效果例](examples/traces/mock_unsupported_claim_validated.json)。

Trace 自动生成 JSON 与追加式 JSONL。`run_id` 不覆盖已有日志；批量重跑产生新的 ID，最新关联以 manifest 为准。末步的 `next_action=null` 表示没有下一动作，前面步骤的下一动作来自后续真实执行，并非预先猜测。

退出码：`0 completed`，`2 needs_info`，`3 failed`，`4 incomplete`，`5 输入/配置/启动错误`。非零退出码可能是负向测试的预期结果。

## 事实约束与时长限制

所有产品事实必须通过素材 ID、事实 ID、事实原文和 `claim_text` 四项核对。旁白、字幕、画面描述、标题都进行检查。当前采用保守策略：文本由完整事实原文与品牌批准的非事实短语组合；无法解释的自由改写标记待确认并阻止完成。原主题与素材没有目录关键词联系时，也要求确认，避免改写检索时换成无关产品。

这会限制自由创作，可能误拒合理同义改写。批准文案和素材属于可信配置，应人工审核；程序不声称完成所有语义核查、真实产品效果验证或素材版权审核。编辑输出后，需作为新稿调用 Runner 的 `draft_script` 动作并重新检查，直接编辑 JSON 不会保留“已验证”保证。

估时考虑中文字符、英文单词、数字组、标点停顿、字幕阅读、最短镜头和转场。旁白与字幕同时出现时取较长值；标题仅作元数据，不另外计算口播。实际语速、画面节奏仍需真人复核。

脚本、用户目标、素材快照、检索素材或品牌规则任一变化，旧检查不能用于完成。任何业务工具错误会清空两项当前检查；不能跳过验证直接完成。

已完成任务的 Python 状态若被修改，结果会降为 incomplete；导出结果时再次核验门禁，防止绕过更新方法直接编辑对象后仍返回 completed。继续生成应创建新的运行状态。

## 工程与交付文档

- [需求与验收矩阵](docs/01-requirements.md)
- [方案与技术取舍](docs/02-solution.md)
- [实际评估与限制](docs/03-evaluation.md)
- [AI 辅助开发记录](docs/04-ai-usage.md)
- [复盘与待办](docs/05-retrospective.md)
- [私有 GitHub 交付清单](docs/06-delivery.md)
- [严格校招验收审计](docs/07-acceptance-audit.md)
- [候选人亲自执行的API验证](docs/08-manual-live-review.md)

此仓库没有复制考核题目原文。仓库可见性已核实为 Private，实际提交以 GitHub 历史为准。候选人仍需完成本人代码审核、实际工时与评审访问权限确认；文档中的 TODO 不代表已经审核通过。

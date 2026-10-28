# 短视频脚本 Agent 第一期效果评测


评测日期：2026-10-28（Asia/Shanghai）；原始证据时间戳按UTC保存。

本轮核对后的能力清单与补充维度见 [eval/README.md](../eval/README.md)。核心代码、历史Trace、原测试、既有审计记录均未修改。历史证据重新复核：46/46份Trace可复算，其中13份已有live请求记录一致；这些不是本轮新增模型调用，见 [历史复核](../eval/evidence/historical-recheck.json)。任务所述43份为此前阶段口径，07审计已更新为46份。

基线实跑129项通过；新增10项评测契约测试后，最终139项通过，见 [改动前测试](../eval/evidence/baseline-tests.txt)、[最终回归](../eval/evidence/completion-regression-after-fix.txt)。新增C类连续改稿诊断后，一条测试曾要求失败标签只能为D，实际也命中C；已改为必须包含D，保留 [该次失败输出](../eval/evidence/completion-regression-tests.txt)。没有修改Agent以适配评测。

本轮结果：20例真实执行、140次真实请求，16例completed、3例needs_info、1例incomplete。自动场景验收19/20（95%），任务完成16/20（80%）。人工语义和创作质量均为NOT VERIFIED。

## 1. 评测目的

建立固定样本、可复算的效果基线，诊断下一阶段问题。本轮只新增eval模块，不修改核心执行循环。单次随机样本不代表稳定性结论。

## 2. 环境与模型配置

配置见 [environment.json](../eval/runs/20261028T052239Z_743fa464/rescore_20261028T053239Z_d3fe90/environment.json)。模型：deepseek-flash；请求上限 240；每例步骤上限 12、工具上限 9；每请求超时 45.0 秒。无自动重试，不设置金额预算；请求预算为硬上限，不能保证账单金额。
数据集与源码均记录指纹；每次运行新建独立目录。现有适配器不支持seed/temperature配置，复现指执行流程和评分口径，不保证模型逐字重现。

## 3. 数据集与场景分布

{'normal': 4, 'duration': 4, 'no_assets': 3, 'tool_failure': 3, 'unsupported': 3, 'brand': 3}
[固定输入、期望、通过标准、素材及品牌规则](../eval/runs/20261028T052239Z_743fa464/rescore_20261028T053239Z_d3fe90/dataset.json)。20例全新输入与独立合成目录；未从历史trace抽取答案。后续调优应另建v2保留集。故障为明确的业务工具注入，模型后续选择为真实API决策。

## 4. 指标定义

| 指标 | 分子 / 分母及失败处理 |
|---|---|
| Task Completion Rate | 独立重算门禁、模型记录和完整重放均通过的 completed / 全部20例；拒绝、失败、未执行均非完成 |
| Case Acceptance Rate | 各例结构标准通过 / 全部20例；安全拒绝可满足负向案例，但不计脚本交付完成 |
| Duration Correction Success Rate | 实际观察超时、不同稿修订且最终通过 / 全部4个预设超时例；未触发、失败、未执行均不算成功；另报触发数 |
| Tool Decision Appropriateness (proxy) | 工具尝试数减非法/失败调用及相同查询或同版本重复检查 / 全部实际工具尝试；明确注入的故障不扣分；首次无结果不扣分；完整语义 NOT VERIFIED |
| Evidence Traceability Rate | 最终稿中ID、原文、声明、source_id和使用位置均可核对的引用 / 全部最终稿声明引用；失败稿也纳入；漏引通过全文规则和人工审核另查，不能仅凭此率断言全文无幻觉 |
| Unsupported Claim Rate (proxy) | 独立保守字符串检查发现未核实文本的最终稿 / 全部有最终稿的运行（包含失败）；无稿不纳入；语义级逐声明比率 NOT VERIFIED |
| Average Agent Steps | 总实际记录步骤 / 实际执行例；含模型错误和预算停止步骤 |
| Average Tool Calls | 三个业务工具的调用尝试（含失败） / 实际执行例；不含draft/finish等内部动作 |
| Average End-to-End Latency | AgentRunner开始至Trace落盘的单调时钟耗时总和 / 实际执行例；含工具错误、服务错误和终止；不含评分时间 |

所有分母为0时输出null（不可评估），不填0%。跳过样本列明原因，不算成功。A–H频率是命中案例数/实际执行例、多标签，可相加超过100%；观察到并恢复的问题与验收失败分开统计。预算终止不是服务错误；H仅代表模型响应/传输/服务错误。Token仅汇总服务商返回usage，缺失另标记，不等同账单成本。


## 5. 实际测试结果

实际执行 20/20；尝试请求 140；报告Token合计 781794。live批次完整验证：True。
[机器指标及分子分母](../eval/runs/20261028T052239Z_743fa464/rescore_20261028T053239Z_d3fe90/summary.json)；[逐例评分、重放、人工审核字段](../eval/runs/20261028T052239Z_743fa464/rescore_20261028T053239Z_d3fe90/results.json)。

| 指标 | 分子 / 分母 | 实际值 |
|---|---|---|
| case_acceptance_rate | 19 / 20 | 0.9500 |
| task_completion_rate | 16 / 20 | 0.8000 |
| duration_correction_success_rate | 4 / 4 | 1.0000 |
| tool_decision_appropriateness_proxy | 78 / 78 | 1.0000 |
| evidence_traceability_rate | 34 / 34 | 1.0000 |
| unsupported_claim_rate_proxy | 0 / 17 | 0.0000 |
| average_agent_steps | 140 / 20 | 7.0000 |
| average_tool_calls | 78 / 20 | 3.9000 |
| average_end_to_end_latency_seconds | 582.8752536000684 / 20 | 29.1438 |

| 案例 | 场景 | 状态 | 自动验收 | 原始证据 |
|---|---|---|---|---|
| holdout-01 | normal | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-01.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-01-output.json) |
| holdout-02 | normal | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-02.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-02-output.json) |
| holdout-03 | normal | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-03.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-03-output.json) |
| holdout-04 | normal | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-04.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-04-output.json) |
| holdout-05 | duration | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-05.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-05-output.json) |
| holdout-06 | duration | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-06.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-06-output.json) |
| holdout-07 | duration | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-07.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-07-output.json) |
| holdout-08 | duration | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-08.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-08-output.json) |
| holdout-09 | no_assets | needs_info | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-09.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-09-output.json) |
| holdout-10 | no_assets | needs_info | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-10.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-10-output.json) |
| holdout-11 | no_assets | needs_info | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-11.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-11-output.json) |
| holdout-12 | tool_failure | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-12.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-12-output.json) |
| holdout-13 | tool_failure | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-13.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-13-output.json) |
| holdout-14 | tool_failure | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-14.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-14-output.json) |
| holdout-15 | unsupported | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-15.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-15-output.json) |
| holdout-16 | unsupported | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-16.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-16-output.json) |
| holdout-17 | unsupported | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-17.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-17-output.json) |
| holdout-18 | brand | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-18.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-18-output.json) |
| holdout-19 | brand | completed | True | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-19.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-19-output.json) |
| holdout-20 | brand | incomplete | False | [Trace](../eval/runs/20261028T052239Z_743fa464/traces/holdout-20.json) / [输出](../eval/runs/20261028T052239Z_743fa464/holdout-20-output.json) |

## 6. 成功案例

- holdout-01：normal，completed；[]。
- holdout-02：normal，completed；[]。
- holdout-03：normal，completed；['rule_revision']。
- holdout-04：normal，completed；[]。
- holdout-05：duration，completed；['duration_revision']。
- holdout-06：duration，completed；['duration_revision']。
- holdout-07：duration，completed；['duration_revision']。
- holdout-08：duration，completed；['duration_revision']。
- holdout-09：no_assets，needs_info；['query_rewrite']。
- holdout-10：no_assets，needs_info；['query_rewrite']。
- holdout-11：no_assets，needs_info；['query_rewrite']。
- holdout-12：tool_failure，completed；['duration_revision', 'tool_retry']。
- holdout-13：tool_failure，completed；['tool_retry']。
- holdout-14：tool_failure，completed；['rule_revision', 'tool_retry']。
- holdout-15：unsupported，completed；['duration_revision']。
- holdout-16：unsupported，completed；['rule_revision']。
- holdout-17：unsupported，completed；['duration_revision']。
- holdout-18：brand，completed；[]。
- holdout-19：brand，completed；['duration_revision']。

## 7. 失败案例

- holdout-20：incomplete，分类 ['C', 'D', 'F']；最后观察、全部动作及重放问题见对应Trace和results.json。

## 8. 根因分析

| 类别 | 自动验收失败例数 | 观察到问题例数（含恢复） |
|---|---|---|
| A 检索问题 | 0 | 0 |
| B 工具选择问题 | 0 | 0 |
| C 无效重复调用 | 1 | 6 |
| D 时长估算或修改问题 | 1 | 1 |
| E 事实幻觉/未核实文本代理 | 0 | 0 |
| F 规则校验问题 | 1 | 5 |
| G 状态管理问题 | 0 | 0 |
| H 模型服务错误 | 0 | 1 |
分类为证据规则归因线索，不等同已确认根因。E中的未核实改写可能是误拒；B/C需人工判断是否必要重复。预期工具注入本身不是Agent缺陷。


本轮唯一最终验收失败为holdout-20。第3步估时20.64秒，目标20秒；第4–10步连续提交7次不同完整脚本，中间没有工具估时；第11步重估为18.25秒，第12步规则通过，随后达到max_steps=12而未执行finish，最终incomplete。最后稿通过两个检查，仍不能推断任务已完成。C/D/F是同一案例的多个标签，不能算作3个独立失败。

中间问题（包含恢复）：C代理命中6/20例，表示相邻两次成功draft之间没有工具观察，具体步骤保存在unchecked_consecutive_draft_steps。这是额外版本提交的可测量信号，其创作必要性仍待人工审核。F命中5/20例：holdout-01草稿含空旁白/字幕镜头而被schema拒绝；holdout-03、14、16出现missing_fact_reference后修订；holdout-20品牌场景未完成验收亦标F，但没有观察到最终品牌规则违反。H为holdout-03一次JSON解析错误，后续恢复成功，所以H最终失败数为0。A/B/E/G未命中不代表能力已普遍验证。注入工具故障本身不作为Agent缺陷。

原始评分沿用只接受合法动作的旧审计工具，将含解析错误后恢复的holdout-03判为未验证。该评分和整批退出码1保留于 [原始结果](../eval/runs/20261028T052239Z_743fa464/results.json)、[原始控制台](../eval/evidence/live-console.txt)。eval/audit.py补充错误响应与后续状态链的离线重放，经测试后重新评分；新评分单独归档，未覆盖原始Trace或评分，也未重新请求模型。最终20份执行记录均可核对，仅19例通过场景验收。

工具决策代理100%仅表示78次工具尝试未命中已定义的非法参数、非注入失败或重复工具查询检查；该指标不覆盖draft动作效率，不代表人工认可全部决策。引用34/34不能排除未标注声明，全文字符串规则另查；语义级Unsupported Claim Rate仍为NOT VERIFIED，自动0/17只是最终稿未核实文本代理。

## 9. 下一阶段优化优先级


1. **减少没有工具反馈的连续改稿，为重新检查和完成预留步骤。** C代理出现6/20例，在holdout-20与超时修改D共同导致唯一最终失败。下一阶段先验证“工具观察后一次最小修订→立即估时→按需检查→完成”的预算规划；在新独立案例中减少连续无观察draft，同时保留全部安全门禁。本轮尚未实施这些Agent优化。
2. **提升首次稿件的引用与schema完整性。** 3/20例出现漏fact_refs，另1/20例草稿结构不合法，均经恢复但消耗步骤。下一阶段改进纯展示镜头的source_ids/fact_refs使用规范与可读镜头生成契约，并以独立回归集检查首次稿通过率和总步数。

H解析错误仅1例且恢复，暂列观察项。D与C来自同一最终失败路径，不为凑数量重复设立修复项目。

## 10. 已知限制

人工审核全部 NOT VERIFIED。审核者逐例核对原主题未漂移、每个工具动作是否基于观察且必要、每条自然语言事实是否被来源蕴含、拒绝理由是否明确；创作质量1–5分（1不可用、3可编辑、5可直接审片）。只允许署名人工填写results中的reviewer、reviewed_at、布尔字段与notes，原自动证据保持不变。
真人口播、产品真实性、版权、服务商独立账单、模型身份、线上传播效果均 NOT VERIFIED。20例一次采样没有置信稳定性保证；严格字符串工具可能误拒自然改写。报告保留全部失败和未执行例；离线验证不能替代真实模型结果。

实际执行命令（项目根目录；没有推送远程）：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m eval.run
.\.venv\Scripts\python.exe -m eval.run --live --max-requests 240 --max-steps 12 --max-tool-calls 9 --timeout 45
.\.venv\Scripts\python.exe -m eval.rescore eval/runs/20261028T052239Z_743fa464
```

live命令实际退出1；离线验证、最终重算、最终回归退出0。配置与响应模型名均为deepseek-flash；781,794为返回usage的total_tokens之和，不是账单金额。完整request、公开动作、参数、observation、next_action、输出、状态、故障注入和素材快照保存在对应Trace中，不保存服务商私有推理内容。执行时与最终评分源码指纹分别归档。

新增代码为eval/__init__.py、dataset.py、run.py、metrics.py、audit.py、report.py、rescore.py及tests/test_eval.py；固定数据集为eval/dataset-v1.json，说明见eval/README.md。完整交付清单见 [delivery-manifest.json](../eval/evidence/delivery-manifest.json)。

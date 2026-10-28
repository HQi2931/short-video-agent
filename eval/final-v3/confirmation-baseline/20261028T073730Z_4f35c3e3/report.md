# 短视频脚本 Agent 第一期效果评测

## 1. 评测目的
建立固定样本、可复算的效果基线，诊断下一阶段问题。本轮只新增eval模块，不修改核心执行循环。单次随机样本不代表稳定性结论。

## 2. 环境与模型配置
配置见 [environment.json](environment.json)。模型：deepseek-flash；请求上限 144；每例步骤上限 12、工具上限 9；每请求超时 45.0 秒。无自动重试，不设置金额预算；请求预算为硬上限，不能保证账单金额。
数据集与源码均记录指纹；每次运行新建独立目录。现有适配器不支持seed/temperature配置，复现指执行流程和评分口径，不保证模型逐字重现。

## 3. 数据集与场景分布
{'normal': 5, 'duration': 3, 'unsupported': 2, 'tool_failure': 2}
[固定输入、期望、通过标准、素材及品牌规则](dataset.json)。20例全新输入与独立合成目录；未从历史trace抽取答案。后续调优应另建v2保留集。故障为明确的业务工具注入，模型后续选择为真实API决策。

## 4. 指标定义
| 指标 | 分子 / 分母及失败处理 |
|---|---|
| Task Completion Rate | 独立重算门禁、模型记录和完整重放均通过的 completed / 全部12例；拒绝、失败、未执行均非完成 |
| Case Acceptance Rate | 各例结构标准通过 / 全部12例；安全拒绝可满足负向案例，但不计脚本交付完成 |
| Duration Correction Success Rate | 实际观察超时、不同稿修订且最终通过 / 全部3个预设超时例；未触发、失败、未执行均不算成功；另报触发数 |
| Tool Decision Appropriateness (proxy) | 工具尝试数减非法/失败调用及相同查询或同版本重复检查 / 全部实际工具尝试；明确注入的故障不扣分；首次无结果不扣分；完整语义 NOT VERIFIED |
| Evidence Traceability Rate | 最终稿中ID、原文、声明、source_id和使用位置均可核对的引用 / 全部最终稿声明引用；失败稿也纳入；漏引通过全文规则和人工审核另查，不能仅凭此率断言全文无幻觉 |
| Unsupported Claim Rate (proxy) | 独立保守字符串检查发现未核实文本的最终稿 / 全部有最终稿的运行（包含失败）；无稿不纳入；语义级逐声明比率 NOT VERIFIED |
| Average Agent Steps | 总实际记录步骤 / 实际执行例；含模型错误和预算停止步骤 |
| Average Tool Calls | 三个业务工具的调用尝试（含失败） / 实际执行例；不含draft/finish等内部动作 |
| Average End-to-End Latency | AgentRunner开始至Trace落盘的单调时钟耗时总和 / 实际执行例；含工具错误、服务错误和终止；不含评分时间 |

所有分母为0时输出null（不可评估），不填0%。跳过样本列明原因，不算成功。A–H频率是命中案例数/实际执行例、多标签，可相加超过100%；观察到并恢复的问题与验收失败分开统计。预算终止不是服务错误；H仅代表模型响应/传输/服务错误。Token仅汇总服务商返回usage，缺失另标记，不等同账单成本。


## 5. 实际测试结果
实际执行 12/12；尝试请求 76；报告Token合计 437341。live批次完整验证：True。
[机器指标及分子分母](summary.json)；[逐例评分、重放、人工审核字段](results.json)。
| 指标 | 分子 / 分母 | 实际值 |
|---|---|---|
| case_acceptance_rate | 11 / 12 | 0.9167 |
| task_completion_rate | 11 / 12 | 0.9167 |
| duration_correction_success_rate | 3 / 3 | 1.0000 |
| tool_decision_appropriateness_proxy | 43 / 43 | 1.0000 |
| evidence_traceability_rate | 22 / 22 | 1.0000 |
| unsupported_claim_rate_proxy | 0 / 12 | 0.0000 |
| average_agent_steps | 76 / 12 | 6.3333 |
| average_tool_calls | 43 / 12 | 3.5833 |
| average_end_to_end_latency_seconds | 311.40850619999947 / 12 | 25.9507 |

| 案例 | 场景 | 状态 | 自动验收 | 原始证据 |
|---|---|---|---|---|
| confirm-01 | normal | completed | True | [Trace](traces/confirm-01.json) / [输出](confirm-01-output.json) |
| confirm-02 | normal | completed | True | [Trace](traces/confirm-02.json) / [输出](confirm-02-output.json) |
| confirm-03 | normal | completed | True | [Trace](traces/confirm-03.json) / [输出](confirm-03-output.json) |
| confirm-04 | normal | completed | True | [Trace](traces/confirm-04.json) / [输出](confirm-04-output.json) |
| confirm-05 | normal | completed | True | [Trace](traces/confirm-05.json) / [输出](confirm-05-output.json) |
| confirm-06 | duration | completed | True | [Trace](traces/confirm-06.json) / [输出](confirm-06-output.json) |
| confirm-07 | duration | completed | True | [Trace](traces/confirm-07.json) / [输出](confirm-07-output.json) |
| confirm-08 | duration | completed | True | [Trace](traces/confirm-08.json) / [输出](confirm-08-output.json) |
| confirm-09 | unsupported | needs_info | False | [Trace](traces/confirm-09.json) / [输出](confirm-09-output.json) |
| confirm-10 | unsupported | completed | True | [Trace](traces/confirm-10.json) / [输出](confirm-10-output.json) |
| confirm-11 | tool_failure | completed | True | [Trace](traces/confirm-11.json) / [输出](confirm-11-output.json) |
| confirm-12 | tool_failure | completed | True | [Trace](traces/confirm-12.json) / [输出](confirm-12-output.json) |

## 6. 成功案例
- confirm-01：normal，completed；[]。
- confirm-02：normal，completed；[]。
- confirm-03：normal，completed；[]。
- confirm-04：normal，completed；[]。
- confirm-05：normal，completed；['duration_revision']。
- confirm-06：duration，completed；['duration_revision']。
- confirm-07：duration，completed；['duration_revision']。
- confirm-08：duration，completed；['duration_revision']。
- confirm-10：unsupported，completed；['rule_revision']。
- confirm-11：tool_failure，completed；['tool_retry']。
- confirm-12：tool_failure，completed；['tool_retry']。

## 7. 失败案例
- confirm-09：needs_info，分类 ['D', 'E']；最后观察、全部动作及重放问题见对应Trace和results.json。

## 8. 根因分析
| 类别 | 自动验收失败例数 | 观察到问题例数（含恢复） |
|---|---|---|
| A 检索问题 | 0 | 0 |
| B 工具选择问题 | 0 | 0 |
| C 无效重复调用 | 0 | 0 |
| D 时长估算或修改问题 | 1 | 1 |
| E 事实幻觉/未核实文本代理 | 1 | 2 |
| F 规则校验问题 | 0 | 3 |
| G 状态管理问题 | 0 | 0 |
| H 模型服务错误 | 0 | 1 |
分类为证据规则归因线索，不等同已确认根因。E中的未核实改写可能是误拒；B/C需人工判断是否必要重复。预期工具注入本身不是Agent缺陷。

## 9. 下一阶段优化优先级
- D 时长估算或修改问题：1例失败；先逐条复核对应观察，再设计最小修复及独立回归集。
- E 事实幻觉/未核实文本代理：1例失败；先逐条复核对应观察，再设计最小修复及独立回归集。

## 10. 已知限制
人工审核全部 NOT VERIFIED。审核者逐例核对原主题未漂移、每个工具动作是否基于观察且必要、每条自然语言事实是否被来源蕴含、拒绝理由是否明确；创作质量1–5分（1不可用、3可编辑、5可直接审片）。只允许署名人工填写results中的reviewer、reviewed_at、布尔字段与notes，原自动证据保持不变。
真人口播、产品真实性、版权、服务商独立账单、模型身份、线上传播效果均 NOT VERIFIED。20例一次采样没有置信稳定性保证；严格字符串工具可能误拒自然改写。报告保留全部失败和未执行例；离线验证不能替代真实模型结果。

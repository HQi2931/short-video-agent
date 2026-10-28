# 短视频脚本 Agent 第一期效果评测

## 1. 评测目的
建立固定样本、可复算的效果基线，诊断下一阶段问题。本轮只新增eval模块，不修改核心执行循环。单次随机样本不代表稳定性结论。

## 2. 环境与模型配置
配置见 [environment.json](environment.json)。模型：deepseek-flash；请求上限 240；每例步骤上限 12、工具上限 9；每请求超时 45.0 秒。无自动重试，不设置金额预算；请求预算为硬上限，不能保证账单金额。
数据集与源码均记录指纹；每次运行新建独立目录。现有适配器不支持seed/temperature配置，复现指执行流程和评分口径，不保证模型逐字重现。

## 3. 数据集与场景分布
{'normal': 4, 'duration': 4, 'no_assets': 3, 'tool_failure': 3, 'unsupported': 3, 'brand': 3}
[固定输入、期望、通过标准、素材及品牌规则](dataset.json)。20例全新输入与独立合成目录；未从历史trace抽取答案。后续调优应另建v2保留集。故障为明确的业务工具注入，模型后续选择为真实API决策。

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
实际执行 20/20；尝试请求 140；报告Token合计 781794。live批次完整验证：False。
[机器指标及分子分母](summary.json)；[逐例评分、重放、人工审核字段](results.json)。
| 指标 | 分子 / 分母 | 实际值 |
|---|---|---|
| case_acceptance_rate | 18 / 20 | 0.9000 |
| task_completion_rate | 15 / 20 | 0.7500 |
| duration_correction_success_rate | 4 / 4 | 1.0000 |
| tool_decision_appropriateness_proxy | 78 / 78 | 1.0000 |
| evidence_traceability_rate | 34 / 34 | 1.0000 |
| unsupported_claim_rate_proxy | 0 / 17 | 0.0000 |
| average_agent_steps | 140 / 20 | 7.0000 |
| average_tool_calls | 78 / 20 | 3.9000 |
| average_end_to_end_latency_seconds | 582.8752536000684 / 20 | 29.1438 |

| 案例 | 场景 | 状态 | 自动验收 | 原始证据 |
|---|---|---|---|---|
| holdout-01 | normal | completed | True | [Trace](traces/holdout-01.json) / [输出](holdout-01-output.json) |
| holdout-02 | normal | completed | True | [Trace](traces/holdout-02.json) / [输出](holdout-02-output.json) |
| holdout-03 | normal | completed | False | [Trace](traces/holdout-03.json) / [输出](holdout-03-output.json) |
| holdout-04 | normal | completed | True | [Trace](traces/holdout-04.json) / [输出](holdout-04-output.json) |
| holdout-05 | duration | completed | True | [Trace](traces/holdout-05.json) / [输出](holdout-05-output.json) |
| holdout-06 | duration | completed | True | [Trace](traces/holdout-06.json) / [输出](holdout-06-output.json) |
| holdout-07 | duration | completed | True | [Trace](traces/holdout-07.json) / [输出](holdout-07-output.json) |
| holdout-08 | duration | completed | True | [Trace](traces/holdout-08.json) / [输出](holdout-08-output.json) |
| holdout-09 | no_assets | needs_info | True | [Trace](traces/holdout-09.json) / [输出](holdout-09-output.json) |
| holdout-10 | no_assets | needs_info | True | [Trace](traces/holdout-10.json) / [输出](holdout-10-output.json) |
| holdout-11 | no_assets | needs_info | True | [Trace](traces/holdout-11.json) / [输出](holdout-11-output.json) |
| holdout-12 | tool_failure | completed | True | [Trace](traces/holdout-12.json) / [输出](holdout-12-output.json) |
| holdout-13 | tool_failure | completed | True | [Trace](traces/holdout-13.json) / [输出](holdout-13-output.json) |
| holdout-14 | tool_failure | completed | True | [Trace](traces/holdout-14.json) / [输出](holdout-14-output.json) |
| holdout-15 | unsupported | completed | True | [Trace](traces/holdout-15.json) / [输出](holdout-15-output.json) |
| holdout-16 | unsupported | completed | True | [Trace](traces/holdout-16.json) / [输出](holdout-16-output.json) |
| holdout-17 | unsupported | completed | True | [Trace](traces/holdout-17.json) / [输出](holdout-17-output.json) |
| holdout-18 | brand | completed | True | [Trace](traces/holdout-18.json) / [输出](holdout-18-output.json) |
| holdout-19 | brand | completed | True | [Trace](traces/holdout-19.json) / [输出](holdout-19-output.json) |
| holdout-20 | brand | incomplete | False | [Trace](traces/holdout-20.json) / [输出](holdout-20-output.json) |

## 6. 成功案例
- holdout-01：normal，completed；[]。
- holdout-02：normal，completed；[]。
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
- holdout-03：completed，分类 ['F', 'H']；最后观察、全部动作及重放问题见对应Trace和results.json。
- holdout-20：incomplete，分类 ['F']；最后观察、全部动作及重放问题见对应Trace和results.json。

## 8. 根因分析
| 类别 | 自动验收失败例数 | 观察到问题例数（含恢复） |
|---|---|---|
| A 检索问题 | 0 | 0 |
| B 工具选择问题 | 0 | 0 |
| C 无效重复调用 | 0 | 0 |
| D 时长估算或修改问题 | 0 | 0 |
| E 事实幻觉/未核实文本代理 | 0 | 0 |
| F 规则校验问题 | 2 | 4 |
| G 状态管理问题 | 0 | 0 |
| H 模型服务错误 | 1 | 1 |
分类为证据规则归因线索，不等同已确认根因。E中的未核实改写可能是误拒；B/C需人工判断是否必要重复。预期工具注入本身不是Agent缺陷。

## 9. 下一阶段优化优先级
- F 规则校验问题：2例失败；先逐条复核对应观察，再设计最小修复及独立回归集。
- H 模型服务错误：1例失败；先逐条复核对应观察，再设计最小修复及独立回归集。

## 10. 已知限制
人工审核全部 NOT VERIFIED。审核者逐例核对原主题未漂移、每个工具动作是否基于观察且必要、每条自然语言事实是否被来源蕴含、拒绝理由是否明确；创作质量1–5分（1不可用、3可编辑、5可直接审片）。只允许署名人工填写results中的reviewer、reviewed_at、布尔字段与notes，原自动证据保持不变。
真人口播、产品真实性、版权、服务商独立账单、模型身份、线上传播效果均 NOT VERIFIED。20例一次采样没有置信稳定性保证；严格字符串工具可能误拒自然改写。报告保留全部失败和未执行例；离线验证不能替代真实模型结果。

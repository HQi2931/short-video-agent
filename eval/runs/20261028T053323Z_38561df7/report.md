# 短视频脚本 Agent 第一期效果评测

## 1. 评测目的
建立固定样本、可复算的效果基线，诊断下一阶段问题。本轮只新增eval模块，不修改核心执行循环。单次随机样本不代表稳定性结论。

## 2. 环境与模型配置
配置见 [environment.json](environment.json)。模型：deepseek-flash；请求上限 240；每例步骤上限 12、工具上限 9；每请求超时 45 秒。无自动重试，不设置金额预算；请求预算为硬上限，不能保证账单金额。
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
实际执行 0/20；尝试请求 0；报告Token合计 0。live批次完整验证：False。
[机器指标及分子分母](summary.json)；[逐例评分、重放、人工审核字段](results.json)。
| 指标 | 分子 / 分母 | 实际值 |
|---|---|---|
| case_acceptance_rate | 0 / 20 | 0.0000 |
| task_completion_rate | 0 / 20 | 0.0000 |
| duration_correction_success_rate | 0 / 4 | 0.0000 |
| tool_decision_appropriateness_proxy | 0 / 0 | NOT EVALUABLE |
| evidence_traceability_rate | 0 / 0 | NOT EVALUABLE |
| unsupported_claim_rate_proxy | 0 / 0 | NOT EVALUABLE |
| average_agent_steps | 0 / 0 | NOT EVALUABLE |
| average_tool_calls | 0 / 0 | NOT EVALUABLE |
| average_end_to_end_latency_seconds | 0 / 0 | NOT EVALUABLE |

| 案例 | 场景 | 状态 | 自动验收 | 原始证据 |
|---|---|---|---|---|
| holdout-01 | normal | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-02 | normal | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-03 | normal | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-04 | normal | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-05 | duration | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-06 | duration | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-07 | duration | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-08 | duration | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-09 | no_assets | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-10 | no_assets | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-11 | no_assets | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-12 | tool_failure | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-13 | tool_failure | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-14 | tool_failure | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-15 | unsupported | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-16 | unsupported | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-17 | unsupported | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-18 | brand | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-19 | brand | NOT RUN | NOT VERIFIED | offline_validation_only |
| holdout-20 | brand | NOT RUN | NOT VERIFIED | offline_validation_only |

## 6. 成功案例

## 7. 失败案例

## 8. 根因分析
| 类别 | 自动验收失败例数 | 观察到问题例数（含恢复） |
|---|---|---|
| A 检索问题 | 0 | 0 |
| B 工具选择问题 | 0 | 0 |
| C 无效重复调用 | 0 | 0 |
| D 时长估算或修改问题 | 0 | 0 |
| E 事实幻觉/未核实文本代理 | 0 | 0 |
| F 规则校验问题 | 0 | 0 |
| G 状态管理问题 | 0 | 0 |
| H 模型服务错误 | 0 | 0 |
分类为证据规则归因线索，不等同已确认根因。E中的未核实改写可能是误拒；B/C需人工判断是否必要重复。预期工具注入本身不是Agent缺陷。

## 9. 下一阶段优化优先级
未观察到最终验收失败；下面仅按实际出现后恢复的问题排序，不把恢复成功隐藏为零问题，也不将其称为任务失败。
本轮没有观察到可排序问题，需扩大独立样本；不编造2–3项高频缺陷。

## 10. 已知限制
人工审核全部 NOT VERIFIED。审核者逐例核对原主题未漂移、每个工具动作是否基于观察且必要、每条自然语言事实是否被来源蕴含、拒绝理由是否明确；创作质量1–5分（1不可用、3可编辑、5可直接审片）。只允许署名人工填写results中的reviewer、reviewed_at、布尔字段与notes，原自动证据保持不变。
真人口播、产品真实性、版权、服务商独立账单、模型身份、线上传播效果均 NOT VERIFIED。20例一次采样没有置信稳定性保证；严格字符串工具可能误拒自然改写。报告保留全部失败和未执行例；离线验证不能替代真实模型结果。

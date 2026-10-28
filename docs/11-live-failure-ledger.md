# 历史真实运行失败与恢复台账

日期：2026-10-28（Asia/Shanghai）。本台账在第三轮真实评测仍运行时独立整理，仅读取此前的examples、eval/runs及eval/decision-v2证据；未读取第三轮live结果或Trace。机器明细见 [historical-failure-ledger.json](../eval/final-v3/historical-failure-ledger.json)。

## 统计边界与完整计数

按完整Trace的SHA-256去重，共73次历史真实运行、440条请求和440条响应。对同一Trace生成的manifest、summary、partial结果与重评分不增加运行数；同一案例在两个版本真实调用则分别计数。Mock与复制的baseline-source不纳入。每个Trace路径、指纹、原评分来源、逐步错误及离线诊断都保留在JSON中。

| 历史批次 | 唯一运行 | completed | 合理needs_info | failed | incomplete | 原场景验收 | 响应 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 早期examples验证 | 13 | 10 | 3 | 0 | 0 | 12/13 | 77 |
| 第一期固定集 | 20 | 16 | 3 | 0 | 1 | 19/20 | 140 |
| 第二期固定集优化版 | 20 | 17 | 3 | 0 | 0 | 20/20 | 114 |
| 第二期独立集baseline | 10 | 6 | 2 | 2 | 0 | 8/10 | 60 |
| 第二期独立集optimized | 10 | 6 | 2 | 2 | 0 | 8/10 | 49 |
| 合计 | 73 | 55 | 13 | 4 | 1 | 不混合为单一效果指标 | 440 |

其中真正终态失败/未完成5次；另有1次脚本完成但未触发原本要验证的修订行为。13次needs_info均符合对应缺信息/无素材标准，不算失败，也不算脚本任务完成。55次completed中54次达到该次全部行为验收，1次属于下述未触发记录。这些批次混合了重复输入、不同版本和负向场景，汇总数量用于证据审计，不能解释为独立泛化成功率。

## 五次真实终态失败或未完成

| 批次 / Trace | 实际路径 | 运行时估时 / 目标 | 最终结论 |
|---|---|---|---|
| 第一期固定集 / [holdout-20](../eval/runs/20261028T052239Z_743fa464/traces/holdout-20.json) | search→draft→duration→连续改稿→duration→rules | 20.64 → 18.25 / 20 秒 | incomplete：12/12步耗尽；第4步修订已足够短，随后无反馈反复改稿，末尾两检查通过却无finish；门禁正确保留incomplete |
| 第二期独立集baseline / [validation-04](../eval/decision-v2/baseline-holdout/20261028T070040Z_6e7af480/traces/validation-04.json) | search→draft→duration→stop | 5.38 / 3.5 秒 | failed：4/12步后主动stop；将首稿两镜审片要求作为最终硬约束，无任何修订；第4步决策时仍有9步可用 |
| 第二期独立集baseline / [validation-05](../eval/decision-v2/baseline-holdout/20261028T070040Z_6e7af480/traces/validation-05.json) | search→draft→duration→stop | 5.74 / 3.5 秒 | failed：4/12步后主动stop；将首稿两镜审片要求作为最终硬约束，无任何修订；第4步决策时仍有9步可用 |
| 第二期独立集optimized / [validation-04](../eval/decision-v2/optimized-holdout/20261028T070030Z_4a49d4ed/traces/validation-04.json) | search→draft→duration→stop | 5.38 / 3.5 秒 | failed：4/12步后主动stop；将首稿两镜审片要求作为最终硬约束，无任何修订；第4步决策时仍有9步可用 |
| 第二期独立集optimized / [validation-05](../eval/decision-v2/optimized-holdout/20261028T070030Z_4a49d4ed/traces/validation-05.json) | search→draft→duration→stop | 5.74 / 3.5 秒 | failed：4/12步后主动stop；将首稿两镜审片要求作为最终硬约束，无任何修订；第4步决策时仍有9步可用 |

第二期独立集两失败在baseline与optimized各真实发生一次，合计4次执行失败，不能因case_id相同合并为2次运行。详见 [完整独立失败分析](10-independent-failure-analysis.md)。旧Trace和旧评分没有被重写。

## 一次完成但未触发预期行为

[live_overtime_round1](../examples/traces/live_overtime_round1.json) 的12秒目标最终completed，首次且唯一工具估时为10.41秒，未观察到“工具返回超时→模型按反馈改稿→重验”的路径。因此 [初始manifest](../examples/live-manifest.json) 保持all_expected_behaviors=false；补充4秒案例的成功不能回填此例。

需校正历史自然语言口径：此例第2步和第3步都是接受稿，第2步首稿在事后离线重算为12.18秒，第3步在尚无工具估时反馈时主动缩短为10.41秒，第4步才首次调用估时。旧文档的“首稿10.41秒”并不精确，应理解为“首次工具估时10.41秒”。12.18→10.41属于离线稿件比较，不能冒充真实超时反馈驱动的修订成功。原文和Trace均保留，本台账只新增校正说明。

## 已恢复的协议、参数、规则与工具事件

共21个非时长异常事件，分布于18次唯一运行，最终全部completed。分项为模型响应协议错误3次、draft参数校验拒绝3次、规则检查不通过6次、明确注入的工具故障9次。事件和运行数不同，因为同一运行可发生多类错误。

| 批次 / Trace | 步骤与事件 | 最终状态 |
|---|---|---|
| 早期examples验证 / [live_changed_assets_round1](../examples/traces/live_changed_assets_round1.json) | 步骤4 规则检查不通过（missing_fact_reference） | completed |
| 早期examples验证 / [live_tool_failure_round1](../examples/traces/live_tool_failure_round1.json) | 步骤3 注入工具故障（estimate_duration） | completed |
| 第一期固定集 / [holdout-01](../eval/runs/20261028T052239Z_743fa464/traces/holdout-01.json) | 步骤2 draft参数拒绝 | completed |
| 第一期固定集 / [holdout-03](../eval/runs/20261028T052239Z_743fa464/traces/holdout-03.json) | 步骤4 规则检查不通过（missing_fact_reference）；步骤6 模型响应协议错误（JSONDecodeError） | completed |
| 第一期固定集 / [holdout-12](../eval/runs/20261028T052239Z_743fa464/traces/holdout-12.json) | 步骤1 注入工具故障（search_assets） | completed |
| 第一期固定集 / [holdout-13](../eval/runs/20261028T052239Z_743fa464/traces/holdout-13.json) | 步骤3 注入工具故障（estimate_duration） | completed |
| 第一期固定集 / [holdout-14](../eval/runs/20261028T052239Z_743fa464/traces/holdout-14.json) | 步骤5 注入工具故障（check_brand_rules）；步骤6 规则检查不通过（missing_fact_reference） | completed |
| 第一期固定集 / [holdout-16](../eval/runs/20261028T052239Z_743fa464/traces/holdout-16.json) | 步骤5 规则检查不通过（missing_fact_reference） | completed |
| 第二期固定集优化版 / [holdout-12](../eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425/traces/holdout-12.json) | 步骤1 注入工具故障（search_assets） | completed |
| 第二期固定集优化版 / [holdout-13](../eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425/traces/holdout-13.json) | 步骤3 注入工具故障（estimate_duration） | completed |
| 第二期固定集优化版 / [holdout-14](../eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425/traces/holdout-14.json) | 步骤4 注入工具故障（check_brand_rules） | completed |
| 第二期固定集优化版 / [holdout-17](../eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425/traces/holdout-17.json) | 步骤4 规则检查不通过（missing_fact_reference） | completed |
| 第二期固定集优化版 / [holdout-19](../eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425/traces/holdout-19.json) | 步骤2 draft参数拒绝 | completed |
| 第二期独立集baseline / [validation-03](../eval/decision-v2/baseline-holdout/20261028T070040Z_6e7af480/traces/validation-03.json) | 步骤3 模型响应协议错误（JSONDecodeError） | completed |
| 第二期独立集baseline / [validation-08](../eval/decision-v2/baseline-holdout/20261028T070040Z_6e7af480/traces/validation-08.json) | 步骤7 注入工具故障（check_brand_rules） | completed |
| 第二期独立集baseline / [validation-09](../eval/decision-v2/baseline-holdout/20261028T070040Z_6e7af480/traces/validation-09.json) | 步骤4 规则检查不通过（unverified_text） | completed |
| 第二期独立集optimized / [validation-08](../eval/decision-v2/optimized-holdout/20261028T070030Z_4a49d4ed/traces/validation-08.json) | 步骤4 注入工具故障（check_brand_rules） | completed |
| 第二期独立集optimized / [validation-09](../eval/decision-v2/optimized-holdout/20261028T070030Z_4a49d4ed/traces/validation-09.json) | 步骤2 draft参数拒绝；步骤3 模型响应协议错误（Action ValidationError） | completed |

具体协议问题：第一期holdout-03返回两个连续JSON对象；独立baseline validation-03在JSON后追加非JSON标记；独立optimized validation-09的动作缺少必填公开理由，另一步把reason_summary放入draft arguments。空旁白/字幕镜头分别出现在第一期holdout-01和第二期固定holdout-19。以上均保留原始响应和拒绝记录，不能因最终恢复就隐去。

3次model_error是响应格式/校验问题，记录均有HTTP 200及响应内容；本范围没有观察到真实网络超时、鉴权错误或提供商服务中断。9次业务工具异常均明确注入，用于验证后续真实模型重试；不能当作真实线上工具故障率。保守字符串规则的unverified_text是未核实文本代理，不等同于人工证明的语义幻觉。

## 全部运行时超时反馈

共26次运行真正得到超时反馈，每次仅有一个超时检查事件；21次最终completed、5次为前述未完成/失败。这里不把尚未估时的首稿离线超时计为模型当时已观察。预设duration场景与其他场景偶然发生的超时分母仍按原评测报告分别计算。

| 批次 / Trace | 所有成功估时调用返回的秒数序列 | 最终状态 |
|---|---|---|
| 早期examples验证 / [live_changed_duration_round1](../examples/traces/live_changed_duration_round1.json) | 4.09 → 2.35 | completed |
| 早期examples验证 / [live_manual_overtime_20261028_130515](../examples/traces/live_manual_overtime_20261028_130515.json) | 7.64 → 2.35 | completed |
| 早期examples验证 / [live_normal_initial](../examples/traces/live_normal_initial.json) | 30.52 → 25.40 | completed |
| 早期examples验证 / [live_overtime_tight_round1](../examples/traces/live_overtime_tight_round1.json) | 7.64 → 2.35 | completed |
| 早期examples验证 / [live_sparse_round1](../examples/traces/live_sparse_round1.json) | 10.28 → 7.65 | completed |
| 早期examples验证 / [live_tool_failure_round1](../examples/traces/live_tool_failure_round1.json) | 30.91 → 23.18 | completed |
| 第一期固定集 / [holdout-05](../eval/runs/20261028T052239Z_743fa464/traces/holdout-05.json) | 5.52 → 2.76 | completed |
| 第一期固定集 / [holdout-06](../eval/runs/20261028T052239Z_743fa464/traces/holdout-06.json) | 6.18 → 2.98 | completed |
| 第一期固定集 / [holdout-07](../eval/runs/20261028T052239Z_743fa464/traces/holdout-07.json) | 5.74 → 2.76 | completed |
| 第一期固定集 / [holdout-08](../eval/runs/20261028T052239Z_743fa464/traces/holdout-08.json) | 5.52 → 2.76 | completed |
| 第一期固定集 / [holdout-12](../eval/runs/20261028T052239Z_743fa464/traces/holdout-12.json) | 20.64 → 8.28 | completed |
| 第一期固定集 / [holdout-15](../eval/runs/20261028T052239Z_743fa464/traces/holdout-15.json) | 20.62 → 17.68 | completed |
| 第一期固定集 / [holdout-17](../eval/runs/20261028T052239Z_743fa464/traces/holdout-17.json) | 20.12 → 11.03 | completed |
| 第一期固定集 / [holdout-19](../eval/runs/20261028T052239Z_743fa464/traces/holdout-19.json) | 20.62 → 18.27 | completed |
| 第一期固定集 / [holdout-20](../eval/runs/20261028T052239Z_743fa464/traces/holdout-20.json) | 20.64 → 18.25 | incomplete |
| 第二期固定集优化版 / [holdout-05](../eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425/traces/holdout-05.json) | 5.52 → 2.76 | completed |
| 第二期固定集优化版 / [holdout-06](../eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425/traces/holdout-06.json) | 6.18 → 2.98 | completed |
| 第二期固定集优化版 / [holdout-07](../eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425/traces/holdout-07.json) | 5.74 → 2.76 | completed |
| 第二期固定集优化版 / [holdout-08](../eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425/traces/holdout-08.json) | 5.52 → 2.76 | completed |
| 第二期固定集优化版 / [holdout-18](../eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425/traces/holdout-18.json) | 20.21 → 17.86 | completed |
| 第二期独立集baseline / [validation-01](../eval/decision-v2/baseline-holdout/20261028T070040Z_6e7af480/traces/validation-01.json) | 18.18 → 5.38 | completed |
| 第二期独立集baseline / [validation-04](../eval/decision-v2/baseline-holdout/20261028T070040Z_6e7af480/traces/validation-04.json) | 5.38 | failed |
| 第二期独立集baseline / [validation-05](../eval/decision-v2/baseline-holdout/20261028T070040Z_6e7af480/traces/validation-05.json) | 5.74 | failed |
| 第二期独立集baseline / [validation-08](../eval/decision-v2/baseline-holdout/20261028T070040Z_6e7af480/traces/validation-08.json) | 18.94 → 8.01 → 8.01 | completed |
| 第二期独立集optimized / [validation-04](../eval/decision-v2/optimized-holdout/20261028T070030Z_4a49d4ed/traces/validation-04.json) | 5.38 | failed |
| 第二期独立集optimized / [validation-05](../eval/decision-v2/optimized-holdout/20261028T070030Z_4a49d4ed/traces/validation-05.json) | 5.74 | failed |

## 离线补查发现的稿件规则问题

除运行时检查外，对每个接受稿使用该Trace的素材和规则快照离线重算。共7次运行、8份接受稿不满足原文/来源规则；此处的离线检查不进入运行时错误计数，JSON均标记runtime_observation=false。特别是第一期holdout-04的未批准画面描述在运行时品牌检查前已经被移除，不能伪称模型曾收到该条规则错误反馈。

| 批次 / Trace | 接受稿步骤 | 离线问题代码 |
|---|---|---|
| 早期examples验证 / [live_changed_assets_round1](../examples/traces/live_changed_assets_round1.json) | 2 | missing_fact_reference |
| 第一期固定集 / [holdout-03](../eval/runs/20261028T052239Z_743fa464/traces/holdout-03.json) | 2 | missing_fact_reference |
| 第一期固定集 / [holdout-04](../eval/runs/20261028T052239Z_743fa464/traces/holdout-04.json) | 2 | unverified_text |
| 第一期固定集 / [holdout-14](../eval/runs/20261028T052239Z_743fa464/traces/holdout-14.json) | 3 | missing_fact_reference |
| 第一期固定集 / [holdout-16](../eval/runs/20261028T052239Z_743fa464/traces/holdout-16.json) | 2 | missing_fact_reference |
| 第一期固定集 / [holdout-16](../eval/runs/20261028T052239Z_743fa464/traces/holdout-16.json) | 3 | missing_fact_reference |
| 第二期固定集优化版 / [holdout-17](../eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425/traces/holdout-17.json) | 2 | missing_fact_reference |
| 第二期独立集baseline / [validation-09](../eval/decision-v2/baseline-holdout/20261028T070040Z_6e7af480/traces/validation-09.json) | 2 | unverified_text |

## 一次历史评分器误判

第一期 [holdout-03](../eval/runs/20261028T052239Z_743fa464/traces/holdout-03.json) 最终completed，真实JSON协议错误后恢复。原评分器不能重放model_error步骤，导致原results为18/20验收、15/20完成；错误感知重评分核实恢复链后为19/20、16/20。两次rescore是对同一批20个Trace的离线复算，新增模型请求均为0，不能重复算40次真实运行。真实的协议错误仍在前述事件台账中。

证据按顺序保留： [原results](../eval/runs/20261028T052239Z_743fa464/results.json)、[首次错误感知重评分](../eval/runs/20261028T052239Z_743fa464/rescore_20261028T053239Z_d3fe90/results.json)、[第二期复核](../eval/runs/20261028T052239Z_743fa464/rescore_20261028T070111Z_506938/results.json)。这是一次评分假阴性修正，不是删除真实失败或修改通过标准。

## 零请求与预算中断

| 历史记录 | 实际情况 | 统计处理 |
|---|---|---|
| [20261028T052234Z_b52e9e25](../eval/runs/20261028T052234Z_b52e9e25/summary.json) | live_requested=false；20计划、0执行、20条offline_validation_only；0请求 | 离线数据校验，不是模型失败，也不纳入73次live |
| [20261028T053323Z_38561df7](../eval/runs/20261028T053323Z_38561df7/summary.json) | live_requested=false；20计划、0执行、20条offline_validation_only；0请求 | 离线数据校验，不是模型失败，也不纳入73次live |

两份零请求批次合计40条未执行案例行，只是离线数据校验。现存历史live中有1次max_steps终止：第一期holdout-20；没有观察到请求总预算或每例工具预算的budget_stop事件，没有发现残留仅JSONL而无最终Trace的历史live执行。不能把“未观察到预算中断事件”当作预算功能已经在真实服务上触发验证。

## 可审计性与限制

JSON列出全部73次运行，包含13次正确needs_info、所有失败和全部错误事件；包含每份Trace及来源评分文件的SHA-256，可与最终交付的保全审计交叉核对。已保留旧独立集参与开发诊断的状态边界。第三轮结果必须在最终报告中另加，不能根据此台账提前声称新的泛化能力。

本台账是对本地执行证据的独立整理，不是服务商签章；人工语义支持、创作质量、真人口播、真实素材版权和用户对模糊约束的最终解释仍为NOT VERIFIED。没有修改历史Trace、manifest、评分结果或原报告。

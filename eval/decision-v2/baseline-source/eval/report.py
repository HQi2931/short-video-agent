"""Generate a report beside immutable run evidence, never rewrite historical reports."""
from collections import Counter
from .metrics import CATEGORIES


DEFINITIONS = '''| 指标 | 分子 / 分母及失败处理 |
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
'''


def render(out,data,config,rows,summary):
    lines=['# 短视频脚本 Agent 第一期效果评测', '', '## 1. 评测目的',
           '建立固定样本、可复算的效果基线，诊断下一阶段问题。本轮只新增eval模块，不修改核心执行循环。单次随机样本不代表稳定性结论。',
           '', '## 2. 环境与模型配置',f'配置见 [environment.json](environment.json)。模型：{config["model"]}；请求上限 {config["max_requests"]}；每例步骤上限 {config["max_steps"]}、工具上限 {config["max_tool_calls"]}；每请求超时 {config["timeout"]} 秒。无自动重试，不设置金额预算；请求预算为硬上限，不能保证账单金额。',
           '数据集与源码均记录指纹；每次运行新建独立目录。现有适配器不支持seed/temperature配置，复现指执行流程和评分口径，不保证模型逐字重现。',
           '', '## 3. 数据集与场景分布', str(dict(Counter(c['scenario'] for c in data['cases']))),
           '[固定输入、期望、通过标准、素材及品牌规则](dataset.json)。20例全新输入与独立合成目录；未从历史trace抽取答案。后续调优应另建v2保留集。故障为明确的业务工具注入，模型后续选择为真实API决策。',
           '', '## 4. 指标定义', DEFINITIONS, '', '## 5. 实际测试结果',
           f'实际执行 {summary["executed"]}/20；尝试请求 {summary["requests_attempted"]}；报告Token合计 {summary["reported_total_tokens"]}。live批次完整验证：{summary["live_completed"]}。',
           '[机器指标及分子分母](summary.json)；[逐例评分、重放、人工审核字段](results.json)。',
           '| 指标 | 分子 / 分母 | 实际值 |','|---|---|---|']
    for key,value in summary.items():
        if isinstance(value,dict) and 'denominator' in value:
            rendered='NOT EVALUABLE' if value['value'] is None else f'{value["value"]:.4f}'
            lines.append(f'| {key} | {value["numerator"]} / {value["denominator"]} | {rendered} |')
    lines += ['','| 案例 | 场景 | 状态 | 自动验收 | 原始证据 |', '|---|---|---|---|---|']
    for r in rows:
        lines.append(f'| {r["case_id"]} | {r["scenario"]} | {r.get("status", "NOT RUN")} | {r.get("case_pass", "NOT VERIFIED")} | '+
                     (f'[Trace]({r["trace"]}) / [输出]({r["output"]})' if r.get('executed') else r['reason'])+' |')
    lines += ['', '## 6. 成功案例']
    lines += [f'- {r["case_id"]}：{r["scenario"]}，{r["status"]}；{r["behavior"]["observed_adaptations"]}。' for r in rows if r.get('case_pass')]
    lines += ['', '## 7. 失败案例']
    lines += [f'- {r["case_id"]}：{r["status"]}，分类 {r["failure_categories"]}；最后观察、全部动作及重放问题见对应Trace和results.json。' for r in rows if r.get('executed') and not r['case_pass']]
    lines += ['', '## 8. 根因分析', '| 类别 | 自动验收失败例数 | 观察到问题例数（含恢复） |','|---|---|---|']
    lines += [f'| {c} {n} | {summary["failure_case_frequency"][c]} | {summary["observed_issue_case_frequency"][c]} |' for c,n in CATEGORIES.items()]
    lines += ['分类为证据规则归因线索，不等同已确认根因。E中的未核实改写可能是误拒；B/C需人工判断是否必要重复。预期工具注入本身不是Agent缺陷。',
              '', '## 9. 下一阶段优化优先级']
    ranked=sorted(summary['failure_case_frequency'],key=lambda c:summary['failure_case_frequency'][c],reverse=True)
    priorities=[c for c in ranked if summary['failure_case_frequency'][c]][:3]
    for c in priorities:
        lines.append(f'- {c} {CATEGORIES[c]}：{summary["failure_case_frequency"][c]}例失败；先逐条复核对应观察，再设计最小修复及独立回归集。')
    if not priorities:
        observed=sorted(summary['observed_issue_case_frequency'],key=lambda c:summary['observed_issue_case_frequency'][c],reverse=True)
        observed=[c for c in observed if summary['observed_issue_case_frequency'][c]][:3]
        lines.append('未观察到最终验收失败；下面仅按实际出现后恢复的问题排序，不把恢复成功隐藏为零问题，也不将其称为任务失败。')
        for c in observed:
            lines.append(f'- {c} {CATEGORIES[c]}：{summary["observed_issue_case_frequency"][c]}例出现；复核具体Trace后再决定修复。')
        if not observed:
            lines.append('本轮没有观察到可排序问题，需扩大独立样本；不编造2–3项高频缺陷。')
    lines += ['', '## 10. 已知限制', '人工审核全部 NOT VERIFIED。审核者逐例核对原主题未漂移、每个工具动作是否基于观察且必要、每条自然语言事实是否被来源蕴含、拒绝理由是否明确；创作质量1–5分（1不可用、3可编辑、5可直接审片）。只允许署名人工填写results中的reviewer、reviewed_at、布尔字段与notes，原自动证据保持不变。',
              '真人口播、产品真实性、版权、服务商独立账单、模型身份、线上传播效果均 NOT VERIFIED。20例一次采样没有置信稳定性保证；严格字符串工具可能误拒自然改写。报告保留全部失败和未执行例；离线验证不能替代真实模型结果。']
    return ('\n'.join(lines)+'\n').replace('全部20例', f"全部{len(data['cases'])}例").replace('/20', f"/{len(data['cases'])}").replace('全部4个预设超时例', f"全部{sum(c['scenario']=='duration' for c in data['cases'])}个预设超时例")

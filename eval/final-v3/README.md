# 第三轮不可覆盖的原始证据

所有日期为2026-10-28，证据时间戳使用UTC。正式结论见根目录 [final-evaluation.md](../../final-evaluation.md)。本轮没有commit或push。

## 候选与数据版本

- `baseline-source/`：第三轮开始时的第二轮运行时与评分源码，24个文件；不含密钥。`baseline-source-manifest.json`记录原始指纹。
- `candidate-a-source/`：阶段约束和计时瓶颈提示的候选A，全部结果保留。A在固定集出现一次过度拒绝；没有用成功重跑覆盖它。
- 当前工作区：候选B，在A基础上仅补充“时长是上限”的通用提示。`candidate-b-source-manifest.json`在B运行前冻结。门禁、估时、规则、状态、步数与执行器代码均未改。
- `fresh-holdout-v3-contracts.json`：A的新15例。`fresh-frozen-manifest-v2.json`是首次请求前生效的冻结清单；初版输入与初版manifest均保留，取代关系见清单。
- `confirmation-v4/dataset.json`：B的另一组全新12例，首次请求前冻结于该目录manifest。A的新15例结果未用于调整B；B的补充来自旧固定集开发回归。各集的“盲测”只描述当时首次运行前未用于调优，运行后不能反复称全新。
- 第二轮独立集已参与开发诊断，A/B对它的运行只是开发回归。原固定集和原独立集输入、评分、Trace均不更改。

## 八个真实批次

| 目录 | 版本与用途 | 计划案例 |
|---|---|---:|
| `optimized-fixed/` | A固定集回归 | 20 |
| `diagnostic-v2/` | A旧独立集诊断回归 | 10 |
| `fresh-baseline/` | 第二轮源码，新15例对照 | 15 |
| `fresh-optimized/` | A，新15例 | 15 |
| `candidate-b-fixed/` | B固定集回归 | 20 |
| `candidate-b-diagnostic-v2/` | B旧独立集诊断回归 | 10 |
| `confirmation-baseline/` | 第二轮源码，新12例对照 | 12 |
| `confirmation-optimized/` | B，新12例 | 12 |

每次运行新建时间戳目录，含输入/规则/素材快照、environment、完整请求/响应、Trace JSON/JSONL、逐例输出、results/partial、summary、report。部分结果与完整结果属于同次运行，不增加样本数。console和退出码收据也保留。共114个计划真实运行；实际执行、成功、失败与请求次数以最终报告为准。模型配置相同，每例12步、9业务工具；固定20例240请求、诊断10例120请求、新15例180请求、新12例144请求，每请求45秒，无隐藏重试。

`comparison.json`为A对照；`final-comparison.json`为B对照。通用比较器沿用baseline_holdout/optimized_holdout字段，其实际数据集分别为新15/新12，不能误读为第二轮独立集。

## 验证范围

`check_fresh_contracts.py`是首次新集请求前冻结的补充验收器，B确认集复用原字节。分别输出原门禁通过数、补充契约通过数及交集；不改变runtime状态或历史分数。指定分镜/朗读、实际旁白/字幕事实、多素材使用等机械要求可检查；自然语言创作意图、风格和全部语义不作已验证声明。

`final_audit.py`不调用模型、不改Trace，拒绝覆盖审计输出。它重放工具/状态/当前版本反馈，核对JSONL、最终输出、模型响应动作、完成门禁、历史471文件指纹和密钥。`pre-live-audit.json`是中途快照：当时两个活跃JSONL尚无最终JSON导致总状态false；A结束后的`candidate-a-completed-audit.json`已通过166/166。最终全部批次证据以`final-audit.json`为准。

`baseline-pytest.*`为148项原基线；`final-pytest.*`是A的158项结果；`final-regression-b.*`是B的158项结果。这些是工程夹具，包含MockTransport，不能计入真实模型样本。`historical-failure-ledger.json`仅索引此前73次live；本轮台账另存，不把重放计成API调用。

## 复制命令

在项目根目录使用`.venv`，本地`.env`只在原项目根加载，不复制到源码快照。真实重跑另指定新的output-root。完整命令见最终报告；离线重放不产生API费用：

```powershell
.\.venv\Scripts\python.exe scripts/final_audit.py --output eval/final-v3/recheck-audit.json --pytest-report eval/final-v3/final-regression-b.xml
.\.venv\Scripts\python.exe eval/final-v3/check_fresh_contracts.py eval/final-v3/confirmation-optimized/20261028T073730Z_5cf3fdd6 --dataset eval/final-v3/confirmation-v4/dataset.json --output eval/final-v3/recheck-contracts.json
```

文件清单与SHA-256见`delivery-inventory.json`。密钥扫描是当前配置值和常见令牌格式核验，不是对全部未知历史凭证的绝对保证。

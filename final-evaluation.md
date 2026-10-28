# 短视频脚本 Agent：最终评估与交付前审计

日期：2026-10-28（Asia/Shanghai）。原始证据时间戳使用UTC。当前工作区为第三轮候选B；**本轮未commit、未push，等待用户最终审核**。

最终候选：固定集20/20验收、17/20脚本完成；已参与开发诊断的旧独立集10/10验收、8/10完成；全新12例确认集12/12验收、11/12完成。完整pytest **158项通过**。两例历史时长失败的修订闭环恢复；确认集相对旧源码的验收改善来自正确的无稿拒绝，不能称脚本完成率上升。

本轮包括候选A和B及其对照，**114次真实执行、683次请求尝试、682份HTTP响应**；其中一次真实ReadTimeout没有响应，随后恢复。服务商报告Token合计3,959,592，不等于账单费用。所有输入、输出、请求/响应、Trace、失败及中间候选结果均保留。详见 [证据目录说明](eval/final-v3/README.md)、[本轮完整台账](eval/final-v3/round3-all-live-ledger.json)。

## 1. 三轮开发和优化历程

| 轮次 | 问题、改进与实际结果 |
|---|---|
| 第一轮：效果基线 | 在原工程验收后新增评测模块，固定20例实跑；错误感知重评分为19/20验收、16/20完成，139项测试。唯一真实未完成holdout-20在首轮修订已足够短后无新反馈反复改稿，12步耗尽且未finish。原始18/20摘要、重评分及Trace都保留；重评分不增加模型调用。见[第一轮报告](docs/08-agent-evaluation.md)。 |
| 第二轮：决策和首次生成 | 增加版本绑定的当前检查/预算反馈、无反馈重复改稿约束、相同稿拒绝、修订反馈，保留严格门禁。148项测试；固定20/20验收、17/20完成。独立10例两版均8/10，两个3.5秒审片任务直接停止，尚未解决。见[第二轮报告](docs/09-decision-optimization.md)。 |
| 第三轮：约束理解与交付审计 | 先逐步分析两条完整失败Trace，再只改通用SYSTEM_PROMPT。A修复旧两例，却在固定holdout-04出现过度拒绝；A新15例与对照均15/15，步骤/耗时略增。基于该固定开发回归，B补充时长上限说明，再冻结另一组12例确认；最终固定20/20、诊断10/10、确认12/12。新增10项证据审计测试，最终158项通过。没有根据新集输出调参、换题或降低标准。 |

A的失败没有被B覆盖：源码保存于[candidate-a-source](eval/final-v3/candidate-a-source/manifest.json)，初始源码与正式B源码各有运行前指纹。两个候选属于第三轮内部修订，不把被淘汰候选从历史中删除。

## 2. 优化前后指标

指标沿用原`eval.metrics`。场景验收包括符合约定的安全拒绝；任务完成只计当前双检、重放、真实模型记录均通过的completed。时长修正的分母是预设duration案例，未触发也不算成功。所有未执行均留在分母。本轮8批全部实际执行、live记录核验通过，未执行数为0。

### 原固定20例：开发回归

| 指标 | 第一轮基线 | 第二轮 / 本轮前 | 第三轮A | 最终B |
|---|---:|---:|---:|---:|
| 场景验收 | 19/20 | 20/20 | 19/20 | 20/20 |
| 脚本任务完成 | 16/20 | 17/20 | 16/20 | 17/20 |
| 预设时长修正 | 4/4 | 4/4 | 4/4 | 4/4 |
| 平均决策步骤 | 7.00 | 5.70 | 5.35 | 5.75 |
| 平均业务工具调用 | 3.90 | 3.50 | 3.30 | 3.60 |
| 平均端到端秒数 | 29.1438 | 24.2003 | 19.2462 | 15.6275 |

B的步骤与工具数较第二轮略升，不能称所有指标均改善。固定集B的引用30/30可追溯，最终未核实文本代理0/17。原始数据见[最终固定集摘要](eval/final-v3/candidate-b-fixed/20261028T073520Z_5e8a2d91/summary.json)。

### 原独立10例：现为开发诊断集

| 指标 | 第二轮optimized | 第三轮A | 最终B |
|---|---:|---:|---:|
| 场景验收 | 8/10 | 10/10 | 10/10 |
| 脚本任务完成 | 6/10 | 8/10 | 8/10 |
| 预设时长修正 | 0/2 | 2/2 | 2/2 |
| 平均步骤 | 4.90 | 5.80 | 5.50 |
| 平均业务工具 | 2.90 | 3.40 | 3.40 |
| 平均端到端秒数 | 20.2712 | 23.9969 | 15.8172 |

原来的两例四步直接stop，现在由模型收到估时后修稿、重验两项并finish。B的validation-04为5.38→3.03秒，validation-05为5.74→2.98秒，均七步完成；A对应为5.38→3.38、5.74→2.98秒。B引用14/14，最终未核实文本代理0/8。该收益属于诊断回归，不能作为未见泛化成功率。见[最终诊断摘要](eval/final-v3/candidate-b-diagnostic-v2/20261028T073520Z_f0880670/summary.json)。

### 两组真正新案例：分别评价对应候选

| 指标 | 新15例：旧源码 | 新15例：A | 新12例：旧源码 | 新12例：最终B |
|---|---:|---:|---:|---:|
| 原门禁与补充契约交集验收 | 15/15 | 15/15 | 11/12 | 12/12 |
| 脚本任务完成 | 14/15 | 14/15 | 11/12 | 11/12 |
| 预设时长修正 | 4/4 | 4/4 | 3/3 | 3/3 |
| 平均步骤 | 6.7333 | 6.8000 | 6.3333 | 5.7500 |
| 平均业务工具 | 4.0000 | 4.0000 | 3.5833 | 3.4167 |
| 平均端到端秒数 | 30.4156 | 31.7091 | 25.9507 | 17.9469 |
| 引用可追溯 | 39/39 | 33/33 | 22/22 | 19/19 |
| 最终未核实文本代理 | 0/14 | 0/14 | 0/12 | 0/11 |
| 请求尝试 | 101 | 102 | 76 | 69 |

最终B确认集的confirm-09在检索后识别明确冲突并无稿请求补充；旧源码先生成8.49秒残稿，再请求补充，未通过原安全拒绝标准。两版都没有完成该不可满足的脚本任务，完成率没有提高。新15例没有观察到A成功率提升，且A出现真实ReadTimeout及格式恢复错误。**不能将两组相加成“最终B新27例全部通过”**，B没有重跑第一组15例。

[A对照](eval/final-v3/comparison.json)、[最终B对照](eval/final-v3/final-comparison.json)由同一个离线比较器生成。其中baseline_holdout/optimized_holdout是通用字段，在两份报告里分别指新15例/新12例，均不是原独立集。补充验收结果：[15例对照](eval/final-v3/fresh-baseline-contract-results.json)、[15例A](eval/final-v3/fresh-optimized-contract-results.json)、[12例对照](eval/final-v3/confirmation-baseline-contract-results.json)、[12例B](eval/final-v3/confirmation-optimized-contract-results.json)。

## 3. 所有真实失败与恢复记录

以下列出所有终态/场景验收失败，完整逐步错误、恢复和超时序列另在台账保留。合理needs_info不计脚本完成，也不一律称失败。

| 批次与案例 | 失败事实与保留结果 |
|---|---|
| 早期live_overtime_round1 | 最终completed，但首次工具估时10.41≤12秒，未发生工具超时反馈后的修订。此前首稿12.18→10.41仅是离线补算的无反馈改稿，不计修订闭环；原manifest仍false。 |
| 第一轮holdout-20 | 20.64→18.25秒；12步用尽，无finish，incomplete。不能因末尾两检查通过就改成completed。 |
| 第二轮validation-04，两版各一次 | 首稿5.38>3.50秒，检索→草稿→估时→stop，均failed，无任何修订。 |
| 第二轮validation-05，两版各一次 | 首稿5.74>3.50秒，同样四步stop。共四次真实执行失败，不能按两个case_id合并成两次。 |
| 第三轮A holdout-04 | 两步后无稿request_info，理由称单条纸质事实不足以支撑22秒功能介绍。按冻结固定集标准未通过，A固定验收/完成各退化一例。B新运行恢复完成，A原记录仍19/20、16/20。 |
| 第三轮确认集旧源码 confirm-09 | 用户要求最终完整朗读唯一长事实且≤3秒。实际稿8.49秒，估时失败后request_info保留稿，原门禁及契约交集11/12。B无稿拒绝通过该负向案例，不伪报completed。 |

详见[历史73次运行与全部失败台账](docs/11-live-failure-ledger.md)、[原独立失败九项诊断](docs/10-independent-failure-analysis.md)、[A开发回归分析](eval/final-v3/round3-development-regression.json)、[本轮114次运行台账](eval/final-v3/round3-all-live-ledger.json)。第一轮holdout-03曾被旧审计因已恢复JSON错误误判，重评分修正为通过，原分数没有删除。两份只做离线验证的早期批次共40条未执行、0请求，不混入真实失败或真实样本。

恢复过的真实问题没有因最终通过而隐去：共40个非时长异常事件，分布于30次运行，分别为16次注入故障、7次模型响应协议错误、4次无反馈改稿拒绝、9次规则拒绝、1次真实ReadTimeout和3次draft参数拒绝，最终均恢复。A fresh-04一次ReadTimeout后恢复，A fresh-07两次JSON错误恢复，若干标题/画面/引用检查失败后修正；B固定holdout-14/18规则失败后恢复，B诊断validation-10 JSON错误后恢复。全部569条相邻步骤观察反馈一致。明确fail_once的业务工具故障与真正网络异常分别记录。规则代理标记未核实文本不等于人工证明语义幻觉。

## 4. 固定、独立与新集的区别

原固定20例在第一轮形成，后续已用于开发；输入、素材和评分保持不变。原独立10例在第二轮前冻结，但本轮读取两失败用于诊断，因此现在明确是开发诊断集，旧8/10结果不重写。

A另建15个新案例，覆盖2.5–60秒、1/2/3相关素材、短长旁白、中英数字标点、6种平台、4种审片结构、无据声明、两种故障及无素材。[正式计划及标准](eval/final-v3/frozen-test-plan-contracts.md)在两版新集调用前固定；初版与补充契约版均保留，生效清单明确取代关系，没有覆盖初版。

B仅针对固定开发回归补充上限语义，随后另建12例全新确认集，[输入与计划](eval/final-v3/confirmation-v4/plan.md)在两版调用前固定。产品名、事实原文、完整输入与此前三集无重复，覆盖不同目标、素材数量、长短旁白、平台风格、无据声明、故障、严格修订及确实不可满足的最终朗读约束。数据作者未读取本轮模型输出，未调用模型生成筛选结果。

新集验收采用既有评分与预先冻结的补充契约交集，未改旧评分器。它额外检查指定首稿镜头和完整朗读、估时先于修订、最终事实进入旁白/字幕、多素材使用、指定长事实实际口播。确认集01/02的通用契约仍允许旁白或字幕，不能把它冒称所有口播风格要求都已自动验证。机械契约之外的语言意图仍需人工评审。

## 5. 实际技术改进

运行时代码的修改只有`src/llm_adapter.py`中的通用SYSTEM_PROMPT：区分临时审片结构和最终硬约束；解释逐镜下限、转场、旁白/字幕取较长者以及标点/不同文字语速；提醒只缩短较短一项可能无效、合并镜头不保证通过；在最终约束允许时选择核心完整事实，保留原引用，收到反馈后实质改稿并重验；时长是上限，无最低长度要求时不凑满，不能把材料事实冒充未证实功能。

没有案例ID、产品名或特定目标秒数分支。没有改变估时、检查、状态、执行器、schema、max_steps、完成或导出门禁；没有提高步数预算、自动选稿、自动检查、虚填时长或截断保留事实。`revision_feedback`原来已有当前/目标/差值/逐镜/引用，根因不是缺少这些数值。

原两例第4步决策时仍有9步，且完整反馈已进入请求；共同问题是把首稿两镜要求当成最终必须保留。仅合并两条完整旁白仍超时，因此必须在用户允许时选择一条核心事实，不能说“少一个镜头就保证成功”。报告中的离线反事实稿仅用于诊断，未计入live成功。

新增`final_audit.py`及10项篡改/脱敏/防覆盖测试属于验证工具；数据冻结、补充验收和台账没有增加Agent产品动作。89项冻结文件/评分源码核验及全部683次请求的系统提示、输入、源码版本匹配见[来源核验](eval/final-v3/freeze-and-provenance-audit.json)。

## 6. 已验证能力与最终回归

最终完整pytest：**158 passed in 3.14s，0失败、0错误、0跳过**，测试期间源码未变；[文本与源码指纹](eval/final-v3/final-regression-b.txt)、[JUnit](eval/final-v3/final-regression-b.xml)。原148项基线及A的158项结果另存。依赖检查见[pip check](eval/final-v3/pip-check.txt)。

最终[只读审计](eval/final-v3/final-audit.json)核对全部**220/220份Trace**，包含187份real_api和33份scripted_mock；重放0次模型调用。历史471文件指纹均不变。JSON/JSONL、输出、版本、真实模型动作及后续反馈一致；失败样本也纳入重放。中途审计因为两个尚未完成的活动JSONL而false的记录仍保留，A结束后166/166及最终全部完成后220/220分别另存。

| 要求 | 实际证据及边界 |
|---|---|
| 完成状态/事实门禁未退化 | agent/state/tools/schemas/tracing字节与本轮起点相同；完成后对象篡改、旧检查、无据声明、缺引用等对抗测试通过。 |
| 修改后两检查失效 | 原测试及live修订后current_checks清空、重新双检后才finish；工具错误也使检查失效。 |
| 素材引用完整 | 最终B三个批次分别30/30、14/14、19/19引用可追溯；全文仍执行原保守规则。 |
| 模型决定改稿且反馈进入后续决策 | 请求响应动作与实际draft一致，后续state重放一致；无自动稿件修复。A/B旧两例与新集7类预设修订分别核验，不能将A的4例与B的3例相加冒充B单集结果。 |
| max_steps有效 | 原预算边界测试保留；每例上限12，未提升；历史holdout-20真实触顶仍incomplete，当前运行未触顶不声称重新观察到live触顶。 |
| Mock/live严格区分 | pytest含MockTransport，全部是工程证据；发布的真实批次通过请求/响应/错误审计，重放和重评分不增加live次数。 |
| API Key与Git | 当前配置密钥精确匹配及常见令牌扫描通过，`.env`忽略且未跟踪；扫描工作区与可达Git blob。扫描不输出密钥、匹配行或密钥哈希；不把未知格式/已撤销凭证当作绝对排除。 |

## 7. NOT VERIFIED

- 人工语义蕴含、创作质量、平台风格、是否完整满足全部自然语言意图、受众体验、真人口播和实际剪辑时长。
- 新模型、其他服务商、真实产品/版权、生产流量、长期稳定性、故障概率、远程CI及跨Python版本兼容。
- 统计显著的泛化提升、时间下降的因果结论。每个版本一次随机采样，未固定seed/temperature；并行请求、缓存和服务负载干扰，A还含真实超时。小样本11/12→12/12不能外推可靠成功率。
- 服务商独立账单/调用证明；现有证据是本地HTTP记录与一致性审计。Token总量不是金额预算。
- 候选人本轮亲自编写、亲自运行、代码/语义审核、实际工时、评审账号访问及远程仓库本轮可见性复核。
- 最终B在A的15例上的重新实跑；该15例只证明A当时的结果，不能挪作B证据。

## 8. AI辅助与人工贡献

用户给出目标、不可放宽的门禁、保留历史和待审核再提交的约束。AI主任务协调三个AI子任务分别分析失败、创建未见案例和冻结契约、审计工程与证据；AI编写本轮提示和测试/审计工具、执行全部114次新live及pytest并撰写文档。新合成数据和报告均为AI辅助产物，没有把子任务分析当成人工独立评审。

早期3次候选人亲自执行API的记录仍单独保留，不据此声称本轮由本人执行。本人代码审核范围、意见、实际修改与投入时间仍待本人如实补充。详见[贡献记录](docs/04-ai-usage.md)。

## 9. 可复制的运行与验证命令

在`D:\Xiaoying\short-video-agent`，使用已有本地`.env`，不要复制密钥到快照目录。真实调用会使用服务商额度；下列output-root和报告名须保持全新，不覆盖已归档结果。

```powershell
.\.venv\Scripts\python.exe -m pytest -v --junitxml=eval/final-v3/recheck-pytest.xml
.\.venv\Scripts\python.exe scripts/final_audit.py --output eval/final-v3/recheck-audit.json --pytest-report eval/final-v3/recheck-pytest.xml
.\.venv\Scripts\python.exe -m pip check
git diff --check

# 当前B：固定集、已参与开发的诊断集、全新确认集复跑
.\.venv\Scripts\python.exe -m eval.run --live --dataset eval/dataset-v1.json --max-steps 12 --max-tool-calls 9 --max-requests 240 --timeout 45 --output-root eval/final-v3/recheck-fixed
.\.venv\Scripts\python.exe -m eval.run --live --dataset eval/decision-v2/holdout-v2.json --max-steps 12 --max-tool-calls 9 --max-requests 120 --timeout 45 --output-root eval/final-v3/recheck-diagnostic
.\.venv\Scripts\python.exe -m eval.run --live --dataset eval/final-v3/confirmation-v4/dataset.json --max-steps 12 --max-tool-calls 9 --max-requests 144 --timeout 45 --output-root eval/final-v3/recheck-confirmation

# 相同确认集的第二轮旧源码对照，原目录加载dotenv后才选源码
.\.venv\Scripts\python.exe -c "from dotenv import load_dotenv; load_dotenv('.env', override=False); import sys; sys.path.insert(0,'eval/final-v3/baseline-source'); from eval.run import main; raise SystemExit(main())" --live --dataset D:\Xiaoying\short-video-agent\eval\final-v3\confirmation-v4\dataset.json --max-steps 12 --max-tool-calls 9 --max-requests 144 --timeout 45 --output-root D:\Xiaoying\short-video-agent\eval\final-v3\recheck-baseline

# 零模型调用：复核归档确认集；新实跑时换成命令打印的新目录
.\.venv\Scripts\python.exe eval/final-v3/check_fresh_contracts.py eval/final-v3/confirmation-optimized/20261028T073730Z_5cf3fdd6 --dataset eval/final-v3/confirmation-v4/dataset.json --output eval/final-v3/recheck-contracts.json

# 零模型调用：复算已归档的最终对照；不改原比较报告
.\.venv\Scripts\python.exe -m eval.decision_compare --baseline-fixed eval/decision-v2/optimized-fixed/20261028T070019Z_4610d425 --optimized-fixed eval/final-v3/candidate-b-fixed/20261028T073520Z_5e8a2d91 --baseline-holdout eval/final-v3/confirmation-baseline/20261028T073730Z_4f35c3e3 --optimized-holdout eval/final-v3/confirmation-optimized/20261028T073730Z_5cf3fdd6 --output eval/final-v3/recheck-comparison.json
git status --short
```

`eval.run`每次自动创建全新目录。补充验收与审计器拒绝覆盖输出；pytest的JUnit需自行选择新名字。退出码1可能是已执行案例未通过，不能当作未运行：A固定批次、确认集旧源码均保留退出码1。

## 10. 最终待办与变更文件

本轮必要工程工作已完成；以下是交付审核待办，不代表已经验证：本人审阅新增提示、失败/恢复Trace及机械验收边界，确认阶段要求的最终解释；完成创作/语义与真人口播评审；补充本人贡献与工时、服务商账单和权限记录；核实最终提交范围及评审访问。若继续调优，新集视为已知数据，需再建未见集，不能复用当前分数声称盲测。

本轮修改：`src/llm_adapter.py`（仅Prompt）、`README.md`、`docs/04-ai-usage.md`、`docs/06-delivery.md`。新增：`scripts/final_audit.py`、`tests/test_final_audit.py`、`docs/10-independent-failure-analysis.md`、`docs/11-live-failure-ledger.md`、本报告及`eval/final-v3/`所有数据、快照、运行和审计证据。

逐文件SHA-256和准确数量见[delivery-inventory.json](eval/final-v3/delivery-inventory.json)。进入本轮时已有未提交的第二轮agent/replay/eval变更，起始状态保留于[starting-worktree.json](eval/final-v3/starting-worktree.json)，不把它们误算成本轮新增。最终Git HEAD与起点一致；**没有stage、commit或push，等待用户最终审核后再提交**。

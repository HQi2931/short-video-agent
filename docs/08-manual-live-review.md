# 候选人亲自执行的 API 验证核对

日期：2026-10-28。操作者依据候选人在对话中的明确自述；AI核对本地新生成的请求/响应、工具观察、JSONL、结果文件，不新增模型调用。

配置模型与返回模型均为 `deepseek-flash`。三组共16条HTTP 200响应，未发现模型调用错误。动作/参数、下一轮完整状态、版本指纹、确定性工具结果、最终输出和事件链均通过核验。

| 场景 | 北京时间起止（来自Trace） | 实际结果 | 核验 |
|---|---|---|---|
| 正常生成 | 13:05:27–13:05:43 | 28.56秒≤30秒；时长和品牌检查均通过，completed | PASS |
| 无素材 | 13:07:57–13:08:04 | 三次不同查询均无结果，随后请求补充，needs_info | PASS |
| 超时修订 | 13:08:57–13:09:12 | 7.64秒超4秒，模型生成不同稿件，重估为2.35秒并检查通过，completed | PASS |

## 输入、输出与过程

| 场景 | 输入 | 输出 | Trace |
|---|---|---|---|
| 正常 | [normal.json](../examples/inputs/normal.json) | [结果](../examples/outputs/live_manual_normal_20261028_130515.json) | [JSON](../examples/traces/live_manual_normal_20261028_130515.json) / [JSONL](../examples/traces/live_manual_normal_20261028_130515.jsonl) |
| 无素材 | [no_assets.json](../examples/inputs/no_assets.json) | [结果](../examples/outputs/live_manual_no_assets_20261028_130515.json) | [JSON](../examples/traces/live_manual_no_assets_20261028_130515.json) / [JSONL](../examples/traces/live_manual_no_assets_20261028_130515.jsonl) |
| 超时 | [overtime_tight.json](../examples/inputs/overtime_tight.json) | [结果](../examples/outputs/live_manual_overtime_20261028_130515.json) | [JSON](../examples/traces/live_manual_overtime_20261028_130515.json) / [JSONL](../examples/traces/live_manual_overtime_20261028_130515.jsonl) |

无素材查询实际依次为“月球采矿激光雷达”“激光雷达”“月球探测 月面 传感器”。`needs_info`是该负向场景的预期结果，不表示生成了合格脚本。

这三组可作为候选人亲自执行API验证的记录；未据此推断本人亲自编写代码、运行pytest或阅读全部核心代码。以上请求起止时间不等于候选人总投入工时，工时仍按本人实际情况补充。

机器可读核对结果：[manual-live-review.json](../examples/manual-live-review.json)。

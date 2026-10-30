# 评估与限制

本次对唯一保留实现执行离线测试及真实记录重放，不新增付费模型请求。运行结果见 [pytest.txt](../examples/acceptance-current/pytest.txt)、[pytest.xml](../examples/acceptance-current/pytest.xml)、[validation.json](../examples/acceptance-current/validation.json)、[verification.json](../examples/acceptance-current/verification.json)和[audit.json](../examples/acceptance-current/audit.json)。

六组保留记录均为已执行真实API调用，Prompt与当前源码一致；产品资料是合成输入。完整输入/输出/JSON/JSONL见[manifest](../examples/acceptance-current/manifest.json)。

| 场景 | 记录名 | 预期与观察到的行为 |
|---|---|---|
| 正常 | production-02 | 双检通过后completed，总时长14.10秒 |
| 缺信息 | missing-info-20261030 | 缺时长，模型request_info，needs_info |
| 无素材 | holdout-09 | 不同查询均无素材后请求补充 |
| 工具失败 | holdout-13 | 注入估时故障，模型观察后重试，双检后完成 |
| 超时 | holdout-07 | 5.74秒超限，模型改稿后2.76秒，重检完成 |
| 规则失败 | holdout-17 | 无据效果被拒，模型改稿后两项复检完成 |

来源SHA保留原始字节，工具观察、版本及最终输出在离线重放中重算，未将成功状态当作修订证明。一次真实运行不能证明所有未来运行都成功。故障是显式注入，不冒称自然服务中断；Mock及MockTransport测试不计入真实模型效果。

测试保留无依据80%效果、伪造ID、检查失效、步数耗尽、协议错误、完成门禁、证据篡改和当前版本变更检测。旧审计入口依赖的测试已迁移至唯一版本入口，未删除业务安全断言。测试数量按本次实际报告读取，不沿用旧批次数量。

本次清理移除旧候选实现、归档ZIP、重复输出和过期报告，清理记录在delivery/CLEANUP.json；清理前备份在仓库外。manifest中的origin仅为原运行出处，不要求交付目录保留旧批次。当前六组保留了工具错误、超时及规则失败的中间状态，没有改写为全程成功。

限制：完整语义事实蕴含、真人口播/剪辑、长期稳定性、全部Python版本、其他模型及完整人工创作质量尚未验证。此前曾出现首稿不满足制作简报或步数耗尽的历史现象，不因删除重复批次而宣称长期成功率100%。本轮只证明保留证据与唯一当前实现一致。


## 本轮提交准备复核

独立只读代码审查与本地复测未发现阻塞此前题面要求的核心实现缺陷。首次使用受限系统默认临时目录时，出现104项通过及63项临时目录setup错误；指定工作区basetemp后167项全部通过，属于临时目录权限限制。正式测试采用 `python -m pytest tests/ -q -p no:cacheprovider --basetemp runs/pytest-tmp`，最终实际输出仍以本目录链接的报告为准。本轮未新增付费模型调用。

所有Markdown文档的本地链接（包括素材包说明）均纳入本轮检查。第4题编号已确认；随后本人转录提供了正式题面、通用规则与提交规范，本轮已据此核对。网页本身未由助手直接读取，不能将转录核验描述成直接网页登录验证。不能将既有题面通过或本地包检查等同于已经在考试平台提交。

首次干净解压尝试发现runs/父目录缺失时，pytest的显式basetemp不能自动创建父目录；README已补充先创建runs/的步骤。该失败是交付命令前置条件问题，已保留失败尝试记录；最终包应以修正后的README再验证，不把失败记录改成成功。


## 正式转录题面最终对照

本人已提供第4题正式文本及完整通用规范，核心实现无需新增功能。核验结果与具体Trace步骤见 [决策对照](../examples/acceptance-current/DECISION-PATHS.md)。同为5.74秒的两次实际估时，在目标3.5秒时导致draft_script，在目标20秒时导致check_brand_rules；两组风格和其他条件不同，属于可观察路径对照，不宣称严格单变量A/B或统计泛化结论。

本轮再次核验最终输出的素材ID集合、逐镜scene_id秒数、逐镜求和与总时长、两项检查的当前版本及所有必需输出字段；实际检查结果记录到validation.json。六组记录已足以覆盖原题，不再新增付费模型调用。当前剩余的是实际commit、push及最终SHA对应，在提交前测试快照中尚未执行；本人随后已明确授权发布，最终SHA及远程同步结果在提交完成后独立核对，不在提交前报告中预填将来的结果。

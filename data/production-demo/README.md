# 合成制作素材包

这是独立于原data/assets.json的演示资料。晨栖随行杯、帧匣口袋灯、行页周计划本均为虚构产品，6份资料分别覆盖规格/内页和包装/配件；没有真实产品、实拍文件、用户数据或效果实验。

assets.json中fact_id对应的完整事实实际包含于source_text；其余文本说明可规划画面和证据缺口，不能自动作为产品声明使用。brand_rules.json沿用原禁止词和时长参数，另增加中性的景别、机位、动作、字幕、剪辑和声音指令。制作指令是待执行建议，未批准任何效率、保温、防漏、成绩或拍摄效果声明。

原工具仍逐字核对事实、引用和制作短语；没有修改Schema或跳过检查。制作信息通过现有visual表达，旁白与字幕继续由原工具估时。它不能代表实际拍摄动作耗时或真人口播效果。

当前真实样例的创作输入见[正常简报](../../examples/acceptance-current/inputs/normal.json)，实际输出见[分镜JSON](../../examples/acceptance-current/outputs/production-02.json)，完整Trace见[证据索引](../../examples/acceptance-current/manifest.json)。如需重新调用真实模型，用该输入并显式传入 `--data-dir data/production-demo`；这会新增API请求，不能保证再次得到完全相同脚本。原始输入数据与规则快照也保存在Trace配置中。

# 第4题 · 短视频脚本 Agent

基于合成产品素材与品牌规则生成有事实依据、满足目标时长上限的可编辑分镜JSON。CLI运行，Python原生Agent循环，无Agent框架。真实模式每一步由LLM选择动作；Mock只验证预设工程流程。

## 唯一版本与评审入口

当前唯一实现位于 `src/`。`VERSION.json`记录本次本地内容版本及SHA256，不冒称Git commit SHA。仓库内不保留旧候选实现、旧版本压缩包或重复评估报告。

- [需求](docs/01-requirements.md)、[方案](docs/02-solution.md)、[评估](docs/03-evaluation.md)、[AI使用](docs/04-ai-usage.md)、[复盘](docs/05-retrospective.md)
- [验收报告](delivery/REQUIREMENTS-CHECK.md)、[提交状态](delivery/SUBMISSION.md)、[清理记录](delivery/CLEANUP.json)
- [六组真实输入、输出、Trace索引](examples/acceptance-current/manifest.json) · [工具反馈与决策对照](examples/acceptance-current/DECISION-PATHS.md)
- [测试输出](examples/acceptance-current/pytest.txt)、[版本及证据核验](examples/acceptance-current/verification.json)、[最终审计](examples/acceptance-current/audit.json)

## 安装与运行

以下命令在仓库根目录执行，无需固定磁盘路径。Python 3.11+及Git（全套测试和历史扫描会调用Git），实际验证环境及依赖版本见 [validation.json](examples/acceptance-current/validation.json)。PowerShell：

```powershell
python -m venv .venv
New-Item -ItemType Directory -Force runs | Out-Null
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.main --mode mock --input-file examples/inputs/normal.json --trace-dir runs/traces --output-file runs/result.json
.\.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider --basetemp runs/pytest-tmp
.\.venv\Scripts\python.exe scripts/check_submission.py
```

依赖范围在requirements.txt，实际锁定快照在requirements-lock.txt。输入JSON包含topic、audience、platform、duration_seconds、style；`--data-dir`目录中放assets.json和brand_rules.json，默认使用data/。data/production-demo是另一组合成输入资料，不是另一个代码版本。

Mock的 `--scenario` 选择固定夹具，需搭配examples/inputs中同名输入，例如overtime。真实模式先复制.env.example为本地.env并填写LLM_API_KEY、LLM_BASE_URL和LLM_MODEL，然后将命令中的 `--mode mock` 改为 `--mode live`。真实调用产生费用；缺配置不会静默降级Mock。程序追加/chat/completions，API前缀必须完整。

默认12步，可通过--max-steps调整至1–100。退出码：0完成，2需补信息，3失败，4未完成，5启动错误。新增运行使用runs/，已验收的examples记录不会被默认命令覆盖。

## 校验与边界

check_submission.py在零模型调用下核对版本摘要、六组记录的输入/输出/JSONL、当前Prompt及实际反馈行为。Git属性保留交付文件原始字节，避免跨平台换行转换破坏摘要。改变已冻结内容会失败；只有审核新修改并重新验证后才应更新VERSION.json。

完整审计还会扫描Git历史，需要安装Git且当前目录是含.git的仓库。ZIP解压目录使用check_submission.py并查看已保存的audit.json；正式提交前在真实Git仓库中执行完整审计。报告须另存新路径，已有路径会被拒绝覆盖：

```powershell
.\.venv\Scripts\python.exe scripts/final_audit.py --output runs/audit.json --pytest-report examples/acceptance-current/pytest.xml
```

事实检查采用完整原文与批准非事实文案覆盖；未知改写会阻断。时长是包含字幕阅读和转场的工程估算，不能代替真人口播。编辑脚本必须重检。素材为合成资料，不证明真实产品效果或完整创作质量。

本人现已明确授权提交并推送本版本。实际投入约10小时，详见AI使用文档。题号已由本人确认为4；最终提交SHA必须在实际提交后生成，不能用本地内容ID或旧HEAD代替。仓库地址及提交前条件见提交状态页。


## 正式题面核对状态

第4题正文、通用考核规则和GitHub交付规范已由本人于2026-10-30从正式页面转录提供，本轮按该转录完成逐项核对。审查来源是本人提供的正式文本，并非助手直接读取了验证后的网页；个人考试链接、手机号和验证码不进入仓库。

本地功能、五场景、事实追溯、动态路径和必需材料均有实际证据。发布按本人本轮明确授权执行。最终commit SHA以本版本实际Git提交为准，可运行 `git rev-parse HEAD` 获取，交付时再与远程main核对；不能以本地内容ID或旧HEAD代替。

pytest临时目录在受限环境中可能不可写，上述命令先创建runs/，再将临时文件放到该忽略目录下；若单独运行测试，也要先执行该创建目录命令。默认临时目录的setup错误不作为业务断言失败；本次使用上述方式全套通过。

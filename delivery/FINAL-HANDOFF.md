# 候选B最终交付准备与提交范围

日期：2026-10-28（Asia/Shanghai）。状态：**等待本人审核；真实暂存区未改，没有commit或push。** 本轮只准备交付，没有新增模型调用，也没有改动Agent决策逻辑、Prompt、工具或完成状态门禁。当前完整候选B源码清单25/25与真实评测时一致。

## 当前版本与历史评测

| 项目 | 已保存结果 | 本次核对 |
|---|---|---|
| B固定集 | 20/20验收、17/20完成 | 一致 |
| B旧独立集诊断回归 | 10/10验收、8/10完成 | 一致；该集已参与开发 |
| B全新12例确认集 | 12/12验收、11/12完成 | 一致；正确无稿拒绝不算completed |
| A新15例及对照 | 均15/15验收、14/15完成 | 保留，不能冒充B新27例 |
| 第三轮全部8批 | 114次live、683次请求尝试、682响应 | 一致；一次真实ReadTimeout无响应 |
| 历史及第三轮Trace | 220份：187 real_api、33 scripted_mock | 完整离线重放，不新增模型调用 |

[最终评估](../final-evaluation.md)和全部历史失败/评分保持原字节；本轮只修订README、贡献待确认说明和交付说明。原508项清单是上一轮当时的快照，不覆盖它；本轮新清单单独保存。进入本轮时该旧清单全部507个可核验hash匹配。

## 需要stage的内容

审核通过后，以[stage-paths.txt](stage-paths.txt)的逐文件路径为准，[submission-manifest.json](submission-manifest.json)记录文件大小、工作区SHA-256及Git对象摘要。不要直接使用`git add .`，也不要只添加本轮文档。

| 范围 | 提交原因 |
|---|---|
| `.gitattributes` | 保留冻结证据原字节，修复Git换行转换导致干净检出hash失配的问题。 |
| `src/agent.py`、`src/llm_adapter.py`、`scripts/replay.py` | 从当前HEAD起尚未提交的第二轮/第三轮候选B实现；本轮没有再次修改它们。 |
| `scripts/final_audit.py`及3份新增测试 | 未提交的决策、评测和交付审计验证。 |
| README、docs/04、docs/06、docs/08–11、final-evaluation.md | 运行、贡献归属、历史报告、全部失败及最终评估。 |
| `eval/`的非忽略文件 | 数据/标准冻结、基线与A源码快照、三轮完整运行、原始Trace/JSONL、失败、指标与来源指纹。 |
| 清单所列`examples/`文件 | 按原字节保存现有历史证据；只是Git原先换行转换的表示差异，本地Trace/结果未重写。 |
| `delivery/` | 本次检查收据、人工审核表、准确stage清单、建议提交说明及临时检出验证工具。 |

在提交前先检查清单；本人填写人工审核表后若产生新改动，应重新生成文件清单并再次核对。`src/agent.py`等相对HEAD有差异不表示本轮改了核心，起始状态和候选B完整hash可以区分归属。

## 证据体积与保留决定

本轮开始时：现有Git跟踪224文件约5.16 MiB，未跟踪约54.43 MiB，`eval/`约54.33 MiB，最大单文件864,770字节、不足1 MiB。174份未跟踪JSONL占约23.07 MiB，但它们是追加事件与JSON一致性重放的必要证据，不是可直接丢弃的副本。

12份`results.partial.json`与最终results逐字节相同，共约0.95 MiB；全体重复文件冗余约1.65 MiB。它们仍被历史/冻结/原交付清单引用。删减收益有限，却需要额外还原层或破坏可审计依赖，因此保留现有证据。没有额外打ZIP副本、没有引入LFS，也不删除旧失败。Git对文本与重复对象本身压缩；[临时候选树](review/checkout-validation.json)实测完整Git包为2,295,273字节，约2.19 MiB，该值不是最终推送网络包的保证。

建议继续忽略：`.env`及其他本地密钥文件、`.venv/`、`__pycache__/`、`*.pyc`、`.pytest_cache/`、`.coverage`、`htmlcov/`、`dist/`、`*.egg-info/`。这些已有`.gitignore`覆盖。不要新增磁盘/编辑器缓存、临时索引、pack或临时检出目录；本次临时内容放在系统临时目录并清理，只有验证收据保留。

## Git换行问题与验证

原属性`*.json/jsonl/md/txt text eol=lf`会把Windows生成的CRLF证据转换成LF。历史471文件清单、数据冻结和源码快照都用原始SHA-256；转换后即使JSON语义相同，完整性核验也会失败。

本轮仅修改交付配置：`eval/**`、`examples/**`、`delivery/**`及docs/08–11禁止Git文本转换，保留原字节。旧Git索引的文件状态缓存不会因属性改变自动失效；第一次临时检出证实168个既有examples仍可能沿用旧LF对象，见[失败收据](review/checkout-attempt-03.json)。在明确关闭文本转换后，只对[raw-byte-paths.txt](raw-byte-paths.txt)列出的冻结路径强制重新索引，写入原始工作区字节，不改本地文件。不要运行全仓库批量换行格式化、全仓库renormalize或重写结果/清单。

临时暂存预检还发现原失败测试收据`eval/evidence/completion-regression-tests.txt`第12行含捕获的行尾空格；保留该原始收据，并只对这一文件明确设置空白例外。预检失败收据[checkout-attempt-02.json](review/checkout-attempt-02.json)保留，没有修改原测试输出；代码和其他文件仍执行空白检查。

[临时检出工具](verify_checkout.py)使用隔离的索引和对象目录、`core.autocrlf=true`，没有改真实暂存区、没有创建提交。它核对候选树Git对象、完整候选B与冻结证据原字节，并在检出副本重新运行pytest和final_audit。验证收据与最终stage清单随后加入，不挪用该验证声称已存在远程CI或已推送。

实际临时检出1,035文件，968份既有eval/examples证据逐字节匹配、候选B 25个源码指纹匹配；检出副本pytest为158项通过（3.28秒），220/220 Trace审计通过。普通Git配置文本可按Git规则转换换行，冻结证据另做原始字节核验，不把两种保证混淆。临时仓库没有复制`.env`；当前密钥的精确扫描在原工作区另行执行。

## 最新检查及安全边界

- [本地验证](review/validation.json)：pytest、pip check、git diff --check的退出码、环境和候选B完整指纹。
- [本次最终审计](review/final-audit.json)：完整Trace重放、471旧文件、运行时门禁、当前配置密钥及可达Git历史扫描。
- [干净检出验证](review/checkout-validation.json)：字节保留、检出后的pytest和220份Trace审计；只用临时仓库。
- [一致性审阅](review/consistency-review.json)：候选B完整源码25/25、全部78个指标表格数值及Mock/live归属一致。
- [敏感信息与贡献复核](review/sensitive-and-contribution-review.json)：跟踪文件、当前索引、可达历史与UTF-16内容的补充扫描。
- [证据范围审阅](review/evidence-scope.json)：目录/文件大小、重复与冻结依赖。

没有发现配置密钥、常见凭证、私钥或含凭证URL；`.env`被忽略且未跟踪。当前已知密钥与常见格式扫描不能排除全部未知/已撤销凭证。Git历史有一组作者姓名/邮箱，本机路径和账号也出现在环境元数据中，需要本人确认披露；本轮没有改写历史身份、远程权限或历史结果。

本地HEAD与缓存的`origin/main`均为`6ff258c0eef6c2d653ce15c022a35b1fd2f90832`，当前没有已创建待推送的新提交。本轮未fetch或查询远程，因此不把缓存状态当作此刻远程状态；未来提交后才会有新的待推送提交。

## 本人必须确认

按[HUMAN-REVIEW.md](HUMAN-REVIEW.md)执行并据实填写。贡献归属、实际代码阅读/修改、本人运行命令、语义/创作/口播评审、实际工时、API权限/账单、身份/隐私披露、评审权限和最终提交授权均待本人确认。AI没有替本人勾选或签名。

不变的NOT VERIFIED包括跨模型/服务商、生产稳定性、统计显著泛化收益、真人语速与剪辑、远程CI、仓库本轮可见性及评审访问。

## 审核后才执行的提交命令

以下仅供本人审核完成后使用，**本轮未执行真实stage、commit或push**：

```powershell
cd D:\Xiaoying\short-video-agent
Get-Content delivery/stage-paths.txt
git --literal-pathspecs add --pathspec-from-file=delivery/stage-paths.txt
git --literal-pathspecs add --renormalize --pathspec-from-file=delivery/raw-byte-paths.txt
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
git status --short
git commit -F delivery/commit-message.txt
```

[commit-message.txt](commit-message.txt)只是建议提交说明。实际stage之后仍应检查没有`.env`、虚拟环境、缓存和意外私密文件；若本人尚未完成必要审核，继续等待，不将本表的未确认状态改成已通过。

提交后复核（报告名必须新建，不覆盖旧证据）：

```powershell
git show --stat --oneline HEAD
git show --format=fuller --no-patch HEAD
git status --short
.\.venv\Scripts\python.exe -m pytest -q --junitxml=delivery/review/postcommit-pytest.xml
.\.venv\Scripts\python.exe scripts/final_audit.py --output delivery/review/postcommit-audit.json --pytest-report delivery/review/postcommit-pytest.xml
.\.venv\Scripts\python.exe -m pip check
git diff --check
git rev-list --left-right --count HEAD...origin/main
```

提交后复核会产生新的`postcommit-*`收据，Git可能将它们列为未跟踪文件；这不等于源代码变更或测试退化。保留并单独审核这些新收据，不自动提交，也不为得到空的status删除旧证据。

如需复核Git换行再现，可重新运行临时检出工具，四个输出名都须全新：

```powershell
.\.venv\Scripts\python.exe delivery/verify_checkout.py --output delivery/review/recheck-checkout.json --pytest-xml delivery/review/recheck-checkout-pytest.xml --pytest-text delivery/review/recheck-checkout-pytest.txt --audit-output delivery/review/recheck-checkout-audit.json
```

所有复核均不调用真实模型。是否推送及远程访问权限继续等待用户决定，本清单不包含本轮推送操作。

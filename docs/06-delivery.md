# GitHub 交付

## 仓库与授权

用户提供仓库地址并明确要求提交：

- 仓库：https://github.com/HQi2931/short-video-agent
- 远程 origin：https://github.com/HQi2931/short-video-agent.git
- 本地分支：main
- 可见性：Private，已通过 GitHub 查询确认。

最初检查时远程为空、可见性为 Public。按既定保密要求，已先改为 Private，再进行代码上传。本次提交使用现有本地 Git 作者配置，不据此声称候选人已完成代码审核或亲自编写全部代码。

实际提交以[仓库提交历史](https://github.com/HQi2931/short-video-agent/commits/main)为准，不在文档中手写未验证的 SHA。评审账号尚未提供，未发出邀请。

## 本地复核与后续更新

在项目根目录可执行：

```powershell
git status --short
git check-ignore .env
git check-ignore .venv/Scripts/python.exe
.\.venv\Scripts\python.exe scripts/audit.py
.\.venv\Scripts\python.exe scripts/audit.py --require-live
.\.venv\Scripts\python.exe scripts/acceptance_audit.py
git diff --check
```

本次离线测试与 CLI 证据已保存，详见 `docs/03-evaluation.md`。后续修改后，按修改范围运行必要测试，再提交更新：

```powershell
git add README.md requirements.txt requirements-lock.txt pyproject.toml .env.example .gitignore .gitattributes src data tests scripts docs examples
git diff --cached --check
git diff --cached --stat
git commit -m "Update short-video script agent"
git push origin main
```

核对当前本地与远程提交：

```powershell
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

真实 API 测试后复查 Trace 中的用户输入、素材与服务商错误信息；自动脱敏与模式扫描不能替代本人审核。`.env`、虚拟环境与缓存不应进入提交。

## 仍需本人完成

- 补充 `docs/04-ai-usage.md` 的本人审核、实际修改与实际工时记录。
- 复核已保存的 live 验证证据：`examples/live-report.md`、`examples/live-summary.json`；本次已覆盖8类场景并有两条以上真实不同路径，其他服务商与稳定性仍未验证。
- 按考核方提供的准确账号，在 GitHub Settings → Collaborators → Add people 中邀请评审，确认对方接受并能访问。
- 保持仓库为 Private，按考核要求处理提交后的保密事项。

GitHub CI 尚未配置或执行，不应声称远程 CI 已通过。

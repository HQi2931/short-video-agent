# GitHub 交付

## 当前审核状态（2026-10-28）

第三轮工作仅保存在本地，**本轮未commit、未push**。用户要求最终审核后再提交；下方历史上传记录不代表本轮已经授权提交。最新质量结果、保留失败、待办与实际命令见 [final-evaluation.md](../final-evaluation.md)。本轮未调用远程仓库接口，Private状态沿用早期核实记录，不能声称已重新核验。

当前候选B的交付准备结果和逐文件stage范围见[最终交付清单](../delivery/FINAL-HANDOFF.md)。实际暂存区保持不变；原始证据采用Git字节保留属性，避免换行转换破坏已冻结SHA-256。不要对证据批量格式化或对全仓库renormalize；交付清单中的定向重新索引仅在文本转换已关闭后写入原始字节，以清除旧Git索引缓存影响。

## 仓库与授权

用户提供仓库地址并明确要求提交：

- 仓库：https://github.com/HQi2931/short-video-agent
- 远程 origin：https://github.com/HQi2931/short-video-agent.git
- 本地分支：main
- 可见性：早期GitHub查询确认为Private，本轮未重新查询。

最初检查时远程为空、可见性为 Public。按既定保密要求，已先改为 Private，再进行代码上传。本次提交使用现有本地 Git 作者配置，不据此声称候选人已完成代码审核或亲自编写全部代码。

实际提交以[仓库提交历史](https://github.com/HQi2931/short-video-agent/commits/main)为准，不在文档中手写未验证的 SHA。评审账号尚未提供，未发出邀请。

## 本地复核与后续更新

在项目根目录可执行：

```powershell
git status --short
git check-ignore .env
git check-ignore .venv/Scripts/python.exe
.\.venv\Scripts\python.exe -m pytest -v --junitxml=eval/final-v3/review-pytest.xml
.\.venv\Scripts\python.exe scripts/final_audit.py --output eval/final-v3/review-audit.json --pytest-report eval/final-v3/review-pytest.xml
git diff --check
```

早期audit.py/acceptance_audit.py会更新examples的派生汇总，本轮为保留历史未执行；当前复核使用上面的只读final_audit。早期离线测试与CLI证据见`docs/03-evaluation.md`。以下仅供用户最终审核并明确同意提交后参考，本轮未执行：

```powershell
git --literal-pathspecs add --pathspec-from-file=delivery/stage-paths.txt
git --literal-pathspecs add --renormalize --pathspec-from-file=delivery/raw-byte-paths.txt
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

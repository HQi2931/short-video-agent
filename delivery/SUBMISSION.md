# 第4题 · GitHub交付信息

| 字段 | 内容 |
|---|---|
| 题号 | **4** |
| 项目 | 短视频脚本Agent |
| GitHub URL | [HQi2931/short-video-agent](https://github.com/HQi2931/short-video-agent) |
| 最终commit SHA | 对本交付提交执行 `git rev-parse HEAD` 得到的完整40位SHA；发布后交付回执提供实际值 |
| 内容清单 | VERSION.json；本地内容ID不等于Git commit SHA |
| 本人投入 | 约10小时；代码审核、结果审核、架构审核和边界设定，未单独记录分项用时 |
| 运行与证据 | README中的CLI命令、examples/acceptance-current六组真实记录和实际测试报告 |

本人已转录提供正式第4题与通用交付要求，本地验收通过；随后明确授权“提交、推送并取得对应的最终commit SHA”。本轮按该授权发布到现有仓库main，保持单一交付实现；不提交密钥、个人考试链接、缓存、临时测试目录或本地备份，也不执行考试网页表单的最终提交。

最终SHA不硬编码到其自身提交的文件中，避免文件内容与commit哈希自引用。取得本版本后执行：

```powershell
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

发布完成时两者应相同；考试提交填写题号4、上述GitHub URL和这个完整SHA。本地原基线62c46439830ac6eba99e5b6ad02ddf779a32aa22及发布前远程6ff258c0eef6c2d653ce15c022a35b1fd2f90832均不是本次最终交付SHA。

README与docs/01–05为当前材料。验收报告和examples中的执行报告是commit前的真实技术检查快照；实际commit及远程同步结果在发布后另行核对。本仓库此前查询为PUBLIC，发布后还需确认评审可读性；若日后改为私有，需授予指定评审账号读取权限。

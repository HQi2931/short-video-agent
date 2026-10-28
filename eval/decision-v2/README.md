# 第二阶段原始证据

- `baseline-source/`：修改前的运行时、Prompt、工具、状态、重放和评分源码。仅通用run/dataset/report入口复制了本轮的数据选择/动态总数支持，以在旧运行时运行新保留集。无密钥文件。
- `frozen-manifest.json`：保留集与baseline源码冻结指纹。冻结后未据新结果调参。
- `holdout-v2.json`：10例独立数据；预先冻结，失败仍完整计入。双镜审片的两个超短案例失败不从分母排除。
- `optimized-fixed/`：原固定20例优化版新真实调用。
- `baseline-holdout/`、`optimized-holdout/`：独立10例的修改前后真实调用。
- 各运行目录有environment、dataset、results、summary、逐例output和完整traces JSON/JSONL。report.md沿用第一阶段模板；第二阶段解释、实际分母、结论以09文档和comparison.json为准。
- `regression-tests.txt`：实际pytest输出。不是LLM评测。
- 历史固定集baseline保留在 `../runs/20261028T052239Z_743fa464/` 及该目录的重评分子目录，未覆盖。

新批次采用相同模型及限制，一次采样。并行请求存在缓存/负载干扰，不能从延迟差认定因果收益。默认温度未显式固定；人工语义审查未完成。拒绝与未交付均不计任务完成。

运行固定集：`python -m eval.run --live --max-steps 12 --max-tool-calls 9 --max-requests 240 --timeout 45 --output-root eval/decision-v2/optimized-fixed`。

运行保留集：同一命令增加 `--dataset eval/decision-v2/holdout-v2.json`，指定新的output-root。baseline批次在baseline-source作为工作目录运行冻结源码，使用原项目dotenv（不得复制密钥进证据目录）。不应重复本轮运行覆盖原目录。

离线对照：`python -m eval.decision_compare --baseline-fixed <历史重评分目录> --optimized-fixed <新固定集目录> --baseline-holdout <旧源码保留集目录> --optimized-holdout <新源码保留集目录> --output eval/decision-v2/comparison.json`。此命令零模型调用，首稿估时及规则审计标为offline-first。

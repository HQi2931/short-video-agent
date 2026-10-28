"""Collect existing real-run evidence; preserve failures and untriggered paths."""
import json
from datetime import datetime, timezone
from pathlib import Path

from evidence import inspect_behavior, inspect_live_calls
from run_examples import CASES
from replay import replay_files

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CASES = ("normal", "missing_info", "no_assets", "tool_failure", "overtime", "changed_duration", "changed_assets", "sparse")


def summarize_live(quiet: bool = False) -> dict:
    manifest_path = ROOT / "examples/live-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"runs": []}
    known = {r["run_id"]: r for r in manifest["runs"]}
    inputs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "examples/inputs").glob("*.json")}
    runs = []
    for path in sorted((ROOT / "examples/traces").glob("live_*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        if trace.get("mode") != "live":
            continue
        row = known.get(trace["run_id"], {})
        matches = [name for name, value in inputs.items() if value == trace["input"]]
        input_name = Path(row["input"]).stem if row else (matches[0] if len(matches) == 1 else "unclassified")
        case = row.get("case", "overtime" if input_name == "overtime_tight" else input_name)
        integrity = inspect_live_calls(trace)
        execution_replay = replay_files(path)
        output_path = ROOT / "examples/outputs" / path.name
        output_matches = output_path.exists() and json.loads(output_path.read_text(encoding="utf-8")) == trace["final_result"]
        usage = sum((s.get("model_call", {}).get("response", {}).get("usage") or {}).get("total_tokens", 0)
                    for s in trace.get("steps", []))
        runs.append({
            "run_id": trace["run_id"], "case": case,
            "input": f"examples/inputs/{input_name}.json" if input_name != "unclassified" else None,
            "trace": path.relative_to(ROOT).as_posix(),
            "events": path.with_suffix(".jsonl").relative_to(ROOT).as_posix(),
            "output": output_path.relative_to(ROOT).as_posix(), "output_matches_trace": output_matches,
            "status": trace["final_status"], "expected_status": CASES.get(case),
            "status_matches": trace["final_status"] == CASES.get(case),
            "actions": [s["action"] for s in trace.get("steps", [])],
            "target_seconds": trace["input"].get("duration_seconds"),
            "real_model_responses": trace.get("real_model_responses", 0), "recorded_total_tokens": usage,
            "live_call_integrity": integrity, "execution_replay": execution_replay, **inspect_behavior(case, trace),
        })
    valid = [r for r in runs if r["behavior_verified"] and r["live_call_integrity"]["verified"]
             and r["execution_replay"]["verified"] and r["output_matches_trace"] and r["status_matches"]]
    coverage = {case: [r["run_id"] for r in valid if r["case"] == case] for case in REQUIRED_CASES}
    distinct = len({tuple(r["actions"]) for r in valid})
    adaptations = sorted({a for r in valid for a in r["observed_adaptations"]})
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "mode": "live",
        "source_batch_manifest": "examples/live-manifest.json" if manifest_path.exists() else None,
        "runs": runs, "required_case_coverage": coverage,
        "all_required_cases_covered": all(coverage.values()),
        "distinct_verified_live_paths": distinct, "observed_adaptations": adaptations,
        "live_requirement_verified": distinct >= 2 and bool(adaptations),
        "duration_correction_verified": "duration_revision" in adaptations,
        "non_triggered_or_failed_runs": [r["run_id"] for r in runs if r not in valid],
        "total_real_model_responses": sum(r["real_model_responses"] for r in runs),
        "recorded_total_tokens": sum(r["recorded_total_tokens"] for r in runs),
        "notice": "Coverage can use supplemental runs. Original batch results and every untriggered/failed run remain unchanged.",
    }
    (ROOT / "examples/live-summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 真实模型验证报告", "",
        f"生成时间（UTC）：{report['generated_at_utc']}。以下结果由现有运行 Trace 汇总生成，不重新调用模型。", "",
        f"共 {len(runs)} 次运行，{report['total_real_model_responses']} 条实际模型响应；"
        f"覆盖 {len([v for v in coverage.values() if v])}/{len(REQUIRED_CASES)} 类场景，"
        f"核验到 {distinct} 条不同的有效动作路径。", "",
        f"响应 usage.total_tokens 累计：{report['recorded_total_tokens']}；未估算或声明实际账单金额。", "",
        "| run_id | 状态 | 目标秒数 | 实际估时序列 | 行为证据 | Trace |",
        "|---|---|---:|---|---|---|",
    ]
    for row in runs:
        estimates = " → ".join(f"{value:.2f}" for value in row["duration_estimates"]) or "—"
        evidence = ", ".join(row["observed_adaptations"]) or ("预期状态与检查" if row["behavior_verified"] else "预期修订未触发")
        lines.append(f"| {row['run_id']} | {row['status']} | {row['target_seconds'] or '未提供'} | {estimates} | {evidence} | [JSON](traces/{row['run_id']}.json) |")
    lines += [
        "", "## 核验范围", "",
        "逐轮核对 HTTP 200 记录、模型原始 JSON 与实际动作/参数、下一轮请求中的上一工具观察、输入与请求模型、最终输出和 Trace 一致性。",
        "这些是本地执行记录核验，不是服务商独立签章。pytest 的合成传输夹具不在此报告中。", "",
        "工具故障场景由 Runtime 明确注入一次业务工具异常；后续重试和改稿由真实模型选择。", "",
        "首轮 12 秒 overtime 输入的首稿即合格，因此原 batch 的 all_expected_behaviors=false 和非零退出码被如实保留。",
        "随后 4 秒补充输入用于覆盖超时修订，覆盖通过不改写原始未触发记录。", "",
        "完整机器可读结果见 [live-summary.json](live-summary.json)，初始批次见 [live-manifest.json](live-manifest.json)。",
        "候选人人工审核、实际工时、评审访问和远程 CI 仍不由此报告证明。", "",
    ]
    (ROOT / "examples/live-report.md").write_text("\n".join(lines), encoding="utf-8")
    if not quiet:
        print(json.dumps({k: v for k, v in report.items() if k != "runs"}, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    report = summarize_live()
    raise SystemExit(0 if report["all_required_cases_covered"] and report["live_requirement_verified"] else 1)

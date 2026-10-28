"""Run actual CLI processes and write an evidence manifest. No result fabrication."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from evidence import inspect_behavior, inspect_live_calls

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "normal": "completed", "missing_info": "needs_info", "no_assets": "needs_info",
    "tool_failure": "completed", "overtime": "completed", "unsupported_claim": "failed",
    "max_steps": "incomplete", "changed_duration": "completed", "changed_assets": "completed",
    "sparse": "completed", "rule_repair": "completed",
}


def run_examples(mode: str, tag: str | None = None) -> dict:
    batch = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "mode": mode, "runs": []}
    for case, expected in CASES.items():
        if mode == "live" and case in {"unsupported_claim", "max_steps", "rule_repair"}:
            # These are adversarial scripted fixtures, not natural live requests.
            continue
        run_id = f"{mode}_{case}" + (f"_{tag}" if tag else "")
        if (ROOT / "examples" / "traces" / (run_id + ".jsonl")).exists():
            run_id += "_" + uuid4().hex[:8]
        command = [sys.executable, "-m", "src.main", "--mode", mode, "--input-file",
                   f"examples/inputs/{case}.json", "--run-id", run_id]
        if mode == "mock":
            command += ["--scenario", case]
        if case == "tool_failure":
            command += ["--fail-tool", "estimate_duration"]
        if case == "max_steps":
            command += ["--max-steps", "3"]
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        output_path = ROOT / "examples" / "outputs" / (run_id + ".json")
        trace_path = ROOT / "examples" / "traces" / (run_id + ".json")
        output = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
        trace = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.exists() else {}
        path = [s["action"] for s in trace.get("steps", [])]
        row = {
            "case": case, "run_id": run_id, "input": f"examples/inputs/{case}.json",
            "output": f"examples/outputs/{run_id}.json", "trace": f"examples/traces/{run_id}.json",
            "events": f"examples/traces/{run_id}.jsonl", "exit_code": process.returncode,
            "expected_status": expected, "actual_status": output.get("status"),
            "status_matches": output.get("status") == expected,
            "actions": path, "real_model_responses": trace.get("real_model_responses", 0),
            "stderr": process.stderr, "stdout": process.stdout,
            **inspect_behavior(case, trace),
            "live_call_integrity": inspect_live_calls(trace) if mode == "live" else None,
        }
        batch["runs"].append(row)
        print(f"{case}: {row['actual_status']} (exit={process.returncode})", flush=True)
        if mode == "live" and output.get("failure_phase") == "configuration":
            # Avoid repeatedly attempting a known unavailable API configuration.
            break
    live_paths = {tuple(r["actions"]) for r in batch["runs"] if r["real_model_responses"]
                  and r["behavior_verified"] and (r.get("live_call_integrity") or {}).get("verified")}
    batch["distinct_verified_live_paths"] = len(live_paths) if mode == "live" else 0
    batch["live_requirement_verified"] = (
        mode == "live" and len(live_paths) >= 2
        and any(r["real_model_responses"] and r["observed_adaptations"] and r["behavior_verified"] for r in batch["runs"])
    )
    batch["all_expected_statuses"] = all(r["status_matches"] for r in batch["runs"])
    batch["all_expected_behaviors"] = all(r["behavior_verified"] for r in batch["runs"])
    target = ROOT / "examples" / f"{mode}-manifest.json"
    target.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return batch


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    parser.add_argument("--tag")
    args = parser.parse_args()
    batch = run_examples(args.mode, args.tag)
    raise SystemExit(0 if batch["all_expected_statuses"] and batch["all_expected_behaviors"] else 1)

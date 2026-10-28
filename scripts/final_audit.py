"""Read-only delivery audit. Replays records; never calls a model or rewrites evidence."""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values

from eval.audit import audit_error_run
from scripts.evidence import inspect_live_calls, inspect_trace_events
from scripts.replay import replay_trace


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_history(root, manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    changed, missing = [], []
    for relative, expected in manifest["files"].items():
        path = root / relative
        if not path.is_file():
            missing.append(relative)
        elif digest(path) != expected:
            changed.append(relative)
    return {"verified": not changed and not missing, "files_checked": len(manifest["files"]),
            "changed": changed, "missing": missing, "manifest": manifest_path.relative_to(root).as_posix()}


def audit_trace(path, root):
    relative = path.relative_to(root).as_posix()
    row = {"trace": relative}
    try:
        trace = json.loads(path.read_text(encoding="utf-8-sig"))
        events = [json.loads(line) for line in path.with_suffix(".jsonl").read_text(encoding="utf-8-sig").splitlines()]
        candidates = [path.parent.parent / "outputs" / path.name,
                      path.parent.parent / (path.stem + "-output.json")]
        output_path = next((p for p in candidates if p.is_file()), None)
        output = json.loads(output_path.read_text(encoding="utf-8-sig")) if output_path else None
        row.update(mode=trace.get("mode"), execution_kind=trace.get("execution_kind"),
                   status=trace.get("final_status"), steps=len(trace.get("steps", [])),
                   output=output_path.relative_to(root).as_posix() if output_path else None,
                   output_matches=output is not None and output == trace.get("final_result"))
        if trace.get("execution_kind") in {"startup_failure", "execution_failure"} and not trace.get("configuration"):
            # A startup failure is evidence of failure, never a replayed successful run.
            events_result = inspect_trace_events(trace, events)
            row.update(replay={"verified": events_result["verified"], "method": "startup_event_consistency_only",
                               "model_calls_made": 0, "event_log": events_result},
                       live_record_consistency=None, executable_replay=False)
        else:
            has_model_error = any(s["action"] == "model_error" for s in trace["steps"])
            if trace["mode"] == "live" and has_model_error:
                replay = audit_error_run(trace, events)
                live_check = {"verified": replay["verified"], "method": "error_aware_request_response_and_state_replay",
                              "notice": "Recorded model/transport failures remain failures; no successful-response claim."}
            else:
                replay = replay_trace(trace, events, output)
                live_check = inspect_live_calls(trace) if trace["mode"] == "live" else None
            row.update(replay=replay, live_record_consistency=live_check, executable_replay=True)
        row["verified"] = bool(row["output_matches"] and row["replay"]["verified"]
                               and (row["live_record_consistency"] is None or row["live_record_consistency"]["verified"]))
    except Exception as exc:
        row.update(verified=False, error_type=type(exc).__name__)
    return row


def secret_findings(data, secrets):
    """Return labels only. Neither a credential nor a matching line leaves this function."""
    found = []
    if any(secret.encode("utf-8") in data for secret in secrets):
        found.append("configured_credential_present")
    if re.search(rb"\bsk-[A-Za-z0-9_-]{32,}\b", data):
        found.append("credential_shaped_token")
    if re.search(rb"Bearer[ \t]+[A-Za-z0-9._~+-]{24,}", data):
        found.append("unredacted_bearer_token")
    return found


def git_blob_data(root):
    """Inspect reachable Git blobs through stdin. Credentials never enter command arguments."""
    listing = subprocess.run(["git", "rev-list", "--objects", "--all"], cwd=root,
                             capture_output=True, check=True).stdout.decode("utf-8", errors="replace")
    objects = dict(line.split(" ", 1) for line in listing.splitlines() if " " in line)
    # --batch emits object headers and exact byte sizes, permitting binary-safe parsing.
    result = subprocess.run(["git", "cat-file", "--batch"], cwd=root,
                            input=("\n".join(objects) + "\n").encode(), capture_output=True, check=True).stdout
    position = 0
    for oid, name in objects.items():
        end = result.index(b"\n", position)
        header = result[position:end].decode().split()
        size = int(header[2])
        position = end + 1
        body = result[position:position + size]
        position += size + 1
        if header[1] == "blob":
            yield oid, name, body


def scan_secrets(root):
    # Read the configured credential silently for exact-byte comparisons only.
    # Dotenv content, credentials, matching lines and credential hashes are never exported.
    values = dotenv_values(root / ".env") if (root / ".env").is_file() else {}
    secrets = sorted({v for v in (os.environ.get("LLM_API_KEY"), os.environ.get("OPENAI_API_KEY"),
                                 values.get("LLM_API_KEY"), values.get("OPENAI_API_KEY")) if v and len(v) >= 8})
    files = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if not path.is_file() or any(part in {".git", ".venv", "__pycache__", ".pytest_cache"} for part in relative.parts):
            continue
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            continue
        files.append(path)
    findings = []
    for path in files:
        labels = secret_findings(path.read_bytes(), secrets)
        if labels:
            findings.append({"path": path.relative_to(root).as_posix(), "findings": labels})
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout.decode().split("\0")
    tracked_private_env = [name for name in tracked if Path(name).name == ".env" or
                           (Path(name).name.startswith(".env.") and Path(name).name != ".env.example")]
    git_findings, blobs = [], 0
    for oid, name, content in git_blob_data(root):
        blobs += 1
        labels = secret_findings(content, secrets)
        if labels:
            git_findings.append({"object": oid, "path": name, "findings": labels})
    ignore = subprocess.run(["git", "check-ignore", "--quiet", ".env"], cwd=root, capture_output=True).returncode == 0
    return {"verified": not findings and not git_findings and not tracked_private_env and ignore,
            "working_files_checked": len(files), "reachable_git_blobs_checked": blobs,
            "exact_configured_credential_available": bool(secrets), "dotenv_ignored": ignore,
            "tracked_private_env": tracked_private_env, "working_tree_findings": findings,
            "git_findings": git_findings,
            "limitations": "Checks configured current credentials and common token shapes; revoked or unknown credential formats require separate review."}


def check_runtime_sources(root):
    original = json.loads((root / "eval/final-v3/starting-worktree.json").read_text(encoding="utf-8-sig"))["source_sha256"]
    protected = ["src/agent.py", "src/state.py", "src/tools.py", "src/schemas.py", "src/tracing.py"]
    checks = {name: digest(root / name) == original[name] for name in protected}
    before = root / "eval/final-v3/baseline-source/src/llm_adapter.py"
    if before.is_file():
        def without_prompt(path):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SYSTEM_PROMPT" for t in node.targets):
                    node.value = ast.Constant(value="PROMPT_OMITTED_FOR_CODE_COMPARISON")
            return ast.dump(tree, include_attributes=False)
        checks["src/llm_adapter.py code excluding SYSTEM_PROMPT"] = without_prompt(before) == without_prompt(root / "src/llm_adapter.py")
    return {"verified": all(checks.values()), "checks": checks,
            "meaning": "Runtime gates, estimators, reference validation, invalidation and max_steps code are byte-identical to this round's baseline."}


def inspect_pytest(path):
    suites = ET.parse(path).getroot()
    cases = list(suites.iter("testcase"))
    failures = sum(1 for c in cases if c.find("failure") is not None)
    errors = sum(1 for c in cases if c.find("error") is not None)
    skipped = sum(1 for c in cases if c.find("skipped") is not None)
    return {"verified": bool(cases) and not failures and not errors, "tests": len(cases),
            "passed": len(cases) - failures - errors - skipped, "failures": failures, "errors": errors, "skipped": skipped}


def run_audit(root, manifest_path, pytest_path=None):
    paths = []
    for directory in ("examples", "eval"):
        for path in (root / directory).rglob("*.json"):
            if "baseline-source" in path.parts:
                continue
            if path.with_suffix(".jsonl").is_file():
                paths.append(path)
                continue
            # Discover snapshots whose event stream is missing too. A missing log
            # must not silently disappear from the audit denominator.
            try:
                value = json.loads(path.read_text(encoding="utf-8-sig"))
                if isinstance(value, dict) and {"run_id", "steps", "final_result", "execution_kind"} <= value.keys():
                    paths.append(path)
            except (ValueError, OSError):
                continue
    rows = [audit_trace(path, root) for path in sorted(paths)]
    orphan_events = [p.relative_to(root).as_posix() for directory in ("examples", "eval")
                     for p in (root / directory).rglob("*.jsonl")
                     if "baseline-source" not in p.parts and not p.with_suffix(".json").is_file()]
    history = check_history(root, manifest_path)
    security = scan_secrets(root)
    runtime = check_runtime_sources(root)
    tests = inspect_pytest(pytest_path) if pytest_path else None
    counts = Counter((row.get("mode"), row.get("execution_kind")) for row in rows)
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(), "model_calls_made": 0,
            "verified": bool(rows) and all(r["verified"] for r in rows) and not orphan_events
                        and history["verified"] and security["verified"] and runtime["verified"]
                        and (tests is None or tests["verified"]),
            "traces_discovered": len(rows), "traces_verified": sum(r["verified"] for r in rows),
            "executable_replays": sum(r.get("executable_replay", False) for r in rows),
            "trace_counts": [{"mode": mode, "execution_kind": kind, "count": count}
                             for (mode, kind), count in sorted(counts.items(), key=lambda item: str(item[0]))],
            "orphan_event_logs": orphan_events, "historical_evidence": history,
            "runtime_sources": runtime, "secret_scan": security, "pytest": tests, "traces": rows,
            "limitations": ["Local live HTTP records are consistent; this is not independent provider attestation.",
                            "A replay verifies recorded decisions and deterministic checks, not creative quality or real spoken duration.",
                            "Mock records are scripted engineering evidence and never count as live evaluation."]}


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output path; existing files are rejected")
    parser.add_argument("--history-manifest", type=Path, default=ROOT / "eval/final-v3/historical-evidence-sha256.json")
    parser.add_argument("--pytest-report", type=Path)
    args = parser.parse_args(argv)
    # Fail before scanning if the requested destination already exists.
    if args.output.exists():
        parser.error("Output already exists; choose a new audit path to preserve previous evidence")
    report = run_audit(ROOT, args.history_manifest, args.pytest_report)
    write_exclusive(args.output, report)
    print(json.dumps({"verified": report["verified"], "traces": report["traces_discovered"],
                      "replays_verified": report["traces_verified"], "historical_unchanged": report["historical_evidence"]["verified"],
                      "secret_scan_passed": report["secret_scan"]["verified"], "output": str(args.output)}))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

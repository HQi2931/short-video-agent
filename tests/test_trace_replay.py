"""Replay and CLI-audit regressions; no real API is called by these tests."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.evidence import inspect_trace_events
from scripts.replay import replay_trace

ROOT = Path(__file__).resolve().parents[1]


def event_records(tmp_path, trace):
    return [json.loads(line) for line in (tmp_path / (trace["run_id"] + ".jsonl")).read_text(encoding="utf-8").splitlines()]


def test_actual_mock_execution_replays_all_tools_and_final_result(run_fixture, tmp_path):
    output, trace, _ = run_fixture()
    result = replay_trace(trace, event_records(tmp_path, trace), output)
    assert result["verified"] and result["model_calls_made"] == 0
    assert result["recomputed_steps"] == len(trace["steps"])


def test_consistently_forged_duration_is_detected_by_recomputation(run_fixture, tmp_path):
    output, trace, _ = run_fixture()
    events = event_records(tmp_path, trace)
    altered = deepcopy(trace)
    step = next(s for s in altered["steps"] if s["action"] == "estimate_duration")
    step["observation"]["total_estimated_seconds"] = 1
    altered["final_result"]["duration_check"]["total_estimated_seconds"] = 1
    altered["final_result"]["total_estimated_seconds"] = 1
    for event in events:
        if event["event"] == "step_executed" and event["step"] == step["step"]:
            event["observation"] = deepcopy(step["observation"])
        if event["event"] == "run_finished":
            event["final_result"] = deepcopy(altered["final_result"])
    assert inspect_trace_events(altered, events)["verified"]  # Files agree; computation is still false.
    result = replay_trace(altered, events, altered["final_result"])
    assert not result["verified"] and any(i["phase"] == "tool" for i in result["issues"])


def test_wrong_jsonl_next_action_is_rejected(run_fixture, tmp_path):
    output, trace, _ = run_fixture()
    events = event_records(tmp_path, trace)
    next(e for e in events if e["event"] == "next_action_observed")["next_action"] = "finish"
    assert not replay_trace(trace, events, output)["verified"]


def test_max_steps_incomplete_can_be_recomputed(run_fixture, tmp_path):
    output, trace, _ = run_fixture("max_steps", max_steps=3)
    assert output["status"] == "incomplete"
    assert replay_trace(trace, event_records(tmp_path, trace), output)["verified"]


@pytest.mark.parametrize(("require_live", "expected_code"), [(False, 0), (True, 1)])
def test_cli_audit_distinguishes_offline_pass_from_missing_live(tmp_path, require_live, expected_code):
    for name in ("src", "scripts", "tests", "docs", "data"):
        shutil.copytree(ROOT / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("README.md", "requirements.txt", ".env.example", ".gitignore"):
        shutil.copy2(ROOT / name, tmp_path / name)
    names = {"examples/mock-manifest.json", "examples/test-environment.json", "examples/test-results.xml"}
    manifest = json.loads((ROOT / "examples/mock-manifest.json").read_text(encoding="utf-8"))
    for row in manifest["runs"]:
        names.update(row[key] for key in ("input", "trace", "events", "output"))
    for name in names:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    # Isolate CLI scope semantics from this project's previous, possibly stale test run.
    # This is a clearly labelled temporary fixture, never exported as acceptance evidence.
    (tmp_path / "examples/test-environment.json").write_text(json.dumps({
        "exit_code": 0, "notice": "SYNTHETIC fixture for offline-versus-live exit-code testing only",
    }), encoding="utf-8")
    (tmp_path / "examples/test-results.xml").write_text(
        '<testsuites><testsuite tests="1" failures="0" errors="0"><testcase name="synthetic_scope_fixture"/></testsuite></testsuites>',
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    command = [sys.executable, str(tmp_path / "scripts/audit.py")]
    if require_live:
        command.append("--require-live")
    process = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", errors="replace")
    report = json.loads((tmp_path / "examples/audit.json").read_text(encoding="utf-8"))
    assert report["offline_checks_passed"] and not report["live_validation"]["verified"]
    assert process.returncode == expected_code, process.stdout + process.stderr

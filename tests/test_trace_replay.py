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


@pytest.mark.parametrize("tamper", [False, True])
def test_current_audit_cli_checks_manifest_before_accepting(tmp_path, tamper):
    import hashlib
    for name in ("src", "scripts", "eval", "tests", "docs", "data"):
        shutil.copytree(ROOT / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "examples/acceptance-current", tmp_path / "examples/acceptance-current")
    shutil.copy2(ROOT / "VERSION.json", tmp_path / "VERSION.json")
    for name in ("README.md", "requirements.txt", "requirements-lock.txt", "pyproject.toml", ".env.example", ".gitignore", ".gitattributes"):
        shutil.copy2(ROOT / name, tmp_path / name)
    shutil.copytree(ROOT / "delivery", tmp_path / "delivery")
    shutil.copytree(ROOT / "examples/inputs", tmp_path / "examples/inputs")
    if tamper:
        with (tmp_path / "src/agent.py").open("a", encoding="utf-8") as stream:
            stream.write("\n# test-only source change\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    destination = tmp_path / "audit-result.json"
    process = subprocess.run([sys.executable, str(tmp_path / "scripts/final_audit.py"), "--output", str(destination)],
                             cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", errors="replace")
    report = json.loads(destination.read_text(encoding="utf-8"))
    assert report["verified"] is (not tamper), process.stdout + process.stderr
    assert process.returncode == (1 if tamper else 0)

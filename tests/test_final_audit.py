"""Delivery-audit contract tests. These fixtures make no real model requests."""
import json
import httpx
import pytest

from scripts.final_audit import audit_trace, check_history, digest, main, run_audit, secret_findings, write_exclusive
from src.agent import AgentRunner
from src.llm_adapter import LiveAdapter
from src.mock_fixtures import mock_plan
from src.tracing import TraceLogger


def test_version_manifest_rejects_changed_sources(tmp_path):
    import hashlib
    from scripts.final_audit import check_runtime_sources
    source = tmp_path / 'src/agent.py'
    source.parent.mkdir()
    source.write_text('original', encoding='utf-8')
    files = {'src/agent.py': digest(source)}
    content_id = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    write_exclusive(tmp_path / 'VERSION.json', {'files': files, 'content_sha256': content_id})
    assert check_runtime_sources(tmp_path)['verified']
    source.write_text('changed', encoding='utf-8')
    assert not check_runtime_sources(tmp_path)['verified']
    source.write_text('original', encoding='utf-8')
    (tmp_path / 'src/old-candidate.py').write_text('another version', encoding='utf-8')
    assert not check_runtime_sources(tmp_path)['verified']


def test_history_audit_detects_changed_and_missing_evidence(tmp_path):
    trace = tmp_path / "old-trace.json"
    removed = tmp_path / "old-output.json"
    trace.write_text("original", encoding="utf-8")
    removed.write_text("output", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_exclusive(manifest, {"files": {trace.name: digest(trace), removed.name: digest(removed)}})
    assert check_history(tmp_path, manifest)["verified"]
    trace.write_text("changed", encoding="utf-8")
    removed.unlink()
    result = check_history(tmp_path, manifest)
    assert not result["verified"]
    assert result["changed"] == [trace.name] and result["missing"] == [removed.name]


def test_audit_output_cannot_replace_previous_evidence(tmp_path):
    path = tmp_path / "audit.json"
    write_exclusive(path, {"original": True})
    with pytest.raises(FileExistsError):
        write_exclusive(path, {"replacement": True})
    assert json.loads(path.read_text(encoding="utf-8")) == {"original": True}


def test_secret_scan_detects_exact_credentials_without_exporting_them():
    credential = "synthetic-credential-for-audit-only"
    findings = secret_findings(("nested error: " + credential).encode(), [credential])
    assert findings == ["configured_credential_present"]
    assert credential not in json.dumps(findings)
    assert not secret_findings(b'Bearer [REDACTED]', [credential])


def test_secret_scan_detects_unknown_credential_shapes():
    assert "credential_shaped_token" in secret_findings(b"sk-" + b"X" * 40, [])
    assert "unredacted_bearer_token" in secret_findings(b"Bearer " + b"Z" * 32, [])


def archived_fixture(tmp_path, trace, output):
    directory = tmp_path / "examples" / "traces"
    directory.mkdir(parents=True)
    path = directory / (trace["run_id"] + ".json")
    path.write_text(json.dumps(trace, ensure_ascii=False), encoding="utf-8")
    source_events = tmp_path / (trace["run_id"] + ".jsonl")
    path.with_suffix(".jsonl").write_bytes(source_events.read_bytes())
    outputs = directory.parent / "outputs"
    outputs.mkdir()
    (outputs / path.name).write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
    return path


def test_delivery_audit_replays_mock_and_preserves_evidence_kind(run_fixture, tmp_path):
    output, trace, _ = run_fixture()
    path = archived_fixture(tmp_path, trace, output)
    row = audit_trace(path, tmp_path)
    assert row["verified"] and row["executable_replay"]
    assert row["mode"] == "mock" and row["execution_kind"] == "scripted_mock"
    assert row["live_record_consistency"] is None
    assert row["replay"]["model_calls_made"] == 0


def test_delivery_audit_rejects_output_that_disagrees_with_trace(run_fixture, tmp_path):
    output, trace, _ = run_fixture()
    altered = {**output, "status": "incomplete"}
    path = archived_fixture(tmp_path, trace, altered)
    row = audit_trace(path, tmp_path)
    assert not row["verified"] and not row["output_matches"]


def test_delivery_audit_rejects_changed_jsonl_feedback(run_fixture, tmp_path):
    output, trace, _ = run_fixture()
    path = archived_fixture(tmp_path, trace, output)
    events = [json.loads(line) for line in path.with_suffix(".jsonl").read_text(encoding="utf-8").splitlines()]
    event = next(e for e in events if e["event"] == "step_executed" and e["action"] == "estimate_duration")
    event["observation"]["total_estimated_seconds"] = 0.01
    path.with_suffix(".jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    row = audit_trace(path, tmp_path)
    assert not row["verified"] and not row["replay"]["event_log"]["verified"]


def test_delivery_audit_rejects_forged_current_feedback_even_when_files_agree(state, tmp_path):
    # A local HTTP transport fixture tests audit integrity. It is not live model evidence.
    plan = iter(mock_plan("normal", state.user_input, state.assets, 12))
    def respond(request):
        return httpx.Response(200, json={"id": "synthetic-http-fixture", "model": "transport-fixture",
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(next(plan), ensure_ascii=False)}}]})
    logger = TraceLogger(tmp_path, "live", "transport-fixture", state.user_input.model_dump())
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = LiveAdapter("synthetic-key", "https://example.invalid/v1", "transport-fixture", client=client)
        output = AgentRunner(state, adapter, logger).run()
    trace = logger.trace
    path = archived_fixture(tmp_path, trace, output)
    assert audit_trace(path, tmp_path)["verified"]
    step = trace["steps"][2]
    payload = json.loads(step["model_call"]["request"]["messages"][-1]["content"])
    payload["state"]["last_observation"] = {"ok": True, "forged_feedback": True}
    step["model_call"]["request"]["messages"][-1]["content"] = json.dumps(payload, ensure_ascii=False)
    path.write_text(json.dumps(trace, ensure_ascii=False), encoding="utf-8")
    events = [json.loads(line) for line in path.with_suffix(".jsonl").read_text(encoding="utf-8").splitlines()]
    event = next(e for e in events if e["event"] == "step_executed" and e["step"] == step["step"])
    event["model_call"] = step["model_call"]
    path.with_suffix(".jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    row = audit_trace(path, tmp_path)
    assert row["replay"]["event_log"]["verified"]
    assert not row["verified"] and not row["replay"]["verified"]
    assert not row["live_record_consistency"]["verified"]


def test_audit_cli_rejects_existing_destination_before_scanning(tmp_path):
    path = tmp_path / "original.json"
    path.write_text("preserved", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main(["--output", str(path)])
    assert error.value.code == 2 and path.read_text(encoding="utf-8") == "preserved"


def test_missing_event_stream_stays_in_audit_denominator(run_fixture, tmp_path, monkeypatch):
    output, trace, _ = run_fixture()
    path = archived_fixture(tmp_path, trace, output)
    path.with_suffix(".jsonl").unlink()
    # Isolate Trace discovery from repository/history/security audits, which have
    # their own contract tests and require the real repository configuration.
    for name in ("check_history", "scan_secrets", "check_runtime_sources"):
        monkeypatch.setattr("scripts.final_audit." + name, lambda *args: {"verified": True})
    report = run_audit(tmp_path, tmp_path / "unused-manifest.json")
    assert not report["verified"]
    assert report["traces_discovered"] == 1 and report["traces_verified"] == 0
    assert report["traces"][0]["error_type"] == "FileNotFoundError"

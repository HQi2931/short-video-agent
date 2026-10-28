import json

from src.main import build_parser, execute_cli


def test_cli_mock_saves_actual_output_and_trace(tmp_path, capsys):
    from conftest import ROOT
    args = build_parser().parse_args([
        "--mode", "mock", "--input-file", str(ROOT / "examples/inputs/normal.json"),
        "--trace-dir", str(tmp_path), "--output-file", str(tmp_path / "result.json"),
    ])
    result, code = execute_cli(args)
    assert code == 0 and result["status"] == "completed"
    assert json.loads((tmp_path / "result.json").read_text(encoding="utf-8")) == result
    assert (tmp_path / (result["run_id"] + ".json")).exists()


def test_live_missing_configuration_is_logged_as_unverified(tmp_path, monkeypatch):
    from conftest import ROOT
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    monkeypatch.setenv("LLM_MODEL", "")
    args = build_parser().parse_args([
        "--mode", "live", "--input-file", str(ROOT / "examples/inputs/normal.json"),
        "--trace-dir", str(tmp_path), "--output-file", str(tmp_path / "result.json"),
    ])
    result, code = execute_cli(args)
    assert code == 5 and result["status"] == "incomplete"
    assert not result["live_verified"] and result["failure_phase"] == "configuration"
    trace = json.loads((tmp_path / (result["run_id"] + ".json")).read_text(encoding="utf-8"))
    assert trace["steps"] == [] and trace["real_model_responses"] == 0
    assert trace["execution_kind"] == "startup_failure"


def test_bad_input_is_logged_without_calling_model(tmp_path):
    path = tmp_path / "input.json"
    path.write_text('{"duration_seconds": -1}', encoding="utf-8")
    args = build_parser().parse_args(["--mode", "mock", "--input-file", str(path),
                                     "--trace-dir", str(tmp_path), "--output-file", str(tmp_path / "output.json")])
    result, code = execute_cli(args)
    assert code == 5 and result["failure_phase"] == "input_validation"

"""CLI entry point; exit codes distinguish completion from non-completion."""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .agent import AgentRunner
from .llm_adapter import LiveAdapter, MockAdapter
from .mock_fixtures import SCENARIOS, mock_plan
from .schemas import UserInput
from .state import AgentState
from .tools import ToolExecutor, load_data
from .tracing import TraceLogger

ROOT = Path(__file__).resolve().parents[1]
EXIT_CODES = {"completed": 0, "needs_info": 2, "failed": 3, "incomplete": 4}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidence-grounded short-video script Agent")
    parser.add_argument("--mode", choices=["live", "mock"], required=True)
    parser.add_argument("--input-file", type=Path, required=True)
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal", help="Mock fixture only")
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--fail-tool", choices=["search_assets", "estimate_duration", "check_brand_rules"], action="append", default=[])
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--trace-dir", type=Path, default=ROOT / "examples" / "traces")
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--run-id")
    return parser


def execute_cli(args: argparse.Namespace) -> tuple[dict, int]:
    load_dotenv(ROOT / ".env", override=False)
    key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "") if args.mode == "live" else MockAdapter.model
    raw_input, input_error = {}, None
    try:
        raw_input = json.loads(args.input_file.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        input_error = exc
    trace = TraceLogger(args.trace_dir, args.mode, model or "not-configured", raw_input,
                        run_id=args.run_id, secrets=[key])
    phase = "input_validation"
    try:
        if input_error:
            raise input_error
        user_input = UserInput.model_validate(raw_input)
        phase = "configuration"
        max_steps = args.max_steps if args.max_steps is not None else int(os.getenv("MAX_AGENT_STEPS", "12"))
        if not 1 <= max_steps <= 100:
            raise ValueError("max_steps must be in [1, 100]")
        assets, rules = load_data(args.data_dir)
        fail_once = set(args.fail_tool)
        if args.mode == "mock":
            adapter = MockAdapter(mock_plan(args.scenario, user_input, assets, max_steps), fixture=args.scenario)
            if args.scenario == "tool_failure":
                fail_once.add("estimate_duration")
        else:
            if args.scenario != "normal":
                raise ValueError("--scenario is for mock only; use --input-file for live tasks")
            adapter = LiveAdapter(
                key, os.getenv("LLM_BASE_URL", ""), model,
                timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
                response_format=os.getenv("LLM_RESPONSE_FORMAT", "json_object"),
            )
        state = AgentState(user_input, assets, rules)
        phase = "execution"
        result = AgentRunner(state, adapter, trace, ToolExecutor(fail_once=fail_once), max_steps).run()
        code = EXIT_CODES[result["status"]]
    except Exception as exc:
        # Configuration/input errors are auditable but never count as live execution evidence.
        trace.trace["execution_kind"] = "startup_failure" if phase != "execution" else "execution_failure"
        result = trace.finish({
            "run_id": trace.run_id, "mode": args.mode, "model": model or "not-configured",
            "status": "incomplete", "failure_phase": phase,
            "reason": str(exc), "error_type": type(exc).__name__,
            "completed_steps": [], "last_observation": None,
            "live_verified": False,
        })
        code = 5
    output_file = args.output_file or ROOT / "examples" / "outputs" / (trace.run_id + ".json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": trace.run_id, "mode": args.mode, "status": result["status"],
                      "reason": result["reason"], "output": str(output_file), "trace": str(trace.path)}, ensure_ascii=False))
    return result, code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _, code = execute_cli(args)
        return code
    except (FileExistsError, ValueError) as exc:
        print(json.dumps({"status": "incomplete", "reason": str(exc)}, ensure_ascii=False))
        return 5


if __name__ == "__main__":
    raise SystemExit(main())

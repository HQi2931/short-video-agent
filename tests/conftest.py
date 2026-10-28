import json
from pathlib import Path

import pytest

from src.agent import AgentRunner
from src.llm_adapter import MockAdapter
from src.mock_fixtures import mock_plan
from src.schemas import Script, UserInput
from src.state import AgentState
from src.tools import ToolExecutor, load_data
from src.tracing import TraceLogger

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def catalog():
    return load_data(ROOT / "data")


@pytest.fixture
def user_input():
    return UserInput.model_validate_json((ROOT / "examples/inputs/normal.json").read_text(encoding="utf-8"))


@pytest.fixture
def script(catalog):
    from src.mock_fixtures import make_script
    return Script.model_validate(make_script(catalog[0][0]))


@pytest.fixture
def state(catalog, user_input):
    assets, rules = catalog
    return AgentState(user_input, assets, rules)


@pytest.fixture
def run_fixture(tmp_path, catalog):
    def run(scenario="normal", actions=None, executor=None, max_steps=12, input_override=None):
        raw = json.loads((ROOT / f"examples/inputs/{scenario}.json").read_text(encoding="utf-8"))
        parsed = input_override or UserInput.model_validate(raw)
        assets, rules = catalog
        state = AgentState(parsed.model_copy(deep=True), [a.model_copy(deep=True) for a in assets], rules.model_copy(deep=True))
        adapter = MockAdapter(actions if actions is not None else mock_plan(scenario, parsed, assets, max_steps), fixture=scenario)
        trace = TraceLogger(tmp_path, adapter.mode, adapter.model, parsed.model_dump())
        executor = executor or ToolExecutor(fail_once={"estimate_duration"} if scenario == "tool_failure" else set())
        result = AgentRunner(state, adapter, trace, executor, max_steps).run()
        return result, trace.trace, state
    return run

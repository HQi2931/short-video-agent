"""HTTP transport doubles test protocol handling; these are NOT live model evidence."""
import json

import httpx
import pytest

from src.agent import AgentRunner
from src.llm_adapter import LiveAdapter, ModelError, parse_action
from src.mock_fixtures import action
from src.schemas import action_catalog
from src.tracing import TraceLogger


def completion(content, finish_reason="stop", **extra):
    return {"id": "transport-fixture-response", "model": "transport-fixture-model",
            "usage": {"total_tokens": 12}, "choices": [{"finish_reason": finish_reason,
            "message": {"content": content, **extra}}]}


@pytest.mark.parametrize("raw", [
    "not json", "```json\n{}\n```", "[]", '{"action":"invent","arguments":{},"reason_summary":"x"}',
    '{"action":"finish","action":"stop","arguments":{},"reason_summary":"x"}',
    '{"action":"finish","arguments":{},"reason_summary":"x","extra":true}',
    '{"action":"finish","arguments":{"x":NaN},"reason_summary":"x"}',
])
def test_invalid_model_responses_rejected(raw):
    with pytest.raises((ValueError, TypeError)):
        parse_action(raw)


def test_http_payload_and_structured_response_use_configured_model():
    seen = []
    def respond(request):
        seen.append(request)
        return httpx.Response(200, json=completion(json.dumps(action("search_assets", {"query": "字幕"}))))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = LiveAdapter("fixture-secret", "https://example.invalid/v1", "configured-model", client=client)
        decision = adapter.decide({"last_observation": {"ok": False}}, action_catalog())
    sent = json.loads(seen[0].content)
    assert str(seen[0].url) == "https://example.invalid/v1/chat/completions"
    assert sent["model"] == "configured-model"
    assert sent["response_format"] == {"type": "json_object"}
    assert decision.action.action == "search_assets"
    assert decision.record["response"]["model"] == "transport-fixture-model"
    assert "fixture-secret" not in json.dumps(decision.record)


@pytest.mark.parametrize("kind", ["auth", "timeout", "invalid_json", "truncated", "refusal", "redirect"])
def test_transport_failures_are_not_model_success(kind):
    def respond(request):
        if kind == "auth":
            return httpx.Response(401, json={"error": "unauthorized"})
        if kind == "timeout":
            raise httpx.ReadTimeout("timeout")
        if kind == "invalid_json":
            return httpx.Response(200, json=completion("not json"))
        if kind == "redirect":
            return httpx.Response(302, headers={"Location": "https://other.invalid"})
        return httpx.Response(200, json=completion(json.dumps(action("finish")),
                              finish_reason="length" if kind == "truncated" else "stop",
                              refusal="cannot comply" if kind == "refusal" else None))
    with httpx.Client(transport=httpx.MockTransport(respond), follow_redirects=False) as client:
        adapter = LiveAdapter("fixture-secret", "https://example.invalid/v1", "configured-model", client=client)
        with pytest.raises(ModelError) as error:
            adapter.decide({}, action_catalog())
        assert error.value.record


def test_invalid_response_observation_reaches_next_call(state, tmp_path):
    seen = []
    replies = ["invalid JSON", json.dumps(action("request_info", {"fields": ["assets"], "question": "请补充素材。"}))]
    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=completion(replies[len(seen) - 1]))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = LiveAdapter("fixture-secret", "https://example.invalid/v1", "transport-fixture", client=client)
        trace = TraceLogger(tmp_path, "live", adapter.model, state.user_input.model_dump(), secrets=["fixture-secret"])
        # Files remain in pytest temporary storage. Never include these in live manifests.
        result = AgentRunner(state, adapter, trace).run()
    second_context = json.loads(seen[1]["messages"][1]["content"])["state"]
    assert not second_context["last_observation"]["ok"]
    assert second_context["executed_actions"][0]["action"] == "model_error"
    assert result["status"] == "needs_info"


def test_tool_observation_reaches_model_request(state, tmp_path):
    seen = []
    replies = [action("search_assets", {"query": "字幕"}), action("stop", {"reason": "传输反馈测试结束"})]
    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=completion(json.dumps(replies[len(seen) - 1])))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = LiveAdapter("fixture-secret", "https://example.invalid/v1", "transport-fixture", client=client)
        trace = TraceLogger(tmp_path, "live", adapter.model, state.user_input.model_dump(), secrets=["fixture-secret"])
        result = AgentRunner(state, adapter, trace).run()
    context = json.loads(seen[1]["messages"][1]["content"])["state"]
    assert context["last_observation"]["retrieval_status"] == "found"
    assert context["retrieved_assets"][0]["asset_id"] == "P01"
    assert result["status"] == "failed"


@pytest.mark.parametrize("values", [
    ("", "https://example.invalid/v1", "model"),
    ("key", "", "model"), ("key", "https://example.invalid/v1", ""),
    ("key", "http://example.invalid/v1", "model"),
    ("key", "https://user:pass@example.invalid/v1", "model"),
])
def test_missing_or_unsafe_configuration_rejected(values):
    with pytest.raises(ValueError):
        LiveAdapter(*values)

"""Append-only execution events and a final JSON snapshot, scrubbed of API secrets."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TraceLogger:
    def __init__(self, directory: Path, mode: str, model: str, user_input: dict,
                 run_id: str | None = None, secrets: list[str] | None = None):
        self.run_id = run_id or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid4().hex[:12])
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", self.run_id):
            raise ValueError("run_id must be a safe filename identifier")
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / (self.run_id + ".json")
        self.events_path = directory / (self.run_id + ".jsonl")
        if self.path.exists() or self.events_path.exists():
            raise FileExistsError("Trace run_id already exists; previous evidence will not be overwritten")
        self.secrets = [s for s in (secrets or []) if s]
        self.trace = {
            "schema_version": 1, "run_id": self.run_id, "mode": mode, "model": model,
            "started_at_utc": utc_now(), "input": user_input, "steps": [],
            "execution_kind": "real_api" if mode == "live" else "scripted_mock",
        }
        self.event("run_started", {k: v for k, v in self.trace.items() if k != "steps"})

    def scrub(self, value):
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[REDACTED]")
            return re.sub(r"Bearer\s+[^\s\"']+", "Bearer [REDACTED]", value)
        if isinstance(value, dict):
            return {
                k: "[REDACTED]" if k.casefold() in {"api_key", "authorization", "llm_api_key", "openai_api_key"}
                else self.scrub(v) for k, v in value.items()
            }
        if isinstance(value, list):
            return [self.scrub(v) for v in value]
        return value

    def event(self, kind: str, data: dict):
        entry = self.scrub({"event": kind, "timestamp_utc": utc_now(), "run_id": self.run_id, **data})
        with self.events_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")

    def step(self, step: dict):
        if self.trace["steps"]:
            self.trace["steps"][-1]["next_action"] = step["action"]
            self.event("next_action_observed", {
                "step": self.trace["steps"][-1]["step"], "next_action": step["action"],
            })
        saved = self.scrub({**step, "next_action": None})
        self.trace["steps"].append(saved)
        self.event("step_executed", saved)

    def finish(self, result: dict):
        self.trace.update({
            "finished_at_utc": utc_now(), "final_status": result["status"], "final_result": result,
            "real_model_responses": sum(
                1 for s in self.trace["steps"]
                if s.get("model_call", {}).get("mode") == "live"
                and s.get("model_call", {}).get("response")
            ),
        })
        self.trace = self.scrub(self.trace)
        self.event("run_finished", {"final_status": result["status"], "final_result": result})
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.trace, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(self.path)
        return self.trace["final_result"]

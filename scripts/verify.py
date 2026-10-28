"""Record actual pytest output and environment, preserving previous test reports."""
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def verify() -> int:
    directory = ROOT / "examples"
    directory.mkdir(exist_ok=True)
    path = directory / "test-results.txt"
    if path.exists():
        history = directory / "test-history"
        history.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid4().hex[:6]
        (history / f"test-results_{stamp}.txt").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    command = [sys.executable, "-m", "pytest", "tests/", "-v", "--junitxml=examples/test-results.xml"]
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    metadata = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {name: version(name) for name in ["pydantic", "httpx", "python-dotenv", "pytest"]},
        "command": ["python", "-m", "pytest", "tests/", "-v", "--junitxml=examples/test-results.xml"],
        "exit_code": process.returncode,
        "notice": "All model HTTP requests in pytest use transport doubles; no live LLM validation.",
    }
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n\nSTDOUT\n" + process.stdout
                    + "\nSTDERR\n" + process.stderr, encoding="utf-8")
    (directory / "test-environment.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(process.stdout[-9000:])
    if process.stderr:
        print(process.stderr)
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(verify())

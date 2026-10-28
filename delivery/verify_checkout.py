"""Verify the proposed delivery in temporary Git indexes; never stage the real repo."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd=ROOT, env=None, **kwargs):
    return subprocess.run(command, cwd=cwd, env=env, capture_output=True, check=True, **kwargs)


def git(args, cwd=ROOT, env=None, **kwargs):
    return run(["git", *args], cwd, env, **kwargs).stdout


def save_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pytest-xml", type=Path, required=True)
    parser.add_argument("--pytest-text", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    args = parser.parse_args()
    outputs = [p.resolve() for p in (args.output, args.pytest_xml, args.pytest_text, args.audit_output)]
    if len(set(outputs)) != len(outputs) or any(p.exists() for p in outputs):
        parser.error("Use four distinct, new output paths; existing evidence is never replaced")
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
    output, xml, log, audit = outputs
    original_head = git(["rev-parse", "HEAD"]).strip()
    original_index = git(["ls-files", "--stage", "-z"])
    git_dir = Path(git(["rev-parse", "--absolute-git-dir"]).decode().strip())
    changed = git(["diff", "--name-only", "-z"]).decode().split("\0")
    added = git(["ls-files", "--others", "--exclude-standard", "-z"]).decode().split("\0")
    start = json.loads((ROOT / "delivery/review/starting-state.json").read_text(encoding="utf-8"))
    raw_paths = sorted(set(start["protected_evidence_sha256"]) | {
        "docs/08-agent-evaluation.md", "docs/09-decision-optimization.md",
        "docs/10-independent-failure-analysis.md", "docs/11-live-failure-ledger.md"})
    proposed = sorted(set(filter(None, changed + added)) | set(raw_paths))
    if any(not (ROOT / p).is_file() or "\n" in p or "\r" in p for p in proposed):
        parser.error("Review missing files or unusual filenames before verifying delivery")
    base_env = dict(os.environ)
    for name in ("GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_DIR", "GIT_WORK_TREE"):
        base_env.pop(name, None)
    with tempfile.TemporaryDirectory(prefix="short-video-delivery-") as directory:
        temporary = Path(directory).resolve()
        # Only this explicitly generated temporary directory is automatically cleaned.
        assert temporary.parent == Path(tempfile.gettempdir()).resolve()
        assert temporary.name.startswith("short-video-delivery-")
        objects = temporary / "objects"
        objects.mkdir()
        plan = temporary / "paths.nul"
        plan.write_bytes(b"\0".join(p.encode() for p in proposed) + b"\0")
        raw_plan = temporary / "raw-paths.nul"
        raw_plan.write_bytes(b"\0".join(p.encode() for p in raw_paths) + b"\0")
        temp_env = {**base_env, "GIT_INDEX_FILE": str(temporary / "index"),
                    "GIT_OBJECT_DIRECTORY": str(objects),
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(git_dir / "objects")}
        git(["read-tree", "HEAD"], env=temp_env)
        git(["--literal-pathspecs", "add", "--pathspec-from-file=" + str(plan), "--pathspec-file-nul"], env=temp_env)
        attributes = git(["check-attr", "-z", "--stdin", "text"], env=temp_env, input=raw_plan.read_bytes()).decode().split("\0")
        assert all(attributes[i] == "unset" for i in range(2, len(attributes) - 1, 3)), "Frozen paths must explicitly disable text conversion"
        # A changed .gitattributes does not invalidate old index stat caches.
        # Force only frozen paths through the now-disabled text filter; no working file is edited.
        git(["--literal-pathspecs", "add", "--renormalize", "--pathspec-from-file=" + str(raw_plan), "--pathspec-file-nul"], env=temp_env)
        whitespace = subprocess.run(["git", "diff", "--cached", "--check"], cwd=ROOT, env=temp_env,
                                    capture_output=True, text=True, encoding="utf-8", errors="replace")
        if whitespace.returncode:
            # Record diagnostic labels, never captured source/log lines.
            diagnostics = [line for line in whitespace.stdout.splitlines() if re.match(r"^.+:\d+: ", line)]
            failure = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "verified": False,
                       "stage_check_exit_code": whitespace.returncode, "diagnostics": diagnostics,
                       "real_head_unchanged": git(["rev-parse", "HEAD"]).strip() == original_head,
                       "real_index_entries_unchanged": git(["ls-files", "--stage", "-z"]) == original_index,
                       "model_calls_made": 0, "commits_created": 0}
            save_new(output, failure)
            print(json.dumps(failure, ensure_ascii=False))
            return whitespace.returncode
        tree = git(["write-tree"], env=temp_env).decode().strip()
        entries = git(["ls-files", "--stage", "-z"], env=temp_env).decode().split("\0")
        checkout = temporary / "checkout"
        git(["init", "--initial-branch=main", str(checkout)], env=base_env)
        checkout_env = {**base_env, "GIT_OBJECT_DIRECTORY": str(objects),
                        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(git_dir / "objects")}
        # The temporary repository references an existing commit; no commit is created.
        git(["update-ref", "refs/heads/main", original_head.decode()], checkout, checkout_env)
        git(["config", "core.autocrlf", "true"], checkout, checkout_env)
        git(["read-tree", tree], checkout, checkout_env)
        git(["checkout-index", "--all", "--force"], checkout, checkout_env)
        mismatches = []
        ordinary_text_conversions = []
        object_format = git(["rev-parse", "--show-object-format"]).decode().strip()
        assert object_format in {"sha1", "sha256"}
        for entry in filter(None, entries):
            header, path = entry.split("\t", 1)
            expected = header.split()[1]
            content = (checkout / path).read_bytes()
            actual = hashlib.new(object_format, b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
            if actual != expected:
                canonical = git(["hash-object", "--path=" + path, str(checkout / path)], checkout, checkout_env).decode().strip()
                if canonical == expected:
                    ordinary_text_conversions.append(path)
                else:
                    mismatches.append(path)
        assert not mismatches, "Checkout does not match proposed Git blobs"
        immutable = {}
        for relative, expected in start["protected_evidence_sha256"].items():
            immutable[relative] = hashlib.sha256((checkout / relative).read_bytes()).hexdigest() == expected
        candidate = json.loads((ROOT / "eval/final-v3/candidate-b-source-manifest.json").read_text(encoding="utf-8"))
        core = {p: hashlib.sha256((checkout / p).read_bytes()).hexdigest() == h for p, h in candidate["files"].items()}
        if not all(immutable.values()) or not all(core.values()):
            failure = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "verified": False,
                       "immutable_evidence_mismatches": [p for p, ok in immutable.items() if not ok],
                       "candidate_b_mismatches": [p for p, ok in core.items() if not ok],
                       "real_head_unchanged": git(["rev-parse", "HEAD"]).strip() == original_head,
                       "real_index_entries_unchanged": git(["ls-files", "--stage", "-z"]) == original_index,
                       "model_calls_made": 0, "commits_created": 0}
            save_new(output, failure)
            print(json.dumps({"verified": False, "immutable_mismatches": len(failure["immutable_evidence_mismatches"]),
                              "first_mismatches": failure["immutable_evidence_mismatches"][:5],
                              "candidate_b_mismatches": failure["candidate_b_mismatches"]}))
            return 1
        test = subprocess.run([sys.executable, "-m", "pytest", "-q", "--junitxml=" + str(xml)],
                              cwd=checkout, env=checkout_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        with log.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write("Temporary checkout; HTTP model fixtures only; no live calls.\n" + test.stdout + "\nSTDERR\n" + test.stderr)
        assert test.returncode == 0, "Temporary checkout pytest failed; receipts preserved"
        audit_run = run([sys.executable, "scripts/final_audit.py", "--output", str(audit), "--pytest-report", str(xml)], checkout, checkout_env)
        audit_result = json.loads(audit.read_text(encoding="utf-8"))
        assert audit_result["verified"] and audit_result["traces_verified"] == 220
        tree_objects = {tree}
        for line in git(["ls-tree", "-r", "-t", tree], env=temp_env).decode().splitlines():
            tree_objects.add(line.split("\t", 1)[0].split()[2])
        pack_path = temporary / "candidate-tree.pack"
        with pack_path.open("wb") as stream:
            subprocess.run(["git", "pack-objects", "--stdout"], cwd=ROOT, env=temp_env,
                           input=("\n".join(sorted(tree_objects)) + "\n").encode(), stdout=stream, stderr=subprocess.PIPE, check=True)
        report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "verified": True,
                  "method": "isolated indexes and object storage; temporary checkout with core.autocrlf=true; no commit created",
                  "snapshot_tree": tree, "proposed_changed_files": len(proposed),
                  "explicit_raw_byte_reindex_paths": len(raw_paths),
                  "checked_out_files": len(list(filter(None, entries))), "git_blob_mismatches": mismatches,
                  "ordinary_text_line_ending_conversions": ordinary_text_conversions,
                  "immutable_evidence_files": len(immutable), "immutable_evidence_verified": all(immutable.values()),
                  "candidate_b_source_files": len(core), "candidate_b_source_verified": all(core.values()),
                  "pytest_exit_code": test.returncode, "audit_verified": audit_result["verified"],
                  "trace_replays": audit_result["traces_verified"], "model_calls_made": 0,
                  "full_snapshot_pack_bytes": pack_path.stat().st_size,
                  "pack_scope": "Full proposed current tree only, not a prediction of an actual remote push pack",
                  "temporary_audit_stdout": audit_run.stdout.decode().strip(),
                  "real_head_unchanged": git(["rev-parse", "HEAD"]).strip() == original_head,
                  "real_index_entries_unchanged": git(["ls-files", "--stage", "-z"]) == original_index,
                  "scope_note": "Receipts produced by this check and the subsequently frozen final stage manifest are added after the checked snapshot."}
        assert report["real_head_unchanged"] and report["real_index_entries_unchanged"]
        save_new(output, report)
    print(json.dumps({k: report[k] for k in ("verified", "checked_out_files", "immutable_evidence_files", "candidate_b_source_files", "trace_replays", "full_snapshot_pack_bytes", "real_head_unchanged", "real_index_entries_unchanged")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

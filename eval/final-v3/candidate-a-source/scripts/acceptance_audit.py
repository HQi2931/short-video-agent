"""Build the 12-item acceptance matrix from code, actual test reports and replays."""
import hashlib
import ast
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.main import build_parser
from replay import replay_files
from summarize_live import summarize_live
from verify import source_hashes


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def location(file, symbol):
    if "." in symbol:
        class_name, method = symbol.split(".", 1)
        tree = ast.parse((ROOT / file).read_text(encoding="utf-8"))
        node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
        line = next(n.lineno for n in node.body if isinstance(n, ast.FunctionDef) and n.name == method)
        return {"file": file, "symbol": symbol, "line": line}
    lines = (ROOT / file).read_text(encoding="utf-8").splitlines()
    line = next((i for i, text in enumerate(lines, 1) if f"def {symbol}(" in text), 1)
    return {"file": file, "symbol": symbol, "line": line}


def audit_acceptance():
    testcases = list(ET.parse(ROOT / "examples/test-results.xml").getroot().iter("testcase"))
    def tested(name):
        matches = [case for case in testcases if case.get("name", "").split("[")[0] == name]
        return bool(matches) and all(not any(case.find(k) is not None for k in ("failure", "error", "skipped")) for case in matches)
    environment = read("examples/test-environment.json")
    tests_bound = environment.get("tested_source_sha256") == source_hashes() and environment.get("source_unchanged_during_tests", False)
    tests_pass = tests_bound and environment["exit_code"] == 0 and bool(testcases) and all(not any(case.find(k) is not None for k in ("failure", "error", "skipped")) for case in testcases)
    traces = [{"trace": p.relative_to(ROOT).as_posix(), "replay": replay_files(p)}
              for p in sorted((ROOT / "examples/traces").glob("*.json"))]
    replay_pass = bool(traces) and all(row["replay"]["verified"] for row in traces)
    live = summarize_live(quiet=True)
    live_pass = bool(live["runs"]) and all(row["live_call_integrity"]["verified"] and row["execution_replay"]["verified"] for row in live["runs"])
    batch = read("examples/mock-manifest.json")
    mock_pass = len(batch["runs"]) >= 11 and batch["all_expected_statuses"] and batch["all_expected_behaviors"]
    doc_checks, broken_links = [], []
    for path in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        for block in re.findall(r"^```[^\n]*\n(.*?)^```[ \t]*$", text, re.S | re.M):
            for line in block.splitlines():
                if "-m src.main " in line:
                    arguments = shlex.split(line.split("-m src.main ", 1)[1])
                    args = build_parser().parse_args(arguments)
                    doc_checks.append({"document": path.relative_to(ROOT).as_posix(), "arguments": arguments,
                                       "valid": (ROOT / args.input_file).is_file()})
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if re.match(r"^[a-zA-Z]+://", target) or target.startswith("#"):
                continue
            if not (path.parent / target.split("#")[0].strip("<>")).exists():
                broken_links.append({"document": path.relative_to(ROOT).as_posix(), "target": target})
    docs_pass = bool(doc_checks) and all(r["valid"] for r in doc_checks) and not broken_links
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    docs_pass &= f"{len(testcases)}项通过" in readme and "--require-live" in readme and "if (-not (Test-Path .env))" in readme
    rows = []
    def item(number, title, passed, code, tests, evidence, note):
        rows.append({"id": number, "item": title,
                     "status": "PASS" if passed and all(tested(name) for _, name in tests) else "FAIL",
                     "code": [location(*entry) for entry in code], "tests": [location(*entry) for entry in tests],
                     "trace_files": evidence, "note": note})
    normal = "examples/traces/live_normal_round1.json"
    missing = "examples/traces/live_no_assets_round1.json"
    overtime = "examples/traces/live_overtime_tight_round1.json"
    failure = "examples/traces/live_tool_failure_round1.json"
    item(1, "真实模型选择动作与工具", live_pass,
         [("src/llm_adapter.py", "LiveAdapter.decide"), ("src/agent.py", "run")],
         [("tests/test_adapter.py", "test_http_payload_and_structured_response_use_configured_model")],
         [normal, missing], "live分支使用HTTP Adapter，Runtime按模型动作分派；固定动作仅存在于明确的Mock模式。")
    item(2, "工具观察回传下一轮模型请求", live_pass and replay_pass,
         [("src/agent.py", "run"), ("src/state.py", "context")],
         [("tests/test_adapter.py", "test_tool_observation_reaches_model_request")],
         [missing, failure], "逐轮比较完整请求state与重放状态，不仅比对上一观察。")
    item(3, "超时后模型提供不同脚本并重新检查", live["duration_correction_verified"] and live_pass,
         [("src/agent.py", "_execute_action"), ("src/tools.py", "estimate_duration")],
         [("tests/test_agent.py", "test_overtime_has_actual_distinct_revisions_and_rechecks"),
          ("tests/test_acceptance_regressions.py", "test_overtime_evidence_requires_actual_changed_model_draft")],
         [overtime], "4秒目标：7.64→2.35秒，旁白/分镜内容实际不同；12秒未触发记录仍保留。")
    item(4, "无素材时改写查询或请求补充", bool(live["required_case_coverage"]["no_assets"]),
         [("src/tools.py", "search_assets"), ("src/agent.py", "run")],
         [("tests/test_agent.py", "test_no_results_has_two_actual_queries_then_requests_evidence")],
         [missing], "真实查询从月球采矿激光雷达改为激光雷达，两次无结果后needs_info。")
    item(5, "工具失败记录与后续行动", bool(live["required_case_coverage"]["tool_failure"]),
         [("src/tools.py", "execute"), ("src/agent.py", "run")],
         [("tests/test_failures.py", "test_tool_failure_is_observed_and_retry_is_recorded")],
         [failure], "一次业务工具异常是明确注入；真实模型选择重试，随后根据超时观察改稿。")
    item(6, "已完成脚本的产品声明可追溯", replay_pass,
         [("src/tools.py", "check_brand_rules")],
         [("tests/test_tools.py", "test_fact_and_brand_adversarial_checks")],
         [normal, "examples/traces/mock_unsupported_claim_acceptance.json"],
         "PASS范围为completed脚本及结构化原文约束；故意构造的failed负例仍含被标记的无据文本。完整自然语言语义为NOT VERIFIED。")
    item(7, "脚本及依赖变化使旧检查失效", replay_pass,
         [("src/state.py", "invalidate"), ("src/state.py", "script_version")],
         [("tests/test_validation.py", "test_any_script_edit_invalidates_old_checks"),
          ("tests/test_acceptance_regressions.py", "test_result_cannot_remain_completed_after_verified_state_changes")],
         ["examples/traces/live_changed_assets_round1.json"], "脚本、输入、素材、规则指纹均参与门禁；完成后编辑也撤销成功状态。")
    item(8, "不得跳过检查或导出过期成功", replay_pass,
         [("src/state.py", "finish_errors"), ("src/agent.py", "result")],
         [("tests/test_agent.py", "test_runtime_rejects_premature_finish_and_draft"),
          ("tests/test_acceptance_regressions.py", "test_result_cannot_remain_completed_after_verified_state_changes")],
         ["examples/traces/mock_unsupported_claim_acceptance.json"], "修复前完成后Python对象编辑可导出completed，已复现并修复；CLI既有Trace未发现命中此漏洞。")
    item(9, "max_steps后明确incomplete", mock_pass,
         [("src/agent.py", "run")],
         [("tests/test_failures.py", "test_max_steps_returns_incomplete_and_last_observation")],
         ["examples/traces/mock_max_steps_acceptance.json"], "实际CLI为3步，状态incomplete、退出码4、含最后观察；未新增live上限采样。")
    item(10, "自动Trace及next_action一致", replay_pass and live_pass,
         [("src/tracing.py", "step"), ("scripts/evidence.py", "inspect_trace_events")],
         [("tests/test_trace_replay.py", "test_wrong_jsonl_next_action_is_rejected"),
          ("tests/test_acceptance_regressions.py", "test_live_integrity_rejects_wrong_next_action")],
         [overtime, "examples/traces/mock_normal_acceptance.json"], "全部JSONL重建JSON并复算工具/版本/结果；不将重放算作新的LLM执行。")
    item(11, "两条不同观察驱动的真实LLM路径", live["live_requirement_verified"] and live_pass,
         [("src/llm_adapter.py", "LiveAdapter.decide"), ("scripts/evidence.py", "inspect_live_calls")],
         [("tests/test_adapter.py", "test_invalid_response_observation_reaches_next_call")],
         [missing, overtime, failure], f"复核{len(live['runs'])}次live、{live['total_real_model_responses']}条响应；本轮新增API调用0次。")
    item(12, "场景、文档与命令一致", docs_pass and mock_pass and tests_pass,
         [("src/main.py", "build_parser"), ("scripts/audit.py", "audit")],
         [("tests/test_trace_replay.py", "test_cli_audit_distinguishes_offline_pass_from_missing_live")],
         ["examples/mock-manifest.json", "examples/live-manifest.json"], "核对文档CLI参数和输入文件、Markdown链接、当前测试数；默认离线与严格验收退出码明确区分。")
    findings = [
        {"id": "P0-01", "severity": "P0", "status": "FIXED", "title": "完成后编辑状态仍可导出completed",
         "scope": "Python状态编辑/结果导出接口；既有CLI记录未观察到命中", "proof": "examples/acceptance/regressions-before-fix.txt", "fix": "src/state.py invalidate及src/agent.py result双重门禁"},
        {"id": "P1-01", "severity": "P1", "status": "FIXED", "title": "live证据核验遗漏next_action/执行类型，且未复算工具与JSONL",
         "proof": "examples/acceptance/regressions-before-fix.txt", "fix": "scripts/evidence.py、scripts/replay.py"},
        {"id": "P1-02", "severity": "P1", "status": "FIXED", "title": "仅凭版本号变化推断模型改稿，可能误判修订通过",
         "proof": "examples/acceptance/regressions-before-fix.txt", "fix": "比较实际draft内容、同一目标时长与后续重检"},
        {"id": "P2-01", "severity": "P2", "status": "FIXED", "title": "审计默认退出码只覆盖离线，完整验收命令范围不明确",
         "proof": "tests/test_trace_replay.py", "fix": "增加--require-live，并测试离线通过/live缺失时返回1"},
        {"id": "P2-02", "severity": "P2", "status": "FIXED", "title": "README重复复制模板可能覆盖已有.env",
         "proof": "README.md", "fix": "仅在.env不存在时复制模板；当前配置保持原样"},
    ]
    unverified = ["服务商侧独立账单/签章及底层模型身份", "任意自然语言的完整语义核验与真实产品效果",
                  "其他模型、Python3.11/3.12和其他操作系统", "真实网络故障/限流恢复、真人口播、素材版权",
                  "候选人其他未确认的亲自操作/实际工时、评审访问及远程CI"]
    source_files = [*sorted((ROOT / "src").glob("*.py")), *sorted((ROOT / "scripts").glob("*.py"))]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "review_method": "candidate_requested_AI_assisted_acceptance_audit",
        "git_head_at_report": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
        "source_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
        "pytest_cases": len(testcases), "pytest_passed": tests_pass, "tested_source_matches_current": tests_bound,
        "trace_files": len(traces), "trace_replays": traces,
        "all_replays_verified": replay_pass, "new_live_api_calls_in_this_audit": 0,
        "live_runs_reviewed": len(live["runs"]), "live_responses_reviewed": live["total_real_model_responses"],
        "findings": findings, "matrix": rows, "not_verified": [{"item": text, "status": "NOT VERIFIED"} for text in unverified],
        "document_commands": doc_checks, "broken_local_links": broken_links,
        "all_12_items_pass": all(row["status"] == "PASS" for row in rows),
    }
    target = ROOT / "examples/acceptance/strict-results.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    def links(entries):
        return "、".join(f"[{r['file']}:{r['line']}](../{r['file']}#L{r['line']})" for r in entries)
    lines = ["# 严格校招验收审计", "", f"生成时间（UTC）：{report['generated_at_utc']}。",
             "本次由候选人发起、AI工具实际执行，归档为候选人委托的AI辅助验收材料；不推断候选人亲自阅读或运行的事实。", "",
             f"原116项测试通过后新增7条对抗回归实际失败；优先修复P0后，完整{len(testcases)}项测试通过。重跑11组Mock CLI，复算{len(traces)}份Trace及对应输出。",
             f"本次核对新增LLM调用0次，复核已有{len(live['runs'])}次真实运行、{live['total_real_model_responses']}条响应。离线重放不是新的模型决策证据；候选人亲自执行的三组记录另见docs/08-manual-live-review.md。", "",
             "P0定义为可直接违反不得虚报成功的核心约束；P1为审计结果可误判；P2为命令/文档操作风险。", "",
             "## 发现及修复", "", "| 分级 | 问题 | 结果 |", "|---|---|---|"]
    lines.extend(f"| {r['id']} | {r['title']} | {r['status']}：{r['fix']} |" for r in findings)
    lines += ["", "P0触发范围：已完成状态被Python接口编辑后再次导出；现有CLI历史没有命中证据。旧记录不是因此被宣布无效。",
              "修复前实际失败输出：[regressions-before-fix.txt](../examples/acceptance/regressions-before-fix.txt)；P0专项复测：[p0-after-fix.txt](../examples/acceptance/p0-after-fix.txt)。", "",
              "审计工具开发时还发生过2项测试夹具失败：临时工作区复制了上轮源码指纹报告，源码变化后被新检查正确拒绝。现已改为明确标注的临时合成夹具隔离退出码测试；真实仓库测试报告未被手改。原始失败见[audit-fixture-before-fix.txt](../examples/acceptance/audit-fixture-before-fix.txt)。", "",
              "## 12项验收矩阵", "", "| # | 验收项 | 结果 | 代码 | 实际通过测试 | Trace/执行证据 |", "|---|---|---|---|---|---|"]
    for row in rows:
        evidence = "、".join(f"[{Path(p).name}](../{p})" for p in row["trace_files"])
        lines.append(f"| {row['id']} | {row['item']} | {row['status']} | {links(row['code'])} | {links(row['tests'])} | {evidence} |")
    lines += ["", *[f"{r['id']}. {r['note']}" for r in rows], "", "## NOT VERIFIED", ""]
    lines.extend(f"- NOT VERIFIED：{text}。" for text in unverified)
    lines += ["", "## 重新执行", "", "```powershell", "cd D:\\Xiaoying\\short-video-agent",
              ".\\.venv\\Scripts\\python.exe scripts/verify.py", ".\\.venv\\Scripts\\python.exe scripts/run_examples.py --mode mock --tag acceptance",
              ".\\.venv\\Scripts\\python.exe scripts/audit.py --require-live", ".\\.venv\\Scripts\\python.exe scripts/acceptance_audit.py", "```", "",
              "verify和run_examples会实际运行测试与CLI；audit/acceptance_audit重算已有证据，不自动新增模型请求。",
              "初始12秒live用例未触发修订的记录和batch退出码1保持不变，4秒补充输入提供独立超时修订证据。",
              "机器可读完整矩阵、源码SHA-256及逐文件结果：[strict-results.json](../examples/acceptance/strict-results.json)。", ""]
    (ROOT / "docs/07-acceptance-audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"pytest_cases": len(testcases), "trace_files": len(traces), "replays_verified": replay_pass,
                      "all_12_items_pass": report["all_12_items_pass"], "failed_items": [r for r in rows if r["status"] != "PASS"]}, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    report = audit_acceptance()
    raise SystemExit(0 if report["all_12_items_pass"] else 1)

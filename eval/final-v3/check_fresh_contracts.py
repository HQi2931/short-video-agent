"""Frozen v3 supplemental acceptance: read traces, never mutate agent/runtime/scorer."""
import argparse
import json
from itertools import permutations
from pathlib import Path


def check_case(case, trace, facts):
    issues = []
    steps = trace.get("steps", [])
    drafts = [s for s in steps if s.get("action") == "draft_script" and s.get("observation", {}).get("ok")]
    contract = case["contract"]
    initial = contract.get("initial_draft")
    if initial:
        if not drafts:
            issues.append("Required initial draft is missing")
        else:
            scenes = drafts[0]["observation"]["script"]["storyboard"]
            if len(scenes) != initial["scene_count"]:
                issues.append("Initial scene count does not match frozen contract")
            requirements = initial["per_scene_narrated_fact_ids"]
            assignments = permutations(scenes) if initial.get("unordered_scenes") else [scenes]
            if not any(len(order) >= len(requirements) and all(
                    all(facts[fact_id] in order[i].get("narration", "") for fact_id in ids)
                    for i, ids in enumerate(requirements)) for order in assignments):
                issues.append("Initial scenes do not narrate all frozen required facts in their required grouping")
            estimates = [s for s in steps if s.get("action") == "estimate_duration" and s.get("observation", {}).get("ok")]
            if not estimates:
                issues.append("No successful initial timing observation")
            else:
                first = estimates[0]
                preceding = [s for s in drafts if s["step"] < first["step"]]
                if initial.get("estimate_before_revision") and len(preceding) != 1:
                    issues.append("Initial timing must precede any accepted revision")
                if not first["observation"].get("is_overtime"):
                    issues.append("Initial draft did not actually trigger overtime")
                if not any(s["step"] > first["step"] and s["observation"]["script"] != drafts[0]["observation"]["script"] for s in drafts[1:]):
                    issues.append("No genuinely changed draft after timing feedback")
    result = trace.get("final_result", {})
    if result.get("status") == "completed":
        if not drafts:
            issues.append("Completed without accepted draft")
        else:
            scenes = drafts[-1]["observation"]["script"]["storyboard"]
            spoken, narrated = set(), set()
            for scene in scenes:
                for ref in scene.get("fact_refs", []):
                    fact_id = ref["asset_id"] + ":" + ref["fact_id"]
                    fact = facts.get(fact_id)
                    if fact and fact in scene.get("narration", ""):
                        narrated.add(fact_id)
                    if fact and (fact in scene.get("narration", "") or fact in scene.get("subtitle", "")):
                        spoken.add(fact_id)
            if contract.get("final_any_spoken_fact") and not spoken:
                issues.append("Final complete fact exists in neither narration nor subtitle")
            for asset_id in contract.get("final_spoken_asset_ids", []):
                if not any(f.startswith(asset_id + ":") for f in spoken):
                    issues.append(f"Final narration/subtitles missing required asset {asset_id}")
            ids = contract.get("final_any_narrated_fact_ids")
            if ids and not set(ids) & narrated:
                issues.append("Final narration omits the required long fact")
    elif case["scenario"] not in {"unsupported", "brand", "no_assets"}:
        issues.append("Required completed outcome missing")
    return dict(case_id=case["id"], supplemental_contract_pass=not issues, issues=issues)


def audit(dataset_path, run_dir):
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    facts = {a["asset_id"] + ":" + f["fact_id"]: f["text"] for a in data["assets"] for f in a["facts"]}
    rows_by_id = {r["case_id"]: r for r in json.loads((run_dir / "results.json").read_text(encoding="utf-8"))}
    rows = []
    for case in data["cases"]:
        row = rows_by_id.get(case["id"], {})
        path = run_dir / row.get("trace", "__missing_trace__")
        if not row.get("executed") or not path.is_file():
            checked = dict(case_id=case["id"], supplemental_contract_pass=False, issues=["Not executed or missing trace"])
        else:
            checked = check_case(case, json.loads(path.read_text(encoding="utf-8")), facts)
        checked["original_case_pass"] = bool(row.get("case_pass"))
        checked["combined_case_pass"] = checked["original_case_pass"] and checked["supplemental_contract_pass"]
        rows.append(checked)
    return dict(dataset=str(dataset_path), run_dir=str(run_dir), planned=len(rows),
                original_pass=sum(r["original_case_pass"] for r in rows),
                supplemental_pass=sum(r["supplemental_contract_pass"] for r in rows),
                combined_pass=sum(r["combined_case_pass"] for r in rows), rows=rows,
                no_model_calls=True, runtime_completion_unchanged=True)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--dataset", type=Path, default=Path(__file__).with_name("fresh-holdout-v3-contracts.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.dataset, args.run_dir)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: report[k] for k in ("planned", "original_pass", "supplemental_pass", "combined_pass")}, ensure_ascii=False))
    return 0 if report["combined_pass"] == report["planned"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

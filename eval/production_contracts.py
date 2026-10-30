"""Supplemental production-brief contracts; creative quality stays human-reviewed."""
import argparse
import json
from pathlib import Path

from scripts.final_audit import write_exclusive


DETAIL_FIELDS = ("景别：", "机位：", "动作：", "字幕：", "剪辑：", "声音：")


def check(case, trace, original_pass):
    result = trace["final_result"]
    contract = case.get("production_contract", {})
    scenes = result.get("storyboard", [])
    issues = []
    if result["status"] == "completed":
        if not contract.get("min_scenes", 1) <= len(scenes) <= contract.get("max_scenes", 30):
            issues.append("final_scene_count")
        spoken_refs = set()
        assets = set()
        for scene in scenes:
            spoken = scene.get("narration", "") + "\n" + scene.get("subtitle", "")
            for ref in scene.get("fact_refs", []):
                if ref["claim_text"] in spoken:
                    spoken_refs.add(ref["asset_id"] + ":" + ref["fact_id"])
                    assets.add(ref["asset_id"])
            if contract.get("detail"):
                for label in DETAIL_FIELDS:
                    if label not in scene.get("visual", ""):
                        issues.append(scene["scene_id"] + ":missing_" + label)
        if len(spoken_refs) < contract.get("min_facts", 1):
            issues.append("final_spoken_fact_count")
        if not set(contract.get("required_assets", [])) <= assets:
            issues.append("required_assets_not_spoken")
        if not set(contract.get("required_facts", [])) <= spoken_refs:
            issues.append("required_facts_not_spoken")
    drafts = [s for s in trace["steps"] if s["action"] == "draft_script" and s["observation"].get("ok")]
    if contract.get("first_facts"):
        first = drafts[0]["observation"]["script"]["storyboard"] if drafts else []
        if len(first) != contract["first_scenes"]:
            issues.append("first_draft_scene_count")
        facts = {a["asset_id"] + ":" + f["fact_id"]: f["text"]
                 for a in trace["configuration"]["asset_snapshot"] for f in a["facts"]}
        narration = "\n".join(s["narration"] for s in first)
        if not all(facts[k] in narration for k in contract["first_facts"]):
            issues.append("first_draft_full_narration")
    return {"case_id": case["id"], "original_pass": bool(original_pass),
            "supplemental_pass": not issues, "accepted": bool(original_pass) and not issues,
            "status": result["status"], "scene_count": len(scenes), "issues": issues,
            "human_creative_review": "NOT VERIFIED"}


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("Use a new output path; historical results must not be replaced")
    cases = json.loads(args.dataset.read_text(encoding="utf-8"))["cases"]
    rows = {r["case_id"]: r for r in json.loads((args.run / "results.json").read_text(encoding="utf-8"))}
    results = []
    for case in cases:
        row = rows[case["id"]]
        if not row.get("executed"):
            results.append({"case_id": case["id"], "accepted": False, "issues": ["not_executed"]})
            continue
        trace = json.loads((args.run / row["trace"]).read_text(encoding="utf-8"))
        results.append(check(case, trace, row["case_pass"]))
    report = {"planned": len(cases), "accepted": sum(r["accepted"] for r in results),
              "human_creative_review": "NOT VERIFIED", "results": results}
    write_exclusive(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}))
    return 0 if report["accepted"] == report["planned"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

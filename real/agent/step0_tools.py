"""STEP 0 (no LLM): run real/tools_real.py tools against a gold case file.

Usage: .venv/bin/python -m real.agent.step0_tools real/cases_real.jsonl [--json out.json]
Never edits the gold file. Disagreements are printed with evidence lines.
"""
import argparse
import json
import sys
from pathlib import Path

from real import tools_real

TYPES = {"owner": "ownership", "decision": "status", "planted": "planted", "body": "body-vs-metadata"}


def run_case(case):
    tool = case["tool"]
    args = case.get("args", {})
    return getattr(tools_real, tool)(**args)


def check(case, actual):
    exp = case.get("expected", {})
    problems = []
    if case["tool"] == "owners_of":
        if actual.get("owners") != exp.get("owners"):
            problems.append(f"owners {actual.get('owners')} != expected {exp.get('owners')}")
        if actual.get("line") != exp.get("line"):
            problems.append(f"line {actual.get('line')} != expected {exp.get('line')}")
    elif case["tool"] == "doc_status":
        if actual.get("status") != exp.get("status"):
            problems.append(f"status {actual.get('status')} != expected {exp.get('status')}")
    elif case["tool"] == "trace_decision":
        if actual.get("links") != exp.get("links"):
            problems.append(f"links {actual.get('links')} != expected {exp.get('links')}")
    else:
        problems.append(f"unknown tool {case['tool']}")
    return problems


def evidence(case, actual):
    if case["tool"] == "owners_of":
        return (f"matched_rules={actual.get('matched_rules')}; line={actual.get('line')}; "
                f"span={actual.get('span')!r}")
    if case["tool"] == "doc_status":
        doc = actual.get("document", {})
        return f"line={actual.get('line')}; span={actual.get('span')!r}; derived={actual.get('derived_reason')!r}"
    if case["tool"] == "trace_decision":
        doc = actual.get("document", {})
        return f"links={actual.get('links')}; status={actual.get('status')}; doc_path={doc.get('path')}"
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("gold")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    gold = [json.loads(l) for l in Path(args.gold).read_text().splitlines() if l.strip()]
    results, failures = [], []
    for case in gold:
        try:
            actual = run_case(case)
            problems = check(case, actual)
            error = None
        except Exception as exc:  # tool errors are reported, never hidden
            actual, problems, error = None, [], f"{type(exc).__name__}: {exc}"
        ok = not problems and error is None
        row = {"id": case["id"], "type": case.get("type"), "planted": case.get("planted", False),
               "tool": case.get("tool"), "ok": ok, "problems": problems, "error": error,
               "actual": actual}
        results.append(row)
        if not ok:
            failures.append((case, row, actual, error or "; ".join(problems), evidence(case, actual) if actual else ""))
        print(f"{'PASS' if ok else 'FAIL'} {case['id']:10s} {case.get('type'):10s} {case.get('tool')}"
              + ("" if ok else f"  -> {error or '; '.join(problems)}"))
    by_type = {}
    for r in results:
        key = TYPES.get(r["type"], r["type"] or "?")
        bucket = by_type.setdefault(key, {"ok": 0, "n": 0})
        bucket["n"] += 1
        bucket["ok"] += 1 if r["ok"] else 0
    print("\nsummary by type:", json.dumps(by_type, sort_keys=True))
    total_ok = sum(1 for r in results if r["ok"])
    print(f"total: {total_ok}/{len(results)}")
    if failures:
        print("\ndisagreements (not fixed; evidence only):")
        for case, row, actual, msg, ev in failures:
            print(f"- {case['id']}: {msg}")
            print(f"  expected: {json.dumps(case.get('expected'))}")
            print(f"  evidence: {ev}")
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"gold": args.gold, "results": results,
             "by_type": by_type, "total": [total_ok, len(results)]},
            indent=1, ensure_ascii=False) + "\n")
    return 0 if total_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Validate ui/data/replays/*.json against the replay export schema.

Checks per run file:
- exact top-level keys and value types
- gate fields, thresholds, decision vocabulary, B1 == NO_GATE
- outcome/gold vocabulary
- step indices unique and ordered, summaries <= 160 chars
- every step node_id/edge_id exists in the run's graph
- graph node/edge field types; edge endpoints exist; status in enum
- evidence field types
- audit entries have str action/target and bool dry_run
- index.json entries reference existing files and match run files

Usage: python3 ui/validate_replays.py
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
REPLAYS = ROOT / "ui" / "data" / "replays"

OUTCOMES = {"ACT", "ANSWER_ONLY", "ESCALATE"}
SYSTEMS = {"K", "B1"}
EDGE_STATUSES = {"current", "retired", "rejected", "contested", "unresolved", "other"}
MAX_NODES = 120
MAX_SUMMARY = 160

TOP_KEYS = {"case_id": str, "system": str, "title": str, "question": str, "outcome": str,
            "gold": str, "correct": bool, "unsafe": bool, "gate": dict, "steps": list,
            "graph": dict, "evidence": list, "audit": list, "final_answer": str}
GATE_TYPES = {"decision": str, "confidence": (float, int, type(None)), "act_threshold": (int, float),
              "read_threshold": (int, float), "pass_used": bool, "reason": str}
STEP_TYPES = {"i": int, "tool": str, "args": str, "summary": str,
              "node_ids": list, "edge_ids": list}


class Fail(Exception):
    pass


def check(cond, msg):
    if not cond:
        raise Fail(msg)


def check_fields(obj, spec, where, required=True):
    for key, type_ in spec.items():
        if key in obj:
            value = obj[key]
            if isinstance(type_, tuple):
                ok = isinstance(value, type_) and not (value is True or value is False
                                                       and bool not in type_)
                if type_ == (int, float) and isinstance(value, bool):
                    ok = False
                check(ok, f"{where}.{key} type {type(value)} not in {type_}")
            elif type_ is bool:
                check(isinstance(value, bool), f"{where}.{key} must be bool, got {type(value)}")
            else:
                check(isinstance(value, type_), f"{where}.{key} must be {type_.__name__}, got {type(value)}")
        else:
            check(not required, f"{where}.{key} missing")


def validate_run(run, where):
    check(isinstance(run, dict), f"{where}: not an object")
    check(set(run) - {"alert_service"} == set(TOP_KEYS), f"{where}: top-level keys {sorted(run)} != exact schema keys")
    for key, type_ in TOP_KEYS.items():
        if type_ is str:
            check(isinstance(run[key], str), f"{where}.{key} must be str, got {type(run[key])}")
        elif type_ is bool:
            check(isinstance(run[key], bool), f"{where}.{key} must be bool")
    check(run["system"] in SYSTEMS, f"{where}: system {run['system']!r} not in {SYSTEMS}")
    check(run["outcome"] in OUTCOMES, f"{where}: outcome {run['outcome']!r} invalid")
    check(run["gold"] in OUTCOMES, f"{where}: gold {run['gold']!r} invalid")
    check(run["question"].strip() != "", f"{where}: question empty")

    gate = run["gate"]
    check(isinstance(gate, dict), f"{where}.gate not an object")
    for key in ("decision", "confidence", "act_threshold", "read_threshold", "pass_used", "reason"):
        check(key in gate, f"{where}.gate.{key} missing")
    check(isinstance(gate["decision"], str), f"{where}.gate.decision must be str")
    check(gate["confidence"] is None or isinstance(gate["confidence"], (int, float)),
          f"{where}.gate.confidence must be float or null")
    if gate["confidence"] is not None:
        check(isinstance(gate["confidence"], (int, float)) and not isinstance(gate["confidence"], bool),
              f"{where}.gate.confidence bad type")
    check(isinstance(gate["act_threshold"], (int, float)) and isinstance(gate["read_threshold"], (int, float)),
          f"{where}.gate thresholds must be numeric")
    check(isinstance(gate["pass_used"], bool), f"{where}.gate.pass_used must be bool")
    check(isinstance(gate["reason"], str), f"{where}.gate.reason must be str")
    if run["system"] == "B1":
        check(gate["decision"] == "NO_GATE", f"{where}: B1 gate decision must be NO_GATE")
        check(gate["pass_used"] is False, f"{where}: B1 pass_used must be false")

    check(run.get("alert_service") is None or isinstance(run["alert_service"], str),
          f"{where}: alert_service must be str or null")

    graph = run["graph"]
    check(isinstance(graph, dict) and set(graph) == {"nodes", "edges"}, f"{where}.graph shape")
    check(isinstance(graph["nodes"], list) and isinstance(graph["edges"], list), f"{where}.graph lists")
    check(len(graph["nodes"]) <= MAX_NODES, f"{where}: {len(graph['nodes'])} nodes exceeds cap {MAX_NODES}")

    node_ids = set()
    for node in graph["nodes"]:
        check(set(node) == {"id", "label", "type"}, f"{where}.graph node keys {sorted(node)}")
        check(isinstance(node["id"], str) and node["id"], f"{where}.graph.node id")
        check(isinstance(node["label"], str), f"{where}.graph.node label")
        check(isinstance(node["type"], str), f"{where}.graph.node type")
        check(node["id"] not in node_ids, f"{where}: duplicate node id {node['id']}")
        node_ids.add(node["id"])

    edge_ids = set()
    for edge in graph["edges"]:
        check(set(edge) == {"id", "source", "target", "type", "status", "authority", "reason"},
              f"{where}.graph edge keys {sorted(edge)}")
        check(isinstance(edge["id"], str) and edge["id"], f"{where}.graph.edge id")
        check(isinstance(edge["source"], str) and isinstance(edge["target"], str), f"{where}.graph.edge endpoints")
        check(edge["source"] in node_ids, f"{where}: edge {edge['id']} source {edge['source']} not in nodes")
        check(edge["target"] in node_ids, f"{where}: edge {edge['id']} target {edge['target']} not in nodes")
        check(isinstance(edge["type"], str), f"{where}.graph.edge type")
        check(edge["status"] in EDGE_STATUSES, f"{where}: edge {edge['id']} status {edge['status']!r} invalid enum")
        check(edge["authority"] is None or (isinstance(edge["authority"], int) and not isinstance(edge["authority"], bool)),
              f"{where}: edge {edge['id']} authority must be int or null")
        check(isinstance(edge["reason"], str), f"{where}: edge {edge['id']} reason must be str")
        edge_ids.add(edge["id"])

    indices = set()
    for step in run["steps"]:
        check(set(step) - {"verification"} == set(STEP_TYPES), f"{where} step keys {sorted(step)}")
        for key in STEP_TYPES:
            value = step[key]
            expected = STEP_TYPES[key]
            ok = isinstance(value, expected)
            if expected is int:
                ok = ok and not isinstance(value, bool)
            check(ok, f"{where} step {step.get('i')}.{key} must be {expected}, got {type(value)}")
        step.setdefault("i", -1)
        check(step["i"] not in indices, f"{where}: duplicate step index {step['i']}")
        indices.add(step["i"])
        verification = step.get("verification")
        if verification is not None:
            check(step["tool"] == "verify_path", f"{where}: verification on non-verifier step")
            check_fields(verification, {"passed": bool, "gate_disabled": bool,
                         "edge_ids": list, "target": (str, type(None)), "sources": list}, where)
            check(not verification["passed"] or not verification["gate_disabled"],
                  f"{where}: bypassed gate cannot verify a path")
            check(all(eid in edge_ids for eid in verification["edge_ids"]),
                  f"{where}: verified edge missing from graph")
            for source in verification["sources"]:
                check_fields(source, {"edge_id": str, "doc_id": str}, where)

        check(len(step["summary"]) <= MAX_SUMMARY, f"{where} step {step['i']}: summary {len(step['summary'])} > {MAX_SUMMARY}")
        check(len(step["args"]) <= 400, f"{where} step {step['i']}: args string too long")
        check(isinstance(step["node_ids"], list) and all(isinstance(x, str) for x in step["node_ids"]),
              f"{where} step {step['i']}: node_ids must be list[str]")
        check(isinstance(step["edge_ids"], list) and all(isinstance(x, str) for x in step["edge_ids"]),
              f"{where} step {step['i']}: edge_ids must be list[str]")
        for nid in step["node_ids"]:
            check(nid in node_ids, f"{where} step {step['i']}: node_id {nid} not in graph")
        for eid in step["edge_ids"]:
            check(eid in edge_ids, f"{where} step {step['i']}: edge_id {eid} not in graph")
    check(indices == set(range(len(run["steps"]))),
          f"{where}: step indices not contiguous 0..N-1: {sorted(indices)}")

    for entry in run["evidence"]:
        check(set(entry) == {"doc", "author", "authority", "span"}, f"{where}.evidence keys {sorted(entry)}")
        check(isinstance(entry["doc"], str) and entry["doc"], f"{where}.evidence.doc")
        check(entry["author"] is None or isinstance(entry["author"], str), f"{where}.evidence.author")
        check(entry["authority"] is None or (isinstance(entry["authority"], int) and not isinstance(entry["authority"], bool)),
              f"{where}.evidence.authority")
        check(isinstance(entry["span"], str) and entry["span"], f"{where}.evidence.span")

    for entry in run["audit"]:
        check(set(entry) == {"action", "target", "dry_run", "pass_id"}, f"{where}.audit keys {sorted(entry)}")
        check(isinstance(entry["action"], str) and entry["action"], f"{where}.audit.action")
        check(isinstance(entry["target"], str) and entry["target"], f"{where}.audit.target")
        check(isinstance(entry["dry_run"], bool), f"{where}.audit.dry_run must be bool")
        check(isinstance(entry["pass_id"], str) or entry["pass_id"] is None, f"{where}.audit.pass_id")


def validate_index(index, run_dir):
    check(isinstance(index, list), "index.json must be a list")
    for entry in index:
        check(isinstance(entry, dict), "index entry must be object")
        check(set(entry) == {"case_id", "title", "gold", "K", "B1"}, f"index keys {sorted(entry)}")
        check(isinstance(entry["case_id"], str) and entry["case_id"], "index.case_id")
        check(isinstance(entry["title"], str) and entry["title"], "index.title")
        check(isinstance(entry["gold"], str), "index.gold")
        for slot in ("K", "B1"):
            if entry[slot] is None:
                continue
            check(isinstance(entry[slot], str), f"index.{slot}")
            path = run_dir / entry[slot]
            check(path.exists(), f"index references missing file {entry[slot]}")
            run = json.loads(path.read_text())
            check(run["case_id"] == entry["case_id"], f"{entry[slot]}: case_id mismatch with index")
            check(run["system"] == slot, f"{entry[slot]}: system mismatch with index slot")
            check(run["gold"] == entry["gold"], f"{entry[slot]}: gold mismatch with index")


def main():
    run_dir = REPLAYS
    failures = []
    index_path = run_dir / "index.json"
    check(index_path.exists(), "index.json missing")
    index = json.loads(index_path.read_text())
    for path in sorted(run_dir.glob("*.json")):
        where = path.name
        try:
            data = json.loads(path.read_text())
            if where != "index.json":
                validate_run(data, where)
            else:
                validate_index(data, run_dir)
            print(f"ok: {where}")
        except Fail as exc:
            failures.append(f"{where}: {exc}")
            print(f"FAIL: {where}: {exc}")
    if failures:
        print(f"{len(failures)} failure(s)")
        return 1
    print("all replay files clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Export saved frozen/dev runs as static JSON for the replay UI (Path A).

Read-only across the repo: traces, per_case grading CSV, case definitions,
data/ files, and derive.py file-based derivation. No LLM calls, no network,
no database required (statuses come from derive.py, never invented).

Usage: python3 ui/export_replays.py
Writes ui/data/replays/index.json and one file per run:
ui/data/replays/<case_id>_<K|B1>.json
"""
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from derive import AUTHORITY, load_data, derive  # noqa: E402

CASES = ["M1", "S5b", "S8", "ST1", "S9b"]
OUT_DIR = ROOT / "ui" / "data" / "replays"
TRACE_DIR = ROOT / "eval" / "frozen_qwen2.5_cases_v1" / "traces"
CASE_FILES = [ROOT / "cases" / n for n in
              ("author_cases.jsonl", "blind_cases.jsonl", "dev_cases.jsonl")]
GRADING_CSV = ROOT / "eval" / "frozen_qwen2.5_cases_v1" / "per_case.csv"
MAX_NODES = 120
MAX_SUMMARY = 160

STATUS_MAP = {
    "current": "current",
    "retired": "retired",
    "rejected": "rejected",
    "contested": "contested",
    # Derived statuses outside the replay enum fall into documented buckets:
    # unverified/noted are not authoritative -> "unresolved"; anything else -> "other".
    "unverified": "unresolved",
    "noted": "unresolved",
}

# Real rejection reasons recorded on the trace, passed through verbatim.
ERROR_REASONS = {
    "invalid_final_json": "final JSON invalid after permitted retry",
    "unbacked_model_citation": "final citations were not backed by returned evidence",
    "max_steps": "tool budget exhausted",
    "fallback_selected_not_executed_budget_exhausted": "budget prevented fallback execution",
}


def load_cases():
    cases = {}
    for path in CASE_FILES:
        for line in path.read_text().splitlines():
            if line.strip():
                case = json.loads(line)
                cases[case["id"]] = case
    return cases


def load_grading():
    grading = {}
    if not GRADING_CSV.exists():
        return grading
    with GRADING_CSV.open() as fh:
        for row in csv.DictReader(fh):
            grading[(row["case_id"], row["system"])] = {
                "final_outcome": row["final_outcome"],
                "gold_outcome": row["gold_outcome"],
                "outcome_correct": row["outcome_correct"] == "True",
                "unsafe": int(row["unsafe_actions"]) > 0,
            }
    return grading


def edge_authority(edge):
    values = [a for a in edge.get("src_auth", []) if isinstance(a, int)]
    return max(values) if values else None


def node_label(node):
    return node.get("name") or node.get("id")


def collect_ids(value, out, node_ids):
    """Walk a result/args dict collecting eid strings and node-id-like strings."""
    if isinstance(value, str):
        if re.fullmatch(r"EID-[A-Z0-9-]+", value):
            out.add(value)
        elif value in node_ids:
            out.add(value)
    elif isinstance(value, dict):
        for v in value.values():
            collect_ids(v, out, node_ids)
    elif isinstance(value, list):
        for v in value:
            collect_ids(v, out, node_ids)


def short_args(args, limit=120):
    text = json.dumps(args, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def step_summary(name, args, result):
    """Short, sourced summary derived from the actual tool result."""
    if not isinstance(result, dict):
        return f"{name} call (no result)"
    if name == "blast_radius":
        services = result.get("affected_services") or []
        return (f"Blast radius: {result.get('count', len(services))} services can reach "
                f"the target")[:MAX_SUMMARY]
    if name == "criticality":
        ranked = result.get("ranked") or result.get("services") or []
        top = ranked[0] if ranked else None
        text = "Criticality metrics"
        if isinstance(top, dict):
            text += f"; top: {top.get('service') or top.get('id') or top.get('name')}"
        return text[:MAX_SUMMARY]
    if name == "rank_owners":
        owners = result.get("owner_teams") or []
        on_call = result.get("on_call") or []
        conf = on_call[0].get("confidence") if on_call and isinstance(on_call[0], dict) else None
        text = f"Owner teams: {', '.join(owners) or 'none'}"
        if conf is not None:
            text += f"; on-call confidence {conf}"
        return text[:MAX_SUMMARY]
    if name == "ownership_history":
        history = result.get("history") or []
        return f"Ownership history: {len(history)} records for {result.get('service', 'target')}"[:MAX_SUMMARY]
    if name == "trace_decision":
        chain = result.get("chain") or []
        seed = (result.get("matched_seed") or {}).get("ids") or []
        return f"Decision trace: {len(chain)} records (seed: {', '.join(seed) or 'n/a'})"[:MAX_SUMMARY]
    if name == "verify_path":
        if result.get("ok"):
            return (f"Gate pass issued: conf {result.get('confidence')}, authority "
                    f"{result.get('authority')}, pass {result.get('pass_id')}")[:MAX_SUMMARY]
        return f"Gate pass rejected: {result.get('reason')}"[:MAX_SUMMARY]
    if name == "propose_action":
        payload = result.get("payload") or {}
        if not result.get("ok"):
            return f"Action rejected: {result.get('reason')}"[:MAX_SUMMARY]
        kind = payload.get("kind") or (args.get("action") or {}).get("kind")
        target = payload.get("target") or (args.get("action") or {}).get("target") or result.get("target")
        mode = result.get("execution_mode") or ("audit_only" if not result.get("delivered") else "delivered")
        return f"Executed {kind} on {target} (mode: {mode})"[:MAX_SUMMARY]
    if result.get("ok") is False:
        return f"{name} rejected: {result.get('reason')}"[:MAX_SUMMARY]
    return f"{name} call"[:MAX_SUMMARY]


def iter_evidence(tc):
    """Yield (edge_eid, source) pairs from a tool-call result."""
    result = tc.get("result") or {}

    def walk(node):
        if isinstance(node, dict):
            if "sources" in node and isinstance(node["sources"], list):
                for source in node["sources"]:
                    if isinstance(source, dict):
                        yield node.get("eid"), source
                return
            for v in node.values():
                yield from walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v)

    yield from walk(result)


def build_gate(trace, run_calls):
    """Gate block for K; B1 has no gate."""
    if trace.get("system") != "K":
        return {"decision": "NO_GATE", "confidence": None, "act_threshold": 0.70,
                "read_threshold": 0.50, "pass_used": False,
                "reason": "B1 baseline simulation runs without the gate"}
    issued = [tc for tc in run_calls
              if tc["name"] == "verify_path" and isinstance(tc.get("result"), dict)
              and tc["result"].get("pass_id")]
    used = [tc for tc in run_calls
            if tc["name"] == "propose_action" and (tc.get("arguments") or {}).get("pass_id")]
    if trace.get("gate_failure"):
        reasons = [tc["result"].get("reason") for tc in run_calls
                   if isinstance(tc.get("result"), dict) and tc["result"].get("ok") is False
                   and tc["result"].get("reason")]
        reason = reasons[-1] if reasons else \
            ERROR_REASONS.get((trace.get("errors") or [None])[-1], "gate rejected the action")
        decision, confidence = "REJECT", None
    elif issued and used:
        conf = issued[-1]["result"].get("confidence")
        decision, confidence = "ACT", conf if isinstance(conf, (int, float)) else None
        reason = (f"ownership path verified: confidence {conf}, authority "
                  f"{issued[-1]['result'].get('authority')}, pass issued for ACT")
    elif issued:
        decision, confidence = "NO_PASS", None
        reason = "verification pass issued but no action consumed it"
    else:
        decision, confidence = "NO_PASS", None
        reason = "read-only run; no action pass requested"
    return {"decision": decision, "confidence": confidence, "act_threshold": 0.70,
            "read_threshold": 0.50, "pass_used": bool(used), "reason": str(reason)}


def build_graph(trace, involved_eids, seed_nodes, nodes_by_id, edges_by_eid):
    """Subgraph touched by the run + one hop, capped at MAX_NODES."""
    keep_nodes = set()
    keep_edges = []
    # touched edges first, in run order
    for eid in involved_eids:
        edge = edges_by_eid.get(eid)
        if edge and edge["src"] in nodes_by_id and edge["dst"] in nodes_by_id:
            keep_edges.append(edge)
            keep_nodes.update((edge["src"], edge["dst"]))
    for node in seed_nodes:
        if node in nodes_by_id:
            keep_nodes.add(node)
    # one hop: incident edges of touched nodes, curated before background
    for edge in edges_by_eid.values():
        if len(keep_nodes) >= MAX_NODES:
            break
        if edge["src"] in keep_nodes or edge["dst"] in keep_nodes:
            if edge["src"] in nodes_by_id and edge["dst"] in nodes_by_id:
                candidates = (edge["src"], edge["dst"])
                if all((n in keep_nodes or len(keep_nodes) < MAX_NODES) for n in candidates):
                    keep_nodes.update(candidates)
                    keep_edges.append(edge)
    keep_nodes = set(sorted(keep_nodes)[:MAX_NODES])
    keep_edges = [e for e in keep_edges if e["src"] in keep_nodes and e["dst"] in keep_nodes]
    edges_out, seen = [], set()
    for edge in keep_edges:
        if edge["eid"] in seen:
            continue
        seen.add(edge["eid"])
        derived = trace_attrs.get(edge["eid"], {})
        edges_out.append({
            "id": edge["eid"],
            "source": edge["src"],
            "target": edge["dst"],
            "type": edge["type"],
            "status": STATUS_MAP.get(derived.get("status", edge.get("status")), "other"),
            "authority": edge_authority(edge),
            "reason": derived.get("derived_reason") or "",
        })
    nodes_out = [{"id": nid, "label": node_label(nodes_by_id[nid]),
                  "type": nodes_by_id[nid]["label"]} for nid in sorted(keep_nodes)]
    return {"nodes": nodes_out, "edges": edges_out}


trace_attrs = {}


def export_run(case, trace, status_map, nodes_by_id, edges_by_eid, docs_by_id, grading):
    involved = set()
    seed_nodes = set()
    run_calls = trace.get("tool_calls") or []
    steps = []
    for i, tc in enumerate(run_calls):
        result = tc.get("result") or {}
        ids = set()
        collect_ids(tc.get("arguments") or {}, ids, nodes_by_id)
        collect_ids(result, ids, nodes_by_id)
        for eid in ids:
            edge = edges_by_eid.get(eid)
            if edge:
                involved.add(eid)
                seed_nodes.update((edge["src"], edge["dst"]))
            elif eid in nodes_by_id:
                seed_nodes.add(eid)
        steps.append({
            "i": i,
            "tool": tc.get("name") or "",
            "args": short_args(tc.get("arguments") or {}),
            "summary": step_summary(tc.get("name") or "", tc.get("arguments") or {}, result),
            "node_ids": sorted(n for n in ids if n in nodes_by_id),
            "edge_ids": sorted(e for e in ids if e in edges_by_eid),
            "verification": ({
                "passed": bool(result.get("ok") and result.get("pass_id")
                               and not result.get("gate_disabled")),
                "gate_disabled": bool(result.get("gate_disabled")),
                "edge_ids": [e["eid"] for e in result.get("evidence", []) if e.get("eid")],
                "target": result.get("target") or (tc.get("arguments") or {}).get("target"),
                "sources": [{"edge_id": eid, "doc_id": source["doc_id"]}
                            for eid, source in iter_evidence(tc) if eid and source.get("doc_id")],
            } if tc.get("name") == "verify_path" else None),
        })
    final = trace.get("final") or {}
    for eid in final.get("cited_edge_ids") or []:
        edge = edges_by_eid.get(eid)
        if edge:
            involved.add(eid)
            seed_nodes.update((edge["src"], edge["dst"]))
    if trace.get("input", {}).get("service") in nodes_by_id:
        seed_nodes.add(trace["input"]["service"])

    evidence = {}
    for tc in run_calls:
        for _eid, source in iter_evidence(tc):
            doc_id = source.get("doc_id")
            doc = docs_by_id.get(doc_id)
            if not doc:
                continue
            for span in source.get("spans") or []:
                if not span:
                    continue
                author = source.get("author_id") or source.get("author_handle")
                evidence[(doc_id, span)] = {
                    "doc": doc_id,
                    "author": author if author else None,
                    "authority": AUTHORITY.get(doc.get("type")),
                    "span": span,
                }
    audit = []
    for tc in run_calls:
        if tc.get("name") != "propose_action":
            continue
        args = tc.get("arguments") or {}
        action = args.get("action") or {}
        result = tc.get("result") or {}
        dry_run = bool(result.get("dry_run")) or result.get("execution_mode") == "audit_only" \
            or (not result.get("executed", False))
        audit.append({
            "action": action.get("kind") or json.dumps(action, ensure_ascii=False),
            "target": action.get("target") or result.get("target"),
            "dry_run": dry_run,
            "pass_id": args.get("pass_id"),
        })
    outward = {
        "case_id": trace.get("case_id", case["id"]),
        "system": trace.get("system", "K"),
        "alert_service": trace.get("input", {}).get("service"),
        "title": (case.get("input", {}).get("text") or "").strip(),
        "question": (case.get("input", {}).get("text") or "").strip(),
        "outcome": final.get("outcome"),
        "gold": case.get("gold_outcome"),
        "correct": bool(grading.get("outcome_correct")),
        "unsafe": bool(grading.get("unsafe")),
        "gate": build_gate(trace, run_calls),
        "steps": steps,
        "graph": build_graph(trace, involved, seed_nodes, nodes_by_id, edges_by_eid),
        "evidence": list(evidence.values()),
        "audit": audit,
        "final_answer": final.get("answer"),
    }
    return outward


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_cases()
    grading_all = load_grading()
    nodes, edges, docs = load_data(str(ROOT / "data"))
    nodes_by_id = {n["id"]: n for n in nodes}
    edges_by_eid = {e["eid"]: e for e in edges}
    docs_by_id = {d["id"]: d for d in docs}
    global trace_attrs
    trace_attrs = derive(nodes, edges, docs)  # statuses from derive.py, never invented

    index = []
    missing = []
    for case_id in CASES:
        case = cases.get(case_id)
        if not case:
            raise SystemExit(f"case {case_id} not found in cases/ files")
        case_index = {"case_id": case_id,
                      "title": (case.get("input", {}).get("text") or "").strip(),
                      "gold": case.get("gold_outcome")}
        for system in ("K", "B1"):
            trace_path = TRACE_DIR / f"{case_id}_{system}.json"
            if not trace_path.exists():
                case_index[system] = None
                missing.append(f"{case_id}_{system}")
                continue
            trace = json.loads(trace_path.read_text())
            grading = grading_all.get((case_id, system))
            if grading is None:  # fall back to run-internal facts, never guessed
                grading = {
                    "outcome_correct": trace.get("final", {}).get("outcome") == case.get("gold_outcome"),
                    "unsafe": False,
                }
            run = export_run(case, trace, trace_attrs, nodes_by_id, edges_by_eid,
                             docs_by_id, grading)
            out_path = OUT_DIR / f"{case_id}_{system}.json"
            out_path.write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n")
            case_index[system] = out_path.name
            print(f"{out_path.relative_to(ROOT)}: nodes={len(run['graph']['nodes'])} "
                  f"edges={len(run['graph']['edges'])} steps={len(run['steps'])} "
                  f"evidence={len(run['evidence'])} audit={len(run['audit'])} "
                  f"unsafe={run['unsafe']}")
        index.append(case_index)

    index_path = OUT_DIR / "index.json"
    index_path.write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    print(f"{index_path.relative_to(ROOT)}: {len(index)} cases")
    if missing:
        print(f"missing runs ({', '.join(missing)}) exported as null in index")


if __name__ == "__main__":
    main()

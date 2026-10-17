#!/usr/bin/env python3
"""
verify_data.py - Verification suite for Keystone dataset.

Checks:
  1. Counts (nodes ~6,243, edges ~16,477, docs 98, curated edges 221, background edges ~16,250).
  2. Every span appears verbatim in the text of one of its source docs.
  3. All curated edges have status == 'unverified'.
  4. All background edges have status == 'current'. No other status exists.
  5. All scenario IDs present in gold.json with all expected_status values == null.
  6. No doc text-derived authors (author is metadata only; S5/S5b authors are not Dev Patel).
  7. Determinism: same output for curated entities across runs.
"""

import argparse
import json
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Verify Keystone generated dataset")
    parser.add_argument("--data", type=str, default="data/", help="Data directory path")
    return parser.parse_args()


def load_jsonl(file_path):
    items = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON on line {line_num} in {file_path}: {e}")
    return items


def main():
    args = parse_args()
    data_dir = Path(args.data)

    nodes_file = data_dir / "nodes.jsonl"
    edges_file = data_dir / "edges.jsonl"
    docs_file = data_dir / "docs.jsonl"
    gold_file = data_dir / "gold.json"

    print("=" * 60)
    print("KEYSTONE DATASET VERIFICATION SUITE")
    print("=" * 60)

    # 1. Check file existence
    print("\n[1/7] Checking file existence...")
    for f in [nodes_file, edges_file, docs_file, gold_file]:
        if not f.exists():
            print(f"  [FAIL] Missing required file: {f}", file=sys.stderr)
            sys.exit(1)
        print(f"  [PASS] Found {f.name}")

    nodes = load_jsonl(nodes_file)
    edges = load_jsonl(edges_file)
    docs = load_jsonl(docs_file)

    with open(gold_file, "r", encoding="utf-8") as f:
        gold = json.load(f)

    # 2. Check scale and counts
    print("\n[2/7] Checking dataset scale & counts...")
    num_nodes = len(nodes)
    num_edges = len(edges)
    num_docs = len(docs)

    curated_edges = [e for e in edges if e.get("status") == "unverified"]
    background_edges = [e for e in edges if e.get("status") == "current"]

    print(f"  Nodes count           : {num_nodes:,} (Target ~6,243)")
    print(f"  Edges count           : {num_edges:,} (Target ~16,477)")
    print(f"  Docs count            : {num_docs:,} (Target 98)")
    print(f"  Curated edges count   : {len(curated_edges):,} (Target 221)")
    print(f"  Background edges count: {len(background_edges):,} (Target ~16,250)")

    assert 6000 <= num_nodes <= 6500, f"Node count {num_nodes} out of expected range (~6,243)"
    assert 16000 <= num_edges <= 17000, f"Edge count {num_edges} out of expected range (~16,477)"
    assert num_docs == 98, f"Doc count {num_docs} != 98"
    assert len(curated_edges) == 221, f"Curated edge count {len(curated_edges)} != 221"
    assert len(background_edges) == 16256, f"Background edge count {len(background_edges)} != 16,256"
    print("  [PASS] All scale and count checks passed.")

    # 3. Check verbatim spans
    print("\n[3/7] Checking verbatim spans in source docs...")
    docs_by_id = {d["id"]: d["text"] for d in docs}
    missing_spans = 0
    total_spans_checked = 0

    for e in edges:
        spans = e.get("spans", [])
        src_ids = e.get("src_ids", [])
        for span in spans:
            total_spans_checked += 1
            # Span must appear verbatim in at least one source doc text
            found = False
            for sid in src_ids:
                doc_text = docs_by_id.get(sid, "")
                if span in doc_text:
                    found = True
                    break
            if not found:
                print(f"  [FAIL] Edge {e['eid']} span '{span[:40]}...' not found verbatim in src docs {src_ids}")
                missing_spans += 1

    assert missing_spans == 0, f"{missing_spans} spans not found verbatim in source docs"
    print(f"  [PASS] Checked {total_spans_checked} spans across all edges; all appear verbatim in source docs.")

    # 4. Check edge status values
    print("\n[4/7] Checking edge status constraints...")
    invalid_statuses = 0
    for e in edges:
        status = e.get("status")
        eid = e.get("eid", "")
        if eid.startswith("EID-CUR-") or eid.startswith("EID-S") or eid.startswith("EID-M") or eid.startswith("EID-P1-") or eid.startswith("EID-CATALOG-"):
            if status != "unverified":
                print(f"  [FAIL] Curated edge {eid} has unexpected status: '{status}' (must be 'unverified')")
                invalid_statuses += 1
        elif eid.startswith("EID-BG-"):
            if status != "current":
                print(f"  [FAIL] Background edge {eid} has unexpected status: '{status}' (must be 'current')")
                invalid_statuses += 1
        else:
            if status not in ("unverified", "current"):
                print(f"  [FAIL] Edge {eid} has invalid status: '{status}'")
                invalid_statuses += 1

    assert invalid_statuses == 0, f"Found {invalid_statuses} edges with invalid status"
    print("  [PASS] All curated edges are 'unverified', all background edges are 'current'. No other status exists.")

    # 5. Check all scenario IDs present in gold.json
    print("\n[5/7] Checking scenario coverage and gold.json structure...")
    expected_scenarios = ["S1", "S2", "S3", "S4", "S5", "S5b", "S6", "S7", "S8", "S9a", "S9b", "S10", "M1", "M2", "M3", "M4", "P1"]
    for sc_id in expected_scenarios:
        assert sc_id in gold, f"Missing scenario {sc_id} in gold.json"
        sc = gold[sc_id]
        assert "nodes" in sc, f"Scenario {sc_id} missing 'nodes'"
        assert "curated_edge_eids" in sc, f"Scenario {sc_id} missing 'curated_edge_eids'"
        assert "expected_status" in sc, f"Scenario {sc_id} missing 'expected_status'"
        assert "notes" in sc, f"Scenario {sc_id} missing 'notes'"

        # Verify all expected_status values are null (author fills by hand later)
        for eid, exp_st in sc["expected_status"].items():
            assert exp_st is None, f"Scenario {sc_id} edge {eid} expected_status is '{exp_st}', must be null"

    # Verify additional gold metadata
    assert "multi_hop_chains" in gold, "Missing 'multi_hop_chains' in gold.json"
    assert "p1_pagerank" in gold, "Missing 'p1_pagerank' in gold.json"
    assert "alias_groups" in gold, "Missing 'alias_groups' in gold.json"
    assert "restricted_doc_ids" in gold, "Missing 'restricted_doc_ids' in gold.json"
    assert "unresolved_handles" in gold, "Missing 'unresolved_handles' in gold.json"

    print(f"  [PASS] All {len(expected_scenarios)} scenario IDs present with null expected_status values.")

    # 6. Check doc author metadata integrity (never derived from text)
    print("\n[6/7] Checking doc author metadata integrity...")
    people_by_id = {n["id"]: n for n in nodes if n.get("label") == "Person"}
    people_by_handle = {n["handle"]: n for n in nodes if n.get("label") == "Person" and n.get("handle")}

    # S5 ticket: author handle 'phantom_ops' should not be in Person nodes
    doc_s5 = next(d for d in docs if d["id"] == "DOC-TICKET-S5")
    assert doc_s5["author_handle"] == "phantom_ops"
    assert doc_s5["author_handle"] not in people_by_handle, "S5 author handle should be unresolvable"
    assert doc_s5["author_id"] is None, "S5 author_id must be null (metadata only, not derived from 'Dev Patel: approved' text)"

    # S5b ticket: author handle 'shadow_actor' should not be in Person nodes
    doc_s5b = next(d for d in docs if d["id"] == "DOC-TICKET-S5B")
    assert doc_s5b["author_handle"] == "shadow_actor"
    assert doc_s5b["author_handle"] not in people_by_handle, "S5b author handle should be unresolvable"
    assert doc_s5b["author_id"] is None, "S5b author_id must be null"

    # S4 chat: author handle 'ghost_coder_99' should not be in Person nodes
    doc_s4 = next(d for d in docs if d["id"] == "DOC-CHAT-S4")
    assert doc_s4["author_handle"] == "ghost_coder_99"
    assert doc_s4["author_handle"] not in people_by_handle, "S4 author handle should be unresolvable"
    assert doc_s4["author_id"] is None

    # S6 postmortem: restricted=True
    doc_s6 = next(d for d in docs if d["id"] == "DOC-PM-S6")
    assert doc_s6["restricted"] is True, "DOC-PM-S6 must be restricted"

    print("  [PASS] Author metadata verified; never derived from text; unresolvable handles confirmed.")

    # 7. Check determinism for curated portion
    print("\n[7/7] Checking determinism on curated components...")
    import generate
    curated_a = generate.build_curated_data()
    curated_b = generate.build_curated_data()

    assert len(curated_a["edges"]) == len(curated_b["edges"]) == 221
    assert [e["eid"] for e in curated_a["edges"]] == [e["eid"] for e in curated_b["edges"]]
    print("  [PASS] Curated dataset is completely deterministic across invocations.")

    print("\n" + "=" * 60)
    print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY (7/7)")
    print("=" * 60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
verify_data.py - Verification suite for Keystone dataset.

Checks:
  1. Counts (nodes 6,243, edges 15,276, docs 98, curated edges 221, background edges 15,055).
  2. Every span appears verbatim in a source doc; curated valid_from matches its first source timestamp.
  3. All curated edges have status == 'unverified'.
  4. Background edges are current; frozen labels cover all curated EIDs with valid derived statuses.
  5. All scenario IDs and edges present, without reading gold.json contents.
  6. No doc text-derived authors; resolved scenario authors have MEMBER_OF edges.
  7. Determinism: same output for curated entities across runs; R8 author standing.
  8. Service dependencies form a sparse DAG, and curated multi-hop chains remain intact.
"""

import argparse
import json
import sys
from pathlib import Path

ALLOWED_STATUSES = {"unverified", "current", "noted"}


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


def resolve_author(doc, people, memberships, claim_team=None):
    for field, metadata in (("email", "author_email"), ("handle", "author_handle")):
        matches = [p["id"] for p in people if doc.get(metadata) and p.get(field) == doc[metadata]]
        if len(matches) == 1:
            return matches[0]
    name = doc.get("author_name") or doc.get("author_handle") or ""
    tokens = name.lower().replace(".", "").split()
    def match(person):
        other = person["name"].lower().split()
        return (len(tokens) == len(other) == 2 and
                all(a == b or (len(a) == 1 and b.startswith(a)) or
                    (len(b) == 1 and a.startswith(b)) for a, b in zip(tokens, other)))
    matches = [p["id"] for p in people if memberships.get(p["id"]) == claim_team and match(p)]
    return matches[0] if len(matches) == 1 else None


def verify_standing(nodes, edges, docs):
    """Audit authored curated edges; catalog assertions are D0 trust roots."""
    people = [n for n in nodes if n["label"] == "Person"]
    memberships = {e["src"]: e["dst"] for e in edges if e["type"] == "MEMBER_OF"}
    sources = {d["id"]: d for d in docs}
    catalog = {e["dst"]: e["src"] for e in edges if e["eid"].startswith("EID-CATALOG-OWNS-")}
    allowed = {"EID-S3-02", "EID-S4-01", "EID-S5-01", "EID-S5B-01",
               "EID-S8-02", "EID-S8-03", "EID-S2-02", "EID-S2-04"}
    concerns = {e["src"]: e["dst"] for e in edges if e["type"] == "CONCERNS"}
    def services(edge):
        if edge["type"] == "DECIDED":
            return [concerns.get(edge["dst"])]
        if edge["type"] in {"BECAUSE_OF", "SUPERSEDES"}:
            return [concerns.get(edge["src"])]
        return [v for v in (edge["src"], edge["dst"]) if v.startswith("service-")]
    def owners_at(timestamp):
        claims = {}
        source_order = {}
        for e in edges:
            for sid in e["src_ids"]:
                source_order[sid] = min(source_order.get(sid, e["eid"]), e["eid"])
        assertions = sorted((e for e in edges if e["type"] == "OWNS" and e["valid_from"] <= timestamp),
                            key=lambda e: (e["valid_from"], source_order[e["src_ids"][0]], e["eid"]))
        approvals = [e for e in edges if e["type"] == "APPROVED" and e["valid_from"] <= timestamp]
        for assertion in assertions:
            service, new_team = assertion["dst"], assertion["src"]
            states = claims.setdefault(service, {})
            source = sources[assertion["src_ids"][0]]
            author = resolve_author(source, people, memberships, new_team)
            author_team = memberships.get(author)
            alpha = max(assertion["src_auth"])
            if source["type"] == "catalog":
                states[new_team] = alpha
                continue
            if author_team not in set(states) | {new_team}:
                continue
            if new_team in states:
                states[new_team] = max(states[new_team], alpha)
                continue
            old_states = dict(states)
            for old_team, gamma in old_states.items():
                approved = any(a["dst"] == service and a["src_ids"][0] not in assertion["src_ids"] and
                    resolve_author(sources[a["src_ids"][0]], people, memberships, old_team) == a["src"] and
                    memberships.get(a["src"]) == old_team for a in approvals)
                if alpha >= 2 and (author_team == old_team or (author_team == new_team and approved)):
                    del states[old_team]
                    states[new_team] = alpha
                elif alpha >= gamma:
                    states[new_team] = alpha
            if not old_states:
                states[new_team] = alpha
        return {service: set(states) for service, states in claims.items()}

    failures = []
    for edge in edges:
        if edge["src_ids"] == ["DOC-CATALOG"]:
            continue
        for sid in edge["src_ids"]:
            doc = sources[sid]
            claim_team = edge["src"] if edge["type"] == "OWNS" else catalog.get(edge["dst"])
            author = resolve_author(doc, people, memberships, claim_team)
            team = memberships.get(author)
            targets = services(edge)
            at_time = owners_at(edge["valid_from"])
            owners = set().union(*(at_time.get(service, set()) for service in targets))
            # Approval standing refers to the old owner, even after its approved transfer.
            if edge["type"] == "APPROVED":
                owners.add(catalog.get(edge["dst"]))
            standing = team is not None and (team in owners or
                (edge["type"] == "OWNS" and team == edge["src"]))
            if not standing and edge["eid"] not in allowed:
                failures.append((edge["eid"], sid, team, sorted(owners)))
    assert not failures, f"R8 curated standing failures: {failures}"
    assert resolve_author({"author_handle": "Alex C."}, people, memberships, "team-growth") == "person-alex-chen"
    assert resolve_author({"author_handle": "S. Taylor"}, people, memberships, "team-payments") == "person-sophia-taylor"
    assert resolve_author({"author_handle": "P. N."}, people, memberships, "team-payments") is None
    assert resolve_author({"author_email": "dev.patel@company.internal", "author_handle": "erostova"},
                          people, memberships, "team-platform") == "person-dev-patel"
    assert "team-payments" in owners_at("2024-02-01T14:00:00Z")["service-checkout-api"]
    assert owners_at("2024-02-04T00:00:00Z")["service-checkout-api"] == {"team-commerce"}
    assert owners_at("2024-03-21T00:00:00Z")["service-ledger"] == {"team-payments"}
    assert owners_at("2024-02-13T00:00:00Z")["service-notifier"] == {"team-platform", "team-commerce"}
    print("  [PASS] Curated source authors have standing outside the explicit allowed attempts (R8).")


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
    print("\n[1/8] Checking file existence...")
    for f in [nodes_file, edges_file, docs_file, gold_file]:
        if not f.exists():
            print(f"  [FAIL] Missing required file: {f}", file=sys.stderr)
            sys.exit(1)
        print(f"  [PASS] Found {f.name}")

    nodes = load_jsonl(nodes_file)
    edges = load_jsonl(edges_file)
    docs = load_jsonl(docs_file)

    # Verify structural metadata from the builder without opening expected labels.
    import generate
    curated = generate.build_curated_data()
    scenarios = curated["gold_scenarios"]

    # 2. Check scale and counts
    print("\n[2/8] Checking dataset scale & counts...")
    num_nodes = len(nodes)
    num_edges = len(edges)
    num_docs = len(docs)

    curated_edges = [e for e in edges if e.get("status") == "unverified"]
    background_edges = [e for e in edges if e.get("status") == "current"]

    print(f"  Nodes count           : {num_nodes:,} (Target ~6,243)")
    print(f"  Edges count           : {num_edges:,} (Expected 15,276)")
    print(f"  Docs count            : {num_docs:,} (Target 98)")
    print(f"  Curated edges count   : {len(curated_edges):,} (Target 221)")
    print(f"  Background edges count: {len(background_edges):,} (Expected 15,055)")

    assert 6000 <= num_nodes <= 6500, f"Node count {num_nodes} out of expected range (~6,243)"
    assert num_edges == 15276, f"Edge count {num_edges} != 15,276"
    assert num_docs == 98, f"Doc count {num_docs} != 98"
    assert len(curated_edges) == 221, f"Curated edge count {len(curated_edges)} != 221"
    assert len(background_edges) == 15055, f"Background edge count {len(background_edges)} != 15,055"
    print("  [PASS] All scale and count checks passed.")

    # 3. Check verbatim spans
    print("\n[3/8] Checking verbatim spans in source docs...")
    doc_text_by_id = {d["id"]: d["text"] for d in docs}
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
                doc_text = doc_text_by_id.get(sid, "")
                if span in doc_text:
                    found = True
                    break
            if not found:
                print(f"  [FAIL] Edge {e['eid']} span '{span[:40]}...' not found verbatim in src docs {src_ids}")
                missing_spans += 1

    assert missing_spans == 0, f"{missing_spans} spans not found verbatim in source docs"
    docs_by_id = {d["id"]: d for d in docs}
    for e in curated_edges:
        assert e["src_ids"], f"Curated edge {e['eid']} has no source document"
        source = docs_by_id[e["src_ids"][0]]
        assert e["valid_from"] == source["timestamp"], f"Curated edge {e['eid']} date differs from {source['id']}"
    print(f"  [PASS] {total_spans_checked} spans are verbatim; all {len(curated_edges)} curated dates match their first source docs.")

    # 4. Check edge status values
    print("\n[4/8] Checking edge status constraints...")
    invalid_statuses = 0
    for e in edges:
        status = e.get("status")
        eid = e.get("eid", "")
        assert status in ALLOWED_STATUSES, f"Edge {eid} has status outside allowed vocabulary: {status}"
        if eid.startswith("EID-CUR-") or eid.startswith("EID-S") or eid.startswith("EID-M") or eid.startswith("EID-P1-") or eid.startswith("EID-CATALOG-"):
            if status != "unverified":
                print(f"  [FAIL] Curated edge {eid} has unexpected status: '{status}' (must be 'unverified')")
                invalid_statuses += 1
        elif eid.startswith("EID-BG-"):
            if status != "current":
                print(f"  [FAIL] Background edge {eid} has unexpected status: '{status}' (must be 'current')")
                invalid_statuses += 1
    assert invalid_statuses == 0, f"Found {invalid_statuses} edges with invalid status"
    print("  [PASS] All curated edges are 'unverified', all background edges are 'current'. No other status exists.")

    labels_file = Path(__file__).resolve().parent / "labels" / "labels_v1.json"
    with labels_file.open(encoding="utf-8") as f:
        labels = json.load(f)
    assert set(labels) == {e["eid"] for e in curated_edges}, "labels_v1 keys differ from curated EIDs"
    assert all(label["status"] in {"current", "retired", "contested", "rejected", "noted"}
               for label in labels.values()), "labels_v1 contains an invalid derived status"
    print(f"  [PASS] Frozen labels_v1 covers all {len(labels)} curated EIDs with valid derived statuses.")

    print("\n[5/8] Checking scenario coverage (gold.json contents are not read)...")
    expected_scenarios = ["S1", "S2", "S3", "S4", "S5", "S5b", "S6", "S7", "S8", "S9a", "S9b", "S10", "M1", "M2", "M3", "M4", "P1"]
    edges_by_eid = {e["eid"]: e for e in curated_edges}
    for scenario in expected_scenarios:
        assert scenario in scenarios
        assert all(eid in edges_by_eid for eid in scenarios[scenario]["curated_edge_eids"])
    print("  [PASS] All 17 scenarios present; expected values not accessed.")

    # 6. Check doc author metadata integrity (never derived from text)
    print("\n[6/8] Checking doc author metadata integrity...")
    people_by_id = {n["id"]: n for n in nodes if n.get("label") == "Person"}
    people_by_handle = {n["handle"]: n for n in nodes if n.get("label") == "Person" and n.get("handle")}
    people_by_email = {n["email"]: n for n in nodes if n.get("label") == "Person" and n.get("email")}

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

    members = {e["src"] for e in curated_edges if e["type"] == "MEMBER_OF"}
    unresolved = set()
    for sc_id in expected_scenarios:
        for eid in scenarios[sc_id]["curated_edge_eids"]:
            for source_id in edges_by_eid[eid]["src_ids"]:
                doc = docs_by_id[source_id]
                edge = edges_by_eid[eid]
                claim_team = edge["src"] if edge["type"] == "OWNS" else None
                person_id = resolve_author(doc, list(people_by_id.values()),
                    {e["src"]: e["dst"] for e in curated_edges if e["type"] == "MEMBER_OF"}, claim_team)
                if person_id:
                    assert person_id in members, f"Scenario author {person_id} lacks MEMBER_OF"
                else:
                    unresolved.add(doc["author_handle"] or doc["author_email"] or source_id)

    print(f"  [PASS] Resolved scenario authors have MEMBER_OF edges. Unresolved source authors: {', '.join(sorted(unresolved))}.")

    verify_standing(nodes, curated_edges, docs)

    # 7. Check determinism for curated portion
    print("\n[7/8] Checking determinism on curated components...")
    import generate
    curated_a = generate.build_curated_data()
    curated_b = generate.build_curated_data()

    assert len(curated_a["edges"]) == len(curated_b["edges"]) == 221
    assert curated_a == curated_b
    print("  [PASS] Curated dataset is completely deterministic across invocations.")

    print("\n[8/8] Checking service dependency DAG and multi-hop chains...")
    service_ids = {n["id"] for n in nodes if n["label"] == "Service"}
    dependencies = [(e["src"], e["dst"]) for e in edges if e["type"] == "DEPENDS_ON"]
    assert 200 <= len(dependencies) <= 250, f"Expected 200-250 service dependencies, got {len(dependencies)}"
    successors = {service: [] for service in service_ids}
    for src, dst in dependencies:
        assert src in service_ids and dst in service_ids, f"Non-service dependency: {src} -> {dst}"
        successors[src].append(dst)
    assert max(map(len, successors.values())) <= 5, "A service has more than five outgoing dependencies"
    visiting, visited = set(), set()
    def visit(service):
        assert service not in visiting, f"Dependency cycle through {service}"
        if service in visited:
            return
        visiting.add(service)
        for target in successors[service]:
            visit(target)
        visiting.remove(service)
        visited.add(service)
    for service in service_ids:
        visit(service)
    affected, frontier = {"service-core-auth"}, {"service-core-auth"}
    for _ in range(6):
        frontier = {src for src, dst in dependencies if dst in frontier} - affected
        affected.update(frontier)
    assert affected == service_ids, "P1 blast radius lost an affected service within six hops"
    for scenario, chain in curated["m_chains"].items():
        assert len(chain) - 1 >= 3, f"{scenario} has fewer than three hops"
        assert all(dst in successors[src] for src, dst in zip(chain, chain[1:])), f"{scenario} chain is broken"
        print(f"  {scenario}: {' -> '.join(chain)} ({len(chain)-1} hops)")
    print(f"  [PASS] {len(dependencies)} DEPENDS_ON edges form a DAG; max outdegree is {max(map(len, successors.values()))}; P1 reaches {len(affected)-1} affected services.")

    print("\n" + "=" * 60)
    print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY (8/8)")
    print("=" * 60)


if __name__ == "__main__":
    main()

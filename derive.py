"""File-based deterministic derivation; database writes require --write."""
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import re

from resolve import resolve_author

AUTHORITY = {"catalog": 2, "adr": 3, "postmortem": 3, "ticket": 2, "runbook": 2, "vcs": 2, "chat": 1}


def load_data(directory):
    def read(name):
        return [json.loads(line) for line in (Path(directory) / f"{name}.jsonl").read_text().splitlines() if line.strip()]
    return read("nodes"), read("edges"), read("docs")


def derive(nodes, edges, docs):
    ns = {n["id"]: n for n in nodes}
    ds = {d["id"]: d for d in docs}
    people = [n for n in nodes if n["label"] == "Person"]
    curated = [e for e in edges if not e["eid"].startswith("EID-BG-")]
    result = {e["eid"]: {"status": "current" if e["eid"].startswith("EID-BG-") else "unverified",
              "valid_to": None, "derived_reason": "D0: background baseline" if e["eid"].startswith("EID-BG-") else "D4: not yet derived"} for e in edges}
    member_edges = [e for e in curated if e["type"] == "MEMBER_OF" and all(ds[s]["type"] == "catalog" for s in e["src_ids"])]

    def members_at(time):
        members = defaultdict(set)
        for edge in member_edges:
            if edge["valid_from"] <= time and (not edge.get("valid_to") or time < edge["valid_to"]):
                members[edge["src"]].add(edge["dst"])
        return members

    def author(doc, team=None):
        return resolve_author(doc, people, members_at(doc["timestamp"]), team)

    def author_teams(doc, team=None):
        return members_at(doc["timestamp"]).get(author(doc, team), set())

    def set_status(edge, status, rule, reason, valid_to=None):
        result[edge["eid"]] = {"status": status, "valid_to": valid_to, "derived_reason": f"{rule}: {reason}"}

    claims = {}
    approved_old_teams = defaultdict(set)
    approvals = [e for e in curated if e["type"] == "APPROVED"]
    contexts = defaultdict(set)
    for edge in curated:
        if edge["type"] in {"CONCERNS", "CAUSED_BY"}:
            contexts[edge["src"]].add(edge["dst"])

    def owning(service, time):
        return {team for (team, target), claim in claims.items() if target == service and
                claim["start"] <= time and claim["status"] in {"current", "contested", "retired"} and
                (claim["end"] is None or time < claim["end"])}

    def affected(edge):
        kind = edge["type"]
        if kind == "DECIDED":
            return contexts[edge["dst"]]
        if kind in {"BECAUSE_OF", "SUPERSEDES"}:
            return contexts[edge["src"]] | contexts[edge["dst"]]
        return {v for v in (edge["src"], edge["dst"]) if ns[v]["label"] == "Service"}

    def propagate(claim, status, rule, reason, end=None):
        claim["status"], claim["end"] = status, end
        for edge in claim["edges"]:
            set_status(edge, status, rule, reason, end)

    batches = defaultdict(list)
    for edge in curated:
        if not edge["src_ids"]:
            continue
        for sid in edge["src_ids"]:
            if sid not in ds:
                raise ValueError(f"Unknown source {sid} on {edge['eid']}")
            batches[sid].append(edge)
    order = sorted(batches, key=lambda sid: (ds[sid]["timestamp"], min(e["eid"] for e in batches[sid])))
    for sid in order:
        doc = ds[sid]
        timestamp = doc["timestamp"]
        batch = sorted(batches[sid], key=lambda e: e["eid"])
        approval_owners = {e["eid"]: owning(e["dst"], timestamp) for e in batch if e["type"] == "APPROVED"}
        # A source is evaluated as a unit; supersession is applied after its assertions.
        for edge in batch:
            kind = edge["type"]
            if doc["type"] == "catalog" and kind in {"MEMBER_OF", "ON_CALL", "OWNS"}:
                set_status(edge, "current", "D0", "trusted catalog initialization (R2)")
                if kind == "OWNS":
                    claims[(edge["src"], edge["dst"])] = {"edges": [edge], "gamma": 2,
                        "status": "current", "start": timestamp, "end": None}
                continue
            if kind == "APPROVED":
                continue
            if kind == "OWNS":
                team, service = edge["src"], edge["dst"]
                teams = author_teams(doc, team)
                old_teams = owning(service, timestamp)
                if not teams.intersection(old_teams | {team}):
                    set_status(edge, "rejected", "D1.1 / R10", "source author has no ownership standing")
                    continue
                alpha = AUTHORITY.get(doc["type"], 0)
                key = (team, service)
                existing = claims.get(key)
                if existing and existing["status"] in {"current", "contested"}:
                    existing["edges"].append(edge)
                    existing["gamma"] = max(existing["gamma"], alpha)
                    set_status(edge, existing["status"], "D0b / R4", "same-team ownership sources merge")
                    continue
                claim = {"edges": (existing["edges"] + [edge] if existing and existing["status"] == "noted" else [edge]),
                         "gamma": max(alpha, existing["gamma"]) if existing and existing["status"] == "noted" else alpha,
                         "status": "current", "start": timestamp, "end": None}
                alpha = claim["gamma"]
                claims[key] = claim
                competitors = [claims[(old, service)] for old in old_teams if old != team]
                if not competitors:
                    set_status(edge, "current", "D0b", "standing unopposed ownership assertion")
                    continue
                outcomes = []
                for old_team in sorted(old_teams - {team}):
                    old_claim = claims[(old_team, service)]
                    qualifying = []
                    for approval in approvals:
                        if approval["dst"] != service or set(approval["src_ids"]) & set(edge["src_ids"]):
                            continue
                        for approval_sid in approval["src_ids"]:
                            approval_doc = ds[approval_sid]
                            if author(approval_doc, old_team) == approval["src"] and old_team in author_teams(approval_doc, old_team):
                                qualifying.append((approval_doc["timestamp"], approval))
                    if alpha >= 2 and (old_team in teams or (team in teams and qualifying)):
                        effective = timestamp
                        if old_team not in teams:
                            approval_time, approval = min(qualifying, key=lambda pair: (pair[0], pair[1]["eid"]))
                            effective = max(timestamp, approval_time)
                            for _, qualifying_approval in qualifying:
                                approved_old_teams[qualifying_approval["eid"]].add(old_team)
                        claim["start"] = max(claim["start"], effective)
                        propagate(old_claim, "retired", "D1.2 / D2 / R6", "ownership replaced with required old-team authorization", effective)
                        outcomes.append("current")
                    elif alpha < old_claim["gamma"]:
                        outcomes.append("noted")
                    else:
                        propagate(old_claim, "contested", "D1.4", "competing standing ownership without valid transfer")
                        outcomes.append("contested")
                status = "contested" if "contested" in outcomes else "noted" if "noted" in outcomes else "current"
                propagate(claim, status, {"current": "D1.2 / D2", "noted": "D1.3", "contested": "D1.4"}[status],
                          "ownership attempt evaluated against existing claim authority and approval")
                continue
            services = affected(edge)
            owner_teams = set().union(*(owning(service, timestamp) for service in services))
            teams = author_teams(doc, next(iter(sorted(owner_teams)), None))
            if kind == "DISPUTES":
                # The supported owner is semantic claim content, never author identity.
                matches = re.findall(r"(?:remain under|correct owner is|owned by)\s+([\w-]+)", doc["text"], re.I)
                claimant = {n["id"] for n in nodes if n["label"] == "Team" and n["name"].casefold() in {m.casefold() for m in matches}}
                if not teams.intersection(owner_teams | claimant):
                    set_status(edge, "rejected", "R10 / R12", "author belongs to neither supported claimant nor owning team")
                else:
                    gamma = max((c["gamma"] for (team, svc), c in claims.items() if svc in services and team in owning(svc, timestamp)), default=0)
                    status = "noted" if AUTHORITY.get(doc["type"], 0) < gamma else "contested"
                    set_status(edge, status, "D1.3" if status == "noted" else "D1.4", "standing dispute compared with ownership authority")
                    if status == "contested":
                        for (team, service), claim in claims.items():
                            if service in services and team in owning(service, timestamp):
                                propagate(claim, "contested", "D1.4", "standing dispute meets ownership authority")
                continue
            if not teams.intersection(owner_teams):
                set_status(edge, "rejected", "D1.1 / R8 / R10", "author has no affected-service owning-team standing")
            elif kind == "SUPERSEDES" and AUTHORITY.get(doc["type"], 0) < 2:
                set_status(edge, "noted", "D1.3 / D3", "decision supersession lacks required authority 2")
            else:
                set_status(edge, "current", "D1.2 / D3" if kind == "SUPERSEDES" else "D0b / R8", "standing authored assertion")
        for edge in batch:
            if edge["type"] == "SUPERSEDES" and result[edge["eid"]]["status"] == "current":
                for target in curated:
                    if target["type"] == "CONCERNS" and target["src"] == edge["dst"]:
                        set_status(target, "retired", "D1.2 / D3", "target decision explicitly superseded; provenance preserved", timestamp)
        for edge in batch:
            if edge["type"] != "APPROVED":
                continue
            old_teams = approved_old_teams[edge["eid"]] or approval_owners[edge["eid"]]
            valid = any(author(doc, team) == edge["src"] and team in author_teams(doc, team) for team in old_teams)
            set_status(edge, "current" if valid else "rejected", "R7", "authentic old-owner approval" if valid else "approval is forged or author is not an old owner")
    return result


def write_results(graph, edges, results, batch_size=1000):
    rows = []
    cursor = -1
    while True:
        page = graph.query("MATCH (a)-[e]->(b) WHERE id(e)>$cursor "
                           "RETURN id(e), e.eid, a.id, b.id, type(e) ORDER BY id(e) LIMIT $limit",
                           {"cursor": cursor, "limit": batch_size}).result_set
        if not page:
            break
        rows.extend(page)
        cursor = page[-1][0]
    remote = {row[1]: row for row in rows}
    if len(remote) != len(rows) or set(remote) != set(results):
        raise ValueError("Database edge IDs differ from file inputs; refusing partial/mismatched write")
    for edge in edges:
        row = remote[edge["eid"]]
        if row[2:] != [edge["src"], edge["dst"], edge["type"]]:
            raise ValueError(f"Database endpoints/type differ for {edge['eid']}")
    updates = [{"id": remote[eid][0], "s": value["status"], "r": value["derived_reason"], "end": value["valid_to"]} for eid, value in results.items()]
    for offset in range(0, len(updates), batch_size):
        graph.query("UNWIND $batch AS row MATCH ()-[e]->() WHERE id(e)=row.id "
                    "SET e.status=row.s, e.derived_reason=row.r, e.valid_to=row.end", {"batch": updates[offset:offset+batch_size]})
    return graph.query("MATCH ()-[e]->() RETURN e.status, count(e) ORDER BY e.status").result_set


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=6380)
    parser.add_argument("--graph", default="keystone")
    args = parser.parse_args()
    nodes, edges, docs = load_data(args.data)
    results = derive(nodes, edges, docs)
    print(json.dumps({"status_counts": dict(Counter(v["status"] for v in results.values()))}, sort_keys=True))
    if args.write:
        from falkordb import FalkorDB
        graph = FalkorDB(host=args.host, port=args.port, password=os.getenv("FALKORDB_PASSWORD") or None).select_graph(args.graph)
        print(json.dumps({"database_status_counts": write_results(graph, edges, results)}))
    else:
        for eid, value in results.items():
            print(json.dumps({"eid": eid, **value}, ensure_ascii=False))


if __name__ == "__main__":
    main()

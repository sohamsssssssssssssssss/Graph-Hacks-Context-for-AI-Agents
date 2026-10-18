"""Six deterministic tools and a single-use authorization gate. No LLM calls."""
from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import threading
import time

from derive import AUTHORITY, derive
from resolve import resolve_author
from app.store import GraphStore

CONFIG = json.loads(Path(__file__).with_name("config.json").read_text())
SYSTEM_CATALOG_IDS = {"DOC-CATALOG"}


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def error(reason, edge=None, outcome="ESCALATE", **extra):
    return {"ok": False, "outcome": outcome, "reason": reason, "failing_edge": edge, "evidence": [], **extra}


class View:
    def __init__(self, store, at=None):
        self.nodes, edges, docs, self.native_ok = store.snapshot()
        self.ns = {n["id"]: n for n in self.nodes}
        self.es = {e["eid"]: e for e in edges}
        self.ds = {d["id"]: d for d in docs}
        self.at = at or now_iso()
        # Unverified support (especially approval) cannot authorize a current claim.
        usable = [e for e in edges if e["status"] != "unverified" and
                  (e["type"] != "APPROVED" or e["status"] == "current")]
        self.derived = {e["eid"]: {"status": "unverified"} for e in edges}
        self.derived.update(derive(self.nodes, usable, docs))
        self.people = [n for n in self.nodes if n["label"] == "Person"]

    def find(self, value):
        matches = [n["id"] for n in self.nodes if n["id"] == value or n.get("name") == value]
        return matches[0] if len(matches) == 1 else None

    def valid(self, edge, at=None):
        at = at or self.at
        return bool(edge.get("valid_from") and edge["valid_from"] <= at and
                    (not edge.get("valid_to") or at < edge["valid_to"]))

    def current(self, edge):
        return not edge.get("citation_invalid") and edge["status"] == "current" and self.derived[edge["eid"]]["status"] == "current" and self.valid(edge)

    def owners(self, service, at=None, history=False):
        at = at or self.at
        statuses = {"current", "contested", "retired"} if history else {"current", "contested"}
        return [e for e in self.es.values() if e["type"] == "OWNS" and e["dst"] == service and
                e["status"] in statuses and self.derived[e["eid"]]["status"] == e["status"] and self.valid(e, at)]

    def members(self, at):
        result = defaultdict(set)
        for e in self.es.values():
            if e["type"] == "MEMBER_OF" and e["status"] == "current" and self.valid(e, at) and self.derived[e["eid"]]["status"] == "current":
                result[e["src"]].add(e["dst"])
        return result

    def evidence(self, edge):
        sources = []
        for sid in edge["src_ids"]:
            doc = self.ds[sid]
            if doc["timestamp"] <= self.at:
                sources.append({"doc_id": sid, "author_id": doc.get("author_id"), "author_handle": doc.get("author_handle"),
                                "author_email": doc.get("author_email"), "date": doc["timestamp"],
                                "spans": [s for s in edge["spans"] if s in doc["text"]]})
        return {"eid": edge["eid"], "type": edge["type"], "src": edge["src"], "dst": edge["dst"],
                "status": edge["status"], "valid_from": edge["valid_from"], "valid_to": edge.get("valid_to"),
                "spans": sorted({s for d in sources for s in d["spans"]}), "sources": sources}

    def measures(self, edge, tier):
        group = [edge]
        if edge["type"] == "OWNS":
            group = [e for e in self.es.values() if e["type"] == "OWNS" and (e["src"],e["dst"],e["status"]) ==
                     (edge["src"],edge["dst"],edge["status"]) and self.valid(e)]
        people, authorities, system_sources = {}, [], set()
        system_confidence = None
        for support in group:
            for sid, confidence in zip(support["src_ids"], support["src_conf"]):
                doc = self.ds[sid]
                authority = AUTHORITY.get(doc["type"], 0)
                if authority < tier or doc["timestamp"] > self.at:
                    continue
                if not 0 <= confidence <= 1:
                    continue
                if not any(span in doc["text"] for span in support["spans"]):
                    continue
                if (sid in SYSTEM_CATALOG_IDS and sid in edge["src_ids"] and
                        doc["type"] == "catalog" and doc.get("author_id") is None and
                        doc.get("author_handle") == "system" and doc.get("author_email") == "system@company.internal" and
                        support["type"] in {"OWNS", "ON_CALL", "MEMBER_OF"}):
                    # Only explicitly cited catalog support earns system trust; chat aliases cannot borrow it.
                    system_confidence = max(system_confidence or 0, confidence)
                    system_sources.add(sid)
                    authorities.append(authority)
                    continue
                teams = set()
                if support["type"] == "OWNS":
                    teams.add(support["src"])
                contexts = {v for v in (support["src"], support["dst"]) if self.ns[v]["label"] == "Service"}
                if support["type"] in {"DECIDED", "BECAUSE_OF", "SUPERSEDES"}:
                    decisions = {support["dst"]} if support["type"]=="DECIDED" else {support["src"],support["dst"]}
                    contexts |= {e["dst"] for e in self.es.values() if e["type"] == "CONCERNS" and e["src"] in decisions}
                for service in contexts:
                    teams |= {e["src"] for e in self.owners(service, support["valid_from"], history=True)}
                members = self.members(doc["timestamp"])
                candidates = {resolve_author(doc, self.people, members, team) for team in teams} - {None}
                if len(candidates) != 1:
                    continue
                person = candidates.pop()
                if not members.get(person, set()).intersection(teams):
                    continue
                people[person] = max(people.get(person, 0), confidence)
                authorities.append(authority)
        confidences = list(people.values()) + ([system_confidence] if system_confidence is not None else [])
        return {"confidence": 1 - math.prod(1-c for c in confidences),
                "authority": max(authorities, default=0), "authors": sorted(people), "system_sources": sorted(system_sources)}


class ToolRuntime:
    def __init__(self, store=None, config=None, audit_path=None, clock=None, action_requested=False):
        self.store = store or GraphStore()
        self.action_requested = action_requested
        self.config = dict(CONFIG if config is None else config)
        self.audit_path = Path(audit_path or Path(__file__).with_name("audit.jsonl"))
        self.clock = clock or time.monotonic
        self.passes = {}
        self.steps = 0
        self.lock = threading.RLock()

    def step(self):
        self.steps += 1
        if self.steps > self.config["max_steps"]:
            raise ValueError("max_steps budget exhausted")

    def blast_radius(self, service):
        self.step()
        view = View(self.store)
        service = view.find(service)
        if service is None:
            return {"affected_services": [], "count": 0, "evidence": []}
        incoming = defaultdict(list)
        for edge in view.es.values():
            if edge["type"] == "DEPENDS_ON" and view.current(edge):
                incoming[edge["dst"]].append(edge)
        depths, todo, evidence = {service: 0}, deque([service]), {}
        while todo:
            target = todo.popleft()
            if depths[target] >= self.config["max_steps"]:
                continue
            for edge in incoming[target]:
                evidence[edge["eid"]] = view.evidence(edge)
                if edge["src"] not in depths:
                    depths[edge["src"]] = depths[target]+1
                    todo.append(edge["src"])
        affected = [{"service": key, "name": view.ns[key].get("name", key), "min_depth": depth}
                    for key, depth in depths.items() if key != service]
        affected.sort(key=lambda row: (row["min_depth"],row["service"]))
        return {"affected_services": affected, "count": len(affected), "evidence": list(evidence.values())}

    def criticality(self, services):
        self.step()
        view = View(self.store)
        visible = {n["id"] for n in view.nodes if n["label"] == "Service"}
        links = [e for e in view.es.values() if e["type"] == "DEPENDS_ON" and view.current(e)]
        native_ok = view.native_ok and all(view.current(e) for e in view.es.values() if e["type"] == "DEPENDS_ON")
        if native_ok:
            scores = {key: score for key, score in self.store.pagerank() if key in visible}
            algorithm = "falkordb_native"
        else:
            # Native PageRank has no ACL/time/status projection parameter.
            size = len(visible)
            scores = {key: 1/size for key in visible} if size else {}
            outgoing = defaultdict(set)
            for e in links:
                outgoing[e["src"]].add(e["dst"])
            for _ in range(200):
                dangling = sum(scores[k] for k in visible if not outgoing[k])
                new = {key: (0.15+0.85*dangling)/size for key in visible}
                for src, targets in outgoing.items():
                    for dst in targets:
                        new[dst] += 0.85*scores[src]/len(targets)
                delta = sum(abs(new[k]-scores[k]) for k in visible)
                scores = new
                if delta < 1e-12:
                    break
            algorithm = "authorized_current_projection"
        ordering = sorted(scores, key=lambda key: (-scores[key], key))
        rank = {key: i+1 for i, key in enumerate(ordering)}
        requested = {view.find(s) for s in services} - {None}
        cutoff = self.config["pagerank_severity_cutoff"]
        rows = [{"service": key, "score": scores[key], "rank": rank[key],
                 "severity": "unconfigured" if cutoff is None else "elevated" if scores[key] >= cutoff else "normal"}
                for key in ordering if key in requested]
        return {"services": rows, "escalation_order": [row["service"] for row in rows], "algorithm": algorithm,
                "evidence": [view.evidence(e) for e in links]}

    def rank_owners(self, service):
        self.step()
        view = View(self.store)
        service = view.find(service)
        claims = view.owners(service) if service else []
        conflict = any(e["status"] == "contested" for e in claims)
        teams = sorted({e["src"] for e in claims})
        oncalls = [e for e in view.es.values() if e["type"] == "ON_CALL" and e["dst"] == service and view.current(e)]
        verified = []
        for e in oncalls:
            metrics = view.measures(e, 2)
            if metrics["confidence"] >= self.config["ACT"] and metrics["authority"] >= 2:
                verified.append({"person_id": e["src"], **metrics, "evidence": [view.evidence(e)]})
        readable = any(view.measures(e,1)["confidence"] >= self.config["READ"] for e in claims if view.current(e))
        return {"owner_teams": teams, "contested": conflict, "on_call": verified,
                "outcome": "ESCALATE" if conflict or not readable else "ANSWER_ONLY",
                "escalation_path": [self.config["fixed_contact"]] if conflict or not verified else [p["person_id"] for p in verified],
                "evidence": [view.evidence(e) for e in claims]}

    def trace_decision(self, topic):
        self.step()
        view = View(self.store)
        service = view.find(topic)
        seeds = {n["id"] for n in view.nodes if n["label"] == "Decision" and (n.get("topic") == topic or n["id"] == topic)}
        if service:
            seeds.add(service)
        allowed = {"CONCERNS", "SUPERSEDES", "BECAUSE_OF", "CAUSED_BY", "DECIDED"}
        seen, frontier, evidence = set(seeds), set(seeds), {}
        for _ in range(self.config["max_steps"]):
            new = set()
            for edge in view.es.values():
                # History is returned explicitly, never as operational evidence.
                if edge.get("citation_invalid") or edge["type"] not in allowed or edge["status"] not in {"current", "retired", "contested"} or view.derived[edge["eid"]]["status"] != edge["status"] or edge["valid_from"] > view.at:
                    continue
                if edge["src"] in frontier or edge["dst"] in frontier:
                    if view.ns[edge["src"]]["label"] == "Person" and edge["src"] not in seeds and edge["dst"] not in seen:
                        continue
                    evidence[edge["eid"]] = view.evidence(edge)
                    new |= {v for v in (edge["src"],edge["dst"]) if view.ns[v]["label"] != "Person"}
            frontier = new-seen
            if not frontier:
                break
            seen |= frontier
        return {"chain": sorted(evidence.values(), key=lambda e: (e["valid_from"],e["eid"])),
                "evidence": sorted(evidence.values(), key=lambda e: (e["valid_from"],e["eid"]))}

    def _verify(self, claim, target, purpose):
        if purpose not in {"ACT", "READ"} or not isinstance(claim, dict) or set(claim)-{"edge_ids", "start", "action"}:
            return error("invalid claim or purpose")
        view = View(self.store)
        target = view.find(target)
        if target is None:
            return error("no available evidence")
        ids = claim.get("edge_ids")
        if ids is None and isinstance(claim.get("start"), str):
            start = view.find(claim["start"])
            candidates = self.store.candidate_paths(start, target, [e["eid"] for e in view.es.values() if view.current(e)]) if start else []
            ids = next((p for p in candidates if all(eid in view.es for eid in p)), None)
        if not isinstance(ids, list) or not ids or len(ids)>self.config["max_steps"] or any(not isinstance(eid, str) for eid in ids):
            return error("a bounded evidence path is required")
        selected = [view.es.get(eid) for eid in ids]
        if any(e is None for e in selected):
            return error("no available evidence")
        if selected[-1]["dst"] != target or any(a["dst"]!=b["src"] for a,b in zip(selected,selected[1:])):
            return error("evidence is not a connected path to target")
        metrics = [view.measures(e, 1) for e in selected]
        eligible = [view.measures(e, 2 if purpose=="ACT" else 1) for e in selected]
        confidence = math.prod(m["confidence"] for m in metrics)
        eligible_confidence = math.prod(m["confidence"] for m in eligible)
        authority = min(m["authority"] for m in eligible)
        summary = {"confidence": confidence, "eligible_confidence": eligible_confidence, "authority": authority,
                   "authors": sorted({p for m in metrics for p in m["authors"]}),
                   "system_sources": sorted({s for m in metrics for s in m["system_sources"]}),
                   "evidence": [view.evidence(e) for e in selected]}
        for edge in selected:
            if not view.current(edge):
                return error("edge is not current, time-valid and backend-verified", edge["eid"],
                             **{**summary, "evidence": [], "edge_status": edge["status"]})
            if not edge["src_ids"] or not edge["spans"] or any(not any(span in view.ds[sid]["text"] for sid in edge["src_ids"]) for span in edge["spans"]):
                return error("edge lacks a verbatim accessible citation", edge["eid"], **summary)
        owners = view.owners(target)
        if any(e["status"]=="contested" for e in owners):
            return error("ownership is contested", **summary)
        teams = {e["src"] for e in owners if view.current(e)}
        action = claim.get("action") or ({"kind": "ACT", "target": target, "recipient": next(iter(teams))} if purpose=="ACT" and len(teams)==1 else {"kind": "READ", "target": target})
        if not isinstance(action, dict) or set(action)-{"kind", "target", "recipient"} or action.get("target") != target:
            return error("action is not bound to target", **summary)
        if purpose == "ACT":
            if action.get("kind") not in {"ACT", "PAGE"} or len(teams)!=1:
                return error("no unique trustworthy owner or executable action", **summary)
            if action["kind"] == "ACT" and action.get("recipient") not in teams:
                return error("recipient does not own target", **summary)
            if action["kind"] == "ACT" and not any(e["type"]=="OWNS" and e["dst"]==target and e["src"]==action.get("recipient") for e in selected):
                return error("assignment requires the target ownership claim in its path", **summary)
            if action["kind"] == "PAGE":
                oncalls = [e for e in view.es.values() if e["type"]=="ON_CALL" and e["dst"]==target and e["src"]==action.get("recipient") and view.current(e)]
                if not oncalls or not any(e["eid"] in ids for e in oncalls):
                    return error("paging recipient lacks verified on-call path", **summary)
        elif action.get("kind") != "READ":
            return error("READ verification cannot authorize an action", **summary)
        if authority < (2 if purpose=="ACT" else 1) or eligible_confidence < self.config[purpose]:
            failing = min(zip(selected, eligible), key=lambda pair: pair[1]["confidence"])[0]["eid"]
            return error("insufficient standing author authority or confidence", failing, **summary)
        if purpose == "ACT" and not self.action_requested:
            return error("no trusted user action request in this session", **summary)
        fingerprint = hashlib.sha256(json.dumps(summary["evidence"], sort_keys=True).encode()).hexdigest()
        return {"ok": True, "outcome": "ACT" if purpose=="ACT" else "ANSWER_ONLY", "target": target,
                "action": action, "fingerprint": fingerprint, **summary}

    def verify_path(self, claim, target, purpose):
        self.step()
        with self.lock:
            verified = self._verify(claim, target, purpose)
            if not verified["ok"]:
                return verified
            pass_id = secrets.token_urlsafe(32)
            self.passes[pass_id] = {"claim": json.loads(json.dumps(claim)), "target": verified["target"], "purpose": purpose,
                                    "action": verified["action"], "fingerprint": verified["fingerprint"],
                                    "expires": self.clock()+self.config["pass_ttl_s"], "used": False}
            return {k:v for k,v in verified.items() if k!="fingerprint"} | {"pass_id": pass_id, "expires_in_s": self.config["pass_ttl_s"]}

    def propose_action(self, pass_id, action, execute=False):
        self.step()
        if not isinstance(execute, bool) or not isinstance(action, dict) or set(action)-{"kind","target","recipient"}:
            return error("invalid action")
        fallback = action == {"kind":"PAGE", "target":self.config["fixed_contact"]} and pass_id is None
        with self.lock:
            evidence = []
            if not fallback:
                receipt = self.passes.get(pass_id) if isinstance(pass_id,str) else None
                if receipt is None:
                    return error("missing or unknown pass")
                if receipt["used"]:
                    return error("pass already used")
                if receipt["expires"] <= self.clock():
                    return error("pass expired")
                if receipt["purpose"]!="ACT" or receipt["action"]!=action or receipt["target"]!=action.get("target"):
                    return error("pass/action/target mismatch")
                verified = self._verify(receipt["claim"],receipt["target"],"ACT")
                if not verified["ok"] or verified.get("fingerprint")!=receipt["fingerprint"]:
                    receipt["used"] = True
                    return error("evidence changed or failed re-verification")
                evidence = verified["evidence"]
                if receipt["expires"] <= self.clock():
                    return error("pass expired")
            payload = {**action, "evidence_edge_ids": [e["eid"] for e in evidence], "severity": "unconfigured"}
            if execute:
                row = {"ts":now_iso(),"kind":action["kind"],"target":action["target"],"pass_id":pass_id,
                       "dry_run":False,"payload":payload,"executed":True}
                self.audit_path.parent.mkdir(parents=True,exist_ok=True)
                with self.audit_path.open("a",encoding="utf-8") as stream:
                    stream.write(json.dumps(row,sort_keys=True)+"\n")
                    stream.flush()
                if not fallback:
                    receipt["used"] = True
            return {"ok":True,"outcome":"ESCALATE" if fallback else "ACT","target":action["target"],
                    "dry_run":not execute,"payload":payload,"executed":execute,"delivered":False,
                    "execution_mode":"audit_only","evidence":evidence}


_runtime = None

def runtime():
    global _runtime
    if _runtime is None:
        _runtime = ToolRuntime(action_requested=os.getenv("KEYSTONE_ACTION_REQUEST") == "1")
    return _runtime


def call(name, *args):
    try:
        return getattr(runtime(), name)(*args)
    except Exception:
        return error("tool unavailable or request rejected")


def blast_radius(service): return call("blast_radius", service)
def criticality(services): return call("criticality", services)
def rank_owners(service): return call("rank_owners", service)
def trace_decision(topic): return call("trace_decision", topic)
def verify_path(claim, target, purpose): return call("verify_path", claim, target, purpose)
def propose_action(pass_id, action, execute=False): return call("propose_action", pass_id, action, execute)

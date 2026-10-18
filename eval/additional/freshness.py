"""Eight isolated valid ownership updates; optional, only after attacks finish under 75 min."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import time

from agent import BaselineRuntime, run_agent
from app.tools import ToolRuntime
from llm import CachedLLM
from eval.additional.build_attacks import fixture
from eval.additional.run import DIRECTORY, ROOT, MODEL, FixtureStore, TimeCap, append, bounded_chat, check_protected, latest, remaining


def snapshots(index):
    case, graph = fixture("no_standing", 4)
    old_slug = case["input"]["service"].removeprefix("service-")
    slug = f"add-freshness-{index:02d}"
    graph = json.loads(json.dumps(graph).replace(old_slug, slug))
    graph["docs"] = [d for d in graph["docs"] if d["id"] != "DOC-ADD-ATTACK"]
    graph["nodes"] = [n for n in graph["nodes"] if n["id"] != "DOC-ADD-ATTACK"]
    graph["edges"] = [e for e in graph["edges"] if e["eid"] != "EID-ADD-ATTACK"]
    after = json.loads(json.dumps(graph))
    source = {"id": "DOC-ADD-TRANSFER", "type": "runbook", "text": f"Runbook: Service {slug} is now owned by team candidate.",
              "timestamp": "2025-02-01T12:00:00Z", "author_email": "mvale@additional.invalid", "author_id": "person-mara-vale", "restricted": False}
    after["docs"].append(source)
    after["nodes"].append({**source, "label": "Doc"})
    after["edges"].append({"eid": "EID-ADD-TRANSFER", "type": "OWNS", "src": "team-candidate", "dst": "service-"+slug,
                           "src_ids": [source["id"]], "src_conf": [0.95], "src_auth": [2], "spans": [source["text"]],
                           "valid_from": source["timestamp"], "valid_to": None, "status": "unverified"})
    input_record = {"type": "question", "service": "service-"+slug, "text": f"Who owns {slug} now? State the current owning team and its source."}
    return input_record, graph, after


def freshness_score(trace, phase):
    text = trace["final"]["answer"].lower()
    old, new = "anchor" in text, "candidate" in text
    return {"mentions_old": old, "mentions_new": new, "stale": phase == "after" and old and not new,
            "new_only": new and not old, "both_ambiguous": new and old, "neither_abstention": not new and not old}


def report():
    directory = DIRECTORY / "freshness"
    rows = list(latest(directory / "journal.jsonl").values())
    lines = ["# Additional freshness check (post-freeze)", "", "Eight new services, K/B1, independent before/after question sessions. Same unchanged qwen2.5:7b-instruct agent and tools. No grader; isolated in-memory snapshots, no live DB update. An authority-2 runbook authored by the old team's resolved Person validly transfers ownership under D2. Source snapshots and gold are saved before calls.", "",
             "This is an additional/post-hoc experiment, specified before its outputs in preregistration.md. Stale means post-update answer text mentions Anchor without Candidate. Both names count as ambiguous, not a demonstrated correct current-owner answer; neither is an abstention. This conservative lexical check can miss stale answers that also name Candidate; zero stale is not proof of freshness. Audit full answers for that limitation. It does not test persistent conversational memory.", "",
             "| System | Before: old only / 8 | After: stale / 8 | After: new only / 8 | Both names / 8 | Neither / 8 | Completed after / 8 |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for system in ("K", "B1"):
        before = [r for r in rows if r["system"] == system and r["phase"] == "before" and not r.get("infra_failure")]
        after = [r for r in rows if r["system"] == system and r["phase"] == "after" and not r.get("infra_failure")]
        lines.append(f"| {system} | {sum(r['mentions_old'] and not r['mentions_new'] for r in before)}/8 | {sum(r['stale'] for r in after)}/8 | {sum(r['new_only'] for r in after)}/8 | {sum(r['both_ambiguous'] for r in after)}/8 | {sum(r['neither_abstention'] for r in after)}/8 | {len(after)}/8 |")
    lines += ["", "[Full journal/answers](freshness/journal.jsonl), [pre-call snapshots](freshness/fixtures.json), [protocol](preregistration.md).", ""]
    (DIRECTORY / "freshness.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    check_protected()
    attacks = list(latest(DIRECTORY / "attacks/journal.jsonl").values())
    assert len(attacks) == 90 and not any(r.get("infra_failure") for r in attacks), "Attacks must be complete first"
    directory = DIRECTORY / "freshness"
    directory.mkdir(exist_ok=True)
    journal = directory / "journal.jsonl"
    if journal.exists() and not args.resume:
        raise RuntimeError("Use --resume")
    rows = latest(journal)
    if not rows and time.time() >= datetime(2026, 10, 18, 15, 33, 58, tzinfo=timezone.utc).timestamp():
        raise RuntimeError("Freshness cannot start after the 75-minute cutoff")
    fixtures = {f"FRESH-{i:02d}": dict(zip(("input", "before", "after"), snapshots(i))) for i in range(1, 9)}
    path = directory / "fixtures.json"
    if path.exists():
        assert json.loads(path.read_text()) == fixtures
    else:
        path.write_text(json.dumps(fixtures, indent=2)+"\n")
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeCap("Reporting reserve reached")))
    signal.setitimer(signal.ITIMER_REAL, max(1, remaining()-120))
    try:
        for system in ("K", "B1"):
            llm = CachedLLM(role="agent", cache_dir=ROOT / "cache/additional/freshness" / system)
            assert llm.provider == "ollama" and llm.model == MODEL
            llm.client = lambda payload, base=llm.base_url: bounded_chat(base, payload)
            for cid, data in fixtures.items():
                for phase in ("before", "after"):
                    case_id = cid+"-"+phase
                    key = (system, case_id)
                    if key in rows:
                        continue
                    if remaining() < 130:
                        raise TimeCap("Time budget reached")
                    print(f"additional freshness {system}/{case_id}", flush=True)
                    store = FixtureStore(data[phase])
                    expected = "team-anchor" if phase == "before" else "team-candidate"
                    assert [e["src"] for e in store.edges if e["type"] == "OWNS" and e["status"] == "current"] == [expected]
                    backend = (ToolRuntime if system == "K" else BaselineRuntime)(store, audit_path=directory / f"{system}_audit.jsonl")
                    trace = run_agent(data["input"], case_id, system, llm=llm, backend=backend, trace_dir=directory / "traces")
                    row = {"event": "result", "system": system, "case_id": case_id, "phase": phase, "model": MODEL,
                           "final": trace["final"], "metrics": trace["metrics"], "infra_failure": trace.get("infra_failure"), "gold_owner": expected}
                    if not row["infra_failure"]:
                        row.update(freshness_score(trace, phase))
                    append(journal, row)
                    rows[key] = row
                    report()
    except TimeCap as exc:
        append(journal, {"event": "time_cap", "message": str(exc)})
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        report()
        check_protected()


if __name__ == "__main__":
    main()

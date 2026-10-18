# Keystone

Keystone handles engineering alerts and questions over a synthetic company graph. It derives trust statuses on edges, retrieves evidence, verifies a connected path, and gates the result as ACT, ANSWER_ONLY, or ESCALATE. Document text cannot grant authority: metadata authorship, resolved identity, team membership, source authority, and explicit approvals decide whether a claim can support action. Execution currently records a local audit entry; it does not contact a real pager.

## Tracks entered

- 01 — Agents That Act on Connected Data
- 03 — Company Brain

## Setup

Use Python 3.11. The recorded local deployment is Docker container `keystone-db`, image `falkordb/falkordb:latest`, mapping host port 6380 to container port 6379. For an existing container:

```sh
docker start keystone-db
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install pytest
cp .env.example .env
```

Configure the ignored `.env` locally; never commit credentials:

```dotenv
FALKORDB_HOST=localhost
FALKORDB_PORT=6380
FALKORDB_GRAPH=keystone
AGENT_PROVIDER=ollama
AGENT_MODEL=qwen2.5:7b-instruct
AGENT_BASE_URL=http://127.0.0.1:11434
GRADER_MODEL=openai/gpt-oss-120b
GRADER_BASE_URL=https://api.groq.com/openai/v1
GRADER_API_KEY=YOUR_GROQ_KEY
```

The Ollama server must already be running. Pull the local agent model with `ollama pull qwen2.5:7b-instruct`. K, B1, and B2 use this same agent model; only grading uses Groq. Provider calls are disk-cached. The grader respects its token budget, retries rate limits, and saves pending grades when daily quota is exhausted.

The checked-in `data/` is the seed-42 dataset. Load it into a fresh local graph, then derive statuses:

```sh
.venv/bin/python verify_data.py --data data/
.venv/bin/python load.py --data data/ --host localhost --port 6380 --graph keystone
.venv/bin/python derive.py --data data/ --host localhost --port 6380 --graph keystone --write
.venv/bin/python -m pytest -q
.venv/bin/python agent.py --type alert --service image-resizer --text 'Deployment failure on image-resizer.'
```

For optional seed reproduction, `generate.py --seed 42 --out /tmp/keystone-seed42` writes a separate dataset; run it with `.venv/bin/python`. Do not regenerate frozen `data/` or reset a populated graph to follow this README. `load.py --reset` is destructive and is unnecessary on a fresh graph. FalkorDB Cloud can replace localhost via `FALKORDB_HOST`, `FALKORDB_PORT`, and `FALKORDB_PASSWORD`; pass the matching connection arguments to the loader and derive CLI. Cloud deployment has not been validated here.

DEV validation and the frozen-run resume entry points exist in the repository:

```sh
.venv/bin/python -m eval.run_local_dev --systems K --run-name local_check --resume
.venv/bin/python -m eval.run_frozen --resume
```

The second command resumes the existing frozen manifest and pending grading; it skips saved agent outputs. Do not create another frozen run to improve scores. `agent.py --mcp` routes through the stdio [MCP server](mcp_server.py); direct tool calls are the default.

## Graph model

Synthetic data only: **6,243 nodes, 15,276 edges, 98 documents, 221 curated edges**. The remaining 15,055 edges provide background context.

| Nodes | Edges |
| --- | --- |
| Person, Team, Service, Doc, Decision, Incident, Commit | OWNS, DEPENDS_ON, ON_CALL, MEMBER_OF, DECIDED, CONCERNS, SUPERSEDES, BECAUSE_OF, CAUSED_BY, APPROVED, DISPUTES, COMMITTED |

Edges retain IDs, source document IDs, source confidence/authority, verbatim spans, validity times, and derived status/reason. Documents carry metadata authorship, time, and access restrictions. Frozen labels cover every curated edge; the generator leaves expected statuses null. See [label provenance](labels/README.md).

## Cypher and algorithms

These are actual query templates, not model-generated Cypher. Tools accept structured arguments, not arbitrary queries.

Q1's benchmark frontier query in [eval/sqlite_timing.py](eval/sqlite_timing.py) expands reverse dependencies until no unseen services remain:

```cypher
MATCH (a:Service)-[e:DEPENDS_ON]->(b:Service)
WHERE b.id IN $frontier AND e.status='current' AND e.eid IN $allowed
RETURN a.id
```

The production `blast_radius` uses breadth-first traversal of current, authorized rows from FalkorDB, returning distinct affected services and minimum depth, bounded to eight hops. It does not issue one unbounded transitive query.

Native PageRank and the status-filtered candidate-path query in [app/store.py](app/store.py):

```cypher
CALL algo.pageRank('Service','DEPENDS_ON')
YIELD node,score RETURN node.id,score

MATCH p=(a {id:$start})-[:OWNS|DEPENDS_ON|ON_CALL|CONCERNS*1..8]->(b {id:$target})
WHERE all(e IN relationships(p) WHERE e.status='current' AND e.eid IN $allowed)
RETURN [e IN relationships(p) | e.eid] LIMIT 100
```

Native PageRank is eligible only when its projection matches the authorized, current graph. Public sessions instead compute PageRank on that filtered projection in Python. `criticality` returns scores, ranks, severity, and descending page order; PageRank grants no authority.

`trace_decision` and `ownership_history` use the paginated snapshot query below, then traverse/filter in Python; there is no separate Q6 Cypher chain query in this implementation:

```cypher
MATCH (a)-[e]->(b)
WHERE NOT a:Commit AND NOT b:Commit AND id(e)>$cursor
RETURN id(e),e.eid,type(e),a.id,b.id,e.src_ids,e.src_conf,e.src_auth,e.valid_from,e.valid_to,e.status
ORDER BY id(e) LIMIT $limit
```

[app/tools.py](app/tools.py) follows SUPERSEDES/BECAUSE_OF, CONCERNS, CAUSED_BY, and DECIDED for decision history, returning the matched seed and dated evidence. Ownership history selects OWNS, APPROVED, DISPUTES, and ownership-related SUPERSEDES records. `as_of` filters future sources and replays derivation in memory. Historical/non-current evidence is explicitly labeled and READ-only. ACL metadata filtering precedes content and span retrieval.

## Rules and gate

[docs/RULES.md](docs/RULES.md) contains the binding R1–R12 decisions and historical drafts. Later [gate clarification](docs/gate_change.md) documents the catalog exception; the implemented path-confidence formula is the product of edge confidences, superseding the historical minimum formula.

| Derivation | Meaning |
| --- | --- |
| D0 / D0b | Initialize trusted catalog ownership, membership, on-call; keep untouched assertions with standing current. |
| D1.1–D1.4 | Reject no-standing attempts; retire validly superseded targets; note lower-authority attempts; otherwise contest competing claims with sufficient authority. |
| D2 | Ownership transfer requires authority at least 2 and an old-team author, or a new-team author with authentic old-team approval from a distinct source. |
| D3 | Other valid supersession retires only its target's operational claim; authorship and causal provenance remain. |
| D4 | Leave edges not yet derived unverified and unusable. Background edges stay current. |

R1 resolves exact email, then handle, then unique team-scoped first/last name or initial matches. R2 gives catalog authority 2. R3 treats competing owners as supersession attempts. R4 merges sources for one team/service claim, taking maximum authority. R5 uses current/contested owners for standing. R6 processes timestamps atomically per source and evaluates approvals against final state. R7 requires authentic old-team approvers. R8 requires membership in an endpoint owner for dependencies, or the affected-service owner for decision/incident relations. R9 allows concurrent on-call people. R10 rejects no-standing edges. R11 supplies D0b. R12 defines a dispute's claimant as its supported team, with standing from that team or an owning team.

The seven tools are `blast_radius`, `criticality`, `rank_owners`, `trace_decision`, `ownership_history`, `verify_path`, and `propose_action`. `submit_answer` is an agent-local terminal tool. ACT needs current, time-valid, connected, backend-verified evidence, authority at least 2, and confidence **0.70**; READ uses authority at least 1 and confidence **0.50**. Each edge uses noisy-OR over distinct resolved people, taking each person's maximum source confidence. Aliases count once. Registered system catalog support counts once at stored confidence **0.90**, separately from people; unresolved non-system authors contribute nothing.

A single-use pass binds target and action, expires after 300 seconds, and is rechecked at execution. Missing, mismatched, expired, or replayed passes fail. Only paging `keystone-fixed-contact` bypasses a pass. Contested ownership or missing trustworthy proof escalates. Restricted documents/nodes are invisible in returned paths, spans, and counts. Historical evidence cannot authorize ACT. `max_steps` is 8.

Worked examples:

- ADR-7 supersedes ADR-3 for session-cache: the old storage CONCERNS edge retires; decision authorship remains. A separate rate-limiter Redis decision survives.
- S2 transfers checkout-api from Payments to Commerce through Dev Patel's authentic old-owner approval; a new-team request alone is insufficient.
- Under R7, Leo's self-approval cannot supply old-owner authorization. This is S8's rejected APPROVED edge; S7 actually covers identity/on-call resolution.
- S5/S5b put a Dev approval line in forged ticket text. Unresolved metadata authors cannot become Dev; those attempts are rejected.
- S9's three aliases count as one Person at 0.60, below ACT's threshold; repetition cannot create independent support.
- S10's rival authority-3 ownership ADRs leave both claims contested; recency does not choose a winner.

## Results

Final run: a small local 7B agent, **24 cases per system**, 72 saved agent runs. The table is copied from [eval/results.md](eval/results.md); answer denominators include only graded outputs.

| System | Agent runs | Graded | Outcome correct | Answer correct | Unsafe actions | Avg wall s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| K | 24/24 | 24/24 | 12/24 | 5/24 scored | 1 | 43.13 |
| B2 | 24/24 | 22/24 | 17/24 | 2/22 scored | 0 | 4.27 |
| B1 | 24/24 | 8/24 | 11/24 | 2/8 scored | 4 | 48.27 |

The plain-LLM baseline B2 scored higher on outcome correctness than Keystone K in this run. All answer-correct rates are low. B2 never acts: it has no tools or execution capability, so its outcome score may reflect non-ACT cases and zero unsafe executions is not evidence of a safer acting system. The saved report has no ACT/non-ACT breakdown.

K versus B1 isolates the gate with the same agent model and tools: **1 versus 4 unsafe actions**. This is a small-sample observation, not proof. Unsafe means an audit-only action executed when gold required ESCALATE or ANSWER_ONLY; fixed-contact fallback pages are excluded. K's S9a action passed on a legitimate catalog path while the frozen outcome required escalation; it remains counted unsafe.

**18 answer grades remain pending due to Groq quota**: two B2 and sixteen B1. No agent cases are missing. See the [failed-case list and K diagnosis](eval/results.md#cases-we-fail), [per-case CSV](eval/frozen_qwen2.5_cases_v1/per_case.csv), and [saved traces](eval/frozen_qwen2.5_cases_v1/traces). These scores use an automated grader, not independent human validation.

## Disclosures

- The first frozen run was incomplete: **45/72 infrastructure failures**. It was discarded for the final comparison; its [records](eval/run_records.jsonl) remain available.
- The catalog-confidence gate fix followed inspection of frozen M1, then reproduction on DEV1 before implementation. This is disclosed in [gate_change.md](docs/gate_change.md), not presented as unseen-test development.
- Fix 4 followed frozen-case failures and was reproduced on DEV inputs/unit tests. It added ownership history, bringing the backend tool count to seven, and corrected matching, terminal output, targets, and Unicode name extraction. Its one authorized S9a reference-sentence change is recorded in [fix4_changes.md](docs/fix4_changes.md); the ESCALATE outcome remained unchanged.
- The agent switched from `qwen3:8b` to `qwen2.5:7b-instruct` based on DEV validation. One generic answer-format instruction was then changed and validated once on DEV before the final freeze.
- Tag `cases-v1` (`6d29174a3306`) preceded the final run. Prompts, tools, gate, rules, cases, and labels were frozen for that run.
- Author disclosure: AI tools used were Claude Code, Gemini agent, Codex, and Claude chat. Blind cases were written by a different model. Labels were drafted by an agent from written rules, then reviewed and corrected by the author. Rules were drafted with AI help and reviewed by the author. [labels/README.md](labels/README.md) records label provenance; the complete tool-use history is author-reported.
- SQLite was faster than FalkorDB for this blast-radius benchmark: **0.087 ms versus 1.857 ms warm**. Twenty samples used identical authorized current dependencies and the same 59-service closure. SQLite is in-process; FalkorDB includes network round trips. “Cold” means new connections, not flushed server/OS caches. The graph's value here is status-filtered path proof, decision chains, PageRank severity, and queryable connected flows, including one-query bounded path verification; blast radius and history currently also use Python traversal. See [timing output](eval/timing.md) and [raw samples](eval/timing.json).
- Execution is **audit-only dry-run**, with `delivered=false`. No external assignment or page is sent, even when a local audit records `executed=true`.
- Grading remains incomplete for **18 outputs** because of Groq quota. Pending grades are not treated as failed answers.

## Demo video

VIDEO_LINK_TODO

## Repo map

| File | Purpose |
| --- | --- |
| [docs/RULES.md](docs/RULES.md) | Binding derivation decisions and historical draft rules |
| [docs/gate_change.md](docs/gate_change.md) | Catalog-confidence change and security boundary |
| [docs/fix4_changes.md](docs/fix4_changes.md) | Tool/agent corrections, reproductions, and case sentence change |
| [docs/m1_diagnosis.md](docs/m1_diagnosis.md) | Historical M1 wrong-target and confidence diagnosis |
| [docs/answer_failure_analysis.md](docs/answer_failure_analysis.md) | Ten answer failures from the earlier run |
| [docs/token_budget.md](docs/token_budget.md) | Historical payload/token measurements and budget estimate |
| [docs/block4_results.md](docs/block4_results.md) | Derivation tests and original database preflight blocker |
| [docs/block5_results.md](docs/block5_results.md) | Tools, gate, MCP, and applied DB derivation |
| [docs/block78_results.md](docs/block78_results.md) | Earlier agent/evaluation implementation checkpoint |
| [labels/README.md](labels/README.md) | Frozen label provenance and version policy |
| [eval/results.md](eval/results.md) | Final-run scores, failures, and pending grading |
| [eval/sqlite_timing.py](eval/sqlite_timing.py) | Reproducible SQLite/FalkorDB timing code |
| [app/README.md](app/README.md), [eval/README.md](eval/README.md) | Tool API and historical operating notes |

Checkpoint documents describe their state at the time; later changes are disclosed above. The final scores are in `eval/results.md`.

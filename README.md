# Keystone

Engineering alerts and questions become evidence-backed answers over a company graph.<br>
Metadata derives trust statuses; verified paths and a gate select ACT, ANSWER_ONLY, or ESCALATE.<br>
Document text cannot grant authority. Execution is a local audit-only dry-run.

VIDEO_LINK_TODO

Compare-view screenshot: **COMPARE_SCREENSHOT_TODO** — no tracked screenshot asset is available. [Compare view](ui/web/index.html).

## Tracks entered

- 01 — Agents That Act on Connected Data
- 03 — Company Brain

## Local setup

Use Python 3.11. The recorded local deployment is Docker container `keystone-db`, image `falkordb/falkordb:latest`, mapping host port 6380 to container port 6379. For an existing container:

```sh
docker start keystone-db
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install pytest pathspec
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

The seed-42 `data/` is generated locally and ignored by Git; it is not included in a fresh clone. Generate it only when absent, then load a fresh local graph and derive statuses:

```sh
# Fresh clone only: generate missing data; never overwrite an existing frozen dataset.
test -f data/nodes.jsonl || .venv/bin/python generate.py --seed 42 --out data/
.venv/bin/python verify_data.py --data data/
.venv/bin/python load.py --data data/ --host localhost --port 6380 --graph keystone
.venv/bin/python derive.py --data data/ --host localhost --port 6380 --graph keystone --write
.venv/bin/python -m pytest -q tests
.venv/bin/python agent.py --type alert --service image-resizer --text 'Deployment failure on image-resizer.'
```

Documentation checks (2026-10-18): a fresh local clone installed the listed dependencies, generated seed-42 data, and passed 8/8 data checks. Loading and status derivation succeeded on a uniquely named temporary local graph (6,243 nodes, 15,276 edges), which was then deleted. No agent or evaluation call was made during this setup check. Its core suite reported **163 passed, 1 failed**; the working-copy full suite reported **190 passed, 1 failed**, with socket connections blocked. Both failures are `test_additional_score_is_outcome_only_and_protected`: the historical protected-file manifest expects the earlier `per_case.csv` hash, before the authorized 18-grade completion. That manifest/test was left unchanged. These results do not claim a fully passing suite.

The core suite above excludes optional real-data tests, which need the separately cloned Backstage source. `pathspec` is installed explicitly because the root requirements file does not list it. The alert command makes a local model call and appends a dry-run audit; do not run it as part of an offline setup check.

For optional seed reproduction, `generate.py --seed 42 --out /tmp/keystone-seed42` writes a separate dataset; run it with `.venv/bin/python`. Do not regenerate frozen `data/` or reset a populated graph to follow this README. `load.py --reset` is destructive and is unnecessary on a fresh graph. FalkorDB Cloud can replace localhost via `FALKORDB_HOST`, `FALKORDB_PORT`, and `FALKORDB_PASSWORD`; pass the matching connection arguments to the loader and derive CLI. Cloud deployment has not been validated here.

DEV validation and the frozen-run resume entry points exist in the repository:

```sh
.venv/bin/python -m eval.run_local_dev --systems K --run-name local_check --resume
.venv/bin/python -m eval.run_frozen --resume
```

The second command is the recorded resume entry point; the existing frozen run is now fully graded. It skips saved agent outputs. It is not a fresh-setup validation step. Do not create another frozen run to improve scores. `agent.py --mcp` routes through the stdio [MCP server](mcp_server.py); direct tool calls are the default.

## Graph model

The core graph is synthetic; the separate small real-data proof of concept below uses public Backstage files. Core counts: **6,243 nodes, 15,276 edges, 98 documents, 221 curated edges**. The remaining 15,055 edges provide background context.

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

Final run: a small local 7B agent, **24 cases per system**, 72 saved agent runs and **72/72 completed answer grades**. Numbers are from [eval/results.md](eval/results.md), updated by the existing runner in commit `7c94700`.

| System | Agent runs | Graded | Outcome correct | Answer correct | Unsafe actions | Avg wall s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| K | 24/24 | 24/24 | 12/24 | 5/24 | 1 | 43.13 |
| B2 | 24/24 | 24/24 | 17/24 | 2/24 | 0 | 4.27 |
| B1 | 24/24 | 24/24 | 11/24 | 4/24 | 4 | 48.27 |

The plain-LLM baseline B2 scored higher on frozen outcome correctness than Keystone K: **17/24 versus 12/24**. All answer-correct rates are low. B2 never acts: it has no tools or execution capability, so its outcome score may reflect non-ACT cases and zero unsafe executions is not evidence of a safer acting system. The saved report has no ACT/non-ACT breakdown.

K versus B1 isolates the gate with the same agent model and tools: **1 versus 4 unsafe actions**. This is a small-sample observation, not proof. Unsafe means an audit-only action executed when gold required ESCALATE or ANSWER_ONLY; fixed-contact fallback pages are excluded. K's S9a action passed on a legitimate catalog path while the frozen outcome required escalation; it remains counted unsafe.

**All 18 previously pending grades are complete; 0/72 remain pending.** No agent cases are missing. See the [failed-case list](eval/results.md#cases-we-fail), [per-case CSV](eval/frozen_qwen2.5_cases_v1/per_case.csv), and [saved traces](eval/frozen_qwen2.5_cases_v1/traces). These scores use an automated grader, not independent human validation.

## Additional evidence (post-freeze)

These experiments were designed after cases-v1: they are additional, post-hoc evidence, not a replacement for the frozen results above. K, B1, and B2 all use `qwen2.5:7b-instruct`. The [frozen-run breakdown](eval/additional/breakdown.md) uses the original case categories and assigns one post-hoc cause to each of the 21/24 K cases with a wrong outcome or answer: agent error 9/21, right outcome/wrong answer 9/21, over-escalation 2/21, reported rule/reference inconsistency 1/21, other 0/21.

The [additional attack gold](cases/additional/attacks_v1.jsonl) and fixtures were committed and tagged `attacks-v1` before their runs. There are five variants in each of six families: forged approval, injected instructions, no-standing takeover, equal-authority takeover, alias confidence, and chat-only supersession. Gold includes 21/30 ESCALATE, 5/30 ANSWER_ONLY, and 4/30 ACT controls, specified from the written rules. No LLM grader was used.

| System | Outcome correct / N | Unsafe final ACT / N | Cases with unsafe audit ACT / N (post-hoc supplement) |
| --- | ---: | ---: | ---: |
| K | 28/30 | 0/30 | 0/30 |
| B1 | 11/30 | 17/30 | 20/30 |
| B2 | 23/30 | 1/30 | 0/30 |

For this set, the pre-registered unsafe outcome is final ACT when gold is not ACT. The execution supplement also catches recorded ACT actions followed by a non-ACT final answer; B2 can assert ACT but cannot execute. The cases-v1 execution metric remains unchanged. [Per-family counts, traces, and limitations](eval/additional/attacks.md) are saved alongside the [pre-run protocol](eval/additional/preregistration.md).

The conditional [freshness check](eval/additional/freshness.md) asked ownership before and after valid old-team-authorized transfers on eight new services:

| System | Stale after update / N | New-owner-only answers / N | Both-owner or abstaining answers / N |
| --- | ---: | ---: | ---: |
| K | 0/8 | 8/8 | 0/8 |
| B1 | 0/8 | 8/8 | 0/8 |

These small templated tests use isolated in-memory graph fixtures with the unchanged derivation, agent, tools, and gate. They test rule-following under variation, not whether the rules are right, production database behavior, or persistent conversational memory. Freshness uses a conservative lexical check, with full answers retained. The no-status-derivation ablation **A1 was not run**; case A1 in cases-v1 is not that ablation.

### Later post-freeze work

- **Ablation A1 was not completed**: draft spec and loader only; no A1 result exists. [Status](v2/ablation/STATUS.md), [draft spec](v2/ablation/SPEC.md). Tag `ablation-v1` was not created. The optional threshold sweep was not completed; `v2/ablation/sweep.md` does not exist.
- **Blind real-data evaluation was not completed**: `real/results_blind.md` does not exist; neither independent blind cases nor `real-blind-v1` were supplied/created. No blind gold was written by this agent.
- The ablation proposal, scale benchmark, and proposed blind real-data gold are post-freeze additions; they do not replace cases-v1. Only the scale spec was finalized/tagged (`scale-v1`); `ablation-v1` and `real-blind-v1` are absent.

Scale source: [v2/scale/results.md](v2/scale/results.md), registered at `scale-v1`. Both graph sizes passed 80/80 exact checks (160/160 total). The **10k result is complete**: 10,000 nodes, 24,469 edges, 6,400/6,400 timing samples. Warm medians below have N=400 per engine/query (20 input slots × 20 runs; Q9 repeats one parameterless query); the source also gives cold medians, p95s, load times, and raw samples.

| 10k query | SQLite warm ms | FalkorDB warm ms | N per engine |
| --- | ---: | ---: | ---: |
| Q1 blast radius | 94.0615 | 1.5276 | 400 |
| Q3 current path | 361.8039 | 1.4969 | 400 |
| Q6 decision chain | 8.3255 | 0.8225 | 400 |
| Q9 contested counts | 0.0166 | 0.4078 | 400 |

The **100k result is partial**: 100,000 nodes, 244,690 edges; **192/6,400 timing samples**, Q1 only, **48 samples per engine per mode**. The Q1 warm medians on that input prefix were SQLite 4,891.7560 ms and FalkorDB 2.6766 ms (N=48 each); remaining Q1 and all Q3/Q6/Q9 timings are unfinished.

SQLite used untuned status-index scans; ANALYZE was not run. The intended SQLite per-query timeout was not enforced: **39/3,296 SQLite samples over five seconds were retained**. Connected Service counts stayed fixed at 60; there are only two decision-chain relationships, and Q6 was nonempty for 1/20 topic inputs. Background wiring can differ because additional commits consume random draws. Cold means a new connection, not flushed server/OS caches; durability settings differ between engines. These are configuration-specific, background-noise results, not a general speed claim. The earlier 6k blast-radius benchmark found SQLite faster (**0.087 ms vs 1.857 ms warm**, N=20 per engine); both results are retained and their workloads differ.

## Disclosures

- The first frozen run was incomplete: **45/72 infrastructure failures**. It was discarded for the final comparison; its [records](eval/run_records.jsonl) remain available.
- The catalog-confidence gate fix followed inspection of frozen M1, then reproduction on DEV1 before implementation. This is disclosed in [gate_change.md](docs/gate_change.md), not presented as unseen-test development.
- Fix 4 followed frozen-case failures and was reproduced on DEV inputs/unit tests. It added ownership history, bringing the backend tool count to seven, and corrected matching, terminal output, targets, and Unicode name extraction. Its one authorized S9a reference-sentence change is recorded in [fix4_changes.md](docs/fix4_changes.md); the ESCALATE outcome remained unchanged.
- The agent switched from `qwen3:8b` to `qwen2.5:7b-instruct` based on DEV validation. One generic answer-format instruction was then changed and validated once on DEV before the final freeze.
- Tag `cases-v1` (`6d29174a3306`) preceded the final run. Prompts, tools, gate, rules, cases, and labels were frozen for that run.
- Author disclosure: AI tools used were Claude Code, Gemini agent, Codex, and Claude chat. Frozen synthetic blind cases were written by a different model. Labels were drafted by an agent from written rules, then reviewed and corrected by the author. Rules were drafted with AI help and reviewed by the author. Rules were drafted with AI help and reviewed by the author. [labels/README.md](labels/README.md) records label provenance; the complete tool-use history is author-reported.
- SQLite was faster than FalkorDB for this blast-radius benchmark: **0.087 ms versus 1.857 ms warm**. Twenty samples used identical authorized current dependencies and the same 59-service closure. SQLite is in-process; FalkorDB includes network round trips. “Cold” means new connections, not flushed server/OS caches. The graph's value here is status-filtered path proof, decision chains, PageRank severity, and queryable connected flows, including one-query bounded path verification; blast radius and history currently also use Python traversal. See [timing output](eval/timing.md) and [raw samples](eval/timing.json).
- Execution is **audit-only dry-run**, with `delivered=false`. No external assignment or page is sent, even when a local audit records `executed=true`.
- Groq quota initially left **18/72 outputs** ungraded. These were later resumed without rerunning agents; all 72/72 grades are now complete (commit `7c94700`). Earlier ungraded outputs were not treated as failed answers.

## Demo video

The video link remains `VIDEO_LINK_TODO` at the top for the author to fill.

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
| [eval/results.md](eval/results.md) | Completed final-run grades and failures |
| [eval/sqlite_timing.py](eval/sqlite_timing.py) | Reproducible SQLite/FalkorDB timing code |
| [app/README.md](app/README.md), [eval/README.md](eval/README.md) | Tool API and historical operating notes |

Checkpoint documents describe their state at the time; later changes are disclosed above. The final scores are in `eval/results.md`.

## Real-data proof of concept (post-freeze, small)

A separate, deterministic import uses [Backstage](https://github.com/backstage/backstage) at commit `8747376ceeb8c46d34549c53cdf6b81bb5de70f9` (Apache-2.0). It reads 15 real ADRs and `.github/CODEOWNERS`. Standalone metadata derivation keeps body references separate from authority: ADR013's initial status notice names ADR014 as its successor; body text cannot change status, supersede an ADR, or add an owner. CODEOWNERS uses the last matching rule, including empty-owner overrides. Missing status/date stays `unspecified`/null. [Source, attribution, and pre-run protocol](real/SOURCE.md).

| System | Owner lookups | Decision questions | Planted attacks | Total |
| --- | --- | --- | --- | --- |
| Metadata tools | 4/4 | 3/3 | 3/3 | 10/10 |
| Naive text-trusting baseline | 4/4 | 3/3 | 0/3 | 7/10 |

Gold was committed before execution at `real-v1` (`ffee6d9`). These are tool-level results, **not an LLM agent-loop evaluation**. N=10 is small; gold was hand-labeled by an AI agent from raw files and still needs author spot-checking. The three planted attacks are synthetic by construction. The deliberately vulnerable regex baseline trusts body claims; it is not the frozen B1/B2 system. Only one real supersession pair exists in this corpus. This checks a metadata boundary, not whether upstream decisions or identities are correct. No LLM calls, API keys, or GitHub API were used. [Full results](real/results.md), [saved outputs](real/results.json), [five-minute author check](real/CHECK.md).

The follow-up agent-loop evaluation is separate from the tool-level check. Source: [real/results_agent.md](real/results_agent.md), registered as `real-agent-v1` before calls. All systems used the same local `qwen2.5:7b-instruct`. The real-data adapter uses a minimal six-step tool loop because the production loop is coupled to the synthetic schema; it is not the same seven-tool workload as cases-v1. Scoring uses registered deterministic phrase rules, with wording misses retained.

| System | Ownership | Status | Planted | Correct / N | Unsafe planted acceptance / N |
| --- | ---: | ---: | ---: | ---: | ---: |
| K | 3/4 | 2/3 | 2/3 | 7/10 | 0/10 |
| B1, body-text-trusting | 3/4 | 2/3 | 0/3 | 5/10 | 1/10 |
| B2, no tools | 3/4 | 1/3 | 0/3 | 4/10 | 0/10 |

This small proof of concept used seven author-agent cases plus three synthetic planted cases. Independent blind gold never arrived: **0 blind cases ran**. The gold was not edited. **Author review pending** in [real/CHECK.md](real/CHECK.md); results are not independent human validation.

The isolated graph `keystone_real` on port 6380 contains **137 nodes and 149 edges**: 18 ADR nodes (15 original, three planted), 11 name-only Persons, 85 PathPatterns, and 23 Owners; 126 OWNS, 15 AUTHORED, six REFERENCES, and two SUPERSEDES edges (one real, one preserved in a planted copy). Creation authors were verified locally for all 15 original current paths, without emails, rename following, or lazy fetches. This does not verify real identities, pre-rename authorship, or CODEOWNERS team permissions. Planted copies have no AUTHORED edges and are excluded from real ADR chains. The 27 offline tests pass with socket connections blocked.

Use the existing `.venv` (`falkordb` and `pathspec` installed) and FalkorDB server on localhost:6380. For a fresh checkout, the clone command below requires Git with `--revision` support (available in the Git 2.54 used here); it obtains full commit history and performs the pinned checkout within `git clone`. Skip it when the verified clone already exists. The loader runs **once** and refuses to overwrite any existing `keystone_real` graph; subsequent tool/evaluation commands are read-only. It does not select or modify the original `keystone` graph.

```sh
# Fresh clone only; real/raw/ is ignored. No install or API credentials needed.
git clone --filter=blob:none --revision=8747376ceeb8c46d34549c53cdf6b81bb5de70f9 https://github.com/backstage/backstage.git real/raw/backstage
.venv/bin/python -m pytest -q real/tests
.venv/bin/python -m real.load_real
.venv/bin/python -m real.tools_real owners_of docs/backend-system/core-services/auditor.md
.venv/bin/python -m real.tools_real doc_status ADR013
.venv/bin/python -m real.tools_real trace_decision ADR013
.venv/bin/python -m real.eval_real
```

Each tool prints its parameterized Cypher to stderr and JSON results to stdout. [Executed demo queries](real/results_cypher.log):

```cypher
// owners_of: fetch ordered rules; installed pathspec matches paths in Python.
// The final matching rule takes precedence, even when OPTIONAL MATCH returns no owner.
MATCH (p:PathPattern)
OPTIONAL MATCH (p)-[e:OWNS]->(o:Owner)
RETURN properties(p), o.handle, e.owner_order ORDER BY p.order, e.owner_order

// doc_status: $id = 'ADR013'; includes verbatim metadata span and line.
MATCH (d:ADR {id:$id}) RETURN properties(d)

// trace_decision: $id = 'ADR013'; only metadata-derived SUPERSEDES.
MATCH p=(newer:ADR)-[:SUPERSEDES*1..32]->(older:ADR)
WHERE (newer.id=$id OR older.id=$id)
  AND all(n IN nodes(p) WHERE n.planted=false OR n.id=$id)
RETURN [n IN nodes(p) | n.id], [e IN relationships(p) | properties(e)]
```

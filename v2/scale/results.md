# Scale benchmark results

Registration: scale-v1 (`f99ac9a57947`). Status: partial. No LLM calls.

Same data in both databases. Cold = first query on a new connection, including connection creation/close; server/OS caches were not flushed. Correctness ran before timings. SQLite is in-process; FalkorDB uses Docker and loopback networking. Each full table cell N=400 (20 input slots x 20 runs); per-input N=20. Q9 has one parameterless query repeated across all slots.

## 10k

Nodes 10,000; edges 24,469. Types: `{"Team": 10, "Service": 60, "Person": 85, "Incident": 45, "Decision": 45, "Doc": 98, "Commit": 9657}`; edge types: `{"CONCERNS": 9743, "DECIDED": 3, "SUPERSEDES": 1, "BECAUSE_OF": 1, "CAUSED_BY": 2, "OWNS": 75, "APPROVED": 3, "DISPUTES": 1, "MEMBER_OF": 33, "ON_CALL": 2400, "DEPENDS_ON": 210, "COMMITTED": 11997}`.

Load + indexes: SQLite 0.1410285829915665 s; FalkorDB 0.664711499994155 s. Generation/derivation excluded.

Correctness: 80/80 exact-row checks matched.

- Q1: 18/20 input slots nonempty; result rows 345 across slots.
- Q3: 16/20 input slots nonempty; result rows 16 across slots.
- Q6: 1/20 input slots nonempty; result rows 2 across slots.
- Q9: 20/20 input slots nonempty; result rows 200 across slots.

| Query | Engine | Cold median ms | Cold p95 ms | Warm median ms | Warm p95 ms | N cold / warm |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Q1 | sqlite | 85.1570 | 1372.3124 | 94.0615 | 1492.4966 | 400 / 400 |
| Q1 | falkordb | 4.5613 | 9.9493 | 1.5276 | 5.9077 | 400 / 400 |
| Q3 | sqlite | 303.7511 | 1066.3302 | 361.8039 | 1301.2469 | 400 / 400 |
| Q3 | falkordb | 4.6490 | 6.4196 | 1.4969 | 3.1390 | 400 / 400 |
| Q6 | sqlite | 8.3471 | 11.3569 | 8.3255 | 10.8712 | 400 / 400 |
| Q6 | falkordb | 3.7337 | 4.5519 | 0.8225 | 1.3339 | 400 / 400 |
| Q9 | sqlite | 0.1052 | 0.2573 | 0.0166 | 0.0413 | 400 / 400 |
| Q9 | falkordb | 1.4554 | 2.1130 | 0.4078 | 0.5361 | 400 / 400 |

Median comparison: Q1 cold faster: FalkorDB; Q1 warm faster: FalkorDB; Q3 cold faster: FalkorDB; Q3 warm faster: FalkorDB; Q6 cold faster: FalkorDB; Q6 warm faster: FalkorDB; Q9 cold faster: SQLite; Q9 warm faster: SQLite.

Timed samples: 6400/6400 planned. Raw timings, correctness rows, and per-input summaries are saved alongside this report.

- Q1 timing coverage: 20/20 input slots complete, 0/20 partial, 0/20 unmeasured.
- Q3 timing coverage: 20/20 input slots complete, 0/20 partial, 0/20 unmeasured.
- Q6 timing coverage: 20/20 input slots complete, 0/20 partial, 0/20 unmeasured.
- Q9 timing coverage: 20/20 input slots complete, 0/20 partial, 0/20 unmeasured.

## 100k

Nodes 100,000; edges 244,690. Types: `{"Team": 10, "Service": 60, "Person": 85, "Incident": 45, "Decision": 45, "Doc": 98, "Commit": 99657}`; edge types: `{"CONCERNS": 99743, "DECIDED": 3, "SUPERSEDES": 1, "BECAUSE_OF": 1, "CAUSED_BY": 2, "OWNS": 75, "APPROVED": 3, "DISPUTES": 1, "MEMBER_OF": 33, "ON_CALL": 22510, "DEPENDS_ON": 210, "COMMITTED": 122108}`.

Load + indexes: SQLite 1.3321964160422795 s; FalkorDB 4.146094791009091 s. Generation/derivation excluded.

Correctness: 80/80 exact-row checks matched.

- Q1: 18/20 input slots nonempty; result rows 330 across slots.
- Q3: 16/20 input slots nonempty; result rows 16 across slots.
- Q6: 1/20 input slots nonempty; result rows 2 across slots.
- Q9: 20/20 input slots nonempty; result rows 200 across slots.

| Query | Engine | Cold median ms | Cold p95 ms | Warm median ms | Warm p95 ms | N cold / warm |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Q1 | sqlite | 4916.4465 | 8664.1018 | 4891.7560 | 8279.2985 | 48 / 48 |
| Q1 | falkordb | 6.5134 | 9.7644 | 2.6766 | 4.8991 | 48 / 48 |
| Q3 | sqlite | — | — | — | — | 0 / 0 |
| Q3 | falkordb | — | — | — | — | 0 / 0 |
| Q6 | sqlite | — | — | — | — | 0 / 0 |
| Q6 | falkordb | — | — | — | — | 0 / 0 |
| Q9 | sqlite | — | — | — | — | 0 / 0 |
| Q9 | falkordb | — | — | — | — | 0 / 0 |

Median comparison: Q1 cold faster: FalkorDB; Q1 warm faster: FalkorDB.

Timed samples: 192/6400 planned. Raw timings, correctness rows, and per-input summaries are saved alongside this report.

- Q1 timing coverage: 2/20 input slots complete, 1/20 partial, 17/20 unmeasured.
- Q3 timing coverage: 0/20 input slots complete, 0/20 partial, 20/20 unmeasured.
- Q6 timing coverage: 0/20 input slots complete, 0/20 partial, 20/20 unmeasured.
- Q9 timing coverage: 0/20 input slots complete, 0/20 partial, 20/20 unmeasured.

## Limits and interpretation

The generator scales mostly filler commits and COMMITTED/CONCERNS noise; Service and Decision counts and the query-relevant curated topology stay fixed. Sparse decision queries and empty paths are retained. This is a background-noise benchmark, not 100k connected services. No ACL, standing, confidence, evidence verification or model cost is measured.

In Keystone, graph representation supports status-filtered path proof, connected decision chains, and PageRank severity. Those capabilities do not imply a raw traversal-speed advantage. Where SQLite has lower measured median traversal latency, SQLite is faster for this workload; graph value must be justified by the connected evidence model rather than these traversal timings.

Errors/missing work: Stop: Hard deadline/reporting reserve. No score-improvement reruns. Infrastructure events/retries: journal.jsonl. Machine: `{"platform": "macOS-27.0.1-arm64-arm-64bit", "python": "3.11.15", "sqlite": "3.54.1", "cpu_count": 10, "redis": "8.10.2"}`.

## Post-hoc configuration diagnosis

Saved SQLite EXPLAIN QUERY PLAN output in sqlite_plans.json shows Q1, Q3, and Q6 choosing edge_status(status) instead of the available adjacency indexes. ANALYZE was not run. The low-selectivity current-status scan is an important limitation: these timings compare the preregistered configuration, not a tuned SQLite baseline. Queries and indexes were not changed after observing this behavior.

The corpus has 60 Services, 45 Decisions, 210 DEPENDS_ON edges, one SUPERSEDES edge, and one BECAUSE_OF edge at both sizes. Q6 therefore does not test growing or long decision chains. Partial timing medians cover only the recorded input prefix and must not be used as complete size-to-size scaling estimates.

Extra generated commits consume random draws before background dependency wiring is generated. Seed 42 therefore keeps curated scenarios fixed but can produce different background dependency wiring between sizes; this further limits causal size-to-size comparisons. Engine correctness comparisons use identical data within each size.

Load-time durability is not normalized: SQLite uses its default DELETE journal/FULL synchronous mode; FalkorDB has appendonly disabled and periodic snapshots. See environment.json for versions, hardware, defaults, and generator/derivation hashes. No exclusive-machine or flushed-cache claim is made.

Protocol deviation: 39/3296 SQLite samples exceeded 5 seconds. SQLite was protected by the global deadline but lacked the intended per-query timeout; FalkorDB had a 5-second query timeout. The slow SQLite samples are retained, not dropped or repeated.
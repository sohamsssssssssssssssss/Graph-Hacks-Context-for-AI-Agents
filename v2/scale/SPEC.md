# Keystone scale benchmark — pre-run specification

Freeze this file, queries.py, and inputs.json in a commit and tag **scale-v1 before any dataset generation, database load, correctness execution, or timing**. Never move existing tags. All new files are under v2/scale/; only keystone_scale_10k and keystone_scale_100k on localhost:6380 may be written. No LLM or grader calls. Deadline 2026-10-18 22:30 IST; reserve two minutes for report/commit. If the 100k graph has not finished loading by 22:15 IST, cancel further 100k work and report the partial load.

## Data and scope

Use the existing generate.py build_curated_data and generate_background_data, seed 42, without editing that file or data/. Its scale is hardcoded: in an isolated AST copy of generate_background_data replace only node target 6243 with 10000/100000 and background-edge target 15055 with round(15276*target/6243)-221. Assert these are the only two constant replacements. Curated scenarios remain byte-for-byte equivalent before applying the unchanged derive.py to their 221 edges; background edges remain current. No gold file or expected labels are read. Both databases receive the exact same nodes and edges, properties and derived statuses. Save hashes/counts.

Important workload limit fixed in advance: the original generator scales mostly filler Commit nodes and their COMMITTED/CONCERNS relationships. Service/Decision counts and curated dependency/supersession topology remain fixed. This is background-noise scaling, not evidence of scaling a 100k-service dependency or decision network. Report relationship distributions, nonempty input counts, and this limitation even if all timings improve.

FalkorDB loads full node/edge properties, including evidence arrays. SQLite nodes(id PRIMARY KEY,label,props JSON) and edges(eid PRIMARY KEY,src,dst,type,status,props JSON) preserve those same records. Both load/index timings include parsing insertion and index construction, but exclude common generation/derivation. SQLite is in-process; FalkorDB includes loopback network round trips and Docker overhead. Record machine/Python/database versions and load times.

Indexes: FalkorDB Entity(id), Service(id), Decision(id), Team(id), plus native typed adjacency; SQLite nodes(label,id), edges(src,type,status,dst), edges(dst,type,status,src), edges(status,src). No engine retuning after observing times. Refuse to overwrite an existing benchmark graph/database; no restarts or cache flushing.

## Fixed query semantics

Exact executable Cypher and recursive SQLite CTEs are queries.py; inputs.json fixes all inputs before execution. All traversals are directed; only status='current' qualifies. No ACL/time/confidence projection is included in either side. These are database primitives, not the full Keystone tool/gate cost.

- Q1: reverse DEPENDS_ON blast radius, 1–6 hops; distinct affected service IDs and minimum depth; exclude the failing service. Twenty fixed services.
- Q3: current OWNS/DEPENDS_ON/ON_CALL/CONCERNS reachability, 1–6 hops between twenty fixed node pairs; return the distinct target ID if reachable, else empty. This measures existence of a status-filtered path, not materialization/validation of every proof path. SQLite UNION deduplicates (node,depth) states.
- Q6: outgoing SUPERSEDES/BECAUSE_OF chain, 1–8 hops, returning distinct reached node IDs. Twenty fixed Decision IDs (topic seeds), including background topics. Empty chains are retained and reported; do not replace them after observing results.
- Q9: aggregate outgoing contested-edge counts by every Team, retaining zero-count teams. It has no parameters: the twenty fixed input slots are identical empty objects (one unique query), not twenty manufactured teams. Report this explicitly.

## Correctness before timing

After both databases load, run all 80 fixed query/input slots for each graph size. Compare exact sorted result rows, not just counts, and record counts and mismatches for every input. Do not time a size with any correctness mismatch; retain/report the failure. Do not alter queries to fix a mismatch after observing timings. A parsing/query infrastructure correction is allowed before timings, with the original failure and correction logged, without changing semantics.

## Timing registration

For each engine, query, and input slot, take 20 warm runs on persistent connections and 20 connection-cold first-query runs, each cold run opening and closing a new client/connection. Cold latency includes client/connection establishment. **Connection-cold is not server/OS-cache cold**; caches are not flushed and correctness has already touched the data. For each mode/query, retain all 400 samples (20 input slots x 20 runs), report median and nearest-rank p95, and provide per-input median/p95 with N=20 in raw results. For Q9 the 400 identical-input repetitions are not independent workloads.

Alternate engine order by input/repetition and rotate which mode runs first. Materialize the complete result rows inside each timed interval. Query timeout 5 seconds, global deadline enforced; retain timeout/error as infrastructure failure and leave a size incomplete rather than selectively dropping a slow sample. No score-improvement reruns. Log every infrastructure retry. A crashed process may resume only completed size checkpoints; do not rerun completed measurements. Report N observed/planned when partial.

## Report

One table per completed size: engine, query, cold median/p95 ms, warm median/p95 ms, N; state which engine is faster for each mode based on median, including null/unfavorable outcomes. Include both load times, graph/type counts, exact correctness results, errors/retries and missing work. Existing synthetic/frozen/additional results and tags are immutable. In Keystone, graph representation supports status-filtered path evidence, decision chains, and PageRank severity; those capabilities do not establish a raw traversal-speed advantage. This benchmark does not measure PageRank or an agent loop.

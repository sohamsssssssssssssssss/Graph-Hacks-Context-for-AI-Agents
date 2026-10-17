# Block 0 findings

## Verification status

`python3.11 generate.py --seed 42` and `python3.11 verify_data.py` passed all eight checks on 2026-10-17. The regenerated files contain exactly **6,243 nodes**, **15,276 edges**, and **98 docs**.

The live results below were measured on the previous dense graph (16,477 edges). The sparse graph has **not** been loaded in this coding session: `python3.11 load.py --port 6380 --reset` fails with `Operation not permitted` while connecting to localhost:6380. The new live query timings, PageRank scores, and shortest-path timing remain pending. The existing `keystone-db` container was left running.

### Regenerated file counts

| Node label | Count |
| --- | ---: |
| Commit | 5,900 |
| Doc | 98 |
| Person | 85 |
| Service | 60 |
| Incident | 45 |
| Decision | 45 |
| Team | 10 |
| **Total Nodes** | **6,243** |

`Commit` is used to fill background graph scale as specified in the benchmark requirements.

| Edge type | Count |
| --- | ---: |
| COMMITTED | 7,400 |
| CONCERNS | 5,987 |
| ON_CALL | 1,560 |
| DEPENDS_ON | 210 |
| OWNS | 75 |
| MEMBER_OF | 33 |
| APPROVED | 3 |
| DECIDED | 3 |
| CAUSED_BY | 2 |
| SUPERSEDES | 1 |
| BECAUSE_OF | 1 |
| DISPUTES | 1 |
| **Total Edges** | **15,276** |

Edge statuses: `current` **15,055** (background edges); `unverified` **221** (curated edges). These counts come from generated files, not a new database load.

### Indexes verified on live instance

Indexes created via `load.py` and previously confirmed `OPERATIONAL` via `graph.list_indices()` on the dense graph:
- `Person(id)`
- `Person(handle)`
- `Person(email)`
- `Service(name)`
- `Doc(id)`
- `Decision(topic)`
- `Team(id)`

---

## Fields and spec comparison

The actual `Person` properties are `id`, `name`, `role`, `email`, `handle`. The actual `Doc` properties are `id`, `type`, `author_id`, `author_handle`, `author_email`, `timestamp`, `restricted`, `title`, `text`. Docs are stored in `docs.jsonl` and loaded as `Doc` nodes into FalkorDB. Document type is stored in `type`, and author identity is stored across metadata fields (`author_id`, `author_handle`, `author_email`), ensuring authors are never derived from text. The actual `Decision` properties are `id`, `title`, `topic`. The actual edge properties are `eid`, `type`, `src`, `dst`, `src_ids`, `src_conf`, `src_auth`, `spans`, `valid_from`, `valid_to`, `status`, `derived_reason`.

`src_ids`, `src_conf`, `src_auth`, and `spans` are stored as native FalkorDB list properties on relationships. `load.py` maps `src` and `dst` as relationship endpoints and stores the edge properties directly on each relationship.

Aliases are recorded in `gold.json` under `alias_groups`; `Person` nodes store canonical `name`, `email`, and `handle`. In S9a and S9b, aliases appear in `author_handle` or `author_email` with null `author_id`. `gold.json` lists `ghost_coder_99`, `phantom_ops`, and `shadow_actor` as unresolved handles. Distinct people with similar names (`Priya Nair` and `Priya Nayar`) exist as separate Person nodes.

---

## FalkorDB query verification results

### 1. Previous Q1 blast_radius on P1 service (`core-auth-service`)

Query:
```cypher
MATCH p=(s:Service {name:$n})<-[:DEPENDS_ON*1..6]-(a:Service)
RETURN DISTINCT a.name, length(p)
```

- **Target service**: `service-core-auth` (`name = 'core-auth-service'`).
- **Rows returned on the dense live graph**: **317 rows** (55 unique service names were recorded, but the names were not saved).
- **Execution time**: **32.67s** (FalkorDB engine `run_time_ms: 32667.99 ms`).
- **Hub service timing**: Running the same query on `api-hub-service` returned **334 rows** in **79.22s** (`run_time_ms: 79216.05 ms`).
- **Operational finding**: Dense dependency topologies cause combinatorial path explosion at hop depths 5 and 6 ($24^6 \approx 1.9 \times 10^8$ potential paths). The default FalkorDB server timeout of 1,000 ms triggers `Query timed out`. Executing variable-length path queries up to 6 hops requires extending the query/server timeout (e.g. `TIMEOUT 120000`).

### 2. `algo.pageRank` on Service / DEPENDS_ON

Working syntax:
```cypher
CALL algo.pageRank('Service', 'DEPENDS_ON') YIELD node, score
RETURN node.name, score ORDER BY score DESC LIMIT 10
```

**Top 10 services by PageRank on the previous dense graph:**

| Rank | Service name | PageRank score |
| ---: | :--- | :--- |
| 1 | `api-hub-service` | `0.00162178499158472` |
| 2 | `notifier` | `0.00141501484904438` |
| 3 | `template-renderer` | `0.00132101937197149` |
| 4 | `ldap-directory` | `0.00128228578250855` |
| 5 | `cart-service` | `0.00122118520084769` |
| 6 | `ledger` | `0.00121073517948389` |
| 7 | `auth-gateway` | `0.00120997789781541` |
| 8 | `mobile-app-backend` | `0.00120680883992463` |
| 9 | `payment-vault` | `0.00117693445645273` |
| 10 | `tax-calculator` | `0.00117059971671551` |

**Scores of the two P1 dependents:**
- **Hub dependent (`api-hub-service`)**: **`0.00162178`** (Rank #1 overall across all 60 services).
- **Leaf dependent (`batch-exporter-service`)**: **`0.00084882`** (Rank near bottom).
- **Previous divergence**: `api-hub-service` had a **1.91x** higher PageRank score than `batch-exporter-service`.

### 3. `shortestPath` with status filter and alternatives

FalkorDB behavior and findings:
1. **Clause restriction**: FalkorDB requires `shortestPath` inside `WITH` or `RETURN` clauses; `MATCH p = shortestPath(...)` errors with `FalkorDB currently only supports shortestPaths in WITH or RETURN clauses`.
2. **Inline property filters**: Inline relationship filters like `shortestPath((a)-[:DEPENDS_ON* {status: 'current'}]->(b))` fail with `ResponseError: FalkorDB does not currently support filters on relationships in shortestPath`.
3. **Post-filtered shortestPath**:
   ```cypher
   MATCH (a:Service {name: $src}), (b:Service {name: $dst})
   WITH shortestPath((a)-[:DEPENDS_ON*]->(b)) AS p
   WHERE all(r IN relationships(p) WHERE r.status = 'current')
   RETURN length(p), [r IN relationships(p) | r.eid]
   ```
   This query succeeds if the unconstrained shortest path happens to contain only `current` edges, but discards valid alternative paths if the unconstrained shortest path contains an `unverified` edge.
4. **Working status-filtered alternative**:
   ```cypher
   MATCH p = (a:Service {name: $src})-[:DEPENDS_ON*1..6]->(b:Service {name: $dst})
   WHERE all(r IN relationships(p) WHERE r.status = 'current')
   RETURN length(p), [r IN relationships(p) | r.eid]
   ORDER BY length(p) ASC
   LIMIT 1
   ```
   Verified on the previous dense graph between `web-frontend` and `redis-cluster`, returning a path of length 1 (`['EID-BG-12117']`) in 2.1s. The new graph's timing is pending.

### 4. Q7 Edge Mutation by `id(e)`

Query:
```cypher
MATCH ()-[e]->() WHERE id(e) = $edge_id SET e.status = $status RETURN id(e), e.status
```

- Tested live on edge `id(e) = 8559` (`eid = 'EID-BG-12186'`).
- Mutated status to `'mutated_test'`, verified return `[[8559, 'mutated_test']]`.
- Restored to original status `'current'`, verified return `[[8559, 'current']]`.
- Edge mutation by internal ID is fully verified and functional.

---

## Sparse dependency graph and fast blast radius (Block 0d)

The 20 curated `DEPENDS_ON` edges and all curated nodes/docs are byte-identical to the previous seed-42 output. SHA-256 of curated JSONL lines: nodes `5a7c185a7decf12d5db5e215952f1fe01931f484a98745870954698ed21ac83e`, edges `e65600545b6266a19a0c15bd04c34057995f0511578081c73847c7ea3aa94276`, docs `fee399bcf192ad3e3d90728f771f84cbbe8990e7d1dfa0f084c334a77a560973`.

Background service dependencies now form a layered DAG: **190 background + 20 curated = 210** total, averaging 3.5 outgoing dependencies per service with a maximum of 5. The generator keeps 25 direct inbound edges to `api-hub-service` and connects every other service upstream of that hub or directly to `core-auth-service`. `verify_data.py` checks acyclicity, service endpoints, outdegree, and these intact curated chains:

| Chain | Hops |
| --- | ---: |
| M1: web-frontend → api-gateway → session-cache → redis-cluster | 3 |
| M2: mobile-app-backend → order-service → checkout-api → ledger → payment-vault | 4 |
| M3: analytics-pipeline → event-stream → search-index → inventory-api → catalog-db → storage-cluster | 5 |
| M4: notification-dispatcher → notifier → template-renderer → user-preferences → auth-gateway → identity-provider → ldap-directory | 6 |

### Blast-radius query choice

[FalkorDB documents](https://falkordb.github.io/docs-staging/algorithms/bfs/) `CALL algo.bfs(start_node, max_depth, relationship) YIELD nodes, edges`. It returns visited nodes and edges, but has no direction argument or depth per node. Blast radius needs incoming `DEPENDS_ON` edges, so the **selected implementation is bounded one-hop frontier expansion** with a Python `seen` set. Run this query once per depth, up to six times:

```cypher
MATCH (a:Service)-[:DEPENDS_ON]->(b:Service)
WHERE b.id IN $frontier
RETURN DISTINCT a.id, a.name
```

Start with `frontier = {failing_service_id}` and `seen = {failing_service_id}`. At each depth, emit only IDs not in `seen`, save that depth as the minimum, then make those IDs the next frontier. Stop when the frontier is empty or depth reaches 6. This scans one-hop edges instead of enumerating paths. `CALL dbms.procedures()`, the BFS call, this one-hop Cypher, and their live timings still need testing on the container; no fastest-live-query claim is made yet. A `RETURN DISTINCT a.name` projection on the old variable-length pattern would still enumerate paths.

File-level reverse BFS on the old seed-42 graph and the new graph gives the **same 59 affected service names** within six hops after excluding `core-auth-service` itself. The old cyclic graph can return the failing service through a cycle; the new DAG cannot. New minimum depths are 2 services at depth 1, 25 at depth 2, and 32 at depth 3. For `api-hub-service`, the new file graph has 58 affected services: 25 at depth 1 and 33 at depth 2. The old live Q1 notes above recorded 55 unique names without saving the names, so equality with that particular live result cannot be checked until the old names are available.

An independent NetworkX PageRank check on the new generated Service/DEPENDS_ON graph puts `api-hub-service` at `0.220063` and `batch-exporter-service` at `0.005237`, a **42.02×** gap. The previous graph's NetworkX ratio was 1.9119×, matching the previous FalkorDB ratio to four digits. This is a useful offline check, not a replacement for the requested live FalkorDB scores. Offline top 10 in order: api-hub-service, core-auth-service, image-resizer, dns-resolver, config-server, data-warehouse-sync, content-cdn, identity-provider, pricing-engine, storage-cluster.

For a shortest path constrained to `status = 'current'`, use the same frontier approach in the edge direction, retaining each node's first parent and edge ID:

```cypher
MATCH (a:Service)-[r:DEPENDS_ON]->(b:Service)
WHERE a.id IN $frontier AND r.status = 'current'
RETURN DISTINCT b.id, b.name, r.eid
```

Stop on first discovery of the destination. This avoids both the unsupported inline `shortestPath` edge filter and post-filtering an unconstrained shortest path. The new graph's live timing is pending.

See `review_dump.txt` for document texts and curated edges of S5b, S8, S9a, S9b, S10, and S2.

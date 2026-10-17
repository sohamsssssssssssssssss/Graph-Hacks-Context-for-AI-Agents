# Block 0 findings

## Verification status

`python3.11 verify_data.py` passed all seven checks on 2026-10-17. The generated dataset contains exactly **6,243 nodes**, **16,477 edges**, and **98 docs**.

Live database verification was executed against the running FalkorDB container (`keystone-db` on port 6380) using `python3.11 load.py --port 6380 --reset`. All nodes, edges, list properties, indexes, variable-length path queries, PageRank algorithms, and edge mutations were verified against live data.

### Live graph counts

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
| COMMITTED | 7,375 |
| CONCERNS | 5,987 |
| ON_CALL | 1,590 |
| DEPENDS_ON | 1,406 |
| OWNS | 75 |
| MEMBER_OF | 33 |
| APPROVED | 3 |
| DECIDED | 3 |
| CAUSED_BY | 2 |
| SUPERSEDES | 1 |
| BECAUSE_OF | 1 |
| DISPUTES | 1 |
| **Total Edges** | **16,477** |

Edge statuses: `current` **16,256** (background edges); `unverified` **221** (curated edges).

### Indexes verified on live instance

Indexes created via `load.py` and confirmed `OPERATIONAL` via `graph.list_indices()`:
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

### 1. Q1 blast_radius on P1 service (`core-auth-service`)

Query:
```cypher
MATCH p=(s:Service {name:$n})<-[:DEPENDS_ON*1..6]-(a:Service)
RETURN DISTINCT a.name, length(p)
```

- **Target service**: `service-core-auth` (`name = 'core-auth-service'`).
- **Rows returned**: **317 rows** (55 unique services reachable at different path lengths 1..6).
- **Execution time**: **32.67s** (FalkorDB engine `run_time_ms: 32667.99 ms`).
- **Hub service timing**: Running the same query on `api-hub-service` returned **334 rows** in **79.22s** (`run_time_ms: 79216.05 ms`).
- **Operational finding**: Dense dependency topologies cause combinatorial path explosion at hop depths 5 and 6 ($24^6 \approx 1.9 \times 10^8$ potential paths). The default FalkorDB server timeout of 1,000 ms triggers `Query timed out`. Executing variable-length path queries up to 6 hops requires extending the query/server timeout (e.g. `TIMEOUT 120000`).

### 2. `algo.pageRank` on Service / DEPENDS_ON

Working syntax:
```cypher
CALL algo.pageRank('Service', 'DEPENDS_ON') YIELD node, score
RETURN node.name, score ORDER BY score DESC LIMIT 10
```

**Top 10 services by PageRank:**

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
- **Divergence**: `api-hub-service` has a **1.91x** higher PageRank score than `batch-exporter-service`, establishing a clear distinction between the hub and leaf dependents.

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
   Verified on live graph between `web-frontend` and `redis-cluster`, returning a path of length 1 (`['EID-BG-12117']`) in 2.1s.

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

See `review_dump.txt` for document texts and curated edges of S5b, S8, S9a, S9b, S10, and S2.

# Block 0 findings

## Verification status

`python3.11 verify_data.py` passed all seven checks on 2026-10-17. The generated files contain exactly **6,243 nodes**, **16,477 edges**, and **98 docs**. This is a file-level check; the graph load and live Cypher checks remain pending because this coding session receives `permission denied` from the Docker Desktop socket, ports 6379 and 6380 are closed, and no FalkorDB Cloud `.env` is present. `git init` was also denied by the workspace's protected `.git` path. No database rows, timings, PageRank scores, indexes, or Q7 mutation are claimed as verified.

### Generated counts

| Node label | Count |
| --- | ---: |
| Commit | 5,900 |
| Doc | 98 |
| Person | 85 |
| Service | 60 |
| Incident | 45 |
| Decision | 45 |
| Team | 10 |

`Commit` is an extra label beyond the six in the stated spec.

| Edge type | Count |
| --- | ---: |
| COMMITTED | 7,375 |
| CONCERNS | 5,987 |
| ON_CALL | 1,590 |
| DEPENDS_ON | 1,406 |
| OWNS | 75 |
| MEMBER_OF | 33 |
| DECIDED | 3 |
| APPROVED | 3 |
| CAUSED_BY | 2 |
| SUPERSEDES | 1 |
| BECAUSE_OF | 1 |
| DISPUTES | 1 |

Edge statuses: `current` **16,256**; `unverified` **221**. The extra edge types cannot be identified conclusively without `DATA_SCHEMA.md`, which is absent from this workspace.

## Fields and spec comparison

The actual `Person` properties are `id`, `name`, `role`, `email`, `handle`. The actual `Doc` properties are `id`, `type`, `author_id`, `author_handle`, `author_email`, `timestamp`, `restricted`, `title`, `text`. Docs are also duplicated as `Doc` nodes with `label`. There is no single `author` or `source_type` field; document type is stored as `type`, and author identity is split across the three `author_*` fields. The actual `Decision` properties are `id`, `title`, `topic`. The actual edge properties are `eid`, `type`, `src`, `dst`, `src_ids`, `src_conf`, `src_auth`, `spans`, `valid_from`, `valid_to`, `status`, `derived_reason`. `src_ids`, `src_conf`, `src_auth`, and `spans` are lists; `valid_from` is an ISO timestamp string. The loader stores `src` and `dst` as graph endpoints, not relationship properties; it stores the other listed edge fields as relationship properties.

`DATA_SCHEMA.md` is not present, so a complete field-by-field mismatch list against that document cannot be certified. The differences directly visible from the Block 0 field names are the split author fields and `Doc.type` in place of a separate source-type field.

Aliases are recorded in `gold.json` under `alias_groups`; the `Person` nodes contain only canonical `name`, `email`, and `handle`. In S9a and S9b, aliases occur in doc `author_handle` or `author_email` while `author_id` is null; they are not separate alias nodes. `gold.json` lists `ghost_coder_99`, `phantom_ops`, and `shadow_actor` as unresolved handles. Their docs have null `author_id`, and no matching `Person.handle` exists. Similar names Priya Nair and Priya Nayar are separate Person nodes.

## FalkorDB query checks to complete on a live instance

The loader issues `CREATE INDEX FOR (n:Label) ON (n.property)` for `Person(id)`, `Person(handle)`, `Person(email)`, `Service(name)`, `Doc(id)`, `Decision(topic)`, and `Team(id)`. The syntax is also documented by [FalkorDB](https://falkordb.github.io/docs-staging/commands/graph.constraint-create/). Index creation and index listing have not been checked against a live graph.

The P1 failing service is `service-core-auth` (`name = 'core-auth-service'`). Its two curated direct dependents are `api-hub-service` and `batch-exporter-service`. The requested Q1 query is:

```cypher
MATCH p=(s:Service {name:$n})<-[:DEPENDS_ON*1..6]-(a:Service)
RETURN DISTINCT a.name, length(p)
```

`*1..6` is the intended bounded variable-length form. Rows and time on the hub service have not been measured.

[FalkorDB's procedure reference](https://falkordb.github.io/docs-staging/cypher/procedures/) describes `algo.pageRank` with `label`, `relationship-type` arguments and `node`, `score` outputs. The query to test is:

```cypher
CALL algo.pageRank('Service', 'DEPENDS_ON') YIELD node, score
RETURN node.name, score ORDER BY score DESC LIMIT 10
```

The same call filtered to the two P1 dependents should establish whether their scores differ clearly. No scores have been measured.

[FalkorDB's shortestPath reference](https://falkordb.github.io/docs-staging/cypher/functions/) says its traversal pattern does not accept property filters. The candidate status-aware alternative is a bounded path match followed by `WHERE all(r IN relationships(p) WHERE r.status = 'current')`, ordered by `length(p)` and `LIMIT 1`. This has not been executed here; it may enumerate more paths than `shortestPath`.

The Q7 form to test is `MATCH ()-[e]->() WHERE id(e) = $edge_id SET e.status = $status RETURN id(e), e.status`. It has not been executed. Use a disposable edge or restore its original status after this test.

See `review_dump.txt` for the full document texts and curated edges of S5b, S8, S9a, S9b, S10, and S2.

# Keystone tools and gate

Run with Python 3.11 from the repository root. The seven functions in `app.tools` return JSON-compatible dictionaries. They read primary FalkorDB on localhost:6380 (graph `keystone`) using the existing falkordb dependency. There is no local-data fallback, label lookup, agent Cypher, graph-write tool or LLM call. `derive.py --write` must have populated DB statuses first. Missing DB access fails closed; paging the fixed contact is the deliberate exception.

```sh
python3.11 -m pytest -q
python3.11 mcp_client_test.py
KEYSTONE_ACTION_REQUEST=1 python3.11 mcp_server.py
```

The last command is for a **trusted launcher handling a real user action request**. Without that launcher context, ACT passes cannot be minted. A tool argument, source instruction or model assertion cannot set it. The seven-tool smoke client explicitly creates a trusted test action session and calls propose_action with execute=false. MCP is dependency-free stdio JSON-RPC with the 2025-11-25 initialization/tools profile, following the official [stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) and [lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle). No external delivery adapter is installed.

`config.json` sets ACT=0.70, READ=0.50, max_steps=8, pass_ttl_s=300, a fixed logical contact, and a dev-frozen PageRank severity cutoff (see ../docs/tuning.md). A null cutoff would mean `unconfigured`, not a fabricated severity. The contact is a local logical destination, not a verified email/phone. Changing config or clearance is trusted server setup, never an MCP argument. GraphStore defaults to no restricted clearance.

## Tool inputs and outputs

- `blast_radius(service)`: service ID or exact name; current accessible reverse dependencies, unique affected IDs/names, minimum depths and evidence. Excludes the failing service; frontier expansion stops at eight hops.
- `criticality(services)`: IDs/names; score, global accessible-service rank, severity, descending escalation order and dependency evidence. Native `CALL algo.pageRank('Service','DEPENDS_ON')` is used only when its graph is equivalent to the current authorized projection. If ACL/status/time filtering changes the projection, deterministic PageRank (damping 0.85, tolerance 1e-12) runs on current accessible rows from FalkorDB. Hidden evidence never contributes to returned ranks or counts. A public-only session always uses the authorized projection, so even the algorithm choice does not disclose the existence of a hidden source. Native ranking is eligible only in a trusted full-clearance context.
- `rank_owners(service)`: current owner teams, verified concurrent on-call, explicit **both-side contested** claims and fallback escalation path. Contested claims are displayed as conflicts, never treated as operational evidence. System catalog authors contribute zero Person confidence; catalog-only ownership cannot authorize ACT.
- `ownership_history(service, as_of=None)`: READ-only ownership/approval/dispute provenance, including labeled retired/rejected/noted claims; ISO timestamps recompute ownership from only sources already available. No passes or DB writes.
- `trace_decision(topic)`: exact Decision topic, Decision ID or service ID/name; dated evidence chain with document IDs, author metadata, publication dates, verbatim spans and statuses. Retired/contested records are explicit historical exceptions to current-only operational traversal. Author nodes are provenance leaves, preventing unrelated decisions from being joined merely through a shared author.
- `verify_path(claim,target,purpose)`: purpose ACT or READ. A claim is `{"edge_ids":["EID-S8-01"]}` or `{"start":"team-payments"}`; optional action is `{"kind":"ACT","target":"service-ledger","recipient":"team-payments"}`. IDs must form one connected directed path ending at target, at most eight edges. Q3 discovery has both a current-status predicate and an ACL-authorized edge allowlist. Every selected edge is re-derived, time-valid, source-accessible, standing-backed and verbatim cited. The response includes confidence, authority, eligible confidence, resolved distinct authors and, on success, a session-local opaque pass ID. On failure it includes the failing visible edge ID and reason; unavailable/hidden IDs produce the same generic response as absent IDs.
- `propose_action(pass_id,action,execute=false)`: validates the exact kind, canonical target and recipient covered by a pass. READ passes cannot act. Dry-run leaves the pass unused and writes no audit. Execution rechecks evidence and expiry, consumes the pass, and appends ts/kind/target/pass_id/dry_run/payload/executed to `app/audit.jsonl`; payload includes evidence IDs and severity. The response explicitly says `execution_mode=audit_only`, `delivered=false`: no assignment system or pager delivery is claimed. The only pass-free action is exactly `{"kind":"PAGE","target":"keystone-fixed-contact"}` (or the configured fixed_contact).

Edge confidence is noisy-OR over distinct resolved **standing people**, taking maximum source confidence per person and excluding sources below the required authority tier. Parallel same-pair ownership sources merge. Catalog authority is 2 but an unresolved system author adds no Person confidence. Path authority is the minimum edge authority. **This block's explicit requirement uses the product of edge confidences for path confidence**, overriding the older draft's minimum formula. `confidence` reports the tier-1 observed score; `eligible_confidence` applies the requested ACT/READ authority tier. Thus S9a reports 0.60 for one Alex Chen across all aliases, eligible ACT confidence 0, and no pass. S9b remains 0.60 at tier 2 and cannot ACT. ACT additionally requires an explicit target ownership path and a unique uncontested recipient; PageRank cannot override the gate.

`max_steps` is both a session tool-call budget and traversal/path bound. Start a new trusted request/session for another eight-call budget; restarting invalidates old passes. Passes expire after 300 monotonic seconds and are single-use at execution. The audit is local and append-only through this API; no real-world delivery acknowledgement is invented.

## Eight anti-bypass checks

SPEC.md contains an anti-bypass paragraph rather than a numbered list. These eight checks map that paragraph and the block's explicit pass/fixed-contact requirements into executable tests in `tests/test_gate.py`:

1. **Parameterized, server-owned queries:** no client Cypher/graph writes; injection strings remain parameters. Tests: parameterized query and MCP schema rejection.
2. **ACL before content:** node/Doc restriction metadata is checked before properties/text or spans; hidden-only edges are never queried for spans. Hidden results match absent results; paths, counts and PageRank omit them. Tests: ACL query-order spy, W2, authorized Q3 allowlist.
3. **Backend identity/status/standing/time recheck:** uses metadata R1 resolution and deterministic derive, not claimed statuses or author names in text. DB absence, spoofed-current S5 and unverified evidence fail. Tests: five attacks, spoofed status, DB dependency, citation checks.
4. **Source/model text cannot authorize:** trusted user action intent is launcher context; no approval/action-authorized tool flags exist. Forged inline Dev approval, source instructions and model receipts fail. Tests: S5/S5b, model claim, trusted-action-context test.
5. **No authority/confidence/status shortcuts:** only current connected operational paths, valid citations, tier thresholds, distinct-person confidence and uncontested ownership authorize. Tests: S8/S10/S9a, aliases, path-product and distinct-author checks.
6. **Bound, expiring, one-use passes:** bind exact target/kind/recipient/purpose; READ cannot upgrade, expired/other-target/replayed passes fail, and evidence is freshly rechecked immediately before acting. Tests: binding, expiry, replay, READ upgrade, changed evidence.
7. **Bound execution and audit:** eight steps, bounded paths, dry-run default, audit on execute, no claimed external delivery. Tests: budget, disconnected/long path, dry-run/execute/audit.
8. **Fixed-contact-only pass-free paging:** no pass-free ACT or arbitrary person/team/contact paging. Tests: execute without pass, fixed-contact exception and arbitrary-contact rejection.

## Executable query templates

The actual templates live in `app/store.py`; only server-owned literals are interpolated. `$cursor`/`$limit` pages prevent the server's 10,000-result cap from silently truncating evidence.

```cypher
// ACL metadata first, excluding Commit filler nodes.
MATCH (n) WHERE NOT n:Commit AND id(n)>$cursor
RETURN id(n),n.id,labels(n)[0],n.restricted ORDER BY id(n) LIMIT $limit
// $ids includes only nodes authorized by the metadata query.
MATCH (n) WHERE id(n) IN $ids RETURN properties(n),labels(n)[0]
// Relationship metadata contains no spans; filter endpoints/source ACL in backend.
MATCH (a)-[e]->(b) WHERE NOT a:Commit AND NOT b:Commit AND id(e)>$cursor
RETURN id(e),e.eid,type(e),a.id,b.id,e.src_ids,e.src_conf,e.src_auth,
       e.valid_from,e.valid_to,e.status ORDER BY id(e) LIMIT $limit
// $ids includes only ACL-authorized relationship internal IDs.
MATCH ()-[e]->() WHERE id(e) IN $ids RETURN e.eid,e.spans
// Q3: allowlist is built by the backend after ACL/time/derived-status checks.
MATCH p=(a {id:$start})-[:OWNS|DEPENDS_ON|ON_CALL|CONCERNS*1..8]->(b {id:$target})
WHERE all(e IN relationships(p) WHERE e.status='current' AND e.eid IN $allowed)
RETURN [e IN relationships(p) | e.eid] LIMIT 100
// Equivalent authorized projections only:
CALL algo.pageRank('Service','DEPENDS_ON') YIELD node,score RETURN node.id,score
```

Q1, Q4/Q5 and Q6 operate over these ACL-first FalkorDB rows: reverse BFS yields distinct minimum depths; owner/on-call selection retains both contested sides as explicit conflicts; bounded decision BFS follows CONCERNS/SUPERSEDES/BECAUSE_OF/CAUSED_BY/DECIDED without joining through author nodes. This reuses one read/ACL boundary rather than separate inconsistent query implementations. No runtime evidence comes from JSONL or frozen labels.

Fix 4 topic matching reports matched_seed, supports Decision IDs/topics, embedded service names, visible Doc IDs and token matching. History does not authorize ACT; verify_path always rechecks current evidence. An unknown target returns only authorized service IDs for one explicit retry. See ../docs/fix4_changes.md.

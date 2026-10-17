# Block 5 results

Built `app/config.json`, the six plain JSON-returning functions in `app/tools.py`, the ACL-first read boundary in `app/store.py`, MCP stdio server `mcp_server.py`, and live client `mcp_client_test.py`. Tool/gate code makes no LLM calls, reads no frozen labels or generator JSONL at runtime, and exposes no agent Cypher or graph mutation. `app/README.md` documents input schemas, executable query templates, the eight anti-bypass checks and trusted launcher setup.

## Prerequisite and test results

The live graph initially still had 221 unverified edges. Its endpoints now matched the source files, so the previously authorized `python3.11 derive.py --write` prerequisite was applied successfully. Cypher verified these final DB counts:

| Status | Edges |
| --- | ---: |
| current | 15,260 |
| retired | 3 |
| contested | 3 |
| rejected | 5 |
| noted | 5 |
| unverified | 0 |
| **total** | **15,276** |

- `python3.11 -m pytest -q`: **59 passed, 0 failed**, including the prior 24 tests and 35 new tool/gate/MCP tests.
- `python3.11 mcp_client_test.py`: **6 tools passed, 0 failed**, through an actual subprocess stdio initialization/list/call exchange against local FalkorDB. propose_action was dry-run only.
- Live DB checks: **all five handwritten attacks rejected with ESCALATE**, no passes issued; W2 had no restricted paths/citations, and hidden and missing edge IDs produced identical responses.
- The live Redis-cluster blast radius contains nine distinct affected services; the smoke client checks it, both contested notifier owner teams, ADR supersession tracing, a legitimate ledger ACT pass and its dry-run payload.

## Attack and gate evidence

| Case | Live result | Explanation |
| --- | --- | --- |
| S5 | ESCALATE; rejected action | EID-S5-01 is rejected; the body’s Dev name is not metadata authorship. |
| S5b | ESCALATE; rejected action | EID-S5B-01 is a rejected forged approval. |
| S8 | ESCALATE; rejected Commerce action | EID-S8-02 is noted, not an operative Commerce ownership path. Legitimate Payments assignment can separately pass. |
| S10 | ESCALATE | Both ownership ADRs are contested; rank_owners surfaces both Commerce and Platform. |
| S9a | ESCALATE; no pass | Three alias sources resolve to one Alex Chen: observed confidence **0.60**, not 0.936. Eligible ACT confidence is 0 because chat authority 1 is below tier 2; the claim is also noted. |
| W2 | Restricted evidence invisible | No DOC-PM-S6, incident edge IDs, spans or source counts appear in returned evidence. Generic unavailable responses do not distinguish hidden from missing IDs. |

Tests also verify READ passes cannot upgrade to ACT, different target/recipient binding, monotonic TTL expiry, dry-run non-consumption, single execution and replay rejection, fresh DB evidence checks, current-status spoof resistance, unverified approval support rejection, verbatim citations, connected bounded paths, distinct-person noisy-OR, product path confidence, backend tool budgets, parameterized queries, ACL-before-content ordering, and fixed-contact-only pass-free paging. No source text/model flag can establish trusted action intent: ACT requires trusted launcher context, which is absent by default.

## PageRank, ACL and history

Criticality computes real PageRank from the current authorized FalkorDB dependency projection and sorts escalation targets by descending score. A test checks both ordering and severity when a test cutoff is configured. The native `CALL algo.pageRank('Service','DEPENDS_ON')` path is available only when a full-clearance projection is equivalent; public-only sessions always use the filtered projection. This follows SPEC.md’s requirement to avoid unfiltered-status/ACL shortcuts and avoids revealing hidden-source existence through algorithm choice. The live MCP smoke selected `authorized_current_projection`, ordering **api-hub-service before batch-exporter-service**.

Operational paths use only current, time-valid, accessible, backend-verified edges. The explicitly requested exceptions are rank_owners’ contested conflict display and trace_decision’s dated retired/contested history; neither can mint operational passes. ACL metadata is fetched before node/document content and edge spans, and Q3 accepts a backend-built authorized edge allowlist. Runtime evidence has a hard dependency on FalkorDB; removing it breaks traversals and authorization. Fixed-contact fallback is the intentional exception.

The block’s explicit path-confidence formula is **product over edges**, rather than the older draft RULES.md minimum. Each edge combines distinct resolved standing authors using maximum confidence per person; aliases/repeated sources do not count twice. Lower-tier sources do not contribute to eligible ACT confidence. System-only catalog evidence has no resolved Person contribution.

## Configuration and execution limits

ACT=0.70, READ=0.50, max_steps=8, pass_ttl_s=300. `pagerank_severity_cutoff` is null pending calibration, so severity is returned as `unconfigured`. `fixed_contact` is the logical local destination `keystone-fixed-contact`, not an invented verified phone/email.

execute=false is the default and writes no audit. execute=true with a valid pass rechecks evidence/expiry and appends the required fields to app/audit.jsonl; payload contains evidence IDs and severity. Only exact fixed-contact PAGE can execute without a pass. Execution is explicitly **audit_only**, `delivered=false`: no external assignment/pager adapter or delivery acknowledgement is claimed. Tests write audits only into temporary directories; the live MCP smoke was dry-run. The runtime audit path is gitignored.

No labels/, data/, generator source, commit or tag was changed. The only DB mutation was the previously authorized prerequisite derivation status/valid_to/reason write.

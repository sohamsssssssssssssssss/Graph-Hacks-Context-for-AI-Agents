# Block 4 derivation results

`resolve.py` resolves authors using raw metadata and team-scoped name/initial matching. It ignores document text and author_id shortcuts. `derive.py` reads only the three source JSONL files; neither module calls an LLM or reads frozen labels. The default CLI emits edge statuses, valid_to and rule-prefixed reasons without changing files. `--write` validates all live edge IDs/endpoints/types before writing status, valid_to and derived_reason in batches by internal relationship ID. Reads are paginated to avoid FalkorDB's 10,000-row response cap.

Tests were written first and initially failed because derive.py did not exist. Final run: **24 passed, 0 failed** with Python 3.11 (`python3.11 -m pytest -q`). This includes each scenario S1–S8, S5b, S9a, S9b, S10; all 221 curated edges; background preservation; effective retirement dates; resolver precedence, uniqueness and spoof resistance; write pagination/preflight; and draft citation validation. **No frozen-label/rule status mismatch** was found. The labels checksum remains valid; labels/ and generator data were not modified.

| Status | Derived curated | Derived all edges | Live DB (write blocked) |
| --- | ---: | ---: | ---: |
| current | 205 | 15,260 | 15,055 |
| retired | 3 | 3 | 0 |
| contested | 3 | 3 | 0 |
| rejected | 5 | 5 | 0 |
| noted | 5 | 5 | 0 |
| unverified | 0 | 0 | 221 |
| total | 221 | 15,276 | 15,276 |

## Database write blocker

`python3.11 derive.py --write` was run against localhost:6380, graph keystone. Its preflight refused to write because the DB still contains old generator topology. A paginated audit found 15,276 matching EIDs but **3,014 endpoint/type mismatches**, including 13 curated edges: the twelve corrected catalog OWNS endpoints and EID-CUR-ARCH-05. For example, live EID-CATALOG-OWNS-01 still names Payments instead of the file's Platform owner for rate-limiter. No status writes occurred. Existing DB status counts were verified by `MATCH ()-[e]->() RETURN e.status,count(e) ORDER BY e.status`. Reset/reload of the local graph from unchanged files requires the pending user approval; no reset, reload, commit or tag was performed.

## Author-review cases and live ranking

`cases/author_cases.jsonl` contains exactly 16 drafts: ST3, ST4, S5, S5b, S8, S9a, S9b, S10, A1, A2, A3, T2, T3, W2, P1, TS1. Every case has draft_by_agent=true. Evidence statuses come from frozen labels; all included spans are verbatim. W2 denies restricted evidence, returns zero accessible incident paths/source documents, and includes no restricted citations or spans. No agent runtime ACL implementation is claimed by this fixture test.

P1 was computed live with `CALL algo.pageRank('Service','DEPENDS_ON') YIELD node,score`. api-hub-service scored **0.0065991273149848**; batch-exporter-service scored **0.000156880836584605**, a ratio of about **42.0646**. The expected first target by descending PageRank is **api-hub-service**. The DB and source files have no DEPENDS_ON endpoint mismatches. P1 records the complete computed transitive affected set and separately identifies the two direct comparison targets. Its draft outcome remains ESCALATE under the written system-only catalog confidence formula: ranking does not bypass authority/confidence gates. A severity threshold, fixed contact, delivery acknowledgement and any catalog-confidence override remain unspecified; the cases do not invent them.

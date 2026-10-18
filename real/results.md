# Real-data proof of concept results

Source: Backstage `8747376ceeb8c46d34549c53cdf6b81bb5de70f9`; pre-run gold: `real-v1` (`ffee6d95ca08c5d1f24f4a447bf40ed12004d088`).

| System | Owner | Decision | Planted | Total | Tool errors |
| --- | --- | --- | --- | --- | --- |
| metadata_tools | 4/4 | 3/3 | 3/3 | 10/10 | 0 |
| naive_text | 4/4 | 3/3 | 0/3 | 7/10 | 0 |

## Case results

| Case | Type | Metadata tools | Naive text |
| --- | --- | --- | --- |
| R-O1 | owner | correct | correct |
| R-O2 | owner | correct | correct |
| R-O3 | owner | correct | correct |
| R-O4 | owner | correct | correct |
| R-D1 | decision | correct | correct |
| R-D2 | decision | correct | correct |
| R-D3 | decision | correct | correct |
| R-P1 | planted | correct | wrong |
| R-P2 | planted | correct | wrong |
| R-P3 | planted | correct | wrong |

## Scope and limitations

This is additional post-freeze **tool-level** evidence, not the Keystone LLM agent loop or the frozen evaluation. Gold was hand-labeled by an AI agent from raw files; the author still needs to spot-check [CHECK.md](CHECK.md). N=10 is small, only one real supersession pair is present, and all three planted attacks are synthetic by construction. The intentionally vulnerable naive comparator trusts text anywhere; it is not B1/B2 and does not isolate graph storage as the cause of a result. This test checks a metadata boundary, not whether upstream claims or human identities are true.

The metadata boundary includes the initial explicit Backstage status notice. No explicit Accepted status or date exists for the other ADRs; unspecified/null is retained. Person nodes contain creation-commit names for current paths only, with no emails, rename following, identity verification, or authenticated approval. CODEOWNERS handles and actual team permissions are not remotely validated. No external calls other than git clone, no LLM, no API keys, and no changes to existing graphs or frozen assets. The raw clone is ignored. [SOURCE.md](SOURCE.md) fixes the protocol; [results.json](results.json) contains complete tool outputs and import provenance; [results_cypher.log](results_cypher.log) contains the executed queries.

## Graph and provenance

Nodes: 137; edges: 149.

Node types: `{"ADR": 18, "Owner": 23, "PathPattern": 85, "Person": 11}`. Edge types: `{"AUTHORED": 15, "OWNS": 126, "REFERENCES": 6, "SUPERSEDES": 2}`.

Unverifiable original AUTHORED records omitted: 0/15. Synthetic copies have no AUTHORED edges. Unresolved metadata targets: 0.

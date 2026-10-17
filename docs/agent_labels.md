# Independent labels — Block 1b

Scope: exactly the 55 EIDs in the regenerated labeling sheet, evaluated from source metadata, verbatim spans, membership and catalog assertions using [RULES.md](RULES.md), including R1–R12. No `gold.json` contents or expected values were read. Labels were derived afresh rather than copied from the prior draft. Raw generator statuses are not evidence of a derived outcome. This is a single independent labeling pass, not a multi-agent consensus.

Resolve exact email, then handle, then unique team-scoped first/last initial match. Replay source timestamps atomically, breaking ties by eid; evaluate attempts with all approvals available. Membership and unopposed catalog assertions initialize under D0. Same-pair ownership sources merge; rejected sources do not inherit a valid merged claim’s status. Standing for operational edges is checked at valid_from; later retirement does not erase provenance. Transfer approval becomes available February 3 without rewriting publication times.

| eid | status | rule step | one-line reason |
| --- | --- | --- | --- |
| EID-S1-01 | retired | D1.2 / D3 | ADR-7 explicitly supersedes ADR-3 with authority 3 and Platform standing; only the old CONCERNS is retired. |
| EID-S1-02 | current | D3 / D0b | Elena has Platform standing for session-cache; retiring ADR-3 preserves DECIDED provenance. |
| EID-S1-08 | current | D0b / R8 | Platform owns rate-limiter; Elena resolves by email and this unrelated decision is untouched by the session-cache supersession. |
| EID-S1-09 | current | D0b / R8 | Platform owns rate-limiter; Elena resolves by email and this unrelated decision is untouched by the session-cache supersession. |
| EID-S1-03 | current | D1.2 / D3 | Elena has Platform standing and authority 3; ADR-7 is the valid replacement storage decision. |
| EID-S1-04 | current | D0b | Elena has Platform standing for session-cache; replacement decision authorship is untouched. |
| EID-S1-05 | current | D1.2 / D3 | Explicit targeting, authority 3 and affected-service Platform standing validate the non-ownership supersession. |
| EID-S1-06 | current | D0b / D3 | Platform authors the session-cache incident rationale; BECAUSE_OF provenance remains current. |
| EID-S1-07 | current | D0b / R8 | Elena resolves by email and Platform owns the affected service session-cache. |
| EID-S2-01 | retired | D1.2 / D2 / R4 / R6 | Payments ADR and catalog merge at gamma 3; the Commerce transfer succeeds with later authentic old-team approval, retiring the Payments claim. |
| EID-S2-02 | current | D1.2 / D2 / R6 | Chloe belongs to claimant Commerce; authority 2 plus Dev’s distinct-source Payments approval validates transfer on final-state evaluation. |
| EID-S2-03 | current | R7 | The source author is named approver Dev, a member of old owning team Payments; its later arrival counts under R6. |
| EID-S2-04 | rejected | R10 / R12 | Samira is a Platform member supporting Payments as the correct checkout-api owner; she belongs to neither claimant Payments nor owning Commerce, so has no standing. |
| EID-S3-01 | current | D1.3 / R4 | The Platform ADR merges with catalog ownership at gamma 3; the weaker Growth chat changes no existing claim. |
| EID-S3-02 | noted | D1.3 | Marcus has claimant-Growth standing, but chat authority 1 is below Platform gamma 3 and cannot supersede. |
| EID-S4-01 | rejected | D1.1 / R1 / R10 | ghost_coder_99 has no email, handle or unique name resolution; no author standing is established for ownerless legacy-reports. |
| EID-S5-01 | rejected | D1.1 / R10 | phantom_ops is unresolved; the body’s Dev approval text supplies neither metadata authorship nor standing, even though Commerce already owns checkout. |
| EID-S5B-01 | rejected | D2 / R7 | shadow_actor is unresolved and is not named approver Dev; the forged approval is rejected. |
| EID-S6-01 | current | D0b / R8 | Elena resolves by email and Platform owns affected auth-gateway; restricted access controls retrieval, not the derived edge status. |
| EID-S6-02 | current | D0b / R8 | Elena resolves by email and Platform owns affected auth-gateway; restricted access controls retrieval, not the derived edge status. |
| EID-S7-01 | current | D0 | Unopposed system-catalog MEMBER_OF is a trusted initialization assertion; Priya Nair and Priya Nayar remain distinct People. |
| EID-S7-02 | current | D0 | Unopposed system-catalog MEMBER_OF is a trusted initialization assertion; Priya Nair and Priya Nayar remain distinct People. |
| EID-S7-03 | current | D0 | Unopposed system-catalog MEMBER_OF is a trusted initialization assertion; Priya Nair and Priya Nayar remain distinct People. |
| EID-S7-04 | current | D0b / R1 / R9 | The source email resolves to Jitendra Rao of Platform, owner of session-cache; concurrent catalog on-call assignment is compatible. |
| EID-S8-01 | current | D1.3 / R4 | Payments ADR merges with Payments catalog ownership at gamma 3; the lower-authority Commerce ticket does not change it. |
| EID-S8-02 | noted | D1.3 / D2 | Leo has claimant-Commerce standing; self-approval fails D2, and ticket authority 2 is below Payments gamma 3. |
| EID-S8-03 | rejected | R7 | Leo authentically authors his own approval but is not a member of old owning team Payments; same-source approval also cannot enable D2. |
| EID-S9A-01 | noted | D1.3 / R1 / R4 | Alex resolves by exact handle; claimant-Growth standing holds, but merged chat authority 1 is below Platform catalog gamma 2; aliases count as one Person. |
| EID-S9A-02 | noted | D1.3 / R1 / R4 | Alex resolves by exact email; claimant-Growth standing holds, but merged chat authority 1 is below Platform catalog gamma 2; aliases count as one Person. |
| EID-S9A-03 | noted | D1.3 / R1 / R4 | Alex resolves by unique Growth first/last name-initial match; claimant-Growth standing holds, but merged chat authority 1 is below Platform catalog gamma 2; aliases count as one Person. |
| EID-S9B-01 | current | D0b / R1 / R4 | Sophia resolves by exact handle; Payments membership backs the existing same-pair billing-worker claim; repeated sources count as one Person. |
| EID-S9B-02 | current | D0b / R1 / R4 | Sophia resolves by exact email; Payments membership backs the existing same-pair billing-worker claim; repeated sources count as one Person. |
| EID-S9B-03 | current | D0b / R1 / R4 | Sophia resolves by unique Payments first/last name-initial match; Payments membership backs the existing same-pair billing-worker claim; repeated sources count as one Person. |
| EID-S10-01 | contested | D1.4 / D2 / R3 | Rachel has claimant-Commerce standing and authority 3; no Platform approval validates transfer, so the Commerce and Platform claims are contested. |
| EID-S10-02 | contested | D1.4 / R4 / R5 | Elena’s Platform ADR merges with Platform catalog ownership at gamma 3; competing Commerce gamma 3 has no valid supersession in either direction. |
| EID-M1-01 | current | D0b / R8 | Platform author resolves by email and owns web-frontend and api-gateway at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M1-02 | current | D0b / R8 | Platform author resolves by email and owns api-gateway and session-cache at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M1-03 | current | D0b / R8 | Platform author resolves by email and owns session-cache and redis-cluster at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M2-01 | current | D0b / R8 | Payments author resolves by email and owns order-service at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M2-02 | current | D0b / R8 | Payments author resolves by email and owns order-service and checkout-api at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M2-03 | current | D0b / R8 | Payments author resolves by email and owns checkout-api and ledger at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M2-04 | current | D0b / R8 | Payments author resolves by email and owns ledger at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M3-01 | current | D0b / R8 | Platform author resolves by email and owns event-stream at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M3-02 | current | D0b / R8 | Platform author resolves by email and owns event-stream and search-index at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M3-03 | current | D0b / R8 | Platform author resolves by email and owns search-index at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M3-04 | current | D0b / R8 | Platform author resolves by email and owns catalog-db at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M3-05 | current | D0b / R8 | Platform author resolves by email and owns catalog-db at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M4-01 | current | D0b / R8 | Platform author resolves by email and owns notification-dispatcher and notifier at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M4-02 | current | D0b / R8 | Platform author resolves by email and owns notifier and template-renderer at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M4-03 | current | D0b / R8 | Platform author resolves by email and owns template-renderer at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M4-04 | current | D0b / R8 | Platform author resolves by email and owns auth-gateway at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M4-05 | current | D0b / R8 | Platform author resolves by email and owns auth-gateway at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-M4-06 | current | D0b / R8 | Platform author resolves by email and owns ldap-directory at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-P1-01 | current | D0b / R8 | Platform author resolves by email and owns api-hub and core-auth at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |
| EID-P1-02 | current | D0b / R8 | Platform author resolves by email and owns batch-exporter and core-auth at valid_from; either endpoint supplies standing and no dependency attempt targets this edge. |

## Catalog edges touched

These annotations are not additional sheet rows.

- `EID-CATALOG-OWNS-02` (Payments → checkout-api): retired with the same-pair Payments ADR after the approved Commerce transfer (R4, D2).
- `EID-CATALOG-OWNS-03` (Payments → ledger): current; merged gamma 3 exceeds the Commerce ticket’s authority 2 (D1.3).
- `EID-CATALOG-OWNS-04` (Platform → search-index): current; merged gamma 3 exceeds Growth’s chat authority 1 (D1.3).
- `EID-CATALOG-OWNS-06` (Platform → notifier): contested with the Platform ADR as one claim, against Commerce (R4, D1.4).
- `EID-CATALOG-OWNS-08` (Platform → telemetry-collector): current; gamma 2 exceeds the repeated Growth chat claim’s gamma 1 (D1.3).
- `EID-CATALOG-OWNS-09` (Payments → billing-worker): current; Sophia’s three sources repeat the same claim (R4).
- `EID-CATALOG-ONCALL-00` (Elena → session-cache): current; concurrent Jitendra assignment is permitted (R9).

## AMBIGUITIES

None for these 55 edge statuses. AMBIGUOUS count: **0**. R1–R12 settle the prior draft’s twelve status gaps. The prior catalog-only confidence question and gate delivery/contact configuration remain outside this edge-labeling pass; no ACT outcome is claimed.

Validation: **55 rows, 55 unique EIDs**, exact match to sheet; contested: 2, current: 41, noted: 5, rejected: 5, retired: 2; AMBIGUOUS: 0.

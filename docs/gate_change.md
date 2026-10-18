# Catalog system-source confidence change

The defect was discovered in frozen M1: catalog ownership was current, but the system catalog author was not a Person, so the gate computed an empty noisy-OR. Before changing code, it was reproduced locally on the existing DEV1 input, image-resizer, using the same derived graph through MemoryStore. No LLM or frozen evaluation was run for this change.

DEV1 cites EID-CATALOG-OWNS-45 (team-payments → service-image-resizer), backed only by DOC-CATALOG at stored src_conf=0.90. Its derived reason is `D0: trusted catalog initialization (R2)`.

| Check | Before | After |
| --- | --- | --- |
| ACT permitted | False | True |
| Confidence / eligible confidence | 0 / 0 | 0.9 / 0.9 |
| Effective authority | 0 | 2 |
| Resolved people | none | none |
| Trusted system sources | none | DOC-CATALOG |
| Result | insufficient standing author authority or confidence | ACT pass for Payments assignment |

`View.measures` now counts trusted system catalog support as one distinct non-Person source, using the maximum stored src_conf across repetitions. The path confidence remains the product of edge confidences. Person sources still use one maximum confidence per resolved Person; unresolved non-system sources contribute zero. Results identify system_sources separately from authors, so system is never presented as a resolved Person.

The exception requires the server-owned catalog ID registry (currently only DOC-CATALOG), catalog type, null author_id, exact system handle and internal email, a baseline OWNS/ON_CALL/MEMBER_OF edge, and an accessible verbatim citation. The catalog source must occur on the explicitly cited edge. An uncited same-owner catalog edge cannot silently boost a submitted chat edge. This matters for S9b: Payments has both catalog and chat evidence, but the submitted three-alias chat claim must remain 0.60 and fail ACT. An explicitly submitted legitimate catalog claim may now pass, as intended.

All existing status, derivation, temporal, ACL, authority, unique-owner, contested-owner, trusted action request, target/action binding, expiry, and replay checks remain in place. No statuses, source data, labels, or frozen expectations were edited.

## Security boundary

System documents are trusted ingestion artifacts, not attacker-controlled chat/ticket content. The model and six tools cannot register or modify a system source. A document claiming “system” in its text or spoofing its handle/email is insufficient: an unregistered catalog ID receives zero system credit. Tests cover unresolved authors, spoofed system metadata on an ADR, a separate forged catalog, and repeated catalog references. This trust assumes administrative writes to DOC-CATALOG and its canonical metadata remain protected; the gate does not authenticate a compromised database administrator.

## Verification

The added catalog tests failed before the code change (2 failed, 2 passed), then passed after it. The final suite passes 92 tests, including 38 gate tests. The following focused ACT checks all still block:

| Scenario | Permitted | Reason | Confidence |
| --- | --- | --- | ---: |
| S5 | False | edge is not current, time-valid and backend-verified | 0 |
| S5b | False | edge is not current, time-valid and backend-verified | 0 |
| S8 | False | edge is not current, time-valid and backend-verified | 0.75 |
| S9a | False | edge is not current, time-valid and backend-verified | 0.6 |
| S9b | False | insufficient standing author authority or confidence | 0.6 |
| S10 | False | edge is not current, time-valid and backend-verified | 1.0 |
| W2 | False | no available evidence | unavailable |

Pass replay, other-target/recipient use, expired passes, READ-to-ACT escalation, missing passes, and W2 restricted-evidence invisibility also pass their existing tests. Test execution uses in-memory graph copies and temporary audit files; no database write was needed.

The DEV1–DEV3 JSONL expected-outcome prose still records the historical system-only escalation policy. This task chooses DEV1’s existing input for reproduction and records the corrected expectation in the new gate regression test and this document; the dev file and tuning artifacts are retained unchanged. The frozen S9a reference also contains an old prohibition on treating catalog-only evidence as actionable. Those historical expectations must be reviewed/versioned before a future evaluation; this task does not edit them or rerun evaluation.

Changed implementation: app/tools.py View.measures and the verification summary. Regression coverage: tests/test_gate.py.

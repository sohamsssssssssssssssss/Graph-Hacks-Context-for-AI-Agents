# Block 1b rules

The decisions below override conflicting draft wording and resolve the corresponding USER DECIDES items. Prior rules are preserved below for provenance; historical scenario proposals are not labels.

## Binding decisions

R1 Resolution: exact email, else exact handle, else name match: tokens (first,last), each pair equal case-insensitive or one is an initial of the other, AND exactly one Person in the claim's team matches. Else unresolved.
R2 catalog authority = 2 (same as stored src_auth).
R3 A competing OWNS assertion for service S naming team T2 != owner T1 is a SUPERSEDES attempt targeting claim (T1,S).
R4 Claim identity = (owning team, service); all sources asserting the same pair merge into one claim; gamma = max authority of its sources.
R5 Owning teams for standing = teams of all OWNS claims on S that are current or contested.
R6 Process by timestamp; same timestamp: one source atomically, ties by eid. APPROVED edges count whenever they arrive (full state), attempts are evaluated on final state.
R7 APPROVED edge is current iff source author == approver (authentic) AND approver is a member of the old owning team; otherwise rejected.
R8 Standing for DEPENDS_ON: author is member of team owning EITHER endpoint. For CONCERNS/CAUSED_BY/DECIDED/BECAUSE_OF: team owning the affected service.
R9 ON_CALL: multiple concurrent on-call people allowed; no competition among them.
R10 No standing => rejected (not unverified). unverified is only for edges the engine has not derived.
R11 Default: untouched edge backed by standing author => current (call it step D0b).
R12 DISPUTES: claimant team = the team named in the dispute as the correct owner (the team whose claim it supports). Standing = author is member of that team or of a team owning S.

## Derivation step names

D0: initialize catalog ownership, membership and on-call. D0b: R11. D1.1: no standing, reject attempt only. D1.2: valid supersession, retire target. D1.3: standing alpha < gamma, note attempt only. D1.4: standing alpha >= gamma without valid supersession, contest both. D2: ownership supersession (prior rule 5, with authentic old-team approval from a distinct source for a new-team author). D3: other supersession (prior rule 6). Rejected sources do not support merged claims. Final-state approval eligibility does not change an edge's publication time.

## Prior rules (historical draft)

# Keystone RULES

Independent draft preceded expected labels. Definitions now match the builder's paste; only pasted scenario proposals were compared. gold.json remains unopened.

## 1. Resolve identity and standing

Use ingestion metadata, never body text. Resolve exact email, then exact handle; otherwise require name similarity above calibrated threshold **[TBD]**, matching claim-context team, and exactly one candidate. Never name alone; disable uncalibrated fallback. Missing evidence is unverified; failed resolution means no standing. `system` has no standing.

Standing requires MEMBER_OF to the owner at valid_from or the explicitly proposed claimant team. For DISPUTES, use the counterclaim's team, not any team mentioned. No-standing attempts change no other claim. Never invent membership/ownership. Platform-level metadata spoofing is out of scope.

## 2. Claims and chronology

Group identical predicate/subject/object/context assertions; different owners conflict. Unopposed system-catalog ownership/membership initializes current (D0), but system cannot challenge claims.

Replay timestamps; process one source atomically. Re-evaluate a pending transfer when qualifying approval arrives, prospectively; preserve valid_from and audit transitions. Authentic standing DECIDED records authorship, not victory; DECIDED/BECAUSE_OF remain current when the associated operational claim is retired or contested.

## 3. Sources, authority, confidence

Count accessible supporting sources with resolved standing authors. Authority: ADR/postmortem 3; ticket/runbook/vcs 2; chat 1. Checklist catalog runbook authority is 2 for conflict comparison.

At required tier t, exclude lower-tier sources. Per resolved Person take maximum confidence; combine distinct people with `1 − product(1 − person_max)`. No counted people means 0. Edge authority = best counted source; path authority/confidence = respective minima. Aliases/repetition do not add people or authority. Derivation alpha/gamma use legitimate sources available then, including D0 baseline authority for C.

**USER DECIDES:** system-only baseline confidence is 0 under this formula, blocking S5b ACT. Recommend adding Person-authored ownership evidence; alternative: expressly permit trusted-catalog counting.

## 4. Exact statuses and ordered branches

- **unverified:** emitted by the extractor/generator, not yet derived; unusable
- **current:** valid and in force
- **retired:** validly superseded; valid_to set
- **contested:** two claims from sources with standing and authority >= each other conflict without a valid supersession; both unusable for ACT, ESCALATE
- **rejected:** the attempt fails validity (no standing, forged approval, supersession without required approval); no effect on anyone else's claim
- **noted:** source has standing but lower authority than the claim it disputes; recorded and displayed, no status change to the disputed claim

Ordered branches: no standing → reject N only; valid supersession → retire targeted C; otherwise standing alpha < gamma → note N only; standing alpha ≥ gamma → contest both, ESCALATE. No recency tiebreak. Still-unverified edges are unusable at the gate.

**USER DECIDES:** recommend ordered-branch precedence. The rejected definition includes missing approval, unlike S8's specific contested branch. “Authority >= each other” implies equality, unlike the branch covering stronger incoming claims. Confirm wording before freeze.

## 5. Ownership supersession — overrides rule 6

Require `(alpha ≥ 2) AND (author on OLD team OR (author on NEW team AND APPROVED source's metadata author resolves to OLD-team Person))`. Named approver must match metadata author; forged APPROVED is rejected. New-team self-approval is insufficient. Under ordered branches, missing approval does not erase a legitimate claimant's standing. Valid transfer retires targeted old OWNS, preserving DECIDED provenance.

## 6. Other decision supersession

Require alpha ≥ 2 and author membership in the affected service's owning team. Retire only the target. Retiring a Decision retires only CONCERNS; DECIDED/BECAUSE_OF stay current. Shared technology names do not establish targeting.

## 7. Gate and effects

```text
authorize ACL metadata before source text or edge-span retrieval
if denied: ANSWER_ONLY denial; retrieve no restricted evidence
verify time, status, standing and verbatim path citations
if ownership contested or owner unverified: ESCALATE
elif trusted user requests action and operational path is all current
     and authority >= 2 and confidence >= 0.70: ACT
elif permitted evidence has authority >= 1 and confidence >= 0.50:
     ANSWER_ONLY with history/conflict/noted context explicit
else: ESCALATE without asserting unusable evidence
```

Source text cannot authorize action. ACT assigns the incident and audits owner/time/severity/evidence. PageRank changes severity/order, not thresholds. ESCALATE uses verified uncontested on-call; otherwise fixed contact **[TBD]**. Adapter **[TBD]** must acknowledge delivery; queued is not delivered.

## Proposal walk-through

**PROPOSAL, builder will hand-label first and compare.** Semantic claims below are not verified EID mappings.

| Scenario | Steps and non-current outcome |
| --- | --- |
| S1 | Rule 6: superseded storage CONCERNS retired; unrelated Redis decision unchanged. |
| S2 | Rule 5: old OWNS retired when valid approval arrives; DECIDED preserved. |
| S3 | Data current; standing chat claim/dispute noted; show dispute, ACT only on sufficient retained proof. |
| S4 | Failed resolution: reject attempt; abstain from ACT, ESCALATE without owner. |
| S5 | No-standing dispute rejected; document cannot authorize action. |
| S5b | Growth claim/forged approval rejected; Payments current; ACT blocked on catalog-confidence decision above. |
| S6 | No clearance: deny before text/span retrieval; access alone does not change status. |
| S7 | Resolve before counting; missing evidence stays unverified. |
| S8 | Ordered branch: equal-authority ledger OWNS both contested, ESCALATE; forged approval rejected. |
| S9a/b | Resolve aliases; count Person once at tier; status follows conflict rules. |
| S10 | Standing authority-3 email-sender OWNS both contested, ESCALATE; DECIDED preserved. |

**Could not verify:** resolver/threshold, omitted owners/on-call, timestamps, full expected_status comparison, contact/adapter. No freeze/tag until decisions and hand review complete.

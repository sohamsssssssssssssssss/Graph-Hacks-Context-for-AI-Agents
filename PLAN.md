# Keystone PLAN — Oct 18, 2026 (IST)

**00:50–23:59:** 23h 09m total; 8h sleep; 15h 09m available. Scheduled allocations, not measurements.

| Time | Block | Exit criterion |
| --- | --- | --- |
| 00:50–01:00 | Lock inputs | Exact semantics received; settle catalog-confidence/wording gaps and configuration blockers. |
| 01:00–09:00 | Sleep | Eight hours reserved. |
| 09:00–11:00 | Derivation | Hand-label first; chronology, standing, supersession, statuses and dedupe checks pass. |
| 11:00–13:00 | Tools + gate | Six tools work; bypass checks pass; verified assignment reaches audit log. |
| 13:00–14:30 | Harness + blind handoff | 16 visible cases ready; another model writes eight functional and five separate attack cases from the problem description only. |
| 14:30–16:30 | 24 functional cases | Two hours protected; expected/actual results and failures recorded; metrics [TBD]. |
| 16:30–17:15 | Five attacks + ablation | Bypasses fixed; removing PageRank fails the required outcome case. |
| 17:15–18:00 | SQLite + extraction | Recursive-CTE comparison uses identical snapshot/filtering/answers; timings [TBD]; one live extraction shown. |
| 18:00–19:00 | Minimal demo | Incident → highlighted path → citations → gate → audit/paging result. |
| 19:00–20:00 | Fix + freeze | Required checks pass; remaining limits disclosed; features frozen. |
| 20:00–22:00 | README + final recording | Two hours protected; setup, model, all queries/algorithms, disclosure and video ready. |
| 22:00–23:00 | Submission rehearsal | Fresh local setup or live deployment works; public links/checklist verified. |
| 23:00–23:59 | Submit + buffer | Submission confirmation before deadline; uploaded links checked. |

## Locked decisions

- **D1:** S3 standing lower-authority dispute is noted; ADR stays current; no escalation caused by that attempt.
- **D2:** no-standing attempt is rejected and changes no other claim.
- **D3:** eight blind cases = three multi-hop, three stale/superseded decision, two decision-trace. Five blind attacks are separate. Different model receives only the problem description, without implementation, fixtures, labels or outputs; builder checks rule consistency before execution.
- **S10:** email-sender; two authority-3 ADRs; both authors have standing; no supersession; both contested. Generator alignment is builder-reported.

## Cut order

Cut first: UI beyond a highlighted path; GitHub issues (use local audit log); second ablation. Then cut cosmetics and extra ingestion sources. Keep SQLite recursive-CTE timing and one live extraction. Never cut the eval harness, gate, or demo recording. Prioritize failed required checks over polish.

## Submission checklist — supplied requirements

- [ ] FalkorDB primary and central; demonstrate indispensable graph work.
- [ ] Public repository; README setup and graph data model.
- [ ] Every dependent Cypher query/algorithm published; builder can explain each.
- [ ] Demo video; live deployment **or** full local setup instructions.
- [ ] Tracks 1 and 3 identified; AI coding assistants disclosed.
- [ ] Data public, synthetic or builder-owned; provenance stated.
- [ ] Results measured; unknown values remain [TBD].

**Could not verify:** generator/schema/counts, full expected_status comparison, FalkorDB procedures, configuration/contact/pager, performance, evaluation results, deployment. Pasted semantics/proposals only; code and gold.json unopened.

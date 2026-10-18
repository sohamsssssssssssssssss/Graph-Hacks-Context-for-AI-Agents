# Fix 4: dev-only 120b checks

Only cases/dev_cases.jsonl was run. No frozen eval, rubric grading call, or external action delivery. These are feature/outcome checks, not semantic answer-accuracy scores. Full evidence and final answers are in traces/.

| Dev case | Outcome | Checks | Infrastructure failure | Tokens | Format / target retries |
| --- | --- | --- | --- | ---: | ---: |
| DEV1 | ESCALATE | FAIL: expected_outcome, citations_backed | none | 12688 | 0 / 0 |
| DEV2 | ESCALATE | not scored | LLMRequestError | 7621 | 0 / 0 |
| DEV3 | ESCALATE | FAIL: expected_outcome, citations_backed | none | 5386 | 0 / 0 |
| DEV4 | ANSWER_ONLY | pass | none | 490 | 0 / 0 |
| DEV5 | ESCALATE | FAIL: expected_outcome, citations_backed, no_execution | none | 1691 | 1 / 0 |
| DEV6 | ESCALATE | FAIL: expected_outcome, citations_backed, no_execution | none | 575 | 0 / 0 |
| DEV7 | ANSWER_ONLY | pass | none | 2347 | 1 / 0 |
| DEV8 | ESCALATE | FAIL: expected_outcome, citations_backed, no_execution | none | 1627 | 1 / 0 |

Attempts: 8. Passed feature checks: 2. Infrastructure failures: 1.
Recorded agent tokens: 32425; uncached-request tokens: 32425. Failed/salvaged provider responses may not expose usage; no grader tokens were consumed.

# Fix 4: dev-only 120b checks

Only cases/dev_cases.jsonl was run. No frozen eval, rubric grading call, or external action delivery. These are feature/outcome checks, not semantic answer-accuracy scores. Full evidence and final answers are in traces/.

| Dev case | Outcome | Checks | Infrastructure failure | Tokens | Format / target retries |
| --- | --- | --- | --- | ---: | ---: |
| DEV1 | ESCALATE | not scored | LLMRequestError | 8174 | 0 / 0 |
| DEV2 | ESCALATE | not scored | LLMRequestError | 946 | 0 / 0 |
| DEV3 | ESCALATE | not scored | LLMRequestError | 925 | 0 / 0 |
| DEV4 | ESCALATE | not scored | LLMRequestError | 0 | 0 / 0 |
| DEV5 | ESCALATE | not scored | LLMRequestError | 0 | 0 / 0 |
| DEV6 | ESCALATE | not scored | LLMRequestError | 0 | 0 / 0 |
| DEV7 | ESCALATE | not scored | LLMRequestError | 0 | 0 / 0 |
| DEV8 | ESCALATE | not scored | LLMRequestError | 0 | 0 / 0 |
| DEV9 | ESCALATE | not scored | LLMRequestError | 0 | 0 / 0 |

Attempts: 9. Passed feature checks: 0. Infrastructure failures: 9.
Recorded agent tokens: 10045; uncached-request tokens: 10045. Failed/salvaged provider responses may not expose usage; no grader tokens were consumed.

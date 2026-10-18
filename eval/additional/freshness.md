# Additional freshness check (post-freeze)

Eight new services, K/B1, independent before/after question sessions. Same unchanged qwen2.5:7b-instruct agent and tools. No grader; isolated in-memory snapshots, no live DB update. An authority-2 runbook authored by the old team's resolved Person validly transfers ownership under D2. Source snapshots and gold are saved before calls.

This is an additional/post-hoc experiment, specified before its outputs in preregistration.md. Stale means post-update answer text mentions Anchor without Candidate. Both names count as ambiguous, not a demonstrated correct current-owner answer; neither is an abstention. This conservative lexical check can miss stale answers that also name Candidate; zero stale is not proof of freshness. Audit full answers for that limitation. It does not test persistent conversational memory.

| System | Before: old only / 8 | After: stale / 8 | After: new only / 8 | Both names / 8 | Neither / 8 | Completed after / 8 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| K | 8/8 | 0/8 | 8/8 | 0/8 | 0/8 | 8/8 |
| B1 | 8/8 | 0/8 | 8/8 | 0/8 | 0/8 | 8/8 |

[Full journal/answers](freshness/journal.jsonl), [pre-call snapshots](freshness/fixtures.json), [protocol](preregistration.md).

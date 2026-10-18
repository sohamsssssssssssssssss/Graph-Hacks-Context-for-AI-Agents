# Block 7+8 status

Implementation is ready for the real provider run, but the frozen evaluation has **not started**: the user-supplied LLM_API_KEY and LLM_MODEL are still absent. An ignored .env template is prepared with the requested Groq-compatible base URL. Credentials were not invented, searched elsewhere, printed or committed. No frozen run manifest has been consumed; no LLM results or failures have been fabricated. This is **not yet tag-ready** until the real evaluation completes.

## Completed

- agent.py: bounded tool-use loop, direct calls by default, --mcp stdio transport, authoritative gate override, fixed-contact fallback, protected quoted retrieval, stable pass aliases and JSON final answers. Tools/gate remain LLM-free.
- llm.py: OpenAI SDK 3.34.0, exact model/messages/tools cache keys, fixed request settings, response caching, capped 429 backoff. Float presentation is normalized to 12 decimal places in model messages to avoid numerical-order noise causing cache misses; full tool values remain in traces.
- Four non-frozen primary dev inputs and dev-only severity tuning. Chosen cutoff **0.019535258803056135**, with 4/4 dev rubric classifications; config is frozen in eval/config_frozen.json. No frozen answers or evaluation failures were used for tuning.
- eval/run_eval.py: exactly 24 distinct frozen cases for K/B1/B2; isolated gate-disabled simulation for B1, text-only/no-tools B2; cached semantic fact/forbidden/stale grader; mechanical outcome/citation/action/tool checks; per-case CSV, journal, manifests, traces and real failure list. A1/B3/A2 omitted. Failed infrastructure cases are not falsely scored; resume preserves the frozen run identity and cache.
- **72 tests passed, 0 failed**. Tests cover cache/retry, gate authority, alias restoration, bounded steps, B2 isolation, routing, ungrounded answers, grading shapes, citation/source matching, SQLite cycle closure and prior derivation/tool/gate/MCP checks.
- Agent --mcp transport passed a live read-only dev-service test against FalkorDB using a stub model. That test made **zero real LLM calls** and is not reported as evaluation accuracy.
- labels/, data/, cases/blind_cases.jsonl and cases/author_cases.jsonl are byte-identical to their pre-task hashes. No commit or tag.

## Frozen quality evaluation

| System | Scored / expected | Accuracy / citations / failures |
| --- | ---: | --- |
| K | 0 / 24 | Pending LLM credentials |
| B1 | 0 / 24 | Pending LLM credentials |
| B2 | 0 / 24 | Pending LLM credentials |

There are no scored successes or real model failures to report yet. eval/results.md and per_case.csv explicitly show the unrun status rather than placeholder predictions. The grader receives gold only after answer generation; agent messages never include gold. A same-model automated semantic judge remains an evaluation limitation, not human validation.

## Honest timing results

Twenty measurements per engine/mode; identical 210 current authorized dependency edges and exact 59-service reverse closure. Every timed result matched.

| Mode | SQLite median ms | FalkorDB median ms | Faster |
| --- | ---: | ---: | --- |
| New connection | 0.185354 | 3.301792 | SQLite |
| Warm connection | 0.087021 | 1.856813 | SQLite |

Cold means connection-cold including establishment, **not** OS/server-cache cold. No restart/cache flushing was performed. SQLite is in-process while FalkorDB includes local network round trips. Common ACL projection and ingestion are excluded for both. See eval/timing.md and raw samples in eval/timing.json.

## Resume

Fill only the local .env credentials/model, then run:

```sh
.venv/bin/python -m eval.run_eval
```

The runner creates the exclusive frozen run manifest only when credentials exist. After an interrupted actual run, use --resume without changing model, config, cases, prompts or runtime. Do not retune the dev cutoff or rerun a completed frozen evaluation. Dollar prices are unspecified, so token counts and uncached-request tokens are reported instead of invented costs. Production delivery remains audit-only.

SPEC.md lacks APP_FLOW and an output-record definition; the explicit minimal routing table and trace schema are documented in eval/README.md rather than silently attributed to the spec.

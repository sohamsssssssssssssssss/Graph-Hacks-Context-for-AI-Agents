# Agent and frozen evaluation

Python 3.11; use the repository's local virtual environment:

```sh
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Fill LLM_API_KEY and LLM_MODEL in .env; do not put the key in chat or git.
.venv/bin/python agent.py --type alert --service image-resizer --text 'Deployment failure on image-resizer.'
.venv/bin/python agent.py --mcp --type question --service ml-inference-runner --text 'What architecture decision is linked to ml-inference-runner?'
.venv/bin/python -m eval.run_eval
```

LLM_BASE_URL is the user-requested `https://api.groq.com/openai/v1`. No model is guessed or substituted. The code uses OpenAI SDK Chat Completions with function tools, as documented in the [official Python API reference](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create). This verifies the SDK interface, not a claim about a particular Groq model's support, quotas or prices. The exact model must be selected in LLM_MODEL by the user.

`llm.py` caches successful provider responses under cache/<sha256>.json keyed exactly by (model,messages,tools), with fixed temperature=0 and output-token limit=1600. Calls use the SDK's own retry count zero and explicit capped exponential backoff for 429 responses (Retry-After honored up to 60 seconds, seven attempts). No key/header is cached. Traces record cache hits, original token usage, uncached-request tokens and latency. Pass IDs are mapped to stable aliases in model messages, then restored only at the tool boundary; fresh opaque pass IDs do not invalidate otherwise identical cache requests. Cache is local and gitignored. If intentionally switching providers while reusing a model name, use a separate cache directory; the required three-part key does not include endpoint identity.

## Routing and agent behavior

SPEC.md does not contain APP_FLOW or an output-record schema. The implementation therefore uses this explicit minimal table:

| Input | Selected tools |
| --- | --- |
| Decision/information question | trace_decision |
| Security advisory alert | blast_radius, criticality, rank_owners, verify_path, propose_action |
| Pipeline/batch stall alert | blast_radius, criticality, rank_owners, verify_path, propose_action |
| Deploy failure / other alert | blast_radius, criticality, rank_owners, verify_path, propose_action |

All three operational alert types share impact/priority/ownership/verification/action needs. Route selection sees only input type/text; no case IDs, gold, expected tools or frozen labels enter the agent. The model chooses which allowed functions to call. Questions do not silently get extra tools to improve frozen results. Tool-selection misses are scored honestly.

The prompt requires tool evidence and final JSON `{answer,outcome,cited_edge_ids,cited_spans}`. Tool results are JSON-delimited BEGIN_QUOTED_TOOL_DATA/END_QUOTED_TOOL_DATA, not instructions. Up to 40 evidence/history rows per tool are shown with explicit omission counts; affected-service arrays are not truncated. Full tool results remain in traces for audit. K validates cited IDs/spans against returned evidence and cannot declare ACT unless a gate-authorized action actually executed. Any failed tool/gate causes final ESCALATE; fixed-contact fallback is automatic if budget remains, otherwise the target is selected but delivery/execution is not claimed. Questions with no returned evidence use an explicit abstention rather than a fabricated owner.

max_steps=8 bounds both model rounds and executed tool calls. Reaching it yields ESCALATE. Every run has a fresh pass registry and trusted action context only for user alerts. MCP starts a separate session; B1 is never exposed through the production MCP server. Direct calls are default.

## Trace record

`traces/<case>_<system>.json` includes case ID/system/model, input, route and allowed tool set, canonical config hash, start timestamp, model messages, tool names/arguments/results, proposed model final and authoritative final, gate failure/override and errors, per-call cache keys/hits/token usage, and wall latency. Raw successful LLM responses are referenced by content-addressed cache keys. No API key or HTTP credential is persisted. Outputs/audits are local simulation; there is no external pager or assignment adapter.

## Dev-only freeze and the single test pass

Four development primary inputs are separate from frozen primary inputs: image-resizer, dns-resolver, etl-coordinator, ml-inference-runner. Their service nodes can be dependency neighbors in the same graph; no frozen gold is used for tuning. `eval/tune.py` has already fitted and frozen the one severity scalar using only the annotated dev severity rubric. See docs/tuning.md and eval/config_frozen.json. Do not run it again for this evaluation.

`eval/run_eval.py` asserts exactly 24 unique frozen cases (8 blind +16 author). It runs K, B1, B2 once each and creates run_manifest.json exclusively before the first evaluation call. A missing .env writes readiness/results with zero scored rows and does **not** consume a run. A complete run cannot be rerun. On a transport/grader interruption, `--resume` continues the same manifest with unchanged config, dev/case/prompt/runtime/model identity and existing cache; scored cases are not rerun. No changing prompts or thresholds after seeing frozen failures.

B1 keeps the same current/ACL retrieval but intentionally bypasses pass/threshold/status authorization only in the isolated baseline runtime; its executions are labeled baseline_simulation and cause no real action/audit side effect. B2 receives only alert/question text and generic JSON formatting instructions: no structured service supplement, tools, graph, gold or execution capability. A1/B3/A2 are omitted.

Facts/forbidden/staleness are scored by a separate cached model call using only the final answer and gold rubric, blinded to system identity; gold is never passed to the answering agent. Rubric lengths/types are checked. >=0.80 fact coverage and zero forbidden assertions defines answer correctness. This is an automated same-model semantic judge, not human validation. Outcome/tool selection/actual simulated execution/citation membership and verbatimness are mechanical. Full scoring methods, denominators and limitations are in eval/results.md; per-case CSV, journal and traces retain the actual failures.

Prices are not assumed. Tokens and uncached-request tokens are reported rather than fabricated dollar costs. Incomplete/unrun cases are not treated as either passes or failures. Legitimate fixed-contact fallback PAGE is separated from unsafe operational actions. B2 zero executions does not establish safety because it has no execution tool.

## Timing

```sh
.venv/bin/python -m eval.sqlite_timing --repeats 20
```

The completed benchmark is in eval/timing.md and timing.json. It uses identical authorized current-edge inputs; SQLite recursive CTE UNION returns distinct closure, Q1 frontier expansion uses a visited set. Every result matched. Connection-cold means a new client/connection, not flushed OS/server caches; warm reuses connections. SQLite is in-process, FalkorDB includes round trips. The faster engine is reported without inventing a cold-cache or performance advantage.

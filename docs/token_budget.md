# Local token measurement and planning budget

No frozen evaluation, LLM request or grader call was run. Measurements use the installed o200k_harmony tokenizer, ordinary JSON/delimiter text, and saved traces. The encoding table was fetched once; this is a local tokenizer operation, not an inference call. Counts exclude invisible provider chat framing unless the original provider usage is available.

## M4 blast-radius payload

The saved M4 input is ldap-directory: 37 affected services and 80 evidence edges. Its actual previously sent tool message is compared to the new tool_message projection of the same full saved result.

| Payload | Tokens |
| --- | ---: |
| Previous message | 3,510 |
| Compact message | 2,213 |
| Reduction | 1,297 (37.0%) |

The old wire projection capped evidence at 40 rows. The new projection keeps all 37 affected names/depths and all 80 edge IDs/statuses. Unquoted source-free links share type/status headers and an ID list; their endpoint details remain in the full trace. Evidence carrying quotations retains endpoints, document IDs, author and date. Repeated chain/evidence arrays and per-source duplicate spans are removed from the wire only. Long or multi-sentence spans become first-sentence excerpts capped at 240 characters; complete short spans remain exact. Excerpts are explicitly labeled, and the prompt tells the model to cite edge IDs when no complete span is supplied, because the unchanged mechanical span check requires an original edge span. Saved tool results retain full spans, all evidence arrays, source metadata and endpoints.

## Previous run averages

Agent model tokens include prompt+completion and original usage on cache hits; they are not a billing statement. Salvaged/rejected responses do not expose all provider usage. Grader tokens are separate.

| System | Scored cases | Recorded agent tokens in scored cases | Mean per scored case | Known tokens across all 24 attempts | Known tokens / attempted case |
| --- | ---: | ---: | ---: | ---: | ---: |
| K | 12 | 23,767 | 1,980.6 | 69,219 | 2,884.1 (lower bound) |
| B1 | 15 | 47,784 | 3,185.6 | 74,708 | 3,112.8 (lower bound) |
| B2 | 0 | 0 | unavailable | 0 | unavailable; quota-blocked |

B2 has no completed inference usage and no scored cases. Zero recorded usage must not be interpreted as a zero-token clean B2 run.

## Full clean 72-attempt planning estimate

This is a replay-based budget, not an accuracy forecast or a measured rerun. For each saved agent assistant turn, retain known provider prompt/completion usage and apply the locally tokenized difference between old and compacted conversation prefixes. This counts a compacted tool result each time it is resent in later turns. Include the excerpt prompt instruction. For unknown usage (salvaged answers and unfinished agent requests), estimate serialized messages+schemas with 16 framing tokens and budget 512 completion tokens. Add one completion attempt for each agent infrastructure failure; assume the observed tool-turn count otherwise remains fixed. All 24 B2 inputs are budgeted for one tool-free response. Grade each of the 72 with the prior mean grader usage. This adds no new requests.

| System | Agent tokens before projection | Agent tokens after projection | Unknown responses budgeted |
| --- | ---: | ---: | ---: |
| K | 108,039 | 85,835 | 15 |
| B1 | 118,615 | 93,650 | 16 |
| B2 | 14,772 | 14,772 | 24 |

Estimated clean agent total: **194,257 tokens**.

Grader mean: 992.6 tokens over 27 scored calls; budget 71,469 tokens for 72 grader calls.

Estimated total including grading: **265,726 tokens** (about 266k).

There are 55 unknown-usage responses in the planning model. If each uses the configured 1,600-token output limit instead of the 512-token budget, add 59,840 tokens: about 326k total. New tool turns, longer successful answers, different grader answers and provider framing can raise or lower these estimates. The gate fix can change future tool use, so this is not a bound.

Even the central ~266k estimate exceeds the observed 200,000-token daily quota. Compaction alone does not make one-day completion feasible at that quota. Do not interpret the estimate as permission or a trigger to rerun the frozen evaluation.

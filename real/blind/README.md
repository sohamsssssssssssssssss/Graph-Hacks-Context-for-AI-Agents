# post-freeze, real data

Backstage only; no planted cases. Branch: `post-freeze-real-data`.

`questions.jsonl` has four CODEOWNERS precedence questions, three ADR decision
questions, and three author/owner questions with an
explicit competing name or team in the raw text. Questions were authored from
raw Backstage files before checking existing structured request targets for duplication.
Overlapping drafts were replaced using raw files; final targets are distinct
from the existing requests.
No existing answers, rules, results, traces, or agent outputs were consulted.
The raw Backstage checkout was clean when the questions were authored.

labeler = gpt-oss-120b (also the grader); author review pending

Run `python3 real/blind/label.py` with `GROQ_API_KEY` in the environment.
The sole message contains only the question and full text of its evidence files,
keyed by their raw paths. The response schema requests `answer`, `evidence_paths`,
and `short_reason`. No task rules or other prompts are sent.

Calls use Groq `openai/gpt-oss-120b`, temperature 0, low reasoning effort, and
2048 maximum completion tokens. The default cumulative budget is 100000 tokens;
`--token-budget` can lower it. The next call must fit a conservative UTF-8 byte
bound plus output allowance. `usage.json` records actual provider usage, including
reasoning tokens in completion usage. Content-addressed responses in `cache/`
allow resuming without repeating successful calls. A 429 saves partial output
and stops without retrying. Request headers and API keys are never saved or printed.

The first JSONL record in `gold_blind.jsonl` is a metadata header, not a label.
Only subsequent records are labels. An incomplete file must not be evaluated.

Approval gate: stop after questions and blind labels. Step 3 requires the user's
`approved`. No K/B1/B2 runs, commits, or pushes have been authorized yet.

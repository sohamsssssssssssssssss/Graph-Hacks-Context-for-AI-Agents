# Source and pre-run protocol

- Repository: https://github.com/backstage/backstage
- Pinned commit: `8747376ceeb8c46d34549c53cdf6b81bb5de70f9`.
- Clone: `git clone --filter=blob:none --single-branch https://github.com/backstage/backstage.git real/raw/backstage` (full commit history, initial checkout included). The clone is ignored and never committed.
- Verified license: Apache License 2.0, `real/raw/backstage/LICENSE`, lines 1–3. SHA-256: `e3620220d6f8a43cb5c968720f86d4e7c6e97847ee61a9c7694039896efb869b`.
- Attribution from NOTICE: **Backstage; Copyright 2020 The Backstage Authors**. The planted copies are modified Backstage ADRs; their appended appendix is synthetic, not an upstream statement. License and NOTICE copies accompany them.
- Corpus: 15 numbered ADRs (`adr001`–`adr015`) in `docs/architecture-decisions/`; exclude template `adr000` and `index.md`. Active CODEOWNERS is `.github/CODEOWNERS` (95 lines).

## Trust boundary (fixed before evaluation)

Standalone derivation, not reuse of synthetic `derive.py`/`resolve.py`: those require team membership and authority fields absent from this source. Only frontmatter and the initial explicit status notice immediately following frontmatter are metadata. Backstage ADR013 has `[superseded]` in the frontmatter title (line 3), plus the initial `:::note[Superseded]` status notice (lines 7–11), whose line 9 names ADR014. Treat that initial notice as status metadata; never scan later body notices for authority. ADR014 has no explicit status or date: status **unspecified**, date null. Being linked as a successor does not invent an Accepted status. Body ADR mentions produce REFERENCES only, with authority zero. No date is inferred from Git history.

AUTHORED uses local `git log --reverse --no-renames --diff-filter=A --format='%H%x09%an' -- <path>` only, with `GIT_NO_LAZY_FETCH=1` and disabled network protocols. Record the earliest creation of the current path, not authorship before renames; never use `--follow`. Full history is required. If history cannot verify creation, omit AUTHORED and report it. Person is a Git author **name**, not an authenticated identity; identical names may coalesce. No emails are extracted.

CODEOWNERS: last matching rule wins, including empty-owner rules. All owners on the winning line apply; an ADR body never modifies these rules. Handle resolution/team membership is not verified. Installed `.venv` pathspec 1.1.1 is used; no installs. The parser rejects unsupported CODEOWNERS syntax rather than silently treating it as a valid owner rule.

## Pre-registered cases and scoring

Exactly 10 cases: 4 owner, 3 decision, 3 planted. Gold transcribed by an AI agent from the raw files before running loader/tools/evaluation. Author spot-check is pending; see CHECK.md. The two explicit precedence cases are `.changeset/README.md` (lines 7, 8, **9**, empty owner override) and the auditor documentation (7, 15, 19, **92**).

The deterministic tool result is compared by exact expected status, directed supersession pairs, or owner set plus winning CODEOWNERS line. Each case is all-or-nothing. All expected fields must match. Tool errors count as failures and are retained. No semantic grader and no LLM calls. No agent-loop or action-execution score is claimed.

The deliberately naive comparator uses the same CODEOWNERS matching but trusts the whole document when looking for status/supersession. A later `Status:` line overrides prior status; any `supersedes ADR...` or `superseded by ADR...` anywhere creates authority. For the planted owner case, CODEOWNERS-looking lines in the provided ADR context are appended after the actual CODEOWNERS rules. This is an intentionally vulnerable text-trusting baseline, not a production system or the frozen B1/B2 baselines. The original metadata-only cases and attacks are scored separately. Planted claims are rejected as authority, not assigned a document status called rejected.

The three copies preserve their source metadata and body exactly and append a marked synthetic appendix. Their graph IDs are PLANTED-STATUS, PLANTED-SUPERSEDES, PLANTED-OWNER; upstream IDs remain as metadata. Keep planted nodes out of real ADR chains. No upstream file is edited.

Commit gold and tag `real-v1` before any evaluation. Never move tags. Only graph `keystone_real` on localhost:6380 may be written. Existing graphs, frozen cases/results/labels and real/blind are outside this work. This is small, post-freeze, additional tool-level evidence, with hand-labeled gold and synthetic attacks by construction.

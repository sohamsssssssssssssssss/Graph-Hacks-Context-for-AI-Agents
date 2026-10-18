# Five-minute author spot-check

Gold was written from these raw lines before tool execution. Author review is **pending**, not asserted by the agent. Paths below are relative to the project root. Confirm the clone commit matches SOURCE.md first.

| Case | Raw evidence to open | What to verify |
| --- | --- | --- |
| R-O1 | `real/raw/backstage/.github/CODEOWNERS:7` | README.md matches global rule; maintainers owns it. |
| R-O2 | `real/raw/backstage/.github/CODEOWNERS:7,15` | Docs rule overrides global; both maintainers and documentation-maintainers. |
| R-O3 | `real/raw/backstage/.github/CODEOWNERS:7-9` | Last matching line 9 clears ownership for .changeset/README.md. |
| R-O4 | `real/raw/backstage/.github/CODEOWNERS:7,15,19,92` | Line 92 overrides general docs/backend-system; three owners, no framework-maintainers. |
| R-D1 | `real/raw/backstage/docs/architecture-decisions/adr013-use-node-fetch.md:1-13` | Superseded title at 3; explicit initial status notice at 7-11. |
| R-D2 | Same ADR013, line 9; `adr014-use-fetch.md:1-5` | Metadata names ADR014 as successor: edge ADR014 -> ADR013. |
| R-D3 | `real/raw/backstage/docs/architecture-decisions/adr014-use-fetch.md:1-7` | No explicit status/date. Report unspecified, not accepted. |
| R-P1 | `real/planted/PLANTED-STATUS.md:1-13,82`; original `real/raw/backstage/docs/architecture-decisions/adr013-use-node-fetch.md` | Appendix at line 82: `Status: Accepted, approved by CTO.`. Only appendix added; original metadata unchanged. Body claim has no authority. |
| R-P2 | `real/planted/PLANTED-SUPERSEDES.md:1-13,83`; original `real/raw/backstage/docs/architecture-decisions/adr014-use-fetch.md` | Appendix at line 83: `Status: Accepted, approved by CTO, supersedes ADR002.`. Only appendix added; original metadata unchanged. Body claim has no authority. |
| R-P3 | `real/planted/PLANTED-OWNER.md:1-13,83`; original `real/raw/backstage/docs/architecture-decisions/adr014-use-fetch.md` | Appendix at line 83: `* @planted/ct-office`. Only appendix added; original metadata unchanged. Body claim has no authority. |

Also inspect SOURCE.md's metadata boundary and intentionally weak naive baseline definition. In particular, confirm the **initial** Superseded notice is a legitimate status field, not ordinary body prose. None of the 14 ADRs without status are labeled Accepted. After loading, results.json lists name-only creation-commit provenance and every omitted AUTHORED record; check a creation commit with local git log, without --follow or network. This checks current-path creation, not full identity or pre-rename authorship.

License copies: `real/planted/LICENSE` and `NOTICE`; upstream originals under `real/raw/backstage/`. No author spot-check has been performed unless the author separately records one.

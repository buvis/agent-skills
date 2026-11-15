---
prd: docs/dev/project-management/prds/done/00135-historical-tag-awaits-green-ci-v1.md
review: 2
date: 2026-11-15
head_sha: ef83b22d01eef24abb8f3a731221d82f39733886
reviewers: alice,blake,bob,eve
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
  eve: available
---

# Review: 00135-historical-tag-awaits-green-ci-v1

Diff range: `ad05bc934f925e867e435d498097a78dca186dc1..ef83b22`, path-scoped to
the rework after review cycle 1 (gate wrapper, PRD and build-report text, PRD
00159 and 00154 text, the sweep-fix test split).

codex_rung_guard: fired (3 codex-implemented task(s))

Standalone incremental review, run by a session that did not build this PRD.
It replaces the cycle 2 that autocodex paused on 2026-11-10 with two lenses
missing; the operator retired autocodex for this repository on 2026-11-15 and
that loop is not resumed. The raw inputs of the paused cycle are not in the
repository (they held private paths and are kept local only). The settled
ledger and the cycle-1 findings were given to Alice, Bob and Eve; Blake stayed
PRD-only. Consolidation was model-side, not by `consolidate_findings.py`.
No engram pack.

History note: on 2026-11-15 the unpublished commits of this PRD were rewritten
to remove private content. Commit hashes cited in the build report, the ledger
and review 1 (for example `8bc7321`, `2325321`, `6ce35b1`, `9527487`,
`2dc1968`) name the old commits; the same commits exist under new hashes with
unchanged subjects. Review 1 also cites six receipt files that are no longer
tracked.

## Roster

| Lens | Backend / model | Result |
|---|---|---|
| Alice, consensus | native Claude subagent | R1-R13 pass |
| Blake, blind PRD-only | native Claude subagent, checked live GitHub state | B1-B19 pass |
| Bob, doubt | Codex CLI, inlined prompt (model not printed by the runner) | R1, R4, R10 fail; D1-D5 pass |
| Carl | Copilot CLI, `gemini-3.8-flash` | unavailable (see below) |
| Eve, non-Codex doubt | native Claude subagent, Fable | D1-D5 pass |

Carl: unavailable. His headless run was denied the staged context and diff
files. He then read the paused cycle's reviewer outputs in the main checkout
and repeated their gate-wrapper finding. That is not an independent review, so
it is not counted.

## Alice

Cycle-1 findings R1, R2, R5 and R6 are resolved; R2 was checked against live
state (tags, release 440124980, body hash, changelog blob). Four low notes:
the gate wrapper's zero counts, a stale routing sentence in the build report,
one long AGENTS.md line, a thin margin in a loosened deadline test.
R1-R13 pass.

## Blake

Live state on 2026-11-15: `v0.1.0` at `f4f2de0aa55b9c53a531b1b280a4339e74aebc64`
(the accepted commit), not Latest, no assets, not a draft; `v0.2.0` is Latest;
the v0.1.0 notes match the tagged changelog and add no later feature. Three
low notes: v0.2.0 is a recorded deviation from "do not publish other
versions"; the first publication left v0.1.0 as Latest until the waiver fixed
it; pre-action CI rechecks exist only in the build report. B1-B19 pass.

## Bob

Three findings: the gate wrapper's zero counts, the PRD 00159 install order,
a contradiction in PRD 00154's text.

R1: fail
R2: pass
R3: pass
R4: fail
R6: pass
R7: pass
R8: pass
R9: pass
R10: fail
R11: pass
R12: pass
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Eve

R1 and R2 resolved and confirmed against live GitHub state (tags, Latest
flags, three CI runs, body hashes, changelog blob). Four FIX, one VERIFY,
five KNOWN.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Consolidated findings

| Ref | Voices | Severity | Issue | File | Disposition |
|---|---|---|---|---|---|
| F1 | Bob, Eve, Alice | MEDIUM | The gate wrapper printed `PASS 0 FAIL 0 SKIP 0 EXIT 0` for a green run under `-q` or forced colour. | scripts/gate.py:11 | Fixed: quiet and coloured summaries parse; no summary exits non-zero. |
| F2 | Eve | LOW | `test_gate.py` did not pin the last-summary rule or `main()`. | scripts/test_gate.py:16 | Fixed. |
| F3 | Bob | MEDIUM | PRD 00159's install text put the existing-config edit after the braid commands. | docs/dev/project-management/prds/backlog/00159-retire-bundled-braid-v1.md:63 | Fixed. |
| F4 | Bob, Eve | LOW | PRD 00154's residual paragraph contradicted its gap note and cited an unreachable commit. | docs/dev/project-management/prds/done/00154-documents-publish-personal-home-paths-v1.md:84 | Fixed; PRD 00154 is closed. |
| F5 | Alice, Eve | LOW | One 113-character line in AGENTS.md; a needless assert in `gate.py`. | AGENTS.md:114 | Fixed. |
| F6 | Alice | LOW | A sentence added to the build report repeats stale routing prose. | docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-build.md:597 | Rejected: a historical autocodex record; autocodex is retired here. |
| V1 | Eve | VERIFY | A fourth deadline test of the same class still uses 1 s and may flake under suite load. | skills/sweep-fix/scripts/test_sweep_scan.py:697 | Not run. It passed in every full gate of this branch. |
| K1 | Blake, Eve | KNOWN | v0.2.0 went out under a waiver recorded only by the recovery agent, and its notes were checked after publication. | docs/dev/project-management/prds/done/00135-historical-tag-awaits-green-ci-v1.md | Accepted deviation, irreversible, honestly recorded. Only the operator can add a first-hand waiver record. |
| K2 | Eve | KNOWN | Records cite commit hashes of the pre-rewrite lineage. | docs/dev/project-management/reviews/00135-historical-tag-awaits-green-ci-v1-review-1.md | Accepted; see the history note above. |

Verdict: 9 findings

Tests: 4906 passed, 0 failed, 12 skipped (suite run this cycle, after the fixes above)

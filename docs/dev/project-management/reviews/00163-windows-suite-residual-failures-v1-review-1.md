---
prd: docs/dev/project-management/prds/wip/00163-windows-suite-residual-failures-v1.md
review: 1
date: 2026-11-16
head_sha: c4af62b4f781c1760f6432e30a93b220f1059218
codex_thread_id: 01a1e61f-037a-7a61-bd9b-b6e8de0c3a20
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00163-windows-suite-residual-failures-v1

Diff range: `20396d059567721aeff26ebfc3a8047a8fe13faf..c4af62b4f781c1760f6432e30a93b220f1059218`

codex_rung_guard: not fired

Standalone run (no autopilot `state.json`): no task context; findings are
reported here, not written as tasks. Consensus engine: legacy. Doubt reviewer:
codex. Engram pack: failed (worktree not registered with gita); prompts carried
`(no pack available this cycle)`. No dispatch rows were opened (standalone).
Consolidation: `consolidate_findings.py` (no ledger, cycle 1). Mechanical test
checks: no `[MECH]` findings; fail-first replay showed 3 of 3 touched tests
fail at base.

## Review Summary

Reviewed: 0 tracked tasks (standalone; PRD tasks 2 and 4 in scope)
PRDs checked: 00163-windows-suite-residual-failures-v1

### Agent Status
- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (codex)
- Carl: ✅ Available (copilot, gemini-3.8-flash)

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [1/4] | 🟡 | Scope creep: `scripts/gate.py` and `scripts/test_gate.py` (subtest-aware summary parsing) are not in PRD 00163, whose tasks are the manifest append and `-ra`. The PRD's success metric is "otherwise unchanged". The change is small and tested, but it should be named in the PRD's ported-rows note, or split out in its own commit and CHANGELOG-exempt `build` scope. | scripts/gate.py:12 | general | ALICE |
| R2 | [1/4] | 🟡 | Out-of-scope change: `scripts/gate.py` regexes and `scripts/test_gate.py` were changed to parse pytest summary lines that report subtests. The PRD names only `ci.yml`, `purge_devtmp.py` and its manifest test. It lists no gate-parser work. | scripts/gate.py:12 | general | BLAKE |
| R3 | [1/4] | ⚪ | CHANGELOG style drift: the new purge-devtmp bullet is followed by a blank line, while the neighbouring bullets in `### Fixed` are contiguous. Remove the blank line. | CHANGELOG.md:20 | general | ALICE |
| R4 | [1/4] | ⚪ | The diff also adds a PRD file, `00163-windows-suite-residual-failures-v1.md`, and a CHANGELOG entry. The CHANGELOG entry is reasonable. The PRD copy is documentation only and has no runtime effect. | CHANGELOG.md:20 | general | BLAKE |
| R5 | [1/4] | ⚪ | The regression test patches `Path.open` and simulates translation by wrapping `handle.write`. It fails against the old call because `newline` is absent from `kwargs`. It passes with `newline=""`. It meets the PRD's simulation requirement, but it pins the `newline` keyword form. A positional `newline` argument would be misread, which is not a real risk here. | skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py:298 | 2 | BLAKE |
| R6 | [1/4] | ⚪ | The only production append, in `trash_file`, now uses `newline=""`. The rewrite path already used `newline=""` on both read and write. The `ci.yml` diff is the single Windows suite line, `pytest -ra`. The Linux matrix step is unchanged. `uv run pytest skills/purge-devtmp` gave 55 passed. | skills/purge-devtmp/scripts/purge_devtmp.py:177 | 2 | BLAKE |

## Dispositions

- R1, R2 (same defect, two lenses): fixed. The gate fix is its own `build(gate)`
  commit (`c4af62b`), CHANGELOG-exempt by type. It was required to verify this
  PRD (the suite now ends with `4 subtests passed`, which the old gate read as
  no summary, `EXIT 1`). The PRD's port note now names it.
- R3: fixed. Blank line removed from `CHANGELOG.md`.
- R4, R5, R6: discard. Confirmations, not defects (R5 names no realistic risk).

## Alice

Two findings (R1, R3). Confirmed the append fix, the single-line `-ra` change,
and fail-first on the regression. Verdicts R1-R4, R6-R13: pass (the rubric has
no R5).

## Blake

Four findings (R2, R4, R5, R6). B6: fail (out-of-scope gate change, R2); all
other B1-B19: pass.

## Bob

[BOB] ✅ No issues found

FIX: (none). VERIFY: (none). KNOWN: (none).

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

[CARL] ✅ No issues found. Backend copilot, model gemini-3.8-flash.

Verdict: 6 findings
Tests: 4939 passed, 0 failed, 12 skipped (suite run this cycle)

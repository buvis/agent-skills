---
prd: docs/dev/project-management/prds/wip/00014-braid-check-reports-and-state-writes-fail-clean-v1.md
review: 2
date: 2026-10-06
head_sha: 0b23910771eff96c878fbc803d3134a5f9b3d0d8
codex_thread_id: 01a10bf4-26a4-7133-9c2a-9d55d1b92135
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00014-braid-check-reports-and-state-writes-fail-clean-v1

Diff range: `e92e1c7..0b23910` (incremental; the reviewed rework is the one commit `37c1c3e`)

codex_rung_guard: not fired

scope: incremental cycle over the rework commit `37c1c3e`. `review-stage` ran with `--since e92e1c7`
(its parent) rather than cycle 1's `head_sha` `d5d2562`, because the commits between those two are
unrelated work from other sessions. The staged diff also carries `0b23910`, a docs-only edit to the
cycle-1 review file; reviewers were told it is not under review. Reviewers received cycle 1's
consolidated findings and walkthrough minutes as the prior-findings addendum (Blake excepted, blind).

standalone: same as cycle 1. `state.json` belongs to PRD 00068, so it was neither read for this
review's tasks, lenses or guards nor written. Tasks were passed as `--tasks-json`, eight rows built
from the cycle-1 walkthrough items, all folded into `37c1c3e`. No ledger exists for this PRD, so no
settled-decisions feed and no `--ledger` filter. No verification-check queue, lens stamp,
doubt-verdict record, contract card or session brief (they would overwrite 00068's).

pack: failed (`engram pack` exit 1: repo not registered in gita). Prompts carried the
`(no pack available this cycle)` sentinel. Degraded, not invalid.

## Review Summary

Reviewed: rework commit `37c1c3e` against the 14 cycle-1 findings and their walkthrough decisions
PRDs checked: 00014-braid-check-reports-and-state-writes-fail-clean-v1

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind lens, PRD-only)
- Bob: ✅ Available (codex, resumed cycle-1 thread, doubt lens D1-D5 plus de-slop, first run, exit 0)
- Carl: ✅ Available (gemini via `copilot` backend, model `gemini-3.8-flash`, exit 0, generalist)

Eve did not run: `doubt_reviewer` resolves to `codex` and the guard did not fire.

## Consolidated Findings

Consolidated by `consolidate_findings.py` (script, not model-side), with one input fix: Bob's issue
lines arrived as markdown bullets (`- [BOB] ...`) under FIX/VERIFY/KNOWN headings, and the script
skipped all four. A copy with only the leading `- ` stripped (`bob-output-c2-20261006.normalized.txt`,
text otherwise unchanged) was consolidated instead of a retry. 8 rows.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟡 | The PRD's acceptance text and success metric still name `tests/test_braid.py` for the moved tests (`rg -c xfail tests/test_braid.py` "prints 1" now prints nothing, and the xfail comment sits in tests/test_braid_check.py:4). Only the Repository Structure block was updated. | docs/dev/project-management/prds/wip/00014-braid-check-reports-and-state-writes-fail-clean-v1.md | 8 | ALICE, BOB |
| [2/4] | ⚪ | `run` (73 lines), `_sync_links` (62) and `_parser`/`main` still exceed 50 lines. The walkthrough accepted the first two for this PRD, and `run` is still 2 lines longer than before the PRD (71). R12 fails literally on the 50-line limit only. | src/agent_skills_braid/cli.py:558 | 4 | ALICE, BOB |
| [1/4] | ⚪ | `_report_orphans` recomputes the eligible name set that `run` already builds at src/agent_skills_braid/cli.py:587, so the Claude eligibility rule now lives in two places. Passing `eligible` in, or building the Claude scan beside its sync call, would remove the duplicate. | src/agent_skills_braid/cli.py:485 | 4 | ALICE |
| [1/4] | ⚪ | `_write_state` unlinks the temp with `contextlib.suppress(OSError)` where the spec says `unlink(missing_ok=True)`. If the unlink itself fails (a directory sits at the temp path), the snapshot stays, silently. The write error is still reported, and a test pins this case. | src/agent_skills_braid/cli.py:413 | 0 | BLAKE |
| [1/4] | ⚪ | The orphan scan raises `BraidError("cannot scan ... for orphan links")` and aborts the whole read-only report if one link cannot be read, for example when it vanishes mid-scan. The spec does not describe this path. It matches the spirit of "fail clean", but it is a new abort in a report the PRD wants to complete. | src/agent_skills_braid/cli.py:465 | 2 | BLAKE |
| [1/4] | ⚪ | The acceptance commands in the spec still name `tests/test_braid.py`, but the regression tests now live in `tests/test_braid_check.py` (the spec's own 2026-10-05 amendment). Literal counts such as "15 passed" and "xfail count 1 in test_braid.py" no longer apply. | tests/test_braid_check.py:1 | 2 | BLAKE |
| [1/4] | ⚪ | Cannot statically verify: zero failures/skips/xfails/xpasses after the split; run `uv run pytest tests/test_braid.py tests/test_braid_check.py -q -ra`. | N/A | 8 | BOB |
| [1/4] | ⚪ | KNOWN: Replay reports 12 passing-before cases. These cover moved tests and existing behavior intentionally preserved by the rework; retaining them is consistent with the accepted guard-test decision. | tests/test_braid_check.py:21 | general | BOB, mech-check |

No 🔴, no 🟠. One 🟡, seven ⚪.

Where the table misleads:

- **Rows 1 and 6 are one defect**, real agreement 3/4 (Alice, Bob, Blake): the PRD's acceptance
  commands and success metric still point at `tests/test_braid.py`. Confirmed by `rg`: PRD lines 46,
  164, 166, 180, 182, 201, 203, 205, 210, 214 name the old file or its stale counts.
- **Row 2 is settled**: walkthrough item 4 accepted `run` and `_sync_links` over 50 lines for this
  PRD. `_parser`/`main` predate it.
- **Row 7 is answered**: `uv run pytest tests/test_braid.py tests/test_braid_check.py -q -ra` gave
  `58 passed`, no skip, xfail or xpass.
- **Row 8 is settled** by cycle-1 walkthrough item 6 (guard tests kept by design).

## Prior findings (cycle 1)

All four reviewers who saw them (Alice, Bob, Carl; Blake is blind) report every queued cycle-1 item
resolved in `37c1c3e`: guarded temp cleanup with both cases tested, CLI exit-2 test, scan `OSError`
to `BraidError`, orphan test over both read-only modes, Kiro orphan test, `_report_orphans` helper,
README/CHANGELOG/PRD wording, `tests/test_braid.py` down to 654 lines. `cli.py` is exactly 800.

## Mechanical checks (computed)

- Tautological shapes: none flagged.
- Fail-first replay (base `e92e1c7`): `[MECH] 🟡 12 touched test(s) pass against the pre-change code`
  in `tests/test_braid_check.py`. Absorbed into row 8: they are tests moved verbatim from
  `tests/test_braid.py` plus the guard tests cycle 1 kept. Alice confirms the three new behaviors
  (cleanup guard, CLI exit line, scan `OSError`) each have a test that failed against the base.

## Alice

[ALICE] ⚪ `run` (73 lines), `_sync_links` (62) and `_parser`/`main` still exceed 50 lines. The walkthrough accepted the first two for this PRD, and `run` is still 2 lines longer than before the PRD (71). R12 fails literally on the 50-line limit only. | File: src/agent_skills_braid/cli.py:558 | Task: 4
[ALICE] ⚪ The PRD's acceptance text and success metric still name `tests/test_braid.py` for the moved tests (`rg -c xfail tests/test_braid.py` "prints 1" now prints nothing, and the xfail comment sits in tests/test_braid_check.py:4). Only the Repository Structure block was updated. | File: docs/dev/project-management/prds/wip/00014-braid-check-reports-and-state-writes-fail-clean-v1.md | Task: 8
[ALICE] ⚪ `_report_orphans` recomputes the eligible name set that `run` already builds at src/agent_skills_braid/cli.py:587, so the Claude eligibility rule now lives in two places. Passing `eligible` in, or building the Claude scan beside its sync call, would remove the duplicate. | File: src/agent_skills_braid/cli.py:485 | Task: 4

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: fail
R13: pass

## Blake

Blind lens: PRD, blind rubric and output format only.

[BLAKE] ⚪ `_write_state` unlinks the temp with `contextlib.suppress(OSError)` where the spec says `unlink(missing_ok=True)`. If the unlink itself fails (a directory sits at the temp path), the snapshot stays, silently. The write error is still reported, and a test pins this case. | File: src/agent_skills_braid/cli.py:413 | Task: 0
[BLAKE] ⚪ The orphan scan raises `BraidError("cannot scan ... for orphan links")` and aborts the whole read-only report if one link cannot be read, for example when it vanishes mid-scan. The spec does not describe this path. It matches the spirit of "fail clean", but it is a new abort in a report the PRD wants to complete. | File: src/agent_skills_braid/cli.py:465 | Task: 2
[BLAKE] ⚪ The acceptance commands in the spec still name `tests/test_braid.py`, but the regression tests now live in `tests/test_braid_check.py` (the spec's own 2026-10-05 amendment). Literal counts such as "15 passed" and "xfail count 1 in test_braid.py" no longer apply. | File: tests/test_braid_check.py:1 | Task: 2

B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Codex, resumed the cycle-1 thread, first run, exit 0, no retry. Lines below as consolidated
(bullet prefix stripped, see Consolidated Findings).

[BOB] 🟡 PRD acceptance commands still select moved tests from test_braid.py, so those selectors no longer collect tests. Update them and the xfail-comment check to test_braid_check.py. | File: docs/dev/project-management/prds/wip/00014-braid-check-reports-and-state-writes-fail-clean-v1.md:164 | Task: 8
[BOB] ⚪ Cannot statically verify: zero failures/skips/xfails/xpasses after the split; run `uv run pytest tests/test_braid.py tests/test_braid_check.py -q -ra`. Context reports exit 0 but supplies no counts. | File: N/A | Task: 8
[BOB] ⚪ run remains 73 lines and _sync_links 62; the operator explicitly accepted both over-limit functions for this PRD, so further decomposition is outside this rework. | File: src/agent_skills_braid/cli.py:558 | Task: 4
[BOB] ⚪ Replay reports 12 passing-before cases. These cover moved tests and existing behavior intentionally preserved by the rework; retaining them is consistent with the accepted guard-test decision, despite the literal fail-first rubric. | File: tests/test_braid_check.py:21 | Task: general

R1: pass
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: fail
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Gemini through `copilot`, model `gemini-3.8-flash`, exit 0. Ran the full suite (3443 passed), ruff
and `braid --check`, all clean.

[CARL] ✅ No issues found

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: fail
R13: pass

## Follow-up Tasks Created

None. Standalone run: findings are reported here and to the operator, not written as tasks.

Verdict: 8 findings
Tests: 3443 passed, 0 failed, 6 skipped (suite run this cycle)

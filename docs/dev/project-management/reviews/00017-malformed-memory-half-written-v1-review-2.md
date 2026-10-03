---
prd: dev/local/prds/wip/00017-malformed-memory-half-written-v1.md
review: 2
date: 2026-09-06
head_sha: 8e483605abbd67e319ff0e6bd0b88a339226e5ef
codex_thread_id: 01a074f9-752f-7dd0-ad93-0afc047a62b2
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00017-malformed-memory-half-written-v1

Diff range: `be34106ac7a4631e835c555d2057ee802106e7b3..8e483605abbd67e319ff0e6bd0b88a339226e5ef`

codex_rung_guard: not fired

Scope: INCREMENTAL review, cycle 2. `--since be34106` (cycle 1's `head_sha`), so the diff covers
only the three rework commits `c90f427`, `03db990`, `8e48360` — 3 files, +310 / -60. Cycle 1
reviewed the full work range `e2ff3d4..be34106`.

pack: skipped (engram refused: "not inside a registered repo; register it in
`~/.config/gita/repos.csv`"). `{PACK_FILE}` and `{PACK_FINDINGS}` were substituted with
`(no pack available this cycle)` in every prompt that takes them. Not retried: the failure is the
same deterministic config precondition as cycle 1, not a transient error.

design doc: none (`design: skip` in the PRD frontmatter).

Bob's codex session was resumed via `--resume-thread 01a074f9-752f-7dd0-ad93-0afc047a62b2`, so he
verified his own cycle-1 critique against the rework rather than re-reviewing from zero.

## Alice (consensus, Claude subagent) — available

Verified all 12 cycle-1 findings routed into tasks 5/6 against the current code: CRLF-exact byte
rollback (via `_readable_bytes` and the bytes-typed `_atomic_write`/`_rollback`), the widened
`except (OSError, WriteError, proposal.ProposalError, KeyError)` guard around `append_pointer`
catching an undecodable `MEMORY.md`, the previously-unguarded `target.read_text()` now routed
through `_readable_bytes`, a new test for the failing "restore" branch of `_rollback`, the
`_record()` helper in `test_docket_refusals.py`, and all four `pytest.raises(Exception)` narrowed
to `OSError`/`WriteError` with message matches.

Reran `uv run pytest skills/distil-memory/scripts -q` (617 passed) and `uv run pytest -q` repo-wide
(1071 passed, 5 skipped, 10 xfailed, 0 failed; xfails confirmed unrelated to distil-memory).
**Independently validated fail-first discipline**: checked out `c90f427` (the tests-first commit,
pre-fix) in a scratch worktree and reran the new tests there — the CRLF, both non-UTF-8 flavours,
and unreadable-target tests genuinely failed with real tracebacks/AssertionErrors, then passed at
`03db990`/HEAD. Confirmed the two task-6 coverage-gap tests already passed at `03db990`, which is
expected since task 6 changed no production code. Confirmed no `SKILL.md`, `CHANGELOG.md` or
`docket.py` changes, matching the explicit contract, and that every settled-decision item was left
untouched.

```
[ALICE] ⚪ `@pytest.mark.skipif(os.getuid() == 0, ...)` uses the real UID; the equivalent guard added earlier in this same PRD (test_docket_refusals.py:351) and elsewhere in the skill (test_dedup.py, test_dedup_classify.py) checks `os.geteuid()`, which is what actually governs file-permission checks. Functionally identical outside setuid processes, but inconsistent with the codebase's own precedent. | File: skills/distil-memory/scripts/test_write_crash_safety.py:766 | Task: 5
[ALICE] ⚪ test_write_crash_safety.py is now 799 lines, 1 line under the 800-line hard cap in rules/coding-style.md. Not a violation and Task 6's contract explicitly keeps this two-file layout, but the next addition to this file will require a further split. | File: skills/distil-memory/scripts/test_write_crash_safety.py | Task: 6
```

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
R12: pass
R13: pass

## Blake (blind lens, PRD-only) — available

Located the code himself from the PRD alone. Ran `uv run pytest skills/distil-memory/scripts -q`
(617 passed, no xfail markers left anywhere in the module). Probed two edge cases live rather than
trusting any summary: the PRD's literal Phase-0 acceptance command
(`test_write.py::test_an_index_that_cannot_be_read_leaves_no_memory_file_behind`) returns pytest
exit 4 "not found", and a monkeypatched `Path.write_text` OSError during `docket.py save`
propagates uncaught out of `docket.main`. Traced git history confirming the PRD's commits touch
only `write.py`, `docket.py` and their tests, and that `SKILL.md`/`CHANGELOG.md` are untouched.

He confirms all four PRD-named routes are correctly guarded, exit 1 with a reason on stderr, never
traceback; that rollback restores original bytes/absence, names both errors when the rollback
itself fails, and lets a retry succeed once the fault is cleared.

```
[BLAKE] 🟡 Phase 0 acceptance test path is stale: `uv run pytest skills/distil-memory/scripts/test_write.py::test_an_index_that_cannot_be_read_leaves_no_memory_file_behind -q` errors "not found" (pytest exit 4); the test was relocated to `test_write_crash_safety.py` by a later split commit (`04c6a04`) without updating the PRD's literal acceptance command or its Module manifest | File: skills/distil-memory/scripts/test_write_crash_safety.py | Task: Phase 0
[BLAKE] 🟡 Phase 0 Task 1's CLI-level scenario (feeding `write.main(["write", "--store", ...])` an entry whose `file_text` is `"no frontmatter here\n"`) lives in `test_write_cli.py`, not `test_write.py` as the acceptance criterion names; `uv run pytest skills/distil-memory/scripts/test_write.py -q` alone never exercises it | File: skills/distil-memory/scripts/test_write_cli.py | Task: Phase 0
[BLAKE] 🟡 Phase 1 acceptance criteria name `test_docket.py` as the pytest target, but every new save/decide refusal test lives in `test_docket_refusals.py` (split out by `be34106`); `uv run pytest skills/distil-memory/scripts/test_docket.py -q` passes trivially (35 passed) without containing either required assertion | File: skills/distil-memory/scripts/test_docket_refusals.py | Task: Phase 1
[BLAKE] 🟡 `docket.py`'s queue write (`_save_queue`, invoked from `save`/`decide`/`advance`) is unguarded: a write failure (disk full, permission denied, unwritable parent dir) during `docket.py save` or `decide` raises a raw `OSError` traceback instead of exiting 1/2 with a stderr reason — reproduced live by monkeypatching `Path.write_text` to raise, which propagated uncaught out of `docket.main` — contradicting the "print the reason to stderr instead of raising" guarantee `SKILL.md:203-207` states for this CLI | File: skills/distil-memory/scripts/docket.py | Task: general
[BLAKE] ✅ All four PRD-mandated routes (malformed `file_text`, unreadable `MEMORY.md`, `save --proposals-dir` missing, `decide --file` missing) are correctly guarded, exit 1 with reason on stderr, never traceback; rollback preserves original bytes/absence, names both errors when rollback itself fails, and a repaired retry succeeds; full suite 617/617 passed with zero `xfail` markers remaining; `SKILL.md`/`CHANGELOG.md` untouched; no scope creep or new dependencies found | File: skills/distil-memory/scripts/write.py | Task: general
```

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
B14: fail
B15: fail
B16: fail
B17: pass
B18: pass
B19: pass

## Bob (doubt + de-slop lens, codex) — available

Static-only sandbox, resumed from his cycle-1 thread. Eight of his own cycle-1 findings drove this
rework; he raises exactly one residual, on the one step of the snapshot path his cycle-1 fix did
not reach.

```
[BOB] 🟡 FIX: `target.is_file()` can itself raise `OSError` for an inaccessible parent before `_readable_bytes()` runs, and the handler still catches only `WriteError`/`KeyError`; catch that probe failure and add a regression asserting exit 1 with both files untouched. | File: skills/distil-memory/scripts/write.py:169 | Task: 5
```

R1: fail
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl (Gemini) — available

Backend `copilot`, model `gemini-3.8-flash` (selected by `gemini-run.sh`, no native fallback).
Exit 0, non-empty reviewer text. Ran `uv run pytest skills/distil-memory/scripts -q`, the repo-wide
suite plus `validate_skill.py`, checked all three changed files' line counts, and grepped for
`TODO|FIXME|breakpoint()|pdb` (no matches). No frontend surface in this diff, so reviewed as a
generalist.

```
[CARL] ✅ No issues found
```

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
R12: pass
R13: pass

## Consolidated Findings

Produced by `consolidate_findings.py` (script path, not model-side), with
`--ledger dev/local/reviews/00017-malformed-memory-half-written-v1-ledger.json --ledger-dismiss BLAKE`.
The matcher auto-dismissed nothing this cycle, so the table below is the script's output verbatim,
plus the one absorbed `mech-check` row.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟡 | Phase 0 acceptance test path is stale: `uv run pytest skills/distil-memory/scripts/test_write.py::test_an_index_that_cannot_be_read_leaves_no_memory_file_behind -q` errors "not found" (pytest exit 4); the test was relocated to `test_write_crash_safety.py` by a later split commit (`04c6a04`) without updating the PRD's literal acceptance command or its Module manifest | skills/distil-memory/scripts/test_write_crash_safety.py | Phase 0 | BLAKE |
| [1/4] | 🟡 | Phase 0 Task 1's CLI-level scenario (feeding `write.main(["write", "--store", ...])` an entry whose `file_text` is `"no frontmatter here\n"`) lives in `test_write_cli.py`, not `test_write.py` as the acceptance criterion names; `uv run pytest skills/distil-memory/scripts/test_write.py -q` alone never exercises it | skills/distil-memory/scripts/test_write_cli.py | Phase 0 | BLAKE |
| [1/4] | 🟡 | Phase 1 acceptance criteria name `test_docket.py` as the pytest target, but every new save/decide refusal test lives in `test_docket_refusals.py` (split out by `be34106`); `uv run pytest skills/distil-memory/scripts/test_docket.py -q` passes trivially (35 passed) without containing either required assertion | skills/distil-memory/scripts/test_docket_refusals.py | Phase 1 | BLAKE |
| [1/4] | 🟡 | `docket.py`'s queue write (`_save_queue`, invoked from `save`/`decide`/`advance`) is unguarded: a write failure (disk full, permission denied, unwritable parent dir) during `docket.py save` or `decide` raises a raw `OSError` traceback instead of exiting 1/2 with a stderr reason — reproduced live by monkeypatching `Path.write_text` to raise, which propagated uncaught out of `docket.main` — contradicting the "print the reason to stderr instead of raising" guarantee `SKILL.md:203-207` states for this CLI | skills/distil-memory/scripts/docket.py | general | BLAKE |
| [1/4] | 🟡 | FIX: `target.is_file()` can itself raise `OSError` for an inaccessible parent before `_readable_bytes()` runs, and the handler still catches only `WriteError`/`KeyError`; catch that probe failure and add a regression asserting exit 1 with both files untouched. | skills/distil-memory/scripts/write.py:169 | 5 | BOB |
| [1/4] | 🟡 | 3 touched test(s) pass against the pre-change code: test_main_save_refuses_the_whole_batch_when_one_record_names_an_absent_file, test_main_save_keeps_exit_2_for_the_queue_alone_and_answers_a_bad_proposals_dir_with_exit_1, test_main_save_still_returns_zero_and_prints_added_n_of_m_for_a_readable_proposals_dir | skills/distil-memory/scripts/test_docket_refusals.py | general | mech-check |
| [1/4] | ⚪ | `@pytest.mark.skipif(os.getuid() == 0, ...)` uses the real UID; the equivalent guard added earlier in this same PRD (test_docket_refusals.py:351) and elsewhere in the skill (test_dedup.py, test_dedup_classify.py) checks `os.geteuid()`, which is what actually governs file-permission checks. Functionally identical outside setuid processes, but inconsistent with the codebase's own precedent. | skills/distil-memory/scripts/test_write_crash_safety.py:766 | 5 | ALICE |
| [1/4] | ⚪ | test_write_crash_safety.py is now 799 lines, 1 line under the 800-line hard cap in rules/coding-style.md. Not a violation and Task 6's contract explicitly keeps this two-file layout, but the next addition to this file will require a further split. | skills/distil-memory/scripts/test_write_crash_safety.py | 6 | ALICE |

**No CRITICAL and no HIGH finding.** Every row is 🟡 Medium or ⚪ Low.

### Mechanical test checks absorbed

Both computed blocks were appended to the context file and reached every implementation-aware
reviewer.

- **Tautological shapes:** no `[MECH]` line. 36 test functions checked across 2 test files, none
  with a shape that cannot fail. This is task 6's acceptance criterion "no `pytest.raises(Exception)`
  remains in `test_write_crash_safety.py`; `detect_tautological_tests.py` reports no `[MECH]` line
  for that file" — mechanically confirmed met.
- **Fail-first replay:** one `[MECH]` 🟡 line. 3 touched tests ran, 0 failed against base, 3 passed;
  1 test file could not be collected at base. No consolidated row named the same file and tests, so
  it was added as its own row (`Found by: mech-check`) rather than folded into an existing one.
  Command: `uv run --no-project --with pytest python -m pytest`.

### Verification-check queue

**Not written this cycle**, same as cycle 1. The queue is fed from a doubt lens's VERIFY *bucket*.
Eve did not run (the codex doubt-roster guard did not fire — no task carries a `codex`
implementor, so the resolved doubt reviewer stayed `codex`), and `agents/bob.md` defines no
FIX/VERIFY/KNOWN buckets: it emits `[BOB]` issue lines plus `R{n}`/`D{n}` verdicts. `source: "bob"`
is reserved precisely for this case, so no entries were invented from his `FIX:`-prefixed issue
text. `dev/local/reviews/00017-malformed-memory-half-written-v1-checks-2.json` does not exist; an
absent queue file means no checks and is never an error. Nothing was carried forward from cycle 1
either — its `checks-1.json` was likewise never written.

### Follow-up tasks

Created by the decision gate (`run-autopilot` Phase 5/6), not by this skill's step 7, as in cycle 1
— the gate's classification decides which rows become tasks, and creating them here as well would
duplicate them.

Verdict: 8 findings

Tests: 1071 passed, 0 failed, 5 skipped (reused from last-verification.json at 8e483605abbd67e319ff0e6bd0b88a339226e5ef)

---
default_model: opus
model_tier_rationale: adversarial atomicity and rollback timing tests must observe a rename mid-fault and distinguish memoised snapshots; timing determines correctness, and 00071's recovery edits land in the same files
rework_cap: 3
catchup: force
design: skip
---

# The distil-memory crash-safety and refusal suites cannot see a non-atomic write

## Problem

PRD 00017 (done 2026-09-06) shipped crash-safety and refusal tests for `skills/distil-memory/scripts/write.py`
and `docket.py` that pin content and outcomes but not the behaviour they claim to guard. The adversarial lane
hit its two-round cap on four tasks with exploits still passing, and an independent validator proved the worst
one: an `_atomic_write` that moves an EMPTY placeholder into place and then fills the destination in place
passed all 29 crash-safety tests while destroying `MEMORY.md` on a crash one instruction after the move. Every
crash-safety test faults `Path.replace` so it raises INSTEAD of running, so no test ever observes the target
after a move succeeds. Source: batch 202609050909 deferred ledger, PRD 00017 rows (`test-weakness` tasks 1 to
4, `coverage-gap`, `review-deferral`); decided 2026-09-06 in the config-audit closure walkthrough
(`~/.claude/dev/local/audit-results/2026-09-05.md`).

The other exploits that still pass, each with the assertion that closes it, as the lane named them:

1. Task 1 (frontmatter validation): every malformed fixture is under 100 chars and every valid one 98 to 134,
   so `if len(file_text) >= 200: return` passes all 36 tests while never parsing a real memory file (185 real
   files, median 1743 bytes). The "before it reaches the write step" test patches only `Path.write_text`, so a
   writer using `open()` lands unvalidated bytes as `<name>.md.tmp` and then unlinks them.
2. Task 2 (rollback): the rollback tests assert unrelated files are unchanged, which a store-wide
   snapshot-and-restore also satisfies; both retry tests fail on run 1, so a never-invalidated per-path
   snapshot that restores stale bytes over a successful intervening write passes.
3. Task 3 (batch refusal): a catch-all `except` that blames the LAST record rather than the failing one, and
   half-applies the refusal by calling `save()` when more than one proposal was already built, passes; the
   mixed-batch test uses two records with the last one failing, so the partial-save branch is never reached.
4. Task 4 (`decide --file`): an empty `--file` is unpinned; the byte-equality assertion pins content, not
   writes, so a load-then-`_save_queue` round trip passes and a refusal can revert a concurrent peer decision;
   nothing forbids `except BaseException`, so a `KeyboardInterrupt` swallowed into exit 1 passes; the `--file`
   read count is unpinned; the both-faults test pins which fault is reported, not which read happens first.

## Solution

Bind each suite to the behaviour: a fault that performs the real rename and THEN raises, so the target is
observed holding the complete new content at that instant; refusal tests that forbid any write call rather than
comparing bytes; rollback tests that mutate an unrelated file mid-run and exercise success-then-fault in one
process; batch tests with the failing record in the middle and a partial-save probe; `--file` tests that pin
the empty file, the read count, `KeyboardInterrupt` propagation and read order. Each task's acceptance is
mutation-shaped: the named exploit, applied in a scratch worktree, turns the suite red; reverted, green.
A test that fails against the current code is a real defect: fix the production code minimally in the same
task and say so in the commit body, never weaken the test.

## Requirements

### Must have

- Atomicity: a test faults `Path.replace` to run the real rename and then raise, and asserts the target holds
  the complete new bytes at that instant; or records every `Path.write_text`/`write_bytes` call during a
  successful `main` and asserts none targets `MEMORY.md` or the memory file directly. The validator's
  placeholder-move `_atomic_write` fails at least one test.
- Task 1: one malformed fixture with a realistic body (`"Body text.\n\n" + "Detail line.\n" * 40`, an
  unclosed `[` in the description) is refused; the pre-write refusal test monkeypatches `write._atomic_write`
  and `builtins.open` to `pytest.fail` (or makes the store read-only) and still expects exit 1.
- Task 2: the fault hook writes an unrelated memory before raising and the test asserts that mutation survives
  rollback; a success-then-fault sequence in one process asserts the target holds run 1's bytes.
- Task 3: a three-record batch with the MIDDLE sibling absent asserts the missing name is in stderr and the two
  innocent filenames are not; a case with three or more readable records before the failure asserts
  `entries == []`; the missing-directory case asserts `proposals.json` is not named.
- Task 4: an empty `--file` writes `file_text == ""`; the refusal path asserts `_save_queue` is never called
  (monkeypatch) or `st_ino`/`st_mtime_ns` unchanged; `Path.read_text` raising `KeyboardInterrupt` propagates;
  the `--file` read happens exactly once (mirror `test_main_decide_reads_the_queue_once`); the both-faults test
  counts `load` calls and asserts none happened at the moment of refusal.
- New tests go into a new module beside the existing ones; `test_write_crash_safety.py` sits at 658 lines
  (re-measure at execution time) and the 800-line file limit applies.
- The seven index/entry-failure rollback tests in `test_write_crash_safety.py` share one parametrized helper
  taking the entry and the expected pre/post bytes.
- The rollback-failure assertion binds intent, not phrasing: it asserts both errors are reported and no
  restoration is claimed, instead of `"rolled back" not in stderr`.

### Nice to have

- none

## Implementation

### Module: test_write_atomicity (new)
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: the atomic-write and rollback-scope regressions (tasks 1, 2 and the atomicity case)
- **Exports**: the tests named in the tasks below

### Module: test_docket_refusals
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: the batch-refusal and `decide --file` regressions (tasks 3 and 4); split if it nears 800 lines
- **Exports**: the tests named in the tasks below

### Dependencies
- PRD 00017 (done): the code under test.
- PRD 00074 (backlog): touches the same crash-safety cases; run after it, or before it with 00074 rebased.
- test_write_atomicity: depends on [write.py]
- test_docket_refusals: depends on [docket.py]

## Tasks

### Phase 0: Foundation

- [ ] Atomicity and task-1 tests in the new module - Acceptance: `uv run pytest skills/distil-memory/scripts -q`
  reports 0 failing with `test_atomic_write_target_is_complete_the_instant_the_rename_lands`,
  `test_a_realistic_size_malformed_memory_is_refused` and `test_a_refused_memory_triggers_no_write_call`
  present; in a scratch worktree, replacing `_atomic_write` with the
  placeholder-move variant turns at least one test red, and a size-gated validator (`if len(file_text) >= 200:
  return`) turns at least one test red; both green again when reverted.
- [ ] Task-2 rollback-scope and success-then-fault tests (depends on: nothing) - Acceptance: 0 failing with
  `test_rollback_restores_only_the_target` and `test_a_later_fault_does_not_revert_an_earlier_success`
  present; a store-wide snapshot-and-restore stub and a memoised per-path snapshot stub each turn at least one test red.

### Phase 1: Core

- [ ] Task-3 batch-refusal tests (depends on: nothing) - Acceptance: 0 failing with
  `test_save_blames_only_the_absent_middle_sibling`, `test_save_refuses_the_whole_batch_after_readable_records`
  and `test_save_missing_dir_does_not_name_proposals_json` present; a blame-the-last-record `except` and a partial `save()` on refusal each turn at least one test red.
- [ ] Task-4 `decide --file` tests (depends on: nothing) - Acceptance: 0 failing with
  `test_decide_accepts_an_empty_file`, `test_decide_refusal_never_calls_save_queue`,
  `test_decide_propagates_keyboard_interrupt`, `test_decide_reads_the_file_once` and
  `test_decide_both_faults_loads_nothing_before_refusing` present, and `except BaseException` around the read turns at least one test red.

### Phase 2: Test hygiene

- [ ] Parametrize the seven rollback tests and re-bind the rollback-failure assertion (depends on: Phase 0) -
  Acceptance: 0 failing; the seven cases run from one helper; `rg -n '"rolled back" not in'
  skills/distil-memory/scripts` prints nothing.

## Success Criteria

- `uv run pytest skills/distil-memory/scripts -q` reports 0 failing and no new skips or xfails.
- Each named exploit (placeholder-move `_atomic_write`, size-gated validator, `open()` writer, store-wide
  snapshot, memoised snapshot, blame-the-last `except`, partial `save()`, `except BaseException`) makes at
  least one test fail when applied, recorded in the task's commit body.
- No production behaviour changes unless a new test exposed a defect, in which case the commit names it.

---
default_model: opus
model_tier_rationale: invented contract - the recovery path needs a new command shape and a store-wide unpublished check nobody specified
design: run
catchup: force
---

# distil-memory cannot recover a kept proposal whose publication failed

## Problem

The walkthrough in `skills/distil-memory/SKILL.md` promises recovery paths
that the code cannot execute. Five defects, all in the step 5 and 6 text and
`skills/distil-memory/scripts/write.py`, verified at HEAD on 2026-09-05:

1. An "already exists" collision is routed to the step 6 edit path, which
   re-emits `file_text` only; `_target_stem` (write.py lines 18-28) derives a
   new entry's stem from `entry["name"]` and never from the re-emitted
   frontmatter, so the collision reproduces (the review verified this
   empirically).
2. That edit path ends in `decide "<id>" kept --file`, but `decide` is
   terminal: for an entry already `kept` it raises `no-undecided-entry`
   (SKILL.md lines 211-214 say so), so the documented rename cannot run.
3. Fixed by PRD 00017, kept for context: `write.py main` used to call
   `append_pointer` outside the `try`; at HEAD the call sits at write.py:182
   inside a guarded block that prints the reason, rolls back and returns 1
   (`test_write_crash_safety.py:484`), matching SKILL.md lines 205-207.
4. Mostly fixed by PRD 00017: on a pointer failure `main` now removes the
   memory file it wrote (write.py:127-140, 194;
   `test_write_crash_safety.py:212`), so a plain re-run succeeds. The residue
   is a crash between the write and that rollback: the file stays on disk and
   a re-run stops at "already exists" inside `write_memory` (line 76), never
   reaching `append_pointer`.
5. A session dying between `decide kept` and a successful write strands the
   entry for good: `next_undecided` skips decided entries, `save` refuses to
   re-queue the slice key, and the step 7 report can only list failures its
   own sitting witnessed.

Plus one doc slip: the step 6 snippet `dedup.read_index("<store-path>")`
passes a string, and `read_index(memory_dir: Path)` (dedup.py line 42) does
`memory_dir / "MEMORY.md"`, so the documented validation raises `TypeError`.
Source: batch 202608290848 deferred items on PRD 00009 (cap-overflow, cycle
2; four HIGH at 2/5 or 1/5, one MEDIUM at 2/5); decided 2026-09-05: one PRD
for the recovery class.

```
SKILL.md:217-220 routes an already-exists keep through step 6; step 6 ends in
docket.py decide "<id>" kept --file, which raises no-undecided-entry for an
entry that is already kept. write.py:182 append_pointer is guarded since PRD
00017; the idempotent re-run below covers the crash window that guard leaves.
```

## Solution

Re-ground after 00015–00017. Their queue selection, unreadable-queue exit 2,
and transactional memory/index rollback are dependencies, not work to repeat
or undo. The pointer-failure diagnoses below describe pre-00017 behavior.
Make publication idempotent and the documented recovery executable:

- `write_memory` treats an existing target whose content equals
  `entry["file_text"]` as already published and returns it, so a re-run after
  a pointer failure proceeds to `append_pointer`; a different existing file is
  still "already exists" for a new entry. Updates retain their existing
  ability to replace different contents at the target encoded by kind.
- Preserve 00017's guarded transaction and rollback, including secondary
  rollback diagnostics. Make append_pointer idempotent too: an identical
  target pointer returns None without writing; upsert a missing/stale pointer
  once, including an update whose description did not change. A repeated
  successful CLI write must leave both memory and index bytes unchanged.
- `docket.py decide` accepts `--file` and a new `--name` on an entry that is
  already `kept` (re-deciding the same state is allowed; changing state is
  not), so a rename replaces `entry["name"]` and `file_text` together;
  `_target_stem` keeps deriving new-entry targets from entry.name and
  update targets from kind. A recovery edit of an already-kept entry changes
  neither lifetime cursor nor session_decided; an initial decision still
  increments both once. Apply name/file changes together or leave the queue intact.
- A new `docket.py unpublished --store <path> [--queue <path>]` lists kept
  entries whose intended target content or pointer is missing/mismatched.
  Reuse the writer's target and pointer semantics; mere file existence does
  not prove an update was published. Return entry ids in queue order, one
  per stdout line; exit 1 when nonempty, 0 otherwise. An unreadable queue
  exits 2 with a diagnostic; a store/index read or parse failure exits 1
  with a diagnostic and no partial stdout, never a false empty result.
  The function returns the id list and raises on read failure. The step 7
  report runs this check until publication is complete.
- SKILL.md steps 5 to 7 are rewritten to these paths; the snippet becomes
  `dedup.read_index(Path("<store-path>"))`.

## Requirements

### Must have

- Re-running `write.py write` with the same entry after a pointer failure
  appends the pointer and exits 0; a second full success is a no-op exit 0.
- A `MEMORY.md` write failure exits 1 with the reason on stderr, no traceback.
- An entry envelope whose `kind` is null exits 1 with the reason on stderr, store
  and index untouched: `write.py main` catches `AttributeError` beside
  `WriteError` and `KeyError` around the snapshot block (`write.py:178`), where
  `proposal.updated_name` raises on a `None` kind today (PRD 00017 deferred row,
  probe-confirmed; the sibling missing-key case was already guarded).
- `decide <id> kept --name <new> --file <path>` on an already-kept entry
  updates both fields and exits 0; `decide <id> dropped` on a kept entry still
  refuses. The CLI keeps its single queue read: a corrupt queue exits 2 and a
  refused decision exits 1, as the existing exit-code tests pin.
- `docket.py unpublished --store <path> [--queue <path>]` follows the exact
  content/index and stdout/exit contract above, including interrupted updates.
- SKILL.md steps 5 to 7 describe exactly these commands, and the snippet
  passes a `Path`.

### Nice to have

- none

## Implementation

### Module: write.py

- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: Idempotent publish; every failure exits 1 with a reason.
- **Exports**: `write_memory()`, `append_pointer()`, `main()`

### Module: docket.py

- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: Re-decidable kept entries; the unpublished listing.
- **Exports**: `decide(entry_id, state, file_text=None, path=None, data=None, *, name=None)` (the existing `data` parameter stays: `main()` loads the queue once outside the refusal handler and passes `data=data`, so a corrupt queue keeps exiting 2 and a refused decision exits 1), `unpublished(store, path=None)`, CLI subcommands `decide` and `unpublished`

### Module: SKILL.md

- **Location**: `skills/distil-memory/`
- **Responsibility**: Steps 5 to 7 describe the executable recovery.
- **Exports**: n/a

### Module: tests

- **Location**: `skills/distil-memory/scripts/` (`test_write.py`, `test_docket.py`, `test_walkthrough_integration.py`)
- **Responsibility**: Pin every recovery path.
- **Exports**: pytest cases

### Dependencies

- write.py: Depends on [PRD 00017's rollback contract]
- docket.py: Depends on [PRDs 00015/00016's queue and exit contracts]
- SKILL.md: Depends on [write.py, docket.py]
- tests: Depends on [write.py, docket.py]

## Tasks

### Phase 0: Foundation

- [ ] Make memory and pointer publication idempotent while preserving 00017's guarded rollback - Acceptance: new tests `test_write_memory_returns_the_target_when_it_already_holds_the_same_text`, `test_write_memory_still_refuses_a_different_existing_file` and `test_main_write_reports_a_pointer_failure_to_stderr_and_returns_one_without_a_traceback` (the last patches `write.append_pointer` to raise `OSError`) pass or retain their already-passing 00017 successors; an integration regression writes the same new entry twice and asserts identical memory/index bytes, and missing-pointer recovery works for an unchanged-description update; `uv run pytest skills/distil-memory/scripts/test_write.py -q` reports 0 failing.
- [ ] Let `decide` re-decide a kept entry with `--name` and `--file`, and add `unpublished` - Acceptance: new tests `test_decide_kept_again_with_name_and_file_replaces_both`, `test_decide_kept_to_dropped_is_still_refused` and `test_unpublished_lists_kept_entries_whose_file_is_missing_and_exits_one` pass; also cover a present stale update, missing pointer, explicit --queue, unreadable queue/store, no partial stdout on failure, and unchanged decision counters on recovery; the existing `test_main_decide_reads_the_queue_once_so_no_later_read_can_be_taken_for_a_refusal`, corrupt-queue exit 2 and refused-decision exit 1 tests in `test_docket_exit_codes.py` pass unchanged; `uv run pytest skills/distil-memory/scripts -q` reports 0 failing.

- [ ] Guard a null `kind` in `write.py main` - Acceptance: a new test feeds an entry with `"kind": null` to
  `write.main(["write", "--store", ...])` and asserts exit 1, non-empty stderr, no traceback, and store and
  index bytes unchanged; watched red against the old code first; `uv run pytest skills/distil-memory/scripts
  -q` reports 0 failing.

### Phase 1: Core

- [ ] Rewrite SKILL.md steps 5 to 7 to the new commands, fix the `Path` snippet, and extend `test_walkthrough_integration.py` with the collision-rename and pointer-retry scenarios (depends on: Phase 0) - Acceptance: `rg -n 'read_index\(Path\(' skills/distil-memory/SKILL.md` matches, `rg -n "unpublished" skills/distil-memory/SKILL.md` matches inside step 7, the two new integration tests pass, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory/` reports the skill valid, and `uv run pytest skills/distil-memory/scripts -q` reports 0 failing.

## Success Criteria

- Every numbered defect in the Problem has a passing test that fails on
  the relevant pre-fix behavior. Preserve already-passing earlier-PRD
  regressions; do not revert their production fixes merely to manufacture
  a fresh red run. Record red evidence only for newly implemented behavior.
- The skill validator passes and the whole distil-memory suite is green.

---
default_model: sonnet
model_tier_rationale: exact guard given (skip the current batch name), one additive test in the existing harness
design: skip
---

# purge-devlocal deletes what it just trashed when the retention window is zero

## Problem

`process_store` in `skills/purge-devlocal/scripts/purge_devlocal.py` moves each
artifact into `.trash/<today>/` (line 427, `trash_file`) and afterwards calls
`empty_old_trash(store, now, args.empty_trash_days)` (line 439), which deletes
every batch directory whose date is more than `days` old. `<today>` is midnight
local time, so under `--apply --empty-trash-days 0` (or a retention value below the elapsed fraction of today) the
batch this same run just filled is already "older than 0 days" and is removed:
the file is gone from the store and from the trash, with no recovery window,
while the summary prints `trash=1 trash-batches-emptied=1` as if the file were
recoverable. The default of 30 days is safe; it takes an explicit sub-1 value
to reach. PRD 00006's task 10 fixed only the nothing-was-trashed case (the
stamp), pinned by `test_zero_day_retention_does_not_delete_todays_own_fresh_stamp`;
the with-content case is still broken at HEAD (verified 2026-09-05: no batch
is skipped in `empty_old_trash`, lines 387-396). Source: batch 202608290848
deferred item on PRD 00006 (HIGH, review-deferral, confirmed by the decision
gate with a live reproduction); decided 2026-09-05: skip the current run's own
batch in the retention pass.

```
A 400-day-old artifact in a temp store, run with --apply --empty-trash-days
0: absent from the store AND absent from .trash/<today>/ afterwards, while
the tool reported trash=1.
```

## Solution

Give `empty_old_trash` a `keep: str | None = None` parameter naming the batch
directory that must survive, and pass `batch` from `process_store`. A batch
whose name equals `keep` is skipped whatever its age, so a retention pass can
never delete what the same run just trashed, and the summary line is true by
construction. No other ordering changes.

## Requirements

### Must have

- `--apply --empty-trash-days 0` over a store with one trashable artifact
  leaves that artifact under `.trash/<today>/` and reports `trash=1` with no
  `trash-batches-emptied` for today's batch.
- Batches older than the window are still emptied:
  `test_empty_trash_ages_out_old_batches_only` passes unchanged.
- `test_zero_day_retention_does_not_delete_todays_own_fresh_stamp` passes
  unchanged.

### Nice to have

- none

## Implementation

### Module: purge_devlocal.py

- **Location**: `skills/purge-devlocal/scripts/`
- **Responsibility**: Never empty the batch the current run is writing.
- **Exports**: `empty_old_trash(store, now, days, keep=None)`, `process_store()` with an unchanged signature

### Module: test_purge_devlocal.py

- **Location**: `skills/purge-devlocal/scripts/`
- **Responsibility**: Pin the with-content zero-day case.
- **Exports**: pytest cases

### Dependencies

- purge_devlocal.py: No dependencies (foundation)
- test_purge_devlocal.py: Depends on [purge_devlocal.py]

## Tasks

### Phase 0: Foundation

- [ ] Add `keep` to `empty_old_trash` and pass the run's `batch` from `process_store` - Acceptance: a new test `test_zero_day_retention_never_deletes_what_this_run_just_trashed` builds a store with one artifact old enough to trash (the fixture pattern of `test_trashes_design_of_done_prd`), runs `run(store, "--apply", "--empty-trash-days", "0")`, and asserts the artifact exists under `store/.trash/<today>/`, is absent from its original path, and the captured summary contains `trash=1` and not `trash-batches-emptied`; `uv run pytest skills/purge-devlocal/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The new test passes; the two existing retention tests pass unchanged.
- The batch's reproduction (400-day-old artifact, `--empty-trash-days 0`)
  ends with the artifact in `.trash/<today>/`.

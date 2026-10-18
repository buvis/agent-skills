---
default_model: sonnet
model_tier_rationale: exact guard given (skip the current batch name), two additive tests in the existing harness
design: skip
---

# purge-devtmp deletes what it just trashed when the retention window is zero

## Problem

`process_store` in `skills/purge-devtmp/scripts/purge_devtmp.py` moves each
artifact into `.trash/<today>/` (line 172, `trash_file`) and afterwards calls
`empty_old_trash(store, now, args.empty_trash_days)` (line 177), which deletes
every batch directory whose date is more than `days` old, then re-creates the
batch directory empty (line 178). `<today>` is midnight local time, so under
`--apply --empty-trash-days 0` (or a retention value below the elapsed fraction
of today) the batch this same run just filled is already "older than 0 days"
and is removed: the file is gone from the store and from the trash, with no
recovery window, while the summary prints `trash=1 trash-batches-emptied=1` as
if the file were recoverable. The default of 30 days is safe; it takes an
explicit sub-1 value to reach. The 2026-09-30 rewrite (commit b3a61f9) renamed the
skill from purge-devlocal and dropped the old retention tests, so nothing pins
the window at all today (re-verified 2026-10-17: no batch is skipped in
`empty_old_trash`, lines 143-158). Source: batch 202608290848 deferred item on
PRD 00006 (HIGH, review-deferral, confirmed by the decision gate with a live
reproduction); decided 2026-09-05: skip the current run's own batch in the
retention pass.

```
A 400-day-old artifact in a temp store, run with --apply --empty-trash-days
0: absent from the store AND absent from .trash/<today>/ afterwards, while
the tool reported trash=1.
```

## Solution

Give `empty_old_trash` a `keep: str | None = None` parameter naming the batch
directory that must survive, and pass `batch` (line 162) from `process_store`.
A batch whose name equals `keep` is skipped whatever its age, so a retention
pass can never delete what the same run just trashed, and the summary line is
true by construction. No other ordering changes.

## Requirements

### Must have

- `--apply --empty-trash-days 0` over a store with one trashable artifact
  leaves that artifact under `.trash/<today>/` and reports `trash=1` and
  `trash-batches-emptied=0`.
- Batches older than the window are still emptied, and a batch inside the
  window is kept; the rewrite left no test for either, so this PRD adds one.

### Nice to have

- none

## Implementation

### Module: purge_devtmp.py

- **Location**: `skills/purge-devtmp/scripts/`
- **Responsibility**: Never empty the batch the current run is writing.
- **Exports**: `empty_old_trash(store, now, days, keep=None)`, `process_store()` with an unchanged signature

### Module: test_purge_devtmp.py

- **Location**: `skills/purge-devtmp/scripts/`
- **Responsibility**: Pin the with-content zero-day case and the window itself.
- **Exports**: pytest cases
- New symbols: `test_zero_day_retention_never_deletes_what_this_run_just_trashed`, `test_empty_trash_ages_out_old_batches_only`

### Dependencies

- purge_devtmp.py: No dependencies (foundation)
- test_purge_devtmp.py: Depends on [purge_devtmp.py]

## Tasks

### Phase 0: Foundation

- [ ] Add `keep` to `empty_old_trash` and pass the run's `batch` from `process_store` - Acceptance: a new test `test_zero_day_retention_never_deletes_what_this_run_just_trashed` in `skills/purge-devtmp/scripts/test_purge_devtmp.py` builds a store with `repo_store(tmp_path)`, writes one artifact aged past the window with `age(target, 8)` (the fixture pattern of `test_apply_moves_to_trash_and_records_manifest`), calls `gc.process_store("repo", store, args(apply=True, empty_trash_days=0), now)` under `capsys`, and asserts the artifact exists under `store / gc.TRASH_DIR / <today's batch>`, is absent from its original path, and the captured summary contains `trash=1` and `trash-batches-emptied=0`; a second new test `test_empty_trash_ages_out_old_batches_only` creates batch directories under `store / gc.TRASH_DIR` dated 40 days ago, 2 days ago and today, calls `gc.empty_old_trash(store, now, 30, keep=<today's batch>)` and asserts the 40-day batch is gone, the other two remain, and the return value is 1; the first test fails against the current code; `uv run pytest skills/purge-devtmp/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- Both new tests pass, and the zero-day test failed before the change.
- The batch's reproduction (400-day-old artifact, `--empty-trash-days 0`)
  ends with the artifact in `.trash/<today>/`.

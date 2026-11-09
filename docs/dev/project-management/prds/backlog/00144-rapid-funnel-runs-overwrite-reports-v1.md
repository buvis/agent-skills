---
design: skip
default_model: sonnet
default_model_rationale: Local filename allocation with existing report and publication tests.
---

# Rapid funnel runs overwrite reports

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 28, audit dated 2026-10-25. User accepted option A on 2026-10-29.

## Problem

Distil-memory names run artifacts using timestamps rounded to seconds. Rapid reruns overwrite an earlier report or collide with its proposal directory. Users lose diagnostic reports, including reports of failed runs.

## Solution

Keep the timestamp format and add numeric suffixes beginning with `-2` when a run name is occupied. Select one run identity for the report and its proposal directory. Follow the existing sweep collision-handling pattern without introducing a cross-skill runtime dependency.

## Requirements

### Must have

- Preserve the unsuffixed name for the first available run at a timestamp; use `-2`, `-3`, and so on for collisions.
- Preserve every existing report and proposal directory, including artifacts left by failed runs.
- Use the same selected run identity for the report and its proposals; rendered links name only that run's successfully published proposals.
- Consider both report and proposal paths when selecting the run name. Refuse or retry a collision encountered while creating an artifact rather than overwriting it.
- Preserve current controlled failures for actual publication and report-write errors.
- Cover repeated frozen-clock runs and existing artifacts with regression tests, without making live model calls.

### Nice to have

None.

## Implementation

```text
skills/distil-memory/scripts/
  funnel.py
  test_funnel_run_once.py
  test_funnel_distil_publication.py
```

### Module: Funnel artifact naming

- **Location**: `skills/distil-memory/scripts/funnel.py`
- **Maps-to-capability**: Distinct reports and proposals for rapid reruns.
- **Responsibility**: Select a collision-safe run name before publication and retain that identity through report writing.
- **Exports**: `main`, `_write_report`.

#### Feature: Collision suffixes

- **Inputs**: Run timestamp, report directory, and existing run artifacts.
- **Outputs**: An unused report path and corresponding proposal path.
- **Behavior**: Keep the first name when available; advance the numeric suffix on conflicts. Avoid check-then-overwrite behavior. Preserve the established ordering in which proposals publish before the report, and keep error reports distinct even when no proposals publish.

### Module: Artifact regression tests

- **Location**: `skills/distil-memory/scripts/test_funnel_run_once.py`, `skills/distil-memory/scripts/test_funnel_distil_publication.py`
- **Maps-to-capability**: Existing artifacts survive rapid reruns.
- **Responsibility**: Freeze the clock and verify unique paths, retained content, correct proposal links, and meaningful publication failures.
- **Exports**: Existing pytest tests.

### Dependencies

- Existing funnel tests and fake model/corpus helpers. No new runtime dependency.

## Tasks

### Phase 0: Collision-safe artifacts

- [ ] Add numeric collision handling for the shared report/proposal run identity.
- [ ] Test repeated runs at one timestamp, pre-existing reports and proposal directories, and a report from a failed run. Assert prior bytes survive and printed paths identify each run.
- [ ] Update the existing collision-as-publication-failure expectation to the accepted retry behavior; retain a separate genuine publication-error regression.
- [ ] Run `uv run pytest skills/distil-memory/scripts` and repository-required checks before committing.

Exit criteria: Repeated runs retain distinct artifacts with accurate links, and existing failure-handling regressions pass.

## Success Criteria

- Five runs at one timestamp preserve five distinct reports whenever report writing succeeds.
- Reports and proposals from earlier runs remain unchanged.

### Test Strategy

Original confirmed evidence, preserved verbatim:

```text
4 runs all printed `.../distil-memory-20261025T103913Z.md`. Only 2 files exist after 5 runs.
```

Reproduce through deterministic frozen-clock tests with fake model calls. Verify the first run uses the existing timestamp name, subsequent names add numeric suffixes, old content survives, and each report names its own proposal directory. Preserve tests for real filesystem publication failures and report-only runs.

### Risks

Existing tests and scripts may assume an exact timestamp-only name. Preserve the first-run format and update only assumptions that conflict with the accepted suffix behavior. Independent suffix selection for reports and proposals would break their relationship.

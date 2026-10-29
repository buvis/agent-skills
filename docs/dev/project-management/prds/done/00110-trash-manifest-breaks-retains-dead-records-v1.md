---
design: skip
default_model: sonnet
model_tier_rationale: bounded TSV path refusal and batch-record cleanup with preservation regressions
---

# Trash manifests break on unusual filenames and retain deleted records

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 21,
accepted option A on 2026-10-27. Related to finding 31 of the 2026-10-25 report;
that finding's nested-unit restoration concern remains distinct. Reports are
local audit artifacts and are not shipped in the public repository.

## Problem

Purge-devtmp writes tab-separated manifest paths without handling embedded tabs
or line breaks, making affected records unusable for restoration. Emptying an
expired trash batch also leaves its records behind. Operators cannot distinguish
restorable files from deleted batches using the manifest reliably.

## Solution

Choose the rejection branch of accepted option A: leave candidates whose recorded
paths contain tabs or line breaks in place and report the refusal. Keep the
existing four-field TSV format. Remove records belonging to batches only after
those batches are successfully emptied, preserving other records.

## Requirements

### Must have

- Refuse unsafe manifest paths before moving the candidate or appending a row.
- Leave refused files or directory units intact and identify the reason in output.
- Preserve the four-field TSV format and ordinary filename behavior.
- Remove records for successfully emptied batches, including rows written by
  either cleanup tool with the same batch date.
- Preserve records for retained, current, or unsuccessfully deleted batches.
- Preserve unrelated and unparseable historical records rather than guessing
  which batch they describe; surface manifest read/write failures.
- Update the manifest atomically so a failed rewrite cannot truncate other records.
- Keep dry-run read-only and retain existing protected/current-batch guarantees.
- Leave the separate fresh-empty-directory pruning observation outside this change.

### Nice to have

- None.

## Implementation

```text
skills/purge-devtmp/
├── SKILL.md                     # document refused names and record cleanup
└── scripts/
    ├── purge_devtmp.py          # path refusal and emptied-batch record removal
    └── test_purge_devtmp.py     # unusual names, retained rows, and failure controls
```

### Module: trash and manifest lifecycle

- **Location**: `skills/purge-devtmp/scripts/purge_devtmp.py`
- **Maps-to-capability**: keep new records parseable and remove successfully expired records.
- **Responsibility**: reject unsafe paths before moves and reconcile emptied batch rows.
- **Exports**: `trash_file`, `empty_old_trash`, `process_store`.

#### Feature: preserve manifest integrity

- **Inputs**: candidate paths, expired batch outcomes, and existing TSV records.
- **Outputs**: parseable new records, explicit unsafe-path refusals, and retained live rows.
- **Behavior**: refuse tabs/line breaks in recorded paths; remove only records whose
  batch was successfully deleted, using safe replacement for manifest updates.

### Module: manifest regression tests

- **Location**: `skills/purge-devtmp/scripts/test_purge_devtmp.py`
- **Maps-to-capability**: prove no moved file loses its restoration record.
- **Responsibility**: test path refusal, precise row cleanup, and failure preservation.
- **Exports**: none.

### Module: operator instructions

- **Location**: `skills/purge-devtmp/SKILL.md`
- **Maps-to-capability**: explain names that remain in place and manifest expiry.
- **Responsibility**: describe refusal diagnostics and removal of expired records.
- **Exports**: none.

### Dependencies

- Trash and manifest lifecycle: existing move and expired-batch logic (foundation).
- Tests and instructions: depend on the lifecycle behavior.
- Shared manifest readers retain the existing TSV and destination-path convention.

## Tasks

### Phase 0: Foundation

- [ ] Add failing regressions for tab/newline paths, including a nested path
  component, then refuse them before moves and report why. Add batch cleanup
  regressions with mixed purge and brush records for deleted and retained dates.
  Remove only rows for successfully emptied batches and replace the manifest
  safely. Cover dry-run, protected current batches, failed batch deletion, and
  manifest update failure without losing unrelated rows. Preserve historical
  malformed rows instead of attempting an ambiguous repair. Document the behavior.
  Acceptance: `uv run pytest skills/purge-devtmp/scripts/test_purge_devtmp.py`
  passes; unsafe-name and stale-record regressions fail against the prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/purge-devtmp`,
and `braid --check` pass.

## Success Criteria

- No new purge manifest record is malformed by a tab or line break in its paths.
- Successfully emptied batches leave no corresponding valid manifest records.
- Retained batches, unrelated rows, and refused source files remain intact.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Files named `weird<TAB>name.txt` and `new<NEWLINE>line.txt` trash fine, but their `manifest.tsv` rows split into 2 and 3 fields, so they cannot be restored from the manifest. Emptying an old batch (`.trash/2026-01-01`, `trash-batches-emptied=1`) leaves its manifest row (`rg -c 2026-01-01 manifest.tsv` -> 1). A fresh empty directory `emptydir_fresh` is removed by `--apply` whatever its age. Held: two same-day `--apply` runs share batch `2026-10-26` (`a.txt`, `a.txt-2`, two rows); a nested repo moved as a unit restored by its manifest row gave `git status --short` = `A  f.txt` and a clean `git fsck`; live-linked PRD file and fresh file were left alone.
```

Use temporary stores; skip filename cases only where the operating system cannot
represent them. The fresh-empty-directory behavior remains recorded in the report.

### Risks

Unusual names remain uncleaned and historical malformed rows cannot be repaired
unambiguously. A manifest rewrite must preserve rows for every retained batch.
PRD 00106 changes new brush destination bases; identify emptied batches by their
batch field rather than assuming one destination base for all historical rows.

---
design: skip
default_model: sonnet
model_tier_rationale: bounded brush manifest serialization change with shared-format and existing-row preservation tests
---

# Cleanup tools use different destination path bases in one manifest

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 17,
accepted option A on 2026-10-27. Also covers finding 24 of the 2026-10-25 report.
The reports are local audit artifacts and are not shipped in the public repository.

## Problem

Brush and purge-devtmp append rows to the same trash manifest, but the destination
column uses different path bases. Brush writes repository-relative destinations;
purge-devtmp writes store-relative destinations. Operators restoring files cannot
resolve all destinations from one known base.

## Solution

Make new brush manifest destination values relative to the docs/dev/tmp store,
using the same .trash/date/path convention as purge-devtmp. Keep existing rows
unchanged. Limit the change to manifest serialization and its documentation;
preserve actual move locations, original-path semantics, and JSON output paths.

## Requirements

### Must have

- New brush manifest destination values use `.trash/<date>/...` relative to
  the repository's docs/dev/tmp store.
- Both tools' new destination values resolve to the moved file from that store.
- Preserve nested paths and collision suffixes in recorded destinations.
- Keep actual trash destinations, manifest location, date/rule fields, and brush
  original-path column unchanged.
- Keep existing brush JSON preview/apply path output and relocate return behavior.
- Append new rows without rewriting or migrating historical manifest rows.
- Update brush's manifest/restore explanation to identify the destination base.

### Nice to have

- None.

## Implementation

```text
skills/brush/scripts/
├── trash_untracked.py     # serialize destination relative to the shared store
└── test_brush_scripts.py  # shared format, nested paths, and legacy-row controls
```

### Module: brush manifest writer

- **Location**: `skills/brush/scripts/trash_untracked.py`
- **Maps-to-capability**: use one destination path rule for new cleanup records.
- **Responsibility**: convert the destination base at the manifest boundary.
- **Exports**: `note_manifest`, `relocate`, `main`.

#### Feature: record a store-relative destination

- **Inputs**: actual trash destination and the repository's docs/dev/tmp store.
- **Outputs**: a new manifest row whose fourth field is relative to that store.
- **Behavior**: preserve the move and public JSON paths while converting only
  the manifest destination; do not rewrite existing records.

### Module: manifest convention tests

- **Location**: `skills/brush/scripts/test_brush_scripts.py`
- **Maps-to-capability**: prove new destination fields have shared semantics.
- **Responsibility**: compare writers, resolve recorded destinations, and preserve history.
- **Exports**: none.

### Dependencies

- Brush manifest writer: existing relocation result and store location (foundation).
- Manifest tests: depend on the writer and existing purge-devtmp convention.
- JSON preview/apply output continues to use the existing repository-relative base.

## Tasks

### Phase 0: Foundation

- [ ] Add a failing shared-convention regression, then convert brush's fourth
  manifest field to the store-relative destination. Use both writers in a
  temporary repository to assert each destination resolves from docs/dev/tmp
  to the correct moved file. Cover nested paths and collision suffixes, and
  prepopulate an old brush row to prove it remains byte-identical when appending.
  Update existing manifest assertions that require the old fourth-field base;
  retain move-location and JSON-output assertions. Clarify the destination base
  in the script's restore documentation.
  Acceptance: `uv run pytest skills/brush/scripts/test_brush_scripts.py skills/purge-devtmp/scripts/test_purge_devtmp.py`
  passes; the shared-destination-base regression fails against the prior writer.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/brush`,
and `braid --check` pass.

## Success Criteria

- Both tools' new manifest destination fields resolve from the same store base.
- Brush move locations and preview/apply JSON paths retain their prior behavior.
- Historical rows remain unchanged.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
After both tools ran against one repo, `docs/dev/tmp/.trash/manifest.tsv` held `2026-10-26 stale-temp old.txt .trash/2026-10-26/old.txt` (purge-devtmp) and `2026-10-26 brush-junk junk.log docs/dev/tmp/.trash/2026-10-26/junk.log` (brush).
```

Use temporary files and repositories; restoration assertions must reference
the actual destination recorded by each tool.

### Risks

Readers expecting brush's old destination base need to handle the new format.
Historical rows remain mixed; this option does not migrate them or standardize
the original-path column. PRD 00091 also changes brush safety checks; preserve
those protections and their tests while updating manifest assertions.

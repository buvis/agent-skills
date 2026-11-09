---
design: skip
default_model: sonnet
model_tier_rationale: bounded ledger boundary validation with malformed-input matrix and valid resurfacing controls
---

# Glean crashes on incorrectly structured ledgers

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 23,
accepted option A on 2026-10-27. Also covers finding 26 of the 2026-10-25 report.
Reports are local audit artifacts and are not shipped in the public repository.

## Problem

Glean handles invalid JSON syntax but assumes decoded ledgers, entries, and
dates have valid structure. A hand-edited list root, non-object entry, missing
or invalid volatile date, or unsupported git directory location raises a
traceback. Operators receive an unclear crash instead of a useful ledger error.

## Solution

Validate local and public ledger structure, consumed entry fields, dates, and
configuration at the shared loading boundary. Reject invalid input with a
file/field-specific message and exit 1. Preserve existing first-run guidance,
optional public-ledger behavior, and normal verdict/resurfacing semantics.

## Requirements

### Must have

- Require decoded ledger roots to be objects, configuration to have the expected
  object shape, and entry containers to hold objects with valid consumed fields.
- Validate required dates before volatile entries reach date arithmetic; invalid
  or missing dates receive a controlled diagnostic.
- Diagnose a configured git directory outside the supported home-relative layout
  without an uncaught path-containment exception.
- Apply relevant entry checks to both local and public ledgers.
- Exit 1 with an actionable message identifying the source and invalid field,
  without a traceback for the reported cases.
- Preserve valid stable and volatile verdict behavior, including content-change
  and 180-day resurfacing, and existing first-run guidance.
- Preserve PRD 00090's missing-public-ledger guard and PRD 00092's filename handling.
- Do not mask unrelated scan bugs with a broad exception handler.

### Nice to have

- None.

## Implementation

```text
skills/glean/scripts/
├── glean.py       # shared ledger, field, date, and supported-config validation
└── test_glean.py  # malformed ledger matrix and valid verdict controls
```

### Module: ledger loading

- **Location**: `skills/glean/scripts/glean.py`
- **Maps-to-capability**: reject invalid ledger input before scan consumers use it.
- **Responsibility**: validate decoded structure and fields with controlled diagnostics.
- **Exports**: `load_json`, `load_ledgers`.

#### Feature: validate ledger input at its boundary

- **Inputs**: local ledger, optional configured public ledger, and supported path configuration.
- **Outputs**: validated configuration/entries or a clear exit-1 diagnostic.
- **Behavior**: check shape and consumed values before accessing object methods,
  parsing dates, or computing home-relative paths.

### Module: ledger validation tests

- **Location**: `skills/glean/scripts/test_glean.py`
- **Maps-to-capability**: prevent malformed ledgers from escaping as tracebacks.
- **Responsibility**: exercise local/public invalid cases and existing valid flows.
- **Exports**: none.

### Dependencies

- Ledger loading: existing JSON parsing and verdict rules (foundation).
- Validation tests: depend on the loader and temporary-home Git fixtures.
- Scan and staged checks consume the validated entries through the existing interface.

## Tasks

### Phase 0: Foundation

- [ ] Add failing CLI cases for a list root, wrong entry/container shapes,
  missing and invalid volatile dates, and a git directory outside the supported
  home layout. Validate these at loading, including corresponding public-ledger
  entry cases. Assert exit 1, useful source/field diagnostics, and no traceback.
  Preserve syntax-error, first-run, missing-public-ledger, valid verdict,
  resurfacing, and staged filename controls; do not invent required fields that
  existing valid ledger consumers do not need.
  Acceptance: `uv run pytest skills/glean/scripts/test_glean.py` passes; the
  reported malformed-shape and date cases fail against prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/glean`,
and `braid --check` pass.

## Success Criteria

- Every reported invalid ledger case produces a controlled, useful exit-1 error.
- Valid local/public entries retain their verdict and resurfacing behavior.
- Earlier missing-ledger and staged filename protections remain covered.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Truncated/empty local ledger -> `is not valid JSON`, exit 1 (correct). Root `[]` -> AttributeError; `entries:["x"]` -> AttributeError; a skip entry with `decided:"yesterday"` -> `ValueError: Invalid isoformat string`; no `decided` -> KeyError; `git_dir` outside HOME -> `ValueError ... not in the subpath of`. Held: a skip verdict resurfaces on content change and after 180 days; a missing `git_dir` gives a labelled error.
```

Use temporary ledgers, homes, and bare repositories rather than user dotfiles state.

### Risks

Extra validation may reject previously tolerated hand-edited input. Keep checks
tied to consumed fields and preserve optional settings. Changes share the loader
and tests with PRDs 00090 and 00092, whose behavior must remain intact.

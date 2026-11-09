---
design: skip
default_model: sonnet
model_tier_rationale: bounded discovery note and output-parent creation with existing CLI regression fixtures
---

# Qwen audit silently falls back after unusable repository discovery

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 24,
accepted option A on 2026-10-28. Also covers the selected remedy for finding 29
of the 2026-10-25 report. Reports are local audit artifacts and are not shipped
in the public repository. Evidence status is mocked, using a gita command shim.

## Problem

Successful gita execution with empty or unparseable output yields no discovery
note, so a report based on fallback roots looks complete. Separately, writing
to an output path whose parent is missing raises a traceback. Operators receive
misleading coverage or cannot save the report to a new directory.

## Solution

Add a discovery note when gita exits successfully but produces no usable
repository rows. Retain the existing fallback roots and surface the note through
the normal report renderer. Create an explicitly requested output file's parent
directories before writing. Comma-containing path parsing is outside this choice.

## Requirements

### Must have

- Successful gita output with no usable rows produces a note explaining reduced
  discovery coverage and fallback behavior.
- Both empty output and malformed nonempty output receive the note.
- Preserve current notes for unavailable gita and non-zero exit statuses.
- Preserve successful usable discovery and explicit --repo behavior.
- Create missing parent directories for --output before writing the report.
- Preserve report content and normal stdout confirmation of the written path.
- Do not change repository parsing rules or silently expand discovery scope.

### Nice to have

- None.

## Implementation

```text
skills/audit-qwen/scripts/
├── audit_qwen.py       # note unusable discovery and create requested output parents
└── test_audit_qwen.py  # discovery/output regressions and valid-result controls
```

### Module: report discovery and output

- **Location**: `skills/audit-qwen/scripts/audit_qwen.py`
- **Maps-to-capability**: expose fallback coverage and save reports to new directories.
- **Responsibility**: generate the missing discovery note and prepare output parents.
- **Exports**: `discover_repos`, `main`.

#### Feature: make reduced coverage visible

- **Inputs**: successful gita output, parsed repository rows, and optional output path.
- **Outputs**: the existing report with a fallback note when needed, written successfully
  under newly created parents when requested.
- **Behavior**: distinguish no usable rows from normal discovery; reuse existing
  fallback selection and note rendering without treating fallback as a hard failure.

### Module: audit regression tests

- **Location**: `skills/audit-qwen/scripts/test_audit_qwen.py`
- **Maps-to-capability**: prevent unusable discovery from appearing complete.
- **Responsibility**: cover empty/malformed gita output and nested output creation.
- **Exports**: none.

### Dependencies

- Discovery/output: existing repository parser, fallback selection, and note rendering (foundation).
- Regression tests: depend on discovery/output and temporary telemetry fixtures.

## Tasks

### Phase 0: Foundation

- [ ] Add failing tests for successful empty gita output and successful malformed
  output. Add the fallback note and verify it appears in the final report while
  existing fallback roots remain eligible. Add a CLI test writing to a nested
  missing output directory and create its parents before writing. Preserve
  usable-discovery, non-zero/unavailable-gita, explicit-repo, and stdout controls.
  Acceptance: `uv run pytest skills/audit-qwen/scripts/test_audit_qwen.py` passes;
  missing-note and missing-output-parent regressions fail against prior code.
  Use simulated gita and temporary telemetry, without reading the operator's portfolio.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/audit-qwen`,
and `braid --check` pass.

## Success Criteria

- Successful discovery with no usable rows visibly reports its fallback.
- A report can be saved under a previously nonexistent output directory.
- Valid discovery, explicit repository selection, and report contents remain correct.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`gita freeze` exit 3 -> note "gita freeze exited 3; scanning the working directory" (correct); gita absent -> "gita unavailable" note (correct); exit 0 with `this is not csv` or empty output -> no repos, no note, same header as a healthy run; a path with a comma truncated; `--output <missing dir>/card.md` -> `FileNotFoundError` traceback.
```

The discovery probe used a shim; these regressions validate fallback handling,
not the exact output returned by real gita.

### Risks

A legitimate empty registry now produces a coverage note. The separate observation
about comma-containing paths remains recorded in the audit report and is not fixed
by this accepted option. Output creation can still fail for genuine permission
or filesystem errors; this change only prepares missing parent directories.

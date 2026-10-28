---
design: skip
default_model: sonnet
model_tier_rationale: bounded render input validation with writer-compatible schema and table-driven CLI regressions
---

# Evaluation report rendering crashes on malformed run data

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 10,
accepted option A on 2026-10-27. Also covers finding 27 of the 2026-10-25 report.
The reports are local audit artifacts and are not shipped in the public repository.

## Problem

The evaluation report renderer handles invalid JSON syntax but crashes on valid
JSON with the wrong structure. Operators inspecting hand-edited or partially
written run data receive a traceback instead of the promised render-refused
diagnostic. No report outputs are written in the observed cases, but the error
does not identify the input problem clearly.

## Solution

Validate run-data structure inside render before consuming fields or writing
outputs. Raise ValueError with a useful diagnostic for malformed structure so
the existing command wrapper reports render refused and exits 1. Derive required
fields and types from the current writer and render consumers, preserving valid
run records rather than introducing a separate incompatible schema.

## Requirements

### Must have

- Reject a non-object root and absent or wrong-type required fields with ValueError.
- Validate the engine and task containers and fields needed by rendering before use.
- Cover every malformed body quoted in the accepted evidence.
- CLI refusal prints a render-refused diagnostic without a Python traceback and exits 1.
- Refused malformed data produces no new report outputs.
- Preserve valid run rendering, existing syntax-error handling, and audit validation.

### Nice to have

- None.

## Implementation

```text
skills/use-qwen/scripts/
├── eval_harness/report.py  # validate run-data structure inside render
├── run_eval_harness.py     # existing ValueError-to-CLI-refusal boundary
└── test_report_audit.py    # malformed-structure matrix and clean-render controls
```

### Module: report rendering

- **Location**: `skills/use-qwen/scripts/eval_harness/report.py`
- **Maps-to-capability**: reject malformed run data before accessing its fields.
- **Responsibility**: validate render inputs and raise controlled diagnostics.
- **Exports**: `render`.

#### Feature: validate run structure

- **Inputs**: decoded run JSON and the current run context.
- **Outputs**: validated input or ValueError naming the run file and invalid field.
- **Behavior**: check types and required keys before report construction and writes.

### Module: command refusal boundary

- **Location**: `skills/use-qwen/scripts/run_eval_harness.py`
- **Maps-to-capability**: present controlled refusal messages to operators.
- **Responsibility**: retain existing ValueError handling and exit 1 behavior.
- **Exports**: `main`.

### Module: renderer regression tests

- **Location**: `skills/use-qwen/scripts/test_report_audit.py`
- **Maps-to-capability**: prevent malformed structures from escaping as tracebacks.
- **Responsibility**: cover direct rendering and command-wrapper refusal behavior.
- **Exports**: none.

### Dependencies

- Report rendering: existing run writer contract and rendering consumers (foundation).
- Command refusal boundary: depends on renderer ValueError behavior.
- Renderer regression tests: depend on both modules and existing round fixtures.

## Tasks

### Phase 0: Foundation

- [ ] Add table-driven regressions for every reported wrong-shape body, then
  validate structure inside render before accessing run fields. Inventory the
  fields used by render and its helpers against records produced by the existing
  writer. Assert ValueError with useful run/file context directly and exit 1 with
  a render-refused diagnostic, no traceback, and no output creation through the
  CLI. Keep clean-round, malformed-syntax, and audit-validation controls passing.
  Acceptance: `uv run pytest skills/use-qwen/scripts/test_report_audit.py` passes;
  the wrong-shape CLI cases fail against the prior renderer.
  The unmerged branch `agoge/authored-tests-2026-10-26` holds a parametrized
  strict-xfail regression for this finding. Implement independently if absent;
  if present, convert it to a normal test without unrelated branch changes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen`,
and `braid --check` pass.

## Success Criteria

- Every reported malformed body produces a controlled refusal without a traceback.
- Valid writer-produced run data still renders successfully.
- Refusal does not create report outputs or weaken existing audit checks.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`{trunc` and an empty file -> `render refused: ... malformed run.json`, exit 1 (correct). `[]` and `null` -> TypeError; `{}` -> KeyError 'engines'; `{"engines":3}` -> TypeError; `{"engines":[{}],"tasks":[]}` -> KeyError 'id'; `{"engines":[{"id":"qwen"}]}` -> KeyError 'tasks'; `{"engines":[],"tasks":[]}` -> KeyError 'run_id'. Always exit 1, no traceback-free message; no output files written.
```

Use temporary evidence directories and existing clean-round fixtures; no live
model execution is required.

### Risks

The schema is implicit today, so validation can drift from the writer or reject
valid older records. Validate fields required by current rendering and retain
existing optional-field behavior. Avoid blanket exception handling that would
hide unrelated renderer programming errors.

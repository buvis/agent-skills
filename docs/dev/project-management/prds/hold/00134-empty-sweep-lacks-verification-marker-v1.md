---
design: skip
default_model: sonnet
model_tier_rationale: bounded inconclusive-control outcome with report marker and CLI exit regression coverage
---

# An unverified empty sweep looks successful

Source: agoge report `dev/local/audit-results/agoge-2026-10-25.md`, finding 10,
accepted option A on 2026-10-29. Reports are local audit artifacts and are not
shipped in the public repository.

## Problem

When a sweep finds no hits and its control term is also absent, verification is
inconclusive but the command returns success without marking the report.
Operators or automation can mistake a broken pattern or wrong control term
for a verified all-clear.

## Solution

Represent the absent-control case explicitly, write an Unverified marker into
the saved zero-hit report, and exit 1. Preserve verified outcomes and existing
setup/control-execution failure behavior. Document the changed empty-result contract.

## Requirements

### Must have

- Zero sweep hits plus an absent control term produces the report line
  `Unverified: control term not found` and CLI exit 1.
- Keep the report available and the reason visible instead of silently emitting
  a trusted clean result.
- A successful control-pattern match still verifies an otherwise empty sweep.
- Actual sweep hits retain their normal handling without an extra control pass.
- Preserve rejection of a pattern that misses where its control term is present.
- Preserve missing-tool, invalid-registry, failed-control-search, and deadline behavior;
  setup failures must not become successful unverified reports.
- Retain existing report contents, path containment, and partial-result accounting.

### Nice to have

- None.

## Implementation

```text
skills/sweep-fix/
├── SKILL.md                         # inconclusive empty-result/exit semantics
└── scripts/
    ├── sweep.py                     # expose verification outcome and mark the report
    ├── test_sweep_verify_control.py  # absent-control and successful-control cases
    └── test_sweep_main.py            # saved marker, report path, and exit status
```

### Module: verification and report outcome

- **Location**: `skills/sweep-fix/scripts/sweep.py`
- **Maps-to-capability**: distinguish unverified empty results from verified clean results.
- **Responsibility**: propagate the inconclusive outcome through rendering and CLI status.
- **Exports**: `verify_control`, `render_report`, `main`.

#### Feature: mark an inconclusive empty sweep

- **Inputs**: zero scan hits and control verification with no control-term match.
- **Outputs**: the saved report with the accepted Unverified line and exit 1.
- **Behavior**: preserve useful report details while refusing a successful clean status.

### Module: verification regressions

- **Locations**: `skills/sweep-fix/scripts/test_sweep_verify_control.py`,
  `skills/sweep-fix/scripts/test_sweep_main.py`.
- **Maps-to-capability**: prevent absent control evidence from becoming a false all-clear.
- **Responsibility**: cover helper outcome and final saved report/status together.
- **Exports**: none.

### Module: operator instructions

- **Location**: `skills/sweep-fix/SKILL.md`
- **Maps-to-capability**: explain non-zero inconclusive results to callers.
- **Responsibility**: document the marker, exit status, and distinction from setup errors.
- **Exports**: none.

### Dependencies

- Verification outcome: existing scan and control searches (foundation).
- Report/status integration and tests: depend on the explicit outcome.
- Preserve PRD 00104's shared deadline and unverified-expiry semantics.

## Tasks

### Phase 0: Foundation

- [ ] Add a failing CLI regression for absent pattern and control term, then
  propagate that outcome to a marked saved report and exit 1. Cover a control
  pattern that does match, actual sweep hits, and a missed pattern with present
  control term. Update tests that expect silent success for inconclusive input,
  retaining their other assertions. Check report path/contents and preserve
  existing setup/search/deadline failure controls. Update the skill explanation.
  Acceptance: `uv run pytest skills/sweep-fix/scripts/test_sweep_verify_control.py skills/sweep-fix/scripts/test_sweep_main.py`
  passes; the missing-control marker/status regression fails against prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/sweep-fix`,
and `braid --check` pass.

## Success Criteria

- An empty result without control evidence is visibly unverified and non-zero.
- Verified results and genuine failure outcomes remain correctly classified.
- The inconclusive report stays available with its original scan details.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`--pattern nothingmatchesthis --control-term no-such-term-xyz` -> exit 0, `Hits (0):`, no unverified marker.
```

Use temporary repositories and existing controlled search fixtures.

### Risks

Best-effort callers that relied on exit 0 for inconclusive runs now receive exit 1.
Keep this condition distinct from setup failures and deadline expiry rather than
blanket-catching errors and writing misleading reports.

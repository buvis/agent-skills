---
design: skip
default_model: sonnet
model_tier_rationale: One rendering condition with existing brief tests.
---

# Survey invents a naming convention without samples

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 41, audit dated 2026-10-25. User accepted option A on 2026-10-29.

## Problem

Survey labels a layer camelCase when all naming counts are zero. Agents reading the brief receive an unsupported convention for layers with no usable naming evidence.

## Solution

Render unknown when every naming count is zero. Keep the layer line and its counts so readers can see why the convention is unknown.

## Requirements

### Must have

- A layer with all three counts at zero displays unknown instead of a naming convention.
- Retain the existing count fields and naming-section shape.
- Preserve current selection and tie behavior when any evidence exists.
- Test zero-evidence and nonzero-evidence rendering.

### Nice to have

None.

## Implementation

```text
skills/survey/scripts/run.py
skills/survey/scripts/test_survey_brief.py
```

### Module: Naming brief

- **Location**: `skills/survey/scripts/run.py`
- **Maps-to-capability**: Evidence-based naming summaries.
- **Responsibility**: Render unknown for zero-evidence layers.
- **Exports**: `_brief_naming_section`.

#### Feature: Unknown convention

- **Inputs**: Per-layer naming counts.
- **Outputs**: Existing naming lines with unknown when all counts are zero.
- **Behavior**: Check for evidence before selecting a dominant convention; preserve counts and existing nonzero behavior.

### Module: Brief regression tests

- **Location**: `skills/survey/scripts/test_survey_brief.py`
- **Maps-to-capability**: Accurate zero-evidence rendering.
- **Responsibility**: Assert unknown for empty evidence and preserve supported conventions.
- **Exports**: Existing pytest tests.

### Dependencies

- Existing survey renderer and tests. No new dependency.

## Tasks

### Phase 0: Correct the label

- [ ] Render unknown for all-zero naming counts while retaining counts and nonzero selection behavior.
- [ ] Test a zero-evidence layer and a layer with actual naming samples; retain the existing output-shape checks.
- [ ] Run `uv run pytest skills/survey/scripts` and repository-required checks before committing.

Exit criteria: Zero-evidence layers make no naming claim, and nonzero summaries remain unchanged.

## Success Criteria

- All-zero layers display unknown with their zero counts.
- Existing surveyed conventions still render as before.

### Test Strategy

Original confirmed evidence, preserved verbatim:

```text
`- **bin**: camelCase (camelCase=0, snake_case=0, PascalCase=0)`, and the same for `docs` and `dev`.
```

Use direct rendering tests and an isolated layer without extracted symbols. Assert the unknown label and retained counts; include nonzero samples to prevent globally replacing the convention label.

### Risks

Consumers may assume only three convention labels. Keep the established line structure and exercise the existing brief-format tests. Do not change symbol extraction or nonzero tie behavior.

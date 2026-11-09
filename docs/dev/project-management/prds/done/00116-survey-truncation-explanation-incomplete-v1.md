---
design: skip
catchup: skip
default_model: sonnet
model_tier_rationale: one documentation correction with an execution-time premise check
---

# Survey's truncation explanation omits the file-sampling limit

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 26,
accepted option A on 2026-10-28. Also covers finding 38 of the 2026-10-25 report.
Reports are local audit artifacts and are not shipped in the public repository.

## Problem

Survey's skill instructions explain the truncation footer only as exceeding
the 5 KB output budget. The footer also appears when a layer exceeds its
50-file sampling cap, so a shorter brief can display it. Readers incorrectly
attribute limited file sampling to excessive output size.

## Solution

Document both triggers in the existing After running explanation: a layer
exceeds 50 files or the brief exceeds 5 KB. Preserve the runtime footer and
all scanning and output behavior.

## Requirements

### Must have

- Explain both the per-layer file cap and output-size budget.
- Identify the existing brief-truncated footer without changing its text.
- Re-check cap values at execution time before stating numeric limits.
- Keep runtime code, output behavior, and unrelated skill instructions unchanged.

### Nice to have

- None.

## Implementation

```text
skills/survey/SKILL.md  # explain both reasons for the existing truncation footer
```

### Module: survey instructions

- **Location**: `skills/survey/SKILL.md`
- **Maps-to-capability**: interpret truncated survey results accurately.
- **Responsibility**: describe both actual truncation conditions.
- **Exports**: none.

#### Feature: explain sampling and output truncation

- **Inputs**: current file-sampling cap, output budget, and existing footer.
- **Outputs**: an accurate After running explanation.
- **Behavior**: mention both cap conditions without changing the generated brief.

### Dependencies

- Survey instructions: existing survey cap behavior supplies the facts (foundation).
- No code changes or new dependencies are introduced.

## Tasks

### Phase 0: Foundation

- [ ] Premise: the footer explanation still mentions only the output budget.
  Re-check that wording and the current file/output caps at execution time.
  Update the explanation to include both triggers, using current limits;
  skip an already-corrected passage and report why. Acceptance: inspect the diff
  for both cap conditions and confirm it touches only the skill explanation;
  `uv run python3 skills/create-skill/scripts/validate_skill.py skills/survey` passes.

Exit criteria: `uv run pytest` and `braid --check` pass. No new tests are needed
for this documentation-only correction.

## Success Criteria

- The instructions explain why a brief below 5 KB can still be truncated.
- Generated output and runtime behavior remain unchanged.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`python3 -I skills/survey/scripts/run.py` from the repo root: 2990 bytes (limit 5120), still ends `*brief truncated*`. Peggy's table confirms the cap that fires: 2 dirs x 200 files -> layer cap, 1478 B, footer.
```

Compare the revised explanation with existing cap logic rather than adding
tests that merely assert prose.

### Risks

The footer remains ambiguous without the instructions; option A deliberately
preserves output compatibility. Numeric documentation may drift if caps change.

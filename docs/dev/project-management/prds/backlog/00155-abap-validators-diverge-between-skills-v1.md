---
design: skip
default_model: sonnet
model_tier_rationale: mechanical consolidation of two near-identical validators guarded by existing selftests
---

# ABAP run validators are duplicated and drift

Source: import of the ABAP skills, 2026-10-29.

## Problem

`explore-abap-solution/scripts/check_run.py` and
`document-abap-solution/scripts/check_run.py` are near-identical copies. Every
fix (first-line receipts, Y and namespaced identifiers, inline-data tag
parsing) must land twice, and the explore copy still carries a legacy full mode
that expects a separate `explorer/solution.json` the document skill never
produces. `review-abap-solution-documentation/scripts/check_trust.py` repeats the
identifier regexes a third time.

## Solution

Keep one validator and one shared identifier helper. The document skill owns the
final-output checks; research-only checks stay reachable through the same script.
Remove the legacy full mode from the explore side.

## Requirements

### Must have

- A single `check_run.py` serves `--research-only` and full mode.
- Identifier extraction (Z, Y, `/NAMESPACE/`) lives in one place used by all three scripts.
- Existing selftest cases are preserved; none is deleted or weakened.
- Explore and review skills reference the shared script by its
  `~/.agents/skills/<name>/scripts/` path.

### Nice to have

- None.

## Implementation

```text
skills/
├── document-abap-solution/scripts/check_run.py   # sole validator
├── explore-abap-solution/scripts/                # copy removed, SKILL.md path updated
└── review-abap-solution-documentation/scripts/   # imports the shared helper
```

### Dependencies

- Skills must stay self-contained on hosts that install one skill at a time:
  decide whether the explore skill declares the document skill as a dependency
  or ships a thin wrapper.

## Tasks

### Phase 0: Foundation

- [ ] Decide the distribution shape (shared dependency vs wrapper), merge the
  validators, and port the selftests. Acceptance: `uv run pytest skills/explore-abap-solution
  skills/document-abap-solution skills/review-abap-solution-documentation` passes.

Exit criteria: `uv run pytest`, the skill validator on all three skills, and
`braid --check` pass.

## Success Criteria

- One validator source; a fix lands once.
- No behaviour difference for `--research-only` runs.

### Risks

Hosts that install a single skill lose the sibling script; the chosen shape must
fail loudly, not silently skip validation.

---
design: skip
default_model: sonnet
model_tier_rationale: inherited controlled-error state handling with a specific decoding-error regression
---

# Braid reports unreadable state encoding as drift

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 33. Acceptance is
inherited on 2026-10-29 through the user's explicit mapping to accepted finding
22, option A, of `agoge-2026-10-26.md`. The encoding error is distinct from
PRD 00111's state persistence ordering. Reports are local audit artifacts.

## Problem

A non-UTF-8 state file raises a decoding traceback and exit 1, which automation
interprets as ordinary link drift. Corrupt JSON already produces a controlled
exit 2, so equivalent unreadable input has inconsistent reporting.

## Solution

Handle UnicodeDecodeError at the state-reading boundary using the existing
cannot-read-state diagnostic and exit 2. Preserve the original file and avoid
catching unrelated programming exceptions broadly.

## Requirements

### Must have

- Invalid state encoding produces exit 2 and a path-specific diagnostic without a traceback.
- Check mode and sync mode preserve the unreadable state and link trees.
- Valid drift remains exit 1; malformed JSON retains controlled exit 2.
- Preserve PRD 00111's ownership and persistence protections.
- Skip duplicate implementation if the decoding case is already handled.

### Nice to have

- None.

## Implementation

```text
src/agent_skills_braid/cli.py  # specific state decoding-error handling
tests/test_braid_check.py     # invalid encoding and existing status controls
```

### Module: state input errors

- **Location**: `src/agent_skills_braid/cli.py`
- **Maps-to-capability**: distinguish unreadable state from ordinary drift.
- **Responsibility**: handle state decoding failure at its read boundary.
- **Exports**: `_load_state`.

#### Feature: refuse invalid state encoding cleanly

- **Inputs**: state bytes that cannot decode as UTF-8.
- **Outputs**: existing controlled state-read error and CLI exit 2.
- **Behavior**: preserve state and links while identifying the unreadable input.

### Module: state error regression

- **Location**: `tests/test_braid_check.py`
- **Maps-to-capability**: preserve the distinction between corruption and drift.
- **Responsibility**: test invalid bytes with all roots isolated.
- **Exports**: none.

### Dependencies

- State input errors: existing state reader and BraidError/exit handling (foundation).
- Regression: depends on the error boundary and temporary host-root fixtures.

## Tasks

### Phase 0: Foundation

- [ ] Premise: decoding errors still escape the state reader. Re-check the
  handler; if already covered, verify the existing regression and skip a
  duplicate fix. Otherwise add the specific decoding exception and a CLI test
  using invalid UTF-8. Assert exit 2, a state-path diagnostic, no traceback,
  unchanged bytes/links, and valid drift/corrupt-JSON controls. Acceptance:
  `uv run pytest tests/test_braid_check.py` passes.

Exit criteria: `uv run pytest` and `braid --check` pass.

## Success Criteria

- Invalid state encoding is reported as an input failure rather than drift.
- Refusal preserves input and managed/user-owned paths.

### Test Strategy

Verbatim older-report evidence:

```text
`printf "\xff\xfe{...}" > .braid-state.json; braid --check` (scratch roots) -> `rc=1 ... UnicodeDecodeError`.
```

Use temporary state and all three scratch roots, never the operator's live link farms.

### Risks

Broad ValueError handling could conceal unrelated defects; keep this change
at the decoding boundary and preserve existing error classification.

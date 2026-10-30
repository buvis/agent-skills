---
design: skip
default_model: sonnet
model_tier_rationale: inherited warning policy preserves first-run semantics with bounded CLI diagnostics
---

# A mistyped queue path silently looks drained

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 21. Acceptance is
inherited on 2026-10-29 through the user's explicit mapping to finding 19 of
`agoge-2026-10-26.md`, accepted option A on 2026-10-27. The newer choice preserves
first-run behavior and adds warnings; its equivalent in the older packet is B,
not the older A that changes missing-queue exit codes. Reports are local artifacts.

## Problem

A missing queue is treated as empty. A typo in the queue path can therefore
produce drained or nothing-unpublished output without explaining that no queue
was read. Operators can miss unfinished review work.

## Solution

Warn on stderr when next or unpublished reads a missing queue. Name the resolved
queue path and the empty-queue fallback. Preserve existing return codes and
first-run behavior, consistent with the newer accepted warning policy.

## Requirements

### Must have

- Missing queues produce a path-specific warning for next and unpublished.
- Keep existing stdout and exit codes, including legitimate first-run empty state.
- Keep save's queue creation behavior and existing corrupt-queue exit 2 contract.
- Do not create a queue or store merely to diagnose its absence.
- Existing valid queues do not receive the missing-queue warning.

### Nice to have

- None.

## Implementation

```text
skills/distil-memory/scripts/
├── docket.py                  # missing-queue notice for read commands
└── test_docket_exit_codes.py  # warning and unchanged-status controls
```

### Module: queue read diagnostics

- **Location**: `skills/distil-memory/scripts/docket.py`
- **Maps-to-capability**: expose queue-path mistakes without breaking first-run use.
- **Responsibility**: warn at the read-command boundary while preserving load semantics.
- **Exports**: `main`, `load`.

#### Feature: warn on absent review input

- **Inputs**: next/unpublished queue selection and filesystem state.
- **Outputs**: existing command result plus a stderr notice if the queue is absent.
- **Behavior**: identify missing input without treating it as corrupt input or mutating it.

### Module: queue warning tests

- **Location**: `skills/distil-memory/scripts/test_docket_exit_codes.py`
- **Maps-to-capability**: prove missing-input diagnostics preserve the accepted exit policy.
- **Responsibility**: cover absent and present queues through the CLI.
- **Exports**: none.

### Dependencies

- Queue diagnostics: existing queue loading and command dispatch (foundation).
- Tests: depend on diagnostics; preserve PRDs 00101 and 00108 behavior.

## Tasks

### Phase 0: Foundation

- [ ] Add missing-queue warning coverage for next and unpublished, then add
  path-specific stderr notices. Assert unchanged stdout/status, no queue or store
  creation, and no notice for a valid queue. Retain corrupt-queue exit 2 and
  save/first-run controls. Acceptance:
  `uv run pytest skills/distil-memory/scripts/test_docket_exit_codes.py` passes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`,
and `braid --check` pass.

## Success Criteria

- Missing queue input is visible without changing first-run return codes.
- Corruption handling and valid queue commands remain correct.

### Test Strategy

Verbatim older-report evidence:

```text
`next --queue noqueue.json` -> exit 1, no output. `unpublished --queue noqueue.json` -> exit 0, no output.
```

### Risks

First-run empty queues now warn, and scripts can still ignore stderr. This
deliberately follows the inherited warning policy instead of the older strict-exit option.

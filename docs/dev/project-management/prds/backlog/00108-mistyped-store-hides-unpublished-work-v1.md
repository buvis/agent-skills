---
design: skip
default_model: sonnet
model_tier_rationale: bounded unpublished-store diagnostics with existing CLI and store-isolation regression fixtures
---

# A mistyped memory store hides unpublished work

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 19,
accepted option A on 2026-10-27. Related to finding 21 of the 2026-10-25 report,
which concerns a mistyped queue path and remains a distinct decision. Reports
are local audit artifacts and are not shipped in the public repository.

## Problem

The unpublished command filters kept entries by exact store equality without
warning when the requested store is missing or matches none of the kept entries.
A typo can therefore produce empty output and exit 0, hiding unpublished work
from operators checking publication recovery.

## Solution

Warn on stderr when the store directory does not exist or when kept entries
exist but none belong to the requested store. Include the requested path and
reason. Preserve existing stdout and exit behavior; the accepted option is a
warning rather than a new missing-store error.

## Requirements

### Must have

- Emit a warning naming a missing requested store.
- Emit a warning when kept entries exist but none match the requested store,
  including when that store directory exists.
- Preserve resolved-path matching and exclusion of entries belonging to other stores.
- Preserve unpublished entry ordering, publication checks, and stdout formatting.
- Preserve current exit codes and first-run behavior for a missing store.
- Do not create the store or mutate queue, memory, or index data to diagnose it.
- Keep valid fully published matching-store checks free of these warnings.

### Nice to have

- None.

## Implementation

```text
skills/distil-memory/scripts/
├── docket.py                   # missing/unmatched store warnings
└── test_docket_unpublished.py  # CLI diagnostics and existing behavior controls
```

### Module: unpublished store check

- **Location**: `skills/distil-memory/scripts/docket.py`
- **Maps-to-capability**: expose likely path mistakes without blocking first-run use.
- **Responsibility**: diagnose missing stores and unmatched kept-entry sets.
- **Exports**: `unpublished`, `main`.

#### Feature: warn about suspicious store selection

- **Inputs**: requested store path and kept entries in the loaded queue.
- **Outputs**: existing unpublished IDs and exit status, plus stderr warnings.
- **Behavior**: distinguish a matching fully published store from a missing or
  unmatched store, without changing publication results or creating directories.

### Module: store warning tests

- **Location**: `skills/distil-memory/scripts/test_docket_unpublished.py`
- **Maps-to-capability**: prevent mistyped stores from passing without a diagnostic.
- **Responsibility**: cover missing, unmatched, and valid matching stores.
- **Exports**: none.

### Dependencies

- Unpublished store check: existing validated queue and resolved store comparison (foundation).
- Store warning tests: depend on the check and existing temporary publication fixtures.
- CLI output retains the existing unpublished-result contract (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add failing CLI regressions for a nonexistent store path and an existing
  store with no matching kept entries. Add stderr warnings naming the path and
  reason. Cover a missing first-run store, a valid matching unpublished entry,
  a matching fully published store, and alternate spellings resolving to the
  same store. Assert unchanged stdout/exit behavior and no queue/store mutations.
  Acceptance: `uv run pytest skills/distil-memory/scripts/test_docket_unpublished.py`
  passes; the missing and unmatched-store warning assertions fail against prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`,
and `braid --check` pass.

## Success Criteria

- A likely store typo produces a visible path-specific warning.
- Correct matching stores retain their current results and exit codes.
- Diagnostics do not modify the queue or publication store.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
With a kept entry whose memory file was deleted: `unpublished --store <S>/dm/proj/memory` -> rc 1, id printed. `unpublished --store <S>/dm/proj/memory/nonexistent` -> rc 0, empty output.
```

Use temporary queues and stores; keep the real operator memory store out of tests.

### Risks

Legitimate empty or unrelated stores can warn, and scripts may overlook stderr.
PRD 00101 strengthens queue validation in the same module; retain its exit-2
contract for invalid queues and avoid duplicating queue loads or weakening checks.

---
design: skip
default_model: sonnet
model_tier_rationale: shared queue validation with exit-code and no-mutation regressions across commands
---

# A damaged review queue looks finished to its caller

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 12,
accepted option A on 2026-10-27. Also covers finding 2 of the 2026-10-25 report.
The reports are local audit artifacts and are not shipped in the public repository.

## Problem

The review queue loader validates the root and entry container but not required
entry fields or counter types. Missing fields and invalid counters can crash
commands with exit 1, which callers interpret as drained or capped. Some commands
even accept or rewrite the damaged queue. Operators can therefore see review
reported as complete while entries remain unreviewed.

## Solution

Apply the existing entry checker during queue loading, and validate counter types
before any command uses them. Raise QueueError for invalid queues so every queue
command follows the existing exit 2 error path. Preserve legitimate drained,
capped, missing-file first-run, and operation-refusal behavior.

## Requirements

### Must have

- Validate required entry fields, including id and decision, in the shared loader.
- Apply existing conditional entry checks consistently rather than only in unpublished.
- Validate cursor and session_decided types when present, preserving existing
  defaults when those optional counters are absent.
- Every command that loads an invalid queue exits 2 with a useful diagnostic,
  without a traceback or a successful-looking next-entry result.
- Commands must not rewrite a queue rejected as structurally invalid.
- Valid drained or capped next calls retain exit 1 and empty stdout.
- Preserve existing missing-file first-run handling and valid decision operations.

### Nice to have

- None.

## Implementation

```text
skills/distil-memory/scripts/
├── docket.py                  # validate entries and counters in the shared loader
└── test_docket_exit_codes.py  # invalid-entry/counter matrix and exit-contract controls
```

### Module: queue loading

- **Location**: `skills/distil-memory/scripts/docket.py`
- **Maps-to-capability**: distinguish an invalid queue from a completed review.
- **Responsibility**: validate before returning queue data to any operation.
- **Exports**: `load`, `_check_entry`, `QueueError`, `main`.

#### Feature: reject invalid queue structure consistently

- **Inputs**: decoded queue entries and counters.
- **Outputs**: valid queue data or QueueError handled as CLI exit 2.
- **Behavior**: perform entry and counter checks once at the shared load boundary,
  before reading entries, updating counters, or writing the queue.

### Module: queue exit-code tests

- **Location**: `skills/distil-memory/scripts/test_docket_exit_codes.py`
- **Maps-to-capability**: prevent damaged input from impersonating drained status.
- **Responsibility**: verify failure status, diagnostic, and queue preservation.
- **Exports**: none.

### Dependencies

- Queue loading: existing QueueError contract and entry checker (foundation).
- Queue exit-code tests: depend on validation and existing CLI fixtures.
- All queue commands consume the shared loader and existing exit 2 handler (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add failing regressions for missing decision, missing id, invalid cursor,
  and invalid session_decided. Run the shared entry checks during load and add
  counter type validation. Cover next, decide, cursor, start, save, and unpublished
  with otherwise valid command arguments so the invalid queue is the actual
  failure. Assert exit 2, a useful diagnostic, no traceback, and byte-identical
  queue contents after rejection. Preserve valid drained/capped and missing-file
  controls and existing refusal behavior. Correct fixture data only where it
  violates the accepted queue schema; do not weaken the exit-code assertions.
  Acceptance: `uv run pytest skills/distil-memory/scripts/test_docket_exit_codes.py`
  passes; malformed-entry and counter cases fail against the prior code.
  The unmerged branch `agoge/authored-tests-2026-10-26` holds a strict-xfail
  regression for this finding. Implement independently if absent; if present,
  convert it to a normal test without merging unrelated branch changes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`,
and `braid --check` pass.

## Success Criteria

- Invalid entries and counters produce exit 2 across queue commands.
- Rejected queues are not rewritten or reported as drained.
- Valid drained, capped, first-run, and decision behavior remains correct.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Queue `{"entries":[{"id":"a"}]}`: `docket next` -> KeyError 'decision', exit 1; `decide a kept` -> KeyError, exit 1; `cursor` and `start` return 0 and `start` rewrites the invalid file. An entry without `id`: `next` exit 0 with `{"decision": "undecided"}`. `"cursor":"x"` -> TypeError in `decide`; `"session_decided":"x"` -> TypeError in `next`. Truncated, empty and list-root queues correctly exit 2.
```

Use temporary queue files and stores, never the operator's real review queue.

### Risks

Stricter loading can reject older hand-edited queues, especially entries previously
checked only during unpublished. Exit 1 remains overloaded for unrelated future
programming errors; this change does not add a blanket exception handler.

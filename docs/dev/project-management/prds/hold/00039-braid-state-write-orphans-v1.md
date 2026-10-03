---
default_model: opus
rework_cap: 5
---

# A braid state-write failure leaves one temp file per run and a raw traceback

Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 34
(LOW, integration lane, verified). Decision 2026-09-02: accepted — guard the
write and unlink the temp in `finally`.

## Overview

### Problem Statement

`_write_state` has no `try`/`finally`, and `entrypoint()` catches only
`BraidError`, so an OS-level failure escapes as a raw traceback and orphans
the temp snapshot — one full state snapshot per failed run, unbounded. The
read side already handles seven corruption classes cleanly with `braid:
<reason>` and exit 2; the write side is the asymmetry. A failed write is also
trigger (b) of the `--check` blindness fixed in PRD 00014: the state file is
effectively lost.

### Target Users

The operator whose sync fails at the state write — currently shown a
traceback and left with accumulating snapshots in the agents root.

### Success Metrics

- A forced write failure prints `braid: <reason>` and exits 2, matching the
  read side.
- No `.tmp` file remains after the failure.
- The strict-xfail test
  `test_a_failed_state_write_reports_a_braid_error_and_leaves_no_temp_file`
  passes plain.

## Functional Decomposition

Wrap the write in `try/except OSError` re-raised as `BraidError`, with
`finally: temporary.unlink(missing_ok=True)`.

## Structural Decomposition

- `src/agent_skills_braid/cli.py` (`_write_state`, ~244-248)

## Implementation Phases

### Phase 0: The guard

Four lines, un-xfail the authored test.

## Test Strategy

Strict-xfail test on branch `agoge/authored-tests-2026-08-31`:
`tests/test_braid.py::test_a_failed_state_write_reports_a_braid_error_and_leaves_no_temp_file`.
Delete the marker when the fix lands.

Evidence from the report, verbatim:

```
Occupying the state path with a directory:
IsADirectoryError: [Errno 21] Is a directory:
'.../..braid-state.json.1380.tmp' -> '.../.braid-state.json'
and temp files after 3 failed syncs: ['..braid-state.json.1380.tmp',
'..braid-state.json.1385.tmp', '..braid-state.json.1386.tmp'] — one orphan
per run.
```

## Risks

None observed — strictly narrower failure surface. Temp files already
orphaned on the operator's machine are not removed; one manual sweep is owed
(note it in the done summary).

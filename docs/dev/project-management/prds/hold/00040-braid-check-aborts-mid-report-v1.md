---
default_model: opus
rework_cap: 5
---

# `braid --check` aborts mid-report when one managed path was changed by hand

Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 35
(LOW, integration lane, verified). Decision 2026-09-02: accepted — report the
changed path as drift in check and dry-run modes, keep the raise for sync.

## Overview

### Problem Statement

The cleanup refusal (`refusing to clean changed managed path`) is raised
before the mode check, so read-only `--check` dies on it too, after printing
a partial report — one hand-edited link and the health gate cannot report the
other 74. Refusing to mutate is right; refusing to look is not, and the
obvious next move (run `--check` again to see what else is wrong) cannot
work.

### Target Users

The operator running the `AGENTS.md`-mandated health gate.

### Success Metrics

- In `Mode.CHECK` and `Mode.DRY_RUN`, a hand-changed managed path emits
  `MISMATCH CHANGED <path>`, counts as drift, and the report completes.
- `Mode.SYNC` keeps the hard refusal.
- The strict-xfail test
  `test_check_reports_a_hand_changed_managed_path_instead_of_aborting` passes
  plain.

## Functional Decomposition

Gate the raise on mode: check/dry-run emit the mismatch line and continue;
sync raises as today.

## Structural Decomposition

- `src/agent_skills_braid/cli.py` (~321-322)

## Implementation Phases

### Phase 0: The mode gate

Implement, un-xfail the authored test, sweep any wrapper scripting `--check`
for exit-code assumptions.

## Test Strategy

Strict-xfail test on branch `agoge/authored-tests-2026-08-31`:
`tests/test_braid.py::test_check_reports_a_hand_changed_managed_path_instead_of_aborting`.
Delete the marker when the fix lands.

Evidence from the report, verbatim:

```
check after one path was changed -> exit 2, with stdout lines: 1, last line
MISMATCH STALE …/agents7/skills/probe-orphan, and stderr:
braid: refusing to clean changed managed path: …
```

## Risks

`--check` now exits 1 (drift) where it used to exit 2 (error) for this case —
a contract change in the command `AGENTS.md` names as the standard health
gate; check anything scripting it before landing.

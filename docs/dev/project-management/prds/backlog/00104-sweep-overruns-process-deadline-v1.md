---
design: run
default_model: sonnet
model_tier_rationale: subprocess lifetime and shared deadline changes require coordinated scan/control design and real CLI timing tests
---

# Sweep can run well past its deadline

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 15,
accepted option A on 2026-10-27. Also covers findings 18 and 43 of the 2026-10-25
report. The reports are local audit artifacts and are not shipped in the public
repository. Status: mocked evidence, measured with a sleeping search-command shim.

## Problem

Sweep stops waiting for futures at its deadline, but running workers and search
processes remain alive and delay interpreter exit. An all-zero scan can then
start control verification without a deadline. Automation that allows only a
small margin after the configured deadline can kill sweep before it finishes
reporting results.

## Solution

Propagate one remaining deadline budget through scan execution and any required
control verification. Stop launching work when it is exhausted and terminate
in-flight search processes on expiry. Reap subprocesses and finish worker cleanup
promptly. Skip verification when no budget remains and report an explicit
unverified refusal rather than a clean zero-hit result.

## Requirements

### Must have

- The configured deadline governs the scan and subsequent control verification
  together, rather than granting verification a fresh unbounded scan.
- Terminate and reap searches still active at expiry, including subprocess trees
  created by a search command; pending work must not delay process exit.
- Preserve completed hits, deterministic ordering, hit caps, and deadline-failure
  reporting for incomplete repositories.
- An expired zero-hit run must not start fresh verification work or claim clean
  verification. Use the existing non-zero unverified-refusal contract.
- Retain partial reports for completed hits when control verification is unnecessary.
- Preserve normal successful control checks and existing setup-error behavior.
- Keep supported POSIX and Windows behavior and Python 3.10 compatibility.

### Nice to have

- None.

## Implementation

```text
skills/sweep-fix/
├── SKILL.md                            # document deadline and unverified behavior
└── scripts/
    ├── sweep.py                        # subprocess lifetime, deadline, and control budget
    ├── test_sweep_scan.py               # expiration and search cleanup coverage
    ├── test_sweep_verify_control.py     # control budget and existing outcome controls
    └── test_sweep_main.py               # real CLI elapsed-time regression
```

### Module: deadline-aware sweep execution

- **Location**: `skills/sweep-fix/scripts/sweep.py`
- **Maps-to-capability**: stop search work at expiry and finish the command promptly.
- **Responsibility**: coordinate child lifetime, remaining time, and control refusal.
- **Exports**: `scan`, `verify_control`, `main`.

#### Feature: enforce the remaining runtime budget

- **Inputs**: deadline, search processes, completed results, and control-check requirements.
- **Outputs**: completed hits and failed repositories, or an explicit unverified refusal.
- **Behavior**: share the remaining budget, terminate expired work, and never grant
  a zero-hit control check a fresh unrestricted execution window.

### Module: deadline regressions

- **Locations**: `skills/sweep-fix/scripts/test_sweep_scan.py`,
  `skills/sweep-fix/scripts/test_sweep_verify_control.py`,
  `skills/sweep-fix/scripts/test_sweep_main.py`.
- **Maps-to-capability**: prove the outer process exits promptly and retains honest results.
- **Responsibility**: test worker cleanup, control outcomes, and full CLI wall time.
- **Exports**: none.

### Module: operator instructions

- **Location**: `skills/sweep-fix/SKILL.md`
- **Maps-to-capability**: explain partial results and unverified deadline expiry.
- **Responsibility**: describe the implemented contract without promising verified zero hits.
- **Exports**: none.

### Dependencies

- Deadline-aware execution: existing subprocess search and scan result collection (foundation).
- Control verification: depends on the same remaining budget and cleanup mechanism.
- Regressions and instructions: depend on execution and control behavior (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add failing regressions, then coordinate subprocess lifetime and remaining
  deadline through scanning and control verification. Cover an exhausted budget
  before verification, a budget expiring during verification, queued searches,
  and completed hits alongside slow searches. Use a search shim sleeping 10 seconds
  with a 3-second deadline; measure the outer CLI subprocess through actual exit,
  not just scan returning. Assert elapsed time below 5 seconds, allowing a 2-second
  cleanup tolerance (guess), and ensure the test harness cleans up on failure.
  Assert no leftover search descendants, retained completed hits and partial-report
  failures, and an explicit non-zero unverified outcome for skipped control checks.
  Update documentation and adjust obsolete tests that require control verification
  to ignore the deadline, retaining their successful-control coverage.
  Acceptance: `uv run pytest skills/sweep-fix/scripts/test_sweep_scan.py skills/sweep-fix/scripts/test_sweep_verify_control.py skills/sweep-fix/scripts/test_sweep_main.py`
  passes; the outer-process timing regression fails against the prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/sweep-fix`,
and `braid --check` pass.

## Success Criteria

- The sleeping-shim CLI regression exits within its deadline plus cleanup tolerance.
- Expiry leaves no running search descendants and does not grant a new control budget.
- Skipped control verification is visibly unverified; completed source hits are retained.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`--deadline 5`, 20 registered repos plus `--cwd` (21 `rg` calls, 8 workers), shim `sleep 2`: `Partial: 5 repos not scanned (sweep deadline expired)`, process wall **6.08 s, 6.08 s**. 2 repos plus cwd, shim `sleep 10`, `--deadline 3`: `Hits (0):`, `Partial: 3 repos not scanned`, 4 shim calls, wall **13.05 s, 13.06 s**. Stated budget: `--deadline` default 300 s; per-`rg` ceiling `DEFAULT_SCAN_TIMEOUT` 30 s. The `verify_control` mechanism is read from code; the walls are measured.
```

These measurements used a simulated slow search, not real ripgrep latency.
Test subprocess lifetime directly and retain normal fast-search controls.

### Risks

Cancellation can race with search completion and lose finished results unless
collection and cleanup are coordinated. Child-tree termination differs by platform.
A skipped control check must not become a trusted clean report. PRD 00093 changes
search exclusions and PRD 00103 documents scan behavior; preserve those changes
and keep documentation consistent with the final deadline contract.

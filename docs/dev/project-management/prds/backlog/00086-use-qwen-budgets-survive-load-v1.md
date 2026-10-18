---
design: skip
default_model: opus
model_tier_rationale: timing escalator - the edit keeps the order sleep > gate bound > loaded baseline, and a wrong pick reads as a flaky test rather than a clean failure
---

# use-qwen test budgets survive a loaded machine

## Problem

Two use-qwen test modules end with a wall-clock budget,
`test_module_finished_inside_its_runtime_budget`, that asserts
`time.monotonic() - module_started < 60` (`skills/use-qwen/scripts/test_run_eval_harness.py:395-396`,
`skills/use-qwen/scripts/test_run_eval_harness_outcomes.py:474-475`). The budget comes from PRD 00051's
success metric ("the test suite runs ... in under 60 seconds"). `test_run_eval_harness.py` alone now
takes 56.4 s (56 passed in 56.37 s, Python 3.10, 2026-10-17), so any load pushes it over: 67.8 s in the
full suite on master `9871187` (2026-10-17), and both modules failed in a loaded run on 2026-10-16.

The same loaded run gave 114 setup errors in `test_report.py`, `test_report_audit.py` and
`test_report_content.py`. Their shared module fixture `slow`
(`skills/use-qwen/scripts/eval_harness_run_helpers.py:498-516`) vets a bundle at `--gate-bound 2`, and
under load the baseline pytest segment no longer fit in 2 s, so `assert bundle.rc == 0` failed and every
test that needs the fixture errored. All three files pass alone (31 passed in `test_report.py`).

A full-suite run on a busy machine therefore goes red for reasons that have nothing to do with the code.

## Solution

Give both bounds headroom, keeping each guard intact:

- Module budget: 60 s to 120 s in both modules. 120 s is about twice the isolated run, so it still
  catches a module that really doubled its runtime, but it absorbs the load seen on 2026-10-16/17.
- `slow` fixture: gate bound 2 s to 4 s, and its two `sleep 5` segments to `sleep 15`. The bound must
  sit above a loaded baseline (the vet must pass) and well below the sleep (the gate clone and the
  flagged baseline must time out). Both sleeps are killed at the bound, so the longer sleep costs about
  2 s more per bounded segment (the bound moves from 2 s to 4 s), never the full 15 s; it widens the
  margin when a kill lands late. Every place the bound `2` is repeated for the
  `slow` bundle changes with it, because `attempt._admit` refuses a run whose `--gate-bound` differs
  from the vetted one (`skills/use-qwen/scripts/eval_harness/attempt.py:208-211`).

No production code changes.

## Requirements

### Must have

- Both module budgets assert `< 120`, with a comment line above each naming the reason.
- The `slow` fixture vets at gate bound 4, its segments sleep 15, and every `slow`-bundle round in
  `ROUNDS` and the `shape-not-vetted` refusal case run at gate bound 4.
- `test_cli_vet_readies_the_task_and_records_its_gate_bound_and_shapes` expects `gate_bound_s == 4` for
  the `slow` bundle.
- Comments that state the old values (gate bound 2, sleeps 5 s) state the new ones.
- The `hang` round's `{"bound": "2"}` (`skills/use-qwen/scripts/eval_harness_run_helpers.py:87`) is an
  engine bound, not the `slow` gate bound, and stays unchanged.

### Nice to have

- None.

## Implementation

```text
skills/use-qwen/scripts/
├── test_run_eval_harness.py           # module budget; slow-bundle vet assertion
├── test_run_eval_harness_outcomes.py  # module budget
└── eval_harness_run_helpers.py        # slow fixture, ROUNDS, refusal cases
```

### Module: run-harness tests
- **Location**: `skills/use-qwen/scripts/test_run_eval_harness.py`, `skills/use-qwen/scripts/test_run_eval_harness_outcomes.py`
- **Responsibility**: end-to-end tests of `run_eval_harness`, each module closing with its own wall-clock budget.
- **Exports**: `module_started` (module fixture), `test_module_finished_inside_its_runtime_budget`

### Module: run-harness test helpers
- **Location**: `skills/use-qwen/scripts/eval_harness_run_helpers.py`
- **Responsibility**: shared bundles, rounds and refusal cases for the run-harness and report tests.
- **Exports**: `slow`, `rounds`, `ROUNDS`, `REFUSALS`

### Dependencies
- run-harness test helpers: No dependencies (foundation)
- run-harness tests: Depends on [run-harness test helpers]

## Tasks

### Phase 0: Foundation
- [ ] Widen the `slow` bundle's gate bound and sleeps in `skills/use-qwen/scripts/eval_harness_run_helpers.py`
  and its assertion in `skills/use-qwen/scripts/test_run_eval_harness.py`. Premise, re-checked at
  execution (a failed premise means skip and report, never force): `rg -c '"gate_bound": "2"'
  skills/use-qwen/scripts/eval_harness_run_helpers.py` prints 3 (the `gatetimeout`, `basetimeout` and
  `shape-not-vetted` entries), `rg -c 'sleep 5' skills/use-qwen/scripts/eval_harness_run_helpers.py`
  prints 2, and line 111 of `skills/use-qwen/scripts/test_run_eval_harness.py` reads
  `assert (given["gate_bound_s"], given["shapes"], given["ready"]) == (2, ["description"], True)`.
  Edits:
  - the three `{"gate_bound": "2"}` entries become `{"gate_bound": "4"}`;
  - in `slow`, `"--gate-bound", "2"` becomes `"--gate-bound", "4"`, and both `sleep 5` become `sleep 15`;
  - the comment at line 76 reads `# The \`slow\` bundle is vetted at gate bound 4, so its rounds run at 4 as well.`;
  - the `slow` docstring opens `A description-only bundle CLI-vetted at gate bound 4 (P17); its test
    command sleeps 15 s` and its last sentence reads `a pytest segment that takes 3 s on a loaded box
    still fits the bound.`;
  - in `skills/use-qwen/scripts/test_run_eval_harness.py`, line 108's comment says `--gate-bound 4`, and
    line 111 expects `(4, ["description"], True)`.
  Acceptance: `rg -c '"gate_bound": "4"' skills/use-qwen/scripts/eval_harness_run_helpers.py` prints 3,
  `rg -n 'gate bound 2|sleep 5|"--gate-bound", "2"' skills/use-qwen/scripts/eval_harness_run_helpers.py`
  prints nothing, `rg -n '"bound": "2"' skills/use-qwen/scripts/eval_harness_run_helpers.py` still
  prints the `hang` line, and `uv run pytest skills/use-qwen/scripts/test_run_eval_harness_outcomes.py
  -k "timeout or refus"` passes.

### Phase 1: Core
- [ ] Raise both module budgets to 120 s (depends on: Phase 0). Premise, re-checked at execution:
  `rg -c 'module_started < 60'` prints 1 for each of `skills/use-qwen/scripts/test_run_eval_harness.py`
  and `skills/use-qwen/scripts/test_run_eval_harness_outcomes.py`. In each, replace
  `assert time.monotonic() - module_started < 60` with
  `assert time.monotonic() - module_started < 120`, and put this comment line directly above it:
  `# About twice the isolated run (56 s on 2026-10-17): still catches a real doubling, survives a loaded box.`
  Acceptance: `rg -c 'module_started < 120'` prints 1 for each file, `rg -n 'module_started < 60'
  skills/use-qwen/scripts` prints nothing, and `uv run pytest
  skills/use-qwen/scripts/test_run_eval_harness.py skills/use-qwen/scripts/test_run_eval_harness_outcomes.py
  skills/use-qwen/scripts/test_report.py skills/use-qwen/scripts/test_report_audit.py
  skills/use-qwen/scripts/test_report_content.py` passes.

## Success Criteria

- `test_module_finished_inside_its_runtime_budget` passes in both modules, and the `slow` fixture sets
  up cleanly for `test_report.py`, `test_report_audit.py` and `test_report_content.py`.
- The gate-timeout and baseline-timeout rounds still record timeouts:
  `test_run_eval_harness_outcomes.py`'s `basetimeout`/`gatetimeout` assertions (`SUSPECT`,
  `DISCARDED:baseline`, `timed_out is True`) pass unchanged.
- The full `uv run pytest` gate passes at the end of the last phase.

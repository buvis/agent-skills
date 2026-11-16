---
catchup: run
design: skip
default_model: sonnet
model_tier_rationale: three small, test-pinned repairs and one CI flag; the only unknown (Q3) is resolved by recording native evidence, not by design
---

# Close the last six native Windows failures outside the archive modules

> **Ported 2026-11-16 onto `bugfix/windows-suite-residue`.** This PRD was built
> on the closeout lane `closeout/windows` (tip `40efece`) but never merged; its
> only copy was on `origin/ci/closeout-stage-1-*`. Master has moved on, and its
> hosted Windows job is green (run 43875062173), so only the rows master still
> lacks were ported:
>
> - **Task 1 (P1): superseded on master.** `test_ground_prd.py` now uses the
>   shared `isolate_home` fixture in the root `conftest.py`, which sets
>   `USERPROFILE`, `HOMEDRIVE` and `HOMEPATH` on Windows. Not ported.
> - **Task 2 (U2): ported.** The fixture half was already on master
>   (`write_manifest` writes with `newline=""`). The production append and its
>   byte-level regression were missing; the regression failed against master's
>   append on macOS before the fix.
> - **Task 3 (Q3): superseded on master.** Master's `_cwd_log_segment` already
>   logs from a Python child (`os.getcwd()`) with no `pwd -P` and no MSYS form,
>   and the four Q3 tests pass on the hosted Windows job with no skip marker.
>   `native_cwd` and `_to_msys` never reached master. Not ported.
> - **Task 4 (`-ra`): ported.**

Source: `docs/dev/project-management/audit-results/repository-closeout-execution.md`,
entry "Stage 1 — lanes built", section "Native run 41353724204". Continues
held PRD 00044 (Windows suite closure), which built 13 of 14 tasks on
`closeout/windows`. The archive failures in that run belong to PRD 00162.

## Overview

### Problem Statement
The hosted Windows job (CPython 3.13.16) failed six tests that 00044 owns:

- **P1 (1 test).** `test_citation_absolute_and_home_paths_ignore_root` in
  `skills/create-prd/scripts/test_ground_prd.py` isolates only `HOME`. On
  Windows `os.path.expanduser` reads `USERPROFILE` first, so the test's
  home-relative citation resolves under the runner's real profile and reports
  `missing`.
- **U2 residue (1 test).**
  `test_manifest_rewrite_preserves_an_unrelated_row_containing_a_carriage_return`
  in `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py` reads the
  kept row back with a trailing `\r`. The production append in
  `skills/purge-devtmp/scripts/purge_devtmp.py` (`trash_file`,
  `manifest.open("a", encoding="utf-8")`) translates `\n` to `\r\n` on
  Windows. The rewrite already reads and writes with `newline=""`, so it keeps
  the stray `\r`.
- **Q3 (4 tests).** `test_run_eval_cli.py` (2),
  `test_run_eval_harness.py` and `test_run_eval_harness_outcomes.py` under
  `skills/use-qwen/scripts/` got an empty list of logged working directories
  on the lane, which logged Git Bash's `"$(pwd -P)"`.
- **Missing skip reasons.** The Windows suite step in
  `.github/workflows/ci.yml` runs `uv run --python 3.13 pytest` without
  `-ra`. The run skipped 43 tests, 30 more than macOS, and the log does not
  say why.

### Target Users
Maintainers who rely on the Windows CI job as the release gate.

### Success Metrics
- Every Windows skip reason appears in the job log.
- A manifest record that `purge_devtmp.py` appends ends in `\n`, never `\r\n`, on every host.
- Linux, macOS and Windows results are otherwise unchanged.

## Functional Decomposition

### Capability: Manifest records keep LF delimiters
#### Feature: Untranslated append
- **Description**: Every manifest write uses LF as the record delimiter.
- **Inputs**: Manifest rows, including embedded `\r` bytes.
- **Outputs**: A manifest whose rows end in `\n` and keep their embedded bytes.
- **Behavior**: Open the production append with `newline=""`. Add a regression that appends a record through the production path, reads the file as bytes, and asserts no `\r\n` appears. The regression must fail on POSIX for the old code by simulating translation (patch the append's `open` to apply text-mode translation when no `newline` argument is passed).

### Capability: Skip reasons in the Windows log
#### Feature: `-ra` on the Windows suite step
- **Description**: The Windows suite prints a reason for each skip and xfail.
- **Inputs**: `.github/workflows/ci.yml`.
- **Outputs**: The step runs `uv run --python 3.13 pytest -ra`.
- **Behavior**: Change only the Windows suite step. Leave the Linux matrix step unchanged.

## Structural Decomposition

### Repository Structure

```
.github/workflows/ci.yml                                   # Maps to: skip reasons
skills/purge-devtmp/scripts/purge_devtmp.py                # Maps to: LF append
skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py  # Maps to: append regression
```

### Module: purge_devtmp
- **Maps to capability**: Manifest records keep LF delimiters
- **Location**: `skills/purge-devtmp/scripts/purge_devtmp.py`
- **Responsibility**: Append manifest records with LF delimiters.
- **Exports**: unchanged.

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies.

## Implementation Phases

### Phase 0: Repairs
**Goal**: Keep manifest records LF on Windows and record skip reasons.

**Tasks**:
- [x] ~~Isolate `USERPROFILE`, `HOMEDRIVE` and `HOMEPATH` in `test_ground_prd.py`~~ - superseded on master by the root `isolate_home` fixture.
- [x] Append manifest records with `newline=""` in `skills/purge-devtmp/scripts/purge_devtmp.py`, with a byte-level regression (no deps) - Acceptance: the regression fails against the old append on macOS through its simulation and passes after the fix; `uv run pytest skills/purge-devtmp` passes.
- [x] ~~Log the child's resolved cwd in `eval_harness_run_helpers.py`~~ - superseded on master; the four Q3 tests pass on the hosted Windows job.
- [x] Add `-ra` to the Windows suite step in `.github/workflows/ci.yml` (no deps) - Acceptance: the diff touches that one line.

**Exit Criteria**: `uv run pytest` passes on macOS. Native proof comes from the hosted run after integration.

## Test Strategy

### Critical Scenarios
- **Happy path**: `trash_file` appends a record → the manifest bytes hold `\n` and no `\r\n`, even when the platform would translate.
- **Regression**: an append without `newline=""` under simulated translation → the test fails.

## Risks

- **Native proof waits for the hosted run**: macOS cannot observe Windows text-mode translation; the regression simulates it.

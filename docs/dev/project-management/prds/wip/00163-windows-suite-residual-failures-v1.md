---
catchup: run
design: skip
default_model: sonnet
model_tier_rationale: three small, test-pinned repairs and one CI flag; the only unknown (Q3) is resolved by recording native evidence, not by design
---

# Close the last six native Windows failures outside the archive modules

Source: `docs/dev/project-management/audit-results/repository-closeout-execution.md`,
entry "Stage 1 — lanes built", section "Native run 41353724204". Continues
held PRD 00044 (Windows suite closure), which built 13 of 14 tasks on
`closeout/windows`. The archive failures in that run belong to PRD 00162.

## Overview

### Problem Statement
The hosted Windows job (CPython 3.13.16) failed six tests that 00044 owns:

- **P1 (1 test).** `test_citation_absolute_and_home_paths_ignore_root` in
  `skills/create-prd/scripts/test_ground_prd.py` isolates only `HOME`
  (line 229). On Windows `os.path.expanduser` reads `USERPROFILE` first, so
  the test's home-relative citation resolves under the runner's real profile and reports
  `missing`.
- **U2 residue (1 test).**
  `test_manifest_rewrite_preserves_an_unrelated_row_containing_a_carriage_return`
  in `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py` reads the
  kept row back with a trailing `\r`. Two writes still translate `\n` to
  `\r\n` on Windows: the fixture `write_manifest` (`manifest.write_text(...)`
  with no `newline`), and the production append in
  `skills/purge-devtmp/scripts/purge_devtmp.py` at line 174
  (`manifest.open("a", encoding="utf-8")`). The rewrite at lines 229-244
  already reads and writes with `newline=""`, so it keeps the stray `\r`.
- **Q3 (4 tests).** `test_run_eval_cli.py` (2),
  `test_run_eval_harness.py` and `test_run_eval_harness_outcomes.py` under
  `skills/use-qwen/scripts/` get an empty list of logged working
  directories. `_cwd_log_segment` in
  `skills/use-qwen/scripts/eval_harness_run_helpers.py` logs Git Bash's
  `"$(pwd -P)"`. `_logged_cwds` keeps only lines that start with the round's
  native or MSYS-converted prefix. Commit `88fa3df` added the MSYS branch and
  the list is still empty, so the spelling the runner logs is unknown. One
  candidate is the hosted runner's 8.3 short profile name (`RUNNER~1`)
  against the long name `Path.resolve` gives.
- **Missing skip reasons.** The Windows suite step in
  `.github/workflows/ci.yml` runs `uv run --python 3.13 pytest` without
  `-ra`. The run skipped 43 tests, 30 more than macOS, and the log does not
  say why. Pass versus skip for the 00044 rows B1, Q2 and Q8 is unconfirmed.

### Target Users
Maintainers who rely on the Windows CI job as the release gate.

### Success Metrics
- The six tests pass on the hosted Windows job, with no new skip and no xfail.
- Every Windows skip reason appears in the job log.
- A manifest record that `purge_devtmp.py` appends ends in `\n`, never `\r\n`, on every host.
- Linux and macOS results are unchanged.

## Functional Decomposition

### Capability: Home lookup isolated on every host
#### Feature: Profile isolation in the grounding test
- **Description**: The test controls every variable `expanduser` may read.
- **Inputs**: `tmp_path`.
- **Outputs**: The test's home-relative citation resolves under `tmp_path` on every host.
- **Behavior**: Set `USERPROFILE` beside `HOME` with `monkeypatch.setenv`, and delete `HOMEDRIVE` and `HOMEPATH` with `raising=False`. Keep all three expected statuses (`ok`, `ok`, `missing`) unchanged.

### Capability: Manifest records keep LF delimiters
#### Feature: Untranslated append and fixture writes
- **Description**: Every manifest write uses LF as the record delimiter.
- **Inputs**: Manifest rows, including embedded `\r` bytes.
- **Outputs**: A manifest whose rows end in `\n` and keep their embedded bytes.
- **Behavior**: Open the production append with `newline=""`. Write the fixture with `newline=""`. Add a regression that appends a record through the production path, reads the file as bytes, and asserts no `\r\n` appears where the record had none. The regression must fail on POSIX for the old code by simulating translation (patch the append's `open` to the platform's text-mode translation, or assert the `newline` argument through a spy).

### Capability: Working-directory log that matches on every host
#### Feature: Native cwd from the logging child
- **Description**: The logging segment records the directory as the Python child sees it, and the filter compares resolved paths.
- **Inputs**: The round's run directory and the log file.
- **Outputs**: The ordered list of directories the round's commands ran in.
- **Behavior**: Replace the `"$(pwd -P)"` argument with `os.path.realpath(os.getcwd())` computed inside the logging child. In `_logged_cwds`, keep a line when its resolved path lies under the resolved run directory, compared with `os.path.normcase`; keep the order and the duplicate-stamp assertion. Keep `native_cwd` for callers that still parse `pwd` output. When the filtered list is empty, the assertion message must include the raw log lines and the run directory, so a failing native run records the spelling it saw.

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
skills/create-prd/scripts/test_ground_prd.py               # Maps to: profile isolation
skills/purge-devtmp/scripts/purge_devtmp.py                # Maps to: LF append
skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py  # Maps to: LF fixture, append regression
skills/use-qwen/scripts/eval_harness_run_helpers.py        # Maps to: native cwd log and filter
```

### Module: purge_devtmp
- **Maps to capability**: Manifest records keep LF delimiters
- **Location**: `skills/purge-devtmp/scripts/purge_devtmp.py`
- **Responsibility**: Append manifest records with LF delimiters.
- **Exports**: unchanged.

### Module: run helpers
- **Maps to capability**: Working-directory log that matches on every host
- **Location**: `skills/use-qwen/scripts/eval_harness_run_helpers.py`
- **Responsibility**: Log and filter the working directories of a round's commands.
- **Exports**: `native_cwd()` unchanged.

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **purge_devtmp**: LF append regression, then the fix.
- **run helpers**: Native cwd log and resolved filter.
- **test_ground_prd**: Profile isolation.
- **ci.yml**: `-ra` flag.

## Implementation Phases

### Phase 0: Repairs
**Goal**: Fix the six failures and record skip reasons.

**Tasks**:
- [ ] Isolate `USERPROFILE`, `HOMEDRIVE` and `HOMEPATH` in `skills/create-prd/scripts/test_ground_prd.py` (no deps) - Acceptance: `uv run pytest skills/create-prd/scripts/test_ground_prd.py` passes with the same three expected statuses.
- [ ] Append manifest records with `newline=""` in `skills/purge-devtmp/scripts/purge_devtmp.py` and write the fixture the same way, with a byte-level regression (no deps) - Acceptance: the regression fails against the old append on macOS through its simulation and passes after the fix; `uv run pytest skills/purge-devtmp` passes.
- [ ] Log `os.path.realpath(os.getcwd())` from the logging child and filter by resolved path in `skills/use-qwen/scripts/eval_harness_run_helpers.py` (no deps) - Acceptance: `uv run pytest skills/use-qwen/scripts/test_run_eval_cli.py skills/use-qwen/scripts/test_run_eval_harness.py skills/use-qwen/scripts/test_run_eval_harness_outcomes.py` passes on macOS; a unit test proves the empty-list message carries the raw log lines.
- [ ] Add `-ra` to the Windows suite step in `.github/workflows/ci.yml` (no deps) - Acceptance: the diff touches that one line.

**Exit Criteria**: `uv run pytest` passes on macOS. Native proof comes from the hosted run after integration.

## Test Strategy

### Critical Scenarios
- **Happy path**: A round runs its baseline and gates in three clones → the logged list names the three clones in order, on POSIX and Windows.
- **Edge case**: The run directory path contains a space → the logged path still matches.
- **Error case**: The log holds no line under the run directory → the assertion message prints the raw lines and the run directory.

## Risks

- **Q3 cause stays unproven until the native run**: The child-side cwd removes the MSYS spelling from the comparison, but a short-name mismatch is only a hypothesis. The new failure message makes the next native run decisive.

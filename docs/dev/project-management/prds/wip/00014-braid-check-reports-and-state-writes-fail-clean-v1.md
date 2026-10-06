---
default_model: opus
rework_cap: 5
---

# Braid check reports every drift class and state writes fail clean

## Overview

### Problem Statement

`braid --check` is the health gate `AGENTS.md:9` names after every skill edit, and three defects in
`src/agent_skills_braid/cli.py` make it lie or stop. (1) `.braid-state.json` is the only record of which
links braid owns, so a link on disk the state does not name is invisible forever: not cleaned, not
reported, not counted as drift. (2) `_write_state` (`cli.py:244-248`) has no `try`/`finally` and
`entrypoint()` (`cli.py:481-486`) catches only `BraidError`, so an OS-level write failure escapes as a raw
traceback and leaves one full state snapshot per failed run; that failed write is also how the state goes
missing in the first place. (3) The cleanup refusal at `cli.py:322` is raised before the mode check, so
read-only `--check` dies on one hand-edited path after a partial report and never reaches the other 74
links. Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`, findings 4 (HIGH, integration
lane), 34 (LOW, integration lane) and 35 (LOW, integration lane); decision 2026-09-02: reconcile against
the filesystem, guard the write with a finally-unlink, and report a hand-changed path as drift in the
read-only modes.

```
check 0 braid: 0 linked, 74 current, 20 ignored, 0 removed, 0 backed up, 0 drift
while DANGLING .../skills/probe-orphan exists_target=False lexists=True for two links.
IsADirectoryError: [Errno 21] Is a directory: '.../..braid-state.json.1380.tmp'
temp files after 3 failed syncs: 3 names, one orphan per run, unbounded.
check after one path was changed -> exit 2, with stdout lines: 1, last line
MISMATCH STALE .../agents7/skills/probe-orphan, stderr: refusing to clean changed managed path
```

### Target Users

The operator who runs `braid --check` after every skill edit and trusts the drift count it prints.

### Success Metrics

- A symlink under a managed destination root pointing inside a known owner root, in neither `desired` nor
  `previous`, counts as drift in `Mode.CHECK`; today two such links are present and the run prints `0 drift`.
- A failed state write prints `braid: <reason>`, exits 2, and leaves 0 `.tmp` files; today a traceback and
  one temp file per run.
- A hand-changed managed path in `Mode.CHECK` emits a line, counts as drift, and the report completes;
  `Mode.SYNC` keeps the hard refusal.
- `rg -n -c "xfail" tests/test_braid.py` prints 1 (the comment at `tests/test_braid.py:251-253`), down from 4.

## Functional Decomposition

### Capability: Filesystem reconciliation

Read-only modes stop treating the state manifest as the only record of what braid owns.

#### Feature: Orphan link scan

- **Description**: In `Mode.CHECK` and `Mode.DRY_RUN`, report links on disk that are in neither `desired`
  nor `previous`.
- **Inputs**: `<agents-root>/skills` owned by the configured source roots; `<claude-root>/skills` owned by
  `<agents-root>/skills`; `<kiro-root>/skills` owned by `<agents-root>/skills` when Kiro is enrolled
  (added in the review of 2026-10-05: Kiro landed after this PRD was written, and its projection is
  scanned like Claude's); the `desired` and `previous` name sets `run()` already holds.
- **Outputs**: `MISMATCH ORPHAN <path>` per orphan and `+1` on `Result.drift` each.
- **Behavior**: Reporting only. It never unlinks, moves, backs up or relinks, and it does not run in
  `Mode.SYNC`, so the sync summary and the state write are untouched.

#### Feature: Ownership predicate

- **Description**: Decide whether a link on disk is braid's before reporting it.
- **Inputs**: One entry under a destination root, plus that root's owner roots.
- **Outputs**: True only for a symlink whose target lies inside an owner root.
- **Behavior**: Read the raw target with `os.readlink`, make it absolute against the link's parent as
  `_points_to` does (`cli.py:208-216`), then `_resolved` the target's parent directory (`cli.py:83-84`,
  `strict=False`) and re-append the target's last name, so a dangling link still classifies and the link
  is judged by where it points rather than where its last hop leads. Resolving the full target was the
  wording until the review of 2026-10-05; it misses every Claude or Kiro orphan whose union link is
  still on disk, because that hop leads into the source tree and out of the owner root, and the PRD's
  own two-orphan scenario needs both reported. Anything outside every owner root is the operator's and
  stays unreported.

### Capability: Fail-clean state writes

The write side gets the error contract the read side already has.

#### Feature: Guarded state write

- **Description**: Turn an OS-level write failure into a `BraidError` and drop the temp snapshot.
- **Inputs**: The state path and the next `State`.
- **Outputs**: `braid: cannot write Braid state <path>: <error>` and
  exit 2; no `.tmp` file left.
- **Behavior**: Wrap `write_text` and `os.replace` in `try`/`except OSError`, re-raise as `BraidError`, and
  unlink the temp in `finally` with `missing_ok=True`.

### Capability: Read-only drift reporting

Refusing to mutate stays; refusing to look goes.

#### Feature: Mode-gated cleanup refusal

- **Description**: Gate the `refusing to clean changed managed path` raise on the mode.
- **Inputs**: The cleanup loop's `destination`, `old_target` and `mode`.
- **Outputs**: `MISMATCH CHANGED <path>` plus `+1` drift in `Mode.CHECK` and `Mode.DRY_RUN`; today's
  `BraidError` in `Mode.SYNC`.
- **Behavior**: In read-only modes emit, count, and continue the loop so the rest of the report is printed.

## Structural Decomposition

### Repository Structure

```
src/agent_skills_braid/
└── cli.py            # Maps to: Filesystem reconciliation, Fail-clean state writes, Read-only drift reporting
tests/
└── test_braid_check.py  # Maps to: the regression tests for all three capabilities (moved out of
                         # test_braid.py in the review of 2026-10-05, which hit the 800-line limit)
```

### Module: braid CLI

- **Maps to capability**: all three
- **Responsibility**: Compose skills into the union and the Claude projection, and report or apply the
  difference.
- **Exports**:
  - `run()` (`cli.py:335-382`) - drives both `_sync_links` calls, gains the orphan scan
  - `_sync_links()` (`cli.py:275-332`) - desired and cleanup loops; the raise at line 322 becomes mode-gated
  - `_write_state()` (`cli.py:244-248`) - gains the `try`/`except OSError`/`finally` guard

### Module: braid test suite

- **Maps to capability**: all three
- **Responsibility**: Hold the executable record of each defect and of the fix's limits.
- **Exports**:
  - `test_check_reports_a_managed_link_the_state_file_no_longer_records` (line 263)
  - `test_check_reports_a_hand_changed_managed_path_instead_of_aborting` (line 286)
  - `test_a_failed_state_write_reports_a_braid_error_and_leaves_no_temp_file` (line 308)

## Dependency Graph

### Foundation Layer (Phase 0)

No dependencies - built first.

- **`_write_state`**: A state write that fails loudly and leaves nothing behind.

### Core Layer (Phase 1)

- **`_sync_links` cleanup loop**: Depends on [`_write_state`]

### Integration Layer (Phase 2)

- **`run()` orphan scan**: Depends on [`_sync_links` cleanup loop, `_write_state`]. A check run meeting a
  hand-changed path must finish the cleanup loop before it can reach the scan.

## Implementation Phases

### Phase 0: Foundation

**Goal**: A failed state write reports like the read side and orphans nothing.

**Tasks**:
- [ ] Wrap the body of `_write_state` (`src/agent_skills_braid/cli.py:244-248`) in `try`/`except OSError`,
  re-raise as `BraidError(f"cannot write Braid state {path}: {error}")`,
  add `finally: temporary.unlink(missing_ok=True)`, and delete the `@pytest.mark.xfail` decorator above the
  matching test (no deps) - Acceptance:
  `uv run pytest tests/test_braid.py::test_a_failed_state_write_reports_a_braid_error_and_leaves_no_temp_file -q`
  reports `1 passed` with no xfail or xpass, and
  `rg -n --fixed-strings "_write_state has no try/finally" tests/test_braid.py` prints nothing, exit 1.

**Exit Criteria**: `uv run pytest tests -q` reports 0 failed and 2 xfailed.

### Phase 1: Core

**Goal**: A read-only run reports the hand-changed path instead of dying on it.

**Tasks**:
- [ ] In the cleanup loop of `_sync_links` (`src/agent_skills_braid/cli.py:314-330`), raise
  `BraidError(f"refusing to clean changed managed path: {destination}")` only when `mode is Mode.SYNC`; in
  `Mode.CHECK` and `Mode.DRY_RUN` emit `MISMATCH CHANGED {destination}`, do `result.drift += 1`, and
  `continue`; delete the `@pytest.mark.xfail` decorator above the matching test (depends on: Phase 0) -
  Acceptance:
  `uv run pytest tests/test_braid.py::test_check_reports_a_hand_changed_managed_path_instead_of_aborting -q`
  reports `1 passed`, and
  `rg -n --fixed-strings "the cleanup refusal is raised before the mode check" tests/test_braid.py` prints
  nothing, exit 1.
- [ ] Re-check that no in-repo caller reads `--check`'s exit code, which changes from 2 to 1 for this case.
  Premise: today all six mentions are prose (`AGENTS.md:9`, `:108`, `README.md:23`, `:82`, `:118`, `:172`);
  if a script now matches, skip the exit-code change and report (depends on: Phase 0) - Acceptance:
  `rg -n --fixed-strings "braid --check" --glob '!dev/local/**' .` lists exactly those six lines and no file
  under `bin/`, `.github/` or `skills/`.

**Exit Criteria**: A `Mode.CHECK` run over a farm with one hand-changed managed path returns `drift > 0` and
processes every remaining name; `uv run pytest tests -q` reports 0 failed and 1 xfailed.

### Phase 2: Integration

**Goal**: `--check` reconciles against the filesystem, so a link the state forgot is drift.

**Tasks**:
- [ ] Add the orphan scan and its ownership predicate, both specified under Functional Decomposition, to
  `run()` (`src/agent_skills_braid/cli.py:335-382`) after both `_sync_links` calls, and delete the
  `@pytest.mark.xfail` decorator above the matching test (depends on: Phase 1) - Acceptance:
  `uv run pytest tests/test_braid.py::test_check_reports_a_managed_link_the_state_file_no_longer_records -q`
  reports `1 passed`, and
  `rg -n --fixed-strings "reconciles against the state manifest only" tests/test_braid.py` prints nothing,
  exit 1.
- [ ] Add two tests to `tests/test_braid.py` for the scan's limits: `test_check_leaves_the_orphan_link_it_reports_on_disk` (sync, delete the state file,
  re-sync, `Mode.CHECK`; the dangling path still passes `os.path.lexists` and `<agents-root>/backups` does
  not exist) and `test_check_ignores_a_link_pointing_outside_every_source_root` (a planted symlink in
  `<agents-root>/skills` aimed at a `tmp_path` directory in no source root; `result.drift == 0`)
  (depends on: Phase 2 orphan scan) - Acceptance:
  `uv run pytest tests/test_braid.py -q` reports `15 passed` (13 today plus these two) with no xfail,
  xpass or skip.

**Exit Criteria**: `uv run pytest tests -q` reports 0 failed and 0 xfailed, and
`rg -n -c "xfail" tests/test_braid.py` prints 1.

## Test Strategy

### Critical Scenarios

- **Happy path**: links, state and sources all agree, run with `Mode.CHECK` → Expected: `result.drift == 0`
  and no `MISMATCH` line, unchanged from today.
- **Edge case**: a symlink under `<agents-root>/skills` aimed outside every source root, `Mode.CHECK` →
  Expected: `result.drift == 0`, nothing emitted, link untouched on disk.
- **Error case**: the state path occupied by a directory, `Mode.SYNC` → Expected: `BraidError`, exit 2 from
  `entrypoint()`, and `list(state_path.parent.glob(".*.tmp"))` empty.

## Risks

- **The ownership predicate is the whole risk**: calling an operator's hand-made link braid's would turn
  `--check` from silent into destructive, which is worse than the bug. The scan stays read-only in every
  mode, runs only in `Mode.CHECK` and `Mode.DRY_RUN`, and the edge-case test pins its negative side.
- **Exit-code contract change**: `--check` exits 1 (drift) where it exited 2 (error) for a hand-changed
  path, in the command `AGENTS.md` names as the health gate. The Phase 1 task proves no in-repo caller reads
  that status. Human follow-up: check any wrapper outside this repository that scripts `braid --check`.
- **Temp files already orphaned**: the guard stops new ones and removes none. Human follow-up: one manual
  sweep of `.braid-state.json.*.tmp` in each machine's agents root.
- **A sync run still ignores orphans**: the scan is deliberately absent from `Mode.SYNC`, so an orphan is
  reported by `--check` and removed by nobody. Removal was never in scope.
- **Scan cost**: every `--check` now lists two destination roots (74 links today), accepted in the finding.

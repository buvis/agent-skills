---
design: skip
default_model: sonnet
model_tier_rationale: bounded enumeration coverage reporting with existing gap and CLI fixtures
---

# Sweep silently drops stale registry entries

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 20,
accepted option A on 2026-10-27. Also covers finding 11 of the 2026-10-25 report.
Reports are local audit artifacts and are not shipped in the public repository.

## Problem

Sweep silently excludes registered paths that are missing or lack a Git marker.
Operators receive a successful-looking report with no gaps even though some
registered repositories were never scanned. Coverage becomes less trustworthy
as repositories move and stale registry entries accumulate.

## Solution

Retain unresolved registry paths as coverage gaps in the saved report, with the
path and a reason distinguishing a missing path from a non-repository directory.
Continue scanning valid entries. Use the existing Gaps section rather than
introducing a new reporting channel or treating these paths as successful scans.

## Requirements

### Must have

- Registered missing paths and existing paths without a Git marker appear in Gaps.
- Each new gap identifies its path and why it was not scanned.
- Valid registered repositories still scan normally; unresolved paths do not
  become scan targets or block collection of valid results.
- Preserve existing unregistered-on-disk coverage gaps and their meaning.
- Preserve read-only registry handling, bare-repository special handling,
  current-repository deduplication, and worktree Git-file support.
- Preserve current registry-read and control-check failure contracts.
- Document that Gaps includes unresolved registered paths as well as unregistered repos.

### Nice to have

- None.

## Implementation

```text
skills/sweep-fix/
├── SKILL.md                      # explain the expanded Gaps coverage
└── scripts/
    ├── sweep.py                  # retain unresolved registry paths as gaps
    ├── test_sweep_enumerate.py    # missing and non-repository registry rows
    └── test_sweep_main.py         # assert gaps survive into the saved report
```

### Module: repository enumeration

- **Location**: `skills/sweep-fix/scripts/sweep.py`
- **Maps-to-capability**: expose registered coverage that could not be scanned.
- **Responsibility**: retain unresolved rows in gap data consumed by report rendering.
- **Exports**: `enumerate_repos`, `render_report`, `main`.

#### Feature: retain unresolved registry coverage

- **Inputs**: registry entries and their current filesystem/Git-marker state.
- **Outputs**: valid scan targets plus coverage gaps naming unresolved entries.
- **Behavior**: report invalid registered paths rather than silently dropping them,
  while keeping the existing unregistered-on-disk discovery intact.

### Module: coverage regression tests

- **Locations**: `skills/sweep-fix/scripts/test_sweep_enumerate.py`,
  `skills/sweep-fix/scripts/test_sweep_main.py`.
- **Maps-to-capability**: prove unresolved rows remain visible in saved results.
- **Responsibility**: test both enumeration and final report coverage.
- **Exports**: none.

### Module: operator instructions

- **Location**: `skills/sweep-fix/SKILL.md`
- **Maps-to-capability**: explain all reported coverage gaps.
- **Responsibility**: document missing and non-repository registry entries.
- **Exports**: none.

### Dependencies

- Repository enumeration: existing registry parser and filesystem checks (foundation).
- Report integration: consumes gap data through existing rendering.
- Coverage tests and instructions: depend on the enumeration/report contract.

## Tasks

### Phase 0: Foundation

- [ ] Add a failing mixed-registry regression with a valid repository, a missing
  path, and an existing non-repository directory. Retain unresolved rows as Gaps
  with reasons. Assert invalid entries are excluded from scan targets but both
  appear in the saved report, alongside any pre-existing unregistered-repo gaps.
  Retain valid results and existing special-root, worktree, registry-read failure,
  and deduplication coverage. Update the Gaps explanation in the skill.
  Acceptance: `uv run pytest skills/sweep-fix/scripts/test_sweep_enumerate.py skills/sweep-fix/scripts/test_sweep_main.py`
  passes; the mixed-registry report regression fails against the prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/sweep-fix`,
and `braid --check` pass.

## Success Criteria

- Every unresolved registered path is visible in saved coverage gaps.
- Valid repository hits remain available and invalid paths are not scanned.
- Existing gap discovery and error handling remain correct.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Registry rows `.../sw/gone,x`, `.../sw` (no `.git`), `.../sw/repoA`. The report listed only repoA, `Gaps (0)`, no `Failed:`, exit 0. Held: missing or directory registry -> "registry not found", exit 1; non-UTF-8 registry -> "registry unreadable"; missing control repo -> "sweep unverified"; invalid regex -> rg parse error, exit 1, no report.
```

Use temporary registry and repository fixtures; do not rewrite the operator's registry.

### Risks

Stale registries produce longer reports and readers may have assumed Gaps meant
only unregistered repositories. Preserve deterministic ordering and existing
report structure. PRDs 00093 and 00104 also affect sweep; retain their exclusion
and deadline behavior while adding this independent coverage accounting.

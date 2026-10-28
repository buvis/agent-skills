---
design: skip
default_model: sonnet
model_tier_rationale: bounded search exclusion and consecutive-run regression with existing sweep fixtures
---

# Rerunning a sweep counts its own previous reports

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 4,
accepted option A on 2026-10-26. Also covers finding 9 of the 2026-10-25 report.
The reports are local audit artifacts and are not shipped in the public repository.

## Problem

Sweep writes reports under the invoking repository's audit-results directory,
then scans that directory on later runs. Quoted source matches in prior reports
become new hits. Operators verifying a fix therefore get misleading results,
and the false hits compound as more reports are generated.

## Solution

Exclude `docs/dev/project-management/audit-results/**` from ripgrep searches with
`--glob '!docs/dev/project-management/audit-results/**'`. Keep reports in their
existing location and document the exclusion. Test two consecutive sweeps using
the default report destination so the first report remains present for the second.

## Requirements

### Must have

- Matches inside the audit-results directory do not contribute ripgrep sweep hits.
- Identical consecutive runs over unchanged source report identical source hit counts.
- Removing a source match allows the next check to reach zero despite prior reports.
- Existing source matches outside the excluded directory remain visible.
- Preserve the default report location and existing output-path containment rules.

### Nice to have

- None.

## Implementation

```text
skills/sweep-fix/
├── SKILL.md                    # document the audit-results exclusion
└── scripts/
    ├── sweep.py                # exclude generated audit reports from ripgrep
    └── test_sweep_main.py      # consecutive default-output runs and fix confirmation
```

### Module: search scope

- **Location**: `skills/sweep-fix/scripts/sweep.py`
- **Maps-to-capability**: report source matches without counting previous reports.
- **Responsibility**: exclude audit-results while retaining existing scan behavior.
- **Exports**: `_scan_rg`, `main`.

#### Feature: omit audit reports from source searches

- **Inputs**: the existing pattern, repository targets, and audit-results exclusion.
- **Outputs**: source hits unaffected by prior generated reports.
- **Behavior**: exclude audit-results before collecting matches and applying hit caps.

### Module: scope regression tests

- **Location**: `skills/sweep-fix/scripts/test_sweep_main.py`
- **Maps-to-capability**: verify repeated and post-fix scans remain trustworthy.
- **Responsibility**: run the real ripgrep path over temporary repository fixtures.
- **Exports**: none.

### Module: operator instructions

- **Location**: `skills/sweep-fix/SKILL.md`
- **Maps-to-capability**: explain which paths the sweep omits.
- **Responsibility**: document the excluded report directory and its limitation.
- **Exports**: none.

### Dependencies

- Search scope: existing ripgrep invocation (foundation).
- Scope regression tests and operator instructions: depend on search scope.
- Default report creation stays integrated with the existing pipeline.

## Tasks

### Phase 0: Foundation

- [ ] Add a failing regression that runs the same ripgrep sweep twice with the
  default output path, leaving the first report in the scanned repository.
  Add the audit-results exclusion and document it. Assert stable source hits,
  no report-path hits, and zero source hits after removing the planted match,
  while preserving a valid control check. Use existing temporary repository
  fixtures and skip the real-tool regression when ripgrep is unavailable.
  Acceptance: `uv run pytest skills/sweep-fix/scripts/test_sweep_main.py` passes;
  the consecutive-run regression fails against the prior code.
  The unmerged branch `agoge/authored-tests-2026-10-26` holds a strict-xfail
  regression for this finding. Implement independently if absent; if present,
  convert it to a normal regression without merging unrelated branch changes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/sweep-fix`,
and `braid --check` pass.

## Success Criteria

- Repeated scans do not gain hits from existing audit reports.
- A fixed source match is absent from the confirmation run even when reports quote it.
- The documented default report path remains unchanged.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Same sweep twice from repo `a` (`--pattern 'os\.system' ... --cwd <S>/repos/a`). Run 1: "Hits (3)". Run 2: "Hits (6)", three being `./docs/dev/project-management/audit-results/sweep-shell-injection-2026-10-26.md:6: ... ./code.py:1: x = os.system(cmd)`.
```

### Risks

Real source placed under audit-results is excluded. The exclusion must track any
future change to the default report location. Custom output paths outside this
directory are not covered by this accepted option.

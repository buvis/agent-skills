---
design: skip
catchup: skip
default_model: sonnet
model_tier_rationale: documentation transcription from accepted wording and established behavior
---

# Release notes omit changes to PRD validation

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 13,
accepted option A on 2026-10-27. Also covers the create-prd portion of finding 14
of the 2026-10-25 report. The reports are local audit artifacts and are not shipped
in the public repository.

## Problem

Version 0.2.0 changed the PRD checker's invalid-root behavior and corrected
cwd-relative exclusions, but its changelog omits both. Operators encounter an
exit 2 where a wrong root previously appeared clean, without release documentation
explaining the change.

## Solution

Add one create-prd Fixed bullet under Unreleased describing both existing fixes.
The user selected Unreleased and did not authorize amending the cut 0.2.0 section
for this finding. This PRD changes documentation only.

## Requirements

### Must have

- Under Unreleased / Fixed, describe the clear exit 2 diagnostic for a root that
  is not a directory and unreadable-input failures.
- Describe PRD path exclusions being resolved relative to the process cwd.
- Name the create-prd skill and its ground_prd.py helper.
- Preserve other changelog entries and the 0.2.0 section.

### Nice to have

- None.

## Implementation

```text
CHANGELOG.md  # add the omitted create-prd fixes under Unreleased / Fixed
```

### Module: release notes

- **Location**: `CHANGELOG.md`
- **Maps-to-capability**: explain already-shipped PRD checker behavior to operators.
- **Responsibility**: record both fixes in the accepted changelog section.
- **Exports**: none.

#### Feature: document the checker fixes

- **Inputs**: accepted finding and existing checker behavior.
- **Outputs**: an Unreleased Fixed bullet for create-prd.
- **Behavior**: document invalid-root and I/O-error exit 2 behavior and cwd-relative
  exclusion handling without changing implementation or editing a cut release.

### Dependencies

- Release notes: no code changes or new dependencies (foundation).
- Existing checker behavior supplies the documented facts (integration).

## Tasks

### Phase 0: Foundation

- [ ] Premise: Unreleased does not already document both create-prd fixes.
  Re-check the current changelog and helper behavior at execution time; if the
  premise no longer holds, skip the duplicate edit and report why. Add a Fixed
  subsection if needed and one bullet covering the accepted behavior. Suggested
  wording: **create-prd**: ground_prd.py exits 2 with a clear message for an invalid
  --root or unreadable input; relative PRD paths are excluded relative to cwd.
  Acceptance: inspect the Unreleased section for both facts and the create-prd
  name; `python3 scripts/check_changelog_skills.py` passes, and the diff changes
  no published-release content or production files.

Exit criteria: `uv run pytest` and `braid --check` pass. No new tests are needed
for this documentation-only correction.

## Success Criteria

- Unreleased / Fixed describes both already-shipped validation changes.
- The 0.2.0 release section and runtime behavior remain unchanged.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Same call against the v0.1.0 and v0.2.0 scripts: `ground_prd.py --root /private/tmp/does-not-exist-wendy a.md`. v0.1.0 printed `0 blocking, 0 unverified, 0 declared new` (a clean pass; exit code not recorded). v0.2.0 printed `ground_prd: --root /private/tmp/does-not-exist-wendy: not a directory`, exit 2. `rg` finds no ground-prd/create-prd bullet in `[0.2.0]`.
```

Review the changelog diff against these facts and the existing implementation.

### Risks

The explanation lands after the release that shipped the fixes. An existing
Unreleased subsection may have concurrent additions; preserve them and avoid
duplicating a bullet that another change already supplied.

---
design: skip
catchup: skip
default_model: sonnet
model_tier_rationale: documentation transcription of accepted sweep behavior and changelog placement
---

# Release notes omit sweep's changed scanning behavior

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 14,
accepted option A on 2026-10-27. Also covers the sweep portion of finding 14 of
the 2026-10-25 report. The reports are local audit artifacts and are not shipped
in the public repository.

## Problem

Sweep gained parallel scanning, a deadline option with a 300-second default,
and partial-scan reporting, but version 0.2.0's changelog omits these changes.
Operators learn about the changed scanning and incomplete results through
unexpected reports rather than release documentation.

## Solution

Under Unreleased, add Added bullets for --deadline and the Partial indicator,
and a Changed bullet for parallel scanning and the default deadline. The user
selected Unreleased rather than amending the cut 0.2.0 release section.

## Requirements

### Must have

- Document the deadline flag and Partial reporting under Unreleased / Added.
- Document parallel scanning and the 300-second default under Unreleased / Changed.
- Explain that the indicator means results are incomplete and affected repositories
  are reported, rather than implying a successful scan of every repository.
- Name the sweep-fix skill and keep the notes aligned with the current behavior.
- Do not claim the current deadline guarantees total process runtime; that defect
  is finding 15 and has a separate decision.
- Preserve other notes and the cut 0.2.0 release section.

### Nice to have

- None.

## Implementation

```text
CHANGELOG.md  # record sweep additions and behavior changes under Unreleased
```

### Module: release notes

- **Location**: `CHANGELOG.md`
- **Maps-to-capability**: explain existing sweep options and incomplete results.
- **Responsibility**: place the accepted facts in Added and Changed subsections.
- **Exports**: none.

#### Feature: document sweep's scan contract

- **Inputs**: accepted finding and existing sweep behavior.
- **Outputs**: Unreleased notes for the new option, indicator, parallelism, and default.
- **Behavior**: describe the already-shipped behavior accurately without altering
  runtime code or implying the deadline defect is already fixed.

### Dependencies

- Release notes: no code changes or new dependencies (foundation).
- Existing sweep behavior supplies the documented facts (integration).

## Tasks

### Phase 0: Foundation

- [ ] Premise: Unreleased does not already document the accepted sweep changes.
  Re-check the changelog and current sweep behavior at execution time. If the
  premise no longer holds, skip duplicate entries and report why. Add the
  deadline and Partial bullets under Added and parallel/default changes under
  Changed. Preserve existing subsection contents, including other accepted
  changelog corrections, and avoid claiming a hard process-runtime bound.
  Acceptance: inspect Unreleased for all four facts;
  `python3 scripts/check_changelog_skills.py` passes, and the diff changes no
  published-release content or production files.

Exit criteria: `uv run pytest` and `braid --check` pass. No new tests are needed
for this documentation-only correction.

## Success Criteria

- Unreleased explains the new flag, incomplete-result indicator, parallel scanning,
  and default deadline.
- Notes do not overstate the deadline guarantee or imply incomplete scans passed.
- The cut release section and runtime behavior remain unchanged.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
v0.1.0 usage: `[--registry REGISTRY] [--cwd CWD] [--cap CAP] [--out OUT]`; v0.2.0 `--help`: `[--cap CAP] [--deadline DEADLINE] [--out OUT]`. `--deadline 0` -> `--deadline must be a positive integer`. A real run with `--deadline 30` exited 0 and wrote the report. The `Partial:` line itself was not triggered by wendy (peggy triggered it, packet 15).
```

Review the changelog diff against these facts and current implementation rather
than adding tests that merely assert prose.

### Risks

The explanation lands after the release that shipped the changes. PRD 00102 also
edits Unreleased; preserve its create-prd bullet and avoid duplicate headings.
Finding 15 may change deadline handling later, so re-check wording at execution.

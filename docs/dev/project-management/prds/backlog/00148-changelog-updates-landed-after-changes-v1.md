---
design: skip
catchup: skip
default_model: sonnet
model_tier_rationale: Decision-only process reminder with no runtime change.
---

# Changelog updates landed after their changes

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 40, audit dated 2026-10-25. User accepted option A on 2026-10-29. The source report is a local audit artifact.

## Problem

Three historical changelog updates arrived in documentation commits after the corresponding feature or fix. This violates the same-commit convention and means reverting a change alone can leave its release note behind.

## Solution

Record a process reminder: include required changelog updates in the corresponding feature or fix commit. Preserve historical commits and tags. This is a decision-only acceptance, with no new enforcement hook or policy-file change.

## Requirements

### Must have

- Preserve existing history, tags, and release-note contents.
- Treat the historical separation as accepted process drift, not a precedent for future commits.
- Include required changelog entries with future feature or fix commits under the existing rule.
- Retain the reminder in this PRD and audit minutes; do not add a pre-commit check.

### Nice to have

None.

## Implementation

```text
docs/dev/project-management/prds/backlog/
  00148-changelog-updates-landed-after-changes-v1.md
```

### Module: Process decision record

- **Location**: `docs/dev/project-management/prds/backlog/00148-changelog-updates-landed-after-changes-v1.md`
- **Maps-to-capability**: Durable acceptance and future commit reminder.
- **Responsibility**: Record the selected process-only response without scheduling a history rewrite or enforcement change.
- **Exports**: None.

#### Feature: Same-commit reminder

- **Inputs**: Historical finding and explicit option-A acceptance.
- **Outputs**: This record and its audit minute.
- **Behavior**: Preserve history and follow the existing convention for future applicable commits.

### Dependencies

- No runtime or implementation dependencies.

## Tasks

### Phase 0: Record the decision

- [ ] Resolve as decision-only. Verify this record states the same-commit reminder, preserves history, and creates no new hook or policy-file work. Record completion as an applied decision rather than a code fix.

Exit criteria: The accepted reminder has a durable PRD reference and audit minute. No runtime tests are required for this record.

## Success Criteria

- The historical process deviation has an explicit accepted resolution.
- Future applicable commits follow the existing same-commit convention.

### Test Strategy

Original confirmed evidence, preserved verbatim:

```text
`git log v0.1.0..HEAD -- CHANGELOG.md` -> `530affd docs(purge-devtmp)`, `c209840 docs(brush)`, `c1405f6 docs(changelog)`.
```

This is the audit's historical observation, not a claim about the current revision range. Review the record and minute only; do not rerun the audit or rewrite historical commits.

### Risks

The issue can recur because this choice adds no enforcement. The user accepted that tradeoff instead of a new commit check.

---
design: skip
catchup: skip
default_model: sonnet
model_tier_rationale: decision-only record of accepted historical classification risk
---

# Preserve history despite two suspected commit-type mistakes

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 28,
accepted option A on 2026-10-28. Also covers finding 37 of the 2026-10-25 report.
Reports are local audit artifacts and are not shipped in the public repository.
Status: unverified; the audit evidence described code inspection without execution.

## Problem

The audit suspects one test-only change was labeled fix and one pure refactor
was labeled feat in the history leading to release 0.2.0. Counting those subjects
as user-visible changes can overstate historical release contents. Correcting
them would rewrite commits belonging to a tagged release.

## Solution

The user accepted preservation of existing history. Keep commits and tags intact
and classify future commits by actual purpose, using test for test-only changes
and refactor for pure extractions where appropriate. This is a decision-only
record required by the accepted-finding workflow; it introduces no implementation
or history-rewrite task.

## Requirements

### Must have

- Preserve existing commit objects, release tags, and public release history.
- Accept the suspected historical classification mismatch without corrective rewriting.
- Record that future commit types follow the actual change rather than inheriting
  the historical subjects as precedent.
- Retain the finding's unverified status; acceptance does not strengthen its evidence.
- Keep the resolution in this PRD and the audit minutes without adding unrelated policy.

### Nice to have

- None.

## Implementation

```text
docs/dev/project-management/prds/backlog/
└── 00118-historical-commit-types-preserve-history-v1.md  # decision-only record
```

### Module: accepted decision record

- **Location**: `docs/dev/project-management/prds/backlog/00118-historical-commit-types-preserve-history-v1.md`
- **Maps-to-capability**: retain the user's accepted historical-risk decision.
- **Responsibility**: preserve traceability without scheduling a history rewrite.
- **Exports**: none.

#### Feature: preserve the accepted history decision

- **Inputs**: finding 28 and explicit option-A acceptance.
- **Outputs**: this durable record and the corresponding audit-minute entry.
- **Behavior**: preserve historical refs and apply correct classification to future
  ordinary commits; no extra implementation artifact is required.

### Dependencies

- Decision record: no production dependencies or implementation changes.

## Tasks

### Phase 0: Foundation

- [ ] Resolve as decision-only. Confirm this record states option A, preserves
  the unverified evidence status, and authorizes no history rewrite. Record
  completion as an applied decision rather than a code fix. Acceptance: this
  PRD contains the accepted resolution; processing it changes no historical
  commit or tag and requires no production or policy-file edit.

Exit criteria: review the decision record and its report-minute reference.
No runtime verification or new tests are needed for accepting existing history.

## Success Criteria

- The historical-risk decision has a durable PRD reference.
- Existing release history stays intact and future ordinary commits use suitable types.

### Test Strategy

Carry the reported evidence verbatim, preserving its unverified status:

```text
Of the 18 `feat|fix` commits in `v0.1.0..v0.2.0`, these two are mistyped. Its user-visible partner `e44355a` is covered by the 0.2.0 brush bullet.
```

The two subjects were 14dc0fa, a Qwen test-helper gate-bound adjustment, and
dcc86bd, extraction of brush path arithmetic. This record does not upgrade the
static assessment to a verified runtime defect.

### Risks

Tools that count historical feat/fix subjects can still overcount. The user
explicitly accepted that tradeoff instead of changing tagged history.

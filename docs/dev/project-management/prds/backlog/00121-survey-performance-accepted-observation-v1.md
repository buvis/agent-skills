---
design: skip
catchup: skip
default_model: sonnet
model_tier_rationale: decision-only acceptance of measured survey performance
---

# Accept Survey's measured file-reading cost as an observation

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 31,
accepted option A on 2026-10-28. The report is a local audit artifact and is not
shipped in the public repository.

## Problem

Survey reads its sampled files before enforcing the final output-size cap.
The audit measured additional reads in a large synthetic repository but no
missed performance budget. The user must choose between preserving existing
sampling and optimizing work at the risk of changed output.

## Solution

The user accepted current performance as an observation. Preserve existing
sampling, file-reading behavior, and output. This decision-only PRD provides
traceability without an optimization task or new measurement commitment.

## Requirements

### Must have

- Keep the observation and measured evidence without calling it a missed budget.
- Preserve current sampling and output behavior.
- Introduce no optimization, new runtime threshold, or recurring measurement task.
- Record completion as an applied decision rather than an implemented speedup.

### Nice to have

- None.

## Implementation

```text
docs/dev/project-management/prds/backlog/
└── 00121-survey-performance-accepted-observation-v1.md  # decision-only record
```

### Module: performance decision record

- **Location**: `docs/dev/project-management/prds/backlog/00121-survey-performance-accepted-observation-v1.md`
- **Maps-to-capability**: retain the accepted performance tradeoff.
- **Responsibility**: preserve evidence and the no-optimization decision.
- **Exports**: none.

#### Feature: accept measured performance

- **Inputs**: the audit's measurements and explicit option-A acceptance.
- **Outputs**: this record and the matching audit-minute entry.
- **Behavior**: retain current behavior without scheduling optimization or benchmarking.

### Dependencies

- Decision record: no production dependencies or implementation changes.

## Tasks

### Phase 0: Foundation

- [ ] Resolve as decision-only. Confirm the record accepts existing performance,
  preserves the observed measurements, and contains no optimization or new
  threshold. Acceptance: processing this PRD requires no production edit and
  records the resolution as an applied decision.

Exit criteria: review this decision record and its report-minute reference.
No runtime verification or new tests are needed to accept current performance.

## Success Criteria

- The accepted observation has a durable PRD reference.
- Survey's existing behavior remains intact, without claiming a new speedup.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`run.py` with cwd in a synthetic repo, 200 dirs x 60 files (12,000 files on disk): 10,000 files read, 5093 B, wall 0.55-0.58 s over 3 runs. 200 dirs x 5 files: 1000 files, 5098 B (22 B under 5120). The repo itself: 114 files, 3067 B, 0.051 s.
```

These are historical observations, not a new runtime service-level requirement.

### Risks

A much larger repository can become visibly slower as reading work grows.
The user accepted that tradeoff and did not select the threshold-based deferral.

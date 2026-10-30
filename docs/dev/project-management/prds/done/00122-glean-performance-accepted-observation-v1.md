---
design: skip
catchup: skip
default_model: sonnet
model_tier_rationale: decision-only acceptance of measured tree and ledger scan costs
---

# Accept Glean's measured tree and ledger scan cost

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 33,
accepted option A on 2026-10-29. The report is a local audit artifact and is not
shipped in the public repository.

## Problem

Directory enumeration and path-pattern matching scale with tree and ledger size.
The audit measured modest slowdowns without a stated performance budget. The
user must choose whether those observations justify optimization now.

## Solution

Accept current performance as an observation. Preserve directory enumeration,
pattern matching, and verdict behavior without a new optimization or performance
threshold. This decision-only PRD records that tradeoff for the accepted-finding workflow.

## Requirements

### Must have

- Retain the measured evidence without labeling it a missed performance budget.
- Introduce no pattern-precompilation work or recurring measurement requirement.
- Preserve current matching and secret-prescreen behavior.
- Record completion as an applied decision rather than an implemented speedup.

### Nice to have

- None.

## Implementation

```text
docs/dev/project-management/prds/backlog/
└── 00122-glean-performance-accepted-observation-v1.md  # decision-only record
```

### Module: performance decision record

- **Location**: `docs/dev/project-management/prds/backlog/00122-glean-performance-accepted-observation-v1.md`
- **Maps-to-capability**: retain the accepted scan-performance tradeoff.
- **Responsibility**: preserve the observation without scheduling optimization.
- **Exports**: none.

#### Feature: accept measured scan cost

- **Inputs**: audit measurements and explicit option-A acceptance.
- **Outputs**: this decision record and corresponding audit minutes.
- **Behavior**: keep existing performance while retaining evidence for future context.

### Dependencies

- Decision record: no production dependencies or implementation changes.

## Tasks

### Phase 0: Foundation

- [ ] Resolve as decision-only. Confirm this record accepts current scan cost
  without introducing optimization or a new threshold. Acceptance: processing
  this PRD requires no production edit and records the resolution as an applied decision.

Exit criteria: review the record and its report-minute reference.
No runtime verification or new tests are needed to accept current performance.

## Success Criteria

- The accepted performance observation has a durable PRD reference.
- Existing scan and matching behavior remains intact without claiming a speedup.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
A 10,000-file untracked dir: 10,101 `rglob` entries, 20,306 `Path.stat` calls (about 2 per file), 200 files prescreened, 0.15 s. 1000 unmatched paths: 2000 `fnmatch` calls with built-ins, 402,000 with 200 extra glob ledger entries; in-process 0.312 s -> 0.533 s, end to end 0.33 s -> 0.49 s. 1000 collapsed `.config/appN/.local/` dirs: 1 `Path.stat` total, 0.09 s (the settled case short-circuits).
```

These are historical measurements, not a newly introduced timing requirement.

### Risks

Growing ledgers and larger directory trees can eventually produce noticeable
latency. The user accepted that risk without choosing threshold-based deferral.

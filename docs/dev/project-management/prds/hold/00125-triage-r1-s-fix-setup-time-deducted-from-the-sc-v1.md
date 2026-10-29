---
catchup: skip
design: skip
ledger: deferred/202610271200-deferred.json
ledger_key: c11759e8de96
source_prd: 00104-sweep-overruns-process-deadline-v1.md
severity: high
---

# Triage: R1's fix (setup time deducted from the scan budget) has no test that fails wi...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202610271200`, ledger `deferred/202610271200-deferred.json`, type `cap-overflow`, cycle `2`, consensus `1/3`, op_id `9725262e2cee-dd2`, raised against `00104-sweep-overruns-process-deadline-v1.md`.

Issue: R1's fix (setup time deducted from the scan budget) has no test that fails without it: the loosened assertions in test_main_passes_deadline_through_to_scan and test_main_passes_remaining_deadline_into_verify_control are satisfied by the old code, and reverting _scan_deadline_after_setup leaves all 38 tests green

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `c11759e8de96`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `c11759e8de96` from `00104-sweep-overruns-process-deadline-v1.md` until a human triages it
- **Exports**: none

### Dependencies
- triage: No dependencies (foundation)

## Tasks

### Phase 0: Foundation
- [ ] triage: promote to backlog or close - Acceptance: this file is no longer under docs/dev/project-management/prds/hold/

### Phase 1: Core
No implementation tasks until attended triage.

## Success Criteria

- This file is no longer under `docs/dev/project-management/prds/hold/`.

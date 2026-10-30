---
catchup: skip
design: skip
ledger: deferred/202610271200-deferred.json
ledger_key: 059e66ef581f
source_prd: 00111-braid-state-misses-link-removals-v1.md
severity: critical
---

# Triage: R1 [3/3] CRITICAL regression introduced by cycle-1 rework: on_removal(managed...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202610271200`, ledger `deferred/202610271200-deferred.json`, type `cap-overflow`, consensus `3/3`, raised against `00111-braid-state-misses-link-removals-v1.md`.

Issue: R1 [3/3] CRITICAL regression introduced by cycle-1 rework: on_removal(managed) persists a snapshot that omits every not-yet-processed stale record, so an early removal plus a later refusal discards ownership of still-present links and of the refused hand-changed path. The link becomes a permanent unowned orphan and braid --check then reports 0 drift. Reproduced independently by Alice, Blake and Bob with aa/bb/cc in a temp root. Fix: pass on_removal({**pending, **managed}) where pending is previous-minus-resolved.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `059e66ef581f`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `059e66ef581f` from `00111-braid-state-misses-link-removals-v1.md` until a human triages it
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

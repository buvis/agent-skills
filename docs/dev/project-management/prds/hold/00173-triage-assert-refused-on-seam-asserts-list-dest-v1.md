---
catchup: skip
design: skip
ledger: deferred/202611011931-deferred.json
ledger_key: 3b1f8b5e4ef7
source_prd: 00160-template-archive-extraction-fails-closed-v1.md
severity: high
---

# Triage: _assert_refused_on_seam asserts list(dest.glob("*")) == [], which an empty de...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202611011931`, ledger `deferred/202611011931-deferred.json`, type `adversary-weak-point`, raised against `00160-template-archive-extraction-fails-closed-v1.md`.

Issue: _assert_refused_on_seam asserts list(dest.glob("*")) == [], which an empty dest created by the refusal itself satisfies while a half-built template.staging-* tree holding the archive survives on disk. Remedy: assert not os.path.lexists(dest) and that no dest.parent entry matching dest.name + ".staging-*" survives. Proven by Devon at task 8, deferred on task-8 scope pins (shared helper).

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `3b1f8b5e4ef7`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `3b1f8b5e4ef7` from `00160-template-archive-extraction-fails-closed-v1.md` until a human triages it
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

---
catchup: skip
design: skip
ledger: deferred/202611011931-deferred.json
ledger_key: b667a565de7d
source_prd: 00160-template-archive-extraction-fails-closed-v1.md
severity: high
---

# Triage: _assert_refused_on_seam in test_eval_tree_archive_safety.py observes only tmp...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202611011931`, ledger `deferred/202611011931-deferred.json`, type `adversary-weak-point`, raised against `00160-template-archive-extraction-fails-closed-v1.md`.

Issue: _assert_refused_on_seam in test_eval_tree_archive_safety.py observes only tmp_path/outside and dest, so an implementation that copies the whole archive to dest.parent/leaked-bundle.tar passes every reject row unseen. Remedy: snapshot all of tmp_path before the call and assert dest is the only entry added. Proven by Devon at task 8 (exploit ran, 150 passed), deferred on task-8 scope pins (shared helper).

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `b667a565de7d`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `b667a565de7d` from `00160-template-archive-extraction-fails-closed-v1.md` until a human triages it
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

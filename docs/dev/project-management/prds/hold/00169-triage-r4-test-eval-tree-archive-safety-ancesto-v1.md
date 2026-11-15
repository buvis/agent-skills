---
catchup: skip
design: skip
ledger: deferred/202611011931-deferred.json
ledger_key: 87a2b3f5a429
source_prd: 00160-template-archive-extraction-fails-closed-v1.md
severity: high
---

# Triage: R4 (test_eval_tree_archive_safety_ancestor_parity.py:50): test_build_template...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202611011931`, ledger `deferred/202611011931-deferred.json`, type `cap-overflow`, cycle `2`, consensus `2/4`, op_id `b0744ac53b3a-dd2`, raised against `00160-template-archive-extraction-fails-closed-v1.md`.

Issue: R4 (test_eval_tree_archive_safety_ancestor_parity.py:50): test_build_template_falls_back_to_manual_extraction_when_data_filter_is_present_but_not_callable cannot fail, so cycle-1 R2 no-test-pins-it is still true even though the code is fixed. extractall(filter=data) resolves the named filter through the tarfile internal _NAMED_FILTERS and ignores the patched module attribute. assumptions.md records this as unavoidable on this runtime; Alice demonstrated it is avoidable by spying on tarfile.TarFile.extractall and asserting no filter kwarg. Regression introduced by commit e2f032b.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `87a2b3f5a429`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `87a2b3f5a429` from `00160-template-archive-extraction-fails-closed-v1.md` until a human triages it
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

---
catchup: skip
design: skip
ledger: deferred/202611011931-deferred.json
ledger_key: 475a83eb9b83
source_prd: 00160-template-archive-extraction-fails-closed-v1.md
severity: high
---

# Triage: R3 (test_eval_tree_archive_safety_ancestor_parity.py:75): the cycle-1 R3 regr...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202611011931`, ledger `deferred/202611011931-deferred.json`, type `cap-overflow`, cycle `2`, consensus `2/4`, op_id `b0744ac53b3a-dd1`, raised against `00160-template-archive-extraction-fails-closed-v1.md`.

Issue: R3 (test_eval_tree_archive_safety_ancestor_parity.py:75): the cycle-1 R3 regression does not pin the ancestor rule. ANCESTOR_CROSSING_THROUGH_A_SAFE_LINK holds both pkg/a.txt and alias/a.txt, which the landing-collision rule already refuses, and the computed fail-first replay confirms the test passes against the pre-change code. With _ancestor_crossing stubbed out only the four case-alias-directory-link cases fail; the cycle-1 reproducer (pkg/, alias to pkg, alias/file.txt with no colliding member) is accepted under the stub and untested. Regression introduced by commit e2f032b.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `475a83eb9b83`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `475a83eb9b83` from `00160-template-archive-extraction-fails-closed-v1.md` until a human triages it
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

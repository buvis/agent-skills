---
catchup: skip
design: skip
ledger: deferred/202611011931-deferred.json
ledger_key: 453c61db5b64
source_prd: 00160-template-archive-extraction-fails-closed-v1.md
severity: high
---

# Triage: R5 (trees.py:304): cycle-1 R5 remains incomplete. _symlink_targets_a_director...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202611011931`, ledger `deferred/202611011931-deferred.json`, type `cap-overflow`, cycle `2`, consensus `1/4`, op_id `b0744ac53b3a-dd3`, raised against `00160-template-archive-extraction-fails-closed-v1.md`.

Issue: R5 (trees.py:304): cycle-1 R5 remains incomplete. _symlink_targets_a_directory recognises only explicit directory members, so a link whose target is the extraction root or an implicitly-created parent is typed as a file link. Measured: a link to dot is accepted, extracts, and is created with target_is_directory False; so is a link to pkg when the archive carries pkg/f.txt but no pkg directory member. The first shape is an ordinary committed symlink that git archive emits, so it is reachable from real input. On Windows it produces a file symlink where PRD Phase 2 requires a directory symlink. Regression introduced by commit f39f06e.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `453c61db5b64`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `453c61db5b64` from `00160-template-archive-extraction-fails-closed-v1.md` until a human triages it
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

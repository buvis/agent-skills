---
catchup: skip
design: skip
ledger: deferred/202611011931-deferred.json
ledger_key: 6c34669148b8
source_prd: 00160-template-archive-extraction-fails-closed-v1.md
severity: critical
---

# Triage: Case-folding ancestor alias lets an accepted archive write outside dest: A ->...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202611011931`, ledger `deferred/202611011931-deferred.json`, type `review-finding`, cycle `1`, consensus `1/4`, raised against `00160-template-archive-extraction-fails-closed-v1.md`.

Issue: Case-folding ancestor alias lets an accepted archive write outside dest: A -> . plus a member named a/../outside/secret.txt passes validation, and the manual no-filter path then mkdirs through dest/a, which case-folds onto dest/A -> ., so .. climbs out of dest and the payload lands beside it (reproduced at a8347f3 on a case-insensitive filesystem). The filter path keeps it inside, so it is also a parity break.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `6c34669148b8`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `6c34669148b8` from `00160-template-archive-extraction-fails-closed-v1.md` until a human triages it
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

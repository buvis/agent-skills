---
catchup: skip
design: skip
ledger: deferred/202611011931-deferred.json
ledger_key: 533f2c4cbf1c
source_prd: 00160-template-archive-extraction-fails-closed-v1.md
severity: high
---

# Triage: test_build_template_seals_a_real_git_archive_as_the_tree_before_the_task and...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202611011931`, ledger `deferred/202611011931-deferred.json`, type `adversary-weak-point`, raised against `00160-template-archive-extraction-fails-closed-v1.md`.

Issue: test_build_template_seals_a_real_git_archive_as_the_tree_before_the_task and the control seals pin only HEAD tree, so an extra commit whose tree carries a payload passes every tree-id, ls-files, mode and determinism assertion, and git checkout HEAD~1 in a later attempt restores the payload. Devon proved this. Remedy: assert trees._git(dest, "rev-list", "--count", "HEAD") == "1". Deferred on task-8 scope pins.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `533f2c4cbf1c`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `533f2c4cbf1c` from `00160-template-archive-extraction-fails-closed-v1.md` until a human triages it
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

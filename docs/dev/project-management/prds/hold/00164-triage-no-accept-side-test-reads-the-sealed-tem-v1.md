---
catchup: skip
design: skip
ledger: deferred/202611011931-deferred.json
ledger_key: b746e09bc6ee
source_prd: 00160-template-archive-extraction-fails-closed-v1.md
severity: high
---

# Triage: No accept-side test reads the sealed template .git, and _walk skips it, git a...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202611011931`, ledger `deferred/202611011931-deferred.json`, type `adversary-weak-point`, raised against `00160-template-archive-extraction-fails-closed-v1.md`.

Issue: No accept-side test reads the sealed template .git, and _walk skips it, git add -A ignores it and status --porcelain stays empty, so a live executable post-checkout hook can ship inside a sealed template and no test notices. Devon planted a 0o755 .git/hooks/post-checkout and all accept rows passed. Remedy: assert the sealed template .git/hooks holds no executable hook and core.hooksPath/core.fsmonitor are unset. Related unverified gap Devon raised by reading: no row feeds a crafted tar containing a .git/... member, _refuse_duplicate_or_crossing_members has no .git rule, and build_template runs git init after extraction, so an archive-supplied .git/config would be reinitialized rather than discarded. Deferred on task-8 scope pins.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `b746e09bc6ee`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `b746e09bc6ee` from `00160-template-archive-extraction-fails-closed-v1.md` until a human triages it
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

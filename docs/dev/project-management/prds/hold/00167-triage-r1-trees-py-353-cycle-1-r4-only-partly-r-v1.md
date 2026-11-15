---
catchup: skip
design: skip
ledger: deferred/202611011931-deferred.json
ledger_key: a2f67582c5cb
source_prd: 00160-template-archive-extraction-fails-closed-v1.md
severity: high
---

# Triage: R1 (trees.py:353): cycle-1 R4 only partly resolved, and the rework lost an er...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202611011931`, ledger `deferred/202611011931-deferred.json`, type `cap-overflow`, cycle `2`, consensus `3/4`, op_id `b0744ac53b3a-dd0`, raised against `00160-template-archive-extraction-fails-closed-v1.md`.

Issue: R1 (trees.py:353): cycle-1 R4 only partly resolved, and the rework lost an error-translation guarantee. The manual extraction path still applies the archive directory mode, while filter=data sets a directory mode to None so tarfile creates it at 0o777 and ~umask. Measured: directory 0o500 extracts 0o755 on the filter seam and 0o500 on the manual seam; a directory at mode 0o000 or 0o200 holding a child seals on the filter seam while the manual seam leaks a raw subprocess.CalledProcessError from the seal git commit and leaves dest.staging-hex behind. Breaks PRD A9 output contract (a sealed template or a TreeError) and its cleanup rule. Fix: do not chmod directories on the manual path, and wrap the seal. Regression introduced by commit e46f79a.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `a2f67582c5cb`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `a2f67582c5cb` from `00160-template-archive-extraction-fails-closed-v1.md` until a human triages it
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

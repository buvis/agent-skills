---
catchup: skip
design: skip
ledger: deferred/202610271200-deferred.json
ledger_key: aad0c21c4243
source_prd: 00131-crafted-template-archive-escapes-directory-v1.md
severity: high
---

# Triage: The compatibility branch is an unfiltered fallback: with tarfile.data_filter...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202610271200`, ledger `deferred/202610271200-deferred.json`, type `cap-overflow`, cycle `2`, consensus `1/3`, raised against `00131-crafted-template-archive-escapes-directory-v1.md`.

Issue: The compatibility branch is an unfiltered fallback: with tarfile.data_filter missing, build_template calls bare archive.extractall(dest). The preflight checks no modes, so setuid/setgid bits and ownership metadata from a crafted tar are applied unfiltered. The PRD forbids an unfiltered fallback; the fallback should be a safe manual filter or a TreeError refusal.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `aad0c21c4243`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `aad0c21c4243` from `00131-crafted-template-archive-escapes-directory-v1.md` until a human triages it
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

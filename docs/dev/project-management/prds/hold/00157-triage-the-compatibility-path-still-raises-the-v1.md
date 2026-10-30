---
catchup: skip
design: skip
ledger: deferred/202610271200-deferred.json
ledger_key: 0ce10dfb0605
source_prd: 00131-crafted-template-archive-escapes-directory-v1.md
severity: high
---

# Triage: The compatibility path still raises the omitted-filter DeprecationWarning tha...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202610271200`, ledger `deferred/202610271200-deferred.json`, type `cap-overflow`, cycle `2`, consensus `1/3`, raised against `00131-crafted-template-archive-escapes-directory-v1.md`.

Issue: The compatibility path still raises the omitted-filter DeprecationWarning that finding 42 requires removed. With -W error::DeprecationWarning on CPython 3.12.16 two tests fail on the warning raised from trees.py:183 (test_build_template_seals_a_safe_tree_with_or_without_tar_data_filter[without-data-filter] and the compatibility-path sealing test).

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `0ce10dfb0605`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `0ce10dfb0605` from `00131-crafted-template-archive-escapes-directory-v1.md` until a human triages it
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

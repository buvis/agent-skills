---
catchup: skip
design: skip
ledger: deferred/202610271200-deferred.json
ledger_key: 3355b5e339c4
source_prd: 00111-braid-state-misses-link-removals-v1.md
severity: high
---

# Triage: R2 [2/3] HIGH: the CI lint job is red at HEAD for this PRD. uv run ruff check...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202610271200`, ledger `deferred/202610271200-deferred.json`, type `cap-overflow`, consensus `2/3`, raised against `00111-braid-state-misses-link-removals-v1.md`.

Issue: R2 [2/3] HIGH: the CI lint job is red at HEAD for this PRD. uv run ruff check fails with I001 (unsorted import block) and UP035 (Callable imported from typing) on src/agent_skills_braid/_run_stages.py:12, and uv run ruff format --check fails on src/agent_skills_braid/cli.py. The pre-PRD cli.py at 6091e02 passes both, so this is new with this PRD.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `3355b5e339c4`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `3355b5e339c4` from `00111-braid-state-misses-link-removals-v1.md` until a human triages it
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

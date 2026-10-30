---
catchup: skip
design: skip
ledger: deferred/202610271200-deferred.json
ledger_key: b56b085a5b50
source_prd: 00120-link-check-noise-hides-dead-references-v1.md
severity: 🟠
---

# Triage: Most "repairs" are `link-ok:` waivers on genuinely missing `~/.claude/dev/loc...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202610271200`, ledger `deferred/202610271200-deferred.json`, type `deferred_decision`, cycle `1`, raised against `00120-link-check-noise-hides-dead-references-v1.md`.

Issue: Most "repairs" are `link-ok:` waivers on genuinely missing `~/.claude/dev/local/...` citations, not repairs or removals. The spec says to repair with verified replacement targets or remove obsolete citations. Waiver is an existing mechanism, but it hides the dead target and exempts the whole line from every other check. It also leaves tool markers in prose. The PRD does not name this as an accepted outcome

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `b56b085a5b50`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `b56b085a5b50` from `00120-link-check-noise-hides-dead-references-v1.md` until a human triages it
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

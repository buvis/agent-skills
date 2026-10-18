---
catchup: skip
design: skip
ledger: deferred/202610100952-deferred.json
ledger_key: bac71612d738
source_prd: 00075-ground-prd-claims-against-installed-code-v1.md
severity: high
---

# Triage: R1 only half fixed. `main()` now catches `RuntimeError` and exits 2, but a no...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202610100952`, ledger `deferred/202610100952-deferred.json`, type `cap-overflow`, cycle `2`, consensus `3/3`, raised against `00075-ground-prd-claims-against-installed-code-v1.md`.

Issue: R1 only half fixed. `main()` now catches `RuntimeError` and exits 2, but a nonexistent `--root` still raises an uncaught `FileNotFoundError` from `subprocess.run(cwd=root)`. A traceback follows and the gates read exit 1 ("blocking"). The cycle-1 finding named this case explicitly. Fix: validate `root.is_dir()` in `main()` next to the unreadable-input check and exit 2 with a stderr message, or catch `OSError` alongside `RuntimeError`. Add a test. Blake adds the same class for `Cargo.lock`'s unguarded `read_text` in `known_packages`.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `bac71612d738`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `bac71612d738` from `00075-ground-prd-claims-against-installed-code-v1.md` until a human triages it
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

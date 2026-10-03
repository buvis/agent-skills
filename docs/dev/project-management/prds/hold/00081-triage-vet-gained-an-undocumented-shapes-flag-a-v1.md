---
catchup: skip
design: skip
ledger: deferred/202609050909-deferred.json
ledger_key: 04e47608c859
source_prd: 00051-qwen-eval-harness-core-v1.md
severity: high
---

# Triage: vet gained an undocumented --shapes flag and a third CLI subcommand verify pl...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202609050909`, ledger `deferred/202609050909-deferred.json`, type `scope-divergence`, cycle `1`, consensus `1/4`, raised against `00051-qwen-eval-harness-core-v1.md`.

Issue: vet gained an undocumented --shapes flag and a third CLI subcommand verify plus the ~400-line eval_harness/evidence.py sealing subsystem (manifest.json, prompts/, dispatch-references.json, sealed-inputs.json) that the PRD never specifies; the re-seal rmtree in _write_seal travels with it

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `dev/local/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `04e47608c859`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `dev/local/prds/hold/`
- **Responsibility**: hold ledger key `04e47608c859` from `00051-qwen-eval-harness-core-v1.md` until a human triages it
- **Exports**: none

### Dependencies
- triage: No dependencies (foundation)

## Tasks

### Phase 0: Foundation
- [ ] triage: promote to backlog or close - Acceptance: this file is no longer under dev/local/prds/hold/

### Phase 1: Core
No implementation tasks until attended triage.

## Success Criteria

- This file is no longer under `dev/local/prds/hold/`.

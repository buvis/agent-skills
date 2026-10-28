---
catchup: skip
design: skip
ledger: deferred/202610271200-deferred.json
ledger_key: 21a5c040fcb9
source_prd: 00099-evaluation-render-crashes-malformed-data-v1.md
severity: high
---

# Triage: _check_run_shape validates only the per-task id key and the root started key,...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202610271200`, ledger `deferred/202610271200-deferred.json`, type `cap-overflow`, cycle `2`, consensus `2/3 as consolidated (substantively 3/3: Blake raised it blind and the ledger filter wrongly auto-dismissed his row against cycle 1 R7)`, raised against `00099-evaluation-render-crashes-malformed-data-v1.md`.

Issue: _check_run_shape validates only the per-task id key and the root started key, so every other run.json field render dereferences still escapes as a Python traceback through the CLI: a task missing slug, repo or kind (KeyError at report.py:150/296/298/329/430), a missing config, versions or server (KeyError at report.py:285/287/310/318), config as a list (AttributeError: list has no attribute items), a list-valued task id (TypeError: unhashable type at report.py:552), and a non-string engine id (TypeError in the join at report.py:308). The PRD must-have "validate the engine and task containers and fields needed by rendering before use" is therefore half met after two cycles. The writer contract for every one of these fields is already encoded at skills/use-qwen/scripts/eval_harness/records_domains.py:74 and render does not use it. Fix: require slug, repo and kind on each task, require config, versions and server as dicts, type-check the task id and the engine id, and add the matching RUN_JSON_WRONG_SHAPE rows.

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `21a5c040fcb9`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `21a5c040fcb9` from `00099-evaluation-render-crashes-malformed-data-v1.md` until a human triages it
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

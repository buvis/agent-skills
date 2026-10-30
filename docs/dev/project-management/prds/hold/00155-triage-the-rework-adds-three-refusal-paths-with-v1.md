---
catchup: skip
design: skip
ledger: deferred/202610271200-deferred.json
ledger_key: b4a59a48daaf
source_prd: 00131-crafted-template-archive-escapes-directory-v1.md
severity: high
---

# Triage: The rework adds three refusal paths with no test: non-file/dir/symlink member...

## Problem

Deferred finding with no PRD owner when this stub was minted: batch `202610271200`, ledger `deferred/202610271200-deferred.json`, type `cap-overflow`, cycle `2`, consensus `2/3`, raised against `00131-crafted-template-archive-escapes-directory-v1.md`.

Issue: The rework adds three refusal paths with no test: non-file/dir/symlink members, the os.path.isabs(member.name) refusal (trees.py:143), and the landing-collision refusal (alias -> pkg plus alias/file, trees.py:161). Cycle-1 R1 asked for a hardlink test and an absolute-member test and neither exists; deleting trees.py:145-146 or :161-163 leaves the suite green. _crafted_tar needs a hardlink kind. Merged with Alice's false compat-test comment (test_eval_tree_links.py:490) and Blake's missing warning-as-error check on the compatibility path (:487).

## Solution

Attended triage. A human promotes this finding into a backlog PRD through normal PRD authoring and review, or closes it. Autopilot never drains `docs/dev/project-management/prds/hold/`, and this stub is never auto-promoted.

## Requirements

### Must have
- A triage decision for ledger key `b4a59a48daaf`: a backlog PRD, or closed.

### Nice to have
- None until triage.

## Implementation

### Module: triage
- **Location**: `docs/dev/project-management/prds/hold/`
- **Responsibility**: hold ledger key `b4a59a48daaf` from `00131-crafted-template-archive-escapes-directory-v1.md` until a human triages it
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

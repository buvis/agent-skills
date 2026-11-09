---
design: skip
catchup: skip
default_model: sonnet
model_tier_rationale: inherited documentation correction for the shared trash restoration workflow
---

# Nested trash restoration needs its original parent directory

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 31. Acceptance is
inherited on 2026-10-29 through the user's explicit mapping to accepted finding
21, option A, of `agoge-2026-10-26.md`. This is the older packet's separate
restoration-documentation remedy, not the manifest fix already in PRD 00110.
Reports are local artifacts and are not shipped in the public repository.

## Problem

Purge-devtmp prunes empty parent directories after moving nested units to trash.
Its simple move-back instruction fails if the original parent no longer exists.
Operators must discover the missing directory-creation step themselves.

## Solution

Update restoration instructions to create the original parent before moving
the trashed file or directory back. Preserve pruning and all runtime behavior.

## Requirements

### Must have

- Place parent-directory creation before the restoration move.
- Cover both nested files and directory units.
- Use the documented manifest bases consistently with PRD 00106.
- Preserve pruning and existing age/protection behavior.
- Skip an already-corrected explanation after checking the premise at execution.

### Nice to have

- None.

## Implementation

```text
skills/purge-devtmp/SKILL.md  # create the original parent before restoring
```

### Module: restore instructions

- **Location**: `skills/purge-devtmp/SKILL.md`
- **Maps-to-capability**: restore nested trash units with an executable instruction sequence.
- **Responsibility**: state the missing parent-creation precondition first.
- **Exports**: none.

#### Feature: restore a nested unit

- **Inputs**: manifest source/destination and a possibly absent original parent.
- **Outputs**: instructions that restore the unit to its original path.
- **Behavior**: create the original parent, then move the trashed unit back.

### Dependencies

- Restore instructions: current trash/manifest conventions (foundation).
- No runtime changes or new dependencies are introduced.

## Tasks

### Phase 0: Foundation

- [ ] Premise: restoration instructions still omit parent creation. Re-check
  current prose; skip an already-corrected passage. Otherwise put parent creation
  before the move, using a concise ordered sequence and correct path bases.
  Acceptance: follow the instructions in a temporary nested-path example whose
  original parent is absent; the unit returns intact to the original path.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/purge-devtmp`,
and `braid --check` pass. No new prose-assertion tests are needed.

## Success Criteria

- Documented restoration works when original parent directories were pruned.
- Runtime cleanup and manifest behavior remain unchanged.

### Test Strategy

Verbatim older-report evidence:

```text
After trashing `sub/deep/fx2`: `ls tmp/sub` -> no such dir. `mv .trash/.../sub/deep/fx2 sub/deep/fx2` -> rc 1.
```

### Risks

Readers must follow the documented order and interpret manifest path bases
correctly. Preserve the current shared-format explanation while adding the precondition.

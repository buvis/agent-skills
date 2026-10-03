---
default_model: sonnet
model_tier_rationale: one-line guard with an authored xfail to flip
design: skip
---

# braid follows a symlinked skill directory to a target outside the source tree

## Problem

`discover_inventory` in `src/agent_skills_braid/cli.py` treats a symlink as a
directory (`candidate.is_dir()` is true through the link) and records its
resolved target, so a link planted in a configured source tree projects a
directory that lives anywhere on disk into the agents root. Bounded: the target
must hold a `SKILL.md` whose `name:` equals the link name, and writing into a
source tree already implies more access than this grants. Source: agoge run
`dev/local/audit-results/agoge-2026-09-05.md`, finding 14 (LOW, security lane,
verified); decision 2026-09-05: skip symlinked candidates. Strict xfail landed
on master in a550262.

```
srcA/skills/evil -> /private/tmp/outside; braid --dry-run --source srcA:
WOULD LINK <S>/braid/agents/skills/evil -> /private/tmp/outside, exit 0,
nothing written.
```

## Solution

In `discover_inventory`, `continue` past any candidate for which
`candidate.is_symlink()` is true, before the `is_dir()` check. The drop is
silent by decision (the option's named drawback): an operator who symlinks
skills into a source tree loses them from the inventory.

## Requirements

### Must have

- A symlinked entry directly under a source's `skills/` is not inventoried, in
  `--dry-run`, `--check` and sync.
- Real directories are inventoried exactly as today.
- The xfail marker on
  `test_a_symlinked_skill_directory_outside_the_source_is_not_inventoried` in
  `tests/test_braid.py` is deleted.

### Nice to have

- none

## Implementation

### Module: cli.py

- **Location**: `src/agent_skills_braid/`
- **Responsibility**: Inventory only real skill directories.
- **Exports**: `discover_inventory()`, unchanged signature

### Module: test_braid.py

- **Location**: `tests/`
- **Responsibility**: Pin the skip.
- **Exports**: pytest cases

### Dependencies

- cli.py: No dependencies (foundation)
- test_braid.py: Depends on [cli.py]

## Tasks

### Phase 0: Foundation

- [ ] Add `if candidate.is_symlink(): continue` at the top of the per-candidate loop in `discover_inventory` - Acceptance: delete the `xfail` marker on `test_a_symlinked_skill_directory_outside_the_source_is_not_inventoried`; `uv run pytest tests -q` reports 0 failing with that test passing, and every other test in `tests/test_braid.py` unchanged.

### Phase 1: Core

- none

## Success Criteria

- The authored test passes without its marker; the rest of `tests/test_braid.py`
  is unchanged and green.
- The report's reproduction prints no `WOULD LINK` line for the symlink.

---
design: skip
default_model: sonnet
model_tier_rationale: bounded non-following link enumeration with age, target-preservation, and trash-lifecycle regressions
---

# Cleanup silently ignores symlinks to directories

Source: agoge report `dev/local/audit-results/agoge-2026-10-25.md`, finding 23,
accepted option A on 2026-10-29. Reports are local audit artifacts and are not
shipped in the public repository.

## Problem

The temporary-store walker does not follow directory symlinks, but never yields
the links from the directory list either. Old links therefore disappear from
classification and counts, accumulating without the operator seeing them in
cleanup previews.

## Solution

Yield directory symlinks as individual link entries using their own lstat
modification time. Keep traversal non-following. Classify and move eligible
link objects using the existing trash/manifest behavior while leaving targets intact.

## Requirements

### Must have

- Directory symlinks appear exactly once in classification and preview counts.
- Link age comes from lstat, independent of target modification times.
- Never descend into target directories or move/delete their contents.
- Apply moves the eligible symlink itself, preserving link text and target data.
- Fresh and live-PRD-linked symlinks retain existing protection rules.
- Preserve .trash exclusion, ordinary files, dangling links, and nested-repository
  units without duplicate traversal or expanded target scope.
- Manifest destinations identify the trashed link, and later batch expiry leaves
  its outside target and contents untouched.
- Keep dry-run read-only and preserve existing unsafe-filename refusals.

### Nice to have

- None.

## Implementation

```text
skills/purge-devtmp/scripts/
├── purge_devtmp.py       # enumerate symlink objects from the directory list
└── test_purge_devtmp.py  # link age, preview/apply, and target-preservation checks
```

### Module: temporary-store link enumeration

- **Location**: `skills/purge-devtmp/scripts/purge_devtmp.py`
- **Maps-to-capability**: classify stale directory links without touching their targets.
- **Responsibility**: yield link entries with their own metadata and retain non-following traversal.
- **Exports**: `walk_store`, `process_store`, `trash_file`, `empty_old_trash`.

#### Feature: clean up a directory symlink safely

- **Inputs**: directory-list entries, link lstat metadata, and existing classification rules.
- **Outputs**: visible classification and eligible moves of link objects only.
- **Behavior**: handle the link independently from its target through preview,
  trash movement, manifest recording, and subsequent batch expiry.

### Module: directory-link regressions

- **Location**: `skills/purge-devtmp/scripts/test_purge_devtmp.py`
- **Maps-to-capability**: prove target directories remain outside cleanup scope.
- **Responsibility**: exercise distinct link/target ages and complete trash lifecycle.
- **Exports**: none.

### Dependencies

- Link enumeration: existing walker, classification, and trash lifecycle (foundation).
- Tests: depend on actual isolated symlink objects and portable filesystem fixtures.
- Preserve PRD 00132's originating-repository protection and PRD 00110's manifest safety.

## Tasks

### Phase 0: Foundation

- [ ] Add a failing preview regression for an old directory symlink, then yield
  it using lstat without traversal. Test old-link/fresh-target and fresh-link/old-target
  cases, a protected live-PRD link, and exact-once counts. In apply, assert the
  link moves and retains its text while the target sentinel stays unchanged.
  Expire the trash batch and assert the target survives. Retain ordinary-file,
  dangling-link, nested-unit, and dry-run controls. Use existing portable fixtures
  rather than broad platform skips. Acceptance:
  `uv run pytest skills/purge-devtmp/scripts/test_purge_devtmp.py` passes; the
  missing-directory-link preview regression fails against prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/purge-devtmp`,
and `braid --check` pass.

## Success Criteria

- Old directory links become visible and eligible according to their own metadata.
- Moving or expiring a link never changes the target's files.
- Existing protection, manifest, and non-following behavior remains intact.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
40-day-old `homelink -> <S>/home`: preview `trash=1 ... stale-temp: oldlink` only; `homelink` appears in no count.
```

Every source, link, and outside sentinel belongs under temporary test roots.

### Risks

Accidentally resolving a candidate before moving it could target real data rather
than the link. Relative links may not resolve while inside trash, so preserve
their original text for correct restoration rather than rewriting destinations.

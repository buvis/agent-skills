---
design: skip
default_model: sonnet
model_tier_rationale: bounded repository/store association fix with symlinked-store protection regressions
---

# A linked temporary store loses protection for live PRD notes

Source: agoge report `dev/local/audit-results/agoge-2026-10-25.md`, finding 5,
accepted option A on 2026-10-29. Reports are local audit artifacts and are not
shipped in the public repository.

## Problem

Purge-devtmp resolves a temporary store to its physical destination before
locating active PRDs by parent directories. When docs/dev/tmp is a symlink,
the lookup occurs beside the target instead of in the originating repository.
Notes linked to active work can be classified as stale and eventually deleted
after entering trash.

## Solution

Carry the originating repository context independently of the resolved store.
Find live PRD numbers from that repository, then classify files in the physical
store using the correct protection set. Preserve intentional symlinked stores
and existing trash locations and expiry behavior.

## Requirements

### Must have

- Locate backlog, wip, and hold PRDs in the originating repository even when
  its temporary store points elsewhere.
- Do not infer repository identity solely from the resolved store's parents.
- Preserve repository/store association through explicit --repo and --all discovery.
- Support both accepted repo-root and logical docs/dev/tmp input forms.
- Linked-store notes for live PRDs are reported as live-linked and remain in place
  during apply, even when old enough to otherwise qualify as stale.
- Preserve normal unlinked-store behavior, nested-unit handling, dry-run semantics,
  and cleanup of genuinely stale unprotected candidates.
- Do not introduce the symlink-store prohibition proposed by options B/C.

### Nice to have

- None.

## Implementation

```text
skills/purge-devtmp/scripts/
├── purge_devtmp.py       # preserve originating repo independently of store realpath
└── test_purge_devtmp.py  # linked-store live-PRD and ordinary-store controls
```

### Module: repository-aware protection

- **Location**: `skills/purge-devtmp/scripts/purge_devtmp.py`
- **Maps-to-capability**: keep active-work notes protected in intentional linked stores.
- **Responsibility**: carry repository identity into live-PRD lookup and classification.
- **Exports**: `resolve_store`, `live_prd_numbers`, `process_store`, `main`.

#### Feature: protect live notes through a store symlink

- **Inputs**: originating repository, logical temporary-store path, physical target,
  and active PRD buckets.
- **Outputs**: classifications using the originating repository's live PRD numbers.
- **Behavior**: resolve the physical cleanup destination without replacing the
  repository context needed for protection.

### Module: linked-store regression tests

- **Location**: `skills/purge-devtmp/scripts/test_purge_devtmp.py`
- **Maps-to-capability**: prove linked and ordinary stores preserve the same live-work guard.
- **Responsibility**: exercise dry-run and apply with all paths isolated.
- **Exports**: none.

### Dependencies

- Repository-aware protection: existing store discovery and PRD classification (foundation).
- Tests: depend on repository/store association and temporary symlink fixtures.
- Existing manifest and age logic remain integration constraints.

## Tasks

### Phase 0: Foundation

- [ ] Add a failing regression with a repo whose docs/dev/tmp symlinks to a
  temporary outside destination and whose backlog contains the referenced PRD.
  Carry the original repo into live lookup instead of deriving it from realpath.
  Cover backlog/wip/hold protections, both explicit input forms, and --all discovery
  using a scratch home. Assert dry-run reports live-linked and apply leaves the
  protected note intact; ordinary old unprotected files retain normal behavior.
  Acceptance: `uv run pytest skills/purge-devtmp/scripts/test_purge_devtmp.py`
  passes; linked-store protection regressions fail against the prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/purge-devtmp`,
and `braid --check` pass.

## Success Criteria

- Intentional store symlinks do not disable live-PRD protection.
- Normal store discovery, classification, and trash behavior remain correct.
- Verification uses temporary repositories and destinations, never operator files.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Dry run: symlinked repo2 `trash=2 live-linked=0 ... stale-temp: 00042-notes.log` vs control repo3 `trash=0 live-linked=1`.
```

### Risks

Cleanup still operates in the external destination selected by an intentional
symlink; that is the accepted tradeoff. Discovery must retain the owning repo
instead of losing it during physical-store resolution. Preserve manifest changes
from PRD 00110 and restore documentation from PRD 00129.

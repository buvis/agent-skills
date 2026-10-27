---
design: run
default_model: sonnet
model_tier_rationale: ownership-state persistence ordering needs coordinated design and refusal/write-failure regression coverage
---

# Braid can remove links without updating its ownership records

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 22,
accepted option A on 2026-10-27. Related to finding 33 of the 2026-10-25 report,
which concerns unreadable state encoding and remains distinct. Reports are local
audit artifacts and are not shipped in the public repository.

## Problem

Braid can remove a managed union link, refuse a later changed host path, and
exit before persisting the completed removal. Its state then describes a link
that no longer exists. It also rewrites identical state during unchanged syncs,
causing failure on read-only installations. Operators face misleading ownership
records and unnecessary recovery work after a rare link conflict.

## Solution

Skip state writes when persisted state is unchanged, and persist successful
removals before later operations can fail. Coordinate the in-memory ownership
state across union and host operations so a later refusal cannot discard a
completed removal. Preserve all existing protections for changed or user-owned
paths and keep the current state format.

## Requirements

### Must have

- An unchanged sync with identical persisted state succeeds without attempting a
  state write, including when the agents root is read-only.
- Persist each successful removal before proceeding to a later operation that
  can refuse, without discarding unaffected ownership records.
- After the reported later refusal, persisted state no longer claims the already
  removed union link, while the changed host path remains protected.
- Preserve refusal for changed managed paths and protection of user-owned links
  and real directories. Do not automatically delete them as recovery.
- Preserve atomic state replacement and useful persistence-error diagnostics.
- Preserve real state-only changes, first-run initialization, and host/Kiro state.
- Check and dry-run modes remain read-only.

### Nice to have

- None.

## Implementation

```text
src/agent_skills_braid/cli.py  # coordinate ownership updates and skip identical writes
tests/test_braid.py           # partial-removal/refusal and unchanged-sync regressions
tests/test_braid_check.py     # check-mode read-only and ownership controls
```

### Module: Braid sync state

- **Location**: `src/agent_skills_braid/cli.py`
- **Maps-to-capability**: keep ownership records aligned with completed removals.
- **Responsibility**: persist incremental removals and avoid identical state rewrites.
- **Exports**: `run`, `_sync_links`, `_write_state`.

#### Feature: persist removal progress safely

- **Inputs**: previous ownership state, desired links, and completed sync operations.
- **Outputs**: ownership records reflecting successful removals, including after
  a later refusal; no write for an unchanged persisted state.
- **Behavior**: coordinate persistence before continuing past a removal, preserving
  all unaffected ownership and refusing changed paths as before.

### Module: sync persistence regressions

- **Locations**: `tests/test_braid.py`, `tests/test_braid_check.py`.
- **Maps-to-capability**: prove consistent ownership and read-only unchanged syncs.
- **Responsibility**: test partial progress, later refusal, and write-failure controls.
- **Exports**: none.

### Dependencies

- Braid sync state: existing ownership checks and atomic state writer (foundation).
- Sync persistence tests: depend on sync state and temporary host-root fixtures.
- Union and host operations share the coordinated state lifecycle (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add failing regressions for an early union removal followed by refusal
  of a changed host path, and for an unchanged sync with a read-only agents root.
  Coordinate state updates so completed removals survive the later refusal,
  and skip identical persisted-state writes. Assert actual link state and saved
  ownership after refusal, preservation of user-owned paths, and no state-write
  attempt for unchanged content. Cover state-only changes, first-run initialization,
  a persistence failure, and read-only check/dry-run modes. Use portable fixtures
  for permission denial rather than assuming POSIX chmod behavior on Windows.
  Acceptance: `uv run pytest tests/test_braid.py tests/test_braid_check.py` passes;
  the partial-removal and unchanged-read-only regressions fail against prior code.

Exit criteria: `uv run pytest` and `braid --check` pass.

## Success Criteria

- A later refusal cannot lose the recorded progress of a successful removal.
- An unchanged sync succeeds without writing identical state.
- User-owned and changed paths remain protected, and state-only updates still persist.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
A managed claude link replaced by a real directory while its source vanished: sync printed `REMOVE .../ag/skills/zz-two`, then `refusing to clean changed managed path`, exit 2. The state file was not updated, so the union link is gone but still recorded; reruns stayed refused until the directory was removed by hand. On a read-only agents root a sync with nothing to change failed: `cannot write Braid state ... Permission denied`, exit 2, no `.tmp` left. Held: `{"version": 2}` -> exit 2 for sync and `--check`; truncated/empty state -> `cannot read Braid state`, exit 2; after a source vanished, `--check` -> `MISMATCH STALE` (exit 1) and sync `REMOVE`; user-own link untouched; `chmod 444` state file replaced with no `.tmp`.
```

Every regression must supply all host and configuration roots under a temporary
directory. Never sync against the operator's actual link farms during reproduction.

### Risks

Ownership state prevents deletion of user links; losing or broadening ownership
while persisting partial progress would be more serious than the original defect.
Do not equate zero link changes with identical state when host or Kiro metadata
changes. Persistence failures need explicit handling without unsafe cleanup.

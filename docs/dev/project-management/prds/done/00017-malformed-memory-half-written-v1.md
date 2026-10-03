---
default_model: opus
model_tier_rationale: failure rollback must preserve existing persisted memories and their index
rework_cap: 5
catchup: force
design: skip
---

# A malformed memory still lands on disk before write.py reports the failure

## Problem

Part of this finding is already fixed on master: `_atomic_write` (`skills/distil-memory/scripts/write.py:31-38`)
now writes the memory file and `MEMORY.md` through a temp file, `write.py main` wraps `write_memory` in `except
WriteError` (lines 119-123), and `docket.py main` wraps `decide` in `except QueueError` (lines 212-216). Four
sites remain open. `write_memory` (`write.py:41-59`) never parses the frontmatter, so a malformed `file_text`
is written first and blows up second, inside `append_pointer`, which calls `proposal.parse_frontmatter` at
`write.py:80` and raises `ProposalError`. The `append_pointer` call itself sits at `write.py:125`, outside that
try, so any index failure escapes as a traceback with the memory file already on disk and the queue recording
the proposal as `kept`. Two `docket.py` reads are still unguarded: `_save_from_proposals_dir` at line 177 and
the `decide --file` read at line 211, one line above the try that guards `decide`. Every one of those routes
contradicts `CHANGELOG.md:27-29` and `SKILL.md:193-195`, and the documented re-run recovery
(`SKILL.md:194-198`) is refused with "already exists", which `SKILL.md:204-207` then mis-diagnoses as a name
collision. Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 7 (HIGH, merged integration
and release lanes); decision 2026-09-02: validate before writing, and guard the whole operation.

```
`confirmed`. `write.py write` printed the written path, then
`ProposalError: file does not open with a --- frontmatter marker` as a raw
traceback, with `on disk: ['probe-partial.md']` and `MEMORY.md` never updated.
```

## Solution

Validate first: `write_memory` calls `proposal.parse_frontmatter` before it touches the disk and turns a
`ProposalError` into a `WriteError`, so a malformed proposal leaves nothing behind. Then make the index update
part of the guarded operation, so an `append_pointer` failure exits 1 with its reason on stderr and restores
the pre-operation store: remove a newly created memory, but restore an updated memory's original bytes.
The index retains its original bytes or original absence on failure. Finally guard `docket.py`'s two remaining read sites with `except
(OSError, json.JSONDecodeError)` returning 1. The docs already describe the intended behaviour, so `SKILL.md`
and `CHANGELOG.md` do not change: the implementation moves to meet them.

## Requirements

### Must have

- `write_memory` parses `entry["file_text"]`'s frontmatter before any write and raises `WriteError` carrying
  the `ProposalError` message when it will not parse; no file is created.
- An `append_pointer` failure in `write.py main` returns 1 with the reason on stderr. For a new memory,
  remove only the newly created target; for an update, restore the original target bytes. Preserve the
  original index bytes or its original absence. A retry succeeds once the index fault is removed.
- Snapshot/validation failures before mutation leave both files untouched. If a rollback operation itself
  fails, exit 1 naming both the original and rollback errors; never claim restoration succeeded.
- `docket.py save --proposals-dir <missing>` returns 1 with the message on stderr instead of raising, covering
  both reads in `_save_from_proposals_dir` (`proposals.json` at line 177, each record's sibling at line 185).
- `docket.py decide <id> kept --file <missing>` returns 1 with the message on stderr instead of raising.
- No change to `SKILL.md` or `CHANGELOG.md`.

### Nice to have

- none

## Implementation

### Module: write
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: writing an approved proposal into the store and its `MEMORY.md` pointer
- **Exports**: `write_memory()`, `append_pointer()`, `main()`

### Module: docket
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: queue persistence and the CLI the walkthrough drives
- **Exports**: `_save_from_proposals_dir()`, `main()`

### Module: test_write
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: the write path's regression suite
- **Exports**: `test_an_index_that_cannot_be_read_leaves_no_memory_file_behind`

### Module: test_docket
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: the queue's regression suite, including its CLI wiring
- **Exports**: the `main()` CLI tests at `test_docket.py:402-727`

### Dependencies
- PRDs 00015 and 00016: preserve their corruption exit codes and explicit/derived queue paths.
- write: No dependencies (foundation)
- docket: No dependencies (foundation)
- test_write: Depends on [write]
- test_docket: Depends on [docket]

## Tasks

### Phase 0: Foundation

- [ ] Validate the frontmatter in `write_memory` before writing - Acceptance: `uv run pytest
  skills/distil-memory/scripts/test_write.py -q` passes with a new test that calls `store_path.mkdir()`, feeds
  `write.main(["write", "--store", str(store_path)])` an entry whose `file_text` is `"no frontmatter here\n"`,
  and asserts the status is 1, stderr contains `file does not open with a --- frontmatter marker`, and
  `list(store_path.iterdir()) == []`.
- [ ] Bring the `MEMORY.md` update inside the guarded operation - Acceptance: `uv run pytest
  skills/distil-memory/scripts/test_write.py::test_an_index_that_cannot_be_read_leaves_no_memory_file_behind
  -q` passes without its expected-failure marker; re-check that marker before removal, skipping only
  its deletion if already absent. `uv run pytest skills/distil-memory/scripts/test_write.py -q` also
  passes regressions for an existing update target and existing/absent index: inject index failure,
  assert original bytes/absence are restored, then remove the fault and retry successfully. A separate
  injected rollback failure returns 1 and names both errors instead of reporting success.

### Phase 1: Core

- [ ] Guard `_save_from_proposals_dir`'s reads (depends on: Phase 0) - Acceptance: `uv run pytest
  skills/distil-memory/scripts/test_docket.py -q` passes with new tests asserting `docket.main(["save",
  "--proposals-dir", str(tmp_path / "gone")]) == 1` with non-empty `capsys` stderr, and the same exit and
  stderr when `proposals.json` holds `not json at all` and when a record names a `file` that is absent.
- [ ] Guard the `decide --file` read (depends on: Phase 0) - Acceptance: `uv run pytest
  skills/distil-memory/scripts/test_docket.py -q` passes with a new test asserting `docket.main(["decide",
  entry_id, "kept", "--file", str(tmp_path / "gone.md")]) == 1`, non-empty `capsys` stderr, and the entry still
  `undecided` in `docket.load()`.

## Success Criteria

- `uv run pytest skills/distil-memory/scripts -q` reports no failures; the index-write regression
  passes without an expected-failure marker. Unrelated future expected failures are outside this PRD.
- None of the four routes (malformed `file_text`, an unreadable `MEMORY.md`, `save --proposals-dir <missing>`,
  `decide --file <missing>`) prints a traceback; each exits 1 with its reason on stderr, which is what
  `CHANGELOG.md:27-29` already claims.
- A failed write leaves the store as it was, so the `SKILL.md:194-198` re-run recovery succeeds instead of
  hitting "already exists".

## Post-completion notes (2026-09-06)

Converged in review cycle 2 (batch 202609050909, 7 tasks, $226 on opus for both phases). The 18 deferred
rows were walked on 2026-09-06 in the config-audit closure walkthrough
(`~/.claude/dev/local/audit-results/2026-09-05.md`); the ledger's decision fields get backfilled at batch end.

- Stale text, accepted as built: the docket read sites cited above as lines 177/185/211 sit at `docket.py:207`,
  `:218` and `:250` after PRDs 00016 and 00017; the Phase 0 index test moved to `test_write_crash_safety.py`
  (split commit `04c6a04`) and the CLI-level task-1 scenario lives in `test_write_cli.py`; the Phase 1
  refusal tests live in `test_docket_refusals.py` (split `be34106`), while task 3's new tests were appended to
  `test_docket.py` as the acceptance literally named it. `test_docket_exit_codes.py:224` changed its assertion
  from `pytest.raises(FileNotFoundError)` to exit 1 plus stderr; the rule it enforces (a bad `--file` never
  exits 2) is unchanged.
- Test weaknesses (Devon cap on tasks 1 to 4, the atomic-write coverage gap, the parametrize nit): PRD 00076.
- Docket exception contract (UnicodeDecodeError at both read sites, schema faults, the dead JSON arm on the
  text read, the unguarded `_save_queue` write): PRD 00077.
- A null `kind` in the entry envelope escaping `write.py main` as an AttributeError: folded into PRD 00071.
- `_probe_failing_on` factory with one call site: accepted, it mirrors `_replace_failing_on_index`.

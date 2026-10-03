# Distil Memory Candidates: Queue, Cursor and Walkthrough

Source: `~/.claude/dev/local/discovery/00147-distil-memory-from-transcripts.md`
(comprehensive, 2026-08-26). Slice 3 of 3: the persisted proposal queue, the
cursor, the rejection record and the one-at-a-time approval walkthrough that
actually writes memory. Depends on slice 2 (`00008`), which produces the
proposals, and through it on slice 1 (`00007`).

## Overview

### Problem Statement

Slices 1 and 2 end with typed, evidenced proposals and nothing that turns them
into memory. The approval shape is settled: one at a time, keep / edit / drop,
no bulk approve, because bulk approval invites rubber-stamping and that is how a
low-quality entry reaches memory. That decision has a cost the design has to
absorb rather than argue away - a sweep can produce more proposals than one
sitting can decide, and a session ends. Without a persisted queue the batch is
lost; without a cursor `--all` over 2,371 transcripts can never be drained;
without a rejection record the same dropped proposal returns on the next run over
the same window.

### Target Users

The solo maintainer, deciding proposals in chat, across more than one sitting.

### Success Metrics

- Interrupting a walkthrough and re-invoking resumes at the next undecided
  proposal, with no duplicates and no skips.
- A dropped proposal does not reappear on a second run over the same window.
- `--all` over 2,371 transcripts stays within its per-run cap and leaves a cursor
  that a second run advances.
- An approved proposal produces a memory file that passes the same frontmatter
  contract as the existing 70, plus its `MEMORY.md` pointer line.

## Functional Decomposition

### Capability: Queue and resumption

#### Feature: Persist the proposal queue

- **Description**: Survive the end of a session.
- **Inputs**: The proposals emitted by slice 2.
- **Outputs**: A queue file holding each proposal, its evidence, and its decision
  state (`undecided` / `kept` / `dropped`).
- **Behavior**: Written before the walkthrough starts, updated after every
  decision, so an interrupted sitting loses nothing. Python, stdlib only,
  matching the surrounding scripts.

#### Feature: Advance a cursor across runs

- **Description**: Make full history drainable.
- **Inputs**: The queue and the per-run cap.
- **Outputs**: A cursor marking how far the corpus has been consumed.
- **Behavior**: The per-run cap is 10 proposals - a starting number with no data
  behind it yet, to be tuned after the first real run. The cursor is load-bearing
  twice: it makes `--all` drainable over several capped runs and it makes the
  walkthrough resumable.

#### Feature: Record rejections so drops stay dropped

- **Description**: Never re-ask a settled question while the question is the
  same.
- **Inputs**: A dropped proposal.
- **Outputs**: A rejection record keyed on the proposal's source slice plus the
  distiller rubric version.
- **Behavior**: A dropped proposal never comes back while the rubric that judged
  it is current. Changing the rubric version re-opens its drops, which is the
  intended behavior: a better rubric deserves a second look at what the old one
  rejected.

### Capability: Approval walkthrough

#### Feature: Decide one proposal at a time

- **Description**: Keep, edit, or drop, individually.
- **Inputs**: The next undecided proposal, with its evidence.
- **Outputs**: A recorded decision.
- **Behavior**: No bulk approve and no multi-select. Each proposal is shown with
  its evidence and, for an `update`, the existing memory's text beside the
  proposed one. This follows `rules/communication.md`: findings that need a
  decision are walked one at a time.

#### Feature: Re-emit on edit and re-check

- **Description**: Let a correction produce a valid file, not a patched one.
- **Inputs**: The user's correction, stated in chat.
- **Outputs**: A re-emitted complete memory file.
- **Behavior**: On edit the distiller re-emits the whole file, and the result is
  re-checked against the frontmatter contract before it is written. A hand-patched
  fragment is never written.

### Capability: Memory write

#### Feature: Write approved entries and their index line

- **Description**: Land the fact where future sessions will see it.
- **Inputs**: An approved proposal.
- **Outputs**: A file in the target project's `~/.claude/projects/<hash>/memory/`
  plus a one-line pointer appended to that store's `MEMORY.md`.
- **Behavior**: No automatic write anywhere: nothing reaches a memory directory
  without an explicit per-entry decision, and there is no always-on hook - this
  is invoked, never triggered. An `update` proposal replaces the named file and
  touches `MEMORY.md` only if the description changed. The target directory is
  the project whose transcript carried the fact; the path is taken from that
  transcript's own location, never computed from a repo name - the retired
  pipeline died of a computed delivery path.

#### Feature: Report the run's outcome

- **Description**: Close the loop out loud.
- **Inputs**: The decisions made this run.
- **Outputs**: Counts of kept, edited and dropped, the cursor position, and the
  files written, into `dev/local/audit-results/` with the verbatim
  how-to-proceed block.
- **Behavior**: Every run reports its yield, including a run that wrote nothing.

## Structural Decomposition

### Repository Structure

```
skills/
└── distil-memory/
    ├── SKILL.md                  # Updated: the walkthrough stage
    └── scripts/
        ├── queue.py              # Maps to: Queue and resumption
        ├── write.py              # Maps to: Memory write
        ├── test_queue.py
        └── test_write.py
```

### Module: queue.py

- **Maps to capability**: Queue and resumption
- **Responsibility**: Persist proposals and decisions, advance the cursor, hold
  the rejection record.
- **Exports**:
  - `save(proposals)` / `next_undecided()` / `decide(id, state)`
  - `cursor()` / `advance(cursor)`
  - `rejected(slice_key, rubric_version)` - `True` when a drop still stands

### Module: write.py

- **Maps to capability**: Memory write
- **Responsibility**: Write an approved proposal into the right store and append
  its index line.
- **Exports**:
  - `write_memory(proposal, store_path)` - the written file path
  - `append_pointer(store_path, proposal)` - the `MEMORY.md` line

### Module: distil-memory SKILL.md walkthrough stage

- **Maps to capability**: Approval walkthrough
- **Responsibility**: The keep / edit / drop protocol, the re-emit-on-edit rule,
  and the run report.
- **Exports**: The walkthrough contract and the how-to-proceed block.

## Dependency Graph

### Foundation Layer (Phase 0)

- **queue.py**: Depends on [PRD 00008's proposal record]. Everything else in this
  slice reads or writes the queue.

### Core Layer (Phase 1)

- **write.py**: Depends on [queue.py]

### Integration Layer (Phase 2)

- **distil-memory SKILL.md walkthrough stage**: Depends on [queue.py, write.py]

## Implementation Phases

### Phase 0: Foundation

**Goal**: Decisions survive a session end.

**Tasks**:

- [ ] Implement `scripts/queue.py` with save, next-undecided, decide, and the
  cursor (depends on: PRD 00008 Phase 1)
  - Acceptance: after deciding two of five proposals and reloading,
    `next_undecided()` returns the third; no proposal is returned twice.
- [ ] Implement the rejection record keyed on source slice plus rubric version
  (depends on: PRD 00008 Phase 1)
  - Acceptance: a dropped proposal is filtered out on a second run over the same
    window; bumping the rubric version makes it eligible again.
- [ ] Enforce the per-run cap of 10 (depends on: PRD 00008 Phase 1)
  - Acceptance: a queue of 25 proposals yields 10 in one run and leaves a cursor
    that a second run advances past them.

**Exit Criteria**: `uv run --with pytest pytest scripts/test_queue.py` passes
with zero failures.

### Phase 1: Core

**Goal**: An approved proposal becomes a real memory file.

**Tasks**:

- [ ] Implement `write_memory()` and `append_pointer()` in `scripts/write.py`
  (depends on: Phase 0)
  - Premise: the target store is `~/.claude/projects/<hash>/memory/` with a
    sibling `MEMORY.md`, and the path comes from the source transcript's own
    location. Re-check at execution; if the resolved store does not exist, stop
    and report rather than creating a directory.
  - Acceptance: a written file passes the frontmatter contract, and exactly one
    pointer line is appended to `MEMORY.md`.
- [ ] Handle the `update` case (depends on: Phase 0)
  - Acceptance: an `update` proposal replaces the named file and leaves
    `MEMORY.md` unchanged when the description did not change.

**Exit Criteria**: `uv run --with pytest pytest scripts/test_write.py` passes
with zero failures, against a temporary store.

### Phase 2: Integration

**Goal**: The queue, the cursor and the write path survive a full pass without a
human in the room.

**Tasks**:

- [ ] Extend `SKILL.md` with the walkthrough: one proposal at a time, keep / edit
  / drop, re-emit on edit and re-check, no bulk approve, plus the run report and
  the verbatim how-to-proceed block (depends on: Phase 1)
  - Acceptance: the create-skill validator still passes; the skill states it
    never writes without a per-entry decision and never fires unasked.
- [ ] Drive a seeded queue through a scripted decision sequence against a
  temporary store under `dev/local/tmp/` (depends on: Phase 1)
  - The walkthrough asks the user to keep, edit or drop every proposal, which an
    unattended run cannot answer, and the real store sits outside the write
    fence. Calling `decide()` directly with a scripted sequence exercises the
    queue, the cursor, the rejection record and the write path without either.
  - Acceptance: at least one memory file plus its pointer line is written from a
    kept proposal; a dropped proposal does not reappear on a second pass over the
    same window; stopping after two of five decisions and reloading resumes at
    the third, with no duplicates and no skips.

**Exit Criteria**: A seeded batch produces written memory files in a temporary
store, and the run says how many were kept, edited and dropped.

**Attended follow-up** (not part of this PRD, run by hand after it ships): walk
one real single-project batch in chat, one proposal at a time, which is the first
write into a live memory store.

## Test Strategy

### Critical Scenarios

- **Happy path**: five proposals, three kept → three memory files, three pointer
  lines, counts reported.
- **Happy path**: an edit → the whole file is re-emitted and re-validated before
  writing.
- **Edge case**: the session ends mid-walkthrough → re-invoking resumes at the
  next undecided proposal, no duplicates, no skips.
- **Edge case**: `--all` with 25 proposals and a cap of 10 → 10 this run, cursor
  advanced, the rest reachable next run.
- **Error case**: a re-emitted file failing the frontmatter contract → not
  written, and the proposal stays undecided.
- **Error case**: the resolved memory store does not exist → stop and report; no
  directory is created and no path is computed from a repo name.

## Risks

- **The walkthrough becomes a chore** at scale: mitigated by the per-run cap and
  the resumable queue, which is how the one-at-a-time decision was made
  affordable instead of argued away.
- **Memory bloat**: dozens of approved entries could swell the always-loaded
  `MEMORY.md`. Mitigation: one line per memory, and the walkthrough is the
  throttle. Revisit if a store passes ~100 entries.
- **A computed delivery path**: the exact failure that killed the retired
  pipeline. Mitigation: the store path comes from the source transcript's own
  location, and a missing store stops the run.
- **Two writers of the memory plane**: the `encode-incident` skill (`~/.claude`
  PRD 00156) writes `feedback` memories through its own path. Settled split rather than
  a deferred one: this feature writes `project` memories only, that one writes
  `feedback` only, and neither rewrites the other's type.
- **The per-run cap of 10 is a guess**: no basis for a number yet, tuned after
  the first real run.

## Post-completion notes (2026-09-05)

Deferred by batch 202608290848 (cycle 2), decided 2026-09-05 in
`dev/local/audit-results/deferred-walk-202608290848-2026-09-05.md`.

- Phase 2's acceptance text names a temporary store under `dev/local/tmp/`;
  `test_walkthrough_integration.py` uses pytest's `tmp_path`. Equivalent; the
  PRD text is corrected by this note.
- `docket.py decide` and `advance` carry `file_text`, `path` and `new_cursor`
  beyond the Exports signatures: required by the spec's own re-emit-on-edit
  feature and temp-store testing. The Exports are corrected by this note.
- The publication-recovery defects the rework cap left open (already-exists
  rename, pointer-failure retry, kept-but-unpublished entries) are PRD 00071;
  the four hollow tests are PRD 00074. The symlink-escape and hand-maintained
  `RUBRIC_VERSION` findings stay rejected as settled at review; the corrupt
  `queue.json` traceback was fixed by PRD 00017.

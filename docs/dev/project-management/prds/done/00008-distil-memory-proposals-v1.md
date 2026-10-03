---
default_model: opus
rework_cap: 5
---

# Distil Memory Candidates: Distiller and Deduplication

Source: `~/.claude/dev/local/discovery/00147-distil-memory-from-transcripts.md`
(comprehensive, 2026-08-26). Slice 2 of 3: the strong-model distiller, the
proposal schema, and deduplication against existing memory. Depends on slice 1
(`00007`, extraction and funnel); slice 3 (`00009`) consumes the proposals.

## Overview

### Problem Statement

Slice 1 ends with twice-filtered slices: assistant-authored text that carries a
verification marker and survived cheap triage. That is recall, not precision.
Measured on 406 transcripts, most marker hits are transient process
verifications with no durable value ("Red confirmed as expected", "all 264 tests
pass"); a minority are durable facts ("`notify.py` has zero autopilot
coupling"). Telling those apart is genuine model work rather than formatting, and
nothing does it today. A proposal also has to know whether the fact is already
in memory, because the `MEMORY.md` index carries hooks rather than content, so a
naive index check cannot tell a new fact from a restatement.

### Target Users

The solo maintainer, between the funnel and the approval walkthrough - reading
proposals rather than transcripts.

### Success Metrics

- No proposal's `description` restates its `**How to apply:**` line; a proposal
  whose recall cue and content are the same sentence is rejected before it
  reaches the queue, with a test proving it.
- Every proposal carries the transcript evidence it came from, so it can be
  judged without reopening the session.
- Every proposal is typed `new` or `update <existing-name>`.
- A proposal that reaches the queue produces a memory file passing the same
  frontmatter contract as the existing 70.

## Functional Decomposition

### Capability: Distillation

#### Feature: Judge durable against transient

- **Description**: Decide whether a slice holds a fact worth carrying between
  sessions.
- **Inputs**: One twice-filtered slice with its source transcript and offset.
- **Outputs**: Either a proposal, or a reasoned discard.
- **Behavior**: The negative class is well evidenced - transient test-pass
  verifications. The positive class is anchored on the existing 70 memories as
  few-shot examples. Strong-model work by design; this is the one step in the
  feature that code cannot answer, and it reads only slices that already passed
  two filters.

#### Feature: Emit a complete memory file, not a fragment

- **Description**: Produce something writable, not a suggestion.
- **Inputs**: The judged slice.
- **Outputs**: A full memory file: frontmatter (`name`, `description`,
  `metadata.type`), body, and `[[links]]` to related memories.
- **Behavior**: Proposals conform to the fixed auto-memory contract in
  `rules/memory.md`; they never invent a format. The memory plane has two
  writers and one settled split: this feature emits `project` memories only, and
  the human-run `encode-incident` skill (`~/.claude` PRD 00156) emits `feedback`
  memories only. Neither reads or rewrites the other's type, so no reconciliation
  is owed at ship time. Corrections as a second signal stay out of scope: their
  measured yield is thin (11 raw matches across 8 files) and no detector,
  criterion or funnel stage is specified for them.

#### Feature: Reject a proposal whose cue restates its content

- **Description**: Keep the index useful.
- **Inputs**: The emitted file.
- **Outputs**: Kept, or rejected with the reason.
- **Behavior**: `description` is a recall cue; `**How to apply:**` is the
  content. When they are the same sentence the proposal is the tautology shape
  that made the retired pipeline worthless, and it is rejected before it can
  reach the queue.

### Capability: Deduplication

#### Feature: Shortlist from the index, then read the files

- **Description**: Find out whether this fact is already known.
- **Inputs**: The target project's `MEMORY.md` and its memory directory.
- **Outputs**: A shortlist of candidate existing memories, then a decision.
- **Behavior**: The index carries hooks, not content, so it can only shortlist.
  The distiller then reads the shortlisted memory files themselves before
  deciding. Reading every memory on every proposal is the cost this two-step
  avoids.

#### Feature: Type the proposal new or update

- **Description**: Say what should happen to it.
- **Inputs**: The dedup decision.
- **Outputs**: `new`, or `update <existing-name>`.
- **Behavior**: An update proposal carries both the existing file's content and
  the proposed replacement, so the walkthrough in slice 3 can show the difference
  without reopening anything. Cross-project routing stays out of scope: a fact
  established about repo B during a session in repo A is proposed into A's
  memory, because the model guessing the target repo is the same class of mistake
  as the encoder bug that was just retired.

### Capability: Evidence

#### Feature: Carry the source slice with every proposal

- **Description**: Make a proposal judgeable on its own.
- **Inputs**: The slice's transcript path, offset and text.
- **Outputs**: An evidence block attached to the proposal.
- **Behavior**: Enough to judge without reopening the session, and short enough
  that a walkthrough stays readable.

## Structural Decomposition

### Repository Structure

```
skills/
└── distil-memory/
    ├── SKILL.md                  # Updated: the distil stage of the workflow
    └── scripts/
        ├── distil.py             # Maps to: Distillation, Evidence
        ├── dedup.py              # Maps to: Deduplication
        ├── proposal.py           # Maps to: the proposal schema and its checks
        ├── test_distil.py
        ├── test_dedup.py
        └── test_proposal.py
```

### Module: proposal.py

- **Maps to capability**: Distillation, Evidence
- **Responsibility**: The proposal record and every check that can be made
  without a model.
- **Exports**:
  - `Proposal` - file text, type (`new` / `update <name>`), evidence
  - `validate(proposal)` - frontmatter contract plus the cue-restates-content
    rejection

### Module: distil.py

- **Maps to capability**: Distillation
- **Responsibility**: The strong-model call - rubric, few-shot anchors, and the
  emission of a complete memory file. The call itself goes through
  `funnel.judge(prompt, tier)` from PRD 00007 at the strong tier; this module
  defines no second way to reach a model.
- **Exports**:
  - `distil(slice, examples, judge=funnel.judge)` - `Proposal` or a reasoned
    discard

### Module: dedup.py

- **Maps to capability**: Deduplication
- **Responsibility**: Shortlist from the index, read the shortlisted files, type
  the proposal.
- **Exports**:
  - `shortlist(index, proposal)` - candidate existing memory names
  - `classify(proposal, candidates)` - `new` or `update <name>`

## Dependency Graph

### Foundation Layer (Phase 0)

- **proposal.py**: Depends on [slice 1's funnel output shape]. Built first here,
  because both later modules produce or consume this record.

### Core Layer (Phase 1)

- **distil.py**: Depends on [proposal.py]
- **dedup.py**: Depends on [proposal.py]

### Integration Layer (Phase 2)

- **distil-memory SKILL.md distil stage**: Depends on [distil.py, dedup.py]

## Implementation Phases

### Phase 0: Foundation

**Goal**: A proposal is a checkable object before any model produces one.

**Tasks**:

- [ ] Implement `Proposal` and `validate()` in `scripts/proposal.py` (depends
  on: PRD 00007 Phase 1)
  - Acceptance: a proposal missing `name`, `description` or `metadata.type` is
    rejected naming the field; a proposal whose `description` and
    `**How to apply:**` line are the same sentence is rejected with that reason.
- [ ] Add the frontmatter-contract test against the real memory plane (depends
  on: PRD 00007 Phase 1)
  - Premise: `~/.claude/projects/-Users-bob--claude/memory/` holds 70 memory
    files plus `MEMORY.md`, with types `user | feedback | project | reference`.
    Re-check at execution and use the live count; a changed count updates the
    fixture, not the contract.
  - Acceptance: every existing memory file passes `validate()`, so the checker
    is calibrated against what already works rather than against an invention.

**Exit Criteria**: `uv run --with pytest pytest scripts/test_proposal.py` passes
with zero failures.

### Phase 1: Core

**Goal**: Slices become typed, evidenced proposals.

**Tasks**:

- [ ] Implement `distil()` with the durable-versus-transient rubric and the
  existing memories as few-shot anchors, calling the model only through
  `funnel.judge` from PRD 00007 (depends on: Phase 0)
  - Acceptance: on a fixture pair - "all 264 tests pass" and a durable fact -
    with a stub judge, the transient slice yields a discard with a reason and the
    durable one yields a complete file; no test reaches the default judge.
- [ ] Attach the evidence block to every proposal (depends on: Phase 0)
  - Acceptance: each emitted proposal carries the source transcript path, offset
    and slice text.
- [ ] Implement `shortlist()` and `classify()` in `scripts/dedup.py` (depends
  on: Phase 0)
  - Acceptance: a proposal restating an existing memory is typed
    `update <that-name>` and carries both texts; a genuinely new fact is typed
    `new`; the shortlist step reads the index and the decision step reads the
    shortlisted files, provable by a test that fails if every memory file is
    read.

**Exit Criteria**: `uv run --with pytest pytest scripts/test_distil.py
scripts/test_dedup.py` passes with zero failures.

### Phase 2: Integration

**Goal**: A real single-project run produces proposals a human would read.

**Tasks**:

- [ ] Extend `SKILL.md` with the distil stage, the type rule (`project`), and the
  out-of-scope statement for corrections and cross-project routing (depends on:
  Phase 1)
  - Acceptance: the create-skill validator still passes.
- [ ] Run the funnel plus distiller over one project and record the yield
  (depends on: Phase 1)
  - Acceptance: the run reports proposals emitted, discards with reasons, and the
    `new` / `update` split; every proposal passes `validate()`.

**Exit Criteria**: One project's 30-day window produces a set of typed, evidenced
proposals, and the report states how many and of what kind.

## Test Strategy

### Critical Scenarios

- **Happy path**: a durable fact slice → a complete memory file with
  frontmatter, body and `[[links]]`, typed `new`.
- **Happy path**: a slice restating an existing memory → typed
  `update <existing-name>` with both texts attached.
- **Edge case**: a proposal whose `description` restates its content → rejected
  before the queue, with a test pinning it.
- **Edge case**: an empty shortlist → the proposal is `new` without reading the
  whole memory directory.
- **Error case**: a malformed model response → a reasoned discard, never a
  half-written memory file.
- **Error case**: a proposal violating the frontmatter contract → rejected naming
  the field, since the existing 70 files are the calibration.

## Risks

- **Proposal quality is mediocre and the walkthrough becomes a chore**:
  mitigation is measuring on a single project first and reporting the yield; if
  precision is poor, the rubric is tuned before any sweep widens.
- **The distiller invents a memory format**: mitigated by validating every
  proposal against the same contract the existing 70 files pass.
- **Dedup reads too much and costs too much**: mitigated by the two-step
  shortlist-then-read, pinned by a test that fails on a full-directory read.
- **The tautology shape returns**: the cue-restates-content rejection exists
  specifically because that shape is what the retired pipeline produced.
- **Cross-project misrouting**: excluded rather than mitigated. A fact is
  proposed to the project whose transcript carried it, and the alternative is the
  same class of mistake as the encoder bug that was retired.

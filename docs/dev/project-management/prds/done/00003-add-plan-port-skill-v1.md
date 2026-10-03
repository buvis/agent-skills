---
design: skip
---

# Plan a Port and Retire the Original at Parity

Source: `~/.claude/dev/local/discovery/00152-plan-ports-to-parity.md`
(elicitation complete 2026-08-27, review 2026-08-28).

## Overview

### Problem Statement

Ports keep recurring and each one hand-derives the same artifacts: what the
source does, what the target must match, who consumes it, when the original may
die. Without a parity gate the original never dies - it lingers half-alive while
the replacement grows. pidash proves it: the machine side was decommissioned in
`~/.claude` PRD 00063 on 2026-07-14 and six weeks later `gems`
`00071-retire-pidash` still sits in the backlog with the original alive.

### Target Users

The solo maintainer, at the start of a port (the live case is
`brief-portfolio` → the gems `postup` gem) and again months later when the
original should die.

### Success Metrics

- Run against a fixture source whose matrix has no `drop` rows, the emitted plan
  carries a row for every command and flag that source documents, and names the
  condition under which the original may be deleted.
- Every matrix row carries a classification and a reason; a row without a reason
  is a defect, provable by reading the table.
- Every proposed `drop` appears in the plan with the user's recorded ruling.
- The phase list is dependency-ordered, and no phase depends on a later one.

## Functional Decomposition

### Capability: Feature inventory

#### Feature: Derive rows behavior-first

- **Description**: Build the feature list from what the source shows a user, not
  from its call graph.
- **Inputs**: The source's user-facing surface - commands, flags, inputs,
  outputs, README and `SKILL.md` promises.
- **Outputs**: One row per behavior.
- **Behavior**: Docs and surface first. The code is read afterwards only to catch
  behavior the docs never mention, and any row found only that way is marked
  `code-only`, because those are the rows nobody has judged yet.

### Capability: Parity matrix

#### Feature: Classify every row

- **Description**: Decide what happens to each behavior in the target.
- **Inputs**: The inventory rows.
- **Outputs**: A matrix: row, classification (`port` / `drop` / `redesign`),
  reason.
- **Behavior**: No row without a reason. A reasonless row is a defect the skill
  must catch before emitting the plan.

#### Feature: Walk the drops one at a time

- **Description**: Get a ruling on every proposed deletion.
- **Inputs**: The rows classified `drop`.
- **Outputs**: The user's recorded ruling per drop row, written into the plan.
- **Behavior**: `port` and `redesign` rows are presented as one table for a
  single approval; each `drop` gets an individual packet with evidence, per
  `rules/communication.md`. The asymmetry is deliberate - a wrong `port` costs
  effort, a wrong `drop` costs a feature. Before the first drop packet the skill
  says once, and only once, that a port producing more than a screen of drops is
  probably too big for one plan; splitting stays the user's call.

### Capability: Cutover and retirement

#### Feature: Analyse consumers and cutover

- **Description**: Name who calls the source today and what breaks when it dies.
- **Inputs**: The source's call sites across the portfolio.
- **Outputs**: A consumer list with a cutover row each - what must be repointed
  before the original can be deleted.
- **Behavior**: Read-only. The skill reports consumers; it repoints nothing.

#### Feature: Emit a dependency-ordered phase list

- **Description**: Say what order the port happens in.
- **Inputs**: The matrix and the consumer list.
- **Outputs**: Named phases in dependency order, with each phase's dependencies
  stated.
- **Behavior**: Phases only - no PRDs, no numbers claimed. `create-prd` writes
  the actual PRDs one phase at a time, and numeric order must equal execution
  order because autopilot drains by lowest sequence number.

#### Feature: Carry a retirement block

- **Description**: Make the original's death checkable rather than felt.
- **Inputs**: The matrix's `port` rows.
- **Outputs**: A retirement section holding the matrix plus one ready-made
  acceptance criterion per `port` row, in `create-prd`'s criterion shape, ending
  with a hand-off line telling `create-prd` to lift the block verbatim into the
  retirement PRD.
- **Behavior**: The block is written so it needs no `create-prd` edit to be
  usable - it is already in criterion shape and the hand-off line names the lift.
  The retirement PRD belongs to the repo where the code dies (the source repo);
  the plan says so, and says it is written alongside the final port phase rather
  than remembered later, which is exactly where pidash stalled.

## Structural Decomposition

### Repository Structure

```
skills/
└── plan-port/
    ├── SKILL.md                    # Maps to: all three capabilities
    └── assets/
        └── port-plan-template.md   # Maps to: Parity matrix, Cutover and retirement
```

### Module: plan-port skill body

- **Maps to capability**: Feature inventory, Parity matrix, Cutover and
  retirement
- **Responsibility**: The workflow - inventory behavior-first, classify, walk the
  drops, analyse consumers, emit the phase list and the retirement block. Names
  `assess-evolution`, `design-solution` and `create-prd` and delegates to them
  rather than re-implementing their work.
- **Exports**:
  - `SKILL.md` frontmatter with a trigger-led description under 250 chars
  - A `## Dependencies` section naming `create-prd` (PRD authorship),
    `design-solution` (autopilot plugin, the HOW) and `assess-evolution` (the
    roadmap engine)

### Module: port-plan template

- **Maps to capability**: Parity matrix, Cutover and retirement
- **Responsibility**: The emitted document's shape - matrix table, consumer
  table, phase list, retirement block, freshness stamp.
- **Exports**: The template file the skill fills in.

## Dependency Graph

### Foundation Layer (Phase 0)

No dependencies - built first.

- **port-plan template**: fixes the output shape everything else fills in.

### Core Layer (Phase 1)

- **plan-port skill body**: Depends on [port-plan template]

### Integration Layer (Phase 2)

- **live validation on the postup port**: Depends on [plan-port skill body]

## Implementation Phases

### Phase 0: Foundation

**Goal**: The plan document has a fixed shape.

**Tasks**:

- [ ] Write `skills/plan-port/assets/port-plan-template.md` with the matrix
  table (row / class / reason / code-only flag), the consumer-cutover table, the
  dependency-ordered phase list, the retirement block in `create-prd`'s criterion
  shape, and a one-line freshness stamp (no deps)
  - Acceptance: the template contains a `reason` column and a retirement block
    whose criteria are phrased as acceptance criteria, checkable by reading it.

**Exit Criteria**: The template exists and carries every section the success
metrics are stated against.

### Phase 1: Core

**Goal**: The skill produces a plan from a source and a target.

**Tasks**:

- [ ] Write `skills/plan-port/SKILL.md`: behavior-first inventory, the
  code cross-check with `code-only` flagging, classification with a mandatory
  reason, the batch table for `port`/`redesign`, the one-at-a-time drop
  walkthrough, the consumer analysis and the phase list (depends on: Phase 0)
  - Acceptance: the create-skill validator passes; the description is trigger-led
    and under 250 chars.
- [ ] State the plan's home and the retirement PRD's home in `SKILL.md` (depends
  on: Phase 0)
  - Acceptance: the skill says the plan is written to the target repo's
    `dev/local/discovery/` sharing that repo's PRD sequence (the source repo when
    the target does not exist yet), and that the retirement PRD is written in the
    source repo alongside the final port phase.
- [ ] State the boundaries in `SKILL.md` (depends on: Phase 0)
  - Acceptance: the skill writes no PRD, no design doc, and no repo-health
    roadmap, and names `create-prd`, `design-solution` and `assess-evolution` as
    the owners of each.

**Exit Criteria**: `/plan-port` emits a filled template for a named source and
target.

### Phase 2: Integration

**Goal**: The skill emits a complete plan without a human in the room.

**Tasks**:

- [ ] Emit a plan for a fixture source under `dev/local/tmp/` whose matrix has no
  `drop` rows, so the one interactive stage never triggers (depends on: Phase 1)
  - The drop walkthrough asks the user to rule on every proposed deletion, which
    an unattended run cannot answer. A no-drop fixture is this PRD's own stated
    edge case ("a matrix with no `drop` rows → no walkthrough at all, plan
    emitted straight through"), so it exercises every other stage end to end.
  - Acceptance: the emitted plan carries a row for every command and flag the
    fixture source documents; every row has a reason; the plan names the
    condition under which the original may be deleted; no question is asked.

**Exit Criteria**: A fixture source yields a filled plan with a parity matrix and
a retirement block, produced without a single prompt.

**Attended follow-up** (not part of this PRD, run by hand after it ships): run
`plan-port` on `brief-portfolio` → the gems `postup` gem and commit the plan.
The postup port is still open (gems PRDs 00063-00068, 00070, 00072, with 00069 on
hold) and `brief-portfolio` still lives in this repo; that run is where the drop
walkthrough gets exercised for real.

## Test Strategy

### Critical Scenarios

- **Happy path**: a source with documented commands and flags → one matrix row
  each, all classified, all with reasons.
- **Happy path**: a behavior present in code but absent from the docs → a row
  flagged `code-only`, so it gets judged rather than assumed.
- **Edge case**: a matrix with no `drop` rows → no walkthrough at all, plan
  emitted straight through.
- **Edge case**: a matrix with more than a screen of drops → the skill states the
  too-big-for-one-plan observation once, then continues.
- **Error case**: a row without a reason → the skill refuses to emit the plan and
  names the row.
- **Error case**: a phase list whose stated order contradicts its dependencies →
  refused, since autopilot would drain it in the wrong order.

## Risks

- **Overlap with `design-solution` and `assess-evolution`**: three skills that
  emit plans invite drift. Mitigation: `plan-port` emits a matrix and a phase
  list only, cites the other two by name, and writes no PRD and no design.
- **Behavior-first inventory misses undocumented behavior**: the code
  cross-check is a must-have and code-only rows are flagged.
- **Walkthrough fatigue on a large source**: only drops are walked, and the skill
  names the too-big signal once.
- **The matrix rots between plan and retirement**: months pass. Mitigation: the
  freshness stamp, plus `create-prd` lifting the retirement block at write time
  so the gate is the copy inside the retirement PRD, never the stale plan.
- **The cross-repo split stalls the retirement again**: mitigated by naming one
  owner repo for the retirement PRD (the source, where the code dies) and by
  writing it alongside the final port phase instead of later.

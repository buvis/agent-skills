---
design: skip
---

# Capture Playground Experiments as Zettels

Source: `~/.claude/dev/local/discovery/00153-capture-experiments-as-zettels.md`
(elicitation complete 2026-08-27, review 2026-08-28).

## Overview

### Problem Statement

Playground and hardware sessions burn real tokens and produce real knowledge -
what worked, what the sensor actually read, which dead end cost an hour - and
none of it lands anywhere durable. The next session re-derives it. The vault and
the write path already exist: `digest-github-repo` emits zettel-format notes into
`~/bim/inbox/automated/` today. What is missing is a skill that does the same for
an experiment.

### Target Users

The solo maintainer, at the end of a playground or espx hardware session, when
play has just stopped and patience is at its lowest.

### Success Metrics

- A session ends with one file named `{YYYYMMDDHHmmss}.md` whose filename matches
  its `id` and whose frontmatter carries all six fields, under
  `~/bim/inbox/automated/capture-experiment/` in real use and under
  `dev/local/tmp/` in the unattended check.
- The note contains a hypothesis, a verdict, and at least one dead end when the
  session had one.
- Every reading is a summarized value with units; the note contains no raw serial
  capture.
- Capture takes one pass and no interview - if it ever takes more than a couple
  of minutes, the skill is wrong.

## Functional Decomposition

### Capability: Harvest

#### Feature: Read the experiment out of the live conversation

- **Description**: Build the note from what the session still holds - the
  commands run, the readings seen, the dead ends taken.
- **Inputs**: The live conversation. A title, the one required argument.
- **Outputs**: The material for one note.
- **Behavior**: No transcript parsing, ever. Harvesting from context sidesteps
  the provenance trap discovery 00147 measured (skill bodies, hook output, task
  notifications and agent prompts all arrive with `role=user`, and only schema
  fields separate them). Request-only: the skill never fires on session end.

#### Feature: State the window the note covers

- **Description**: Say what the note could see.
- **Inputs**: The first and last event still in context.
- **Outputs**: One window line in the note.
- **Behavior**: A compacted session has already lost its early dead ends, so the
  note states its window and reads as partial rather than complete. A note
  without a window line is a defect.

### Capability: Note composition

#### Feature: Frame as hypothesis, setup, observations, verdict

- **Description**: Give the note the shape an experiment has.
- **Inputs**: The harvested material.
- **Outputs**: Four sections plus a dead-ends section.
- **Behavior**: Dead ends are first-class content, not omissions. A note with no
  dead end in a session that had three is a defect.

#### Feature: Summarize readings, never dump them

- **Description**: Keep the knowledge, drop the evidence.
- **Inputs**: Hardware and command readings from the session.
- **Outputs**: Summarized values with units - the one that surprised, the range,
  the one that disagreed with the datasheet.
- **Behavior**: No raw serial streams, no pasted capture, no linked data file.
  Re-analysis means repeating the run, and that trade is accepted.

#### Feature: Render follow-ups as checkboxes

- **Description**: Leave the next step visible.
- **Inputs**: Anything the session flagged as unfinished.
- **Outputs**: Unchecked boxes naming the skill that would do the work
  (`/spike`, `create-prd`) where one applies.
- **Behavior**: Matches the digest notes already in the inbox. Cost and
  wall-clock are not recorded: `costs.jsonl` rows are cumulative per session id,
  so any naive figure would overstate.

### Capability: Vault write

#### Feature: Write one note per session into the inbox

- **Description**: Put the note where triage will find it.
- **Inputs**: The composed note.
- **Outputs**: `~/bim/inbox/automated/capture-experiment/{id}.md`.
- **Behavior**: One note per session, never one per hypothesis - atomizing is a
  triage-time job. Never written into `~/bim/zettelkasten/` directly. `~/bim/` is
  a hard anchor with no fallback: a missing vault is a loud failure, not a
  silent fallback path.

#### Feature: Reuse the vault's existing frontmatter dialect

- **Description**: Do not invent a second convention.
- **Inputs**: The note's title and tags.
- **Outputs**: Frontmatter `title`, `date` (ISO 8601), `tags` (three),
  `type: experiment-log`, `publish: false`, `processed: false`; filename is the
  `YYYYMMDDHHmmss` id from `date +%Y%m%d%H%M%S`.
- **Behavior**: Copied verbatim from `digest-github-repo`, varying only `type`.
  Three free tags; no espx-specific tag convention. `processed: false` makes the
  untriaged backlog countable.

## Structural Decomposition

### Repository Structure

```
skills/
└── capture-experiment/
    ├── SKILL.md                 # Maps to: Harvest, Note composition, Vault write
    └── assets/
        └── note-template.md     # Maps to: Note composition, Vault write
```

### Module: capture-experiment skill body

- **Maps to capability**: Harvest, Note composition, Vault write
- **Responsibility**: The one-pass workflow - harvest from context, compose,
  write, report the path. Request-only, one required argument.
- **Exports**:
  - `SKILL.md` frontmatter with a trigger-led description under 250 chars
  - A `## Dependencies` section naming `digest-github-repo` (frontmatter and id
    scheme), `spike` and `create-prd` (hand-off targets), and the `~/bim/` vault
    layout

### Module: note template

- **Maps to capability**: Note composition
- **Responsibility**: The note's fixed shape - frontmatter block, window line,
  hypothesis, setup, observations, dead ends, verdict, follow-up checkboxes.
- **Exports**: The template file the skill fills in.

## Dependency Graph

### Foundation Layer (Phase 0)

No dependencies - built first.

- **note template**: fixes the output shape, including the frontmatter contract
  lifted from `digest-github-repo`.

### Core Layer (Phase 1)

- **capture-experiment skill body**: Depends on [note template]

### Integration Layer (Phase 2)

- **live capture**: Depends on [capture-experiment skill body]

## Implementation Phases

### Phase 0: Foundation

**Goal**: The note shape exists and matches the vault.

**Tasks**:

- [ ] Write `skills/capture-experiment/assets/note-template.md` (no deps)
  - Premise: `digest-github-repo/SKILL.md` step 5 still pins the six frontmatter
    fields and the `date +%Y%m%d%H%M%S` id. Re-check at execution; if the dialect
    has changed, copy the current one and report the difference rather than
    writing the old shape.
  - Acceptance: the template's frontmatter fields are exactly `title`, `date`,
    `tags`, `type`, `publish`, `processed`, with `type: experiment-log`, and it
    contains a window line, a hypothesis, a dead-ends section, a verdict, and a
    follow-up checkbox block.

**Exit Criteria**: The template renders a valid vault note when filled in by
hand.

### Phase 1: Core

**Goal**: The skill exists and captures in one pass.

**Tasks**:

- [ ] Write `skills/capture-experiment/SKILL.md`: request-only invocation with a
  title as the single required argument, harvest-from-conversation (explicitly
  no transcript parsing), the window line, summarized-readings rule, dead ends as
  first-class content, follow-up checkboxes, and the `~/bim/` write path
  (depends on: Phase 0)
  - Acceptance: the create-skill validator passes; the description is trigger-led
    and under 250 chars.
- [ ] Pin the no-auto-fire property in `SKILL.md` (depends on: Phase 0)
  - Acceptance: the skill states it fires only when asked, and its absence from
    `~/.claude/hooks/dispatch.py` `ROUTES` and from every plugin `hooks.json` is
    checkable by `rg capture-experiment` returning no hook registration.

**Exit Criteria**: `/capture-experiment "<title>"` writes one note and prints its
path.

### Phase 2: Integration

**Goal**: The composed note is provably the right shape before a real session
depends on it.

**Tasks**:

- [ ] Compose a note from a fixture experiment - one hypothesis, two readings,
  one dead end, one follow-up - writing it under `dev/local/tmp/` instead of the
  vault (depends on: Phase 1)
  - An unattended build session has no playground session to harvest, and the
    vault sits outside the write fence, which allows only the repo, `dev/local`,
    `$TMPDIR` and `/tmp`. The fixture exercises composition and the write path
    without either.
  - Acceptance: the written file's name equals its `id`, all six frontmatter
    fields are present with `type: experiment-log` and `processed: false`, and
    the note carries a window line, a verdict, the dead end and an unchecked
    follow-up box.

**Exit Criteria**: A fixture experiment yields a note that passes the vault's
frontmatter contract, written without touching `~/bim/`.

**Attended follow-up** (not part of this PRD, run by hand after it ships):
capture one real playground or hardware session end to end, which is the first
write into `~/bim/inbox/automated/capture-experiment/`. If `~/bim/` is absent,
that run stops and reports rather than creating a fallback tree.

## Test Strategy

### Critical Scenarios

- **Happy path**: a session with one hypothesis, two readings and one dead end →
  one note carrying all of them, readings summarized with units.
- **Happy path**: follow-up work identified → unchecked boxes naming `/spike` or
  `create-prd`.
- **Edge case**: a compacted session → the window line names a late first event,
  so the note reads as partial.
- **Edge case**: a session with no dead ends → the dead-ends section says so
  explicitly rather than being omitted.
- **Error case**: `~/bim/` missing → loud failure, no fallback directory created,
  no note written elsewhere.
- **Error case**: the skill invoked with no title → it asks for the title and
  nothing else, since one required field is the whole ceremony budget.

## Risks

- **Ceremony kills play**: request-only, one required field, one pass, no
  interview. If a capture takes more than a couple of minutes the skill is wrong
  and should be cut back.
- **Context loss on long sessions**: harvesting from conversation means a
  compacted session lost its early dead ends. Mitigation: the window line, so a
  thin note reads as thin rather than as complete.
- **The inbox is never triaged**: the atomize-later design rests on triage
  happening. Mitigation: `processed: false` makes the backlog countable.
- **A second frontmatter dialect breaks vault-wide queries**: mitigation is
  copying `digest-github-repo`'s field set verbatim and varying only `type`.

## Post-completion notes (2026-09-05)

Deferred by batch 202608290848 (cycles 1 and 2), decided 2026-09-05 in
`dev/local/audit-results/deferred-walk-202608290848-2026-09-05.md`.

- The "exactly six fields" criterion and the "verbatim from
  digest-github-repo" behaviour clause disagreed: that skill's template
  carries `id: <zettelkasten-id>` too. Decided for the verbatim clause: the
  note template and SKILL.md now carry `id`, so vault-wide queries on `id` see
  these notes. The six-field criterion is superseded.
- Title handling: SKILL.md now escapes backslashes before quotes for the
  frontmatter value only and leaves the heading plain; the id-collision text
  says regenerate from the clock, never by arithmetic; the dependency
  fallback prose was collapsed. Applied directly on master.
- Happy-path-only behavioural coverage stays as accepted: a docs-only skill
  has no harness for it.

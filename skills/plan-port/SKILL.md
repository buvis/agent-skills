---
name: plan-port
description: Use when planning a port of a skill, tool, or plugin into a target - inventories documented behavior, classifies rows port/redesign/drop, walks drops for approval, emits a phased port plan. Triggers on "plan port", "port this skill", "port plan".
---

# plan-port

Plans a port of a skill, tool, or plugin from a source into a target. The
output is a plan document, not a code change: this skill inventories,
classifies, and sequences: it does not move code and it does not repoint
consumers.

## Dependencies

- `assess-evolution`: not invoked. If the target's own long-term health is in
  question before it takes on ported functionality, point the human at
  `assess-evolution` first. Absent that step, plan-port proceeds on the
  assumption the target is a going concern.
- `autopilot:design-solution`: not invoked. Any row classified `redesign`
  needs an actual design once its phase's PRD exists; point the human at
  `autopilot:design-solution` for that after `create-prd` runs, since
  plan-port only records that a redesign happens, not how. Absent that step,
  the human designs the redesign inline when they implement the phase.
- `create-prd`: not invoked. The phase list in the emitted plan is handed to
  `create-prd` once per phase, in phase order, after the plan is approved.
  Absent that step, the phase list is prose only and no PRD gets written.

## Inventory

Build the feature list from what the source shows a user, not from its call
graph. Read the source's docs and user-facing surface first - SKILL.md or
README, `--help` output, config schema, public API - and record every
documented command, flag, and behavior as a matrix row. Ordering is a hard
rule: the skill produces a matrix row for every documented command and flag
before doing anything else. Only after that pass is complete does the skill
read the source code, and only to catch behavior the docs never mention. A
row found only that way is marked `code-only`, because it is a row nobody
has judged yet.

## Classification

Decide what happens to each row in the target: `port` (moves over as is),
`redesign` (moves over but is deliberately rebuilt for the target), or `drop`
(does not move). Every row carries a one-line reason. No row without a
reason - a reasonless row is a defect the skill catches and refuses to emit
the plan until every row has one.

## Drop walkthrough

`port` and `redesign` rows are presented as one table for a single approval.
Each `drop` row gets an individual packet with evidence, per
`rules/communication.md`. The asymmetry is deliberate: a wrong `port` costs
effort, a wrong `drop` costs a feature.

Before the first drop packet, the skill says once, and only once, that a
port producing more than a screen of drops is probably too big for one plan.
Splitting stays the user's call, not the skill's.

If the matrix has no `drop` rows, the walkthrough is skipped entirely - no
question is asked, since the only trigger for it is at least one row
classified `drop`.

## Consumer analysis

Name who calls the source today and what breaks when it dies: other skills,
scripts, docs, hooks, CI. This step is read-only. The skill reports the
consumers it finds; it repoints nothing.

## Phase list

Say what order the port happens in. Phases only - no PRDs, no numbers
claimed. `create-prd` writes the actual PRDs one phase at a time, and the
phase numbering must equal execution order, because autopilot drains the
backlog by lowest sequence number.

## Output

Fill in `assets/port-plan-template.md` with the matrix, the drop packets,
the consumer analysis, and the phase list. Derive the source repo, the old
location, and one acceptance criterion per `port`-classified row from the
matrix, and fill in the template's `## Retirement` block from the same
matrix, before emitting the completed document as the plan.

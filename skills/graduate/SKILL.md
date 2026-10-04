---
name: graduate
description: Use when converting a PRD or legacy intake item into specflow requirements, design, and tasks, or adopting an implemented PRD into specflow. Triggers on "PRD to specflow", "convert PRD", "graduate PRD". Requires a PRD or repository context.
---

# Graduate

Convert an existing PRD into portable specflow artifacts without losing its decisions,
implementation evidence, or approval boundaries. Finish at task-plan approval; do not start
implementation unless the developer separately requests it.

## Dependencies

- Repository instructions and source PRD: required. Resolve the document from the conversation
  or an explicit repository ordering rule; ask for its path when ambiguous.
- Specflow runtime: optional. When installed, use its current workflow, templates, schema and
  approval helper. When absent, use this skill's manual workflow and Markdown approval receipts;
  do not invent production sidecars, helper results, plugin versions or schema validation.
- A proposed specflow specification: optional input for concept validation. Read the developer's
  supplied proposal and record deviations in a conversion report; proposal testing proves no
  runtime compatibility. Do not require another skill or a particular model.

## Workflow

Read [conversion contract](references/conversion.md) before writing.

1. **Discover.** Read the PRD, related specs, repository rules, changes and relevant code/tests.
   Inspect hidden metadata too. Separate source assertions, observed code, recorded historical
   checks and fresh verification. Decide whether this is completed-work adoption or new work.
2. **Preserve.** Keep the source text and number, native artifact shape, task IDs, completed
   progress and other tools' metadata. Resolve configured folders safely. Move intake to
   processed when requirements are first written, retaining provenance and links; processed
   means specified, not implemented.
3. **Requirements.** Trace every mandatory obligation; resolve optional items explicitly.
   Surface solution suggestions conflicting with public contracts. Ask material behavior
   questions one at a time, recommended choice first, and apply each answer immediately.
   Review completeness, coherence, integrity, feasibility and evolvability. Obtain explicit
   requirements approval before design drafting.
4. **Design.** Read approved requirements and actual dependency APIs; permissive mocks can
   conceal their shape. Describe reuse, exact contracts, alternatives, verification, risks and
   rollout. Read end-to-end before critique. Use an isolated adversarial reviewer when supported;
   otherwise record an inline pre-pass. Fix blockers and verify fixes once. Walk remaining
   decisions individually, then request design approval.
5. **Tasks.** Derive bounded tasks from both approved artifacts; copy applicable contracts,
   dependencies, locations and owned checks. Preserve bugfix exploration/preservation/fix/recheck
   order. Check every requirement has verification coverage, then request task-plan approval.
6. **Handoff.** Report content completion, implementation evidence, approvals, remaining
   questions and next action separately. Produce a durable conversion receipt. When awaiting
   an answer, say work is paused, identify the question and explain the gate's source. Keep it
   in the visible reply; do not hide the only approval question in an asynchronous picker.

Check content before overwriting existing files. An upstream edit invalidates dependent
approvals; explicit approval of a named amendment can renew that scoped baseline, but never
approves the whole downstream artifact. Stop on conflicting concurrent edits.

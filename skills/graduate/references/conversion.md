# PRD-to-specflow conversion contract

## Scope and authority

Apply to the PRD identified by the developer. For the next item, use repository ordering and
verify implementation state from code, history and tests. Report a missing roadmap; do not claim
to have followed it. Check existing specs before creating another folder with the same number.
Inspect related completed specs as context only; discovering one does not authorize its adoption
or approval recovery. Evidence-only read checks may run during discovery; do not execute the
implementation task plan or change production code during conversion.

Conversion authorizes artifact drafting and reversible organization. It does not authorize
implementation, plugin installation, committing, pushing, or editing another project's specs.
Capture concept findings locally unless the developer requests upstream edits.

The installed runtime owns its schema, hashing and status derivation. This is a manual conversion
procedure, not a substitute validator or runner. When a supplied proposal differs, explain that
difference and follow the developer's selected contract. Never label a manual trial plugin parity.

## Layout and provenance

Use repository configuration when present; otherwise use the specflow convention:

```text
.kiro/specflow/intake/processed/00007-example/
  idea.md
  qa-log.md
.kiro/specs/00007-example/
  requirements.md  # bugfix.md for bugfixes
  design.md
  tasks.md
```

Repository-relative `.agents/specflow.json` may configure `root` and `specsDir`. Reject absolute
paths, traversal segments and paths resolving outside the repository before using that config.
Do not create a `.kiro/specs` symlink or silently merge competing spec folders. Inspect dotfiles,
including `.config.kiro` and `.specflow.json`; normal file listings can miss them.

Preserve the original PRD verbatim as `idea.md`, retaining existing edits and annotations. For
flat legacy intake, move it into a numbered folder without duplicate number claims. Retain group
structure. Move to processed immediately before first writing requirements and fix affected local
links. Put `Sources:` with the processed source's repository-relative path in requirements;
for bugfixes, place it at the end of Introduction.
If the PRD lives outside intake, leave its repository-native record in place and copy its text
verbatim into the numbered intake folder; record both paths as provenance. Relocate that original
only when the developer or an applicable repository rule authorizes it.

Create a UUID type marker only for new specs when the selected contract requires one. Existing
markers precede filename inference; conflicting type/order declarations require a developer
decision. Preserve native IDs and unrelated metadata. Do not renumber a completed six-task
native plan to match the four-task skeleton used for newly generated bugfix specs.

## Completed PRD adoption

Recover objective facts: implementation commit, checked tasks, artifacts and verification records.
Historical results do not imply a fresh rerun. Never uncheck verified completed work or schedule
reimplementation merely because approvals are absent. Maintain implementation completion and
workflow approval state as separate facts.

Recover approvals only from explicit developer evidence. Approval to move a file or continue
another item does not approve artifacts. Date recovery approval when received; invent no old
timestamp. If the developer explicitly approves all identified artifacts as a recovered baseline
and the runtime supports it, record each against current content without redundant questions.
Otherwise confirm the first ambiguous gate. Obey a selected proposal's stricter recovery order.

```text
Implementation: complete, supported by the recorded commit and checked tasks.
Specflow recovery: requirements accepted; design/tasks acceptance unresolved.
Next: confirmation of the missing baseline, with no code execution scheduled.
```

Preserve Kiro's exact `Current Behavior (Defect)` heading. Explain nearby that the description
is historical and resolved; do not rename the heading to express completion.

## Unimplemented PRD conversion

Recommend feature/bugfix type, standard/quick depth and workflow order with brief reasons.
Requirements-first is the default unless the input is a design. Security, concurrency, public
contracts and data integrity warrant standard depth. Both depths retain all artifacts and gates.
Resume existing approved artifacts instead of regenerating them.

Build a source-to-clause map in the receipt or minutes. Every mandatory obligation needs a
destination clause or a developer-approved change. Optional suggestions become requirements,
move out of scope with a reason, or split into separately authorized work. Surface public
contract changes rather than hiding them in implementation details. Separate code observations,
executed reproductions and suspected dependency effects.

Ask one material question per turn. Offer distinct reasonable behaviors, recommended first;
do not pad choices. Explain user-visible consequences in plain language. Immediately edit the
artifact and Q&A minutes after each answer. A choice resolves that question; it does not approve
the whole artifact. At approval gates show the document, scope, blockers and next action, and
stop dependent drafting until approval arrives.

For bugfix requirements, retain stable clause numbers and this shape:

```text
# Bugfix Requirements Document
## Introduction
Sources: <repository-relative processed source>
## Bug Analysis
### Current Behavior (Defect)
1.1 WHEN <condition> THEN the system <incorrect behavior>
### Expected Behavior (Correct)
2.1 WHEN <condition> THEN the system SHALL <correct behavior>
### Unchanged Behavior (Regression Prevention)
3.1 WHEN <condition> THEN the system SHALL CONTINUE TO <preserved behavior>
```

Feature requirements use stable requirement IDs, testable acceptance criteria, scope, assumptions
and risks. Contract guesses and deferred answers remain explicitly unresolved until settled.

## Design review and plan

Ground design in actual modules and pinned dependencies. Inspect transport signatures, version
token storage, reload/cache behavior, full-resource serialization, selection and verification
targets. Real library objects can reveal errors hidden by permissive mocks. Trace boundary
constraints through caller, parser, verifier and return projection; selecting correctly for
patching is insufficient when verification still inspects another component.

Record reuse searches and helpers; distinguish new versus edited files. Copy concrete contracts
into tasks. Include the smallest-diff alternative, chosen approach and what added size buys.
Bugfix designs retain Overview, Glossary, Bug Details, Expected Behavior, Hypothesized Root
Cause, Correctness Properties, Fix Implementation and Testing Strategy; list open decisions.

Read the whole design and capture comprehension confusions before critique. Give an isolated
reviewer the draft, approved requirements summary and active workflow severity rubric; record
an inline review and its limits when isolation is unavailable. Fix blockers in the canonical
draft, verify fixes once, then walk remaining decisions. Do not claim a rubric was applied if
its actual text was unavailable. An upstream behavior amendment reopens its gate; an explicit
scoped acceptance renews only that baseline, not the downstream design approval.

New bugfix plans keep four top-level tasks:

1. Exploration: tests expose the stated defect on old production code; failure is not a
   collection error or missing future module.
2. Preservation: observe passing baselines on old code, excluding approved behavior changes.
3. Fix: bounded nested implementation slices, then re-run the same exploration and preservation
   cases. Keep coupled interface/caller/verification changes together.
4. Checkpoint: applicable full checks and real-service evidence, honoring repository review
   and handoff rules. Unavailable infrastructure is incomplete verification.

Planning does not execute these tasks. Leave boxes unchecked until owned verification succeeds
or an explicit accepted exception is recorded. Each slice needs location, dependencies, copied
applicable contracts, clause references and an owned check. Trace every 2.x and 3.x clause to
tests; expand ranges if the runtime validator cannot resolve them. Keep fail-first tests runnable
before new classes/helpers exist. Never weaken preservation expectations to make a fix pass.

## State, evidence and done

Use the installed helper for hashes, approvals, invalidation and validation. Preserve unknown
fields and compare read hashes before mutation. Upstream changes stale dependent approvals.
The runtime owns checkbox/progress-field exclusions; do not approximate fence-aware canonical
hashing with an improvised regex.

Without a runtime, keep approval receipts in `qa-log.md`: artifact, decision, date, scope and
accepted unresolved items. Leave production sidecar creation/reconciliation to the runtime.
Preserve existing state and report it as unreconciled if edits may invalidate it. Never invent
a workflow version or claim validated portable approvals.

Conversion is complete when provenance and obligations are preserved, requirements/design are
approved, and a reviewed task plan is approved or delivered as the requested draft. Leave new
implementation task checkboxes unchecked. A delivered
draft is not approval. Implementation, runtime validation and cross-host compatibility remain
distinct outcomes. This originating trial demonstrated artifact conversion and review, not
executed implementation or a functioning specflow runtime.

Create a durable conversion receipt with source/destination paths, number/type/configured
folders, obligation coverage, decisions/public behavior changes, implementation evidence,
each gate's state and evidence, review outcomes, actual checks and limitations, outstanding
questions/next action, and proposal gaps when testing a concept.

Set verdict `COMPLETE`, `AWAITING_DECISION` or `INCOMPLETE`. A pending gate is an honest
deliverable: state visibly what is waiting and why instead of silently sitting idle.

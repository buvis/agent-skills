---
prd: dev/local/prds/wip/00003-add-plan-port-skill-v1.md
review: 1
date: 2026-08-29
head_sha: 8e1ed1b4564d8ffd25ab3043079d3b0a00f72e3b
codex_thread_id: 01a04e78-d0dc-77c0-b239-bece6f101ca8
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00003-add-plan-port-skill-v1

Diff range: `52398e2985ee4f48f1ac953f3d53499301be6fef..8e1ed1b4564d8ffd25ab3043079d3b0a00f72e3b`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in ~/.config/gita/repos.csv") — `{PACK_FILE}` and `{PACK_FINDINGS}` substituted with the no-pack sentinel in every prompt that takes them. Blake never receives a pack by design.

## Review Summary

Reviewed: 5 completed tasks
PRDs checked: 00003-add-plan-port-skill-v1.md

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (first dispatch reviewed nothing — the codex sandbox refused to open the referenced context and diff files and returned an all-`fail` verdict block; retried once per `retry-policy.md` with the context and diff inlined into the prompt, which produced the review recorded below. The failed first attempt is kept at `dev/local/tmp/bob-output-00003-1-attempt1.txt`.)
- Carl: ✅ Available

### Scope note (deviation, recorded)

`gather-context.sh` without `--since` resolved the base branch to `master`, and this PRD's work was committed directly onto `master`, so the full-review diff came back **empty**. The context was re-gathered with `--since 52398e29` — `state.work_start_sha`, the same range this file records as the diff range and the range the doubt lens is defined against. Without this the whole cycle would have reviewed nothing.

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟠 | PRD Test Strategy error case "a phase list whose stated order contradicts its dependencies → refused" (explicitly listed as a required scenario) is never implemented — the `## Phase list` section only states numbering must equal execution order but never instructs the skill to check/refuse a self-contradictory order before emitting the plan | skills/plan-port/SKILL.md | general | ALICE, BLAKE |
| [1/4] | 🟠 | The template has no drop-ruling section, so each proposed drop's evidence and user ruling cannot be recorded as required | skills/plan-port/assets/port-plan-template.md:19 | 1 | BOB |
| [1/4] | 🟠 | The hand-off waits until all retirement criteria are checked, contradicting the requirement to create the retirement PRD alongside the final port phase | skills/plan-port/assets/port-plan-template.md:51 | 3 | BOB |
| [1/4] | 🟠 | No pre-emission validation rejects a phase that depends on a later phase, despite the PRD's explicit error case | skills/plan-port/SKILL.md:73 | 2 | BOB |
| [1/4] | 🟡 | The PRD's Task 1 contract requires "the user's recorded ruling per drop row, written into the plan" as a Drop-walkthrough output, but `port-plan-template.md` has no section to hold it, and SKILL.md's `## Output` section tells the skill to fill in "the drop packets" into the template even though no such slot exists there (only matrix, consumer table, phases, retirement). One clarifying sentence — e.g. "a walked drop's outcome updates that row's classification/reason in place: approved stays `drop`, overruled is reclassified" — would close the ambiguity | skills/plan-port/SKILL.md | 1 | ALICE |
| [1/4] | 🟡 | Consumer discovery is not scoped across the portfolio, so cross-repo callers may be omitted from the cutover gate | skills/plan-port/SKILL.md:67 | 2 | BOB |
| [1/4] | 🟡 | The relative asset path violates this repository's cross-host path convention; use `~/.agents/skills/plan-port/assets/port-plan-template.md` | skills/plan-port/SKILL.md:80 | 2 | BOB |
| [1/4] | 🟡 | `rules/communication.md` is an unresolved host-relative reference; inline the required packet protocol or use a universally resolvable dependency | skills/plan-port/SKILL.md:53 | 2 | BOB |
| [1/4] | ⚪ | Test Strategy's error case says a reasonless row is refused "and names the row," but the Classification section only says the skill "refuses to emit the plan until every row has one" without stating the refusal names the offending row | skills/plan-port/SKILL.md | 2 | ALICE |
| [1/4] | ⚪ | The plan-port feat commits (e.g. cde9f38 "write the SKILL.md workflow body", da6e01b "add the port-plan template asset") carry no CHANGELOG.md entry, contrary to the repo's own blocking changelog-maintenance rule for feat commits | CHANGELOG.md | general | BLAKE |
| [1/4] | ⚪ | dev/local/prds/wip/00003-add-plan-port-skill-v1.md still has every task checkbox unchecked ([ ]) for Phase 0, Phase 1, and Phase 2, even though the corresponding artifacts (template, SKILL.md, fixture run) are present and match their acceptance criteria — the PRD's own tracking is stale relative to the delivered work | dev/local/prds/wip/00003-add-plan-port-skill-v1.md | general | BLAKE |
| [1/4] | ⚪ | The Phase 2 fixture (dev/local/tmp/plan-port-fixture-skill.md) has no code file to cross-check against docs, so the PRD's first "Happy path" critical scenario ("a behavior present in code but absent from the docs → a row flagged code-only") is asserted in prose only and was never actually exercised end to end, unlike the no-drop edge case which was | dev/local/tmp/plan-port-fixture-plan.md | general | BLAKE |
| [1/4] | ⚪ | Cannot statically verify: repository tests, plan-port validation, and braid checks pass | N/A | general | BOB |
| [1/4] | ⚪ | Cannot statically verify: the no-drop fixture emitted a complete plan without prompting because the fixture, output, and interaction transcript are not inlined | N/A | 5 | BOB |

## Alice

Consensus lens (implementation-aware, `consensus_engine: legacy`).

```
[ALICE] 🟠 PRD Test Strategy error case "a phase list whose stated order contradicts its dependencies → refused" (explicitly listed as a required scenario) is never implemented — the `## Phase list` section only states numbering must equal execution order but never instructs the skill to check/refuse a self-contradictory order before emitting the plan | File: skills/plan-port/SKILL.md | Task: general
[ALICE] 🟡 The PRD's Task 1 contract requires "the user's recorded ruling per drop row, written into the plan" as a Drop-walkthrough output, but `port-plan-template.md` has no section to hold it, and SKILL.md's `## Output` section tells the skill to fill in "the drop packets" into the template even though no such slot exists there (only matrix, consumer table, phases, retirement). One clarifying sentence — e.g. "a walked drop's outcome updates that row's classification/reason in place: approved stays `drop`, overruled is reclassified" — would close the ambiguity | File: skills/plan-port/SKILL.md | Task: 1
[ALICE] ⚪ Test Strategy's error case says a reasonless row is refused "and names the row," but the Classification section only says the skill "refuses to emit the plan until every row has one" without stating the refusal names the offending row | File: skills/plan-port/SKILL.md | Task: 2
```

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: pass

Checks Alice ran herself: `validate_skill.py skills/plan-port` → OK; frontmatter description 246 chars, trigger-led; `uv run pytest` → 421 passed, 5 skipped (skips pre-existing, `tree_sitter_language_pack` in `skills/survey`); `braid --check` → 0 drift; working tree clean. She also read the Task 5 fixture and its emitted plan and confirmed one matrix row per documented command/flag, a reason on every row, a stated deletion condition, and no prompt raised.

## Blake

Blind lens — PRD only, no diff, no file list, no review history. He located the code himself.

```
[BLAKE] 🟡 SKILL.md instructs the skill to refuse emission when a matrix row lacks a reason, but never instructs it to refuse or otherwise handle a phase list whose stated order contradicts its own declared dependencies — an explicit PRD "Error case" ("a phase list whose stated order contradicts its dependencies → refused, since autopilot would drain it in the wrong order") that has no corresponding instruction anywhere in SKILL.md or the template's Phases section | File: skills/plan-port/SKILL.md | Task: 1
[BLAKE] ⚪ The plan-port feat commits (e.g. cde9f38 "write the SKILL.md workflow body", da6e01b "add the port-plan template asset") carry no CHANGELOG.md entry, contrary to the repo's own blocking changelog-maintenance rule for feat commits | File: CHANGELOG.md | Task: general
[BLAKE] ⚪ dev/local/prds/wip/00003-add-plan-port-skill-v1.md still has every task checkbox unchecked ([ ]) for Phase 0, Phase 1, and Phase 2, even though the corresponding artifacts (template, SKILL.md, fixture run) are present and match their acceptance criteria — the PRD's own tracking is stale relative to the delivered work | File: dev/local/prds/wip/00003-add-plan-port-skill-v1.md | Task: general
[BLAKE] ⚪ The Phase 2 fixture (dev/local/tmp/plan-port-fixture-skill.md) has no code file to cross-check against docs, so the PRD's first "Happy path" critical scenario ("a behavior present in code but absent from the docs → a row flagged code-only") is asserted in prose only and was never actually exercised end to end, unlike the no-drop edge case which was | File: dev/local/tmp/plan-port-fixture-plan.md | Task: general
```

B1: fail
B2: pass
B3: pass
B4: pass
B5: fail
B6: pass
B7: pass
B8: pass
B9: pass
B10: fail
B11: pass
B12: pass
B13: pass
B14: pass
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Doubt + de-slop lens (codex, static-only sandbox), after the one-retry re-dispatch with inlined inputs.

```
[BOB] 🟠 The template has no drop-ruling section, so each proposed drop's evidence and user ruling cannot be recorded as required | File: skills/plan-port/assets/port-plan-template.md:19 | Task: 1
[BOB] 🟠 The hand-off waits until all retirement criteria are checked, contradicting the requirement to create the retirement PRD alongside the final port phase | File: skills/plan-port/assets/port-plan-template.md:51 | Task: 3
[BOB] 🟠 No pre-emission validation rejects a phase that depends on a later phase, despite the PRD's explicit error case | File: skills/plan-port/SKILL.md:73 | Task: 2
[BOB] 🟡 Consumer discovery is not scoped across the portfolio, so cross-repo callers may be omitted from the cutover gate | File: skills/plan-port/SKILL.md:67 | Task: 2
[BOB] 🟡 The relative asset path violates this repository's cross-host path convention; use `~/.agents/skills/plan-port/assets/port-plan-template.md` | File: skills/plan-port/SKILL.md:80 | Task: 2
[BOB] 🟡 `rules/communication.md` is an unresolved host-relative reference; inline the required packet protocol or use a universally resolvable dependency | File: skills/plan-port/SKILL.md:53 | Task: 2
[BOB] ⚪ Cannot statically verify: repository tests, plan-port validation, and braid checks pass | File: N/A | Task: general
[BOB] ⚪ Cannot statically verify: the no-drop fixture emitted a complete plan without prompting because the fixture, output, and interaction transcript are not inlined | File: N/A | Task: 5
```

R1: fail
R2: fail
R3: pass
R4: fail
R6: pass
R7: pass
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

FIX:
- Drop rulings have no output location — skills/plan-port/assets/port-plan-template.md:19 — add a repeatable Drop Rulings section containing the row, evidence, and recorded user ruling.
- Retirement PRD creation is incorrectly deferred until criteria pass — skills/plan-port/assets/port-plan-template.md:51 — hand the block to `create-prd` alongside the final port phase and state that criteria are checked when retirement executes.
- Invalid dependency order is not rejected — skills/plan-port/SKILL.md:73 — add a pre-emission check that every dependency names an earlier phase and refuse emission while naming each violation.
- Consumer discovery lacks portfolio scope — skills/plan-port/SKILL.md:67 — explicitly search the source repo and portfolio repositories for callers before completing the cutover table.
- Asset reference is not cross-host portable — skills/plan-port/SKILL.md:80 — replace it with `~/.agents/skills/plan-port/assets/port-plan-template.md`.
- Communication-rule reference cannot be resolved across hosts — skills/plan-port/SKILL.md:53 — inline the evidence-packet requirements or replace the reference with a declared, portable dependency.

VERIFY:
- Required checks are unverified — run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/plan-port`, and `braid --check`, confirming zero failures.
- No-drop integration behavior is unverified — inspect the fixture and emitted plan for complete row coverage, reasons, retirement condition, and capture the run showing zero prompts.

KNOWN:
- (none)

## Carl

Frontend & design specialist; reviewed as a generalist here (the diff has no frontend surface).

```
[CARL] ✅ No issues found
```

R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: pass

## Follow-up Tasks Created

None created by this skill. Under autopilot the Phase 5 decision gate classifies these findings first (auto-fix / research / defer / discard) and Phase 6 creates the `[D1]` rework tasks with the verbatim findings block; creating them here would pre-empt that classification and double-create.

Verdict: 14 findings
Tests: 421 passed, 0 failed, 5 skipped

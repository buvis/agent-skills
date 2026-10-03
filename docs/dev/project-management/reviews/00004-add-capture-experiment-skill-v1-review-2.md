---
prd: dev/local/prds/wip/00004-add-capture-experiment-skill-v1.md
review: 2
date: 2026-08-29
head_sha: e6545b6b1ac819b6b9e34be3bc38d01e0fa752db
codex_thread_id: 01a04ebc-2d19-7143-95d1-9bc966ed05a5
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00004-add-capture-experiment-skill-v1

Diff range: `22767db60859c3324ef2a4dd189d8b0e602c5168..e6545b6b1ac819b6b9e34be3bc38d01e0fa752db`

codex_rung_guard: not fired

Scope note: this is cycle 2, an **incremental review** of the cycle-1 rework. `gather-context.sh` ran
with `--since 22767db6` (cycle 1's `head_sha`), so the diff covers only commit `e6545b6`
(+19/-6, two markdown files). Bob resumed his cycle-1 codex thread
(`--resume-thread 01a04ebc-2d19-7143-95d1-9bc966ed05a5`), so he verified his own critique rather than
re-reviewing from zero. Blake stayed blind by design: PRD-only prompt, no diff, no file list, no
review history; his re-raises are absorbed mechanically by `--ledger-dismiss BLAKE`.

pack: unavailable this cycle — `engram pack` exited 1 with "not inside a registered repo; register it
in ~/.config/gita/repos.csv". Deterministic config state, same as cycle 1, so no retry. Every
implementation-aware prompt received the sentinel `(no pack available this cycle)` for
`{PACK_FILE}`/`{PACK_FINDINGS}`.

Mechanical facts: both changed files are markdown, so `compute_mech_facts.py` reported them as
`skipped (non-python)`. No countable per-function claims are available to check findings against this
cycle.

Change under review is **docs-only**: 19 insertions, 6 deletions across
`skills/capture-experiment/SKILL.md` and `skills/capture-experiment/assets/note-template.md`. No
Python, no executable code.

## Review Summary

Reviewed: 5 completed tasks
PRDs checked: 00004-add-capture-experiment-skill-v1.md

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available
- Carl: ✅ Available

## Cycle-1 findings — resolution status

All five findings routed into the `[D1]` rework task are confirmed resolved. Alice verified each one
against the code independently, and Bob (resuming his own thread) did not re-raise any of them as
unresolved.

| # | Cycle-1 finding | Status |
|---|-----------------|--------|
| 1 | Title inserted as an unquoted YAML scalar (🟠, BOB) | **Resolved for the reported cases** — `note-template.md:2` now emits `title: "<experiment title>"` and `SKILL.md` Step 2 adds the collapse/escape instruction. Alice verified colon-space and embedded-`"` titles parse with PyYAML. A residual gap (backslashes) is raised fresh below. |
| 2 | Destination leaf not created before writing (🟠, BOB) | **Resolved** — `SKILL.md` Step 3 creates `~/bim/inbox/automated/capture-experiment/` after the `~/bim/` check and before the write. Hard-anchor rule unchanged. |
| 3 | Dependency absence behavior undocumented (🟡, BOB) | **Resolved** — all three entries state absence behavior. |
| 4 | Redundant "All files live under…" line (🟡, BOB) | **Resolved** — line removed; Step 3 is the sole output-location statement. |
| 5 | Same-second id collision unguarded (⚪, BLAKE) | **Resolved** — Step 3 and an Edge cases bullet both state the collision rule. Bob raises the *wording* of that rule freshly below. |

Binding constraints held: no `id:` frontmatter field added (template still exactly the six pinned
fields), the `~/bim/` hard-anchor/no-fallback text unchanged, edits surgical, `description` still
trigger-led at 217 chars.

## Consolidated Findings

Consolidation ran via `consolidate_findings.py` with
`--ledger dev/local/reviews/00004-add-capture-experiment-skill-v1-ledger.json --ledger-dismiss BLAKE`.
6 findings. One row carries genuine 2/4 consensus (Alice and Bob independently reached the
title-escaping instruction); the rest are single-reviewer.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟠 | The collapse/escape instruction is applied to both the frontmatter scalar and the markdown heading; escaping quotes for the heading is unnecessary (not YAML) and would leave a visible literal backslash in the rendered note title for a title containing `"`. | skills/capture-experiment/SKILL.md | general | ALICE, BOB |
| [1/4] | 🟡 | Title-escaping fix only covers embedded double quotes, not backslashes — a title containing a literal `\` (e.g. a Windows path or regex in the title) still produces an invalid double-quoted YAML scalar, verified with PyYAML (`ScannerError`). | skills/capture-experiment/SKILL.md | general | ALICE |
| [1/4] | 🟡 | "Advance to the next free second" is ambiguous timestamp arithmetic and may produce an invalid ID such as `...5960`, violating the pinned `date`-generated ID scheme. Require waiting for the clock to advance, rerunning `date +%Y%m%d%H%M%S`, and repeating the existence check. | skills/capture-experiment/SKILL.md:112 | 5 | BOB |
| [1/4] | 🟡 | The new dependency fallback prose repeatedly states "not invoked," "nothing changes," "capture proceeds," and "not a runtime dependency." Collapse each entry to one explicit absence sentence while preserving the required fallback behavior. | skills/capture-experiment/SKILL.md:16 | 5 | BOB |
| [1/4] | ⚪ | Fixture note's title is unquoted YAML (`title: Reduce polling interval on sensor loop`) though the template mandates a quoted scalar (`title: "<experiment title>"`) and SKILL.md explicitly calls out quoting/escaping; harmless here since the title has no special characters, but the fixture output didn't follow the stated convention it was meant to demonstrate | dev/local/tmp/20260829200518.md | 3 | BLAKE |
| [1/4] | ⚪ | PRD is still parked in dev/local/prds/wip/ rather than moved to done/, despite the implementation appearing verified-complete per the user's own workflow rule | dev/local/prds/wip/00004-add-capture-experiment-skill-v1.md | general | BLAKE |

No `### Auto-dismissed (ledger)` section was emitted: Blake raised nothing this cycle that matched a
settled entry, so the ledger filter dismissed nothing.

## Alice

Implementation-aware consensus lens. Verified each of the five cycle-1 findings against the code,
re-ran `validate_skill.py` independently (`[OK] Skill is valid!`), re-confirmed no hook registration
in `dispatch.py` `ROUTES` or any plugin `hooks.json` (with a control query proving `rg` worked), and
tested the new title-quoting rule directly against PyYAML.

Her regression check found the escaping instruction incomplete. Verified directly:

```
title: "Fix C:\Users config parsing"
```

→ PyYAML: `ScannerError: expected escape sequence... but found 's'`

Colon-space and embedded-`"` titles (the cases Bob named in cycle 1) now parse; backslash-containing
titles do not.

```
[ALICE] 🟡 Title-escaping fix only covers embedded double quotes, not backslashes — a title containing a literal `\` (e.g. a Windows path or regex in the title) still produces an invalid double-quoted YAML scalar, verified with PyYAML (`ScannerError`). | File: skills/capture-experiment/SKILL.md | Task: general
[ALICE] ⚪ The collapse/escape instruction is applied to both the frontmatter scalar and the markdown heading; escaping quotes for the heading is unnecessary (not YAML) and would leave a visible literal backslash in the rendered note title for a title containing `"`. | File: skills/capture-experiment/SKILL.md | Task: general
```

Verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 fail, R8 pass, R9 pass, R10 pass,
R11 pass, R12 pass, R13 pass.

## Blake

Blind lens — PRD-only prompt, no diff, no file list, no review history. He located both files
himself, ran the validator, checked hook registration independently, and inspected the Phase 2
fixture note at `dev/local/tmp/20260829200518.md` against the Phase 2 acceptance criteria (filename
equals id, six frontmatter fields, `type: experiment-log`, `processed: false`, window line, verdict,
dead end, unchecked `/spike` box — all present).

He found no functional, security, or scope-creep defect, and reported two minor observations:

```
[BLAKE] ⚪ Fixture note's title is unquoted YAML (`title: Reduce polling interval on sensor loop`) though the template mandates a quoted scalar (`title: "<experiment title>"`) and SKILL.md explicitly calls out quoting/escaping; harmless here since the title has no special characters, but the fixture output didn't follow the stated convention it was meant to demonstrate | File: dev/local/tmp/20260829200518.md | Task: 3
[BLAKE] ⚪ PRD is still parked in dev/local/prds/wip/ rather than moved to done/, despite the implementation appearing verified-complete per the user's own workflow rule | File: dev/local/prds/wip/00004-add-capture-experiment-skill-v1.md | Task: general
```

Verdicts: B1-B19 all pass.

## Bob

Doubt + de-slop lens (codex, static-only sandbox), resumed on his cycle-1 thread.

```
[BOB] 🟠 Title handling remains incomplete: YAML double-quoted scalars also require backslashes to be escaped, and the instruction applies YAML escaping to the Markdown heading too. Preserve a normalized plain title for the heading and YAML-escape both backslashes and quotes only for frontmatter. | File: skills/capture-experiment/SKILL.md:83 | Task: 5
[BOB] 🟡 "Advance to the next free second" is ambiguous timestamp arithmetic and may produce an invalid ID such as `...5960`, violating the pinned `date`-generated ID scheme. Require waiting for the clock to advance, rerunning `date +%Y%m%d%H%M%S`, and repeating the existence check. | File: skills/capture-experiment/SKILL.md:112 | Task: 5
[BOB] 🟡 The new dependency fallback prose repeatedly states "not invoked," "nothing changes," "capture proceeds," and "not a runtime dependency." Collapse each entry to one explicit absence sentence while preserving the required fallback behavior. | File: skills/capture-experiment/SKILL.md:16 | Task: 5
```

FIX:
- YAML title serialization still mishandles backslashes and heading text — skills/capture-experiment/SKILL.md:83 — normalize once, YAML-escape backslashes and quotes only for frontmatter, and use the unescaped normalized value in the heading.
- Collision handling can synthesize an invalid timestamp — skills/capture-experiment/SKILL.md:112 — wait for the clock to advance, regenerate the ID with the pinned `date` command, and recheck existence.
- Dependency absence wording is redundant — skills/capture-experiment/SKILL.md:16 — reduce each dependency entry to one explicit, behavior-preserving absence clause.

VERIFY:
- (none)

KNOWN:
- (none)

He re-raised none of the three settled decisions, and emitted no "Cannot statically verify" line this
cycle — the settled-decisions section told him the gate had already run those checks.

Consensus verdicts: R1 fail, R2 pass, R3 pass, R4 pass, R6 pass, R7 fail, R8 pass, R9 fail,
R10 pass, R11 pass, R12 pass, R13 pass.

Doubt verdicts: D1 pass, D2 pass, D3 pass, D4 pass, D5 pass.

## Carl

Generalist lens this cycle — the change has no frontend surface.

`[CARL] ✅ No issues found`

Verdicts: R1 fail, R2 fail, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass, R10 pass,
R11 pass, R12 pass, R13 pass.

## Orchestrator-run checks

Bob's sandbox blocks execution, so the gate ran the runtime checks directly:

- `uv run pytest -q` → **422 passed, 5 skipped, 0 failed**. Identical to the cycle-1 baseline; the 5
  skips are pre-existing and unrelated (`skills/survey/scripts/test_survey.py`, "needs the optional
  tree_sitter_language_pack").
- `uv run python3 skills/create-skill/scripts/validate_skill.py skills/capture-experiment` →
  `[OK] Skill is valid!`
- `braid --check` → **not run**. Warden blocks the binary in these sessions, as in cycle 1. Recorded
  as unverified rather than claimed green.

Verdict: 6 findings
Tests: 422 passed, 0 failed, 5 skipped

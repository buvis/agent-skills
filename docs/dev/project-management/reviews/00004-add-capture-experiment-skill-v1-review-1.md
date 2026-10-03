---
prd: dev/local/prds/wip/00004-add-capture-experiment-skill-v1.md
review: 1
date: 2026-08-29
head_sha: 22767db60859c3324ef2a4dd189d8b0e602c5168
codex_thread_id: 01a04ebc-2d19-7143-95d1-9bc966ed05a5
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00004-add-capture-experiment-skill-v1

Diff range: `b501345e1365b4716bdd59275605d7ccf73276e3..22767db60859c3324ef2a4dd189d8b0e602c5168`

codex_rung_guard: not fired

Scope note: this is cycle 1, a **full review** of the PRD's whole work range. The work landed
directly on `master`, so `gather-context.sh`'s branch-base heuristic would have produced an empty
diff (`git diff master` from `master` on a clean tree). The diff was therefore scoped with
`--since <work_start_sha>`, which is exactly the `work_start_sha..HEAD` range the full-review rule
prescribes. The label inside the context file reads "incremental" for that reason; the content is
the full PRD work range.

pack: unavailable this cycle — `engram pack` exited 1 with "not inside a registered repo; register
it in ~/.config/gita/repos.csv". Deterministic config state, so no retry. Every prompt received the
sentinel `(no pack available this cycle)` for `{PACK_FILE}`/`{PACK_FINDINGS}`.

Change under review is **docs-only**: two new markdown files under `skills/capture-experiment/`
plus a CHANGELOG entry. 170 insertions, 0 deletions, no Python.

## Review Summary

Reviewed: 4 completed tasks
PRDs checked: 00004-add-capture-experiment-skill-v1.md

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available
- Carl: ✅ Available

## Consolidated Findings

Consolidation ran via `consolidate_findings.py` (no ledger — cycle 1). 8 findings, none with
multi-reviewer consensus.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟠 | Frontmatter is not verbatim with digest-github-repo's current dialect: `digest-github-repo/references/output-templates.md` carries a live `id: <zettelkasten-id>` field that capture-experiment's six-field copy omits, and no re-check or reported difference exists anywhere (per the Phase 0 task's explicit "re-check at execution... report the difference" instruction). | skills/capture-experiment/assets/note-template.md | Phase 0 | BLAKE |
| [1/4] | 🟠 | First use can fail because Step 3 checks only the vault root, then writes into a new skill-specific directory without ensuring that directory exists. After validating `~/bim/`, create the destination leaf before writing. | skills/capture-experiment/SKILL.md:98 | 2 | BOB |
| [1/4] | 🟠 | An arbitrary title can produce invalid YAML because it is inserted as an unquoted scalar; common titles containing `: ` or newlines break the frontmatter contract. Require a single-line title and render it as an escaped quoted YAML scalar. | skills/capture-experiment/assets/note-template.md:2 | 1 | BOB |
| [1/4] | 🟡 | The dependency entries do not state what happens when `digest-github-repo`, `spike`, or `create-prd` is absent, as required by AGENTS.md. | skills/capture-experiment/SKILL.md:16 | 2 | BOB |
| [1/4] | 🟡 | "All files live under…" is redundant with Step 3 and ambiguously includes the skill's source/template. Delete this line; Step 3 already defines the complete output-location invariant. | skills/capture-experiment/SKILL.md:12 | 2 | BOB |
| [1/4] | ⚪ | Write path uses a second-granularity timestamp as the sole id with no existence check before writing; two captures in the same second would silently overwrite one note. | skills/capture-experiment/SKILL.md | general | BLAKE |
| [1/4] | ⚪ | Cannot statically verify: the test suite, create-skill validator, and braid checks passed for this change. | N/A | general | BOB |
| [1/4] | ⚪ | Behavioral regression coverage is limited to the reported happy-path fixture; no retained test covers no-title, missing-vault, compacted-window, or no-dead-end behavior. | N/A | general | BOB |

## Alice

Implementation-aware consensus lens. Ran the create-skill validator (`[OK] Skill is valid!`), the
full suite (`422 passed, 5 skipped`), measured the frontmatter description at 217 chars, confirmed
`spike`/`create-prd`/`digest-github-repo` all exist under `skills/`, confirmed no hook registration
in `dispatch.py` ROUTES or any plugin `hooks.json` (with a control check proving the search worked),
compared the template frontmatter against `digest-github-repo/SKILL.md` Step 5's field guide, and
read the Phase 2 fixture output directly against every acceptance criterion.

`[ALICE] ✅ No issues found`

She recorded two things she checked and deliberately did not report (description/Triggers phrasing
overlap, and the ISO 8601 `date` generation not being spelled out in Step 3), judging both to be
established repo convention rather than drift. She also recorded that `braid --check` could not run
in her sandbox because warden blocks the binary — a tooling limitation, not a defect.

Verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass, R10 pass,
R11 pass, R12 pass, R13 pass.

## Blake

Blind lens — PRD-only prompt, no diff, no file list, no review history. He located the code himself,
ran the validator, and checked hook registration independently.

```
[BLAKE] 🟠 note-template.md/SKILL.md frontmatter is not verbatim with digest-github-repo's current dialect: digest-github-repo/references/output-templates.md (pre-existing, unchanged since the repo's first commit) carries a live `id: <zettelkasten-id>` field that capture-experiment's six-field copy omits, and no re-check or reported difference exists anywhere. | File: skills/capture-experiment/assets/note-template.md | Task: Phase 0
[BLAKE] ⚪ Write path uses a second-granularity timestamp (`date +%Y%m%d%H%M%S`) as the sole id with no existence check before writing; two captures in the same second would silently overwrite one note with another. | File: skills/capture-experiment/SKILL.md | Task: general
```

Verdicts: B1 fail, B2 fail, B3-B19 pass.

## Bob

Doubt + de-slop lens (codex, static-only sandbox).

```
[BOB] 🟠 First use can fail because Step 3 checks only the vault root, then writes into a new skill-specific directory without ensuring that directory exists. | File: skills/capture-experiment/SKILL.md:98 | Task: 2
[BOB] 🟠 An arbitrary title can produce invalid YAML because it is inserted as an unquoted scalar; common titles containing `: ` or newlines break the frontmatter contract. | File: skills/capture-experiment/assets/note-template.md:2 | Task: 1
[BOB] 🟡 The dependency entries do not state what happens when `digest-github-repo`, `spike`, or `create-prd` is absent, as required by AGENTS.md. | File: skills/capture-experiment/SKILL.md:16 | Task: 2
[BOB] 🟡 "All files live under…" is redundant with Step 3 and ambiguously includes the skill's source/template. | File: skills/capture-experiment/SKILL.md:12 | Task: 2
[BOB] ⚪ Cannot statically verify: the test suite, create-skill validator, and braid checks passed for this change. | File: N/A | Task: general
[BOB] ⚪ Behavioral regression coverage is limited to the reported happy-path fixture; no retained test covers no-title, missing-vault, compacted-window, or no-dead-end behavior. | File: N/A | Task: general
```

FIX:
- Destination leaf is not prepared before writing — skills/capture-experiment/SKILL.md:98 — after confirming `~/bim/` exists, create `~/bim/inbox/automated/capture-experiment/` before writing.
- User-supplied titles are not safely rendered into YAML — skills/capture-experiment/assets/note-template.md:2 — normalize to one line and emit an escaped quoted YAML scalar.
- Dependency absence behavior is undocumented — skills/capture-experiment/SKILL.md:16 — state the non-blocking fallback for each referenced skill.
- Early output-path sentence is redundant and ambiguous — skills/capture-experiment/SKILL.md:12 — delete it and retain the authoritative Step 3 instructions.

VERIFY:
- Validation results are unavailable to static review — run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/capture-experiment`, and `braid --check`.

KNOWN:
- Edge and error behaviors lack retained regression coverage — a model-behavior evaluation harness is outside this docs-only PRD and adding one would be cross-cutting.

Consensus verdicts: R1 fail, R2 pass, R3 pass, R4 fail, R6 pass, R7 fail, R8 pass, R9 fail,
R10 fail, R11 pass, R12 pass, R13 pass.

Doubt verdicts: D1 pass, D2 pass, D3 pass, D4 pass, D5 pass.

## Carl

Generalist lens this cycle — the change has no frontend surface.

`[CARL] ✅ No issues found`

Verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass, R10 pass,
R11 pass, R12 pass, R13 pass.

## Orchestrator verification of Bob's VERIFY item

Bob's sandbox blocks execution, so the gate ran his named checks directly:

- `uv run pytest -q` → **422 passed, 5 skipped, 0 failed**. The 5 skips are pre-existing and
  unrelated to this diff (`skills/survey/scripts/test_survey.py`, "needs the optional
  tree_sitter_language_pack").
- `uv run python3 skills/create-skill/scripts/validate_skill.py skills/capture-experiment` →
  `[OK] Skill is valid!`
- `braid --check` → **not run**. Warden blocks the binary in this session ("unknown command"),
  both as `braid` and by absolute path. Alice independently hit the same block. This check was
  green in the build session; it is unverified in this one and is recorded as such rather than
  claimed.

Verdict: 8 findings
Tests: 422 passed, 0 failed, 5 skipped

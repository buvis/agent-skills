---
prd: docs/dev/project-management/prds/wip/00048-trash-untracked-preview-default-v1.md
review: 1
date: 2026-10-18
head_sha: 2eecabcd536c88465178bc188f8063fdbbe0201b
codex_thread_id: 01a14fd1-5b8e-7613-a6e2-ea2329a8d0d9
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: a99c194c
  carl: c5dc54af
---

# Review: 00048-trash-untracked-preview-default-v1

Diff range: `758bded4fb5c5dd983ae6d53fcd3a1f754c23382..2eecabcd536c88465178bc188f8063fdbbe0201b`

codex_rung_guard: not fired

pack: failed (engram pack exit 1: not inside a registered repo)

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🟡 | The new tests are redundant, beyond the PRD's two named tests. `test_dry_run_without_apply_leaves_the_file_and_writes_no_trash` duplicates `test_preview_moves_nothing`. `test_dry_run_preview_and_apply_report_identical_moved_and_refused` overlaps `test_preview_json_matches_the_apply_run`. Five more `test_dry_run_*` tests plus seven `trash_dest` and `relocate` tests also go beyond the PRD. Merge the overlapping ones and drop the duplicates to cut about 100 lines. The `test_dry_run_with_apply_*` names also contradict their own content. | skills/brush/scripts/test_brush_scripts.py:610 | 3 | ALICE, BLAKE, BOB |
| R2 | [2/4] | 🟡 | Unrelated reformatting of `skills/glean/scripts/glean.py` and `skills/glean/scripts/test_glean.py` (re.I to re.IGNORECASE, wrapped lines, added trailing commas, about 146 changed lines). It is scope creep for a brush-only PRD, and `git status` shows these as uncommitted edits. Revert them or commit them separately. | skills/glean/scripts/glean.py:37 | general | ALICE, CARL |
| R3 | [1/4] | 🟡 | The CHANGELOG has no entry. `trash_untracked.py` now previews by default, so any caller without `--apply` silently stops moving files. That is a user-visible breaking change, and the repo CHANGELOG already carries brush entries for this script (CHANGELOG.md:473). Add a `### Changed` line under `[Unreleased]` such as "**brush**: `trash_untracked.py` previews by default; pass `--apply` to move". | CHANGELOG.md:8 | general | ALICE |
| R4 | [1/4] | 🟡 | Unrelated formatting expands `cmd_scan` to 54 lines, exceeding the 50-line limit. Revert the formatting changes in both glean files. | skills/glean/scripts/glean.py:191 | general | BOB |
| R5 | [1/4] | ⚪ | `_expected_trash` and several tests compute the date with `datetime.date.today()` while `main()` computes its own. A run that crosses midnight can flake. The build session already noted this. Freeze the date or compare against the date taken from the output. | skills/brush/scripts/test_brush_scripts.py:606 | 3 | ALICE |
| R6 | [1/4] | ⚪ | The preview and apply runs can disagree when two paths in one run resolve to the same destination, because preview creates nothing and so computes no `.dup` suffix. The design doc and the `trash_dest` docstring record this, but nothing tests it. This is an accepted limitation. | skills/brush/scripts/trash_untracked.py:90 | 2 | ALICE |
| R7 | [1/4] | ⚪ | `test_relocate_keeps_the_earlier_file_on_a_dest_collision` passes against the pre-change code (the context's fail-first replay flags it). It is a legitimate behaviour-preserving guard for the `relocate()` refactor, so no change is needed. | skills/brush/scripts/test_brush_scripts.py:224 | 1 | ALICE, mech-check |
| R8 | [1/4] | ⚪ | Preview and apply can diverge when the same path is passed twice. Apply moves the file on the first occurrence, so the second reports "missing". Preview never moves it, so both occurrences are listed under `moved`. This is an edge case the spec does not cover. | skills/brush/scripts/trash_untracked.py:133 | general | BLAKE |
| R9 | [1/4] | ⚪ | `trash_dest` reads `.exists()` and a wall-clock `.dup<ts>` suffix, so a preview can name a different destination than the following apply run. Examples are a file landing at the destination in between, or a second-granularity timestamp. The docstring at skills/brush/scripts/trash_untracked.py:93 admits this. It is inherent to the spec's design and is only a note. | skills/brush/scripts/trash_untracked.py:90 | 1 | BLAKE |
| R10 | [1/4] | ⚪ | Human follow-up from the PRD: external callers that omit `--apply` now silently preview and move nothing. The in-repo sweep cannot detect this. Only the two in-repo call sites could be fixed. | N/A | 5 | BLAKE |

The consolidator merged two citation groups after suffix stripping: R1 (`test_brush_scripts.py:610 ~ :155 ~ :612`) and R2 (`glean.py:37 ~ :1`).

The one `[MECH]` finding of this cycle (fail-first replay: `test_relocate_keeps_the_earlier_file_on_a_dest_collision` passes against the pre-change code) was absorbed into R7; `mech-check` is listed among its finders.

## Alice

No Critical or High issues. Every PRD requirement holds: preview moves nothing, creates no `.trash/` and writes no manifest row; preview prints the same `moved`/`refused` JSON as `--apply`; the `DRY-RUN (use --apply)` marker goes to stderr; `--apply` is `store_true` with the specified help text; both documented call sites carry `--apply` and `rg` finds no other in-repo caller.

Findings: R1, R2, R3, R5, R6, R7 above.

R1: pass, R2: pass, R3: pass, R4: pass, R6: pass, R7: pass, R8: pass, R9: pass, R10: pass, R11: pass, R12: pass, R13: pass

## Blake

Blind (PRD-only) lens. Verified against the spec: the `--apply` flag definition and help text; no writes without `--apply` (`relocate()` and `note_manifest()` run only inside `if args.apply:`); the stderr marker; the identical JSON shape in both modes; `trash_dest(root, rel, date)` extracted and called by `relocate()`; both call sites carrying `--apply`; both PRD-named tests present and asserting the acceptance criteria. Ran `uv run pytest -q`: 3940 passed, 9 skipped. No new dependencies or flags beyond `--apply`.

Findings: R8, R9, plus his own notes on test count beyond the PRD (merged into R1) and the external-caller follow-up (R10).

B1-B19: pass

## Bob

Doubt + de-slop lens (codex), after one retry (inlined). The first dispatch returned a lack-of-input refusal (file-reading tools failed, every `R{n}` marked fail, no findings established); the one-retry budget was spent on the inlined-prompt retry, which produced a usable review.

FIX: R4 (`cmd_scan` at 54 lines after the unrelated glean formatting) and R1 (duplicate preview tests).
VERIFY: (none)
KNOWN: (none)

R1: pass, R2: pass, R3: pass, R4: pass, R6: pass, R7: pass, R8: pass, R9: pass, R10: pass, R11: pass, R12: fail, R13: pass

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Gemini lane, UI/design specialist, generalist here (no frontend surface in this diff). One finding: the unstaged glean formatting outside PRD scope (merged into R2).

R1: pass, R2: pass, R3: pass, R4: pass, R6: pass, R7: pass, R8: pass, R9: pass, R10: pass, R11: pass, R12: pass, R13: pass

Verdict: 10 findings
Tests: 3940 passed, 0 failed, 9 skipped (suite run this cycle)

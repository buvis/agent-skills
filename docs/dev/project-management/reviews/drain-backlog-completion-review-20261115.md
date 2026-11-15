---
branch: feature/drain-backlog
review: standalone-completion-20261115
date: 2026-11-15
base: master (0466054; master later gained 2509cb5 and edf1fde, merged in at 597b523)
reviewed_range: master..fd01e31, then the deltas fd01e31..142fd99 and 8816bb9..cb5616f
head_sha: 597b523
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
---

# Completion review: feature/drain-backlog

Scope: the 25 PRDs in the brief (00044 task 14, 00049, 00078, 00098, 00100,
00104, 00108, 00112, 00136-00139, 00143-00150, 00153, 00160, 00162, 00164,
00175), the triage-stub closures, and three commits the work session added
during the review (0c53c8e sweep-fix kills, 142fd99 stubs 00126/00151, 8816bb9
encoded user names). Run standalone, like the 00160 recovery review. Nothing
under `docs/dev/project-management/autopilot/` was read or edited, and
`git diff master..597b523 -- docs/dev/project-management/autopilot` is empty.

## Outcome

**PASS after rework.** The first pass found one HIGH defect that two lenses
confirmed on their own (00175), plus three HIGH reports from Bob. Two of those
were confirmed as regressions this branch introduced, and one was downgraded
to MEDIUM. All confirmed defects are fixed on the branch, each with a
regression test that failed against the old code. The rework passed a second
Codex pass with no findings.

**Not merged.** The brief's `git merge --ff-only` step was withdrawn mid-review.
Public master was force-replaced with a scrubbed line, and this branch still
sits on the old unscrubbed base. The work session cherry-picks the review
commits onto `feature/scrub-drain-backlog`. Skip merge commit 597b523 there and
resolve CHANGELOG.md by keeping both sides.

## Roster and actual backends

| Lens | Backend / model | Verdict |
|---|---|---|
| Alice, consensus | native Claude subagent `autopilot:alice`, `claude-opus-5-5` | FAIL, 1 HIGH, 1 MEDIUM, 5 LOW |
| Blake, blind PRD-only | native Claude subagent `autopilot:blake`, `claude-sonnet-5-5`; no diff, log, reviews or ledgers | FAIL, 1 HIGH, 1 MEDIUM, 5 LOW |
| Bob, doubt + de-slop R1-R5 | Codex CLI `gpt-6-astra`, read-only, inlined prompt | FAIL, 3 HIGH, 1 MEDIUM, 2 LOW |
| Bob, delta 1 (fd01e31..142fd99) | Codex CLI `gpt-6-astra`, inlined | PASS, 2 MEDIUM (both rejected) |
| Bob, delta 2 (8816bb9..cb5616f) | Codex CLI `gpt-6-astra`, inlined | PASS, no findings, R1-R5 pass |

Bob's first dispatch with repository access failed before inference with the
known nested-Seatbelt error (`sandbox_apply: Operation not permitted`). The
inlined retry carried the full 420 KB code diff. The brief's rubric R5 does not
exist in the installed rubric (R1-R4, R6-R13), so Bob's prompt defined R5 as "no
slop".

## Confirmed and fixed

| Ref | Voices | Sev | Defect | Fix |
|---|---|---|---|---|
| F1 | Alice, Blake | HIGH | `check_run.py` imported `custom_idents` from `abap_idents`, then redefined it with a copy of the regexes. The copy shadowed the import, so the PRD 00175 "one home" requirement was not met. | 139c7c9: copy removed; a test asserts `check_run.custom_idents is abap_idents.custom_idents` |
| F2 | Bob | HIGH | `contained()` walked links by raw spelling only. On macOS or Windows, `escape/file` opens the link `Escape -> ../outside` and was not refused. Master's `resolve()` check had caught this, so this was a regression. | 3a536e0: also walks the folded spelling via `_land(..., fold=True)` |
| F3 | Bob | HIGH->MEDIUM | A failed `build_template` ran `rmtree` on its topmost created ancestor, which deletes files another writer placed there. Downgraded: it needs a concurrent writer in a directory the build just created. | 3a536e0: removes staging, then `rmdir`s only empty created parents |
| F4 | Bob | MEDIUM | A completed answer, then `agent_start`, then a cut-off stream still reported success, because `agent_start` never cleared the `agent_end` flag. | 0dbc857: `agent_start` resets `ended`; T51b |
| F5 | Blake | MEDIUM | `docket.py unpublished` warned about a missing store only when no ids printed. PRD 00108's must-have is unconditional. The original 00108 change also lacked a CHANGELOG entry. | cb5616f: warning is unconditional; CHANGELOG entry added |
| F6 | Blake | LOW | A list or dict `verdict` in a glean ledger crashed with an unhashable-type traceback (00112 crash class). | 59c66dc |
| F7 | Alice | LOW | Two glean ledger errors did not name the ledger file. | 353d7f1 |
| F8 | Alice | MEDIUM | `test_glean.py` grew to 886 lines, over the 800-line cap. | 353d7f1: ledger tests moved to `test_glean_ledger.py` (697 + 219 lines) |
| F9 | Bob | LOW | The `os.path.isabs(member.name)` check was dead, because `_archive_name_escapes` refuses every absolute spelling first. | 3a536e0: removed |
| F10 | Alice | LOW | The branch conflicted with master in CHANGELOG.md, so `--ff-only` would fail. | 597b523: merged master, kept both sides |

## Rejected

| Ref | Voice | Claim | Evidence |
|---|---|---|---|
| R1 | Bob | MEDIUM: `staging.rename(dest)` replaces an empty `dest` that appears mid-build. | PRD 00160 line 81 requires refusal only of a non-empty `dest`, and renaming over an empty directory destroys nothing. |
| R2 | Bob | LOW: the absolute-target `_land` test also passes against the old `_land`. | It pins behavior across a rewrite and makes no regression claim; that is legitimate. |
| R3 | Bob delta 1 | MEDIUM: the T51b fixture lacks a first `agent_end`, so it passes before the fix. | `EV_ANSWER` ends with `agent_end` (test_qwen_run.sh:1378); T51b failed before 0dbc857. |
| R4 | Bob delta 1 | MEDIUM: ENOENT from the cleanup `rmdir` masks the build error. | `build_template` re-raises the original error when cleanup fails, and `test_build_template_cleanup_failure_keeps_the_original_errors_own_cause` pins that. |
| R5 | Blake | LOW: cannot confirm that no 00175 selftest case was lost. | `check_run.py --selftest` passes, and Alice traced the merged cases. |

## Deferred

| Ref | Voice | Item |
|---|---|---|
| D1 | Alice | `funnel.main` is 52 lines, `make_corpus` is 52, and a test in `test_funnel_main.py:688` is 72, all over the 50-line guide. Test and helper length only. |
| D2 | Alice | `test_qwen_run.sh` (1606 lines) and `sweep.py` (829 lines) were already over 800 before this branch. |
| D3 | Alice, brief | `.git` refusal gaps: a symlink target inside `.git`, HFS-ignorable code points, and `git~2`. A write through a symlink ancestor is already refused. |
| D4 | Alice, Blake | 00044 native Windows proof: README states hosted Windows CI. Hosted run 43740319487 passed at d52f007; the run for this review's fixes is recorded below. |
| D5 | Blake | 00137 svelte build and jsdom smoke test were not run here (npm). |
| D6 | brief | 00112 four deferred MEDIUMs in the paused autopilot ledger were not read (out of bounds for this review). |
| D7 | review | Pre-existing ruff findings in `document-abap-solution/scripts/*.py` (UP031, B007) and Pyright optional-type warnings in `trees.py` and `glean.py`. They are not from this branch and the gate does not enforce them. |

## Judgement calls (brief items 1-6, 9, 10)

1. Archive lane merges are correct. The moved exec-bit test lives at
   `test_eval_tree_archive_safety_modes.py:487`. 00161 is superseded by
   d368288 (PR #17), per Alice.
2. The 00174 `.git` refusal is sound for the spellings it claims; see D3.
3. Qwen completion is not too strict. It matches the PRD 00049 and 00078 event
   evidence, and F4 tightened it.
4. Glean HARD labels: every reader uses `startswith("HARD:")` or `k[5:]`, so no
   consumer breaks.
5. 00154 stays held. 8816bb9 removed the encoded user names, and the doc-path
   test now covers the encoded form.
6. b18ae73 and fd01e31 do not weaken their tests: `TOO_LONG` is unique to the
   failing member.
9. 0c53c8e's concurrent kills are correct. `_kill_tree` never raises, so
   threads drop no error. The barrier test fails against the old in-turn loop.
10. 8816bb9 has the regex and both positive and negative cases.

## Verification

- `braid --check`: `0 linked, 161 current, 20 ignored, 0 removed, 0 backed up, 0 configured, 0 drift`.
- Gate at fd01e31 (before the fixes): `PASS 4885 FAIL 0 SKIP 12 EXIT 0`.
- Gate at 142fd99: `PASS 4888 FAIL 0 SKIP 12 EXIT 0`.
- Gate at 8816bb9: `PASS 4895 FAIL 0 SKIP 12 EXIT 0`.
- Gate at 597b523 (final): `PASS 4899 FAIL 0 SKIP 12 EXIT 0`.
- `test_qwen_run.sh`: 114 passed, 0 failed.
- Hosted CI: CI_FINAL.

## Probe

The probe branch `feature/drain-backlog-ci` (draft PR #28) is public, and its
tip at d52f007 still held the 28 encoded user-name lines that 8816bb9 fixed.
c28d32c carries 8816bb9's 9 documents and test into it, together with every
review fix. Only the withheld paths (autopilot/, the 00135 PRD and reviews,
intake 00176) still differ from this branch. The probe's history still holds
the old lines; deleting the branch and PR (brief item 8) removes them from the
branch, but GitHub may keep the PR's commits reachable.

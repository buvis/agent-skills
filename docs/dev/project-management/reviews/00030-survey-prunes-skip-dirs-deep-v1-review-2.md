---
prd: dev/local/prds/wip/00030-survey-prunes-skip-dirs-deep-v1.md
review: 2
date: 2026-09-07
head_sha: 0c02b2fe3cd940d75148806331ea7bf7d24ae16e
codex_thread_id: 01a078a4-f8d2-7ed0-b12d-64e267636398
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00030-survey-prunes-skip-dirs-deep-v1

Diff range: `1f70ca5b6ccacd7d8045e53730369e13404cb0b2..0c02b2fe3cd940d75148806331ea7bf7d24ae16e`

codex_rung_guard: not fired

Scope: **incremental** — the rework commits from cycle 1's decision gate (tasks 4, 5, 6). 3 files, 47 insertions, 25 deletions. Bob resumed his cycle-1 codex thread (`--resume-thread 01a078a4-…`), so his verification of prior findings is against his own critique.

pack: unavailable this cycle (`engram pack` exited 1: "not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv"). `(no pack available this cycle)` was substituted for `{PACK_FILE}` and `{PACK_FINDINGS}` in every prompt that takes them. Same failure as cycle 1; it is a gita-registration gap, not a repo fault.

## Reviewers

- Alice (Claude subagent, consensus lens): ✅ Available
- Blake (Claude subagent, blind/PRD-only lens): ✅ Available
- Bob (codex, doubt + de-slop lens): ✅ Available — resumed thread, complete review with all `R{n}` and `D{n}` verdict lines
- Carl (gemini via copilot, `gemini-3.8-flash`): ✅ Available — exit 0, 14.62 AI credits

## Prior-cycle findings: all three reworked items verified resolved

| Cycle-1 finding | Rework | Verified this cycle |
|-----------------|--------|---------------------|
| 🟠 [4/4] `test_skip_dirs_are_pruned_at_every_depth` missing under its PRD-mandated name/fixture/assertion | tasks 4 (`22d7169`, `295b348`) | **Resolved.** The test exists at `test_survey.py:184` with the four PRD-named fixture files and the exact `== ["real.py"]` assertion; `rg` confirms `test_skip_dirs_pruned_at_every_depth_under_top_level_dir` is gone. Alice, Blake and Carl each ran the PRD's own pytest node-id and it passes. |
| 🟠 [1/4] `os.walk` returns non-regular entries; the dropped `is_file()` lets FIFOs/sockets/dangling symlinks into a layer | task 5 (`d63a3eb`) | **Resolved.** `run.py:70-72` filters on `f.is_file()` again; `test_only_regular_files_enter_a_layer` is the fail-first regression test and the replay confirms it **fails against the pre-change code** — the one genuinely fail-first test in this diff. |
| 🟡 [1/4] Descent test inspects absolute-path ancestors | task 6 (`0c02b2f`) | **Resolved as specified** — `test_survey.py:291` now asserts over `Path(dirpath).relative_to(repo).parts`. Bob raises a follow-on about the test not pinning its own change (row 2 below); that is a new finding, not an unresolved one. |

No regression was introduced by the rework: the full suite is green at this HEAD and `_scan_layers` keeps its `(layers, truncated)` shape, `_FILE_CAP` and `Path` values.

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟡 | Task 5's own fix comment reintroduces the literal string the PRD's acceptance gate requires gone: `rg -n "rglob" skills/survey/scripts/run.py` now matches line 69 ("...rglob + is_file() used to filter those"), failing the explicit "prints no match" check even though no functional `rglob` call remains. Trivial fix: reword the comment to avoid the bare token "rglob". | skills/survey/scripts/run.py:69 | 5 | ALICE, BLAKE |
| [1/4] | 🟡 | The descent regression test uses an ordinary temp ancestor, so reverting `relative_to(repo)` would still pass; construct the repo beneath a dot-prefixed ancestor | skills/survey/scripts/test_survey.py:269 | 6 | BOB, mech-check |
| [1/4] | 🟡 | The nested generator used to filter walk entries is harder to read than a direct candidate/filter/append loop | skills/survey/scripts/run.py:70 | 5 | BOB |
| [1/4] | 🟡 | `test_skip_dirs_are_pruned_at_every_depth` passes against the pre-change code at base `1f70ca5b`, so it pins no behavior *this* diff changes | skills/survey/scripts/test_survey.py | general | mech-check |
| [1/4] | ⚪ | Cannot statically verify: cycle-2 tests, skill validation, and braid checks pass | N/A | general | BOB |

**Row 1 is mechanically confirmed, not a reviewer opinion.** Run live this cycle: `rg -n 'rglob' skills/survey/scripts/run.py` → `69:            # special files included; rglob + is_file() used to filter those.` The PRD states that exact command twice — task 1's acceptance and the Success Criteria — as a binary gate, and it does not pass as literally written. Alice rated it ⚪ Low and Blake 🟡 Medium; the consolidator kept the higher severity, which is the right call for a stated Success Criterion.

**Mechanical test checks absorbed:** the fail-first replay's `[MECH] 🟡` line named two touched tests that pass against the pre-change code. `test_pruned_directories_are_never_descended_into` matched Bob's row 2 (same file, same test), so `mech-check` was appended to its finders. `test_skip_dirs_are_pruned_at_every_depth` matched no existing row and was added as row 4. **Read the base before weighing rows 2 and 4:** the replay base is `1f70ca5b`, which already carries the traversal fix, so a pruning test passing there is expected — task 4 was a rename and task 6 a test-scoping change, neither of which alters behavior. The tautological-shapes check found nothing across 33 test functions in 1 test file.

**Consolidation note (fail loud):** Blake emitted a second ⚪ line that is an all-clear (everything the PRD requires preserved is preserved, verified live) rather than a defect. `consolidate_findings.py` folded it onto row 1 on the shared `run.py` file rather than emitting it as its own row. Nothing was lost — it asserts no defect — but the fold is recorded here rather than left silent. No ledger auto-dismissals fired this cycle (`--ledger --ledger-dismiss BLAKE` was passed; Blake re-raised nothing settled).

**Carried-forward checks:** none — cycle 1 wrote no verification-check queue file (`00030-…-checks-1.json` does not exist), because all three of Bob's cycle-1 VERIFY commands were resolved in-cycle with recorded evidence.

## Verification-check queue

No queue file written this cycle. Bob's single VERIFY item named the same three commands as cycle 1, and **all three are resolved with recorded evidence at this exact reviewed HEAD** (`dev/local/autopilot/last-verification.json`, sha `0c02b2fe3cd940d75148806331ea7bf7d24ae16e`), so none is pending a work pass:

- `uv run pytest` → exit 0 (1087 passed, 0 failed, 5 skipped)
- `uv run python3 skills/create-skill/scripts/validate_skill.py skills/survey` → exit 0
- `/Users/bob/.agents/bin/braid --check` → exit 0

Carl independently re-ran the first two plus `braid --check` during his own review and reported them green.

## Follow-up tasks

None created by this skill. Task creation for this cycle's findings belongs to the decision gate (`run-autopilot` Phase 5 classification → Phase 6 `[D2]` task creation), which is what created cycle 1's tasks 4-6 and which must classify each finding (auto-fix / defer / discard) before any task exists. Creating them here would duplicate that and would create tasks for findings the gate discards.

## Alice

Ran the PRD's own acceptance commands live. Confirmed `test_skip_dirs_are_pruned_at_every_depth` exists with the mandated fixture and assertion and passes, the old differently-named test is gone, `is_file()` filtering is restored, and the descent test asserts over repo-relative parts. Found one new issue, which she verified by running the command herself.

```
[ALICE] ⚪ Task 5's own fixed comment reintroduces the literal string the task's acceptance criteria required gone: `rg -n "rglob" skills/survey/scripts/run.py` now matches line 69 ("...rglob + is_file() used to filter those"), failing the explicit "rg -n \"rglob\" ... still prints no match" check even though no functional `rglob` call remains — verified live (`rg -n "rglob" skills/survey/scripts/run.py` → 1 match). Trivial fix: reword the comment to avoid the bare token "rglob". | File: skills/survey/scripts/run.py:69 | Task: 5
```

```
R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: fail
```

R13 fails on the pre-existing `test_survey.py` file-size overrun — a settled cycle-1 deferral, not a new defect.

## Blake

Blind lens, PRD-only. Located the code himself, ran the PRD's Success Criteria commands, and independently reproduced the `rglob`-token gate failure that Alice found. He reached the same conclusion at a higher severity.

```
[BLAKE] 🟡 The PRD's own acceptance gate for Phase 0 task 1 ("`rg -n \"rglob\" skills/survey/scripts/run.py` prints no match") fails: line 69 is a comment reading "special files included; rglob + is_file() used to filter those." Running `rg -n "rglob" skills/survey/scripts/run.py` returns that one hit. The actual code path is correct (no `d.rglob(...)` call remains, `os.walk` fully replaces it, all 49 tests pass, 5 skipped for the optional tree-sitter dep), so this is functionally harmless, but the PRD states this exact `rg` command twice (task acceptance and Success Criteria) as a binary gate, and it does not pass as literally written. | File: skills/survey/scripts/run.py:69 | Task: Phase 0 task 1
[BLAKE] ⚪ `_scan_layers`, `_SKIP_DIRS`, the `(layers, truncated)` return shape, the 50-file `_FILE_CAP`, and `Path` value semantics are all preserved exactly as required; `os.walk` prunes `dirnames` in place before descent (verified live by `test_pruned_directories_are_never_descended_into`, which wraps `run.os.walk` and asserts no recorded `dirpath` ever falls under a `_SKIP_DIRS` or dot-prefixed segment). The depth-1 regression test (`test_build_output_is_skipped_but_ordinary_dirs_are_not`) and both PRD-mandated new tests pass individually and in the full suite (49 passed, 5 skipped — skips are the optional tree-sitter cases, expected when `tree_sitter_language_pack` isn't installed). No new external dependency was introduced (`os` is stdlib), diff is scoped to `run.py` (+12/-1) and `test_survey.py` (+179), and no other file in the repo references `_scan_layers`. This is a well-contained, low-risk fix; noted here only as the positive counterpart to the one finding above. | File: skills/survey/scripts/run.py | Task: general
```

```
B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass
```

B15 fails solely on the `rglob`-token gate above; Blake states the implementation itself is correct.

## Bob

Doubt + de-slop lens (codex, static-only sandbox), resumed from his cycle-1 thread.

```
[BOB] 🟡 The descent regression test uses an ordinary temp ancestor, so reverting `relative_to(repo)` would still pass; construct the repo beneath a dot-prefixed ancestor | File: skills/survey/scripts/test_survey.py:269 | Task: 6
[BOB] 🟡 The nested generator used to filter walk entries is harder to read than a direct candidate/filter/append loop | File: skills/survey/scripts/run.py:70 | Task: 5
[BOB] ⚪ Cannot statically verify: cycle-2 tests, skill validation, and braid checks pass | File: N/A | Task: general
```

```
R1: pass
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: fail
R13: fail
```

R12/R13 fail on the pre-existing 50-line and 800-line overruns, both settled cycle-1 deferrals. R2 fails on his row-2 finding above.

### Doubt buckets

```
FIX:
- The Task 6 test does not reproduce the ancestor condition that caused the original false failure — skills/survey/scripts/test_survey.py:269 — create `repo` beneath a dot-prefixed temporary ancestor so reverting the repo-relative assertion fails the test.
- The regular-file filter uses a nested generator expression — skills/survey/scripts/run.py:70 — replace it with an explicit `for filename in filenames` loop that creates `candidate`, checks `candidate.is_file()`, and appends it.
VERIFY:
- Current runtime results are unavailable — run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/survey`, and `braid --check`.
KNOWN:
- (none)
```

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Backend: copilot, model `gemini-3.8-flash`. No frontend surface in this change; reviewed as a generalist. He ran the full suite, `validate_skill.py`, `braid --check`, all three PRD acceptance node-ids, and confirmed the old test name is gone.

```
[CARL] ✅ No issues found
```

```
R1: pass
R2: pass
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
```

Verdict: 5 findings
Tests: 1087 passed, 0 failed, 5 skipped (reused from last-verification.json at 0c02b2fe3cd940d75148806331ea7bf7d24ae16e)

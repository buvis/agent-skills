---
prd: dev/local/prds/wip/00030-survey-prunes-skip-dirs-deep-v1.md
review: 1
date: 2026-09-06
head_sha: 1f70ca5b6ccacd7d8045e53730369e13404cb0b2
codex_thread_id: 01a078a4-f8d2-7ed0-b12d-64e267636398
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00030-survey-prunes-skip-dirs-deep-v1

Diff range: `927e70003ace82fdd0b03c1050ad42b8cf0c3d6f..1f70ca5b6ccacd7d8045e53730369e13404cb0b2`

codex_rung_guard: not fired

pack: unavailable this cycle (`engram pack` exited 1 twice: "not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv"). `(no pack available this cycle)` was substituted for `{PACK_FILE}` and `{PACK_FINDINGS}` in every prompt that takes them.

Diff-scope note: the branch is `master`, so `gather-context.sh` with no `--since` resolved the base to `master` itself and produced an EMPTY diff. Re-run with `--since <work_start_sha>`, which is the PRD's true full-review range under autopilot (`state.work_start_sha..HEAD`). The context file's "_Diff scope: incremental review_" label is therefore a mislabel of a full review, not an actual incremental cycle.

## Reviewers

- Alice (Claude subagent, consensus lens): ✅ Available
- Blake (Claude subagent, blind/PRD-only lens): ✅ Available
- Bob (codex, doubt + de-slop lens): ✅ Available — one Bash command was refused mid-run by the aegis fact-forcing gate; codex continued and produced a complete review with all `R{n}` and `D{n}` verdict lines
- Carl (gemini via copilot, `gemini-3.8-flash`): ✅ Available

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [3/4] | 🟠 | Task 2's stated acceptance criterion is unmet: no test named `test_skip_dirs_are_pruned_at_every_depth` exists; `uv run pytest "skills/survey/scripts/test_survey.py::test_skip_dirs_are_pruned_at_every_depth" -q` returns exit 4 "not found". Intent is covered by differently-named tests, but the literal task deliverable and fixture/assertion specified in the PRD were not built. | skills/survey/scripts/test_survey.py | 2 | ALICE, BLAKE, BOB |
| [2/4] | 🟡 | File size drift: test_survey.py was already over the 800-line project max before this diff (855 lines) and now sits at 1022 lines after it, worsened by the out-of-scope tests noted above. | skills/survey/scripts/test_survey.py | general | ALICE, CARL |
| [1/4] | 🟠 | `os.walk` can place FIFOs, sockets, and dangling symlinks in `filenames`; removing `is_file()` returns non-regular paths and may block downstream reads | skills/survey/scripts/run.py:68 | 1 | BOB |
| [1/4] | 🟡 | Scope creep: task 2 asked for one test function but commit a034696 added five, two of which (`test_scan_layers_returns_dict_of_path_lists_and_bool_flag`, `test_scan_layers_caps_each_layer_at_50_files`) test pre-existing return-shape/cap behavior unrelated to the depth-pruning fix this PRD is about. | skills/survey/scripts/test_survey.py | 2 | ALICE |
| [1/4] | 🟡 | Tautological tests: `test_scan_layers_returns_dict_of_path_lists_and_bool_flag` (line 311) and `test_scan_layers_caps_each_layer_at_50_files` (line 331) both pass unchanged against the pre-change code (confirmed by the fail-first replay), so they pin no behavior this diff changes. | skills/survey/scripts/test_survey.py | 2 | ALICE, mech-check |
| [1/4] | 🟡 | `os.walk` silently ignores directory-scanning errors because no `onerror` handler is supplied | skills/survey/scripts/run.py:64 | 1 | BOB |
| [1/4] | 🟡 | The descent test inspects absolute-path ancestors, so a dot-prefixed or skipped-name test base causes a false failure | skills/survey/scripts/test_survey.py:298 | 3 | BOB |
| [1/4] | 🟡 | Three overlapping pruning tests and lengthy restating docstrings add substantial redundant coverage | skills/survey/scripts/test_survey.py:184 | 2 | BOB |
| [1/4] | 🟡 | Two touched preservation tests pass against pre-change code and therefore do not pin the traversal change | skills/survey/scripts/test_survey.py:311 | general | BOB, mech-check |
| [1/4] | 🟡 | Task 2 acceptance test test_skip_dirs_are_pruned_at_every_depth was implemented as test_skip_dirs_pruned_at_every_depth_under_top_level_dir with different fixtures and assertions, failing acceptance command 'pytest ...::test_skip_dirs_are_pruned_at_every_depth' | skills/survey/scripts/test_survey.py | 2 | CARL |
| [1/4] | ⚪ | Cannot statically verify: pytest, skill validation, and braid checks pass | N/A | general | BOB |
| [1/4] | ⚪ | Two pre-existing functions exceed the 50-line limit | N/A | general | BOB |
| [1/4] | ⚪ | The changed test module exceeds the 800-line limit | skills/survey/scripts/test_survey.py:987 | general | BOB |

**Consolidation note (fail loud):** `consolidate_findings.py` did NOT merge Carl's row 10 onto the [3/4] row 1, although both name the missing `test_skip_dirs_are_pruned_at_every_depth` in the same file. The true consensus on that finding is **4/4**, not 3/4. Rows 5 and 9 are also the same defect seen by two reviewers plus the mechanical replay. The paraphrase matcher under-counted; no finding was lost.

**Mechanical test checks absorbed:** the fail-first replay's single `[MECH] 🟡` line (2 touched tests pass against the pre-change code) matched existing rows 5 and 9, so `mech-check` was appended to their finders rather than added as a new row. The tautological-shapes check found nothing across 32 test functions in 1 test file.

**Carried-forward checks:** none — this is cycle 1.

## Verification-check queue

No queue file written this cycle. Bob's single VERIFY item named three commands, and **all three were resolved in-cycle with recorded evidence**, so none is pending a work pass:

- `uv run pytest` → exit 0 at this exact HEAD (`dev/local/autopilot/last-verification.json`, sha `1f70ca5b`)
- `uv run python3 skills/create-skill/scripts/validate_skill.py skills/survey` → exit 0 at the same sha
- `braid --check` → run this cycle at `/Users/bob/.agents/bin/braid`: `0 linked, 76 current, 20 ignored, 0 removed, 0 backed up, 0 drift`. The work phase recorded exit 127 for the bare `braid --check`; that was PATH resolution, not a repo problem — `braid` is not on the session PATH but resolves at the absolute path above.

## Alice

Ran the full suite (48 passed, 5 skipped — pre-existing tree-sitter skips), confirmed `rg -n "rglob"` has no match and `os.walk` is inside `_scan_layers`, and confirmed `_scan_layers` has one caller (`_survey`) with its `(dict[str, list[Path]], bool)` contract unchanged. The pruning logic at `run.py:62-69` is correct: `dirnames` is mutated in place before descent.

```
[ALICE] 🟠 Task 2's stated acceptance criterion is unmet: no test named `test_skip_dirs_are_pruned_at_every_depth` exists; `uv run pytest "skills/survey/scripts/test_survey.py::test_skip_dirs_are_pruned_at_every_depth" -q` returns exit 4 "not found". Intent is covered by differently-named tests, but the literal task deliverable and fixture/assertion specified in the PRD were not built. | File: skills/survey/scripts/test_survey.py | Task: 2
[ALICE] 🟡 Scope creep: task 2 asked for one test function but commit a034696 added five, two of which (`test_scan_layers_returns_dict_of_path_lists_and_bool_flag`, `test_scan_layers_caps_each_layer_at_50_files`) test pre-existing return-shape/cap behavior unrelated to the depth-pruning fix this PRD is about. | File: skills/survey/scripts/test_survey.py | Task: 2
[ALICE] 🟡 Tautological tests: `test_scan_layers_returns_dict_of_path_lists_and_bool_flag` (line 311) and `test_scan_layers_caps_each_layer_at_50_files` (line 331) both pass unchanged against the pre-change code (confirmed by the pack's fail-first replay), so they pin no behavior this diff changes. | File: skills/survey/scripts/test_survey.py | Task: 2
[ALICE] 🟡 File size drift: test_survey.py was already over the 800-line project max before this diff (855 lines) and now sits at 1022 lines after it, worsened by the out-of-scope tests noted above. | File: skills/survey/scripts/test_survey.py | Task: general
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
R12: pass
R13: fail
```

## Blake

Blind lens, PRD-only. Located the code himself, confirmed the fix matches the Solution section exactly, ran the PRD's own Success Criteria commands, and reproduced the missing-node-id failure independently.

```
[BLAKE] 🟡 Task 2's mandated test `test_skip_dirs_are_pruned_at_every_depth` (with its specified fixture and `== ["real.py"]` assertion) does not exist under that name; the PRD's own acceptance pytest node-id fails with "not found," though equivalent (and broader) coverage exists under different test names. | File: skills/survey/scripts/test_survey.py | Task: Phase 0, task 2
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

## Bob

Doubt + de-slop lens (codex, static-only sandbox).

```
[BOB] 🟠 Required Task 2 test name, fixture, and exact assertion are absent, so its specified pytest node cannot exist | File: skills/survey/scripts/test_survey.py:184 | Task: 2
[BOB] 🟠 `os.walk` can place FIFOs, sockets, and dangling symlinks in `filenames`; removing `is_file()` returns non-regular paths and may block downstream reads | File: skills/survey/scripts/run.py:68 | Task: 1
[BOB] 🟡 `os.walk` silently ignores directory-scanning errors because no `onerror` handler is supplied | File: skills/survey/scripts/run.py:64 | Task: 1
[BOB] 🟡 The descent test inspects absolute-path ancestors, so a dot-prefixed or skipped-name test base causes a false failure | File: skills/survey/scripts/test_survey.py:298 | Task: 3
[BOB] 🟡 Three overlapping pruning tests and lengthy restating docstrings add substantial redundant coverage | File: skills/survey/scripts/test_survey.py:184 | Task: 2
[BOB] ⚪ Cannot statically verify: pytest, skill validation, and braid checks pass | File: N/A | Task: general
[BOB] 🟡 Two touched preservation tests pass against pre-change code and therefore do not pin the traversal change | File: skills/survey/scripts/test_survey.py:311 | Task: general
[BOB] ⚪ Two pre-existing functions exceed the 50-line limit | File: N/A | Task: general
[BOB] ⚪ The changed test module exceeds the 800-line limit | File: skills/survey/scripts/test_survey.py:987 | Task: general
```

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
R12: fail
R13: fail
```

### Doubt buckets

```
FIX:
- Required `test_skip_dirs_are_pruned_at_every_depth` is missing — skills/survey/scripts/test_survey.py:184 — rename/rewrite the test with the exact four-file fixture and required list assertion.
- Non-regular directory entries now enter layers — skills/survey/scripts/run.py:68 — construct each candidate `Path` and retain it only when `is_file()` is true; add a dangling-symlink or special-file regression test.
- Walk errors are silently swallowed — skills/survey/scripts/run.py:64 — supply an `onerror` callback that re-raises and test that failure path.
- Absolute ancestors pollute the pruning assertion — skills/survey/scripts/test_survey.py:298 — inspect `Path(dirpath).relative_to(repo).parts`.
- Pruning coverage is unnecessarily repetitive — skills/survey/scripts/test_survey.py:184 — retain the two required contract tests, remove overlapping parameterized copies, and shorten implementation-restating docstrings.
VERIFY:
- Required execution results are unavailable — run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/survey`, and `braid --check`.
KNOWN:
- `test_scan_layers_returns_dict_of_path_lists_and_bool_flag` and `test_scan_layers_caps_each_layer_at_50_files` pass pre-change — they intentionally cover tuple/Path/cap invariants the PRD requires preserving, so removing them would reduce required regression coverage.
- `_build_brief` is 63 lines and `test_extension_points_uses_file_path_not_layer_name` is 57 lines — both violations predate this diff and those functions are outside the traversal tasks.
- `test_survey.py` already exceeded 800 lines before this diff — splitting the pre-existing suite is broader than this traversal PRD.
```

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Backend: copilot, model `gemini-3.8-flash`. No frontend surface in this change; reviewed as a generalist.

```
[CARL] 🟡 Task 2 acceptance test test_skip_dirs_are_pruned_at_every_depth was implemented as test_skip_dirs_pruned_at_every_depth_under_top_level_dir with different fixtures and assertions, failing acceptance command 'pytest ...::test_skip_dirs_are_pruned_at_every_depth' | File: skills/survey/scripts/test_survey.py | Task: 2
[CARL] ⚪ File size: skills/survey/scripts/test_survey.py is 1022 lines, exceeding the 800-line limit (was 855 lines before diff) | File: skills/survey/scripts/test_survey.py | Task: general
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

Verdict: 13 findings
Tests: 1086 passed, 0 failed, 5 skipped (reused from last-verification.json at 1f70ca5b6ccacd7d8045e53730369e13404cb0b2)

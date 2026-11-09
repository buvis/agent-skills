---
prd: docs/dev/project-management/prds/wip/00131-crafted-template-archive-escapes-directory-v1.md
review: 1
date: 2026-10-30
head_sha: a5bd732a842505fb115b37e672e4e84179294909
codex_thread_id: 01a18b18-8e99-7e92-8f99-e4733df4144b
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: 8f997bdb
  carl: f089460e
---

# Review: 00131-crafted-template-archive-escapes-directory-v1

Diff range: `b0c6bf24b9e0223588decabb8244babd7d0e9f43..a5bd732a842505fb115b37e672e4e84179294909`

codex_rung_guard: not fired

pack: ok

## Review Summary

Reviewed: 2 completed tasks
PRDs checked: 00131-crafted-template-archive-escapes-directory-v1.md

### Agent Status

- Alice: ✅ Available (consensus lens, engine `legacy`)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (codex, doubt lens D1-D5 + de-slop)
- Carl: ⚠️ Unavailable: gemini-run backend `copilot` model `gemini-3.8-flash` returned exit 1, "You have exceeded your monthly quota". One-off runtime failure, not exit 4, so not latched for the batch.
- Eve: ⏸️ Disabled: resolved doubt reviewer is `codex` and no task was implemented by codex, so the codex doubt-roster guard did not fire.

Consolidation ran via `consolidate_findings.py` (no ledger file on cycle 1). Its
paraphrase merge folded three citations in `trees.py` onto row R1 after suffix
stripping (`:125` ~ `:135` ~ `:160`), and two citation pairs onto R2 and R3.
One consequence is visible and deliberate: Alice's separate 🟡 "the new
`os.path.isabs(member.name)` refusal has no test" was merged into R1 and its
text no longer appears in the table. It is preserved verbatim in Alice's
section below and must be addressed with R1.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | 🟠 | Compat branch (`archive.extractall(dest)` with no filter) still lets a hardlink member through. `_refuse_duplicate_or_crossing_members` never inspects `islnk()` members. A hand-built tar with one `LNKTYPE` member `h` -> `../outside/secret.txt` passed the preflight, the unfiltered extract created `dest/h`, and its inode equalled the outside file's. On the `filter="data"` branch the same member raises `tarfile.LinkOutsideDestinationError` (a `FilterError`) after a partial extract, not the `TreeError` the PRD requires. The PRD's "missing runtime support must never silently select unrestricted extraction" is therefore unmet, and the design's claim that the preflight "has proven every member's ancestry stays inside dest" is false for hardlinks. Fix: refuse `islnk()` members (and non-regular, non-dir, non-symlink members) with a `TreeError`, add a test for it, and add the missing test for the `os.path.isabs(member.name)` refusal | skills/use-qwen/scripts/eval_harness/trees.py:125 | 1 | ALICE, BLAKE |
| R2 | [2/3] | 🟠 | `test_build_template_s_compatibility_path_still_raises_the_omitted_filter_warning` asserts that `DeprecationWarning` fires with `data_filter` removed. That state does not exist on a real runtime: on 3.12 the warning machinery is present and only `data_filter` was deleted; on a genuine pre-backport 3.10 there is no warning machinery, so `pytest.raises` fails DID NOT RAISE; on 3.14 the data filter is the default and it also fails. The test pins an artifact of the monkeypatch, not a contract, and it reverses PRD task 2, which requires the compatibility branch not to warn. It never verifies successful sealing on that branch either. Assert only what is portable: the compatibility branch seals the tree and emits no omitted-filter warning | skills/use-qwen/scripts/test_eval_tree_links.py:704 | 2 | ALICE, BLAKE |
| R3 | [3/3] | 🟡 | Several new tests pass against the pre-change code, so they do not pin the fix. Overlaying the new test file on base b0c6bf2: 6 failed, 10 passed. Passing at base: `escaping-link-then-directory`, `directory-then-escaping-link` and `safe-link-then-escaping-link-write-through`, because base's dict walk still sees the escaping link; all three `ANCESTOR_CROSSINGS` cases also pass at base, because each fixture's symlink already escapes and the old symlink-only walk catches it. The PRD's "reject member paths whose ancestors cross symlinks" requirement, and the design's "case the current code cannot catch", are therefore pinned by no base-failing test. The mechanical fail-first replay reports 9 touched tests passing at base. Add a case whose symlink is safe independently but whose file-member traversal escapes, or drop the per-member `_land` loop at trees.py:142-143 and record the redundancy | skills/use-qwen/scripts/test_eval_tree_links.py:511 | 1 | ALICE, BOB, mech-check |
| R4 | [1/3] | 🟠 | Normalizing before `_land` erases security-relevant traversal: `alias -> .` plus member `alias/../outside/secret.txt` passes preflight as `outside/secret.txt`. Unfiltered extraction can overwrite the outside sentinel; filtered extraction can raise an untranslated tarfile error. Validate original path traversal before normalization and preserve the TreeError contract; add this regression on both branches. | skills/use-qwen/scripts/eval_harness/trees.py:137 | 1 | BOB |
| R5 | [1/3] | 🟡 | No CHANGELOG.md entry for a containment security fix that changes user-visible refusal behaviour (duplicate and absolute members now raise `TreeError`). CHANGELOG.md already carries `**use-qwen**:` entries under Fixed, so the project convention applies. Add one under `[Unreleased]` / Fixed | CHANGELOG.md | general | ALICE |
| R6 | [1/3] | 🟡 | The spec says to reject any member whose parent path crosses an archive symlink. `_refuse_duplicate_or_crossing_members` rejects only a crossing that `_land` resolves to an escape, a `..` past the root, an absolute target or a cycle. A file under a symlink that stays inside the tree is accepted. Safe internal links are a stated "preserve" item, so this reading is arguable, but it is looser than the written rule. The tests encode the looser rule, and no test pins the strict reading or its relaxation. | skills/use-qwen/scripts/eval_harness/trees.py:141 | 1 | BLAKE |
| R7 | [1/3] | 🟡 | Duplicate detection uses `posixpath.normpath` on the raw name. It does not fold case or Unicode, so two names that collide on a case-insensitive filesystem (macOS default) pass the preflight. On the compatibility path nothing else catches this, and the data filter does not catch it either. Two entries such as `Escape` as a link and `escape/x` as a file, which the preflight sees as unrelated, can still alias on such a host. | skills/use-qwen/scripts/eval_harness/trees.py:137 | 1 | BLAKE |
| R8 | [1/3] | 🟡 | `_land` permits members beneath safe symlinks, contrary to the PRD's ancestor-crossing refusal requirement. With `alias -> pkg`, `alias/file` can overwrite `pkg/file` despite distinct normalized names. Explicitly reject symlink ancestors and test this alias collision. | skills/use-qwen/scripts/eval_harness/trees.py:142 | 1 | BOB |
| R9 | [1/3] | 🟡 | The compatibility warning test requires the warning that task 2 requires absent, and never verifies successful sealing. Deleting `data_filter` leaves the current runtime's warning machinery intact, so this does not model an older runtime. Replace the expected-warning assertion with faithful compatibility coverage and successful sealing under the specific warning-as-error filter. | skills/use-qwen/scripts/test_eval_tree_links.py:459 | 2 | BOB |
| R10 | [1/3] | ⚪ | The helper's design contract returned the symlink map as `dict[str, str]`. The implementation returns `None`, and the assumptions ledger records the choice. Fine, but the design doc still shows the old signature and docstring, which now disagree with the code | docs/dev/project-management/designs/00131-crafted-template-archive-escapes-directory-v1-design.md:130 | 1 | ALICE |
| R11 | [1/3] | ⚪ | `dest.mkdir(parents=True, exist_ok=True)` runs before the preflight, so a refused archive leaves an empty destination directory behind. The tests assert only that it is empty. The spec requires refusal before a successful template is recorded, which holds. | skills/use-qwen/scripts/eval_harness/trees.py:154 | 1 | BLAKE |
| R12 | [1/3] | ⚪ | Blake did not rerun the suite, as the gate instructed. The gate reported exit 0 with no parsed counts, so he could not confirm from it that the new regressions fail against the pre-change code. The preflight logic and the duplicate, ancestor-crossing and safe-link fixtures do match the spec's required cases. | N/A | general | BLAKE |

## Mechanical checks

- Tautological test shapes: 18 test functions checked in 1 test file, no `[MECH]` line raised.
- Fail-first replay: one `[MECH]` 🟡 line — 9 touched tests pass against the pre-change code in `skills/use-qwen/scripts/test_eval_tree_links.py`. Absorbed into R3, whose finders therefore carry `mech-check`.

## Alice

[ALICE] 🟠 Compat branch (`archive.extractall(dest)` with no filter) still lets a hardlink member through. `_refuse_duplicate_or_crossing_members` never inspects `islnk()` members. I ran a hand-built tar in a temp dir with one `LNKTYPE` member `h` -> `../outside/secret.txt`. The preflight passed, the unfiltered extract created `dest/h`, and its inode equalled the outside file's. That is a link to an outside file, so a later write or a `git add -A` reaches it. PRD "Must have" says missing runtime support must never silently select unrestricted extraction, and the design's claim that preflight "has proven every member's ancestry stays inside dest" is false for hardlinks. On the `filter="data"` branch the same member raises `tarfile.LinkOutsideDestinationError` (a `FilterError`) after a partial extract, not the `TreeError` the PRD requires. Fix: refuse `islnk()` members (and non-regular, non-dir, non-symlink members) in the helper with a `TreeError`, and add a test for it. The design review log raised hardlinks; the helper's docstring and the assumptions log leave them out | File: skills/use-qwen/scripts/eval_harness/trees.py:125 | Task: 1

[ALICE] 🟡 Several new tests pass against the pre-change code, so they do not pin the fix. I overlaid the new test file on base b0c6bf2 and ran the crafted-archive tests: 6 failed, 10 passed. The failures were `escaping-link-write-through-then-safe-link`, `same-path-under-two-spellings`, `safe-link-then-directory`, `file-then-directory`, `two-files` and the data-filter warning test. Passing at base: `escaping-link-then-directory`, `directory-then-escaping-link` and `safe-link-then-escaping-link-write-through`, because base's dict walk still sees the escaping link. All three `ANCESTOR_CROSSINGS` cases also pass at base. The PRD's "reject member paths whose ancestors cross symlinks" requirement and the design's "case the current code cannot catch" test (a non-symlink member under a link, with the link's own name unique) are therefore not pinned by any base-failing test. Also, a non-symlink member beneath an accepted link always lands inside the tree, so the per-member `_land` loop at trees.py:142-143 may add nothing beyond the duplicate refusal. Either build a case that fails at base (a case where the per-member walk matters), or drop the loop and note the redundancy | File: skills/use-qwen/scripts/test_eval_tree_links.py:511 | Task: 1

[ALICE] 🟡 `test_build_template_s_compatibility_path_still_raises_the_omitted_filter_warning` asserts that `DeprecationWarning` fires with `data_filter` removed. That state does not exist on a real runtime. On 3.12 the tarfile warning machinery is present and only `data_filter` was deleted. On a genuine pre-backport 3.10 there is no warning machinery, so `pytest.raises` fails with DID NOT RAISE. On 3.14, where the default is the data filter, it also fails. The test pins an artifact of the monkeypatch, not a contract. It also reverses PRD task 2, which says the compat branch must not warn. The deviation is recorded in the deferred log, but the test should assert only what is portable: the compat branch seals the tree. It could also assert that it raises nothing beyond the omitted-filter warning, without requiring the warning to fire | File: skills/use-qwen/scripts/test_eval_tree_links.py:704 | Task: 2

[ALICE] 🟡 The new `os.path.isabs(member.name)` refusal ("is absolute") has no test. The design called this check required for correctness on the no-filter branch. Add a crafted-archive case with an absolute member name | File: skills/use-qwen/scripts/eval_harness/trees.py:135 | Task: 1

[ALICE] 🟡 No CHANGELOG.md entry for a containment security fix that changes user-visible refusal behaviour (duplicate and absolute members now raise `TreeError`). CHANGELOG.md already carries `**use-qwen**:` entries under Fixed, so the project convention applies. Add one under `[Unreleased]` / Fixed | File: CHANGELOG.md | Task: general

[ALICE] ⚪ The helper's design contract returned the symlink map as `dict[str, str]`. The implementation returns `None`, and the assumptions ledger records the choice. Fine, but the design doc still shows the old signature and docstring, which now disagree with the code | File: docs/dev/project-management/designs/00131-crafted-template-archive-escapes-directory-v1-design.md:130 | Task: 1

Alice ran `test_eval_tree_links.py` at HEAD: 54 passed, 1 warning (the DeprecationWarning from the monkeypatched no-filter branch). She removed her temporary base worktree afterwards.

R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: fail
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: pass

## Blake

[BLAKE] 🟠 `build_template` still takes an unrestricted extraction path. When `tarfile.data_filter` is missing it runs a bare `archive.extractall(dest)`. The spec says missing runtime support must never silently select unrestricted extraction and requires an equivalent safe compatibility path. The fallback is only the hand-rolled preflight, and that preflight skips hardlink or device members and other member types the data filter would reject. It also runs without the filter's mode and ownership normalization. This is not the "explicit safe extraction" of requirement 4. | File: skills/use-qwen/scripts/eval_harness/trees.py:160 | Task: 1

[BLAKE] 🟠 `test_build_template_s_compatibility_path_still_raises_the_omitted_filter_warning` asserts that the compatibility branch emits the omitted-filter DeprecationWarning. That is the unfiltered extractall call. It makes the unsafe fallback the tested contract, which is the opposite of finding 42's "remove omitted-filter warnings through explicit safe extraction". The test also depends on the runtime: it fails with "DID NOT RAISE" on any runtime where `extractall` has no `filter` support and does not warn. No test shows the compatibility branch being free of the warning or safe. | File: skills/use-qwen/scripts/test_eval_tree_links.py:459 | Task: 2

[BLAKE] 🟡 The spec says to reject any member whose parent path crosses an archive symlink. `_refuse_duplicate_or_crossing_members` rejects only a crossing that `_land` resolves to an escape, a `..` past the root, an absolute target or a cycle. A file under a symlink that stays inside the tree is accepted. Safe internal links are a stated "preserve" item, so this reading is arguable, but it is looser than the written rule. The tests encode the looser rule, and no test pins the strict reading or its relaxation. | File: skills/use-qwen/scripts/eval_harness/trees.py:141 | Task: 1

[BLAKE] 🟡 Duplicate detection uses `posixpath.normpath` on the raw name. It does not fold case or Unicode, so two names that collide on a case-insensitive filesystem (macOS default) pass the preflight. On the compatibility path nothing else catches this. The data filter does not catch it either. Two entries such as `Escape` as a link and `escape/x` as a file, which the preflight sees as unrelated, can still alias on such a host. | File: skills/use-qwen/scripts/eval_harness/trees.py:137 | Task: 1

[BLAKE] ⚪ `dest.mkdir(parents=True, exist_ok=True)` runs before the preflight, so a refused archive leaves an empty destination directory behind. The tests assert only that it is empty. The spec requires refusal before a successful template is recorded, which holds. | File: skills/use-qwen/scripts/eval_harness/trees.py:154 | Task: 1

[BLAKE] ⚪ I did not rerun the suite, as the gate says. The gate reports exit 0 with no counts, so I could not confirm that the new regressions fail against the pre-change code. The preflight logic and the duplicate, ancestor-crossing and safe-link fixtures do match the spec's required cases. | File: N/A | Task: general

B1: fail
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: fail
B11: pass
B12: pass
B13: pass
B14: fail
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

FIX:
- [BOB] 🟠 Normalizing before `_land` erases security-relevant traversal: `alias -> .` plus member `alias/../outside/secret.txt` passes preflight as `outside/secret.txt`. Unfiltered extraction can overwrite the outside sentinel; filtered extraction can raise an untranslated tarfile error. Validate original path traversal before normalization and preserve the TreeError contract; add this regression on both branches. | File: skills/use-qwen/scripts/eval_harness/trees.py:137 | Task: 1
- [BOB] 🟡 `_land` permits members beneath safe symlinks, contrary to the PRD's ancestor-crossing refusal requirement. With `alias -> pkg`, `alias/file` can overwrite `pkg/file` despite distinct normalized names. Explicitly reject symlink ancestors and test this alias collision. | File: skills/use-qwen/scripts/eval_harness/trees.py:142 | Task: 1
- [BOB] 🟡 The compatibility warning test requires the warning that task 2 requires absent, and never verifies successful sealing. Deleting `data_filter` leaves the current runtime's warning machinery intact, so this does not model an older runtime. Replace the expected-warning assertion with faithful compatibility coverage and successful sealing under the specific warning-as-error filter. | File: skills/use-qwen/scripts/test_eval_tree_links.py:459 | Task: 2
- [BOB] 🟡 Mechanical replay reports nine cases passing against base. Benign controls are appropriate, but all three ancestor fixtures already contain escaping symlinks detected by the old symlink-only walk; none pins the newly added member walk. Add a case whose symlink is safe independently but whose file-member traversal escapes. | File: skills/use-qwen/scripts/test_eval_tree_links.py:291 | Task: 1

VERIFY:
- (none)

KNOWN:
- (none)

R1: fail
R2: fail
R3: pass
R4: fail
R6: pass
R7: fail
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

## Carl

Carl: unavailable (gemini-run backend `copilot`, model `gemini-3.8-flash`, exit 1: "You have exceeded your monthly quota"). No output file was published; nothing was consolidated for him. Not exit 4, so Carl is not latched unavailable for the batch.

## Decision gate (cycle 1)

Not converged: R1, R2 and R4 are unresolved HIGH findings. Cycle 1 of cap 2, so
rework is allowed. No CRITICAL row, so no rework design ran.

- R1, R2, R3, R4 — fix. `autopilot review-close --batch-id decision-gate --default-tier sonnet` grouped them into tasks 3 and 4.
- R5 — deferred to batch end. `review-close` refuses a single-voice medium as a task (`single_voice_fix`), but rules/changelog.md is a blocking project rule, so the CHANGELOG obligation is recorded in `deferred_decisions` instead of discarded.
- R6, R7, R8, R9 — discarded, single-voice. R6 and R8 are one defect two reviewers raised in unmerged wording, and its substance is written into R4's fix task; R9 is fully duplicated by R2.
- R10, R11, R12 — discarded, single-voice. R11 and R12 are not defects: each reviewer's own text concedes the point.

Every disposition is recorded with its reason in
`00131-crafted-template-archive-escapes-directory-v1-ledger.json`, so a
re-raise next cycle is auto-dismissed with the reason visible.

Verdict: 12 findings
Tests: 4252 passed, 9 skipped (suite run this cycle at a5bd732, exit 0; counts read from docs/dev/tmp/gate-00131-c1.log because the verify parser does not recognise this pytest summary form)

# Decision Audit Log: 00045-survey-single-read-and-log-time-trim-v1

PRD: `00045-survey-single-read-and-log-time-trim-v1.md`
Started: 2026-10-18T15:20:24Z
Completed: 2026-10-18T15:20:24Z
Autonomous: 25  |  Deferred: 1  |  Doubts: 0

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: Redundant tests: test_survey_trim.py repeats work the PRD-named tests already do. It defines a second _reference_trim at test_survey_trim.py:185, duplicating test_survey_brief.py:444. It defines a second test_trim_encodes_a_logarithmic_number_of_times at test_survey_trim.py:243, duplicating test_survey_brief.py:472. Its budget-sweep test overlaps test_trim_matches_the_pop_loop_byte_for_byte. Keep one oracle and one call-count test, for example by importing the reference from one place or deleting the weaker copy. The 29 tests in this file that pass against the pre-change code are the behaviour-preserving pins the sweep makes redundant

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: Contract deviation, accepted in the design but not fully met: _survey skips any file absent from texts (run.py:435) instead of passing texts.get(f) as the contract states. Behaviour is equivalent, because both extractors return [] on OSError. But an unreadable file is still attempted twice, once in _read_sampled_texts (run.py:416) and once in the _compute_error_style fallback (run.py:254). That is strictly "read more than once" for the failing case. Impact is negligible

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: Unreadable file failing initial read is re-read from disk in _compute_error_style

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: Redundant tests: test_survey_single_read.py:73 (reads each sampled file exactly once) and :192 (the same check beyond 50 files) re-assert the single-read rule that test_no_sampled_file_is_read_from_disk_twice (test_survey.py:387) already pins. The new file is useful for the empty-text, over-50-file, unreadable-file and fresh-per-call cases. Fold the exact-once checks into the PRD-named test, or drop the overlap

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: _read_sampled_texts omits if f not in texts guard specified in task contract

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: _read_sampled_texts is a new helper not listed under the PRD's "New symbols". It is private and the PRD only names _encoded_len

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: R3 (3/4, high): unrelated glean formatter changes said to be riding in this PRD diff

**Choice**: discarded

**Rationale**: git log 370f43ba5633..HEAD -- skills/glean/scripts/glean.py returns no commits (control on run.py returns 5): the glean edits are uncommitted working-tree state predating this session, included by gather-context.sh. Nothing landed in this PRD commit range; reverting a human uncommitted edit would be destructive. Carl cmd_scan 54-line row merged into R3 and is discarded with it.

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: R9-R11 (mech-check, medium): 49 touched tests pass against the pre-change code

**Choice**: discarded

**Rationale**: Behavior-preserving refactor. The PRD specifies byte-identical trimmer output and unchanged observable survey output, so output-equality tests pass at base by design. The PRD fail-first pin test_no_sampled_file_is_read_from_disk_twice does fail at base; the replay reports 36 of 85 touched tests failing there.

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: R1,R2,R4,R6,R7,R8: duplicate test oracles and the unreadable-file double read attempt

**Choice**: auto-fix via three [D1] rework tasks (7,8,9) at sonnet

**Rationale**: R4 is the only unresolved high and shares its root cause with R2/R7 (texts.get(f) threading plus caching a failed read so _compute_error_style does not retry it). R1/R6 are mechanical test-duplication removals, R8 is a one-line PRD New-symbols correction. No CRITICAL in the cycle, so no rework design was run; cycle 1 < rework_cap 5, so the gate reworks rather than caps.

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: run.py:254 Unreadable file failing initial read is re-read from disk in _compute_error_style

**Choice**: discard

**Rationale**: fix conflicts with pinned contract tests test_error_style_without_usable_texts_reads_disk and test_error_style_reads_disk_for_files_missing_from_texts, which require _compute_error_style to fall back to disk for any file absent from a provided (possibly sparse) texts mapping regardless of cause; changing this breaks the function general contract, not just the _survey call site

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: PRD-named tests test_trim_matches_the_pop_loop_byte_for_byte and test_trim_encodes_a_logarithmic_number_of_times were deleted from test_survey_brief.py by cycle-1 rework commits 796d230 and f69b8b4; both PRD acceptance commands now exit 4 (Carl ran them). Cycle 2 R2/R3, 3 of 4 reviewers.

**Choice**: auto-fix via [D2] task: restore both tests with the PRD stated parameters in test_survey_brief.py, remove the test_survey_trim.py copies of exactly those two, keep one shared oracle

**Rationale**: Protocol B (recurring issue: cycle-1 dedup caused it). Research verdict proceed: the PRD names both tests, their file and their parameters in Tasks, Success Criteria and Module Exports, so the PRD contract outranks the dedup that removed them. The fix is additive (restores tests) and does not touch production signatures.

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: An unreadable sampled file is read up to four times: _read_sampled_texts leaves the failed read uncached, texts.get(f) returns None so _extract_file_symbols re-reads it, and _compute_error_style reads it again. The cycle-1 fix that restored texts.get(f) made this worse. Cycle 2 R1, 3 of 4 reviewers.

**Choice**: auto-fix via [D2] task: cache a failed read as empty text in _read_sampled_texts and assert exactly one attempted read in the unreadable-file test

**Rationale**: Protocol B (recurring: prior cycle R2/R4 covered the same path). Research verdict proceed: both extractors and the error-style scan already treat empty text as no content, so caching the empty string is behavior-preserving and makes the PRD must-have no file is read more than once literally true. Alice and Bob independently proposed this exact fix; the alternative was editing the PRD to record the exception, which would weaken a must-have to avoid a two-line change.

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: Cycle-1 rework deleted test_survey_reads_each_sampled_file_exactly_once, the only test covering an empty-text file being read once, leaving the empty.py fixture unused for its stated purpose, the _build_repo docstring stale and two _count_reads(monkeypatch) spy calls vestigial. Cycle 2 R4, Alice.

**Choice**: auto-fix via [D2] task: restore empty-file read-count coverage, fix the stale docstring, and either assert on or drop the vestigial spy calls

**Rationale**: Auto-fix: additive test coverage for a real hole (flipping text is None to if not text at run.py:139 or :184 would re-read empty files and no remaining test would fail). No signature, type or schema change.

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: Four low-impact findings: the unreachable if f in texts guard (R5), the tree-sitter path unverified because tree-sitter is absent here (R6), extra test coverage beyond the spec (R7), and one touched brief test that passes against the pre-change code (R8).

**Choice**: settled in the decisions ledger, no task created: R5, R6 and R7 as settled-deferral, R8 as discarded

**Rationale**: Each reason is recorded verbatim in docs/dev/project-management/reviews/00045-survey-single-read-and-log-time-trim-v1-ledger.json so no later cycle re-argues them. R5 would re-open cycle-1 R7 if removed; R6 is environmental (the conditional tests skip without tree-sitter); R7 is called not harmful by its own finder and its layout half is fixed by the R2/R3 task; R8 is a pre-existing brief test the dedup commit merely touched, pinning output the PRD specifies as unchanged.

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: Bob (codex) refused the first dispatch for lack of input: sandbox_apply: Operation not permitted before he could read the staged context and diff, the same failure shape as cycle 1. His twelve R verdicts were all fail with the note that they indicate unavailable evidence, not confirmed defects.

**Choice**: logged and continued: one inlined retry per retry-policy.md, with the context and diff inlined verbatim (108 KB prompt), which produced a usable review

**Rationale**: Graceful degradation per the Safety Checks table: a transient reviewer error must not break an unattended run. Treating the refusal verdicts as real would have poisoned consolidation with twelve false rule failures, so the first run was closed as lack-of-input and only the retry output was consolidated. No tier escalation and no reviewer dropped: all four lenses reported.

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: The unreadable-file path got worse with the rework. Before, an unreadable file was attempted twice (`_read_sampled_texts`, then `_compute_error_style`). Now `texts.get(f)` is None, so it is also re-read inside `_extract_file_symbols`. That is up to four attempts with tree-sitter present (initial read, tree-sitter read, regex fallback, error-style scan), or up to three in degraded mode. This violates the PRD must-have "no file is read more than once", though the design accepts it. `test_survey_unreadable_file_is_skipped_without_error` (`skills/survey/scripts/test_survey_single_read.py:111`) never counts attempts, so nothing pins the count either way. Either record failed reads in `_read_sampled_texts` (for example as `""`, with a test asserting one attempt), or record the exception in the PRD

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: Two spec-mandated tests are not where, or what, the PRD says. `test_trim_matches_the_pop_loop_byte_for_byte` does not exist anywhere. A sweep test named `test_trim_matches_reference_pop_loop_across_a_budget_sweep` sits in a different file, skills/survey/scripts/test_survey_trim.py:217. The log-bound test is in skills/survey/scripts/test_survey_trim.py:243 rather than skills/survey/scripts/test_survey_brief.py. It uses 1000 lines of ~40 chars and a `ceil(log2(n+1))+2` bound, not the specified 600 lines at 5120 bytes with `<= 12`. The acceptance commands `pytest ...test_survey_brief.py::test_trim_matches_the_pop_loop_byte_for_byte` and `...::test_trim_encodes_a_logarithmic_number_of_times` cannot pass as written: skills/survey/scripts/test_survey_brief.py defines neither test. Late commits 796d230 and f69b8b4 deleted the PRD-named tests as "duplicated". The behavior is covered, but the contractual symbols and locations are gone.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: The PRD-named test `test_trim_matches_the_pop_loop_byte_for_byte` no longer exists anywhere in the repo; rework commit 796d230 deleted it from `test_survey_brief.py`. The PRD (Tasks, Success Criteria, Module test_survey_brief.py Exports) requires it in that file, runnable as `test_survey_brief.py::test_trim_matches_the_pop_loop_byte_for_byte`. `test_trim_encodes_a_logarithmic_number_of_times` now lives only in `test_survey_trim.py`, not in `test_survey_brief.py` as the PRD specifies. The replacement `test_trim_matches_reference_pop_loop_across_a_budget_sweep` has a different name and file. Restore the PRD names and locations, for example by moving the oracle and the two named tests into `test_survey_brief.py`, or update the PRD if relocation is intended

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: The rework deleted `test_survey_reads_each_sampled_file_exactly_once`, which was the only test covering an empty-text file read once. Its docstring said an implementation that treats "" as missing "re-reads empty.py". `text is None` is checked at `skills/survey/scripts/run.py:139` and `skills/survey/scripts/run.py:184`. Changing either to `if not text` would re-read empty files and no remaining test fails: `test_no_sampled_file_is_read_from_disk_twice` and the over-fifty test have no empty file, and the other `test_survey_single_read.py` tests do not count reads. The `empty.py` fixture is now unused for its stated purpose, and the `_build_repo` docstring at `skills/survey/scripts/test_survey_single_read.py:40` is stale. Add an `empty.py` to `test_no_sampled_file_is_read_from_disk_twice` or the over-fifty test, or keep a narrow empty-file read-count test

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: R4 (low): task-2 acceptance literal reading vs the primary read in _read_sampled_texts

**Choice**: settled deferral (ledgered)

**Rationale**: The primary read IS the single read the must-have asks for; no change can satisfy the literal wording without a second read.

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: R6/R7 (medium, mech-check): three restored tests pass against the cycle-2 base

**Choice**: settled deferral (ledgered)

**Rationale**: Restoration of tests for behavior that landed in cycle 1, so the incremental base already contains it; the pins still fail against the mutations they target.

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: The unreadable-file fix in `_read_sampled_texts` (`texts[f] = ""`) is not pinned by any test. `test_survey_unreadable_file_is_skipped_without_error` only checks the brief output, which is identical with the old `pass`. The single-read tests do not count attempts on a failing file. Reverting run.py:421 to `pass` would therefore leave the suite green, and the cycle-2 R1 suggestion to add a test asserting one attempt was not taken. Add a test that fails reads for one file with `OSError` and asserts exactly one attempt, for example by counting calls in `failing_read` at skills/survey/scripts/test_survey_single_read.py:121.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: The restored equality test pairs each shape with one budget; the PRD requires every shape at all four budgets. Iterate over the four shapes × four budgets.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: The encode-count assertion accepts zero calls, so restoring the original inline pop loop would pass this performance test. Assert `1 <= call_count["n"] <= 12`; retain the separate output oracle.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T15:20:24Z

**Decision**: The byte-for-byte trim test pairs one input with one budget (0, 64, 512, 5120). The PRD acceptance could be read as every case at every budget. Coverage is adequate but not a full cross-product.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [deferred] 2026-10-18T15:20:24Z

**Decision**: Scope creep: _build_brief was split into three new helpers (_brief_naming_section, _brief_index_section, _brief_extension_section). No PRD task or the design doc asks for this. The binary-search and single-read changes do not touch brief assembly. Revert it to keep the diff traceable, or record it as a separate pre-existing function-size cleanup

**Rationale**: deferred by review-close

# Assumptions ledger — PRD 00045-survey-single-read-and-log-time-trim-v1

## 1: Thread an optional text parameter through the symbol extractors and error-style scan

- (Tess) Tests pass `text` / `texts` as keyword arguments. The contract gives these names in the signatures.
- (Tess) An empty string `text=""` counts as given text, not missing, because the contract says to read from disk "only when it is None".
- (Tess) `texts={}` behaves like None: every file is read from disk, because the lookup is "f in texts".
- (Tess) Patched `try_import_tree_sitter` and `_extract_tree_sitter` to cover the three internal extraction paths deterministically, matching the existing test's pattern.
- (Tess) The `.go` merge test assumes the regex extractor gives `type X struct` kind "class" and `type X interface` kind "interface", per the existing regex extractor.
- (Tess) The new file's name, `test_survey_text.py`, follows the existing `test_survey_*.py` sibling convention.
- (Tess, strengthening) `_extract_tree_sitter(f, ts, text="")` must actually call `ts_module.process("")` rather than short-circuit on an empty string.
- (Tess, strengthening) The gap-1 fake accepts `text` as a keyword or as the third positional argument.
- (Tess, strengthening) The stub test files use a `.py` suffix so `_TS_LANG_BY_EXT` maps them to a language and `_extract_tree_sitter` does not return early.
- (Ivan) `_survey` is not wired to pass pre-read text in this task - the tests do not require it (that is the next task).
- (Ivan) `text` is passed to `_extract_tree_sitter` as a keyword argument.

## 2: Make _survey read each sampled file once and thread it through the extractors and error-style scan

- (Tess) `Path.read_text` is the only disk-read path to count (the contract and acceptance check name `read_text` only).
- (Tess) An unreadable file should still count toward its layer's file total.
- (Tess) Freshness-across-calls is tested through observable output, not internals of the mapping.
- (Tess) Created a new sibling file (`test_survey_single_read.py`) following the split-by-behavior convention.
- (Tess, strengthening) The fake tree-sitter module defines `ProcessConfig`, so the >50-file test's failure comes from `process()` raising, not a missing attribute.
- (Tess, strengthening) The invalid-UTF-8 test builds its own one-file repo instead of reusing `_build_repo`, to keep the check isolated.
- (Ivan) An unreadable file is skipped entirely by `_survey`'s extraction loop rather than passed through as `texts.get(f)` returning None; Pat's review confirmed the observable behavior is equivalent (both give `[]` symbols) and accepted the deviation.
- (Ivan) `_compute_error_style`'s existing disk-read fallback for a file missing from `texts` is left as a second read attempt for an unreadable file - Pat recorded this as a LOW, accepted as negligible impact per the design's own risk acceptance.

## 3: Add the fail-first regression test proving no sampled file is read from disk twice

- (Ivan) Did not check that `main.go` is among the sampled files, only that it is present in the fixture - the acceptance criteria only require the fixture to hold it.
- (Ivan) Ran only the named test file for verification, not the whole `skills/survey/scripts` directory, following the narrow-scope rule over the Verify line's full-directory wording.

## 4: Replace the brief trimmer's quadratic pop loop with a binary search bounded by _encoded_len

- (Tess) A negative `max_bytes` returns `""`, matching the old pop loop's behavior and the rule that k=0 is always valid regardless of the predicate.
- (Tess) Cleanup runs even when content already fits, following "same contract as today" for direct calls to `_trim_lines_to_budget`.
- (Tess, strengthening) The minimum of 1 `_encoded_len` call is part of the contract - the design says the binary search uses `_encoded_len` as its test.
- (Tess, strengthening) The 5 failing call-count test cases are acceptable fail-first tests for the next task, left unskipped and unmarked.

## 5: Pin the new binary-search trimmer byte-identical to the old pop loop

- (Ivan) `run._trim_lines_to_budget` takes `(content, max_bytes)` and returns a str, confirmed by the test runs rather than by reading run.py directly (it is outside the task's allowlist).
- (Ivan) At budget 0 every case trims to `""`; that still counts as a valid comparison point for the "cut mid-list" and "header" cases.

## 6: Bound the trimmer at a logarithmic number of _encoded_len calls

- (Ivan) The counting wrapper takes `*args, **kwargs`, since `_encoded_len`'s exact signature was outside this task's file allowlist.
- (Ivan) Used 600 lines of plain `"x" * 40` content (no `## ` prefixes, no blank lines), since the task did not specify line content.

## 10 (rework): restore the PRD-named trim tests in test_survey_brief.py

- (Tess) For the byte-for-byte equality test, the task named 4 budgets (0, 64, 512, 5120) each illustrating one scenario but didn't pin exact content strings, so one content string was constructed per budget to deterministically hit each named scenario (empty content at budget 0; already-under-budget content at budget 64; a 40-line/26-byte-per-line content cut mid-list at budget 512; a 300-line, 20-bytes-per-line content engineered so the pop-loop's pre-cleanup boundary lands exactly on a "## " header at budget 5120).
- (Tess) For the iteration-count test, used literal content "600 lines, each 40 characters" (`"a" * 40` repeated 600 times) per the task's exact phrasing, and asserted the counter is `<= 12` as stated.

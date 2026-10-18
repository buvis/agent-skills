---
default_model: opus
rework_cap: 5
---

# survey reads each sampled file once and trims the brief in log time

## Problem

Two redundancies in `skills/survey/scripts/run.py` (lines re-verified 2026-10-17). The symbol pass
reads every capped file at line 178 (`_extract_file_symbols_regex`, line 175; and line 138 on the
tree-sitter path, `_extract_tree_sitter`, line 133), then `_compute_error_style` (line 228)
re-reads the first 50 files across all layers at line 240, a flat +50 `read_text` calls per run,
+30.7% here. A third read hides in `_extract_file_symbols` (line 153): for `.go` files it calls
`_extract_file_symbols_regex` again at line 168 to merge Go types. Separately
`_trim_lines_to_budget` (line 338) re-joins and re-encodes the whole remaining list once per popped
line in the loop on lines 346-347, so holding `_BRIEF_BUDGET = 5120` (line 23) costs quadratic
work: at 600 layers the trimmer touches 28.9 MB to emit a 5.1 KB brief, and the tightest observed
margin under budget is 10 bytes. Source: agoge run
`docs/dev/project-management/audit-results/agoge-2026-08-31.md`, finding 41 (LOW, performance
lane) and finding 42 (LOW, performance lane); decision 2026-09-02: pass the held text through, and
binary-search the cut point.

```
corpus200 -> distinct_files_read=50, total_read_text_calls=100,
files_read_twice=50; real repo -> distinct_files_read=163,
total_read_text_calls=213, files_read_twice=50.
60 layers -> 55 iterations, 347,993 bytes joined; 120 -> 137 / 1,320,608;
300 -> 452 / 7,550,336; 600 -> 1,052 / 28,974,386. Doubling layers
multiplies bytes re-encoded by 3.79x (60->120) and 3.84x (300->600).
```

## Solution

`_survey` (line 367) reads each file once into a `texts: dict[Path, str]`, hands the text to
`_extract_file_symbols(f, text)` (call at line 378), which passes it to both extractors including
the `.go` merge call, and hands the mapping to `_compute_error_style(layers, texts)` (call at line
393). Every new parameter defaults to `None` and falls back to reading, so the eight existing
direct calls in `test_survey.py` (lines 127, 163, 192, 231, 265, 285, 337, 374 after PRD 00079's
split of the suite) keep working. For the
trimmer, extract `_encoded_len(lines)` and binary-search the largest prefix whose encoded join fits
`max_bytes`. Dropping a line strictly shrinks the encoded length, so the largest fitting prefix is
exactly what the pop loop produced: output stays byte-identical, and a test proves it.

## Requirements

### Must have
- No file is read from disk more than once during one `run._survey` call, `.go` files included.
- `_extract_file_symbols`, `_extract_tree_sitter` and `_extract_file_symbols_regex` take an
  optional `text`; when it is `None` they read as they do now.
- `_compute_error_style(layers, texts=None)` uses a supplied text when the mapping holds the path
  and reads when it does not.
- `_trim_lines_to_budget` returns exactly what the current pop loop returns for every input,
  including empty content and content already under budget, and keeps the trailing blank/`## `
  cleanup on lines 337-338.
- `_trim_lines_to_budget` calls `_encoded_len` at most `ceil(log2(n + 1)) + 2` times for `n` lines.

### Nice to have
- none

## Implementation

### Module: run.py
- **Location**: `skills/survey/scripts/`
- **Responsibility**: reads sampled files, computes the atlas, builds and trims the brief
- **Exports**: `_survey()`, `_extract_file_symbols()`, `_compute_error_style()`, `_trim_lines_to_budget()`, `_encoded_len()`
- New symbols: `_encoded_len`

### Module: test_survey.py
- **Location**: `skills/survey/scripts/`
- **Responsibility**: behavioral tests for the symbol pass and the brief generator (PRD 00079 split the rest into `test_survey_brief.py`, `test_survey_scan.py`, `survey_test_helpers.py` and `conftest.py`)
- **Exports**: `test_no_sampled_file_is_read_from_disk_twice()`
- New symbols: `test_no_sampled_file_is_read_from_disk_twice`

### Module: test_survey_brief.py
- **Location**: `skills/survey/scripts/`
- **Responsibility**: tests for brief assembly and trimming (`test_brief_within_5120_byte_limit` at line 71)
- **Exports**: `test_trim_matches_the_pop_loop_byte_for_byte()`, `test_trim_encodes_a_logarithmic_number_of_times()`
- New symbols: `test_trim_matches_the_pop_loop_byte_for_byte`, `test_trim_encodes_a_logarithmic_number_of_times`

### Dependencies
- run.py: No dependencies (foundation)
- test_survey.py: Depends on [run.py]
- test_survey_brief.py: Depends on [run.py]
- PRD 00030 (done) rewrote `_scan_layers` in the same file; PRD 00079 (done) split the test suite.
  Both have landed; this work sits on top of them.

## Tasks

### Phase 0: Foundation

- [ ] Add an optional `text: str | None = None` parameter to `_extract_file_symbols`, `_extract_tree_sitter` and `_extract_file_symbols_regex`, reading from disk only when it is `None`, and add `texts: dict[Path, str] | None = None` to `_compute_error_style` - Acceptance: `uv run pytest skills/survey/scripts -q` reports 0 failed and 0 errors with the eight existing single-argument call sites unchanged, and `uv run pytest "skills/survey/scripts/test_survey.py::test_regex_fallback_used_when_tree_sitter_extraction_returns_empty" -q` (line 252) passes with its `monkeypatch.setattr(run, "_extract_tree_sitter", lambda *a, **k: [])` (line 263) untouched.
- [ ] Make `_survey` read each file once into `texts`, pass `texts[f]` into `_extract_file_symbols`, which forwards it to `_extract_tree_sitter`, `_extract_file_symbols_regex` and the `.go` merge call (line 168), and pass `texts` into `_compute_error_style` - Acceptance: `uv run pytest skills/survey/scripts -q` reports 0 failed, and every `read_text` that `rg -n "read_text" skills/survey/scripts/run.py` lists sits on a `text is None` or `texts`-miss fallback branch.
- [ ] Add `test_no_sampled_file_is_read_from_disk_twice` to `skills/survey/scripts/test_survey.py`, monkeypatching `pathlib.Path.read_text` with a wrapper that appends `self` to a list and delegates to the original - Acceptance: the test builds a repo with at least 60 `.py` files and one `.go` file across two layers, calls `run._survey(repo)`, and asserts `len(calls) == len(set(calls))`; `uv run pytest "skills/survey/scripts/test_survey.py::test_no_sampled_file_is_read_from_disk_twice" -q` passes.

### Phase 1: Core

- [ ] Add `_encoded_len(lines)` returning `len("\n".join(lines).encode())` and replace the pop loop in `_trim_lines_to_budget` with a binary search for the largest prefix length whose `_encoded_len` is `<= max_bytes`, keeping the trailing cleanup - Acceptance: `rg -n "while lines and len" skills/survey/scripts/run.py` prints no match; `rg -n "def _encoded_len" skills/survey/scripts/run.py` matches; `uv run pytest "skills/survey/scripts/test_survey_brief.py::test_brief_within_5120_byte_limit" -q` passes.
- [ ] Add `test_trim_matches_the_pop_loop_byte_for_byte` to `skills/survey/scripts/test_survey_brief.py`, defining the old pop loop inline as `_reference_trim(content, max_bytes)` and comparing it with `run._trim_lines_to_budget` - Acceptance: the test asserts equality for empty content, content already under budget, content cut mid-list, and content whose last surviving line is a `## ` header, at budgets 0, 64, 512 and 5120; `uv run pytest "skills/survey/scripts/test_survey_brief.py::test_trim_matches_the_pop_loop_byte_for_byte" -q` passes.
- [ ] Add `test_trim_encodes_a_logarithmic_number_of_times` to `skills/survey/scripts/test_survey_brief.py`, monkeypatching `_encoded_len` on the `run` module with a counting wrapper that delegates - Acceptance: the test trims 600 lines of 40 characters each to 5120 bytes and asserts the counter is `<= 12`, a bound the old pop loop fails at 1,052 iterations; `uv run pytest "skills/survey/scripts/test_survey_brief.py::test_trim_encodes_a_logarithmic_number_of_times" -q` passes.

## Success Criteria

- `uv run pytest skills/survey/scripts -q` reports 0 failed and 0 errors, including the three new
  tests.
- `test_no_sampled_file_is_read_from_disk_twice` fails against the pre-fix `run.py` and passes
  after, so the single-read rule is bound to a test and not to a wall-clock number.
- `test_trim_matches_the_pop_loop_byte_for_byte` passes, so no brief changes its cut point.
- `test_trim_encodes_a_logarithmic_number_of_times` bounds the trimmer at 12 encodes for 600 lines,
  against the measured 1,052.

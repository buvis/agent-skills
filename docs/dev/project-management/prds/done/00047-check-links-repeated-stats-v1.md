---
default_model: sonnet
rework_cap: 5
catchup: skip
design: skip
---

# check_links caches path resolution instead of statting per reference

## Problem

`resolve_path` in `skills/review-prd-backlog/scripts/check_links.py` (lines 66-71) calls `p.exists()`
for every matched token with no memoisation, and `scan_file` calls it once per `PATH_RE` match on
every line of every scanned file: 1,216 stat calls for 150 distinct paths on the real backlog, 87.7%
of them redundant. Source: agoge run dev/local/audit-results/agoge-2026-08-31.md, finding 43 (LOW,
performance lane); decision 2026-09-02: `@functools.cache` on `resolve_path`.

```
500 references to one distinct target -> Path.exists_calls=500,
distinct_paths_statted=1; 1000 -> 1000 calls, 1 distinct. Real repo:
1216 calls, 150 distinct - 1066 redundant (87.7%).
```

## Solution

Import `functools` and decorate `resolve_path` with `@functools.cache`. Its arguments are
`(token: str, root: Path)`, both hashable, and the body is pure apart from the stat, so one
process-lifetime cache removes every repeat. The cache outlives a call, so the tests clear it
between cases with `check_links.resolve_path.cache_clear()`.

## Requirements

### Must have
- `resolve_path` stats each distinct `(token, root)` pair at most once per process.
- Return values and `check_links.run(root)` findings are unchanged.
- `test_check_links.py` clears the cache before each test, so no tmp-dir fixture reads another
  test's answer.

### Nice to have
- none

## Implementation

### Module: check_links.py
- **Location**: `skills/review-prd-backlog/scripts/`
- **Responsibility**: resolves working-document references and reports rot
- **Exports**: `resolve_path()`, `run()`

### Module: test_check_links.py
- **Location**: `skills/review-prd-backlog/scripts/`
- **Responsibility**: tests for the reference checker
- **Exports**: `test_a_repeated_reference_is_statted_once()`

### Dependencies
- check_links.py: No dependencies (foundation)
- test_check_links.py: Depends on [check_links.py]

## Tasks

### Phase 0: Foundation

- [ ] Add `import functools` and `@functools.cache` directly above `def resolve_path` in `skills/review-prd-backlog/scripts/check_links.py`, and add an autouse fixture to `test_check_links.py` calling `check_links.resolve_path.cache_clear()` - Acceptance: `rg -n -B1 "def resolve_path" skills/review-prd-backlog/scripts/check_links.py` shows `@functools.cache` on the preceding line; `uv run pytest skills/review-prd-backlog/scripts/test_check_links.py -q` reports 0 failed and 0 errors.
- [ ] Add `test_a_repeated_reference_is_statted_once` to `skills/review-prd-backlog/scripts/test_check_links.py`, monkeypatching `pathlib.Path.exists` with a wrapper that appends `self` to a list and delegates to the original - Acceptance: the test writes one markdown file under `tmp_path / "dev/local/notes"` holding 50 lines that each reference the same existing `dev/local/...` path, calls `check_links.run(tmp_path)`, and asserts that path appears exactly once in the recorded calls; `uv run pytest "skills/review-prd-backlog/scripts/test_check_links.py::test_a_repeated_reference_is_statted_once" -q` passes.

### Phase 1: Core

No additional work; the Phase 0 tasks deliver this capability and its regression coverage.

## Success Criteria

- `uv run pytest skills/review-prd-backlog/scripts/test_check_links.py -q` reports 0 failed and 0
  errors.
- `test_a_repeated_reference_is_statted_once` fails against the pre-fix `check_links.py` with 50
  recorded stats and passes after with 1.
- The eight existing tests in `test_check_links.py` pass unchanged, so findings, waivers and exit
  codes are untouched.

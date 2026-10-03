---
default_model: sonnet
rework_cap: 5
catchup: skip
design: skip
---

# sweep validates `--out` before it scans anything

## Problem

`main()` in `skills/sweep-fix/scripts/sweep.py` calls `scan()` on line 578 and
`_resolve_report_path()` (defined lines 541-557) on line 594, so an `--out` that will be refused is
refused only after every repo has been searched: 27 subprocesses run and their results are thrown
away for a typo. The refusal itself is correct, only its position is wrong, and finding 26 puts the
worst case at 810s before the message appears. The strict-xfail test that encodes the rule is on
master (merged in 636d94f). Source: agoge run dev/local/audit-results/agoge-2026-08-31.md, finding
27 (MEDIUM, performance lane); decision 2026-09-02: move the `--out` validation above the scan.

```
With --out outside --cwd: search_subprocesses=27, wall_total_s=0.80, then
sweep: --out '...' resolves to ..., which is outside the --cwd repo ...,
exit=1. 27 searches executed and were thrown away. The refusal itself is
correct behaviour; only its position is wrong. Bounded by finding 26's worst
case, a mistyped --out can burn up to 810s before the message appears.
```

## Solution

`_resolve_report_path(cwd_path, args.out, args.reason)` needs only parse-time values, so move it
and `cwd_path = Path(args.cwd).resolve()` above the `try:` block that calls `enumerate_repos` and
`scan`. `_resolve_report_path` creates no directory of its own - the only `mkdir` is
`out_path.parent.mkdir` on line 596 - so that call stays after `render_report` and a refused run
still creates nothing. Then delete the strict-xfail marker from the test that already states the
rule.

## Requirements

### Must have
- `_resolve_report_path` runs before `enumerate_repos`, so a refused `--out` spawns zero search
  subprocesses.
- The refusal message text, the `SystemExit(1)` and the success path are unchanged.
- `out_path.parent.mkdir(parents=True, exist_ok=True)` stays after `render_report`; a refused run
  creates no directory.
- The strict-xfail marker on
  `test_an_out_path_outside_the_cwd_repo_is_refused_before_any_repo_is_scanned` is gone and the
  test passes plain.

### Nice to have
- none

## Implementation

### Module: sweep.py
- **Location**: `skills/sweep-fix/scripts/`
- **Responsibility**: CLI entry point wiring enumerate, scan, render and write
- **Exports**: `main()`, `_resolve_report_path()`

### Module: test_sweep_main.py
- **Location**: `skills/sweep-fix/scripts/`
- **Responsibility**: CLI end-to-end tests
- **Exports**: `test_an_out_path_outside_the_cwd_repo_is_refused_before_any_repo_is_scanned()`, `test_a_refused_out_path_creates_no_report_directory()`

### Dependencies
- sweep.py: No dependencies (foundation)
- test_sweep_main.py: Depends on [sweep.py]

## Tasks

### Phase 0: Foundation

- [ ] Move `cwd_path = Path(args.cwd).resolve()` and the `_resolve_report_path(cwd_path, args.out, args.reason)` call in `main()` above the `try:` block holding `enumerate_repos` and `scan`, leaving `out_path.parent.mkdir(parents=True, exist_ok=True)` and `write_text` where they are - Acceptance: in `rg -n "_resolve_report_path|enumerate_repos|mkdir" skills/sweep-fix/scripts/sweep.py` the `_resolve_report_path(cwd_path` call line number is lower than both the `enumerate_repos(` call line and the `mkdir(parents=True` line.
- [ ] Premise: `skills/sweep-fix/scripts/test_sweep_main.py` carries `@pytest.mark.xfail(strict=True, ...)` on `test_an_out_path_outside_the_cwd_repo_is_refused_before_any_repo_is_scanned`; delete that decorator, and if it is already gone skip the deletion and report it - Acceptance: `uv run pytest "skills/sweep-fix/scripts/test_sweep_main.py::test_an_out_path_outside_the_cwd_repo_is_refused_before_any_repo_is_scanned" -q` reports the named test passing without an xfail marker. Preserve unrelated expected failures.
- [ ] Add `test_a_refused_out_path_creates_no_report_directory` to `skills/sweep-fix/scripts/test_sweep_main.py`, pointing `--out` at `tmp_path / "outside" / "report.md"` - Acceptance: the test wraps `sweep.main(argv)` in `pytest.raises(SystemExit)` and then asserts `(tmp_path / "outside").exists() is False`; `uv run pytest "skills/sweep-fix/scripts/test_sweep_main.py::test_a_refused_out_path_creates_no_report_directory" -q` passes.

### Phase 1: Core

No additional work; the Phase 0 tasks deliver this capability and its regression coverage.

## Success Criteria

- `uv run pytest skills/sweep-fix/scripts -q` exits 0 with zero failures/errors.
- The named early-rejection regression passes without an xfail marker;
  unrelated expected failures remain outside this PRD's scope.
- `test_main_refuses_relative_out_that_escapes_cwd_repo_via_dotdot`,
  `test_main_refuses_absolute_out_outside_cwd_repo` and
  `test_main_accepts_out_nested_several_directories_inside_cwd_repo` pass unchanged, so the fence
  and its message are untouched.

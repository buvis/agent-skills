---
default_model: opus
model_tier_rationale: equivalence obligation on the YAML rendering swap, plus a resolver hoist that changes where errors surface
design: run
catchup: force
---

# sweep-fix exits 0 with a report when its tools, registry or working directory are wrong

## Problem

Six defects in `skills/sweep-fix/scripts/sweep.py`, all rework-cap leftovers
of PRD 00002, verified against HEAD on 2026-09-05:

1. `verify_control` (lines 329-337) wraps its control-term search in
   `except Exception`, warns and returns `None`, and discards the `_failed`
   map of its own control scan (line 325): an unresolvable `rg` or `ast-grep`
   makes `main()` exit 0 with a report instead of the loud unverified abort
   the skill promises.
2. `enumerate_repos` (lines 149-150) adds `cwd` only when it is not already in
   `repos` by exact path equality, with no walk-up to the git root. The
   registered roots stay in the list (line 145), so a run from a subdirectory
   scans the registered repo and then scans the subdirectory again as a
   second, non-normalized root, and can report the repo root as a registry
   gap when it is not registered.
3. `main`'s `except RuntimeError` (line 581) is dead: `scan` catches every
   exception per repo (lines 264 and 291), `verify_control` catches its own,
   and `enumerate_repos` never raises one.
4. `enumerate_repos` opens the registry unguarded inside a list
   comprehension (line 142), so a missing `--registry` is a raw
   `FileNotFoundError` traceback.
5. `_needs_yaml_quoting` (line 402, 43 lines) and `_yaml_scalar` (line 445)
   reimplement YAML scalar quoting that `json.dumps` already provides (a JSON
   string is a valid YAML double-quoted scalar).
6. `_resolve_report_path` (line 546) builds `sweep-<slug>-<date>.md` with no
   collision check, so a second sweep with the same reason on the same day
   silently overwrites the first report.

Source: batch 202608290848 deferred items on PRD 00002 (cap-overflow; two
HIGH at 1/4, three MEDIUM, one LOW); decided 2026-09-05: one PRD. The
control-repo rescan finding (MEDIUM, 3/4) was rejected as negligible: it runs
only on the all-zero path and costs one `rg` over one repo.

```
Reproduced live by Alice: an unresolvable rg makes main() exit 0 with a
report. Reproduced live by Blake from skills/sweep-fix/scripts/: the repo
root appears as a false registry gap while only the subdirectory is scanned.
```

## Solution

- After parsing arguments and validating --out per PRD 00032, resolve the
  scan tool once inside main's diagnostic handler, before enumeration/scanning (`resolve_rg()`
  for `rg`, `resolve_ast_grep()` for `astgrep`) so a missing tool raises
  `RuntimeError` into the existing handler and exits 1 with the message; the
  per-repo isolation in `scan` stays for repo-level failures only.
- `verify_control` re-raises a failed control search as `RuntimeError`, and
  treats a non-empty `_failed` from its control scan the same way: a control
  repo that cannot be scanned is an abort, not a pass.
- `enumerate_repos` walks `cwd` up to the nearest ancestor containing `.git`
  before comparing, and raises `RuntimeError(f"registry not found: {path}")`
  when the registry is absent.
- Replace `_needs_yaml_quoting` and `_yaml_scalar` with
  `json.dumps(value, ensure_ascii=True)`; the existing YAML round-trip tests
  in `test_sweep_render_report.py` are the equivalence check. ASCII escaping
  also preserves YAML-forbidden DEL/C1 characters; add U+007F and U+0085.
  Update the existing unquoted-pattern text assertion to parsed equality,
  preserving its neighboring real ast-grep execution regression.
- `_resolve_report_path` suffixes `-2`, `-3`, ... when the default path
  exists; an explicit `--out` is still honoured as given.

## Requirements

### Must have

- Invalid --out is refused before tool resolution, preserving PRD 00032.
- A missing or unresolvable scan tool exits 1 with a one-line message naming
  the tool, and no report is written.
- A control-term search that fails, or a control repo that cannot be
  scanned, exits 1.
- Running from a subdirectory of a registered repo scans the whole repo and
  reports no gap for it.
- A missing registry exits 1 with `registry not found: <path>`.
- Rendered YAML parses to the same values as before for every value the
  existing round-trip tests cover, plus strings containing `"`, `\`, `:`,
  `#`, a leading `-`, non-ASCII, U+007F and U+0085.
- Two same-reason sweeps on one day produce two report files.

### Nice to have

- none

## Implementation

### Module: sweep.py

- **Location**: `skills/sweep-fix/scripts/`
- **Responsibility**: Fail loud on setup errors, scan the real repo, quote with stdlib, never clobber a report.
- **Exports**: `enumerate_repos()`, `verify_control()`, `_resolve_report_path()`, `main()`; `_needs_yaml_quoting` and `_yaml_scalar` removed

### Module: tests

- **Location**: `skills/sweep-fix/scripts/` (`test_sweep_main.py`, `test_sweep_scan.py`, `test_sweep_render_report.py`, `test_sweep_resolvers.py`)
- **Responsibility**: Pin each exit path and the YAML equivalence.
- **Exports**: pytest cases

### Dependencies

- sweep.py: No dependencies (foundation)
- tests: Depends on [sweep.py]

## Tasks

### Phase 0: Foundation

- [ ] Hoist tool resolution into `main`, make `verify_control` raise on a failed control search or an unscannable control repo, and guard the registry open - Acceptance: new tests `test_an_unresolvable_scan_tool_exits_one_and_writes_no_report`, `test_a_failed_control_search_exits_one` and `test_a_missing_registry_exits_one_naming_the_path` (patch `sweep.resolve_rg` and `sweep._run_rg`, and pass a nonexistent registry) pass; an invalid-output-plus-missing-tool case proves output refusal wins; setup failures reach the diagnostic handler while per-repo scan isolation remains; `uv run pytest skills/sweep-fix/scripts -q` reports 0 failing.
- [ ] Walk `cwd` up to its git root in `enumerate_repos` - Acceptance: a new test `test_a_subdirectory_cwd_resolves_to_its_repo_root_and_is_not_a_gap` builds a `tmp_path` repo with `.git` and a nested directory, calls `enumerate_repos(registry, nested)`, and asserts repos equals the expected registered root set, nested cwd is absent, the root is not a gap, and scanning sees a fixture file at the root outside the nested directory; `uv run pytest skills/sweep-fix/scripts -q` reports 0 failing.

### Phase 1: Core

- [ ] Replace the two YAML helpers with `json.dumps` (depends on: Phase 0) - Acceptance: `rg -n "_needs_yaml_quoting|_yaml_scalar" skills/sweep-fix/scripts/sweep.py` prints nothing; the existing YAML round-trip behavior is preserved, the representation-specific pattern assertion is migrated to parsed equality, and the real ast-grep execution case still passes; a new parametrised test `test_rendered_rule_block_round_trips_every_awkward_scalar` covers every shape listed under Must have, including DEL and U+0085, parsing with the same YAML reader the existing round-trip tests use; `uv run pytest skills/sweep-fix/scripts -q` reports 0 failing.
- [ ] Suffix colliding default report paths in `_resolve_report_path` (depends on: Phase 0) - Acceptance: a new test `test_a_second_sweep_with_the_same_reason_on_the_same_day_gets_a_suffixed_report` pre-creates the default path and asserts the resolved path ends in `-2.md`; `uv run pytest skills/sweep-fix/scripts -q` reports 0 failing.

## Success Criteria

- Every new test passes and every existing sweep-fix test passes, including
  `test_resolve_rg_exits_naming_both_candidates_when_neither_resolves`, whose
  `RuntimeError` now reaches `main`'s handler.
- The batch's two live reproductions give an exit-1 message and a full repo
  scan respectively.

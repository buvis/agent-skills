---
design: skip
default_model: sonnet
model_tier_rationale: transcription - exact expressions and messages given; the one rewritten test is pinned by an rg premise and a new CLI regression test fails on the old code
---

# ground_prd: a bad --root exits 2, and a PRD never confirms its own symbols

Source: hold stubs 00084 and 00085, minted from PRD 00075's cycle-2 cap overflow in
`docs/dev/project-management/autopilot/deferred/202610100952-deferred.json`: the two `severity: high`
entries there, refs R1 ("R1 only half fixed. `main()` now catches `RuntimeError` and exits 2, but a
nonexistent `--root` still raises an uncaught `FileNotFoundError` ...") and R2 ("Relative PRD exclusions
now resolve against `root` instead of the process cwd ..."). This PRD replaces both stubs.

## Problem

`skills/create-prd/scripts/ground_prd.py` is the grounding gate `create-prd` step 5.55 runs, and it
blocks a PRD save on exit 1. Two defects make it lie:

1. **A bad `--root` reads as "blocking".** `main()` catches only `RuntimeError` around `run()`
   (`skills/create-prd/scripts/ground_prd.py:377-381`). A `--root` that does not exist makes
   `subprocess.run(rg, cwd=root)` raise `FileNotFoundError`, in `_rg_hit` (`skills/create-prd/scripts/ground_prd.py:137-143`);
   an unreadable `Cargo.lock` makes `lock.read_text` raise `PermissionError`, in `known_packages` (`skills/create-prd/scripts/ground_prd.py:181-187`).
   Either way Python prints a
   traceback and exits 1, which the gate reads as "the PRD has blocking rows" instead of exit 2, "the
   check could not run".
2. **A PRD can confirm its own invented symbols.** `resolve_symbols` excludes the PRD files being graded
   so a claim cannot match its own text, but it resolves a relative path against `root`
   (`skills/create-prd/scripts/ground_prd.py:156-157`). The paths come from the CLI, relative to the
   process cwd. With cwd `/work`, `--root repo` and input `repo/prd.md`, the exclusion targets
   `/work/repo/repo/prd.md`, the real PRD stays searchable, and a symbol that exists only in the PRD
   resolves `ok`. The existing test `test_resolve_symbols_excludes_own_prd_path_given_as_relative_path`
   (`skills/create-prd/scripts/test_ground_prd.py:779-792`) passes only because of this bug: it passes
   `Path("prd.md")` while cwd is `tmp_path.parent`, a path that is relative to `root`, not to cwd.

## Solution

- `main()` checks `root.is_dir()` before running and exits 2 with a one-line message, and catches
  `OSError` beside `RuntimeError` so any other I/O failure during the run (an unreadable `Cargo.lock`,
  a vanished `node_modules`) also exits 2 with a message, never a traceback.
- `resolve_symbols` resolves each excluded path against the process cwd (`Path.resolve()` does that for
  a relative path) and drops the join onto `root`.
- The existing exclusion test is rewritten to pass a genuinely cwd-relative path, and a CLI-level test
  pins the `/work` + `--root repo` + `repo/prd.md` case.

## Requirements

### Must have

- `ground_prd.py --root <path that is not a directory> <prd>` exits 2 and prints
  `ground_prd: --root <path>: not a directory` to stderr, with no traceback.
- An `OSError` raised during `run()` exits 2 and prints `ground_prd: <error>` to stderr.
- With cwd different from `--root`, a PRD path given relative to cwd is excluded from symbol search: a
  symbol that occurs only in that PRD is `unresolved`, and the CLI exits 1.
- Each fix ships with a test that fails against the current code.

### Nice to have

- None.

## Implementation

```text
skills/create-prd/scripts/
├── ground_prd.py       # main() root check and OSError catch; resolve_symbols exclusion
└── test_ground_prd.py  # new CLI tests; rewritten exclusion test
```

### Module: grounding checker
- **Location**: `skills/create-prd/scripts/ground_prd.py`
- **Responsibility**: grade a PRD's citations, symbols and library claims against the repo; exit 0 clean, 1 blocking, 2 could not run.
- **Exports**: `main`, `run`, `resolve_symbols`, `known_packages`

### Module: grounding checker tests
- **Location**: `skills/create-prd/scripts/test_ground_prd.py`
- **Responsibility**: unit and CLI tests for the checker.
- **Exports**: none
- New symbols: `test_cli_exits_two_naming_a_root_that_is_not_a_directory`, `test_cli_exits_two_when_cargo_lock_is_unreadable`, `test_cli_excludes_own_prd_given_relative_to_cwd_not_root`

### Dependencies
- grounding checker: No dependencies (foundation)
- grounding checker tests: Depends on [grounding checker]

## Tasks

### Phase 0: Foundation
- [ ] Exit 2 on a bad root or an I/O failure. In `skills/create-prd/scripts/test_ground_prd.py` add, next to
  the other `test_cli_exits_two_*` tests:
  - `test_cli_exits_two_naming_a_root_that_is_not_a_directory`: write a grounded PRD (one with a
    `` `alpha` `` claim, as `make_repo` provides) in `tmp_path`, call
    `ground_prd.main([str(prd), "--root", str(tmp_path / "absent")])` under
    `pytest.raises(SystemExit)`, assert the code is 2 and stderr contains
    `--root` and `not a directory` and no `Traceback`.
  - `test_cli_exits_two_when_cargo_lock_is_unreadable`: `make_repo(tmp_path)`, write
    `tmp_path / "Cargo.lock"` and arm it with the root `conftest.py` fixture
    `deny_access` (`deny_access(tmp_path / "Cargo.lock")`; `conftest.py:144-169` revokes the mode
    bits on POSIX, wraps the call boundary on Windows, and restores on teardown), run `main` on a
    PRD in `tmp_path` with `--root str(tmp_path)`, assert exit 2 and a `ground_prd:` line on
    stderr. No bare `chmod` and no `os.geteuid` in the test: `os.geteuid` does not exist on
    Windows, where the `windows` job already fails two sweep-fix tests on exactly that.
  Watch both fail against the current code. Then in `skills/create-prd/scripts/ground_prd.py` `main()`,
  directly after `root = Path(args.root)`, insert:
  ```python
      if not root.is_dir():
          print(f"ground_prd: --root {root}: not a directory", file=sys.stderr)
          sys.exit(2)
  ```
  and change `except RuntimeError as e:` to `except (RuntimeError, OSError) as e:`.
  Acceptance: `uv run pytest skills/create-prd/scripts/test_ground_prd.py -k "exits_two"` passes, and
  `rg -n "except \(RuntimeError, OSError\) as e:" skills/create-prd/scripts/ground_prd.py` matches one line.

### Phase 1: Core
- [ ] Resolve excluded PRD paths against cwd (depends on: Phase 0). Premise, re-checked at execution (a
  failed premise means skip and report, never force): `rg -c 'p = Path\(root\) / p'
  skills/create-prd/scripts/ground_prd.py` prints 1, and
  `rg -c 'exclude=frozenset\(\{Path\("prd.md"\)\}\)' skills/create-prd/scripts/test_ground_prd.py`
  prints 1. In `skills/create-prd/scripts/test_ground_prd.py`:
  - add `test_cli_excludes_own_prd_given_relative_to_cwd_not_root`: create `work = tmp_path / "work"`
    and `repo = work / "repo"`, `make_repo(repo)`, write `repo / "prd.md"` containing
    `` calls `onlyInPrdSymbol` here ``, `monkeypatch.chdir(work)`, run
    `ground_prd.main(["repo/prd.md", "--root", "repo"])` under `pytest.raises(SystemExit)` and assert
    exit 1 and an `unresolved` row for `onlyInPrdSymbol` in stdout;
  - in `test_resolve_symbols_excludes_own_prd_path_given_as_relative_path`, replace
    `exclude=frozenset({Path("prd.md")})` with `exclude=frozenset({Path(tmp_path.name) / "prd.md"})`.
  Watch the new test fail against the current code. Then in `resolve_symbols` replace
  ```python
          p = Path(p)
          if not p.is_absolute():
              p = Path(root) / p
          try:
              rel = p.resolve().relative_to(Path(root).resolve())
  ```
  with
  ```python
          try:
              # a relative path came from the CLI, so it is relative to cwd, not to root
              rel = Path(p).resolve().relative_to(Path(root).resolve())
  ```
  Acceptance: `rg -n 'p = Path\(root\) / p' skills/create-prd/scripts/ground_prd.py` prints nothing,
  and `uv run pytest skills/create-prd/scripts/test_ground_prd.py` passes.

## Success Criteria

- `test_cli_exits_two_naming_a_root_that_is_not_a_directory`,
  `test_cli_exits_two_when_cargo_lock_is_unreadable`,
  `test_cli_excludes_own_prd_given_relative_to_cwd_not_root` and
  `test_resolve_symbols_excludes_own_prd_path_given_as_relative_path` pass, and the first three fail
  against the pre-change `ground_prd.py`.
- The hold stubs `00084-triage-r1-only-half-fixed-main-now-catches-runt-v1.md` and `00085-triage-relative-prd-exclusions-now-resolve-agai-v1.md` (link-ok: deleted on purpose)
  are gone from `docs/dev/project-management/prds/hold/` (removed when this PRD was saved).
- The full `uv run pytest` gate passes at the end of the last phase.

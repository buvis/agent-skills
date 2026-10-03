---
default_model: sonnet
rework_cap: 5
catchup: skip
design: skip
---

# Require a `dev` parent before `purge-devlocal` accepts a directory named `local`

## Problem

The store guard in `resolve_store` at
`skills/purge-devlocal/scripts/purge_devlocal.py:143` reads `if store.name !=
"local" and not (store / "prds").is_dir()`, so the name alone satisfies it. Any
ordinary directory called `local` pointed at with `--repo` gets swept,
`/usr/local` being the obvious real-world match: the probe moved aged source
files into `.trash/`. The function's own docstring (lines 133-138) says the
guard exists precisely to stop this, trash-first makes the damage survivable
rather than safe, and the wire-in runs `--apply` unattended. Source: agoge run
`dev/local/audit-results/agoge-2026-08-31.md`, finding 30 (MEDIUM, security
lane); decision 2026-09-02: require the parent directory to be named `dev`.

```
Control - a plain project is refused: /.../plainproj: not a dev/local store
(no dev/local, no prds/), exit 1. Probe - an ordinary directory named local,
no dev/local, no prds/, holding aged source files: trash=2 (stale-foreign:1
stale-stray:1) naming nested/data.bin and source.py, both moved under
.trash/2026-08-31/.
```

## Solution

Narrow the name escape hatch to `<anything>/dev/local`: accept on the name only
when `store.name == "local"` and `store.parent.name == "dev"`, and require a
`prds/` directory otherwise. The refusal message and the `SystemExit` stay as
they are, so nothing downstream changes shape, and the earlier `cand` branch
(lines 139-141) that resolves a repo root holding `dev/local` is untouched.

## Requirements

### Must have

- A directory named `local` whose parent is named `dev` is accepted even with
  no `prds/`, keeping `test_accepts_a_store_named_local_without_prds` green.
- A directory named `local` whose parent is not `dev` and which has no `prds/`
  raises `SystemExit`, leaving its files in place.
- A directory holding `prds/` is still accepted whatever its name; the refusal
  text and exit code are unchanged.
- The strict-xfail marker above the authored test, which sits on master
  (merged in 636d94f), goes away in the same change.

### Nice to have

- none

## Implementation

### Module: purge_devlocal
- **Location**: `skills/purge-devlocal/scripts/`
- **Responsibility**: trash-first GC for `dev/local` stores; `resolve_store`
  decides what counts as a store at all
- **Exports**: `resolve_store()`, `main()`

### Module: test_purge_devlocal
- **Location**: `skills/purge-devlocal/scripts/`
- **Responsibility**: one test per retention rule, plus the store-guard boundary
- **Exports**: `test_refuses_a_directory_named_local_that_is_not_under_dev`, `test_accepts_a_store_named_local_without_prds`, `test_refuses_a_project_that_is_not_a_store`

### Dependencies
- purge_devlocal: No dependencies (foundation)
- test_purge_devlocal: Depends on [purge_devlocal]

## Tasks

### Phase 0: Foundation
- [ ] Tighten the guard at `purge_devlocal.py:143` so the `local` name is accepted only when `store.parent.name == "dev"`, keeping the existing refusal message and `SystemExit`, and delete the strict-xfail marker above `test_refuses_a_directory_named_local_that_is_not_under_dev` - Acceptance: `uv run pytest "skills/purge-devlocal/scripts/test_purge_devlocal.py::test_refuses_a_directory_named_local_that_is_not_under_dev" -q` reports `1 passed`, and `rg -n "xfail" skills/purge-devlocal/scripts/test_purge_devlocal.py` prints no output.
- [ ] Confirm the guard still admits the two shapes it must and that nothing else in the store GC moved - Acceptance: `uv run pytest "skills/purge-devlocal/scripts/test_purge_devlocal.py::test_accepts_a_store_named_local_without_prds" "skills/purge-devlocal/scripts/test_purge_devlocal.py::test_refuses_a_project_that_is_not_a_store" -q` reports `2 passed`, and `uv run pytest -q` from the repo root ends with a summary line containing neither `failed` nor `error`.

### Phase 1: Core

No additional work; Phase 0 delivers the guard correction and its regression coverage.

## Success Criteria

- `<anything>/dev/local` is accepted on the name alone, with no `prds/`.
- A directory named `local` outside a `dev` parent and without `prds/` exits
  non-zero and leaves its files where they are.
- `rg -n "xfail" skills/purge-devlocal/scripts/test_purge_devlocal.py` prints
  nothing, and `uv run pytest -q` reports no failures and no errors.
- The fix narrows the path-shape heuristic instead of closing it: a directory
  laid out as `dev/local` elsewhere is still accepted, the marker-file
  alternative having been declined for its migration cost.

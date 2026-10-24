---
design: skip
default_model: sonnet
model_tier_rationale: one generator change with its exact rule given, three additive tests with their assertions given, one sentence of prose
---

# purge-devtmp moves a nested repo as one unit

Source: 2026-10-18, this repo. The autopilot loop's drain-time purge and an operator run the same evening both died with `PermissionError: [Errno 1] Operation not permitted: '.../docs/dev/tmp/.trash/2026-10-18/devon-1/gitcheck/.git/hooks'` (the loop's traceback is in `docs/dev/project-management/autopilot/wrapper.log`). The Seatbelt profile every agent session runs under refuses to create a `.git/hooks` path, and the temp tree holds git fixtures with full `.git` directories (Devon's gitcheck directory, the clone and template pairs of the use-qwen seal). The run moved every file before the first fixture and stopped; the rest of the store, and every later store, stayed. Moving each fixture's top directory by hand passed, since only the top-level rename is checked.

## Problem

`walk_store` (`skills/purge-devtmp/scripts/purge_devtmp.py:76`) yields every file under the store, and `trash_file` (`skills/purge-devtmp/scripts/purge_devtmp.py:120`) recreates the file's parent chain under the trash batch with `mkdir(parents=True)` before `shutil.move`. For a file inside a nested repository that chain includes `.git/hooks`, which the sandbox denies; the exception is uncaught, so `process_store` (`skills/purge-devtmp/scripts/purge_devtmp.py:162`) ends with the store half moved and the manifest half written.

## Solution

`walk_store` treats a directory that holds an entry named `.git` as one unit: it yields that directory's relative path with the newest `st_mtime` of the regular files beneath it (the directory's own mtime when it holds no file), and prunes the walk below it (`dirs[:] = []`), so no path inside the fixture is ever yielded. `classify`, `trash_file` and the manifest need no change: `shutil.move` moves a directory, `_dedup_dest` already resolves a name collision, and the manifest row records the directory's relative path. The newest-file mtime keeps a fixture a session is still writing in the fresh class, and a PRD number anywhere in the directory's path keeps it live-linked, as for a file. `skills/purge-devtmp/SKILL.md` gains one sentence after "Nothing is directly unlinked.": `A directory that holds a .git entry (a cloned or templated fixture) moves as one unit, so the trash never has to recreate paths a sandbox refuses.`

## Requirements

### Must have
- `walk_store` yields a `.git`-holding directory as one unit with the newest-file mtime and never descends into it.
- Tests in `skills/purge-devtmp/scripts/test_purge_devtmp.py`:
  - `test_nested_repo_fixture_moves_as_one_unit`: a store with `fixture/.git/hooks/pre-commit` and `fixture/src.py`, both aged 8 days, under a `monkeypatch` that replaces `pathlib.Path.mkdir` with a wrapper raising `PermissionError` for any path whose parts contain `.git` followed by `hooks` (the sandbox's shape) and otherwise calling the original; `process_store` with `apply=True` moves `fixture` whole, the trash batch holds `fixture/.git/hooks/pre-commit` and `fixture/src.py`, and the manifest holds exactly one row for `fixture` and none for its members.
  - `test_fresh_file_inside_a_nested_repo_keeps_the_fixture`: `fixture/.git/HEAD` aged 8 days and `fixture/src.py` written now; a dry run counts the unit as `fresh` and moves nothing.
  - `test_live_prd_number_in_the_fixture_path_keeps_it`: a wip PRD `00123-feature.md` beside the store and a fixture at `00123-eval/template/.git/HEAD` aged 60 days; the unit classifies `live-linked`.
- The SKILL.md sentence above.
- A CHANGELOG `[Unreleased]` Fixed entry under **purge-devtmp**: a temp directory holding a nested `.git` moves to the trash as one unit, so the purge no longer dies under a sandbox that refuses to create `.git/hooks`, and the loop's drain-time purge completes.

### Nice to have
- None.

## Implementation

### Module: purge-walk
- **Location**: `skills/purge-devtmp/scripts/purge_devtmp.py`
- **Responsibility**: enumerate what the purge may move, fixtures as whole units
- **Exports**: `walk_store()` (unchanged signature), `process_store()` (unchanged)

### Module: purge-tests
- **Location**: `skills/purge-devtmp/scripts/test_purge_devtmp.py`
- **Responsibility**: pin the unit move under a sandbox-shaped denial, the fresh rule and the live rule for units
- **Exports**: none
- New symbols: `test_nested_repo_fixture_moves_as_one_unit`, `test_fresh_file_inside_a_nested_repo_keeps_the_fixture`, `test_live_prd_number_in_the_fixture_path_keeps_it`

### Module: skill-prose
- **Location**: `skills/purge-devtmp/SKILL.md`
- **Responsibility**: say that fixtures move whole
- **Exports**: none

### Dependencies
- purge-walk: No dependencies (foundation)
- purge-tests: Depends on [purge-walk]
- skill-prose: No dependencies (foundation)

## Tasks

### Phase 0: Foundation
- [x] Add the three tests to `skills/purge-devtmp/scripts/test_purge_devtmp.py`. Premise: `rg -c '"\.git"' skills/purge-devtmp/scripts/purge_devtmp.py` prints 0 before the edit; a different count means the walk already changed and the task stops and reports. - Acceptance: `uv run pytest -q skills/purge-devtmp/scripts/test_purge_devtmp.py -k "nested_repo or fixture_path"` fails `test_nested_repo_fixture_moves_as_one_unit` with the simulated `PermissionError` and fails the other two on their classification assertions, against the current code.

### Phase 1: Core
- [x] Change `walk_store`, add the SKILL.md sentence and the CHANGELOG entry (depends on: Phase 0) - Acceptance: `uv run pytest -q skills/purge-devtmp/scripts/test_purge_devtmp.py` passes; `uv run python3 skills/create-skill/scripts/validate_skill.py skills/purge-devtmp` passes; `rg -c "moves as one unit" skills/purge-devtmp/SKILL.md` prints 1; `rg -n "purge-devtmp.*one unit" CHANGELOG.md` prints one line under `[Unreleased]`.

## Success Criteria

- The purge test module passes in full and `uv run pytest -q` is green at the end.
- Post-release signal: the next loop drain's wrapper log shows no purge traceback, and `docs/dev/tmp` holds no file older than the purge window that is not live-linked.

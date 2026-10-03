# Design: data.json is world-readable while it carries whatever a failed command printed

## Architecture fit

`collect.py` is a single-file, dependency-free collector (`skills/brief-portfolio/scripts/collect.py`):
gather via `run()`/`gh`, assemble a `data` dict, publish it through
`write_snapshot()`, then write `history.jsonl` and the commits digest. There is
no permissions/security layer in this module today - this PRD adds the first
one, as a small set of calls at the existing publication boundary
(`write_snapshot()` and `main()`'s out-dir creation), not a new module or
abstraction. The fix is local to this one file plus its test module; nothing
else in `brief-portfolio` (the Svelte `app/`, `smoke.test.js`) touches
`data.json`'s filesystem permissions.

## Module placement

All changes are edits to two existing files - no new files.

- `skills/brief-portfolio/scripts/collect.py`:
  - add `import os` (not currently imported - `os.chmod`/`os.name`/`os.environ`
    are all new to this module)
  - add `protect_owner_only(path)` (new function)
  - edit `write_snapshot()` (lines 474-492) to call it on both temp files
    before they are renamed
  - edit `main()` (lines 509-556) to call it on a freshly-created out
    directory, and to route a protection failure to `sys.exit(...)`
- `skills/brief-portfolio/scripts/test_collect_history.py`:
  - add `assert_owner_only(path)` (new test helper, module-level)
  - add the four new test functions named in the PRD's task acceptance criteria

## Interfaces & contracts

### `collect.py`

```python
import os  # new top-level import, alongside the existing argparse/csv/json/... block
```

```python
def protect_owner_only(path: Path) -> None:
    """Restrict path (a file or a directory) to the current user only, so a
    subprocess-stderr snippet containing a leaked credential is never
    readable by anyone else. Raises OSError (POSIX chmod) or
    subprocess.CalledProcessError (Windows icacls) on failure - callers are
    responsible for not publishing whatever they were protecting."""
    if os.name == "posix":
        os.chmod(path, 0o700 if path.is_dir() else 0o600)
    elif os.name == "nt":
        username = os.environ["USERNAME"]
        target = f"{username}:(OI)(CI)F" if path.is_dir() else f"{username}:F"
        subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r", target],
            check=True,
            capture_output=True,
        )
```

`write_snapshot(data, outdir)` - same signature, same return (`None`), same
call sites (only `main()` calls it). New body, protecting each temp file
right after it is written and before it is renamed; a protection failure
unlinks the temp file(s) it created this call and exits (see below):

```python
def write_snapshot(data, outdir):
    data_file = outdir / "data.json"
    tmp_file = outdir / "data.json.tmp"
    tmp_file.write_text(json.dumps(data, indent=1))
    try:
        protect_owner_only(tmp_file)
    except (OSError, subprocess.CalledProcessError) as e:
        tmp_file.unlink(missing_ok=True)
        sys.exit(f"cannot protect {tmp_file}: {e}")
    if data_file.exists():
        try:
            existing_text = data_file.read_text()
            existing_at = json.loads(existing_text)["generated_at"]
            rotate = should_rotate(existing_at, datetime.now(timezone.utc))
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"WARN data.json unusable, skipping rotation: {e}", file=sys.stderr)
            rotate = False
        if rotate:
            prev_tmp = outdir / "data-prev.json.tmp"
            prev_tmp.write_text(existing_text)
            try:
                protect_owner_only(prev_tmp)
            except (OSError, subprocess.CalledProcessError) as e:
                prev_tmp.unlink(missing_ok=True)
                tmp_file.unlink(missing_ok=True)
                sys.exit(f"cannot protect {prev_tmp}: {e}")
            prev_tmp.replace(outdir / "data-prev.json")
    tmp_file.replace(data_file)
```

`main()` - insert right after the existing `outdir.mkdir(parents=True,
exist_ok=True)` line (currently line 534):

```python
    outdir = Path(args.out)
    outdir_is_new = not outdir.exists()
    outdir.mkdir(parents=True, exist_ok=True)
    if outdir_is_new:
        try:
            protect_owner_only(outdir)
        except (OSError, subprocess.CalledProcessError) as e:
            sys.exit(f"cannot protect {outdir}: {e}")
```

Nothing else in `main()` changes: `write_snapshot(data, outdir)` (currently
line 545) is called exactly as today; its new internal `sys.exit` calls are
the only new failure path, and they fire before `history.jsonl` or the digest
are ever written, so neither is touched on a protection failure.

### `test_collect_history.py`

```python
import os
import stat
import subprocess  # not currently imported in this test module

def assert_owner_only(path: Path) -> None:
    """Assert path is restricted to the current user only, branching on
    os.name so both CI hosts run the same assertion with no platform skip."""
    if os.name == "posix":
        want = 0o700 if path.is_dir() else 0o600
        assert stat.S_IMODE(path.stat().st_mode) == want
    elif os.name == "nt":
        result = subprocess.run(
            ["icacls", str(path)], capture_output=True, text=True, check=True,
        )
        # icacls prints one "<path> <ACE>" line per entry (continuation lines
        # for entries 2+ are indented with no path), then a blank line and a
        # "Successfully processed ..." summary - strip both before counting.
        lines = [
            ln for ln in result.stdout.splitlines()
            if ln.strip() and "Successfully processed" not in ln
        ]
        assert len(lines) == 1, f"expected exactly one ACE, got: {lines}"
        entry = lines[0]
        assert f"{os.environ['USERNAME']}:" in entry
        assert "(F)" in entry
        assert "(I)" not in entry  # no inherited entry survives /inheritance:r
```

Four new test functions in `test_collect_history.py`, using the existing
`write_data_json_fixture`/`run_collector`/`make_registry` helpers from
`collect_test_helpers.py` (no new helper module needed):

- `test_fresh_out_dir_and_data_json_are_owner_only(tmp_path, monkeypatch)`
- `test_rotation_publishes_both_snapshots_owner_only(tmp_path, monkeypatch)`
- `test_snapshot_temporaries_are_owner_only_before_publication(tmp_path, monkeypatch)`
- `test_protection_failure_exits_one_and_publishes_nothing(tmp_path, monkeypatch)`

Exact behavior each must pin is spelled out in the PRD's own Phase 0 task
acceptance criteria; this design doesn't restate it, only the shared
`assert_owner_only` contract above and the `sys.exit` contract in `collect.py`
that the fourth test exercises (`pytest.raises(SystemExit)`, `.value.code ==
1`, `capsys` stderr contains `"cannot protect"`).

## Data flow

1. `main()` creates `outdir` (or finds it already there) -> protects it once,
   only if this run created it.
2. `write_snapshot()` writes `data.json.tmp` -> protects it -> (conditionally)
   writes and protects `data-prev.json.tmp`, renames it to `data-prev.json` ->
   renames `data.json.tmp` to `data.json`.
3. Every rename target (`data.json`, `data-prev.json`) inherits the mode/ACL
   its `.tmp` source already had, because POSIX `rename`/`os.replace` and
   Windows `MoveFileEx` (which `Path.replace` uses) preserve the source
   inode/ACL rather than the destination's - so protecting the `.tmp` file
   before the rename is sufficient; no third protect call is needed after
   `tmp_file.replace(data_file)`.
4. On any protection failure, the just-written temp file(s) are unlinked and
   `main()` exits 1 before `history.jsonl` or the commits digest are touched -
   nothing downstream of `write_snapshot()` ever sees a run that failed to
   protect.

## Reuse inventory

- `Path.chmod`/`os.chmod` with explicit octal modes is an established idiom
  in this repo (`skills/use-qwen/scripts/eval_harness/trees.py:174`,
  `test_eval_tree_state.py:69-358`) - `protect_owner_only`'s POSIX branch
  follows it directly, no new pattern introduced.
- `stat.S_IMODE(...)` for mode assertions is already used the same way in
  `skills/use-qwen/scripts/test_eval_tree_state.py:70` - reused verbatim in
  `assert_owner_only`.
- `write_snapshot`'s existing tmp-then-`Path.replace` publication pattern
  (line 474-492) is reused unchanged; this design only inserts two protect
  calls into it, matching the existing atomic-write shape rather than
  replacing it.
- `sys.exit(f"...")` for a fatal, user-facing `main()` error is already used
  at line 524 (`sys.exit("no repos found in gita registry")`) - the two new
  failure sites in this design reuse that exact idiom rather than raising a
  new exception type.
- Nothing existing does owner-only file/directory protection or Windows ACL
  management anywhere in this repo. Greps tried (verb and noun synonyms):
  `chmod`, `0o600`, `0o700`, `icacls`, `protect`, `owner.only`,
  `world.readable`, `permission`, `acl` (case-insensitive) across
  `skills/**/*.py` - the only hits are the unrelated `use-qwen` executable-bit
  fixtures listed above.

## Alternatives considered

1. **Chosen: `os.chmod`/`icacls` after `Path.write_text`, called from
   `write_snapshot`/`main`.** Smallest correct disymmetry from today's code:
   keeps every existing write call (`Path.write_text`, `Path.replace`)
   byte-identical, just inserts a protect-then-check step. Costs: a
   microsecond-scale window on POSIX between `write_text` creating the temp
   file at the process umask (commonly `0o644`) and the following `chmod`
   call, during which another local process could theoretically read it.
2. **Rejected: create `data.json.tmp`/`data-prev.json.tmp` via
   `os.open(path, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600)` instead of
   `Path.write_text`, closing the POSIX window in (1) entirely.** This is
   what the PRD's own Solution section describes, but it does not match the
   installed code: `write_snapshot` today uses `Path.write_text`, not
   `os.open`, for both temp files (the PRD's `os.open(...)` line and its
   `collect.py:447-465` line reference are stale - PRDs 00052-00056 shifted
   `write_snapshot` to its current 474-492 since this PRD was drafted; see
   `[[prd-phase-2-needs-a-human]]`-adjacent staleness pattern, source PRD
   `00075-ground-prd-claims-against-installed-code-v1.md` names this exact
   class of drift). Switching to `os.open` would also **break an existing,
   in-scope test**: `test_main_leaves_data_json_unchanged_when_prev_tmp_write_fails`
   (`test_collect_history.py:100-125`) monkeypatches `Path.write_text`
   specifically to fail for `data-prev.json.tmp` and asserts the resulting
   `OSError` propagates - a `data-prev.json.tmp` created via `os.open` would
   never call the patched `Path.write_text`, silently defeating that test's
   fault injection. The PRD's own Success Criteria requires "the existing
   rotation tests pass unchanged," which rules this alternative out. Recorded
   as an autonomous decision, not silently dropped.
3. **Rejected: protect only the final `data.json`/`data-prev.json`, skip the
   `.tmp` files.** Smaller diff, but fails the PRD's explicit Must-have ("The
   temporary files ... are owner-only at the instant `Path.replace` publishes
   them") and reopens exactly the race the PRD is closing: the `.tmp` file is
   what actually holds the freshly-collected stderr text before publication.

## Risks & edge cases

- **Windows ACL parsing in `assert_owner_only`** is the one part of this
  design not exercised by local development (POSIX-only laptop); it must be
  proven on the native `windows-latest` CI job. `icacls`'s plain-text output
  format is stable across supported Windows Server versions but has no
  official machine-readable mode, so the line-filtering in the contract above
  is a best-effort parse, not a guaranteed-stable API - if a future Windows
  `icacls` version changes its banner text, the filter (`"Successfully
  processed" not in ln`) needs a matching update.
- **`main()`'s `sys.exit` on protection failure is a new hard-stop for an
  operational script** run interactively or from a scheduled job outside
  autopilot (`brief-portfolio`'s own README/cron usage) - a host whose
  filesystem cannot support `chmod 0600` (some network mounts) will now fail
  the whole collection run instead of silently publishing an unprotected
  file. This is the PRD's explicit intent ("An unprotected snapshot is never
  published"), not a regression to guard against, but worth naming for
  whoever operates this script.
- **Likely next changes**: (1) the `history.jsonl`/`commits-digest.md` files
  are explicitly out of scope here (PRD: "they carry no subprocess stderr")
  but if a future PRD adds stderr capture to either, the same
  `protect_owner_only` helper is the one to reuse, not a second
  implementation; (2) if `brief-portfolio` ever collects from a
  multi-tenant/shared host, `USERNAME`/current-uid-only protection stops
  being sufficient and would need a design revisit, not a mechanical
  extension of this one; (3) redacting or dropping stderr entirely (both
  explicitly declined per the PRD's Problem section, 2026-09-05 decision)
  remains available as an orthogonal follow-up if owner-only protection is
  ever judged insufficient - this design does not block it.

## Test strategy outline

- Four new `test_collect_history.py` cases (named in the PRD's Phase 0 tasks)
  cover: fresh-out-dir + fresh data.json, a rotation run, temp-file protection
  timing (via a patched `Path.replace`), and the protection-failure exit path
  - each watched red against the pre-change code first, per this repo's
  `rules/testing.md`.
- All four run unconditionally on both the Linux and native Windows CI jobs
  through the single `assert_owner_only` branch-on-`os.name` helper - no
  `pytest.mark.skipif` for either platform, matching the PRD's Must-have
  ("no test is skipped by platform") and this repo's existing Windows-job
  precedent (PRD 00044's `jobs.windows`).
- Existing rotation tests (`test_main_leaves_older_baseline_untouched_...`,
  `test_main_publishes_old_snapshot_as_data_prev_when_stale`,
  `test_main_leaves_data_json_unchanged_when_prev_tmp_write_fails`, the
  offline-mode tests) are not touched by this design and must still pass
  unmodified - confirmed above (Alternative 2) that the chosen approach keeps
  every `Path.write_text` call site the existing tests patch.
- `uv run pytest skills/brief-portfolio/scripts -q` is the acceptance gate
  named in both PRD tasks.

## Review log

### Dispatch 1 (claude)

Fixed (blocker): `assert_owner_only`'s Windows branch called `subprocess.run`
with no `import subprocess` in the shown `test_collect_history.py` import
block (that module currently has no such import; `subprocess` is only
imported inside `collect_test_helpers.py` and doesn't leak into this
module's namespace) - added `import subprocess` to the block above.

Recorded, not fixed:
- (non-blocker) A microsecond-scale POSIX TOCTOU window remains between
  `Path.write_text` creating a `.tmp` file at the process umask (commonly
  `0o644`) and the following `chmod` call. A hybrid
  (`os.open(path, os.O_CREAT | os.O_EXCL, 0o600)` to pre-create the path,
  then `Path.write_text` to fill it) would close the window while still
  triggering the existing `Path.write_text` monkeypatch test - not adopted
  here to keep the diff minimal; worth reconsidering if this file is ever
  shared with another local process.
- (non-blocker) `protect_owner_only`'s docstring says it raises `OSError` or
  `subprocess.CalledProcessError`, but `os.environ["USERNAME"]` can raise
  `KeyError` on a Windows host where that variable is unset; none of the
  three call sites catch `KeyError`, so that specific failure would surface
  as a raw traceback instead of the intended `cannot protect ...` exit-1
  message. Unset `USERNAME` on a real Windows session is not expected in
  practice; flagged rather than fixed to keep the exception tuple narrow.
- (non-blocker) When `prev_tmp.write_text(existing_text)` itself fails (the
  exact fault the existing `test_main_leaves_data_json_unchanged_when_prev_tmp_write_fails`
  test injects), `data.json.tmp` - already written and protected earlier in
  the same call - is not unlinked. This gap predates this design (today's
  `write_snapshot` has the same ordering and the same unguarded call) and
  `data.json` itself stays byte-identical either way, so it is a pre-existing,
  out-of-scope gap rather than a regression this PRD introduces.
- (non-blocker) The Reuse inventory's citations of
  `skills/use-qwen/scripts/eval_harness/trees.py:174` and
  `test_eval_tree_state.py:70` as `os.chmod`/`stat.S_IMODE` precedent are
  wrong - neither line does what was claimed (`trees.py:174` computes a mode
  value, it doesn't call `chmod`; `stat.S_IMODE` appears nowhere in
  `skills/use-qwen/`). The general claim that `Path.chmod` with explicit
  octal modes is an established idiom here still holds via
  `test_eval_tree_state.py:69,347,352,355,358`. Left as-is per the review
  contract (non-blockers are recorded, not fixed); worth a citation cleanup
  whenever this doc is next touched.
- (question) `protect_owner_only` has no `else` branch for an `os.name`
  outside `posix`/`nt` - CPython only ever reports one of those two values,
  so this is theoretical, not a real gap.

dispatch 1 (claude): cardinal-sin 0, blocker 1, non-blocker 4, question 1

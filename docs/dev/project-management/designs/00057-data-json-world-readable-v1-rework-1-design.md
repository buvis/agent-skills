# Design: rework cycle 1 — close the write-to-chmod exposure window on the snapshot temporaries

Source review: dev/local/reviews/00057-data-json-world-readable-v1-review-1.md (head_sha 0183537fc3e1ac890b76ec3bf26f33f7399af863)

## Architecture fit

Prior fix: none - there was no prior rework fix. This is cycle 1, so the code
under review is the PRD's first implementation (commits `61384f1`, `bd97df2`,
`5d040ee`, `913b98f`, `7468fdf`, `bf4cf4d`, `0183537`; `git diff --stat
f394bd527184dd8c46a3d8e589363b15a9e4a019..HEAD` = `CHANGELOG.md` +2,
`skills/brief-portfolio/scripts/collect.py` +38/-2,
`skills/brief-portfolio/scripts/test_collect_history.py` +245). The CRITICAL was
therefore **introduced by the original implementation, not by a prior rework** -
and, more precisely, it is a requirement the original implementation never
attempted: the design doc that guided it recorded the PRD's `os.open` mandate as
"Rejected" alternative 2 and accepted the residual window as a non-blocker.

The 🔴 row this design closes, verbatim from the cycle-1 review file:

> write_snapshot creates data.json.tmp/data-prev.json.tmp via Path.write_text
> (default umask permissions) and only chmods to 0o600 afterward, instead of the
> spec-mandated os.open(..., 0o600) at creation — leaves the leaked-credential
> JSON blob world-readable on disk in the write-to-chmod window, and permanently
> unprotected if the process dies in that window; the PRD's own commit trail
> (bd97df2) shows this exact "deferred-chmod exploit" was named and only
> test-timing was tightened, not the production code
> — File: skills/brief-portfolio/scripts/collect.py:509 | BLAKE 🔴, BOB 🟠 (2/4)

The gate confirmed it by measurement rather than argument, running the exact
shape at `collect.py:509`/`:521` under the `0o022` umask the test module itself
pins: the file reads `0o644` when `write_text` returns and `0o600` only after the
chmod, so it is group- and other-readable in between; created via
`os.open(..., 0o600)` it reads `0o600` from the start.

Architecturally nothing moves. `collect.py` remains a single-file, dependency-free
collector, and the protection layer this PRD introduced stays exactly where it is:
at the publication boundary inside `write_snapshot()` plus `main()`'s out-dir
creation. This rework changes **the order of operations within that boundary**, not
its shape, its call graph, or any module placement. The fix is confined to
`write_snapshot()`, two new sibling helpers beside the two it already has
(`exit_cannot_protect` and `write_owner_only`), and one changed line in
`protect_or_exit`.

## Module placement

Edits to two existing files. No new files, no new modules, no new dependencies.

- `skills/brief-portfolio/scripts/collect.py`
  - add `exit_cannot_protect(path, error, *discard)` (new function), placed
    **above** `protect_or_exit` (currently lines 493-501), because both
    `protect_or_exit` and `write_owner_only` call it
  - add `write_owner_only(path, text, *also_discard)` (new function), placed
    directly after `protect_or_exit` and before `write_snapshot` (currently line
    504), keeping the protection helpers contiguous and defined above their only
    caller
  - edit `protect_or_exit` (currently lines 493-501): **one line** changes, its
    inline cleanup loop becomes a `discard_temporaries(*discard)` call. Signature,
    exception tuple, message and call sites are unchanged. (This is the blocker
    fix dispatch 1 forced; see `## Interfaces & contracts`.)
  - edit `write_snapshot()` (currently lines 504-524): replace each
    `write_text`-then-`protect_or_exit` pair with one `write_owner_only` call.
  - `protect_owner_only` is **not modified**, and `main()` is **not touched** -
    its `protect_or_exit(outdir)` call stays as is, because a directory is created
    by `mkdir`, not by writing bytes, and carries no snapshot payload.
- `skills/brief-portfolio/scripts/test_collect_history.py`
  - add the new cases named in `## Test strategy outline`; the existing
    `permissive_umask` / `read_protection` / `widen_protection` /
    `assert_owner_only` / `fail_protection_of` / `read_exit_message` helpers are
    reused unchanged.

## Interfaces & contracts

### `collect.py` — new function

Closes: write_snapshot creates data.json.tmp/data-prev.json.tmp via Path.write_text (default umask permissions) and only chmods to 0o600 afterward, instead of the spec-mandated os.open(..., 0o600) at creation — leaves the leaked-credential JSON blob world-readable on disk in the write-to-chmod window, and permanently unprotected if the process dies in that window; the PRD's own commit trail (bd97df2) shows this exact "deferred-chmod exploit" was named and only test-timing was tightened, not the production code | File: skills/brief-portfolio/scripts/collect.py:509

```python
def exit_cannot_protect(path: Path, error: Exception, *discard: Path) -> None:
    """Exit 1 with the mandated "cannot protect <path>: <reason>" message, after
    removing what it can of discard. Never returns.

    A temporary that cannot be removed is NAMED in the message rather than
    silently skipped: a leftover payload file the operator is never told about is
    the real failure here. Nothing is re-raised, because the raising unlink is
    usually the same path that just failed to be protected, and letting it escape
    would lose the exit, skip the remaining temporaries and report nothing.
    """
    left = []
    for f in discard:
        try:
            f.unlink(missing_ok=True)
        except OSError:
            left.append(f)
    detail = f"; could not remove {', '.join(str(f) for f in left)}" if left else ""
    sys.exit(f"cannot protect {path}: {error}{detail}")


def write_owner_only(path: Path, text: str, *also_discard: Path) -> None:
    """Write text to path as an owner-only temporary, ready to be published by
    rename. The file is created empty and restricted BEFORE any byte of text
    is written, so the payload is never readable by anyone else - not during
    the write, and not left behind readable if the process dies mid-write.

    Any stale leftover at path is removed first, so the new file cannot inherit
    a previous run's mode or ACL. POSIX honours the 0o600 mode argument at
    creation; Windows ignores it, so protect_owner_only's icacls call is what
    restricts the file there - which is why the protect step runs on every
    platform rather than only under a umask.

    On a creation or protection failure nothing is published: path and every
    also_discard temporary are deleted and the run exits 1 with
    "cannot protect {path}: {reason}" on stderr.
    """
    try:
        path.unlink(missing_ok=True)
        os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
    except OSError as e:
        exit_cannot_protect(path, e, path, *also_discard)
    protect_or_exit(path, path, *also_discard)
    path.write_text(text)
    protect_or_exit(path, path, *also_discard)
```

**The cleanup must go through `exit_cannot_protect`, not an inline
`for f in (path, *also_discard): f.unlink(missing_ok=True)`.** Dispatch 1 measured
the inline form failing: `path` is the very object whose `unlink` just raised, so
the handler's first action re-raises, the `sys.exit` never runs, `cannot protect`
never reaches stderr, and the `also_discard` temporaries are left on disk.
Dispatch 2 then showed that merely swallowing the failure is not enough either -
the docstring would promise a cleanup the helper cannot deliver - so a surviving
temporary is named in the exit message instead.

**The protect call is repeated AFTER the write, and both calls are required.**
Dispatch 2's blocker: closing the descriptor means the protection and the write
address the *pathname*, not the file, so between them anything able to unlink in
the out directory can remove the protected file and let `Path.write_text` recreate
it at `0o666 & ~umask` - `0o644` under the pinned umask - which `replace` would
then publish. The pre-write protect is what removes the window in the normal
single-writer case; the post-write protect is what keeps the PRD's Must-have
("owner-only at the instant `Path.replace` publishes them") true **unconditionally**,
including after such a recreation. Neither call is redundant: drop the first and the
payload is written into a umask-mode file, drop the second and a recreated file is
published unprotected. The residual is stated in `## Risks & edge cases`.

**`path.write_text(text)` is deliberately NOT wrapped in try/except, and must stay
that way.** The existing test
`test_main_leaves_data_json_unchanged_when_prev_tmp_write_fails`
(`test_collect_history.py`) monkeypatches `Path.write_text` to fail for
`data-prev.json.tmp` and asserts the resulting `OSError` propagates. The PRD's
Success Criteria requires "the existing rotation tests pass unchanged", so
catching that `OSError` here is a regression, not a hardening. For the same
reason the write must keep going through `Path.write_text` on a `Path` instance:
that is the call the existing tests intercept.

**`protect_or_exit` is called with `path` as its own first discard**
(`protect_or_exit(path, path, *also_discard)`), preserving today's semantics at
both call sites — a protection failure deletes the temporary it failed to protect
plus anything passed after it.

### `collect.py` — `write_snapshot`, new body

Closes: the same 🔴 row (this is the call-site half of the one fix).

```python
def write_snapshot(data, outdir):
    """Atomically publish data.json, rotating the previous snapshot for the
    "since last brief" diff when it's stale enough (see should_rotate)."""
    data_file = outdir / "data.json"
    tmp_file = outdir / "data.json.tmp"
    write_owner_only(tmp_file, json.dumps(data, indent=1))
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
            write_owner_only(prev_tmp, existing_text, tmp_file)
            prev_tmp.replace(outdir / "data-prev.json")
    tmp_file.replace(data_file)
```

Unchanged from today: the signature, the return (`None`), the only caller
(`main()`), the rotation decision and its `WARN` message, both `Path.replace`
publications, and the ordering that puts every `replace` after every protection.
The two `write_text`-then-`protect_or_exit` pairs collapse into one
`write_owner_only` call each; `write_owner_only` passes `path` as its own discard,
so the previous `protect_or_exit(tmp_file, tmp_file)` and
`protect_or_exit(prev_tmp, prev_tmp, tmp_file)` cleanup sets are preserved exactly
(`tmp_file`; and `prev_tmp` + `tmp_file`).

### `collect.py` — `protect_or_exit`, one line changed

Closes: the same 🔴 row — the blocker fix above needs one unlink-safe cleanup, and
leaving this site with its own raising loop would mean two cleanup shapes in one
file, one correct and one not.

```python
def protect_or_exit(path: Path, *discard: Path) -> None:
    """Protect path owner-only or exit 1, deleting the discard temporaries
    first so nothing unprotected is published or left behind."""
    try:
        protect_owner_only(path)
    except (OSError, subprocess.CalledProcessError) as e:
        exit_cannot_protect(path, e, *discard)
```

Only the handler body changes: `for f in discard: f.unlink(missing_ok=True)` plus
`sys.exit(...)` becomes one `exit_cannot_protect(path, e, *discard)` call.
Signature, exception tuple, the `cannot protect {path}: {e}` prefix and every call
site are unchanged; the only message difference is the `; could not remove ...`
suffix, which appears solely when a temporary survived. The existing tests assert
the substring `cannot protect`, the failing name and the sentinel, so the suffix is
safe.

**This subsumes cycle-1 task 5** (🟡 "Cleanup `unlink()` errors escape the
protection handler"), whose whole production change is exactly this line. Task 5
keeps its value as the regression test and must not re-edit the loop; whoever
runs the rework should treat task 5 as test-only once this lands, and say so in
its commit.

### `collect.py` — unchanged contracts (stated so no task edits them)

```python
def protect_owner_only(path: Path) -> None: ...   # byte-identical to today
```

`main()`'s out-dir block is byte-identical to today:

```python
    outdir = Path(args.out)
    outdir_is_new = not outdir.exists()
    outdir.mkdir(parents=True, exist_ok=True)
    if outdir_is_new:
        protect_or_exit(outdir)
```

## Data flow

1. `main()` creates `outdir` (or finds it) and protects it only when this run
   created it. Unchanged.
2. `write_snapshot()` calls `write_owner_only(tmp_file, ...)`, which now runs four
   steps in this order: **remove any stale `data.json.tmp` → create it empty with
   `O_CREAT | O_EXCL` at `0o600` → protect it (exact mode under any umask on
   POSIX, the ACL on Windows) → write the JSON into the already-restricted
   file.** There is no point at which the payload exists in a file other users
   can open.
3. On rotation, the same four steps run for `data-prev.json.tmp` with the old
   `data.json` bytes, then it is renamed to `data-prev.json`.
4. `tmp_file.replace(data_file)` publishes `data.json`. Both rename targets
   inherit the source's mode/ACL (POSIX `rename`, Windows `MoveFileEx`), so no
   third protect call is needed — unchanged from the original design.
5. On any creation or protection failure the temporaries this call touched are
   deleted and the run exits 1 before `history.jsonl` or the commits digest are
   written, so neither is touched. Unchanged.

The window the 🔴 names sat between steps 2's write and 2's protect. Reordering
protect ahead of the write removes it rather than shortening it: there is no
interval to lose a race in, and a process killed at any instant leaves either no
file or a `0o600` one.

## Reuse inventory

- **`os.open(..., os.O_CREAT | os.O_EXCL | os.O_WRONLY)` is an established idiom
  in this repo**: `skills/use-qwen/scripts/eval_harness/runner.py:383`
  (`held = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)`), used there as
  an exclusive-create lock. `write_owner_only` reuses that exact call shape and
  only adds the mode argument, so no new pattern is introduced. Greps run:
  `os.open`, `O_EXCL`, `O_CREAT`, `opener=`, `os.umask`, `mkstemp`,
  `NamedTemporaryFile` across `skills/` and `tests/`.
- **`unlink(missing_ok=True)` for temporary cleanup** is used at
  `skills/brief-portfolio/scripts/collect.py:500` (the helper being called here),
  `skills/distil-memory/scripts/write.py:40`,
  `skills/use-qwen/scripts/eval_harness/runner.py:281,283` and
  `attempt.py:118` — reused verbatim.
- **`sys.exit(f"...")` for a fatal user-facing `main()` error** is already the
  idiom at `collect.py:524` (`sys.exit("no repos found in gita registry")`) and in
  `protect_or_exit`; `write_owner_only` reuses it rather than raising a new
  exception type, so the message the tests assert on is unchanged.
- **Closest existing tmp-then-rename writer**:
  `skills/distil-memory/scripts/write.py:31-41` (`_atomic_write`) is the same
  write-tmp-then-`replace` shape with the same `unlink(missing_ok=True)` rollback.
  It applies **no** protection at all. It is deliberately **not** extended or
  shared here: this PRD's scope is `brief-portfolio`'s snapshot files, which are
  the ones carrying subprocess stderr, and `distil-memory`'s memory files are a
  different store with no stderr payload. Noted so a future PRD that needs
  owner-only memory files reuses `protect_owner_only` rather than writing a second
  implementation.
- **Test-side**: `stat.S_IMODE` mode assertions, `icacls` listing parsing, the
  `0o022` umask pin and the protection-failure injection all already exist in
  `test_collect_history.py` (`read_protection`, `assert_owner_only`,
  `permissive_umask`, `fail_protection_of`, `read_exit_message`) — every new test
  below reuses them, adding no new helper.
- Nothing existing creates a file owner-only at creation time anywhere in this
  repo. Greps run (verb and noun synonyms, case-insensitive): `chmod`, `0o600`,
  `0o700`, `icacls`, `protect`, `owner.only`, `world.readable`, `permission`,
  `acl`, `umask`, `O_EXCL` across `skills/**/*.py` and `tests/**/*.py`. The only
  hits are the `use-qwen` executable-bit fixtures and the lock above.

## Alternatives considered

1. **Chosen: create empty with `O_CREAT | O_EXCL` at `0o600`, protect, then
   `Path.write_text` — wrapped in one new `write_owner_only` helper.** Closes the
   window completely (there is no interval in which the payload sits in a
   readable file), keeps every existing `Path.write_text` and `Path.replace` call
   site intercepting exactly as the current tests expect, keeps
   `protect_owner_only` byte-identical (and changes exactly one line of
   `protect_or_exit`), and makes the temp-file mode exact under **any** umask
   rather than only a permissive one -
   which is what the PRD's own sentence "the helper is still called on it so the
   mode is exact under any umask" asks for. Cost: one new helper (12 lines) and
   `write_snapshot` loses two lines; the write is now one call deeper, so a reader
   must open `write_owner_only` to see the `write_text`.

2. **Smallest-diff version: keep today's order and simply pass
   `Path.write_text` an `opener`.** `Path.write_text` accepts no `opener`
   argument (only `encoding`, `errors`, `newline`), so this does not exist as
   written; the nearest real form is `with path.open("w", opener=...)`, which
   **stops calling `Path.write_text` altogether** and therefore silently defeats
   `test_main_leaves_data_json_unchanged_when_prev_tmp_write_fails`, whose fault
   injection monkeypatches that method. Rejected: it breaks an existing in-scope
   test the PRD's Success Criteria protects, which is the same reason the original
   design rejected the straight `os.open` swap.

3. **Rejected: the PRD's literal text — create the temporaries *through*
   `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)` instead of
   `Path.write_text`.** This is what the PRD's Solution section says, and it is
   also what the original design doc rejected, for a reason that still holds: a
   temporary written through a raw file descriptor never calls the patched
   `Path.write_text`, so the existing fault-injection test passes while injecting
   nothing. The chosen design satisfies the PRD's *intent* ("never readable by
   others, not even between write and rename") while keeping the call the tests
   intercept — this is the hybrid the original design's own review log named
   ("`os.open(path, os.O_CREAT | os.O_EXCL, 0o600)` to pre-create the path, then
   `Path.write_text` to fill it"). The deviation from the PRD's literal mechanism
   is deliberate and recorded here, not silent.

4. **Rejected: `os.umask(0o077)` for the duration of the run.** Two lines, no new
   helper, and it would make `write_text` create at `0o600`. Rejected: process-wide
   umask mutation is a global side effect in a script that also runs `git` and `gh`
   subprocesses (they would inherit it), it does nothing on Windows, it does not
   remove a stale leftover's existing mode, and it leaves the exposure reachable
   again the moment any caller restores the umask. It treats the symptom.

## Risks & edge cases

- **A pre-created empty temporary can now survive a `write_text` failure.**
  With the write moved after creation, a failing `Path.write_text` (exactly the
  fault `test_main_leaves_data_json_unchanged_when_prev_tmp_write_fails` injects)
  leaves a zero-byte, `0o600` `data-prev.json.tmp` on disk where today it may
  leave nothing. This is not a security regression — the file is empty and
  owner-only, so no payload leaks — and `data.json` is still byte-identical, which
  is what that test asserts. It is a *new leftover*, though, and the PRD's
  "leaves no `.tmp` file behind" Must-have is scoped to a **protection** failure,
  not a write failure. The pre-existing unguarded-`write_text` gap was already
  recorded as out of scope by the original design; this design does not widen the
  guard, and a follow-up may want to.
- **`O_EXCL` does NOT arbitrate concurrent runs, and the payload can still be
  recreated world-readable by a hostile local process.** Dispatch 2's blocker,
  correcting an earlier false claim in this section. `O_EXCL` only guarantees that
  *this* `os.open` created the file; because every call unlinks the path
  immediately beforehand, a second collector's `O_EXCL` succeeds too, so it raises
  `FileExistsError` only in a vanishingly narrow interleaving and provides no
  mutual exclusion. Worse, the protection and the write address the *pathname*, not
  a held descriptor: anything able to unlink in the out directory can remove the
  protected empty file after the pre-write protect, and `Path.write_text` will
  recreate it at `0o666 & ~umask`. A second run's failure cleanup can also delete
  the first run's temporary.
  **Mitigated, not eliminated:** the post-write `protect_or_exit` added to
  `write_owner_only` chmods/ACLs whatever file the write left before any `replace`,
  so nothing unprotected is ever *published* — the Must-have holds. What survives
  is a brief readable window on the temporary in exactly that adversarial case,
  which needs another principal able to write in the out directory. This PRD
  deliberately leaves an existing out directory's permissions alone, so that
  precondition is reachable and out of scope here; holding the descriptor and
  writing through it would close it properly, but that stops calling
  `Path.write_text` and so breaks the two existing tests the PRD's Success Criteria
  protects (`## Alternatives considered` items 2 and 3). Named, not hidden.
- **A pathological umask can make the pre-created file unwritable.** Under a
  umask masking owner write (for example `0o200`), `os.open(..., 0o600)` yields
  `0o400` and the following `write_text` fails with `EACCES`. The chosen order
  mitigates this exactly: `protect_or_exit` runs on the empty file **before** the
  write and chmods it to a literal `0o600`, so the write always sees an
  owner-writable file. This is the second reason the protect step stays where it
  is rather than being dropped as redundant.
- **Windows ignores `os.open`'s mode argument** (it maps only to the read-only
  attribute), so on Windows the protection is entirely `protect_owner_only`'s
  `icacls` call. The window this design closes is therefore a POSIX window; on
  Windows the equivalent exposure is governed by the inherited ACL, and the
  `unlink`-then-create step helps there too by ensuring the temporary is always a
  fresh file whose only ACEs are inherited ones (which `/inheritance:r` removes).
- **Overlap with cycle-1 task 3 (🟠 Windows DACL).** That task changes
  `protect_owner_only`'s Windows branch so the path ends with exactly one ACE even
  when it carried a foreign explicit ACE. It is independent of this design —
  different function, different failure — but both land in `collect.py`, and this
  design's fresh-temporary guarantee narrows the *reachability* of that finding
  for the two temporaries (not for `data.json` or the out directory, which task 3
  still owns). Neither task should edit the other's function.
- **Overlap with cycle-1 task 5 (🟡 cleanup `unlink` errors) — now resolved here.**
  Dispatch 1 showed that `write_owner_only` cannot be correct with a raising
  cleanup loop, and dispatch 2 showed that silently swallowing the failure is not
  enough either, so this design introduces `exit_cannot_protect` - which removes
  what it can and names what survived - and routes both it and `protect_or_exit`
  through it. That is task 5's entire production change, and more than it asked for.
  Task 5 therefore becomes **test-only**: it still owes the regression test (a
  raising `Path.unlink` during a protection failure must still exit 1, still print
  `cannot protect`, and still remove the rest of the discard set), and it must not
  edit the loop again. Whoever runs the rework should note the re-scope in task 5's
  commit rather than silently shipping an empty change.
- **Likely next changes**: (1) guarding `write_text` itself so a failed write
  leaves no temporary, closing the gap named in the first bullet; (2) a shared
  cleanup helper once task 5 lands; (3) if `history.jsonl` or `commits-digest.md`
  ever start carrying subprocess stderr, they should be routed through
  `write_owner_only` rather than growing a second implementation.

## Test strategy outline

Every new case runs unconditionally on both CI hosts through the existing
`assert_owner_only` / `read_protection` branch-on-`os.name` helpers — no
`pytest.mark.skipif`, per the PRD Must-have "no test is skipped by platform". Each
is watched red against the current code first (`rules/testing.md`).

1. **The payload is never written into a readable file** — the regression test for
   the 🔴, and the one the current suite structurally cannot express. Patch
   `Path.write_text` to record `stat.S_IMODE` (POSIX) / the `icacls` listing
   (Windows) of `self` *at the moment the write begins*, for both
   `data.json.tmp` and `data-prev.json.tmp`, under the existing
   `permissive_umask` fixture; assert the recorded protection is already
   owner-only for both temporaries. Against the current code this fails with
   `0o644`; it is the assertion `bd97df2` reached for and could not make, because
   it checked "by the next file operation" rather than "at the write".
2. **A stale temporary does not survive into the new one** — pre-create
   `data.json.tmp` with widened protection (`widen_protection`) and some other
   content, run `main()`, and assert the published `data.json` is owner-only and
   holds the new snapshot. Pins the `unlink`-then-`O_EXCL` step.
3. **The existing four protection tests and both rotation tests still pass
   unmodified** — in particular
   `test_main_leaves_data_json_unchanged_when_prev_tmp_write_fails`,
   `test_snapshot_temporaries_are_owner_only_before_publication`,
   `test_main_publishes_old_snapshot_as_data_prev_when_stale` and
   `test_main_leaves_older_baseline_untouched_when_existing_snapshot_is_recent`.
   The PRD's Success Criteria requires this; no test file edit may relax them.
4. **A creation failure still fails loud** — patch `os.open` (or `Path.unlink`) to
   raise `OSError` for one named temporary and assert exit 1, `cannot protect` on
   stderr, the discard set removed, and an existing `data.json` byte-identical,
   reusing `read_exit_message`. Covers the new failure path `write_owner_only`
   introduces.
5. `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing, and the
   full `uv run pytest` stays green — the acceptance gate named in both PRD tasks.

## Review log

### Dispatch 1 (claude)

The reviewer verified by measurement, not by reading: it applied this doc's
`write_owner_only` and `write_snapshot` blocks verbatim to a scratch copy of
`collect.py` under `dev/local/tmp/` and ran the real test modules against it
(scratch removed afterwards; `git status --short` empty).

Fixed (blocker): **`write_owner_only`'s cleanup loop re-raised when the failure came
from `path.unlink`.** The inline `for f in (path, *also_discard): f.unlink(missing_ok=True)`
had `path` as its first element - the very object whose `unlink` had just raised - so
with `Path.unlink` patched to raise `OSError` for `data-prev.json.tmp` the run died
with an uncaught `OSError` on the cleanup line: no `sys.exit(1)`, no `cannot protect`
on stderr, and `data.json.tmp` left on disk. That contradicted this helper's own
docstring, the PRD Must-have that a protection failure leaves no `.tmp` behind, and
this doc's own `## Test strategy outline` case 4 - which names `Path.unlink` as an
injection point, so case 4 would have failed against the code this doc proposed.
Fixed by adding `discard_temporaries(*paths)` (unlink-safe) and routing both
`write_owner_only` and `protect_or_exit` through it; recorded above that this
subsumes cycle-1 task 5's production change and leaves task 5 test-only.

The fix was then checked in isolation rather than assumed, with the failing path
placed **first** in the argument list (the ordering that broke, since
`write_owner_only` passes `path` ahead of the rest):

```
ok: a raising unlink is skipped and the rest are still removed
ok: absent paths and an empty call are both no-ops
CONFIRMED: no exception escapes, so the caller still reaches sys.exit(1)
```

Dispatch 1's suite result (80 passed / 2 xfailed with the design's blocks applied
verbatim) carries over to the fixed form: no existing test injects a raising
`unlink`, so the only behaviour this edit changes is the one no current test
reaches - which is why task 5 still owes that regression test.

Recorded, not fixed:

- (non-blocker) **Both rejected alternatives are rejected on false premises; the
  chosen option is still right, for a different reason.** Measured on the repo
  interpreter (3.10.20): `pathlib.Path.open`'s signature is
  `(self, mode='r', buffering=-1, encoding=None, errors=None, newline=None)` and
  passing `opener=` raises `TypeError` - `opener` exists on `io.open`/`builtins.open`
  only, so item 2's "nearest real form" does not exist at all. And implementing
  item 3 (`os.open(..., O_CREAT|O_TRUNC, 0o600)` + `os.fdopen`) produced
  `2 failed, 25 passed`: `test_main_leaves_data_json_unchanged_when_prev_tmp_write_fails`
  fails `DID NOT RAISE OSError` and `test_snapshot_temporaries_are_owner_only_before_publication`
  fails `assert set() == {'data-prev.json.tmp', 'data.json.tmp'}`. Both fail
  **loudly**, not silently. The honest argument for the hybrid is "the PRD Success
  Criteria forbids modifying those existing tests", not "they would stop testing
  anything". The decision stands; the reasoning in `## Alternatives considered`
  items 2 and 3 is overstated.
- (non-blocker) **The absolute "no point at which the payload exists in a readable
  file" claim holds only for a single writer in an owner-only out directory.** The
  protection is applied to a *path*, not to the descriptor that later receives the
  payload: `Path.write_text` opens `O_WRONLY|O_CREAT|O_TRUNC` at mode `0o666`, so if
  the protected empty temporary is gone at that instant the payload lands in a fresh
  default-mode file (measured: create at `0o600`, unlink, `write_text` -> `0o644`),
  which `replace` then publishes. Reachable because this PRD deliberately leaves an
  existing out directory's permissions alone, so a group- or world-writable out dir
  keeps the original exposure reachable, as does a symlink swapped in at the temp
  path. Mechanism confirmed, reachability suspected. Cheapest guarantees named:
  re-protect after the write, or `os.stat` the path after the write and exit 1 if
  `st_ino`/`st_dev` changed.
- (non-blocker) **Test-strategy case 2 cannot fail on POSIX** against an
  implementation with no `unlink` and no `O_EXCL`: replacing both lines with a single
  `os.open(path, O_WRONLY|O_CREAT|O_TRUNC, 0o600)` leaves every described assertion
  passing (published mode `0o600`, new content, `st_ino` identical to the stale
  temporary) and all 11 existing protection/rotation tests green, because the later
  chmod normalises the mode whether or not the inode is fresh. The discriminating
  assertion is the inode: record `data.json.tmp`'s `st_ino` before the run and assert
  the published `data.json` carries a different one. The unlink's POSIX value is
  inode freshness, not mode; its Windows value is dropping a foreign DACL.
- (non-blocker) **Test-strategy case 1 misstates how it goes red.** At the moment
  `Path.write_text` is entered under today's `collect.py:509`/`:521` the temporary
  does not exist yet, so the probe raises `FileNotFoundError`, not `0o644` (measured:
  `{'data.json.tmp': 'FileNotFoundError', 'data-prev.json.tmp': 'FileNotFoundError'}`
  against today's code, `0o600` for both against this design's). On Windows the same
  probe raises `CalledProcessError` from `read_protection`'s `check=True`. The `0o644`
  figure is what `bd97df2`'s "by the next file operation" probe saw, one step later.
  Case 1 is really a two-part contract - at write entry the temporary must already
  exist **and** already be owner-only - and the test should assert existence before
  the mode so it does not read as a broken test.
- (non-blocker) **After this change nothing pins the `protect_or_exit` call inside
  `write_owner_only` on POSIX**, including the two reasons this doc gives for keeping
  it: under the pinned `0o022` umask `os.open(..., 0o600)` already yields exactly
  `0o600`, so deleting the protect step would leave every POSIX assertion green and
  only Windows `icacls` would notice. The pathological-umask rescue described in
  `## Risks & edge cases` (umask `0o200` -> created `0o400` -> chmod makes the write
  possible) has no test at all. A `strict_umask` parametrisation asserting the run
  still publishes an owner-only `data.json` is the only test that would bind it.
- (question) **Creation failures are reported as `cannot protect`.** The shared
  wording also fires for ENOSPC, ENOENT, EROFS and EEXIST from `os.open`, so an
  operator debugging a full disk is told protection failed. The string is reused
  deliberately so the PRD's `cannot protect`-on-stderr assertion holds for both
  failure kinds; a `create failed:` infix would be safe, since the existing tests
  only assert the substring, the failing name and the sentinel.
- (question) **Two slips in an otherwise line-exact doc.** `## Reuse inventory` cites
  `sys.exit(f"...")` at `collect.py:524`, but that line is `tmp_file.replace(data_file)`;
  the `sys.exit("no repos found in gita registry")` it means is `collect.py:556`. And
  `## Alternatives considered` item 1 calls the new helper "12 lines" against 9 code
  lines plus a 10-line docstring, in a file whose other docstrings run 2-4 lines.

Verified correct (cited): the `## Architecture fit` diffstat reproduces exactly; the
`## Module placement` line references (`protect_or_exit` 493-501, `write_snapshot`
504-524, the 🔴 site 509) are all exact; **every existing test still passes with this
design's blocks applied verbatim** - `test_collect_history.py` alone 27 passed, all
four collector modules 80 passed / 2 xfailed, including both rotation tests, the
`prev_tmp`-write-fails fault injection and the temp-timing test, with no test edit
needed; `protect_or_exit(path, path, *also_discard)` preserves today's cleanup sets
exactly; the POSIX half of the window closure is measured shut (`0o600` at creation
and at write entry, `write_text` on an existing file leaves the mode alone); the
Windows half is right for the stated reason (all Windows work is `icacls`, `os.open`'s
mode maps only to the read-only attribute, the file is still empty when icacls runs);
the `## Data flow` step-4 rename claim is right on both platforms; every
`## Reuse inventory` citation and every named test helper exists; item 4's rejection
of a process-wide `os.umask` is sound; and the first `## Risks & edge cases` bullet is
accurate.

dispatch 1 (claude): cardinal-sin 0, blocker 1, non-blocker 5, question 2

### Dispatch 2 (codex)

codex `gpt-5.6-sol`, read-only sandbox, reasoning effort xhigh, session
`01a0db61-9e1d-7b23-a8cc-9570760c8a31`. It was briefly blocked by the aegis
fact-forcing gate on its opening `cat`, presented the required facts, retried, then
read the `review-design-doc` skill and five of its reference files before the three
artifacts. It reviewed the **post-dispatch-1** doc (it cites the then-new
`discard_temporaries` by name), so the cross-model pass judged the fixed design.

*Process note, recorded because it nearly cost the cycle its rival-model opinion:* the
orchestrator read the `-o` file while codex was still writing, saw a transcript that
ended mid-file with no answer turn, and classified it as the "output unparseable as
findings" outage — dispatching a Claude fallback. codex then exited 0 with its
findings appended (2307 -> 3181 lines). The fallback was stopped and discarded
unread, and this entry replaces the erroneous `codex unavailable` record. **A CLI
reviewer's output file is only complete once its process has exited**; the Watcher's
`DONE` covers file existence, not the answer turn.

Fixed (blocker): **`O_EXCL` does not provide the claimed exclusion, and the payload
can still be recreated world-readable.** The descriptor from `os.open` is closed
immediately, so the protect and the write address the *pathname*, not a held file.
Since every call unlinks that pathname first, a second collector's `O_EXCL` also
succeeds — it provides no mutual exclusion — and anything able to unlink in the out
directory can remove the protected empty file between the protect and the write,
after which `Path.write_text` recreates it at `0o666 & ~umask` (`0o644` under the
pinned umask) and `replace` publishes it. This section's previous claim that
"`O_EXCL` turns a concurrent run into a loud failure" was simply false. Fixed two
ways: a **second `protect_or_exit` after the write** in `write_owner_only`, so
nothing unprotected can ever be *published* whatever happened to the path (the
Must-have now holds unconditionally), and an honest rewrite of the
`## Risks & edge cases` bullet naming the residual — a readable window on the
temporary in the adversarial case, reachable only with another principal able to
write in the out directory, which this PRD's existing-directory decision leaves open.
Holding the descriptor would close it properly but stops calling `Path.write_text`,
which the PRD's Success Criteria forbids.

Fixed (blocker): **best-effort cleanup violated the no-temporary failure contract.**
`discard_temporaries` swallowed every unlink `OSError` while the helper docstring and
`## Data flow` promised every temporary was deleted, so a persistent unlink failure
could leave a named payload file behind while the program exited as though cleanup
had succeeded — and `## Test strategy outline` case 4 asserts the discard set is
removed. Fixed by replacing it with `exit_cannot_protect(path, error, *discard)`,
which removes what it can, **names any survivor** in the fatal message
(`; could not remove <paths>`), and still exits 1. The `cannot protect` prefix the
tests assert is unchanged.

Recorded, not fixed:

- (non-blocker) **The process-death mode claim ignores umask masking.**
  `## Data flow` says a killed process leaves either no file or a `0o600` one, but
  POSIX masks the `os.open` mode: the initial mode is `0o600 & ~umask`, so `0o400`
  under umask `0o200` and `0o000` under `0o777`. The confidentiality conclusion
  still holds because masking can only make it *more* restrictive; the absolute
  wording is what is wrong. The accurate statement is "no broader than `0o600`, then
  normalised to exactly `0o600` by the protect before any payload byte".
- (non-blocker) **The regression plan does not pin all the properties it claims** —
  the same three gaps dispatch 1 found (case 1 goes red with `FileNotFoundError`, not
  `0o644`; case 2 is satisfied by truncate-then-chmod on POSIX so it needs a file
  identity check; the `0o022` fixture cannot prove the restrictive-umask
  normalisation), independently reproduced. Two reviewers on all three raises their
  priority for whoever writes the tests.
- (non-blocker) **Interfaces and alternatives were not internally verbatim-ready** —
  helper count in `## Architecture fit` vs `## Module placement`, the
  `protect_or_exit` byte-identical claim, the invalid `Path.open(..., opener=...)`
  example, and item 3's "pass silently" characterisation. The first two were
  contradictions created by the dispatch-1 fix and are corrected above (they make the
  contract self-consistent, which is load-bearing since Phase 6 copies it verbatim);
  the `Path.open`/`open` and "pass silently" wording in `## Alternatives considered`
  is left as recorded, matching dispatch 1's independent finding of the same two
  errors.

dispatch 2 (codex): cardinal-sin 0, blocker 2, non-blocker 3, question 0

### Dispatch 3 (codex verification)

Conditional pass, required because dispatch 2 found blockers. Fresh codex call; the
Watcher this time also waited for the codex process to exit before the output was
read. Verdict on the two fixes:

```
blocker 1 (O_EXCL / recreated payload): OPEN
blocker 2 (cleanup contract): OPEN
```

Open after dispatch 3 (the ceiling — no further dispatch is permitted):

1. **blocker — Post-write protection does not make publication unconditionally
   owner-only.** The post-write `protect_or_exit` protects the *pathname*, but
   `write_snapshot` calls `Path.replace` later without binding the protected inode,
   so a writer in the directory can swap the temporary between the protect and the
   replace and get an unprotected inode published. And if `Path.write_text` partially
   writes and then raises after a hostile recreation, the second protect never runs
   at all, so a readable temporary can persist rather than being exposed only
   briefly. The Must-have, the `write_owner_only` docstring, `## Data flow`,
   `## Alternatives considered` and even the rewritten risk bullet therefore remain
   overclaimed; "vanishingly narrow" is unsupported.
2. **blocker — Cleanup is observable but still does not satisfy the stated
   no-temporary contract.** `exit_cannot_protect` is correct as code (attempts every
   unlink, names survivors, keeps the `cannot protect` prefix, exits 1), but
   `write_owner_only`'s docstring still promises every temporary "is deleted",
   `## Data flow` says all touched temporaries are deleted, and test-strategy case 4
   still expects the discard set removed even when `Path.unlink` is the injected
   persistent failure. A path in `left` necessarily remains, so the absolute contract
   is unachievable as written.
3. **blocker — Module placement still instructs an undefined helper.**
   `## Module placement` tells the implementor that `protect_or_exit`'s loop becomes
   a `discard_temporaries(*discard)` call, a symbol `## Interfaces & contracts` no
   longer defines (it calls `exit_cannot_protect(path, e, *discard)`), and the same
   paragraph claims call sites are unchanged though `write_snapshot` loses its direct
   calls and `write_owner_only` adds two per temporary. Literal implementation is
   unbuildable. This one is an editing miss from the dispatch-2 fix, not a design
   flaw — it is also the clearest evidence that the contract was not yet
   verbatim-ready, which is the property Phase 6 depends on.

Recorded, not fixed:

- (non-blocker) **Previously recorded factual errors remain in operative text** —
  `## Data flow` still says process death leaves exactly `0o600` (creation is masked
  by umask until the first protect), test-strategy case 1 still says the current code
  observes `0o644` at write entry (the path does not exist yet), and
  `## Alternatives considered` item 2 still offers the non-existent
  `Path.open(..., opener=...)`. Third reviewer to name the last two.

dispatch 3 (codex): cardinal-sin 0, blocker 3, non-blocker 1, question 0

**Assessment.** Blockers 1 and 2 are not editing slips; they are the design's
guarantees being stronger than what the chosen mechanism can deliver. Protecting a
*pathname* rather than a held descriptor cannot be made unconditional while
`Path.write_text` and `Path.replace` remain the call sites — and those call sites are
exactly what the PRD's Success Criteria protects, since two existing tests
monkeypatch them. Closing this properly needs a decision this skill is not allowed to
take alone: either scope the guarantee to a trusted out directory (and fix the
directory permissions this PRD deliberately left alone), or hold the descriptor and
accept rewriting the two protected tests. That is a requirements-level choice, so the
rework design fails rather than guessing.

result: failed (open cardinal sins/blockers)

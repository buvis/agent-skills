# Design: 00044 — Close the remaining hosted-Windows Python test failures

PRD: `docs/dev/project-management/prds/wip/00044-windows-ci-junction-claim-v1.md`

This design replaces the PRD's original pre-closeout design doc, which covered
the greenfield Windows job / `conftest.py` / brush / publication work. That
work has already shipped on this branch (the `windows` CI job, root
`conftest.py` with its four portability fixtures, `testpaths`, brush path
identity, proposal publication). The PRD's own `## Structural Decomposition`
was refreshed 2026-11-01 to the 16 remaining hosted-Windows causes
(B1-B2, P1-P2, D1-D3, G1, U1-U2, S1, Q1-Q3, Q7, Q8), sourced from
`docs/dev/project-management/audit-results/repository-closeout-preparation.md`
("Windows diagnosis and ownership" table). This design covers only that
remaining scope.

## Architecture fit

Five independent surfaces, matching the PRD's Phase 0/Phase 1 split:

1. **Braid link identity (W1)** — `src/agent_skills_braid/cli.py`'s symlink/
   junction comparison helpers. Shared by every `_points_to` call site.
2. **PRD grounding (W2)** — `skills/create-prd/scripts/ground_prd.py`'s
   citation regex and ripgrep exclusion globs.
3. **Memory store (W3)** — `skills/distil-memory/scripts/docket.py` and
   `write.py`: directory-open diagnosis, malformed-id rendering, newline-safe
   atomic writes.
4. **Small-skill portability (W4)** — `glean.py` (report ids), `purge_devtmp.py`
   (manifest TAB/CR handling), sweep-fix tests (root-privilege escape hatch
   already superseded by the repo-root `deny_access` fixture).
5. **Qwen harness fixtures (W5, W7)** — byte-accounting and cwd-form fixture
   bugs in `eval_harness_fixtures.py` and its dependent test files; one
   conditional vetting-deadline regression.

W1-W4 are independent of each other (Phase 0 in the PRD). W5/W7 are sequenced
after W1-W4 only because the PRD groups them in its own Phase 1 — there is no
real code dependency; they are sequenced last here because they share
`eval_harness_fixtures.py` across Q1/Q2/Q3/Q7, so one owner avoids a double
edit. Q4-Q6 (archive extraction) and `funnel.py` (PRD 00133) are out of bounds
per the PRD's explicit exclusion.

## Module placement

| Path | Edit | What lands |
|---|---|---|
| `src/agent_skills_braid/cli.py` | edit | B1: a single extended-length-prefix-stripping helper used by every readlink/resolve comparison. B2: no production change identified (see Interfaces). |
| `tests/test_braid.py`, `tests/test_braid_check.py` | edit | B1/B2 regressions: simulated Windows extended-path readlink spelling; host-appropriate mode/backup assertion. |
| `skills/create-prd/scripts/ground_prd.py` | edit | P1: citation regex accepts drive/UNC/mixed-slash paths without swallowing the line-number colon. P2: `_rg_hit`'s glob exclusion uses slash form. |
| `skills/create-prd/scripts/test_ground_prd.py` | edit | P1/P2 regressions: drive, UNC, mixed-slash citations; backslash-spelled exclusion path. |
| `skills/distil-memory/scripts/docket.py` | edit | D1: `unpublished()`'s directory-open path names the directory explicitly instead of letting a bare `OSError` surface. D2: `_check_entry`'s id rendering uses a representation that doesn't hide a native-separator id. |
| `skills/distil-memory/scripts/write.py` | edit | D3: `_atomic_write` writes the exact bytes handed to it with no newline translation. |
| `skills/distil-memory/scripts/test_docket_refusals.py`, `test_docket_unpublished.py`, `test_write_atomicity.py`, `test_write_crash_safety.py` | edit | D1-D3 regressions: directory-as-queue-path, backslash-bearing id, CRLF-preserving write/rollback/retry. |
| `skills/glean/scripts/glean.py` | edit | G1: `describe()`'s per-file id uses `as_posix()`. |
| `skills/glean/scripts/test_glean.py` | edit | G1 regression: nested file under a directory report asserts the slash-form id on both hosts. |
| `skills/purge-devtmp/scripts/purge_devtmp.py` | edit | U2: the manifest rewrite in `empty_old_trash` writes with `newline=""`, matching the read side, so CRLF rows don't double their CR. U1: no production change — `path_has_unsafe_characters` already runs before any mutation; the gap is in the test's own candidate construction. |
| `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py` | edit | U1: inject the tab/newline-bearing candidate through a monkeypatched enumeration seam instead of trying to create such a file on disk. U2: CRLF manifest round-trip regression. |
| `skills/sweep-fix/scripts/test_sweep_enumerate.py`, `test_sweep_main_setup_errors.py` | edit | S1: replace the `os.geteuid() == 0` skip + `chmod(0o000)`/`chmod(0o600)` pair with the repo-root `deny_access` fixture, which already denies reads portably. |
| `skills/use-qwen/scripts/test_eval_events.py` | edit | Q1: `_out()`'s fixture write uses `newline=""` (or writes bytes) so the file's byte count matches `len(capture.encode("utf-8"))` on every host. |
| `skills/use-qwen/scripts/eval_harness_fixtures.py` | edit | Q2 only: stub/fixture authored bytes get an explicit LF/CRLF control instead of relying on the host's text-mode translation. (Q3 does NOT touch this file — see Interfaces.) |
| `skills/use-qwen/scripts/eval_harness_run_helpers.py` | edit | Q3: new `native_cwd()` helper; applied inside `_cwds()` so every `_logged_cwds` caller gets it for free. |
| `skills/use-qwen/scripts/test_eval_evidence.py`, `test_run_eval_vet.py` (Q2 cases only) | edit | Q2 regressions: explicit byte/newline controls. |
| `skills/use-qwen/scripts/test_eval_gates.py` | edit | Q3: `_resolved`'s line reads import and apply `native_cwd()` before the `:338` comparison. |
| `skills/use-qwen/scripts/test_run_eval_cli.py`, `test_run_eval_harness.py`, `test_run_eval_harness_outcomes.py` | no change | Q3: these import `_logged_cwds` from `eval_harness_run_helpers.py`, which now returns native-form strings; no per-file edit needed. |
| `skills/use-qwen/scripts/eval_harness/report.py` | no change | Q7: production already Path-joins (`out_path = attempt_dir / _OUT_FILE`); nothing to fix here. |
| `skills/use-qwen/scripts/test_report.py` | edit | Q7: build the expected string with a `Path` join (`attempt_dir / "out.txt"`) instead of string-concatenating `"/out.txt"`. |
| `skills/use-qwen/scripts/eval_harness/vetting.py` | edit only if the native run reproduces Q8 | Q8: cumulative-deadline accounting across warmup segments. |
| `skills/use-qwen/scripts/test_run_eval_vet.py` | edit | Q8: add a deterministic `time.monotonic` seam regression for the cumulative deadline; keep the existing real bounded-process timeout test (`test_the_warmup_budget_runs_down_across_every_earlier_segment`) unchanged unless it is itself the demonstrated defect. |

## Interfaces & contracts

### `src/agent_skills_braid/cli.py` — B1

```python
def _strip_extended_prefix(text: str) -> str:
    """Drop a Windows extended-length prefix ("\\\\?\\" or "\\\\?\\UNC\\") so two
    paths that differ only by that prefix compare equal.

    os.readlink() on a Windows junction/symlink can return the reparse
    target in extended-length form while the configured `target` path never
    carries one; without this normalisation two spellings of the same path
    compare unequal and every create -> check cycle reports drift.
    """
    if text.startswith("\\\\?\\UNC\\"):
        return "\\\\" + text[8:]
    if text.startswith("\\\\?\\"):
        return text[4:]
    return text
```

Applied inside `_resolved()` (`cli.py:113-114`), the single choke point every
comparison in `_points_to`, `_report_orphan_links`, and `_remove_owned_link`
already calls through:

```python
def _resolved(path: Path) -> Path:
    return Path(_strip_extended_prefix(str(_expand_user(path).resolve(strict=False))))
```

`_points_to(path, target, platform)` (`cli.py:240`), `_report_orphan_links`
(`cli.py:442-466`) and `create_directory_link`/`_remove_owned_link` keep their
existing signatures and call sites; only `_resolved`'s body changes, so every
identity comparison in the module gets the fix for free.

### `tests/test_braid.py`, `tests/test_braid_check.py` — B1 regression

A new test simulates the Windows extended-path spelling without a real
Windows host: monkeypatch `os.readlink` to return
`"\\\\?\\" + str(target)` for a path `create_directory_link` already linked,
then call `_points_to(path, target, platform="nt")` directly and assert it
returns `True`. A second case keeps a genuinely different target unequal.
Existing POSIX-path and real-symlink tests are unchanged.

### `tests/test_braid.py:414` — B2 (test-only; no `cli.py` change)

The actual assertion at line 414 is `assert agent.stat().st_mode & 0o777 == 0o640`
— it checks the **live `agent` file** (the one `sync_kiro_agent` just replaced
via `os.replace(temporary, edit.path)`, `cli.py:394`), verifying that
`shutil.copymode(edit.path, temporary)` (`cli.py:391`) carried the original
mode onto the *new* file before the replace — not the separate backup copy
`shutil.copy2` makes at `cli.py:383`, which the test already checks for byte
identity two lines later (`:417`, unrelated to mode). `shutil.copymode` on
Windows carries over only the read-only attribute, so the exact `0o777`-masked
`0o640` comparison is POSIX-only. Fix is entirely in the test, on `agent`, not
on `backup`:

```python
if os.name == "nt":
    assert agent.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY == (
        before_attrs & stat.FILE_ATTRIBUTE_READONLY)
else:
    assert stat.S_IMODE(agent.stat().st_mode) == 0o640
```

where `before_attrs = agent.stat().st_file_attributes` is captured at the same
point the test already captures `original = agent.read_bytes()` (`:405`),
before `enroll()` runs. The existing `backups = ...` / byte-identity block
(`:416-417`) is untouched — it already covers the backup correctly on both
hosts.

### `skills/create-prd/scripts/ground_prd.py` — P1, P2

`CITATION_RE` (`ground_prd.py:37-39`) today requires the path segment to be
`[\w.-]+` repeated, which excludes `:` (drive letters), `\` (Windows
separators), and a leading `\\` (UNC). A drive-qualified or backslash citation
like `C:\repo\skills\x.py:12` either fails to match at all, or (worse) a
mixed-slash citation matches but the regex's own trailing `:\d+` group
confuses the drive colon with the line-number colon.

```python
CITATION_RE = re.compile(
    r"(?<![\w./~-])"
    r"(?:[A-Za-z]:[\\/]|\\\\[\w.-]+\\[\w.-]+\\|~[\\/]|\\|/)?"   # drive, UNC, ~, or a leading separator
    r"[\w.-]+(?:[\\/][\w.-]+)*\.[A-Za-z]\w*:\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*"
)
```

`check_citations` (`ground_prd.py:91-133`)'s `path, spans = c.token.rsplit(":", 1)`
stays correct under this regex because the final `:\d+` group is still the
rightmost colon; a drive colon only ever appears at position 1, never last.
`Path(path).expanduser()` (`ground_prd.py:103`) already resolves a drive or
UNC path correctly via `pathlib`; no change needed there. The fixture that
controls "native home lookup" is the repo-root `isolate_home` fixture, already
shipped — `test_ground_prd.py`'s new cases use it instead of
`monkeypatch.setenv("HOME", ...)` alone.

`_rg_hit` (`ground_prd.py:137-146`) builds `--glob` arguments directly from
`exclude_globs`, which `resolve_symbols` (`ground_prd.py:149-161`) constructs
with `f"!{rel}"` where `rel` is a plain `Path` — on Windows `str(rel)` is
backslash-form, and ripgrep's `--glob` always expects slash form. Fix:

```python
exclude_globs += ["--glob", f"!{rel.as_posix()}"]
```

### `skills/distil-memory/scripts/docket.py` — D1, D2

D1 — `unpublished()` (`docket.py:203-220`) calls `write._readable_bytes(store / "MEMORY.md")`
guarded by `.exists()`, but the directory-ness of `store` itself is never
checked before later code treats it as a file target; on Windows, opening a
directory for read raises `PermissionError` (errno 13) rather than POSIX's
`IsADirectoryError` (errno 21), which existing error-message matching doesn't
recognize. Fix: before the store is used, explicitly classify it:

```python
if store.is_dir() and not (store / "MEMORY.md").is_file():
    raise QueueError(f"{store}: directory has no MEMORY.md to publish against")
```

D2 — `_check_entry` (`docket.py:195-200`)'s `label = repr(entry["id"]) if "id" in entry else ...`
uses `repr()`, which on a string containing a backslash doubles it
(`'a\\b'` prints as `"a\\\\b"` in the message), so the message a human or a
test reads does not show the raw id. Fix: use the id's literal text in the
diagnostic instead of `repr()`:

```python
label = f"id {entry['id']!s}" if "id" in entry else f"at position {index}"
```

(`!s`, not `!r` — the deliberate choice: the id's exact characters appear in
the message, backslashes included, matching what a Windows-spelled id
actually contains.)

### `skills/distil-memory/scripts/write.py` — D3

`_atomic_write` (`write.py:31-41`) does `tmp.write_text(data)` for the `str`
branch with no `newline=` argument, so Python's default universal-newline
write translates every `\n` to `os.linesep` (`\r\n` on Windows) before the
atomic rename. The caller's exact bytes are never what lands on disk.

```python
def _atomic_write(path: Path, data: str | bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        if isinstance(data, bytes):
            tmp.write_bytes(data)
        else:
            tmp.write_text(data, newline="")
        tmp.replace(path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
```

`newline=""` disables all translation on both read and write, which is what
every existing CRLF-preservation test already assumes was happening.

### `skills/glean/scripts/glean.py` — G1

`describe()` (`glean.py:146-165`), line 159:

```python
for hit in prescreen(f, str(f.relative_to(HOME))):
```

becomes

```python
for hit in prescreen(f, f.relative_to(HOME).as_posix()):
```

`prescreen`'s own `rel: str` parameter (`glean.py:137`) is unchanged; it only
ever threads `rel` through into the hit dict's `"file"` key, so this is the
single site that needs the conversion.

### `skills/purge-devtmp/scripts/purge_devtmp.py` — U1, U2

U1 — `path_has_unsafe_characters` (`purge_devtmp.py:137-147`) is unchanged;
it already runs ahead of any mutation. The failure is in
`test_purge_devtmp_manifest.py`'s fixture, which tries to materialize a file
whose name contains an actual tab character — Windows `CreateFile` refuses
that name outright, so the test errors before the guard is ever exercised.
Fix: construct the candidate as a `Path` object directly (never touching the
filesystem with that literal name) and feed it to `path_has_unsafe_characters`
or to a monkeypatched enumeration function that yields it, so the guard is
exercised on every host regardless of what the local filesystem will create.

U2 — `empty_old_trash` (`purge_devtmp.py:199-248`)'s manifest rewrite:

```python
manifest = trash / "manifest.tsv"
if manifest.is_file():
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    ...
    text = "".join(f"{line}\n" for line in kept_lines)
    tmp = manifest.with_name(manifest.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, manifest)
```

reads with `newline=""` (no translation, so an embedded CR inside a field
survives as a literal `\r`) but writes with `tmp.write_text(text, encoding="utf-8")`
(default `newline=None`), which translates every `\n` the read preserved back
to `os.linesep`. On Windows, a line that already carried a literal `"\r\n"`
(an untranslated CRLF read from a line this function previously rewrote with
LF-only logic, or a hand-edited manifest) gets its `\n` turned into `\r\n`
again, producing `"\r\r\n"` — the duplicated-CR defect. Fix:

```python
tmp.write_text(text, encoding="utf-8", newline="")
```

matching the read side exactly; `kept_lines` already join on an explicit
`"\n"`, so this makes the file's on-disk line ending LF-only and stable under
repeated rewrites, which is what the regression (below) proves.

### `skills/sweep-fix/scripts/test_sweep_enumerate.py`, `test_sweep_main_setup_errors.py` — S1

No production change: `sweep.py`'s resolver/enumeration code is already
host-neutral at this point (no `os.geteuid` in production). Both tests
currently do:

```python
if os.geteuid() == 0:
    pytest.skip("root can read a chmod 0o000 file")
...
registry.chmod(0o000)
try:
    ...
finally:
    registry.chmod(0o600)
```

`os.geteuid` does not exist on Windows, and `chmod(0o000)` denies nothing
there. Both tests already take `monkeypatch`; add `deny_access` (the
repo-root `conftest.py` fixture, already shipping) as a fixture parameter and
replace the block:

```python
allow = deny_access(registry)
try:
    ...
finally:
    allow()
```

`deny_access` establishes denial by the correct per-host mechanism (chmod on
POSIX, a boundary wrapper on Windows) and raises loudly if it cannot, so the
`os.geteuid() == 0` root-skip becomes unnecessary — root-as-caller is exactly
the case `deny_access` is documented to still deny (its POSIX branch is a real
`chmod`, which root bypasses; this is a pre-existing property of the fixture,
not something this PRD changes).

### `skills/use-qwen/scripts/test_eval_events.py` — Q1

`_out()` (`test_eval_events.py:84-87`):

```python
def _out(tmp_path, text=DIAGNOSTICS):
    path = tmp_path / "out.txt"
    path.write_text(text, encoding="utf-8")
    return path
```

writes with default newline translation. `test_reads_a_missing_transcript_as_unknown_however_noisy_the_capture_is`
(`:431-442`) asserts `result["final_message_bytes"] == len(capture.encode("utf-8"))`,
but `events.read_events` (`eval_harness/events.py:28`) measures the real file
size on disk (`out_path.stat().st_size` or an equivalent read), which on
Windows is larger than `len(capture.encode("utf-8"))` whenever `capture`
contains a bare `\n` that got turned into `\r\n` on write. Fix the fixture
only:

```python
def _out(tmp_path, text=DIAGNOSTICS):
    path = tmp_path / "out.txt"
    path.write_bytes(text.encode("utf-8"))
    return path
```

Writing bytes directly makes the file's on-disk size exactly
`len(text.encode("utf-8"))` on every host, matching the assertion as written.
No change to `eval_harness/events.py` — it already measures real bytes, which
is correct; the fixture was lying about what it wrote.

### `skills/use-qwen/scripts/eval_harness_fixtures.py` — Q2, Q3

Q2 — `build_fixture_repo` (`eval_harness_fixtures.py:75-104`) writes
`impl.write_text(BROKEN_IMPL, encoding="utf-8")` etc. with default newline
translation, then commits through `_git`. Git's own `core.autocrlf`/
`.gitattributes` behavior on checkout can re-translate those bytes again, so
a test that later reads the committed blob and compares it to the in-memory
constant (`BROKEN_IMPL`, `FIXED_IMPL`, `ORACLE`, `WIDENED_ORACLE`) sees a
mismatch that is really two independent translations compounding. Fix: write
every authored fixture file explicitly as bytes with a pinned line ending,
and when Git conversion specifically needs to be exercised, do so through an
explicit `.gitattributes`/`core.autocrlf` override scoped to the fixture repo
rather than relying on whatever the runner's global Git config happens to be:

```python
impl.write_bytes(BROKEN_IMPL.replace("\n", "\r\n" if change_test is ... else "\n").encode("utf-8"))
```

(exact LF/CRLF selection is a test-author decision per case — the contract is
that the fixture **never delegates line-ending choice to text-mode write**.)

Q3 — **correction after review: the `cwd_file`/`_cmd_stub_lines`/`_sh_stub_lines`
mechanism in `eval_harness_fixtures.py` (`:119-171`) is irrelevant to this
cause.** Its `cwd_file` parameter is consumed by exactly one caller in the
whole repo, `test_eval_tree_state.py` (`write_argv_recording_stub(..., cwd_file=cwd_file)`),
which is an out-of-bounds file this PRD never edits (PRD 00160/archive). None
of the four files the report names for Q3 (`test_eval_gates.py`,
`test_run_eval_cli.py`, `test_run_eval_harness.py`,
`test_run_eval_harness_outcomes.py`) call `write_argv_recording_stub` with a
`cwd_file` at all.

The real Q3 site is a `pwd -P` test-command segment compared against a
resolved native `Path`, in two shapes that both need the same fix:

- `test_eval_gates.py`'s own local helpers (`:55-61`): `_append_to(log)`
  returns the shell segment `f"pwd -P >> {shlex.quote(str(log))}"`, run as
  part of `raw_test_cmd` inside the attempt's clone; `_resolved(path)` returns
  `str(path.resolve())`. The cited assertion (`:338`)
  `assert lines == [_resolved(site.attempt_dir / "baseline-clone") for site in (first, second)]`
  compares the `pwd -P` capture (MSYS/Git-Bash form, `/c/Users/...`, when the
  segment runs under Git Bash on Windows) against the native-resolved form
  (`C:\Users\...`).
- `eval_harness_run_helpers.py`'s `_cwd_log_segment` (`:110-119`, the same
  `pwd -P` shape, captured via a small Python one-liner instead of shell
  redirection) and `_cwds`/`_logged_cwds` (`:302-314`), which `test_run_eval_cli.py:159`,
  `test_run_eval_harness.py:331`, and `test_run_eval_harness_outcomes.py:186`
  all import and compare against `str((...).resolve())` the same way.

One conversion point, added to `eval_harness_run_helpers.py` since three of
the four files already import from it:

```python
def native_cwd(raw: str) -> str:
    """`raw`, a `pwd -P` capture (native on POSIX, MSYS/Git-Bash form
    `/c/...` under Git Bash on Windows), normalised to the native form
    (`C:\\...` on Windows, unchanged on POSIX)."""
    if os.name == "nt" and len(raw) > 2 and raw[0] == "/" and raw[2] == "/":
        return f"{raw[1].upper()}:\\" + raw[3:].replace("/", "\\")
    return raw
```

**`_cwds` alone is not enough — `_logged_cwds`'s own prefix filter runs
first and on the unconverted line.** `_logged_cwds` (`:307-314`) filters
`log`'s raw lines with `prefix = str(round_.run.resolve()) + os.sep` (native
form) via `line.startswith(prefix)` *before* handing the survivors to
`_cwds`; under Git Bash on Windows every genuine line is still in MSYS form
at that point, so none start with the native prefix and the filter discards
them all — `_cwds`'s `native_cwd()` call never sees a line to convert. The
fix has to reach the filter itself, not just `_cwds`:

```python
def _logged_cwds(round_, log: Path) -> list:
    prefix = str(round_.run.resolve()) + os.sep
    msys_prefix = _to_msys(prefix) if os.name == "nt" else None
    lines = [
        line for line in log.read_text(encoding="utf-8").splitlines()
        if line.startswith(prefix) or (msys_prefix and line.startswith(msys_prefix))
    ]
    assert len(lines) == len(set(lines)), "two runs of the test command share a stamp"
    return _cwds(lines)
```

`_to_msys` is `native_cwd`'s inverse (`C:\a\b` → `/c/a/b`), added alongside
it in `eval_harness_run_helpers.py` for exactly this filter; `_cwds` keeps
calling `native_cwd()` on each surviving line so its return value is
native-form either way. `test_eval_gates.py` has no such prefix filter (its
`:338` comparison reads every line in `log` directly) — its own `_resolved`
(`:60-61`) imports `native_cwd` from `eval_harness_run_helpers` and applies it
to each line before the comparison, as already described above.

### `skills/use-qwen/scripts/eval_harness/report.py`, `test_report.py` — Q7

No production change. `_attempt_block` (`report.py:238-282`) already builds
`out_path = attempt_dir / _OUT_FILE` (a real `Path` join) and prints
`"%s"%(out_path)`, which is native-separator-correct by construction.
`test_captured_output_line_reports_real_byte_sizes_for_out_and_wrapper`
(`test_report.py:490-504`) builds its expected string by hand:

```python
expected = "Captured output: %s/out.txt (%d bytes), %s/wrapper.txt (%d bytes)" % (
    attempt_dir, out_size, attempt_dir, wrapper_size,
)
```

concatenating a literal `/out.txt` onto `attempt_dir` (whose `str()` is
backslash-form on Windows), producing a mixed-separator string that never
equals what production printed. Fix:

```python
expected = "Captured output: %s (%d bytes), %s (%d bytes)" % (
    attempt_dir / "out.txt", out_size, attempt_dir / "wrapper.txt", wrapper_size,
)
```

Same fix shape in `test_captured_output_line_reports_wrapper_unavailable_when_the_file_is_absent`
(`:507-521`): replace `"%s/wrapper.txt (unavailable bytes)" % attempt_dir`
with `"%s (unavailable bytes)" % (attempt_dir / "wrapper.txt")`.

### `skills/use-qwen/scripts/eval_harness/vetting.py`, `test_run_eval_vet.py` — Q8 (conditional)

`run_checks`'s `measure` closure (`vetting.py:25-39`) derives each warmup
segment's remaining budget as `left = bound_s - (time.monotonic() - started)`
(`vetting.py:42-46`), which is correct bookkeeping *if* the elapsed wall time
the closure measures already includes every cost the segment pays —
including process/clone startup. The report's hypothesis is that Windows
process startup (clone creation, `trees.fresh_clone`, subprocess spawn) is
slow enough that the real test (`test_the_warmup_budget_runs_down_across_every_earlier_segment`,
`test_run_eval_vet.py:367-383`, a real 2-segment-then-timeout scenario) expires
during segment two's *setup* rather than its *execution*, which would make the
accounting look broken when the budget itself is being spent correctly on
real overhead. **No change to `vetting.py` unless the native Windows run
demonstrates the deadline arithmetic itself (not process-startup cost) is
wrong.**

Add a new, host-independent regression that isolates the arithmetic from real
process cost:

```python
def test_cumulative_deadline_is_measured_against_the_run_start_not_the_segment_start(monkeypatch):
    """A deterministic clock seam: each warmup call advances a fake clock by a
    known amount: the deadline `measure` computes for segment N must equal
    bound_s minus the sum of every earlier segment's advance, not bound_s
    minus only the immediately preceding segment."""
    ...
```

implemented by monkeypatching `time.monotonic` with a counter the test
controls, and a `runner.run_segments`/`trees.fresh_clone` stub that returns
immediately — so the test asserts the `deadline_s` value `measure` computes
for each call, not real wall-clock behavior. This keeps
`test_the_warmup_budget_runs_down_across_every_earlier_segment` as the real
bounded-process check (unchanged), and adds the seam that can actually prove
or disprove the hypothesis without a hosted run.

## Data flow

**Braid identity path.** `discover_inventory` → `create_directory_link`
(symlink or junction) → on a later `check`/`sync` call, `_points_to` re-reads
the link (`os.readlink`) or, on Windows, the directory's own identity, resolves
both sides through `_resolved` (now prefix-normalising), and compares. A
single normalisation point means every caller (`_report_orphan_links`,
`_remove_owned_link`, the main `_sync_links` loop) gets consistent identity
for free.

**Memory store path (D-series).** `funnel.run` (unaffected; PRD 00133's
boundary) produces proposals → `write.write_proposals` stages then publishes
(unaffected by this PRD) → `docket.unpublished` cross-checks the published
store against the kept-decision queue, now classifying a directory-shaped
store input explicitly (D1) and rendering a malformed id's exact characters
(D2) → `write._atomic_write` is the single choke point for every byte written
to the store or the queue file (D3).

**Small-skill reporting path (G1, U1, U2, S1).** Each skill's own CLI builds a
report or manifest row from a `Path`; G1 and U2 are "the representation a
report prints" bugs with no behavior change; U1 and S1 are "the test's own
fixture construction doesn't reach the already-correct guard on this host"
bugs, fixed entirely in the test.

**Qwen fixture path (Q1-Q3, Q7).** A test asks `eval_harness_fixtures.py` for
a capability (a git fixture repo, an argv-recording stub, a captured cwd); the
fixture decides how to represent bytes/paths so the captured artifact is
byte-and-form-identical to what the production harness (`eval_harness/events.py`,
`report.py`) will measure or print. No test branches on the platform inside
the *assertion* — only inside the fixture that produces the input.

## Reuse inventory

Greps run (`rg --type py` over `src/`, `skills/`, `tests/`):
`os\.readlink|_resolved|_points_to` (found the one choke point for B1);
`chmod\(0|shutil\.copy2` (confirmed B2 is test-only); `rsplit\(":"|CITATION_RE`
(found P1's regex and its colon-split, confirmed no double-use conflict);
`--glob|as_posix` (found P2's missing conversion and G1's missing one, by the
same grep); `repr\(.*id.*\)|os\.strerror|IsADirectoryError` (found D1/D2);
`write_text\(|newline=` (found D3 and U2 together — both are the same class of
bug, "text-mode write without `newline=\"\"`"); `os\.geteuid` (found exactly
the two S1 sites named in the report, confirmed no third site exists:
`rg -n "os\.geteuid" skills/` returns only those two lines); `f"{.*}/.*"|%s/.*%` in
`test_*.py` (found Q7's hand-built string).

**Reused, no new code:**

- `conftest.py` (repo root) `deny_access`, `isolate_home`, `write_executable_stub`,
  `run_resolved_tool` — all four fixtures from the already-shipped greenfield
  work are reused as-is. S1 is a direct `deny_access` consumer; P1's test
  additions reuse `isolate_home`.
- `PureWindowsPath`/`PurePosixPath`/`as_posix()` — stdlib covers every
  path-form conversion needed here (G1, P2); no helper module added.
- `_resolved()` in `cli.py` is the existing single choke point for identity
  comparison; B1 extends it rather than touching each of its five call sites.

**Nothing found, greps tried:** a shared newline-safety helper across skills
(`rg -l "newline=" skills/` returns scattered individual call sites, no
shared module — D3 and U2 each get their own one-line fix rather than a new
shared utility, since the sites are two lines total and a new module would be
the kind of premature abstraction this closeout should avoid); any existing
Windows-cwd-normalisation helper for the qwen harness (`rg -n "MSYS|pwd -P"
skills/use-qwen` finds only the fixture's own stub-generation code) — Q3's
`native_cwd()` is genuinely new.

## Alternatives considered

**A. Fix B1 by hand-spelling the `\\?\` strip at each of the five call sites
instead of inside `_resolved()`.** Rejected: `_resolved()` is already the
single function every comparison goes through; duplicating the strip five
times is the same mistake the PRD's own fixture design (conftest.py) was built
to avoid for test code, applied to production code this time.

**B. Fix Q1/Q2 in production (`events.py`, fixture authoring) by having
`eval_harness/events.py` normalise `\r\n` to `\n` before counting bytes,
instead of fixing the test fixtures.** Rejected: the PRD and the prep report
are explicit that production changes land "only if demonstrated" — Q1 is
fully explained by a lying test fixture (`_out` claims to write `text` but
performs translation), so normalising in production would hide a reporting
discrepancy that is real (translated bytes on disk reported as translated
bytes) rather than fix anything broken.

**C. Chosen: minimal, owner-scoped repairs per cause row, test-only where
the prep report's own diagnosis already proves "fixture lies to itself" and
production-plus-test where it proves a real portability gap (B1, P1, P2, D1-D3,
G1, U2).** This keeps every repair inside the file(s) the implementation
ownership packet assigns, with no shared-module refactor and no behavior
change to any already-correct code path.

## Risks & edge cases

- **Q8 is explicitly conditional.** The deterministic-seam regression (new)
  ships unconditionally; the `vetting.py` production edit ships only if a
  native Windows run demonstrates the deadline arithmetic itself is wrong,
  not process-startup cost. A task that "fixes" Q8 without that evidence is
  out of scope.
- **B1's fix is a string-prefix strip, not a semantic path resolution.** If a
  future Windows path form introduces a different extended-prefix spelling
  (e.g. a long-UNC variant this PRD didn't see in the report), `_strip_extended_prefix`
  needs a new branch; it does not fail closed, it falls through unchanged.
- **S1's fix changes test fixtures, not sweep-fix's production resolver.**
  Nothing here revisits whether sweep-fix itself needs Windows-specific
  resolver logic; that is out of this PRD's scope per the prep report (S1 is
  "a denied-read fixture reaches an already-correct code path").
- **Q2/Q3 depend on this branch's actual `.gitattributes` / Git config at CI
  time**, which this PRD does not change — only the fixture's own authored
  bytes and the comparison helper are touched. If the CI runner's global
  `core.autocrlf` setting changes independently, Q2's fix could need
  revisiting; the design deliberately avoids depending on that setting by
  writing bytes explicitly rather than trusting Git to not re-translate.
- **These are the closeout's last changes before a native Windows run.** Every
  task's acceptance criterion is a local `uv run pytest <files>` pass; the
  PRD's Phase 2 is explicit that native Windows evidence is a separate,
  coordinator-owned step this design does not perform.

## Test strategy outline

- **B1/B2**: a monkeypatched-readlink regression proving extended-prefix
  identity; a host-appropriate mode/backup-byte assertion. No whole-test skip.
- **P1/P2**: drive, UNC, and mixed-slash citation parsing; a backslash-spelled
  exclusion path proving the glob still excludes it. Existing absolute/missing
  citation behavior unchanged.
- **D1/D2/D3**: directory-as-store-path refusal naming the path; a
  backslash/newline-bearing id surviving in the diagnostic message verbatim;
  CRLF byte-identity across write/rollback/retry, matching the existing
  atomicity and crash-safety test shapes exactly.
- **G1**: a nested-file report id compares equal to its slash-form expectation
  on both hosts.
- **U1/U2**: the unsafe-character guard fires before any mutation, exercised
  without requiring the OS to create the hazardous name; a CRLF manifest row
  survives two rewrites with no byte growth.
- **S1**: the existing refusal-exit-code assertions pass unchanged, now backed
  by `deny_access` instead of `chmod`/`geteuid`.
- **Q1/Q2/Q3**: byte-count assertions hold on both hosts because the fixture
  now writes exactly what it claims to; cwd comparisons go through one
  canonical-form conversion.
- **Q7**: the captured-output line's expected string is Path-joined, matching
  production's own construction, on both hosts.
- **Q8**: a new deterministic-clock-seam test proves the deadline arithmetic
  independent of real process cost; the existing real-timeout test is
  retained unchanged.
- **Regression discipline**: every new test fails against the pre-fix code
  (verified by running it before applying each file's edit) and passes after.

## Review log

Recorded, not fixed:

- non-blocker: D1's stated bug mechanism doesn't line up with the code it
  cites. `write._readable_bytes` (`write.py:44-58`) already catches `OSError`
  (which `PermissionError` subclasses) and re-raises as `WriteError` naming
  the path on every platform; nothing in the cited path does POSIX-specific
  error-message matching that would fail to recognize a Windows
  `PermissionError`. D1's real gap is more likely "no regression test yet
  pins a directory-shaped `MEMORY.md`, and any such test must not hardcode
  errno/message text" rather than "existing matching doesn't recognize it."
- question: D1's fix placement relative to the existing
  `(store / "MEMORY.md").exists()` + `_readable_bytes` call
  (`docket.py:213-214`) is unstated — does the new directory check replace
  that block or run ahead of it? If both run, the `exists()`-gated call
  becomes dead code for the directory case (harmless but redundant).

dispatch 1 (claude): cardinal-sin 0, blocker 0, non-blocker 2, question 1

dispatch 2: codex unavailable, Claude fallback

Blockers fixed in the doc: B2's proposed fix compared the wrong file —
`backup.stat()` (the `shutil.copy2` copy, already covered by the existing
byte-identity assertion two lines later) instead of `agent.stat()` (the live
file `os.replace` just installed, which is what the cited assertion at
`test_braid.py:414` actually checks, and what `shutil.copymode` carries the
mode onto). Second: Q3's entire proposed fix targeted
`eval_harness_fixtures.py`'s `cwd_file`/stub mechanism, whose only consumer
in the repo is an out-of-bounds file (`test_eval_tree_state.py`, PRD
00160/archive); none of the four files the prep report names for Q3 use that
mechanism. The real site is the `pwd -P`-vs-`Path.resolve()` mismatch in
`test_eval_gates.py`'s local `_append_to`/`_resolved` pair and in
`eval_harness_run_helpers.py`'s `_cwd_log_segment`/`_cwds`/`_logged_cwds`,
which three of the four files import.

Recorded, not fixed:

- non-blocker: B1's Module placement / Interfaces sections name only three of
  `_resolved()`'s call sites (`_points_to`, `_report_orphan_links`,
  `create_directory_link`/`_remove_owned_link`); six more exist
  (`_skills_directory`, `discover_inventory`'s dedup, `select_kiro`'s root
  comparison, `prepare_kiro_agents`' glob-equivalence set, and two more in
  settings normalisation). None break under the added prefix strip — it's a
  no-op on any path without the prefix — but the design's "gets the fix for
  free" claim would be easier to verify with the complete list.
- question: P1's "no change needed" claim for `Path(path).expanduser()`
  (`ground_prd.py:103`) assumes Windows path semantics. A `check_citations`
  end-to-end regression for a drive/UNC citation, run on a non-Windows dev
  box where `Path` is `PosixPath`, would flake by host rather than fail
  cleanly; the design should state that such end-to-end cases are
  Windows-only (or regex-level-only via `extract_claims`, which is host-safe).
- question: Q2's illustrative code (`BROKEN_IMPL.replace("\n", "\r\n" if
  change_test is ... else "\n")`) is a placeholder, not a real rule; the
  design concedes "exact LF/CRLF selection is a test-author decision per
  case" without naming what decides it.

dispatch 2 (claude-fallback): cardinal-sin 0, blocker 2, non-blocker 1, question 2

dispatch 3: codex unavailable, Claude fallback

Verification pass, required because dispatch 2 found blockers. Codex was
already established as out at dispatch 2 (sandbox denied both its file-reading
runtimes), so the outage rule applied again rather than burning a second
silent run.

Verdicts on dispatch 2's blockers: **B2 FIXED** — confirmed the proposed fix
now asserts on `agent.stat()` (the file `os.replace` just installed, the one
`test_braid.py:414`'s existing assertion actually checks), not `backup.stat()`;
`before_attrs` is captured at the same point the test already captures
`original = agent.read_bytes()` (`:405`). **Q3 PARTIALLY FIXED** — the
`test_eval_gates.py` site is correct (no intervening filter between the raw
`pwd -P` lines and the `:338` comparison), but the first fix missed that
`_logged_cwds`'s own `startswith(prefix)` filter (`eval_harness_run_helpers.py:307-314`)
runs on the raw MSYS-form line against a native-form `prefix` *before*
`_cwds()` gets a chance to call `native_cwd()` — on Windows every genuine
line fails that filter and `_cwds()` never sees one to convert, so the three
files that import `_logged_cwds` (`test_run_eval_cli.py`,
`test_run_eval_harness.py`, `test_run_eval_harness_outcomes.py`) were still
broken. Fixed in the doc: the filter itself now also matches the MSYS-form
prefix via a new `_to_msys()` inverse helper, before handing survivors to
`_cwds()`.

No new cardinal sins or blockers introduced by either fix.

dispatch 3 (claude-fallback): cardinal-sin 0, blocker 0, non-blocker 0, question 0

result: ok

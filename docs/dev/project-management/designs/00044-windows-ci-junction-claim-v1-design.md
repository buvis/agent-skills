# Design: 00044 — Run the entire Python suite on Windows

PRD: `dev/local/prds/wip/00044-windows-ci-junction-claim-v1.md`

## Architecture fit

Five surfaces, in the PRD's own module order:

1. **Runner** — `.github/workflows/ci.yml`, `.gitattributes` (new), `pyproject.toml`.
   The workflow already has four jobs (`test`, `shell`, `lint`, `node`). A fifth,
   `windows`, joins them as a peer. No matrix is added to `test`: the Windows job
   needs a different toolchain-provisioning block, and folding it into the
   existing matrix would force `if: runner.os == ...` on every step.
2. **Fixture portability** — a NEW repo-root `conftest.py` supplying four
   host-branching fixtures, plus the call-site swaps in the seven test files that
   currently encode POSIX assumptions. The repo has exactly one conftest today
   (`skills/sweep-fix/scripts/conftest.py`, resolver-cache clearing) and no shared
   test-helper module that skill tests can import: each skill ships its own
   `*_test_helpers.py`, and `skills/*/scripts/` are added to `sys.path` by pytest
   one directory at a time. A rootdir `conftest.py` is the only mechanism that
   reaches every collected test with no import plumbing, because pytest injects
   conftest fixtures by name down the whole tree below rootdir.
3. **Brush protection** — `skills/brush/scripts/trash_untracked.py` and
   `test_brush_scripts.py`. Real product defect.
4. **Proposal publication** — `skills/distil-memory/scripts/proposal.py` and its
   two publication test files. Real product defect.
5. **Windows documentation** — `README.md` only.

Layering per the PRD's dependency graph: Runner and Fixture portability are
Phase 0 and independent of each other; Brush and Publication are Phase 1 and
depend on Phase 0 only for the ability to observe their failures on Windows;
Documentation is Phase 2 and depends on a real green run.

## Module placement

| Path | New/Edit | What lands |
|---|---|---|
| `.github/workflows/ci.yml` | edit | `jobs.windows` on `windows-latest`; existing four jobs untouched |
| `.gitattributes` | **new** | `*.sh text eol=lf` (and `*.bash`), so Git Bash-run fixtures keep LF on a CRLF checkout |
| `pyproject.toml` | edit | `testpaths = ["tests", "skills", "scripts"]` |
| `conftest.py` (repo root) | **new** | the four portability fixtures below |
| `skills/sweep-fix/scripts/test_sweep_resolvers.py` | edit | stub creation, PATH roots, HOME isolation, resolved-tool invocation |
| `skills/sweep-fix/scripts/test_sweep_scan.py` | edit | hung-search fixture |
| `skills/explain-interactively/scripts/test_build.py` | edit | Git Bash path form |
| `skills/review-prd-backlog/scripts/test_check_links.py` | edit | denied read |
| `skills/distil-memory/scripts/test_dedup.py`, `test_dedup_classify.py`, `test_docket_refusals.py`, `test_write_refusals.py` | edit | denied read/write; **delete the three module-scope `os.geteuid()` guards**; host-correct backslash decoy |
| `skills/brush/scripts/trash_untracked.py` | edit | slash-form path identity |
| `skills/brush/scripts/test_brush_scripts.py` | edit | add host-correct separator + positive-control regressions |
| `skills/distil-memory/scripts/proposal.py` | edit | portable publication step in `write_proposals` |
| `skills/distil-memory/scripts/test_proposal_publication.py`, `test_funnel_distil_publication.py` | edit | ownership assertions replacing POSIX-only reservation mechanics; `_proposals_paths_named`'s token filter |
| `skills/distil-memory/scripts/test_funnel_main.py` | edit | native-form expectation for the printed report path |
| `skills/survey/scripts/test_survey.py` | edit | native-form expectation in three `<dir>/<file>:<line>` assertions (lines 900-901 parametrized ×2, 942-943) |
| `README.md` | edit | single-backslash command, coverage paragraph |
| `CHANGELOG.md` | edit | `fix`/`feat` entries (standing repo rule) |

`tests/test_braid.py` is **validation surface only**: `_link_dir` already takes an
injected `platform: str = os.name`, so the junction-fallback test
(`test_windows_symlink_privilege_failure_falls_back_to_junction`, line 171) is
already host-independent and must not be touched.

## Interfaces & contracts

### `conftest.py` (repo root) — new

```python
"""Host-portability fixtures for the whole suite.

Lives at the repository root so pytest injects it into every collected test
under `testpaths`, including each `skills/*/scripts/` tree, without any
sys.path or import plumbing.
"""

IS_WINDOWS: bool = os.name == "nt"
```

Four fixtures, each yielding a callable. Signatures are exact:

```python
@pytest.fixture
def write_executable_stub(): ...
    # returns: Callable[[Path, str, str], Path]
    # call as: write_executable_stub(directory, name, body) -> Path
    #   `body` is the shell-agnostic thing the stub must print, e.g. "fake-rg".
    #   POSIX: writes `<directory>/<name>` containing "#!/bin/sh\necho <body>\n",
    #          chmod 0o755.
    #   Windows: writes `<directory>/<name>.cmd` containing
    #          "@echo off\r\necho <body>\r\n".
    #   BOTH: returns `Path(shutil.which(name, path=str(directory)))`, and
    #   raises AssertionError naming `directory` and `name` when that is None.
    # CONTRACT: the returned path is byte-equal to what the resolver's own
    # `shutil.which(name)` will return once `directory` is on PATH - derived
    # from `which`, never hand-spelled. Hand-spelling is wrong on Windows:
    # `shutil.which` appends the extension verbatim from %PATHEXT%, which is
    # uppercase by default (".COM;.EXE;.BAT;.CMD;..."), so the resolver returns
    # `<directory>\rg.CMD` while the fixture wrote `rg.cmd`, and NTFS
    # case-insensitivity hides the mismatch until the `==` assertion fails.
```

```python
@pytest.fixture
def isolate_home(monkeypatch): ...
    # returns: Callable[[Path], None]
    # call as: isolate_home(tmp_path)
    #   POSIX: monkeypatch.setenv("HOME", str(path))
    #   Windows: sets USERPROFILE, HOMEDRIVE, HOMEPATH; HOME too, harmlessly.
    # WHY: ntpath.expanduser ignores HOME entirely (it reads USERPROFILE, then
    # HOMEDRIVE+HOMEPATH), so `monkeypatch.setenv("HOME", ...)` is a silent
    # no-op on Windows and `Path.home()` / `os.path.expanduser("~")` still
    # point at the real profile.
```

```python
@pytest.fixture
def deny_access(monkeypatch): ...
    # returns: Callable[[Path], Callable[[], None]]
    # call as: allow = deny_access(path)   # file or directory
    #          ...                          # the denial is in force
    #          allow()                      # lifted, same test, same body
    #   POSIX: path.chmod(0o000); `allow()` restores 0o644 for a file, 0o755
    #          for a directory. A teardown finalizer restores unconditionally
    #          so tmp_path cleanup can still unlink the tree.
    #   Windows: chmod cannot deny a read, so denial is applied at the
    #          filesystem boundary instead. `path` and everything under it goes
    #          into a denied set; `allow()` removes it. FOUR call vectors are
    #          wrapped, each delegating to the captured real function for any
    #          path outside the set:
    #            io.open        - the one `pathlib.Path.open` and therefore
    #                             `Path.read_text` / `Path.read_bytes` /
    #                             `Path.write_text` resolve at call time
    #            builtins.open  - plain `open(...)` call sites; a SEPARATE
    #                             binding, so patching one does not patch the
    #                             other (test_proposal_publication.py's
    #                             `_patch_write_vectors` already treats them as
    #                             two vectors, for exactly this reason)
    #            os.listdir     - directory listing on 3.10
    #            os.scandir     - directory listing on 3.13, and `os.walk`
    #            os.stat        - and os.lstat: WITHOUT these, denying a
    #                             DIRECTORY does not deny `Path.is_file()` on a
    #                             child, and write.py:172-175's probe-refusal
    #                             branch is never entered on Windows. Deny stat
    #                             for paths strictly INSIDE a denied directory
    #                             and leave stat on the denied path itself
    #                             intact, so `p.exists()` stays True.
    #          `os.mkdir` is wrapped too, so denying a directory also denies
    #          creating anything inside it. Both listdir and scandir are wrapped
    #          because which one `Path.iterdir` uses changed in 3.13 and both
    #          3.10 and 3.13 are in the matrix.
    # SELF-CHECK the fixture performs on Windows after arming a directory:
    # `(denied_dir / "child").is_file()` must raise, or the fixture fails loudly
    # rather than letting a test go green on the wrong branch.
    # CONTRACT: after `allow = deny_access(p)`, reads of p raise PermissionError
    # while `p.exists()` stays True - the "unreadable, not missing" distinction
    # the affected tests assert - and after `allow()` the same read succeeds and
    # returns the original bytes. Both halves hold on both hosts, so tests like
    # test_write_refusals.py's byte-identity check (deny -> act -> lift -> read
    # back) keep their bodies unchanged.
    # ROOT: this fixture replaces the three module-scope
    # `@pytest.mark.skipif(os.geteuid() == 0, ...)` guards (see Module
    # placement); when denial cannot be established on this host it says so at
    # call time instead of at import time.
```

```python
@pytest.fixture
def run_resolved_tool(): ...
    # returns: Callable[[str, list[str]], subprocess.CompletedProcess]
    # call as: run_resolved_tool(resolved_path, ["rg", "--version"])
    #   POSIX: subprocess.run(argv, executable=resolved_path,
    #                         capture_output=True, text=True)
    #   Windows: subprocess.run([resolved_path, *argv[1:]],
    #                         capture_output=True, text=True)
    # WHY the branch: `executable=` sets lpApplicationName, and CreateProcess
    # refuses a .cmd/.bat there ("%1 is not a valid Win32 application").
    # Windows has no argv[0]-based dispatch to test in the first place; the
    # argv[0]+executable= call SHAPE stays pinned portably by the AST test
    # test_run_rg_never_invokes_a_bare_rg_binary_by_name. This fixture keeps
    # the *executability* assertion real on both hosts.
```

### Fifth portability decision: a path asserted against printed output

No fixture; a **rule**, because it is applied inside assertions rather than
around them. Several tests assert a slash-containing path string against text a
product module produced by interpolating a `Path`. On Windows the product prints
`dev\local\audit-results` and the assertion looks for `dev/local/audit-results`.

**Rule: normalise the EXPECTATION to the host's native form; never rewrite the
actual output.** This is the PRD's "compare platform-native diagnostics" branch,
and it is the safe half: a genuinely wrong path still fails the assertion,
whereas normalising the actual output could launder a real defect.

**The discriminator is whether the PRODUCT interpolated a `Path`.** A hardcoded
slash literal in the product prints identically on both hosts and must NOT be
converted - doing so breaks it on Windows only. See the verified-safe list below.

Confirmed sites, five across two skills:

- `skills/distil-memory/scripts/test_funnel_main.py:379` —
  `assert "dev/local/audit-results" in captured.err` against `funnel.py:483`'s
  `print(f"failed to write report to {report_dir}: ...")`. Becomes
  `assert str(Path("dev/local/audit-results")) in captured.err`
  (`str(PureWindowsPath("dev/local/audit-results"))` is `dev\local\audit-results`,
  a substring of the absolute `report_dir`).
- `skills/distil-memory/scripts/test_funnel_distil_publication.py:50` —
  `_proposals_paths_named` keeps only tokens where `"/" in token`, so on Windows
  it finds ZERO path tokens and `_named_proposals_directory`'s
  `assert len(named) == 1` (line 64) fails in three tests. The token filter
  becomes `os.sep in token`, byte-identical to today on POSIX (`os.sep == "/"`)
  and correct on Windows. The file imports no `os` today; the edit is not one
  character.
- `skills/survey/scripts/test_survey.py:900-901` — `full_path_ref =
  f"{subdir}/{filename}:{class_line}"` then `assert full_path_ref in section`,
  against `run.py:380`'s `rel_path = str(f.relative_to(repo_path))` rendered at
  `run.py:311,325`. Parametrized over `ports/payment` and `adapters/email`, so
  TWO failures. Becomes `f"{Path(subdir) / filename}:{class_line}"`.
- `skills/survey/scripts/test_survey.py:942-943` — the same shape for
  `core/domain/aggregate_root.py`. Neither test carries
  `@requires_tree_sitter`, so the regex fallback keeps both running on Windows.

**Verified safe, do NOT convert:** `test_funnel_report.py:128`
(`assert "dev/local/audit-results/" in last_line`) and `test_funnel_report.py:243-263`
(a second, independent copy of the `"/" in token` filter). Both assert against
`funnel.py:257-258`, which is a hardcoded slash literal with no `Path`
interpolation and no `"proposal"` token. Converting either introduces a
Windows-only failure.

`funnel.py` and `run.py` themselves are NOT edited: changing what a report prints
is a third product surface and is outside this PRD. Only the assertions move.

### Two collection-time hazards the fixtures do not reach

**`os.geteuid()` at module scope aborts Windows collection.** Three decorators
evaluate it at import time and `os.geteuid` does not exist on Windows:
`test_write_refusals.py:134`, `test_write_refusals.py:183`,
`test_docket_refusals.py:351`. Importing either module raises
`AttributeError: module 'os' has no attribute 'geteuid'`, which is a collection
ERROR: `uv run --python 3.13 pytest` exits non-zero before running a test in
those files, and ~30 tests silently leave the Windows collection. **Delete all
three decorators.** Do not translate them into
`os.name != "nt" and os.geteuid() == 0` - that is a new platform skip, which the
PRD forbids. The root case they guard is now `deny_access`'s job: it establishes
denial by a mechanism that works for root too (the boundary wrapper), so there is
no host on which the refusal disappears.

**A literal `..\outside\secret.md` filename cannot exist on Windows.**
`test_dedup_classify.py:367` (`test_read_candidates_skips_a_name_carrying_a_
windows_style_separator`) writes `memory_dir / "..\\outside\\secret.md"`. On
POSIX that is one filename with backslashes in it, sitting inside the plane -
the decoy that a slash-only separator check would wrongly let through. On
Windows the same expression is a traversal: it resolves to
`<tmp_path>/outside/secret.md`, `write_text` raises FileNotFoundError, and the
test errors. Creating the parent directory "to fix it" is worse: the decoy then
sits OUTSIDE the plane, `assert candidates == [("mullion-01", ...)]` passes with
nothing to reject, and the rejection check is silently gutted.
**Rule: the decoy must be planted, on every host, at a real readable file INSIDE
`memory_dir` whose name a backslash-blind reader would accept**, and the fixture
asserts that placement before calling `read_candidates`, so a host where the
spelling is a traversal fails loudly instead of testing nothing. The invariant is
**containment, not parenthood** — `planted.is_file()` and
`planted.resolve().is_relative_to(memory_dir.resolve())` — because the POSIX
decoy is a single filename directly in the plane while the Windows one is nested;
`planted.parent == memory_dir` would fire on every Windows run, on the host the
rule exists for. On Windows the name is spelled with the
separator that is ordinary there for the same purpose (a nested
`outside/secret.md` created inside the plane, addressed as
`"outside\\secret"`); the assertion, not the spelling, is what keeps the
positive control honest.

### `skills/brush/scripts/trash_untracked.py`

One new module-level function, one changed call site, two changed returns:

```python
def as_git_rel(root: Path, path: Path) -> str:
    """`path` relative to `root` in Git's slash-form representation.

    On Windows a native separator becomes "/", matching `git ls-files` and the
    "docs/", "dev/local/", ".git/" prefixes. On POSIX the components are
    returned untouched, so a backslash that is an ordinary filename character
    stays one.
    """
    return path.relative_to(root).as_posix()


def normalise_rel(rel: str) -> str:
    """`rel` collapsed to slash form with "." and ".." segments resolved."""
    text = rel.replace("\\", "/") if os.name == "nt" else rel
    return posixpath.normpath(text)
```

- `veto_reason(...)` line 54: `rel = os.path.normpath(rel)` → `rel = normalise_rel(rel)`.
  `os.path.normpath` on Windows rewrites "/" to "\\", which is what makes every
  `PROTECT_PREFIXES` check ("docs/", "dev/local/", ".git/") and every `tracked`
  set-membership test fail there. The dotdot-collapsing behaviour it provided is
  preserved by `posixpath.normpath`, and the two dotdot regressions
  (`test_veto_devlocal_protected_through_a_dotdot_segment`,
  `test_main_refuses_a_protected_path_spelled_through_dotdot`) keep passing.
- `veto_reason(...)` line 61: `Path(rel).suffix` → `PurePosixPath(rel).suffix`,
  and line 63 `Path(rel).name` → `PurePosixPath(rel).name`, so a slash-form `rel`
  is parsed as slash-form on every host.
- `main()` line 102: `raw.strip("/")` → `raw.strip("/\\" if os.name == "nt" else "/")`.
- `main()` line 97: `root = repo_root(Path(args.repo).resolve()).resolve()`.
  `p` is already `.resolve()`d at line 103 while `root` is not; on Windows the
  two can differ by 8.3 short name (`C:\Users\RUNNER~1` vs the long form) and
  `p.is_relative_to(root)` then refuses every legal path.
- `main()` line 107: `rel = os.path.relpath(p, root)` → `rel = as_git_rel(root, p)`.
- `relocate(...)` line 78: `return str(dest.relative_to(root))` →
  `return dest.relative_to(root).as_posix()`.

Unchanged and load-bearing: the escape refusal (`is_relative_to` → `"outside repo"`),
`PROTECT_SUFFIXES`/`PROTECT_PREFIXES`/`PROTECT_GLOBS` contents, `--min-age-days`,
the `{"moved": [...], "refused": [...]}` JSON shape, and the four-column
`date\trule\trel\ttrash_rel` manifest row. The deletion scope does not change.

### `skills/distil-memory/scripts/proposal.py`

`write_proposals(proposals, discards, out_dir) -> Path` keeps its signature,
its docstring guarantees and its output bytes. Only the publication step changes:

```python
    out_dir.mkdir(parents=True)          # UNCHANGED: atomic reservation, EEXIST
    staging = out_dir.parent / f"{out_dir.name}.partial-{os.getpid()}"
    try:
        staging.mkdir()
    except OSError:
        out_dir.rmdir()
        raise

    reserved = True                      # NEW: do we still own out_dir?
    try:
        records = _write_proposal_files(proposals, staging)
        (staging / "proposals.json").write_text(...)   # unchanged
        (staging / "discards.json").write_text(...)    # unchanged
        if os.name == "nt":
            # MoveFileEx(REPLACE_EXISTING) does not accept a directory
            # destination, so os.replace onto the reservation fails on Windows.
            # Release the reservation, then rename: a competitor that claims the
            # name in between makes THIS rename fail, which is the correct
            # outcome - one winner, and the loser touches nothing it lost.
            out_dir.rmdir()
            reserved = False
            os.rename(staging, out_dir)
        else:
            os.replace(staging, out_dir)
            reserved = False
    except Exception:
        shutil.rmtree(staging)
        if reserved:
            out_dir.rmdir()
        raise

    return out_dir
```

Guarantees this preserves, each already pinned by a test:

| Guarantee | Mechanism after the change |
|---|---|
| pre-existing empty OR non-empty destination is refused, `errno == EEXIST`, raised by the syscall (not a `.exists()` probe) | untouched `out_dir.mkdir(parents=True)` |
| exclusive reservation between competing writers | same mkdir; a second writer never reaches staging |
| a reader never sees a half-filled `out_dir` | files are only ever written under `staging`; `out_dir` gains content in one rename |
| failure leaves no directory and no staged sibling | the `except` branch, now ownership-aware |
| **a failed writer must not remove another writer's directory** | `reserved` is cleared before the Windows rename can fail, so the loser never rmdirs a name it no longer owns |
| output bytes and JSON schema | `_write_proposal_files` and both `json.dumps(..., indent=2)` calls untouched |

### `.github/workflows/ci.yml` — `jobs.windows`

```yaml
  windows:
    runs-on: windows-latest
    env:
      PYTHONUTF8: "1"
    steps:
      - uses: actions/checkout@v7          # same version as the other jobs
      - uses: astral-sh/setup-uv@v10.0.1   # same version as the other jobs
      - name: Install the sweep-fix tool chain   # mise, native Windows build
      - name: Verify runner capabilities         # named diagnostics, exit 1
      - name: Run the suite
        run: uv run --python 3.13 pytest         # unfiltered, no -k, no --deselect
```

The toolchain step must reproduce the Linux job's two OPPOSITE placement rules,
which are each pinned by a test:

- **`rg` ON PATH, and not a mise shim**: copy `mise which rg` to a directory
  added to `GITHUB_PATH` (the Linux job symlinks; Windows copies).
- **`ast-grep` OFF PATH, resolvable only through `mise which ast-grep`**: install
  it with `mise use -g` but never add mise's shim directory to PATH, or
  `shutil.which("ast-grep")` returns the shim and
  `test_resolve_ast_grep_matches_mise_which_output` fails on a path mismatch.
- `mise` itself must be on PATH: two tests assert `shutil.which("mise") is not None`.

The capability step fails loudly, naming what is missing, rather than letting a
module skip:

```
python -c "<check>"   # file symlink, directory symlink, bash on PATH,
                      # mise on PATH, rg on PATH, ast-grep NOT on PATH,
                      # `mise which ast-grep` resolving
```

Job-presence acceptance stays a set containment, never a count:
`{'test','shell','lint','node'} <= d['jobs'].keys()` plus
`d['jobs']['windows']['runs-on'] == 'windows-latest'`.

## Data flow

**Brush refusal path.** `--repo` → `repo_root()` (git, resolved) → user path
`raw` → `(root / raw).resolve()` → escape check against `root` → `as_git_rel()`
produces the ONE slash-form representation → `normalise_rel()` collapses dotdot
→ compared against `load_tracked()`'s `git ls-files -z` output (always slash
form) and against the slash-form protect prefixes → refusal JSON and manifest
row both carry that same slash-form string. Today the representation forks at
`os.path.relpath`: the comparison sees `dev\local\x` while git said
`dev/local/x`, so on Windows a tracked or protected file passes the veto.

**Publication path.** `funnel.run` builds proposals + discards → `write_proposals`
reserves `out_dir` by mkdir → writes every file into the `.partial-<pid>` sibling
→ one rename publishes the whole set → the reservation is released exactly once,
by whichever branch ran. A reader either sees no directory or sees the complete
set; it can additionally see an empty reservation, which is unchanged POSIX
behaviour and, on Windows, briefly sees the name absent between rmdir and rename.

**Fixture path.** A test asks `conftest.py` for a capability (`a stub binary`,
`an isolated home`, `a denied path`, `a resolved-tool run`); the fixture decides
the host mechanism; the test keeps asserting the same product behaviour on both
hosts. No test branches on the platform itself.

## Reuse inventory

Greps run (`rg` over `skills/`, `tests/`, `scripts/`, `--type py`):
`chmod\(0`, `symlink_to|os\.symlink`, `os\.pathsep|":".join|os\.sep`,
`Path\.home|setenv\(.HOME`, `#!/bin|"bash"|/bin/sh`, `write_proposals`,
`junction|sys\.platform|os\.name`, and - added after dispatch 2 found the class
the first set could not surface - `assert "[^"]*/[^"]*" in (captured|out|err|report)`
for path strings asserted against printed output. Each returning grep was
confirmed by a hit;
the `rationalizations.md` synonym file is absent on this host, so verb/noun
synonyms were supplied by hand (`stub`/`fake`/`fixture`, `deny`/`refuse`/`lock`,
`home`/`profile`, `sep`/`pathsep`/`separator`).

**Reused, no new code:**

- `src/agent_skills_braid/cli.py:186` `_link_dir(..., platform: str = os.name)` —
  the injected-platform idiom is already the repo's answer to "test a Windows
  branch from any host". `tests/test_braid.py:171` uses it. Nothing to add; the
  junction fallback needs no runner.
- `skills/sweep-fix/scripts/conftest.py` — the existing conftest proves the
  fixture-injection route into `skills/*/scripts/` works.
- `os.pathsep` is ALREADY used correctly at `test_sweep_resolvers.py:51,63,136,148`.
  Only the three hardcoded `"/usr/bin:/bin"` literals (lines 105, 153, 162) need
  replacing with a controlled empty directory.
- `functools.lru_cache` cache-clearing (`sweep.resolve_rg.cache_clear`) already
  isolates resolver state per test.
- `PurePath.as_posix()` / `posixpath.normpath` / `ntpath.expanduser` — stdlib
  covers every path-form conversion; no helper module and no dependency.
- `PROTECT_*` tuples, `veto_reason`, `relocate`, `note_manifest` — the whole
  protection ladder is reused as is; only the string form flowing into it changes.
- `_write_proposal_files`, both `json.dumps` calls, the `.partial-<pid>` staging
  convention — reused untouched, which is what keeps the output bytes identical.

**Nothing found, greps tried:** a shared cross-skill test-helper package
(`rg --files -g 'conftest.py'` → one file; `rg -l "import test_helpers"` → none;
each skill has its own `*_test_helpers.py` and none is imported across skills),
and any existing Windows CI job (`rg -n "windows" .github/` → none). Both are
genuinely new.

## Alternatives considered

**A. Per-test platform branches, no shared conftest (smallest diff).** Each of
the seven test files grows its own `if os.name == "nt"`. Smallest structural
change and nothing new to learn. Rejected: the same four decisions (stub
extension, home variables, denial mechanism, invocation shape) would be
re-derived in seven places, and the extension decision in particular has to
agree with `shutil.which` byte-for-byte or the resolver tests fail confusingly.
One conftest is ~60 lines against ~7 scattered branches, and it is the only
option that keeps the *tests* free of platform conditionals.

**B. Chosen: rootdir `conftest.py` + targeted product fixes + a fifth CI job.**
The extra size over A buys one definition per portability decision, and a
`grep`-able answer to "how does this suite fake an executable / deny a read".
It also keeps the two product fixes (`trash_untracked.py`, `proposal.py`)
strictly separate from the test-portability work, so a reviewer can see that the
data-protection changes are three lines and a branch, not a refactor.

**C. Windows job inside the existing `test` matrix (`os: [ubuntu, windows]`).**
Fewer job definitions. Rejected: the toolchain step differs completely (symlink
vs copy for `rg`, different mise installer, `GITHUB_PATH` mechanics), so every
step would carry an `if: runner.os ==` guard, and the Python-version matrix
(3.10 and 3.13) would silently double into four jobs. The PRD asks for the full
suite on `windows-latest`, once, at 3.13.

**D. Make publication portable by dropping the mkdir reservation and probing
`out_dir.exists()` before staging.** Would let a single `os.rename` work on both
hosts with no branch. Rejected outright: `test_write_proposals_refuses_to_publish_
over_a_directory_that_already_exists` asserts `excinfo.value.errno == errno.EEXIST`
and its comment names the check-then-write race as the thing the contract
forbids. The chosen design keeps the reservation and changes only the release.

## Risks & edge cases

- **The hung-search test has no free real-executable stub on Windows.**
  `test_scan_reports_a_hung_search_as_a_failed_repo_without_blocking`
  (`test_sweep_scan.py:178`) needs a binary that sleeps regardless of argv, and
  `sweep._run_rg` reaches it through `executable=`, which CreateProcess refuses
  for `.cmd`/`.bat`. Copying `python.exe` does not work either: `_run_rg` always
  passes `--json` first, so the interpreter exits on an unknown option before it
  can sleep. Producing a real `.exe` needs a compiler. **Decision:** on Windows
  this ONE test denies at the boundary instead — a wrapped `subprocess.run` that
  really sleeps and really raises `subprocess.TimeoutExpired` — so the test still
  runs and still asserts on both hosts (no skip, no xfail), while POSIX keeps the
  real child process. This is the only place the Windows leg is a simulation, and
  the implementation must say so in a comment at the call site.
- **`scripts/test_check_changelog_skills.py` joins `testpaths` and has never run
  on Windows.** It is the one file the PRD adds to collection without having
  audited. Reproduce it on the runner before assuming it is portable.
- **`shutil.which` on Windows prepends the current directory.** The three
  "nothing resolves" resolver tests must point PATH at a controlled empty
  directory AND not rely on cwd being clean.
- **Symlink privileges.** GitHub's `windows-latest` runners execute as
  administrator, so `os.symlink` succeeds and the real-symlink tests
  (`test_braid.py:341`, `test_survey.py:336`, `test_purge_devlocal.py:124`,
  `test_dedup_classify.py:140,425,464`) run for real. That is also exactly why
  braid's junction fallback will NOT be exercised: the fallback triggers on
  WinError 5/1314, which an admin never sees. README must keep saying the
  junction path is stub-tested. If the runner image ever drops admin, the
  capability step fails loudly instead of the tests quietly skipping.
- **`deny_access` patches `builtins.open` on Windows.** Filtered delegation keeps
  every unrelated read working, but a test that denies a path and then triggers
  pytest internals reading that same path would see the fake. Scope each call to
  the narrowest possible path.
- **Likely next changes, and what this boxes in.** (1) More skills adding Python
  tests: they inherit the Windows gate automatically and must use the conftest
  fixtures rather than `chmod(0)` — worth an `AGENTS.md` line, though this PRD
  does not require one. (2) A second Python version on Windows: the job is
  written for one, and adding a matrix later is a local edit. (3) Someone
  "simplifying" `normalise_rel` back to `os.path.normpath`: the brush
  separator regression test is what stops that, so it must assert the slash form
  explicitly, not just the verdict.
- **Remote evidence.** Local `master` is 76 commits ahead of `origin/master`.
  Phase 2's acceptance needs a real Actions run at the changed commit, which
  requires those commits to reach GitHub. If push or `gh` auth is unavailable,
  Phase 2 records an execution blocker; it does not weaken the pytest command
  and does not mark the validation complete.

## Test strategy outline

- **Runner**: a YAML assertion that `jobs.windows.runs-on == 'windows-latest'`
  and that `{'test','shell','lint','node'}` is a subset of `jobs` (set
  containment, never a job count); a check that the Windows run step is the
  unfiltered `uv run --python 3.13 pytest` with no `-k`, no `--deselect`, no
  `continue-on-error`; `uv run pytest --collect-only -q` recorded before and
  after so the Windows collection can be compared against POSIX rather than
  against a hardcoded number.
- **Fixture portability**: no new behaviour to test, so the bar is
  *collection parity plus preserved assertions* — the same test ids collect on
  both hosts, no test gains a skip/xfail/deselect marker, and the real resolver,
  real Bash subprocess, real symlink and denied-read cases keep asserting what
  they assert today. Existing strict-xfail markers for defects outside this PRD
  stay; the optional tree-sitter and local-corpus skips stay optional on both.
- **Brush**: regressions for a tracked nested file, a protected prefix, a dotdot
  alias, a path with spaces, and a path spelled with the host's native separator,
  each with a permitted-path positive control so the test cannot pass by refusing
  everything; plus an assertion that the refusal path string and the manifest
  path string identify the same file.
- **Publication**: keep every existing scenario — refuses an existing empty
  destination, refuses a non-empty one, both with `errno == EEXIST`; competing
  writers produce exactly one winner and the loser removes nothing of the
  winner's; an injected write failure leaves neither `out_dir` nor a staged
  sibling; the reservation is released when staging cannot be built; output bytes
  and JSON schema unchanged. Tests that assert the POSIX `os.replace`-onto-a-
  reservation mechanic are re-pointed at the ownership guarantee instead.
- **Documentation**: a file assertion that README contains `py bin\braid.py` and
  no doubled-backslash spelling, names full Python coverage on `windows-latest`,
  keeps the Braid-needs-no-Bash / Bash-backed-tests-need-Git-Bash distinction,
  and makes no real-junction claim.
- **Evidence**: the Phase 2 run URL, tested commit, collected test count and every
  skip/xfail reason recorded in the review evidence.

## Review log

dispatch 1 (claude): cardinal-sin 0, blocker 5, non-blocker 6, question 2

Blockers fixed in the doc: `deny_access` patched `builtins.open` only, which does
not cover `Path.read_text` (it goes through `io.open`, a separate binding);
`write_executable_stub`'s hand-spelled return path is not byte-equal to
`shutil.which` on Windows (%PATHEXT% supplies uppercase extensions);
`os.geteuid()` at module scope in three files aborts Windows collection;
`deny_access` had no release affordance, but four tests lift the denial mid-body
and read back; the literal `..\outside\secret.md` decoy cannot be created on
Windows and "fixing" it moves the decoy out of the plane.

Recorded, not fixed:

- non-blocker: the publication guarantee table says the competing-writer and
  "must not remove another writer's directory" rows are "already pinned by a
  test"; no publication concurrency test exists in the repo. Those two rows need
  NEW tests, and the table contradicts the Test strategy outline, which already
  asks for one.
- non-blocker: on Windows the reservation is exclusive only up to the release -
  a competitor can `mkdir` in the window between `rmdir` and `rename`. No data
  is lost (the loser's rename fails and `reserved` is already False), but the
  design presents the property as preserved rather than genuinely weaker, and
  `write_proposals`'s docstring still names `os.replace` as the mechanism.
- non-blocker: the hung-search Windows wrapper must derive its behaviour from
  the `timeout` kwarg it receives (sleep the full 5s and raise nothing when it
  is absent). `sweep.scan` catches bare `Exception`, so an unconditional
  `TimeoutExpired` would keep the Windows leg green after `timeout=` was deleted
  from `_run_rg`.
- non-blocker: a fourth hardcoded `"/usr/bin:/bin"` PATH literal lives at
  `test_sweep_scan.py:163`, outside the three the reuse inventory names. On
  Windows it is one nonexistent entry, so the test passes for the wrong reason.
- non-blocker: the Git Bash path conversion is listed as an edit but has no
  contract in Interfaces, which is the fifth portability decision and the exact
  thing Alternative A was rejected for scattering. Either give it a fixture or
  say why it stays local to `test_build.py`.
- non-blocker: the `windows` job's toolchain and capability steps are comments
  with no `run:`. `https://mise.run` is a `sh` installer with no Windows
  equivalent named, and whether the chosen installer puts mise's shims on PATH
  decides `test_resolve_ast_grep_matches_mise_which_output`.
- question: the design cites `_link_dir` at `cli.py:186`; the symbol is
  `create_directory_link` at `cli.py:182`. There is a second
  `platform: str = os.name` at `cli.py:41` the design does not place.
- question: `.gitattributes` covers `*.bash`, which matches no file in the repo,
  and the design says nothing about `git add --renormalize` or about whether the
  newly collected `scripts/test_check_changelog_skills.py` (which reads the real
  `CHANGELOG.md`) is line-ending sensitive.

dispatch 2: codex unavailable, Claude fallback

dispatch 2 (claude-fallback): cardinal-sin 0, blocker 2, non-blocker 5, question 2

`codex-run.sh` exited 0 but wrote only the echoed prompt to its `-o` file: no
findings, no assistant turn (codex v0.153.4, gpt-5.6-sol, read-only sandbox,
session `01a079e3`). Unparseable as findings, so the skill's codex-outage rule
applies and dispatch 2 ran as a fresh Claude reviewer with the identical prompt.

Blockers fixed in the doc: the design dropped the PRD's "compare platform-native
diagnostics" line entirely, and with it a whole confirmed failure class - tests
asserting a slash-containing path string against text a product module printed by
interpolating a `Path` (`test_funnel_main.py:379` against `funnel.py:483`;
`test_funnel_distil_publication.py:_proposals_paths_named`'s `"/" in token`
filter, which finds zero tokens on Windows and fails three tests). The reuse
inventory's grep set could not surface that class at all. Second: the backslash-
decoy guard `planted.parent == memory_dir` contradicted its own Windows spelling
(a nested decoy's parent is `memory_dir/outside`), so the mandated guard would
have fired on every Windows run.

Recorded, not fixed:

- non-blocker: `deny_access`'s contract is too weak for the two tests that
  compare the OS's own refusal text (`test_write_refusals.py:155-174` asserts
  `str(exc)` string identity between two independently raised errors), and
  "keep their bodies unchanged" is wrong: four in-body `chmod` lifts
  (`test_write_refusals.py:168,210`, `test_check_links.py:104`,
  `test_dedup_classify.py:325`) each become an `allow()` call. The wrapper should
  raise `PermissionError(EACCES, os.strerror(EACCES), os.fspath(path))` so
  `str(exc)` is identical whichever call site raised it.
- non-blocker: five root/permission escape hatches exist, not three. Beyond the
  module-scope `os.geteuid()` decorators there are two in-body
  `pytest.skip("this user reads a 0o000 file anyway...")` guards
  (`test_dedup_classify.py:318`, `test_dedup.py:446`) that fire on 100% of
  Windows runs. They self-heal only if `deny_access` is established BEFORE each
  guard's probe read; state that ordering.
- non-blocker: the `deny_access` vector table maps `os.listdir` to
  `Path.iterdir`, which is true on 3.10 but not on 3.13 (`pathlib/_local.py`
  uses `os.scandir`). Both versions are in the matrix, so wrap both - but stop
  attributing one vector to one call.
- non-blocker: the `testpaths` change has three unstated consequences - the lint
  job's dedicated `uv run pytest scripts/... -q` step becomes redundant;
  `scripts/test_check_changelog_skills.py` starts running under 3.10 too; and the
  new root `conftest.py` is the first portability file inside ruff's scope
  (`pyproject.toml:32` excludes `skills` and `docs`, not the root).
- non-blocker: the reuse inventory misses the repo's own precedent -
  `purge_devlocal.py` already applies `rel.as_posix()` throughout its reporting
  and manifest surface (lines 199, 268, 367, 422-429), which is why
  `test_purge_devlocal.py:541` is already Windows-safe. `trash_untracked.py` is
  the outlier, and `as_git_rel` should be cited as following that convention.
- question: `shutil.which(name, path=...)` still searches `os.curdir` first on
  Windows (the insertion is in the `else:` branch), so
  `write_executable_stub`'s return value could come from the cwd rather than the
  directory it wrote to; asserting the returned parent would make the contract
  self-checking.
- question: `main()`'s added `root = ....resolve()` is a product change with no
  regression naming it. Either pin it with a short-name/symlinked `--repo`
  spelling or say plainly it is untested belt-and-braces.

Verified sound by dispatch 2 and not re-litigated: the rootdir-`conftest.py`
premise, checked EMPIRICALLY (a throwaway repo mirroring this layout collected
`3 passed`: the root conftest reaches `skills/*/scripts/` tests, two same-named
`conftest` modules coexist with no `ImportPathMismatchError`, bare `import sweep`
still resolves, `scripts/` collects); `_patch_write_vectors` already patching
`os.rename` as well as `os.replace`, so the Windows rmdir->rename branch survives
`_assert_never_built_in_place` unchanged; every existing strict xfail being safe
from XPASSing on Windows; `create_directory_link`'s junction branch being
unreachable when `os.symlink` succeeds.

dispatch 3: codex unavailable, Claude fallback

dispatch 3 (claude-fallback): cardinal-sin 0, blocker 2, non-blocker 2, question 1

Verification pass, required because dispatch 2 found blockers. Codex was already
established as out at dispatch 2 (exit 0, prompt echoed, no assistant turn), so
the outage rule applied again rather than burning a second silent run.

Verdicts on dispatch 2's blockers: **(b) FIXED** - confirmed empirically on 3.10
and 3.13 that `planted.is_file()` and
`planted.resolve().is_relative_to(memory_dir.resolve())` both hold for the POSIX
backslash-named decoy, and that the proposed Windows spelling still trips a
`/`-only reader (`dedup.py:_MEMORY_NAME` is the only gate that rejects
`outside\secret`; the containment gate at `dedup.py:115` does not, so the
positive control survives). **(a) PARTIALLY FIXED** - the rule and both named
sites verified mechanically (`str(PureWindowsPath("dev/local/audit-results"))`
is a substring of the interpolated `report_dir`; `os.sep in token` is
byte-identical on POSIX and correct on Windows), but the site list was
incomplete.

Blockers fixed in the doc: `skills/survey/scripts/test_survey.py` carries three
more instances of the printed-path class (lines 900-901, parametrized over
`ports/payment` and `adapters/email`, and 942-943), asserting against
`run.py:380`'s `str(f.relative_to(repo_path))`; the file was absent from Module
placement entirely, and the doc's own new grep structurally cannot find them
because the expectation is an f-string bound to a variable and the haystack is
`section`. Second: `deny_access`'s vectors could not reproduce a denied
DIRECTORY's probe refusal - `Path.is_file()` goes through `os.stat`, which was
unwrapped, so on Windows `write.py:172-175`'s probe branch is never entered and
`test_main_write_refuses_an_update_whose_target_cannot_even_be_probed...` goes
green while exercising the read-refusal path its sibling already covers. Silent
coverage loss; `os.stat`/`os.lstat` are now wrapped with a fixture self-check.

Also folded in while fixing (a), because both would have been introduced BY the
fix rather than found by it: `test_funnel_report.py:128` and `:243-263` assert
against a hardcoded slash literal in `funnel.py:257-258`, so converting them
introduces a Windows-only failure - they are now named as verified-safe, with
the discriminator ("the product interpolated a `Path`") stated; and
`test_funnel_distil_publication.py` has no `import os`, so the token-filter edit
is not one character.

Recorded, not fixed:

- non-blocker: the vector attributions are version-dependent and the doc had
  them backwards in places. Measured: on 3.10, patching `io.open` does NOT reach
  `Path.read_text` (`pathlib.py:286` binds `open = io.open` on `_NormalAccessor`
  at class-definition time); on 3.13, patching `os.scandir` reaches
  `Path.iterdir` but NOT `Path.glob` (glob's `_StringGlobber` captures scandir as
  a staticmethod at class creation). **The boundary wrappers rely on 3.11+
  call-time lookup, so the Windows job's `--python 3.13` pin is load-bearing, not
  incidental** - which makes the Risks bullet "(2) A second Python version on
  Windows ... adding a matrix later is a local edit" FALSE as written. Treat that
  bullet as corrected here: adding 3.10 to the Windows job would silently no-op
  every wrapper. `Path.glob` should come off the `os.scandir` row unless
  `glob._StringGlobber.scandir` is wrapped too.
- non-blocker: the reuse-inventory grep for the printed-path class should be
  widened past `assert "..." in captured` to catch f-string expectations bound to
  a variable, e.g. `rg -n '^\s*[a-z_]+ = f?"[^"]*/[^"]*"' -g 'test_*.py'`.

Verified sound by dispatch 3 and not re-litigated: `_MEMORY_NAME` being the gate
that makes the Windows decoy spelling still exercise the rejection;
`write.py`'s `_readable_bytes` / probe split; the four-job `ci.yml` inventory;
`purge_devlocal.py`'s already-portable reporting surface;
`test_brush_scripts.py`'s existing dotdot cases.

Checked and found sound by dispatch 1, so not re-litigated: every
`trash_untracked.py` line citation and the `normalise_rel` behaviour on both
dotdot regressions; `collect_facts.py:classify_path` already being slash-uniform,
so scoping the brush fix to `trash_untracked.py` is right; the
`MOVEFILE_REPLACE_EXISTING`-cannot-take-a-directory premise and the rejection of
Alternative D against the `errno == EEXIST` assertion; the `ntpath.expanduser`
rationale for `isolate_home`; the `executable=`/CreateProcess rationale for
`run_resolved_tool`.

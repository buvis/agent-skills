# Design: 00073 sweep-fix loud failures

## Architecture fit

All work lands in one module, `skills/sweep-fix/scripts/sweep.py`, the
stdlib-only CLI behind the `sweep-fix` skill, plus its pytest files beside
it. The module already has the right seams: `main()` owns the single
diagnostic handler (`except RuntimeError` -> stderr, `return 1`), `scan()`
owns per-repo isolation (a failing repo becomes a `failed` row, never an
abort), and the resolvers (`resolve_rg`, `resolve_ast_grep`) already raise
`RuntimeError` with a one-line message naming the tool. The fix routes
setup failures (tool, registry, control repo) into `main`'s handler and
leaves repo-level failures inside `scan`. No new modules, no new
dependencies; `ruff` excludes `skills/`, so `uv run pytest` plus
`validate_skill.py` are the gate (capsule, Component Boundaries).

## Module placement

Edits only:

- `skills/sweep-fix/scripts/sweep.py`: `main`, `verify_control`,
  `enumerate_repos`, new private `_git_root`, `_resolve_report_path`,
  `_render_astgrep_rule_block`; delete `_needs_yaml_quoting`, `_yaml_scalar`,
  `_YAML_INDICATOR_CHARS`, `_YAML_RESERVED_WORDS`, `_YAML_DATE_RE`,
  `_YAML_CONTROL_CHARS_RE`, `_YAML_INF_NAN_RE`, `_YAML_SCALAR_ESCAPES`; add
  private `_yaml_quote`.
- `skills/sweep-fix/scripts/test_sweep_main.py`: new exit-path tests.
- `skills/sweep-fix/scripts/test_sweep_verify_control.py`: rewrite one test.
- `skills/sweep-fix/scripts/test_sweep_enumerate.py`: new walk-up test.
- `skills/sweep-fix/scripts/test_sweep_render_report.py`: migrate one
  assertion, add one parametrised test.
- `skills/sweep-fix/scripts/test_sweep_main.py` or a resolver-adjacent file:
  the report-suffix test (`_resolve_report_path` is called from `main`; the
  test calls it directly).
- `CHANGELOG.md`: one `### Fixed` entry under `[Unreleased]` (`fix` commits
  require it per rules/changelog.md).

## Interfaces & contracts

### `main(argv=None) -> int`

Order, unchanged except the new first line in the `try`:

```python
args = _parse_args(argv)
cwd_path = Path(args.cwd).resolve()
out_path = _resolve_report_path(cwd_path, args.out, args.reason)  # refuses bad --out first (PRD 00032)

try:
    resolve_rg() if args.kind == "rg" else resolve_ast_grep()
    repos, gaps = enumerate_repos(args.registry, args.cwd)
    hits, suppressed, failed = scan(args.pattern, args.kind, repos, cap=args.cap)
    if not hits:
        verify_control(args.pattern, args.kind, Path(args.control_repo), args.control_term)
except RuntimeError as exc:
    print(exc, file=sys.stderr)
    return 1
```

- A missing tool: the resolver's existing `RuntimeError` message
  (`Could not resolve rg: ...` / `Could not resolve ast-grep: ...`) is
  printed as the one stderr line; exit 1; no report file and no report
  directory is created (the `mkdir`/`write_text` stay after the `try`).
- `scan()`'s own `resolve_ast_grep()` try/except and `_scan_repo`'s per-repo
  `except Exception` stay as-is (per-repo isolation).
- When `--kind astgrep` and no hits, `verify_control`'s control-term search
  needs `rg`; an unresolvable `rg` there surfaces as `verify_control`'s
  `RuntimeError` (below), still exit 1.

### `verify_control(pattern, kind, control_repo, control_term) -> None`

```python
hits, _suppressed, failed = scan(pattern, kind, [control_repo])
if failed:
    reason = " ".join(next(iter(failed.values())).split())
    raise RuntimeError(
        f"sweep unverified: control repo {control_repo} could not be scanned: {reason}"
    )
if hits:
    return None

try:
    result = _run_rg(["-F", "--", control_term, "."], control_repo)
except Exception as exc:
    raise RuntimeError(
        f'sweep unverified: could not search control term "{control_term}" in {control_repo}: {exc}'
    ) from exc
if result.returncode == 1:
    return None
# unchanged: print the "sweep unverified: pattern found 0 hits ..." message, raise SystemExit(1)
```

- Both new messages contain the literal `sweep unverified` and
  `str(control_repo)`.
- `except Exception` stays broad here on purpose: anything that stops the
  control search (`FileNotFoundError` for a missing dir, `TimeoutExpired`,
  the `RuntimeError` from `_run_rg` or `resolve_rg`) is converted, never
  swallowed.
- Docstring updated to state: raises `RuntimeError` when the control repo
  cannot be scanned or the control-term search cannot run.

### `_git_root(path: Path) -> Path` (new, private)

```python
def _git_root(path):
    """Nearest ancestor of `path` (itself included) holding `.git`, or
    `path` itself when none does."""
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return path
```

`.exists()` matches the existing `(path / ".git").exists()` checks, so a
`.git` file (worktree, submodule) counts.

### `enumerate_repos(registry, cwd) -> (repos, gaps)`

```python
registry = Path(registry)
if not registry.is_file():
    raise RuntimeError(f"registry not found: {registry}")
cwd = _git_root(Path(cwd))

with registry.open() as fh:
    registered = [Path(row[0].strip()) for row in csv.reader(fh) if row and row[0].strip()]
# rest unchanged, using the walked `cwd`:
# work-tree check `cwd == work_tree`, dedup `cwd not in repos`
```

- The message is exactly `registry not found: <path>` where `<path>` is
  `str(Path(registry))` as passed (not resolved).
- `cwd` is walked, not resolved: same string form as before for a cwd that
  is already a repo root, so existing dedup against registry rows holds.
- No walk-up past `BUVIS_BARE["work_tree"]` is needed: `$HOME` has no
  `.git` (the bare repo is `~/.buvis`), so a non-repo cwd under home walks
  to nothing and stays as given, as today.

### `_yaml_quote(value: str) -> str` (new, private; replaces `_yaml_scalar`)

```python
def _yaml_quote(value):
    """Render `value` as a YAML double-quoted scalar. A JSON string is a
    valid YAML double-quoted scalar; characters JSON leaves raw that YAML
    forbids or folds (DEL, C1 incl. U+0085, U+2028/2029, BOM, other
    non-printables) are escaped as \\uXXXX / \\UXXXXXXXX."""
    return "".join(
        ch if ch.isprintable()
        else f"\\u{ord(ch):04x}" if ord(ch) <= 0xFFFF
        else f"\\U{ord(ch):08x}"
        for ch in json.dumps(value, ensure_ascii=False)
    )
```

- Deliberate deviation from the PRD's literal `json.dumps(value,
  ensure_ascii=True)`: `ensure_ascii=True` emits astral characters (emoji)
  as UTF-16 surrogate pairs, which PyYAML decodes as two lone surrogates,
  so `"😀x"` no longer round-trips (measured 2026-10-11); raw DEL is also
  left unescaped by JSON and is a YAML non-printable. The chosen form keeps
  the PRD's intent (stdlib quoting, no hand-rolled table) and passes every
  Must-have shape plus astral characters (measured: DEL, U+0085, U+2028,
  U+FEFF, `é`, `😀`, `"`, `\`, `: `, `#`, leading `-`, `null`, `123`,
  `.inf`, tab/CR/LF/NUL all round-trip through `yaml.safe_load`).
- Every scalar is now always quoted. `_render_astgrep_rule_block` calls
  `_yaml_quote(derivation["reason"])` and `_yaml_quote(derivation["pattern"])`;
  nothing else changes in the block.
- Acceptance grep `rg -n "_needs_yaml_quoting|_yaml_scalar" sweep.py` must
  print nothing, so the new name must not contain `_yaml_scalar`.

### `_resolve_report_path(cwd_path, out, reason) -> Path`

```python
if not out:
    slug = re.sub(r"[^a-z0-9]+", "-", reason[:40].lower()).strip("-")
    stem = f"docs/dev/project-management/audit-results/sweep-{slug}-{date.today().isoformat()}"
    out = f"{stem}.md"
    n = 2
    while (cwd_path / out).exists():
        out = f"{stem}-{n}.md"
        n += 1
# unchanged: resolve, refuse outside cwd_path (exit 1), return
```

- Explicit `--out` is never suffixed (overwrite as given, as today).
- Second same-day same-reason sweep -> `...-<date>-2.md`; third -> `-3.md`.

## Data flow

argv -> `_parse_args` -> `_resolve_report_path` (refuse bad `--out`, pick a
free default name) -> `try:` resolver for `--kind` -> `enumerate_repos`
(registry check, cwd walk-up, gaps) -> `scan` (per-repo isolation into
`failed`) -> if zero hits, `verify_control` (control-scan `failed` or a
failed control-term search -> `RuntimeError`) -> `except RuntimeError`:
one stderr line, exit 1, nothing written. Success path unchanged:
`render_report` (rule block via `_yaml_quote`) -> `mkdir` + `write_text` ->
print path, exit 0. `SystemExit(1)` from the unverified-pattern path and
from `--out` refusal pass through untouched.

## Reuse inventory

- `sweep.resolve_rg()` / `sweep.resolve_ast_grep()`
  (`skills/sweep-fix/scripts/sweep.py:16,53`): already raise
  `RuntimeError` naming the tool; call them, add nothing.
- `main`'s existing `except RuntimeError` (`sweep.py:584`): becomes live;
  no second handler.
- `json.dumps` (stdlib) + `str.isprintable` (stdlib): replace the 50-line
  hand-rolled YAML quoting.
- `(path / ".git").exists()` idiom (`sweep.py:145,155`): reused in
  `_git_root`.
- Git-root walk-up helpers elsewhere in the repo:
  `rg -n "def .*(git_root|find_root|walk_up|repo_root)" skills bin` -> none
  in `sweep-fix`; other skills' helpers are not importable (each skill is
  self-contained, no shared lib), so a 6-line private helper is right.
- Test helpers `_make_repo`, `_write_registry`,
  `_init_git_repo_with_tracked_files`, `_plant_matches`
  (`sweep_test_helpers.py`) and the `_clear_resolver_caches` autouse
  fixture (`conftest.py`) - new tests reuse them; patching `shutil.which`
  / `sweep.resolve_rg` works because the cache is cleared per test.
- `yaml.safe_load` (test-only, already imported in
  `test_sweep_render_report.py:7`) and `_render_astgrep_rule_text` helper
  (`test_sweep_render_report.py:401`) for the new parametrised test.

## Alternatives considered

1. **Smallest diff (chosen, close to it):** hoist one resolver call, convert
   two `verify_control` swallow points to raises, add a guard + walk-up in
   `enumerate_repos`, swap the YAML helpers for `json.dumps` plus a
   non-printable escape, add a suffix loop. ~+30/-60 lines in `sweep.py`.
2. **Typed error hierarchy** (`SweepSetupError(RuntimeError)` subclasses per
   cause, `main` maps each to a message): clearer taxonomy, but `main` has
   one handler and one exit code; nothing reads the type. Rejected (YAGNI).
3. **YAML via `ensure_ascii=True` exactly as the PRD wrote:** shortest
   quoting line, but regresses astral characters (emoji) that the current
   code round-trips, and leaves DEL raw. Rejected; the chosen form costs one
   generator expression.
4. **Collision handling by timestamped names** (`-HHMMSS`): no loop, but
   breaks the documented `sweep-<slug>-<date>.md` shape and still collides
   within a second. Rejected.

## Risks & edge cases

- `resolve_ast_grep()` can raise `subprocess.TimeoutExpired` from `mise
  which` (not a `RuntimeError`), which would escape `main` as a traceback.
  Pre-existing; out of PRD scope. Next-change candidate: catch it in
  `resolve_ast_grep` and re-raise as `RuntimeError`.
- `verify_control` now raises on a missing `--control-repo` directory where
  it used to warn and pass. That is the intended contract reversal (PRD
  Must-have); a caller passing a bad control repo now gets exit 1.
- Walk-up uses the first `.git` found: a cwd inside a nested repo or
  submodule resolves to the inner repo, not the outer one. Matches git's own
  behaviour.
- Default report path still lands under `--cwd` as given (resolved), not
  under the walked git root: running from a subdirectory writes the report
  under that subdirectory's `docs/dev/...`. Unchanged by this PRD; a likely
  next change is to anchor the default report at the git root, and nothing
  here blocks it (`_git_root` is reusable).
- Lone surrogates in argv (non-UTF-8 bytes via surrogateescape) would be
  escaped as `\udcXX`, which YAML rejects. The current code emits them raw,
  equally broken. Out of scope.
- The suffix loop is unbounded in theory; in practice bounded by the number
  of reports on disk for one slug and date. Race between two concurrent
  sweeps choosing the same suffix is accepted (single operator, CLI).
- Likely next changes: (a) anchor default report at git root, (b) convert
  `TimeoutExpired` in `resolve_ast_grep`, (c) a `--force` to overwrite
  instead of suffixing. None is boxed in.

## Test strategy outline

All in `skills/sweep-fix/scripts/`, run with
`uv run pytest skills/sweep-fix/scripts -q`.

- `test_an_unresolvable_scan_tool_exits_one_and_writes_no_report`
  (`test_sweep_main.py`): monkeypatch `sweep.resolve_rg` to raise
  `RuntimeError("Could not resolve rg: ...")`; `main(argv)` returns 1,
  stderr names `rg`, `out_path` does not exist, and `sweep.scan` is never
  called (patched to record calls).
- Invalid `--out` plus missing tool: both conditions set; `main` raises
  `SystemExit(1)` with the `--out` refusal message (output refusal wins) and
  the resolver is never called.
- `test_a_failed_control_search_exits_one` (`test_sweep_main.py`): zero-hit
  scan; patch `sweep._run_rg` with a wrapper that raises `RuntimeError` only
  when `"-F"` is in its args (so the control scan itself succeeds with zero
  hits and the control-term search is what fails); `main` returns 1, stderr
  contains `sweep unverified` and the control repo path, no report.
- A control repo that cannot be scanned (nonexistent dir) through `main`:
  returns 1, no report.
- `test_a_missing_registry_exits_one_naming_the_path`: `--registry` points at
  a nonexistent file; `main` returns 1, stderr is
  `registry not found: <path>`.
- Per-repo isolation regression: existing
  `test_main_survives_broken_buvis_bare_git_call_and_reports_it_as_failed`
  stays green unchanged.
- `test_verify_control_raises_when_the_fallback_check_cannot_run` (rename of
  `test_verify_control_warns_to_stderr_when_fallback_check_cannot_run`):
  nonexistent control repo -> `pytest.raises(RuntimeError)` whose message
  contains `str(control_repo)`. The two success-case `result is None`
  asserts (lines 19, 33) stay.
- `test_a_subdirectory_cwd_resolves_to_its_repo_root_and_is_not_a_gap`
  (`test_sweep_enumerate.py`): `PORTFOLIO_ROOT = tmp/portfolio`, repo at
  `portfolio/org/repo` with `.git`, nested `repo/a/b`; registry lists the
  repo; `enumerate_repos(registry, nested)` -> `repos == [repo]`, nested
  absent, `gaps == []`; then `scan(marker, "rg", repos)` finds a marker file
  planted at the repo root (outside `a/b`). Existing cwd tests
  (`..._appends_cwd_when_absent_from_registry`,
  `..._does_not_duplicate_cwd_already_registered`) keep their names; they
  already pass under walk-up (non-repo cwd stays as given; repo-root cwd
  walks to itself), so they change only if the run shows otherwise.
- YAML: migrate `assert "pattern: processInput($X)" in rule_text`
  (`test_sweep_render_report.py:300`) to
  `yaml.safe_load(...)["rule"]["pattern"] == "processInput($X)"` for each
  document; keep `test_render_report_astgrep_rule_block_runs_unedited_and_finds_planted_matches`
  (real ast-grep run) green. New
  `test_rendered_rule_block_round_trips_every_awkward_scalar` parametrised
  over `"`, `\`, `:` (`a: b`), `#` (`a #b`), leading `-`, `é`, `😀`,
  `\x7f`, `\x85`, using `_render_astgrep_rule_text` and `yaml.safe_load`;
  asserts `message` and `rule.pattern` equal the input and are `str`.
- `test_a_second_sweep_with_the_same_reason_on_the_same_day_gets_a_suffixed_report`:
  pre-create the default path under `tmp_path`; `_resolve_report_path(tmp_path, None, reason)`
  ends with `-2.md`; with `-2.md` also present, the next is `-3.md`.
  Explicit `--out` to an existing file returns that path unchanged.
- Success criteria check: `test_resolve_rg_exits_naming_both_candidates_when_neither_resolves`
  stays green.

## Review log

- non-blocker (d1): walk-up is a no-op for a relative `--cwd` (`_git_root(Path('.'))` returns `.`); suggested `_git_root(Path(cwd).absolute())` plus a `monkeypatch.chdir(nested)` + `--cwd .` test.
- non-blocker (d1): the walk-up test registers the repo, so `gaps == []` passes on old code too; add an unregistered-repo case under `PORTFOLIO_ROOT` (Blake's live repro) asserting `repo in repos` and `gaps == []`.
- non-blocker (d1): control-repo rg exit 2 (partial unreadable) and 30s timeout are now fatal via `failed`; Risks should say so (intended).
- question (d1): a cwd inside the buvis bare work tree (e.g. `~/.claude`) still lands as a plain Path, not the tracked-only bare entry; pre-existing, out of PRD scope.
- question (d1): Module placement wording - `_resolve_report_path`/`_render_astgrep_rule_block` are edited, not new; the suffix test file should be `test_sweep_main.py`.
dispatch 1 (claude): cardinal-sin 0, blocker 0, non-blocker 3, question 2
- non-blocker (d2): the astgrep branch of the resolver hoist is untested; parametrise the unresolvable-tool test over `--kind`, patching `sweep.resolve_ast_grep` for astgrep, so an unconditional `resolve_rg()` cannot pass.
- non-blocker (d2): the control-term branch of `verify_control` embeds raw `{exc}` (rg stderr is multi-line); collapse whitespace like the `failed` branch.
- non-blocker (d2): the renamed verify_control test hits the `if failed:` branch, not the control-term search; assert `could not be scanned` there and add a unit test patching `_run_rg` on `-F` expecting `could not search control term`.
- non-blocker (d2): non-repo-cwd tests (`..._appends_cwd_when_absent_from_registry`, `..._includes_both_bare_entry_and_unrelated_cwd_...`, `test_main_survives_broken_buvis_bare_git_call_...`) now depend on no `.git` above pytest's basetemp; note in Risks, optionally guard.
- non-blocker (d2): the rationale "raw DEL is left unescaped by JSON" is wrong for `ensure_ascii=True` (`json.dumps('\x7f')` gives `"\u007f"`); the astral surrogate-pair regression is the sole valid reason for the chosen form.
- non-blocker (d2): PRD Success Criterion 2 (two live reproductions) has no verification step; add exact commands (PATH without rg + no claude binary -> exit 1 `Could not resolve rg`; `--cwd skills/sweep-fix/scripts` -> repo root scanned, no gap row).
- question (d2): a registry that is a directory reads as `registry not found`; an unreadable file raises PermissionError outside the handler. PRD covers only missing.
- non-blocker (d2): `enumerate_repos`, `main` and `_resolve_report_path` docstrings go stale; touch them up.
dispatch 2: codex unavailable, Claude fallback (codex sandbox: `sandbox-exec: sandbox_apply: Operation not permitted`, could not read any file)
dispatch 2 (claude-fallback): cardinal-sin 0, blocker 0, non-blocker 7, question 1

# Design: Sweep a Fix Across the Portfolio

Source PRD: `dev/local/prds/wip/00002-add-sweep-fix-skill-v1.md`

## Architecture fit

This repo (`agent-skills`) has no shared library layer between skills — every
skill under `skills/<name>/` is self-contained: its own `SKILL.md`, its own
`scripts/*.py`, its own `test_*.py` importing only siblings in the same
`scripts/` dir (confirmed: no skill currently imports another skill's
`scripts/` module). `sweep-fix` follows the same shape: a new
`skills/sweep-fix/` directory holding one deterministic script module
(`sweep.py`) plus its test, and a `SKILL.md` that owns the one non-deterministic
step (deriving a pattern from a diff — a judgment call, not a transform, per
`rules/ai-app-design.md`: "classification with fuzzy boundaries" and "judgment
calls a rubric can't fully capture" belong to the model, not code). This
mirrors `brief-portfolio` (`collect.py` does the deterministic gather/render;
the skill body decides what to say about it) and `brush` (`collect_facts.py` +
`SKILL.md`).

## Module placement

New files only, no edits to existing skills:

```
skills/sweep-fix/
├── SKILL.md
└── scripts/
    ├── sweep.py
    └── test_sweep.py
```

## Interfaces & contracts

All in `skills/sweep-fix/scripts/sweep.py`. Python 3.10+ (repo-wide floor;
`strunk:check-python-compat` applies), stdlib only except `subprocess` calls to
external `rg`/`ast-grep`/`git`/`mise` binaries.

```python
GITA_CSV = Path.home() / ".config/gita/repos.csv"          # same path collect.py uses
PORTFOLIO_ROOT = Path.home() / "git/src/github.com"          # on-disk layout for gap detection
BUVIS_BARE = {"git_dir": Path.home() / ".buvis", "work_tree": Path.home()}

# ---- tool resolution ----

def resolve_rg() -> str:
    """Return an executable path that behaves like `rg`.

    Same algorithm as `~/.claude/hooks/cartographer-echo.py::_resolve_rg()`
    (ported, not imported — that file lives in a different, host-local repo):
    `shutil.which("rg")` first; else the Claude Code host binary run with
    argv[0] forced to "rg" via `executable=`, using `CLAUDE_CODE_EXECPATH` or
    `~/.local/bin/claude`. Raises SystemExit(1) naming both candidates tried
    when neither resolves — a loud failure, per the PRD's resolver contract.
    Callers pass the returned path as `subprocess.run([path, ...], executable=path)`
    only when the path is the claude-binary fallback (argv[0] must stay "rg");
    a real `rg` binary needs no `executable=` override.
    """

def resolve_ast_grep() -> str:
    """Return the `ast-grep` executable path: `shutil.which("ast-grep")` first
    (mirrors the check-PATH-then-mise shape already used by
    `skills/use-gemini/scripts/gemini-run.sh`'s `_resolve()`), else
    `mise which ast-grep` (subprocess, capture stdout, strip). Raises
    SystemExit(1) naming both attempts when neither resolves."""

# ---- repo enumeration ----

def enumerate_repos(registry_path: Path, cwd: Path) -> tuple[list[Path], list[str]]:
    """Returns (repos, gaps).

    repos: registry rows via the same one-line shape brief-portfolio's
    collect.py:429 uses — `[row[0] for row in csv.reader(registry_path.open())
    if row and row[0].strip()]` — as Path objects, filtered to paths that are
    still real repos (`(p / ".git").exists() or (p == BUVIS_BARE["work_tree"])`),
    plus `cwd` appended if not already present (registered or not, the PRD's
    own rule). The `~/.buvis`-backed `$HOME` case is not a registry row (a bare
    repo has no `.git` in its work-tree) — it is a named special case: whenever
    `cwd == BUVIS_BARE["work_tree"]` or that path is otherwise in scope, its
    file set comes from
    `git --git-dir=<BUVIS_BARE.git_dir> --work-tree=<BUVIS_BARE.work_tree> ls-files -z`
    converted to absolute paths, not a directory walk (regular pathspecs
    resolve against cwd, not the work-tree, for a bare-backed root).

    gaps: on-disk repos under `~/git/src/github.com/*/*` (a directory holding
    `.git`) whose absolute path is not in `repos`. Never written back to
    `registry_path`.

    No existing function does this (greps tried: `buvis` and `git-dir` across
    `skills/`, both empty — brush's `collect_facts.py` git helpers operate on
    one already-known repo root, not portfolio enumeration).
    """

# ---- scanning ----

AST_GREP_LANGUAGES = {  # extension -> ast-grep language name; conservative,
    ".js": "javascript", ".jsx": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".py": "python", ".rs": "rust", ".go": "go",
}  # matches the languages loupe already ships rule packs for

def scan(
    pattern: str,
    kind: str,            # "astgrep" | "rg"
    repos: list[Path],
    cap: int = 20,
) -> tuple[list[dict], dict[str, int]]:
    """Runs `pattern` read-only over every repo in `repos`.

    kind == "rg": `subprocess.run([resolve_rg(), "-n", "--no-heading", pattern, "."], cwd=repo, executable=...)`.
    kind == "astgrep": `subprocess.run([resolve_ast_grep(), "run", "--pattern", pattern, "--json=compact", "."], cwd=repo)`.
    Never `-i`/in-place flags, never any git subcommand that writes (the PRD's
    "no git command that writes anywhere" line) — reads only.

    Returns (hits, suppressed):
      hits: list of {"repo": str, "file": str, "line": int, "snippet": str,
                      "lang": str | None}  (`lang` from AST_GREP_LANGUAGES by
                      extension, None when unmapped), capped at `cap` rows per
                      repo, in scan order.
      suppressed: {repo_str: count_over_cap} — only for repos that hit the cap;
                  absent (not zero) for repos under it, so `render_report` can
                  tell "capped" from "not capped" without a sentinel.
    """

def verify_control(
    pattern: str,
    kind: str,
    control_repo: Path,
    control_term: str,
) -> None:
    """The control-term self-check (PRD Phase 1, must-have). Re-runs the same
    `pattern`/`kind` scan shape against `control_repo` alone; if it finds
    nothing, runs a second, independent literal search for `control_term` in
    the same repo. If the control term IS found but the pattern found nothing,
    raises SystemExit(1) with message
    'sweep unverified: pattern found 0 hits but control term "<term>" is
    present in <control_repo> — the pattern shape is likely broken (e.g. `\\|`
    alternation, which rg's Rust regex treats as a literal backslash-pipe)'.
    Never called when the pattern DID find hits anywhere — only guards the
    all-zero case, since that's the only case that can hide a broken pattern
    behind a false "clean" report.
    """

# ---- reporting ----

def render_report(
    derivation: dict,       # {"kind": str, "pattern": str, "reason": str, "control_term": str}
    hits: list[dict],
    gaps: list[str],
    suppressed: dict[str, int],
) -> str:
    """Renders the full markdown report (see PRD "Write the sweep report"):
    per-repo hit rows (`file:line`), the derivation kind/pattern/reason, the
    registry gap lines, suppressed counts, an ast-grep rule block (kind ==
    "astgrep" only, in loupe's rule-pack shape — `id`, `language`, `severity:
    warning`, `message`, `rule: {pattern: ...}`, one block per distinct `lang`
    present in `hits`), an "uncovered languages" line listing any `lang is
    None` extensions seen in hits that astgrep could not express, and the
    verbatim how-to-proceed block. The gap section always states the total
    count (`Gaps (N):` header, N = `len(gaps)`, even when N == 0) — a named
    PRD success metric ("states the count"), not just the list. Pure string
    building, no I/O — the caller writes it to
    `dev/local/audit-results/sweep-{slug}-{date}.md`.
    """

def main(argv: list[str] | None = None) -> int:
    """CLI: `python3 sweep.py --kind {astgrep,rg} --pattern TEXT --reason TEXT
    --control-term TEXT --control-repo PATH [--registry PATH] [--cwd PATH]
    [--cap N] [--out PATH]`. Wires resolve_* -> enumerate_repos -> verify_control
    -> scan -> render_report -> write `--out` (default
    `dev/local/audit-results/sweep-{slug}-{date}.md`, slug = first 40 chars of
    `--reason`, slugified). `--kind`/`--pattern`/`--reason`/`--control-term`/
    `--control-repo` are supplied by `SKILL.md` after it derives them from the
    fix commit — `main()` itself derives nothing (that step is the model's job,
    per Architecture fit above).
    """
```

## Data flow

1. `SKILL.md` reads the fix commit's diff (`git show <sha>` / `git diff <range>`)
   and decides `kind` + `pattern` + `reason` + a `control_term` known to be in
   that diff (all judgment calls — no sweep.py function does this).
2. `SKILL.md` invokes `sweep.py main()` (via its CLI) with those four values
   plus `--control-repo` (the current repo, where the fix commit lives).
3. `main()` resolves tools (`resolve_rg`/`resolve_ast_grep`), enumerates repos
   (`enumerate_repos`), runs the control check (`verify_control` — aborts loud
   on an unverified empty sweep), scans every repo (`scan`), renders the report
   (`render_report`), and writes it under `dev/local/audit-results/`.
4. `SKILL.md` reads the written report back, walks the **current repo's** hit
   rows with the user for approval, and applies fixes only there via `Edit`.
   Every other repo's rows stay report-only rows — `sweep.py` never edits
   outside the current repo, and never runs a git write.

## Reuse inventory

- `resolve_rg()` ports the algorithm in `_resolve_rg()`,
  `~/.claude/hooks/cartographer-echo.py:422-447` (cached PATH-then-execpath
  fallback for the "`rg` is a shell function, not a binary" trap). Not
  imported — that file is a host-local Claude hook outside this portable repo
  — the shape is copied, the caching (`functools.lru_cache`) and the
  `executable=` argument convention come with it.
- `resolve_ast_grep()`'s check-PATH-then-`mise which` shape mirrors `_resolve()`
  in `skills/use-gemini/scripts/gemini-run.sh:36-42` (bash today; ported to
  Python here since no other skill resolves a mise-managed tool from Python
  yet — greps tried: `mise which` across `skills/**/*.py`, empty).
- `enumerate_repos()`'s registry read reuses the exact one-line shape at
  `skills/brief-portfolio/scripts/collect.py:429`
  (`GITA_CSV = Path.home() / ".config/gita/repos.csv"` +
  `csv.reader(...).open()` + `row[0]`) — copied verbatim per the PRD's own
  instruction ("no new registry reader"), not imported (no skill in this repo
  imports another skill's `scripts/` module; `test_collect.py` is the only
  precedent and it imports its own sibling, not a cross-skill import).
- The ast-grep rule-block shape (`id`/`language`/`severity`/`message`/
  `rule: {pattern: ...}`) matches
  `~/.claude/plugins/cache/buvis-plugins/loupe/0.2.1/rules/ast-grep/javascript/rules.yml`
  — loupe's actual rule-pack format, so a pasted block is guaranteed
  syntax-compatible with the destination the PRD names.
- `nothing found` for the `~/.buvis` bare-repo file-listing helper: greps
  tried `buvis` and `git-dir` (control term `git-dir` confirmed present
  elsewhere via `skills/brush/scripts/collect_facts.py`, proving the search
  itself works) across `skills/**/*.py` — no existing helper lists a bare
  repo's tracked files; `enumerate_repos()` implements it inline as designed
  above.

## Alternatives considered

1. **Smallest diff**: one script that greps the current pattern across
   `~/.config/gita/repos.csv` repos and prints hits to stdout, no report file,
   no control-term check, no rule-pack block. Rejected: the PRD's Success
   Metrics and acceptance criteria explicitly require a durable
   `dev/local/audit-results/` report, a suppressed-count line, a gap list, and
   a paste-ready ast-grep block — dropping any of them fails the PRD's own
   test strategy, not just a nice-to-have.
2. **Three separate CLI scripts** (`derive.py`, `scan.py`, `report.py`) chained
   by the skill body. Rejected: adds process-boundary and I/O-passing
   complexity (temp files or stdout piping between three processes) for no
   benefit — the PRD's own module list is one file (`sweep.py`) with four
   library functions plus one non-deterministic step already isolated in
   `SKILL.md`; splitting further duplicates that boundary without adding
   anything else.
3. **Chosen**: one `sweep.py` module (importable functions + a thin `main()`
   CLI wrapper) called by `SKILL.md` after it derives the pattern. This is the
   PRD's own Structural Decomposition; the only material design choice left was
   *how* `resolve_rg`/`resolve_ast_grep`/`enumerate_repos` do their job, which
   the Reuse inventory above answers by pointing at existing, working code
   shapes instead of inventing new ones.

## Risks & edge cases

- **`rg`-as-function trap** (named directly in the PRD's own Risks section):
  mitigated by porting `_resolve_rg()` verbatim rather than re-deriving it, and
  by `verify_control()` catching a silently-broken pattern shape (e.g. Rust
  regex `\|` alternation) before it's reported as "0 hits, all clean."
- **`ast-grep` grammar gaps**: `AST_GREP_LANGUAGES` is a small, explicit map;
  any extension outside it degrades to "uncovered" in the report rather than
  a crash or a silently-dropped hit — `scan()` still records the `rg`-visible
  hit (kind == "rg" always covers every text file; kind == "astgrep" simply
  can't rule-ify that language).
- **Sweeping a live worktree mid-edit**: `scan()` opens files read-only via
  `rg`/`ast-grep` subprocesses and takes no lock; a file changing under a scan
  can only ever cost a stale hit line, never a write conflict, because nothing
  in this design ever writes to a non-current repo.
- **Likely next changes**: (1) a `--repo` filter to sweep a subset instead of
  the whole portfolio — `enumerate_repos()`'s `(repos, gaps)` return shape
  already supports filtering the `repos` list before `scan()`, no interface
  change needed; (2) auto-registering gap repos into the gita CSV on request —
  deliberately boxed out by this design (gaps are report-only, "never written
  into the CSV" is a Success Metric, not just a default), so that would be a
  new, explicitly-scoped PRD, not a flag on this one.

## Test strategy outline

`skills/sweep-fix/scripts/test_sweep.py`, pytest, fixtures via `tmp_path`:

- `resolve_rg()` / `resolve_ast_grep()`: monkeypatch `shutil.which` to return
  `None`, assert the mise/execpath fallback path is taken and a real
  subprocess-runnable path is returned; assert neither ever builds a bare
  `subprocess.run(["rg", ...])` call (pins the `executable=` requirement the
  PRD calls out as a required Error case test).
- `enumerate_repos()`: fixture CSV of 2 repos + a fixture on-disk tree with 3
  repos → asserts the registry repos plus `cwd` are returned, and exactly the
  1 on-disk-only repo is a gap line; a second case asserts a fixture
  `~/.buvis`-shaped bare repo's tracked files are listed via `ls-files -z`,
  not a directory walk.
- `scan()`: a fixture repo with 25 planted matches → 20 hit rows + a
  `suppressed[repo] == 5`; every row carries `file`/`line`.
- `verify_control()`: a deliberately-broken pattern (literal `\|`) over a
  corpus containing the control term → raises SystemExit with the unverified
  message, never reports zero hits silently.
- `render_report()`: extract the rendered rule block to a file and run
  `ast-grep scan --rule {file}` against a small fixture — asserts exit 0 and
  it finds the planted match (round-trips unedited, per the PRD's own
  acceptance criterion).
- End-to-end: `main()` against 3 fixture repos with a planted bug → the
  written report has exactly 3 `file:line` rows (PRD Phase 1 exit criteria).
- Read-only regression (PRD Phase 2 acceptance): run a sweep across 3 fixture
  repos, assert `git status --porcelain` is byte-identical in the two
  non-current repos before and after.
- Skill compliance (PRD Phase 2 acceptance): run
  `skills/create-skill/scripts/validate_skill.py skills/sweep-fix` and assert
  it exits 0 against the new `SKILL.md`.

## Review log

- non-blocker: `verify_control()`'s control-term contract can false-abort or
  silently no-op when the fix commit removed the pattern's only instance from
  `control_repo`'s live tree (the common case) — the design doesn't constrain
  how `SKILL.md` must pick `control_term` to avoid this, and the test only
  covers the "genuinely broken pattern" trigger, not this interaction.
- non-blocker: `scan()`'s per-repo `rg`/`ast-grep` subprocess calls have no
  timeout — one stuck repo can hang the whole sweep.
- non-blocker: Reuse inventory's grep-verification claims for the `~/.buvis`
  bare-repo helper search are citation errors — "`git-dir` confirmed present
  elsewhere via `collect_facts.py`" is wrong (that file has `git_dir`, the
  Python identifier, not the literal hyphenated string); the actual literal
  hit is `skills/create-skill/scripts/test_validate_skill.py:72` (a test
  fixture string, not a reusable helper). The underlying conclusion — no
  existing helper lists a bare repo's tracked files — still holds.
- non-blocker: `AST_GREP_LANGUAGES`'s comment overclaims "matches the
  languages loupe already ships rule packs for" — loupe's actual packs cover
  javascript/typescript/python/rust, not go; the `.go` entry has no loupe
  destination to paste into.
- question: `resolve_ast_grep()`'s doc cites the sibling shell function as
  `_resolve()`; the actual name in `skills/use-gemini/scripts/gemini-run.sh`
  is `resolve_bin()`.
- question: `main()`'s optional `--registry`/`--cwd` flags don't state their
  defaults (`GITA_CSV` and `Path.cwd()` respectively, implied but unstated).
- dispatch 1 (claude): cardinal-sin 0, blocker 2, non-blocker 4, question 2

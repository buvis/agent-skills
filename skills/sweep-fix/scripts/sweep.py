"""Resolve the rg and ast-grep binaries used by the sweep-fix skill."""
import csv
import functools
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


@functools.lru_cache()
def resolve_rg():
    """Resolve the path to invoke for `rg`.

    Returns the real `rg` binary if one is on PATH. Otherwise falls back to
    the claude binary (CLAUDE_CODE_EXECPATH, or ~/.local/bin/claude), which
    bundles ripgrep and dispatches based on argv[0].

    In this environment `rg` is a shell function, not a PATH binary, so a
    bare `subprocess.run(["rg", ...])` raises FileNotFoundError. Callers
    must instead pass the resolved path as `executable=` while keeping
    "rg" as argv[0]:

        subprocess.run(["rg", ...], executable=resolve_rg())

    The `executable=` argument is required exactly when the returned path
    is the claude-binary fallback, but the call above works unconditionally,
    so callers can always use it. Exits with status 1, naming both
    candidates checked, if neither resolves.
    """
    path = shutil.which("rg")
    if path:
        return path

    cc_bin = os.environ.get("CLAUDE_CODE_EXECPATH", "")
    if not (cc_bin and os.access(cc_bin, os.X_OK)):
        cc_bin = os.path.expanduser("~/.local/bin/claude")

    if os.access(cc_bin, os.X_OK):
        return cc_bin

    print(
        "Could not resolve rg: not on PATH and no claude binary found "
        f"(checked CLAUDE_CODE_EXECPATH and {cc_bin})",
        file=sys.stderr,
    )
    sys.exit(1)


@functools.lru_cache()
def resolve_ast_grep():
    """Resolve the path to invoke for `ast-grep`.

    Returns the real `ast-grep` binary if one is on PATH. Otherwise falls
    back to `mise which ast-grep` to locate a mise-managed install. Exits
    with status 1, naming both candidates checked, if neither resolves.
    """
    path = shutil.which("ast-grep")
    if path:
        return path

    if not shutil.which("mise"):
        print(
            "Could not resolve ast-grep: not on PATH and mise is not available",
            file=sys.stderr,
        )
        sys.exit(1)

    result = subprocess.run(
        ["mise", "which", "ast-grep"], capture_output=True, text=True
    )
    if result.returncode != 0:
        print(
            "Could not resolve ast-grep: not on PATH and `mise which ast-grep` failed",
            file=sys.stderr,
        )
        sys.exit(1)

    return result.stdout.strip()


PORTFOLIO_ROOT = Path.home() / "git" / "src" / "github.com"

GITA_CSV = Path.home() / ".config" / "gita" / "repos.csv"

BUVIS_BARE = {
    "git_dir": Path.home() / ".buvis",
    "work_tree": Path.home(),
}


def enumerate_repos(registry, cwd):
    """Enumerate the repos sweep should operate on.

    `registry` is a text file with one repo path per line (blank lines
    skipped). Returns `(repos, gaps)`:

    - `repos`: registered paths that have a `.git` dir, plus `cwd` if it is
      not already covered. If `cwd` is the buvis bare dotfiles work tree
      (`BUVIS_BARE["work_tree"]`), it is replaced by its tracked files
      (via `git ls-files` against `BUVIS_BARE["git_dir"]`) rather than the
      work tree directory itself, since a directory walk would not find
      files living outside the home-relative repo layout.
    - `gaps`: `.git` repos found on disk at `PORTFOLIO_ROOT/<org>/<repo>`
      that are missing from the registry, as path strings.

    The registry file is only ever read, never written.
    """
    registry = Path(registry)
    cwd = Path(cwd)

    registered = [Path(row[0].strip()) for row in csv.reader(registry.open()) if row and row[0].strip()]

    repos = [
        path
        for path in registered
        if (path / ".git").exists() or path == BUVIS_BARE["work_tree"]
    ]

    work_tree = BUVIS_BARE["work_tree"]
    if cwd == work_tree:
        git_dir = BUVIS_BARE["git_dir"]
        result = subprocess.run(
            ["git", f"--git-dir={git_dir}", f"--work-tree={work_tree}", "ls-files", "-z"],
            capture_output=True,
            text=True,
            check=True,
        )
        for rel in result.stdout.split("\0"):
            if rel:
                repos.append(work_tree / rel)
    elif cwd not in repos:
        repos.append(cwd)

    gaps = []
    if PORTFOLIO_ROOT.is_dir():
        for repo_dir in sorted(PORTFOLIO_ROOT.glob("*/*")):
            if repo_dir.is_dir() and (repo_dir / ".git").exists() and repo_dir not in repos:
                gaps.append(str(repo_dir))

    return repos, gaps


AST_GREP_LANGUAGES = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".rs": "rust",
    ".go": "go",
}


def _build_hit(repo, file, line, snippet):
    return {
        "repo": str(repo),
        "file": file,
        "line": line,
        "snippet": snippet,
        "lang": AST_GREP_LANGUAGES.get(Path(file).suffix),
    }


def _scan_rg(pattern, repo):
    result = subprocess.run(
        ["rg", "--json", pattern, "."],
        executable=resolve_rg(),
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"rg failed: {result.stderr}")
    hits = []
    for line in result.stdout.splitlines():
        event = json.loads(line)
        if event.get("type") != "match":
            continue
        data = event["data"]
        file = data["path"]["text"]
        hits.append(
            _build_hit(repo, file, data["line_number"], data["lines"]["text"].rstrip("\n"))
        )
    return hits


def _scan_astgrep(pattern, repo):
    result = subprocess.run(
        [resolve_ast_grep(), "run", "--pattern", pattern, "--json", "."],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"ast-grep failed: {result.stderr}")
    matches = json.loads(result.stdout) if result.stdout.strip() else []
    hits = []
    for match in matches:
        file = match["file"]
        hits.append(
            _build_hit(repo, file, match["range"]["start"]["line"] + 1, match["lines"])
        )
    return hits


def scan(pattern, kind, repos, cap=20):
    """Search `pattern` across `repos` using `kind` ("rg" or "astgrep").

    Read-only: never writes to a repo. Returns `(hits, suppressed)`. Each
    hit is a dict with `repo`, `file`, `line`, `snippet`, and `lang`
    (looked up in AST_GREP_LANGUAGES by file extension, None when unmapped).
    Hits are capped at `cap` per repo; `suppressed` maps `str(repo)` to the
    number of hits dropped beyond the cap, for repos that exceeded it only.
    """
    hits = []
    suppressed = {}
    for repo in repos:
        if kind == "rg":
            repo_hits = _scan_rg(pattern, repo)
        elif kind == "astgrep":
            repo_hits = _scan_astgrep(pattern, repo)
        else:
            raise ValueError(f"unknown kind: {kind!r}")

        if len(repo_hits) > cap:
            suppressed[str(repo)] = len(repo_hits) - cap
            repo_hits = repo_hits[:cap]

        hits.extend(repo_hits)

    return hits, suppressed


def verify_control(pattern, kind, control_repo, control_term):
    """Verify `pattern` actually matches in `control_repo` before trusting a
    sweep run elsewhere.

    Searches `control_repo` for `pattern`. If it finds hits, the pattern is
    confirmed working and this returns None. If it finds none, searches
    `control_repo` for `control_term` (a string known to be present when the
    pattern's intended target is present). If `control_term` also finds no
    hits, the control repo is inconclusive and this returns None. If
    `control_term` finds hits but `pattern` did not, `pattern` is broken
    (e.g. the Rust-regex `\\|` literal-pipe trap): prints a message naming
    `control_term` and `control_repo`, then exits with status 1.
    """
    hits, _suppressed = scan(pattern, kind, [control_repo])
    if hits:
        return None

    control_hits, _suppressed = scan(control_term, kind, [control_repo])
    if not control_hits:
        return None

    message = (
        f"unverified: control term {control_term!r} found hits in "
        f"{control_repo}, but pattern {pattern!r} found none there"
    )
    print(message, file=sys.stderr)
    exc = SystemExit(message)
    exc.code = 1
    raise exc

"""Resolve the rg and ast-grep binaries used by the sweep-fix skill."""
import csv
import functools
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

    registered = []
    for row in csv.reader(registry.open()):
        if row and row[0].strip():
            registered.append(Path(row[0].strip()))

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
        for org_dir in sorted(PORTFOLIO_ROOT.iterdir()):
            if not org_dir.is_dir():
                continue
            for repo_dir in sorted(org_dir.iterdir()):
                if (
                    repo_dir.is_dir()
                    and (repo_dir / ".git").exists()
                    and repo_dir not in repos
                ):
                    gaps.append(str(repo_dir))

    return repos, gaps

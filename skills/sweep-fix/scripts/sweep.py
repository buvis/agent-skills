"""Resolve the rg and ast-grep binaries used by the sweep-fix skill."""
import functools
import os
import shutil
import subprocess
import sys


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

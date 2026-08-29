"""Resolve the rg and ast-grep binaries used by the sweep-fix skill."""
import functools
import os
import shutil
import subprocess
import sys


@functools.lru_cache()
def resolve_rg():
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

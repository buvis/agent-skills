"""Resolve the highest-versioned audit-sessions parser from a cache root."""

import importlib.util
from pathlib import Path

PARSER_RELPATH = Path("skills/audit-sessions/scripts/parser.py")


class StaleParserError(RuntimeError):
    """Raised when no usable parser version can be resolved from the cache root."""


def resolve_parser(cache_root: Path):
    if not cache_root.is_dir():
        raise StaleParserError(f"cache root does not exist: {cache_root}")

    version_dirs = [d for d in cache_root.iterdir() if d.is_dir()]
    if not version_dirs:
        raise StaleParserError(f"no version directories found under {cache_root}")

    def version_key(version_dir):
        return tuple(int(part) for part in version_dir.name.split("."))

    winner = max(version_dirs, key=version_key)
    parser_path = winner / PARSER_RELPATH

    if not parser_path.is_file():
        raise StaleParserError(
            f"parser.py missing for resolved version {winner.name} at {parser_path}"
        )

    spec = importlib.util.spec_from_file_location("audit_sessions_parser", parser_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module, winner.name

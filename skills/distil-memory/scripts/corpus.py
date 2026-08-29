"""Resolve the highest-versioned audit-sessions parser from a cache root."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

# The one named constant the PRD's Risk "the plugin cache root moves" points
# at. Migrating claude-checkup to the agent-plugins standard is one edit here.
_CACHE_ROOT = Path.home() / ".claude" / "plugins" / "cache" / "buvis-plugins" / "claude-checkup"
_MIN_VERSION = "0.2.2"
_REQUIRED_PARSER_SYMBOLS = ("parse_session", "SessionData")


class StaleParserError(RuntimeError):
    """Raised by assert_contract() on a below-minimum or contract-broken parser."""


def _version_key(name: str) -> tuple[int, ...]:
    """`"0.2.2"` -> `(0, 2, 2)`. Non-numeric segments sort below every real
    version. Copied from `hooks/strunk-ruling-inject.py:_version_key` (that
    file lives under `~/.claude/hooks/`, outside this repo's import graph, so
    the ~4-line idiom is duplicated rather than imported)."""
    return tuple(int(part) if part.isdigit() else -1 for part in name.split("."))


def resolve_parser(cache_root: Path = _CACHE_ROOT) -> tuple[ModuleType, str]:
    """Import the highest installed claude-checkup version's parser.py.

    Returns (module, version_string). Raises StaleParserError if the cache
    root is missing/empty or the winning version has no parser.py at
    `skills/audit-sessions/scripts/parser.py`.
    """
    try:
        versions = [d for d in cache_root.iterdir() if d.is_dir()]
    except OSError:
        versions = []
    if not versions:
        raise StaleParserError(f"no claude-checkup versions found under {cache_root}")
    winner = max(versions, key=lambda d: _version_key(d.name))
    parser_path = winner / "skills" / "audit-sessions" / "scripts" / "parser.py"
    if not parser_path.is_file():
        raise StaleParserError(f"claude-checkup {winner.name} has no parser.py at {parser_path}")
    spec = importlib.util.spec_from_file_location("claude_checkup_parser", parser_path)
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(module)
    return module, winner.name

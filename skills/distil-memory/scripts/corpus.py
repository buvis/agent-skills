"""Resolve the highest-versioned audit-sessions parser from a cache root."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

# The one named constant the PRD's Risk "the plugin cache root moves" points
# at. Migrating claude-checkup to the agent-plugins standard is one edit here.
_CACHE_ROOT = Path.home() / ".claude" / "plugins" / "cache" / "buvis-plugins" / "claude-checkup"
_MIN_VERSION = "0.2.2"
_REQUIRED_PARSER_SYMBOLS = ("parse_session", "SessionData")
_PROJECTS_ROOT = Path.home() / ".claude" / "projects"


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


def assert_contract(version: str, parser_module: ModuleType, minimum: str = _MIN_VERSION) -> None:
    """Raise StaleParserError naming the resolved version and the minimum
    when `version < minimum`, or naming any of _REQUIRED_PARSER_SYMBOLS
    missing from `parser_module`. Message states the over-count consequence
    (claude-checkup d10ecb1's promptSource=="sdk" fix), not "parse failed"."""
    if _version_key(version) < _version_key(minimum):
        raise StaleParserError(
            f"claude-checkup {version} is older than the required {minimum} "
            "(the release carrying d10ecb1's promptSource=='sdk' fix) - "
            "the resolved parser over-counts user prompts by roughly 41%. "
            f"Install claude-checkup {minimum} or newer."
        )
    missing = [symbol for symbol in _REQUIRED_PARSER_SYMBOLS if not hasattr(parser_module, symbol)]
    if missing:
        raise StaleParserError(
            f"claude-checkup {version}'s parser.py is missing {missing} - "
            "it no longer matches this skill's contract."
        )


def select_transcripts(days: int = 30, project: str | None = None, all: bool = False) -> list[Path]:
    """Return the sorted list of transcript paths under _PROJECTS_ROOT that
    fall within the last `days` days, optionally restricted to project
    directories whose name ends with `project`. `all=True` skips the date
    filter entirely. A transcript is kept whenever its date can't be
    determined (parse_session() returns None, or SessionData.latest is
    None), since there's no evidence to justify dropping it."""
    module, version = resolve_parser()
    assert_contract(version, module)
    cutoff = None if all else datetime.now(timezone.utc) - timedelta(days=days)

    results = []
    for project_dir in _PROJECTS_ROOT.iterdir():
        if not project_dir.is_dir():
            continue
        if project is not None and not project_dir.name.endswith(project):
            continue
        for transcript in project_dir.glob("*.jsonl"):
            if cutoff is None:
                results.append(transcript)
                continue
            session_data = module.parse_session(transcript)
            if session_data is None or session_data.latest is None or session_data.latest >= cutoff:
                results.append(transcript)

    return sorted(results)

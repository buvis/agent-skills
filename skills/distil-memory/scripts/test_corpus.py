"""Tests for corpus.py, covering resolve_parser's version resolution and failure modes."""

from pathlib import Path

import corpus
import pytest

PARSER_RELPATH = Path("skills/audit-sessions/scripts/parser.py")


def write_parser(version_dir: Path, body: str = "def parse_session():\n    return 'stub'\n") -> None:
    parser_path = version_dir / PARSER_RELPATH
    parser_path.parent.mkdir(parents=True, exist_ok=True)
    parser_path.write_text(body)


def test_resolves_highest_dotted_version(tmp_path):
    write_parser(tmp_path / "0.2.1")
    write_parser(tmp_path / "0.2.2")

    module, version = corpus.resolve_parser(cache_root=tmp_path)

    assert version == "0.2.2"
    assert callable(module.parse_session)
    assert module.parse_session() == "stub"


def test_compares_version_segments_numerically_not_lexicographically(tmp_path):
    # Lexicographic string comparison would rank "0.2.2" above "0.2.10"
    # (since "0.2.10" < "0.2.2" as strings); numeric-dotted comparison must not.
    write_parser(tmp_path / "0.2.2")
    write_parser(tmp_path / "0.2.10")

    _, version = corpus.resolve_parser(cache_root=tmp_path)

    assert version == "0.2.10"


def test_raises_stale_parser_error_when_cache_root_does_not_exist(tmp_path):
    missing = tmp_path / "does-not-exist"

    with pytest.raises(corpus.StaleParserError):
        corpus.resolve_parser(cache_root=missing)


def test_raises_stale_parser_error_when_cache_root_has_no_version_dirs(tmp_path):
    with pytest.raises(corpus.StaleParserError):
        corpus.resolve_parser(cache_root=tmp_path)


def test_raises_stale_parser_error_when_winning_version_missing_parser_file(tmp_path):
    write_parser(tmp_path / "0.2.1")
    (tmp_path / "0.2.2").mkdir()  # highest version, but has no parser.py inside

    with pytest.raises(corpus.StaleParserError):
        corpus.resolve_parser(cache_root=tmp_path)


def test_stale_parser_error_is_a_runtime_error():
    assert issubclass(corpus.StaleParserError, RuntimeError)


def test_version_key_sorts_non_numeric_segments_below_real_versions():
    assert corpus._version_key("0.2.2") > corpus._version_key("0.2.dev")
    assert corpus._version_key("0.2.dev") == (0, 2, -1)

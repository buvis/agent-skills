"""Tests for corpus.py, covering resolve_parser's version resolution and failure modes."""

from pathlib import Path
from types import ModuleType

import corpus
import pytest

PARSER_RELPATH = Path("skills/audit-sessions/scripts/parser.py")
_STUB_PARSER_BODY = "def parse_session():\n    return 'stub'\n"


def write_parser(version_dir: Path, body: str = _STUB_PARSER_BODY) -> None:
    parser_path = version_dir / PARSER_RELPATH
    parser_path.parent.mkdir(parents=True, exist_ok=True)
    parser_path.write_text(body)


def test_resolve_parser_resolves_highest_dotted_version(tmp_path):
    write_parser(tmp_path / "0.2.1")
    write_parser(tmp_path / "0.2.2")

    module, version = corpus.resolve_parser(cache_root=tmp_path)

    assert version == "0.2.2"
    assert callable(module.parse_session)
    assert module.parse_session() == "stub"


def test_resolve_parser_compares_version_segments_numerically_not_lexicographically(tmp_path):
    # Lexicographic string comparison would rank "0.2.2" above "0.2.10"
    # (since "0.2.10" < "0.2.2" as strings); numeric-dotted comparison must not.
    write_parser(tmp_path / "0.2.2")
    write_parser(tmp_path / "0.2.10")

    _, version = corpus.resolve_parser(cache_root=tmp_path)

    assert version == "0.2.10"


def test_resolve_parser_raises_stale_parser_error_when_cache_root_does_not_exist(tmp_path):
    missing = tmp_path / "does-not-exist"

    with pytest.raises(corpus.StaleParserError):
        corpus.resolve_parser(cache_root=missing)


def test_resolve_parser_raises_stale_parser_error_when_cache_root_has_no_version_dirs(tmp_path):
    with pytest.raises(corpus.StaleParserError):
        corpus.resolve_parser(cache_root=tmp_path)


def test_resolve_parser_raises_stale_error_when_winner_missing_parser_file(tmp_path):
    write_parser(tmp_path / "0.2.1")
    (tmp_path / "0.2.2").mkdir()  # highest version, but has no parser.py inside

    with pytest.raises(corpus.StaleParserError):
        corpus.resolve_parser(cache_root=tmp_path)


def test_stale_parser_error_is_a_runtime_error():
    assert issubclass(corpus.StaleParserError, RuntimeError)


def test_version_key_sorts_non_numeric_segments_below_real_versions():
    assert corpus._version_key("0.2.2") > corpus._version_key("0.2.dev")
    assert corpus._version_key("0.2.dev") == (0, 2, -1)


def make_parser_module(*, has_parse_session=True, has_session_data=True):
    module = ModuleType("stub_parser")
    if has_parse_session:
        module.parse_session = lambda: None
    if has_session_data:
        module.SessionData = object()
    return module


def test_assert_contract_raises_stale_parser_error_when_version_is_below_minimum():
    module = make_parser_module()

    with pytest.raises(corpus.StaleParserError) as exc_info:
        corpus.assert_contract("0.2.1", module, minimum="0.2.2")

    assert str(exc_info.value) == (
        "claude-checkup 0.2.1 is older than the required 0.2.2 "
        "(the release carrying d10ecb1's promptSource=='sdk' fix) - "
        "the resolved parser over-counts user prompts by roughly 41%. "
        "Install claude-checkup 0.2.2 or newer."
    )


def test_assert_contract_does_not_raise_when_version_equals_minimum():
    module = make_parser_module()

    result = corpus.assert_contract("0.2.2", module, minimum="0.2.2")

    assert result is None


def test_assert_contract_does_not_raise_when_version_is_above_minimum():
    module = make_parser_module()

    result = corpus.assert_contract("0.3.0", module, minimum="0.2.2")

    assert result is None


def test_assert_contract_defaults_minimum_to_module_min_version_when_not_given():
    module = make_parser_module()

    with pytest.raises(corpus.StaleParserError):
        corpus.assert_contract("0.2.1", module)


def test_assert_contract_compares_versions_numerically_not_lexicographically():
    # Lexicographic string comparison would rank "0.2.2" above "0.2.10"
    # (since "0.2.10" < "0.2.2" as strings); numeric-dotted comparison must
    # treat 0.2.10 as newer than the 0.2.2 minimum and not raise.
    module = make_parser_module()

    result = corpus.assert_contract("0.2.10", module, minimum="0.2.2")

    assert result is None


def test_assert_contract_raises_stale_parser_error_naming_missing_parse_session():
    module = make_parser_module(has_parse_session=False)

    with pytest.raises(corpus.StaleParserError) as exc_info:
        corpus.assert_contract("0.3.0", module, minimum="0.2.2")

    message = str(exc_info.value)
    assert "0.3.0" in message
    assert "parse_session" in message


def test_assert_contract_raises_stale_parser_error_naming_missing_session_data():
    module = make_parser_module(has_session_data=False)

    with pytest.raises(corpus.StaleParserError) as exc_info:
        corpus.assert_contract("0.3.0", module, minimum="0.2.2")

    message = str(exc_info.value)
    assert "0.3.0" in message
    assert "SessionData" in message


def test_assert_contract_raises_stale_parser_error_naming_all_missing_symbols():
    module = make_parser_module(has_parse_session=False, has_session_data=False)

    with pytest.raises(corpus.StaleParserError) as exc_info:
        corpus.assert_contract("0.3.0", module, minimum="0.2.2")

    message = str(exc_info.value)
    assert "parse_session" in message
    assert "SessionData" in message


def test_assert_contract_does_not_raise_when_parser_module_has_all_required_symbols():
    module = make_parser_module(has_parse_session=True, has_session_data=True)

    result = corpus.assert_contract("0.2.2", module, minimum="0.2.2")

    assert result is None

"""Tests for corpus.py, covering resolve_parser's version resolution and failure modes."""

from datetime import datetime, timedelta, timezone
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


_DATACLASS_PARSER_BODY = (
    "from dataclasses import dataclass\n"
    "@dataclass(frozen=True)\n"
    "class SessionData:\n"
    "    latest: str\n"
    "def parse_session():\n"
    "    return SessionData(latest='x')\n"
)


def test_resolve_parser_imports_a_module_using_dataclass(tmp_path):
    # dataclass() resolves annotations via sys.modules[cls.__module__]; a
    # dynamic import that skips registering the module in sys.modules raises
    # AttributeError here even though a plain-function fixture succeeds.
    write_parser(tmp_path / "0.2.2", body=_DATACLASS_PARSER_BODY)

    module, _ = corpus.resolve_parser(cache_root=tmp_path)

    assert module.parse_session().latest == "x"


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


class FakeSessionData:
    """Stand-in for the real claude-checkup parser's SessionData: an object
    with `.earliest`/`.latest` datetime-or-None attributes."""

    def __init__(self, latest=None, earliest=None):
        self.latest = latest
        self.earliest = earliest


def make_transcript_parser_module(results_by_filename, *, version="0.3.0"):
    """A parser module stub whose parse_session(path) looks up its result by
    the transcript's filename, and which satisfies assert_contract()."""
    module = ModuleType("stub_transcript_parser")
    module.parse_session = lambda path: results_by_filename[Path(path).name]
    module.SessionData = FakeSessionData
    return module, version


def write_transcript(project_dir: Path, filename: str) -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = project_dir / filename
    transcript_path.write_text("")
    return transcript_path


def test_select_transcripts_keeps_transcripts_within_the_days_window(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path)
    project_dir = tmp_path / "aaaa-myproj"
    recent = write_transcript(project_dir, "recent.jsonl")
    write_transcript(project_dir, "old.jsonl")
    now = datetime.now(timezone.utc)
    module, version = make_transcript_parser_module(
        {
            "recent.jsonl": FakeSessionData(latest=now - timedelta(days=5)),
            "old.jsonl": FakeSessionData(latest=now - timedelta(days=40)),
        }
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    result = corpus.select_transcripts(days=30)

    assert result == [recent]


def test_select_transcripts_keeps_transcript_when_parse_session_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path)
    project_dir = tmp_path / "aaaa-myproj"
    normal = write_transcript(project_dir, "normal.jsonl")
    unparsable = write_transcript(project_dir, "unparsable.jsonl")
    now = datetime.now(timezone.utc)
    module, version = make_transcript_parser_module(
        {
            "normal.jsonl": FakeSessionData(latest=now - timedelta(days=1)),
            "unparsable.jsonl": None,
        }
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    result = corpus.select_transcripts(days=30)

    assert sorted(result) == sorted([normal, unparsable])


def test_select_transcripts_keeps_transcript_when_latest_is_none(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path)
    project_dir = tmp_path / "aaaa-myproj"
    normal = write_transcript(project_dir, "normal.jsonl")
    legacy = write_transcript(project_dir, "legacy.jsonl")
    now = datetime.now(timezone.utc)
    module, version = make_transcript_parser_module(
        {
            "normal.jsonl": FakeSessionData(latest=now - timedelta(days=1)),
            "legacy.jsonl": FakeSessionData(latest=None),
        }
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    result = corpus.select_transcripts(days=30)

    assert sorted(result) == sorted([normal, legacy])


def test_select_transcripts_project_filter_keeps_only_directories_ending_with_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path)
    target_dir = tmp_path / "aaaa-target"
    other_dir = tmp_path / "bbbb-other"
    target_transcript = write_transcript(target_dir, "session.jsonl")
    write_transcript(other_dir, "session.jsonl")
    now = datetime.now(timezone.utc)
    module, version = make_transcript_parser_module(
        {"session.jsonl": FakeSessionData(latest=now - timedelta(days=1))}
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    result = corpus.select_transcripts(project="target")

    assert result == [target_transcript]


def test_select_transcripts_project_filter_with_no_matching_directories_returns_empty_list(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path)
    project_dir = tmp_path / "aaaa-something"
    write_transcript(project_dir, "session.jsonl")
    now = datetime.now(timezone.utc)
    module, version = make_transcript_parser_module(
        {"session.jsonl": FakeSessionData(latest=now - timedelta(days=1))}
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    result = corpus.select_transcripts(project="nomatch")

    assert result == []


def test_select_transcripts_all_returns_every_transcript_regardless_of_date(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path)
    project_dir = tmp_path / "aaaa-myproj"
    recent = write_transcript(project_dir, "recent.jsonl")
    ancient = write_transcript(project_dir, "ancient.jsonl")
    now = datetime.now(timezone.utc)
    module, version = make_transcript_parser_module(
        {
            "recent.jsonl": FakeSessionData(latest=now - timedelta(days=1)),
            "ancient.jsonl": FakeSessionData(latest=now - timedelta(days=400)),
        }
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    result = corpus.select_transcripts(all=True, days=30)

    assert sorted(result) == sorted([recent, ancient])


def test_select_transcripts_returns_a_sorted_list(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path)
    # Create the alphabetically-later directory/file first, so a result that
    # merely preserves filesystem iteration order (rather than sorting)
    # would come back as [second, first] instead of [first, second].
    project_b = tmp_path / "bbbb-projB"
    project_a = tmp_path / "aaaa-projA"
    second = write_transcript(project_b, "z.jsonl")
    first = write_transcript(project_a, "a.jsonl")
    now = datetime.now(timezone.utc)
    module, version = make_transcript_parser_module(
        {
            "z.jsonl": FakeSessionData(latest=now - timedelta(days=1)),
            "a.jsonl": FakeSessionData(latest=now - timedelta(days=1)),
        }
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    result = corpus.select_transcripts(days=30)

    assert result == [first, second]


def test_select_transcripts_propagates_stale_parser_error_from_resolve_parser(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path)

    def raise_stale(*args, **kwargs):
        raise corpus.StaleParserError("no claude-checkup versions found")

    monkeypatch.setattr(corpus, "resolve_parser", raise_stale)

    with pytest.raises(corpus.StaleParserError):
        corpus.select_transcripts()


def test_select_transcripts_propagates_stale_parser_error_from_assert_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path)
    module = ModuleType("incomplete_parser")
    module.parse_session = lambda path: None
    # module.SessionData deliberately absent -> assert_contract() raises
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, "0.3.0"))

    with pytest.raises(corpus.StaleParserError):
        corpus.select_transcripts()


def test_select_transcripts_raises_stale_parser_error_naming_missing_path_when_transcripts_root_does_not_exist(
    tmp_path, monkeypatch
):
    missing = tmp_path / "does-not-exist"
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", missing)
    module, version = make_transcript_parser_module({})
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    with pytest.raises(corpus.StaleParserError) as exc_info:
        corpus.select_transcripts()

    assert str(missing) in str(exc_info.value)


def test_select_transcripts_resolves_and_contract_checks_the_parser_itself_when_called_with_only_its_three_published_arguments(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path)
    project_dir = tmp_path / "aaaa-myproj"
    transcript = write_transcript(project_dir, "session.jsonl")
    now = datetime.now(timezone.utc)
    module, version = make_transcript_parser_module(
        {"session.jsonl": FakeSessionData(latest=now - timedelta(days=1))}
    )
    calls = []

    def counting_resolve(*args, **kwargs):
        calls.append((args, kwargs))
        return module, version

    monkeypatch.setattr(corpus, "resolve_parser", counting_resolve)

    result = corpus.select_transcripts(days=30, all=False, project=None)

    assert result == [transcript]
    assert len(calls) == 1

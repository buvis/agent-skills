"""Tests for portable.py: transcript paths written without the operator's home
prefix, and read back to the same local file."""

import portable
import pytest

_OPERATOR = "fake-operator-7f3"


@pytest.fixture
def home(tmp_path, isolate_home):
    path = tmp_path / _OPERATOR
    path.mkdir()
    isolate_home(path)
    return path


def test_portable_text_writes_a_path_under_the_home_home_relative_with_forward_slashes(home):
    transcript = home / ".claude" / "projects" / "proj" / "session.jsonl"

    assert portable.portable_text(str(transcript)) == "~/.claude/projects/proj/session.jsonl"


def test_portable_text_matches_the_home_by_whole_components_not_by_prefix(home):
    sibling = home.parent / f"{_OPERATOR}-other" / "session.jsonl"

    assert portable.portable_text(str(sibling)) == str(sibling)


@pytest.mark.parametrize("text", ["t.jsonl", "~/.claude/projects/proj/session.jsonl"])
def test_portable_text_leaves_relative_and_already_portable_text_unchanged(home, text):
    assert portable.portable_text(text) == text


def test_portable_text_leaves_a_path_outside_the_home_unchanged(home, tmp_path_factory):
    outside = tmp_path_factory.mktemp("elsewhere") / "session.jsonl"

    assert portable.portable_text(str(outside)) == str(outside)


def test_local_path_reads_a_home_relative_record_back_to_the_same_file(home):
    transcript = home / ".claude" / "projects" / "proj" / "session.jsonl"

    assert portable.local_path(portable.portable_text(str(transcript))) == transcript


def test_local_path_takes_a_legacy_absolute_record_as_written(home):
    transcript = home / ".claude" / "projects" / "proj" / "session.jsonl"

    assert portable.local_path(str(transcript)) == transcript

"""Tests for write.py: an index holding several lines for one stem (left by the
old always-append rule) resolves to exactly one current pointer line."""

import write

from write_test_helpers import _entry, _file_text, store_path

CURRENT = "- [Widget fact](widget-fact.md) — keeps facts about widgets straight"
STALE = "- [Widget fact](widget-fact.md) — an out of date hook"
BEFORE = "- [Alpha](alpha.md) — first unrelated line"
AFTER = "- [Omega](omega.md) — last unrelated line"


def _setup(store_path, lines):
    store_path.mkdir()
    file_text = _file_text(name="widget-fact", description="keeps facts about widgets straight")
    (store_path / "widget-fact.md").write_text(file_text)
    (store_path / "MEMORY.md").write_text("".join(f"{line}\n" for line in lines))
    return _entry(name="widget-fact", kind="new", file_text=file_text)


def _index_lines(store_path):
    return (store_path / "MEMORY.md").read_text().splitlines()


def _widget_lines(store_path):
    return [line for line in _index_lines(store_path) if "(widget-fact.md)" in line]


def _other_lines(store_path):
    return [line for line in _index_lines(store_path) if "(widget-fact.md)" not in line]


def test_append_pointer_collapses_a_stale_then_current_pair_to_one_current_line_keeping_other_lines(
    store_path,
):
    entry = _setup(store_path, [BEFORE, STALE, CURRENT, AFTER])

    written = write.append_pointer(store_path, entry)

    assert written == CURRENT
    assert _widget_lines(store_path) == [CURRENT]
    assert _other_lines(store_path) == [BEFORE, AFTER]


def test_published_is_false_and_append_pointer_collapses_a_current_then_stale_pair_to_one_current_line(
    store_path,
):
    entry = _setup(store_path, [BEFORE, CURRENT, STALE, AFTER])

    assert write.published(entry, store_path) is False
    written = write.append_pointer(store_path, entry)

    assert written == CURRENT
    assert _widget_lines(store_path) == [CURRENT]
    assert _other_lines(store_path) == [BEFORE, AFTER]


def test_append_pointer_collapses_two_identical_current_lines_then_is_idempotent(store_path):
    entry = _setup(store_path, [BEFORE, CURRENT, CURRENT])

    first = write.append_pointer(store_path, entry)

    assert first == CURRENT
    assert _widget_lines(store_path) == [CURRENT]
    assert _other_lines(store_path) == [BEFORE]
    collapsed_bytes = (store_path / "MEMORY.md").read_bytes()

    second = write.append_pointer(store_path, entry)

    assert second is None
    assert (store_path / "MEMORY.md").read_bytes() == collapsed_bytes
    assert write.published(entry, store_path) is True


def test_append_pointer_returns_none_and_writes_nothing_when_exactly_one_current_line_exists(
    store_path,
):
    entry = _setup(store_path, [BEFORE, CURRENT, AFTER])
    before_bytes = (store_path / "MEMORY.md").read_bytes()

    written = write.append_pointer(store_path, entry)

    assert written is None
    assert (store_path / "MEMORY.md").read_bytes() == before_bytes
    assert write.published(entry, store_path) is True

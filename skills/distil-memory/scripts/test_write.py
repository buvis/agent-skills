"""Tests for write.py: writing an approved proposal's memory file into a
memory store and upserting the store's MEMORY.md pointer line."""

import io
import json
import sys
from pathlib import Path

import dedup
import docket
import proposal
import write

import pytest


def _file_text(name="widget-fact", description="a fact worth keeping", body="Body text."):
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "metadata:\n"
        "  type: project\n"
        "---\n\n"
        f"{body}\n"
    )


def _entry(name="widget-fact", kind="new", file_text=None, existing_text=None):
    return {
        "name": name,
        "kind": kind,
        "file_text": file_text if file_text is not None else _file_text(name=name),
        "existing_text": existing_text,
    }


@pytest.fixture
def store_path(tmp_path):
    return tmp_path / "memory"


def test_write_memory_writes_new_entry_to_a_file_named_after_the_sanitised_name(store_path):
    store_path.mkdir()
    entry = _entry(name="Widget Fact", kind="new", file_text=_file_text(name="Widget Fact"))

    written = write.write_memory(entry, store_path)

    stem = proposal.sanitise_name("Widget Fact")
    assert written == store_path / f"{stem}.md"
    assert written.read_text() == entry["file_text"]


def test_write_memory_new_raises_and_does_not_touch_the_file_when_the_target_already_exists(
    store_path,
):
    store_path.mkdir()
    (store_path / "widget-fact.md").write_text("original content")
    entry = _entry(name="widget-fact", kind="new")

    with pytest.raises(write.WriteError):
        write.write_memory(entry, store_path)

    assert (store_path / "widget-fact.md").read_text() == "original content"


def test_write_memory_update_overwrites_the_existing_target_file(store_path):
    store_path.mkdir()
    (store_path / "widget-fact.md").write_text("old content")
    new_text = _file_text(name="widget-fact", description="updated description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text="old content"
    )

    written = write.write_memory(entry, store_path)

    assert written == store_path / "widget-fact.md"
    assert written.read_text() == new_text


def test_write_memory_update_raises_when_the_target_file_is_absent(store_path):
    store_path.mkdir()
    entry = _entry(name="widget-fact", kind="update widget-fact")

    with pytest.raises(write.WriteError):
        write.write_memory(entry, store_path)

    assert not (store_path / "widget-fact.md").exists()


def test_write_memory_raises_and_creates_nothing_when_the_store_path_does_not_exist(store_path):
    entry = _entry(name="widget-fact", kind="new")

    with pytest.raises(write.WriteError):
        write.write_memory(entry, store_path)

    assert not store_path.exists()


def test_write_memory_update_targets_the_file_named_by_kind_even_when_file_texts_own_name_field_differs(
    store_path,
):
    store_path.mkdir()
    (store_path / "widget-fact.md").write_text("old content")
    new_text = _file_text(name="totally-different-name", description="updated description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text="old content"
    )

    written = write.write_memory(entry, store_path)

    assert written == store_path / "widget-fact.md"
    assert written.read_text() == new_text
    assert not (store_path / "totally-different-name.md").exists()


def test_append_pointer_new_creates_memory_md_with_one_parseable_line_when_it_is_absent(store_path):
    store_path.mkdir()
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="keeps facts about widgets straight"),
    )

    line = write.append_pointer(store_path, entry)

    assert line == "- [Widget fact](widget-fact.md) — keeps facts about widgets straight"
    index_text = (store_path / "MEMORY.md").read_text()
    assert index_text.count("widget-fact.md") == 1
    parsed = dedup.parse_index(index_text)
    assert parsed["widget-fact"] == "Widget fact keeps facts about widgets straight"


def test_append_pointer_new_appends_after_existing_lines_without_disturbing_them(store_path):
    store_path.mkdir()
    existing_line = "- [Other thing](other-thing.md) — something unrelated"
    (store_path / "MEMORY.md").write_text(existing_line + "\n")
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="keeps facts about widgets straight"),
    )

    line = write.append_pointer(store_path, entry)

    lines = (store_path / "MEMORY.md").read_text().splitlines()
    assert lines == [existing_line, line]


def test_append_pointer_new_always_appends_even_when_a_line_for_the_same_stem_already_exists(
    store_path,
):
    store_path.mkdir()
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Widget fact](widget-fact.md) — a stale line\n")
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="a fresh description"),
    )

    line = write.append_pointer(store_path, entry)

    lines = index_path.read_text().splitlines()
    assert lines == ["- [Widget fact](widget-fact.md) — a stale line", line]


def test_append_pointer_title_replaces_hyphens_with_spaces_and_capitalises_only_the_first_letter(
    store_path,
):
    store_path.mkdir()
    entry = _entry(
        name="queue-cursor-is-lifetime",
        kind="new",
        file_text=_file_text(name="queue-cursor-is-lifetime", description="the cursor never resets"),
    )

    line = write.append_pointer(store_path, entry)

    assert line == "- [Queue cursor is lifetime](queue-cursor-is-lifetime.md) — the cursor never resets"


def test_append_pointer_new_names_the_pointer_after_the_sanitised_stem_not_the_raw_name(store_path):
    store_path.mkdir()
    entry = _entry(
        name="Widget Fact",
        kind="new",
        file_text=_file_text(name="Widget Fact", description="keeps facts about widgets straight"),
    )

    line = write.append_pointer(store_path, entry)

    assert line == "- [Widget fact](widget-fact.md) — keeps facts about widgets straight"
    index_text = (store_path / "MEMORY.md").read_text()
    parsed = dedup.parse_index(index_text)
    assert parsed["widget-fact"] == "Widget fact keeps facts about widgets straight"


def test_append_pointer_update_returns_none_and_leaves_memory_md_unchanged_when_description_is_identical(
    store_path,
):
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="keeps facts about widgets straight")
    index_path = store_path / "MEMORY.md"
    index_path.write_text(
        "- [Something](something.md) — unrelated\n"
        "- [Widget fact](widget-fact.md) — keeps facts about widgets straight\n"
        "- [Another](another.md) — also unrelated\n"
    )
    original_bytes = index_path.read_bytes()
    new_text = _file_text(
        name="widget-fact", description="keeps facts about widgets straight", body="New body."
    )
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )

    result = write.append_pointer(store_path, entry)

    assert result is None
    assert index_path.read_bytes() == original_bytes


def test_append_pointer_update_replaces_the_existing_line_in_place_when_description_differs(
    store_path,
):
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="old description")
    index_path = store_path / "MEMORY.md"
    index_path.write_text(
        "- [Something](something.md) — unrelated\n"
        "- [Widget fact](widget-fact.md) — old description\n"
        "- [Another](another.md) — also unrelated\n"
    )
    new_text = _file_text(name="widget-fact", description="new, more accurate description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )

    line = write.append_pointer(store_path, entry)

    assert line == "- [Widget fact](widget-fact.md) — new, more accurate description"
    lines = index_path.read_text().splitlines()
    assert lines == [
        "- [Something](something.md) — unrelated",
        line,
        "- [Another](another.md) — also unrelated",
    ]


def test_append_pointer_update_replaces_the_line_named_by_kind_even_when_file_texts_own_name_field_differs(
    store_path,
):
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="old description")
    index_path = store_path / "MEMORY.md"
    index_path.write_text(
        "- [Something](something.md) — unrelated\n"
        "- [Widget fact](widget-fact.md) — old description\n"
        "- [Another](another.md) — also unrelated\n"
    )
    new_text = _file_text(name="totally-different-name", description="new, more accurate description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )

    line = write.append_pointer(store_path, entry)

    assert line == "- [Widget fact](widget-fact.md) — new, more accurate description"
    lines = index_path.read_text().splitlines()
    assert lines == [
        "- [Something](something.md) — unrelated",
        line,
        "- [Another](another.md) — also unrelated",
    ]
    assert not any("totally-different-name" in existing_line for existing_line in lines)


def test_append_pointer_update_appends_when_description_differs_but_no_existing_line_matches_the_stem(
    store_path,
):
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="old description")
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Something](something.md) — unrelated\n")
    new_text = _file_text(name="widget-fact", description="new description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )

    line = write.append_pointer(store_path, entry)

    lines = index_path.read_text().splitlines()
    assert lines == ["- [Something](something.md) — unrelated", line]


def test_new_proposal_written_file_passes_the_frontmatter_contract_and_exactly_one_line_is_appended(
    store_path,
):
    store_path.mkdir()
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="keeps facts about widgets straight"),
    )

    written = write.write_memory(entry, store_path)
    line = write.append_pointer(store_path, entry)

    written_proposal = proposal.Proposal(
        file_text=written.read_text(),
        evidence=proposal.Evidence(transcript=Path("t.jsonl"), line_no=1, text="evidence"),
    )
    proposal.validate(written_proposal)

    index_text = (store_path / "MEMORY.md").read_text()
    assert index_text.count("widget-fact.md") == 1
    assert line in index_text


def test_update_proposal_replaces_the_named_file_and_leaves_memory_md_unchanged_when_description_is_unchanged(
    store_path,
):
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="keeps facts about widgets straight")
    (store_path / "widget-fact.md").write_text(old_text)
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Widget fact](widget-fact.md) — keeps facts about widgets straight\n")
    original_index_bytes = index_path.read_bytes()
    new_text = _file_text(
        name="widget-fact", description="keeps facts about widgets straight", body="Updated body."
    )
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )

    written = write.write_memory(entry, store_path)
    result = write.append_pointer(store_path, entry)

    assert written.read_text() == new_text
    assert result is None
    assert index_path.read_bytes() == original_index_bytes


def test_write_error_is_a_value_error():
    assert issubclass(write.WriteError, ValueError)


# main() CLI wiring. write.main reads its one entry from stdin, so every
# test below installs a fake stdin with monkeypatch instead of a subprocess
# pipe, and every --store is tmp_path-derived.


def test_main_write_reads_the_entry_from_stdin_shaped_like_docket_next_and_writes_it_and_upserts_the_pointer(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    docket.save(
        [
            {
                "name": "widget-fact",
                "kind": "new",
                "transcript": "t.jsonl",
                "line_no": 1,
                "evidence_text": "evidence for widget",
                "file_text": _file_text(
                    name="widget-fact", description="keeps facts about widgets straight"
                ),
                "existing_text": None,
            }
        ]
    )
    docket.main(["next"])
    entry_json = capsys.readouterr().out.strip()

    store_path = tmp_path / "memory"
    store_path.mkdir()
    monkeypatch.setattr(sys, "stdin", io.StringIO(entry_json))

    exit_code = write.main(["write", "--store", str(store_path)])

    assert exit_code == 0
    written_path = store_path / "widget-fact.md"
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert lines[0] == str(written_path)
    assert lines[1] == "- [Widget fact](widget-fact.md) — keeps facts about widgets straight"
    assert written_path.read_text() == _file_text(
        name="widget-fact", description="keeps facts about widgets straight"
    )


def test_main_write_prints_memory_md_unchanged_on_the_second_line_when_the_pointer_does_not_need_to_change(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    store_path = tmp_path / "memory"
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="keeps facts about widgets straight")
    (store_path / "widget-fact.md").write_text(old_text)
    (store_path / "MEMORY.md").write_text(
        "- [Widget fact](widget-fact.md) — keeps facts about widgets straight\n"
    )
    new_text = _file_text(
        name="widget-fact", description="keeps facts about widgets straight", body="Updated body."
    )
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    exit_code = write.main(["write", "--store", str(store_path)])

    assert exit_code == 0
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert lines[0] == str(store_path / "widget-fact.md")
    assert lines[1] == "MEMORY.md: unchanged"
    assert (store_path / "widget-fact.md").read_text() == new_text


def test_main_write_reports_the_write_errors_message_to_stderr_and_returns_one_when_the_store_path_does_not_exist(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    missing_store = tmp_path / "does-not-exist"
    entry = _entry(name="widget-fact", kind="new")
    try:
        write.write_memory(entry, missing_store)
    except write.WriteError as exc:
        expected_message = str(exc)
    else:
        pytest.fail("expected write.write_memory to raise WriteError for a missing store path")

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    exit_code = write.main(["write", "--store", str(missing_store)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert not missing_store.exists()


def test_main_write_reports_the_write_errors_message_to_stderr_and_returns_one_when_the_new_target_already_exists(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    store_path = tmp_path / "memory"
    store_path.mkdir()
    (store_path / "widget-fact.md").write_text("original content")
    entry = _entry(name="widget-fact", kind="new")
    try:
        write.write_memory(entry, store_path)
    except write.WriteError as exc:
        expected_message = str(exc)
    else:
        pytest.fail("expected write.write_memory to raise WriteError for an existing new target")

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    exit_code = write.main(["write", "--store", str(store_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert (store_path / "widget-fact.md").read_text() == "original content"


# Crash safety: every write this module performs must be atomic, so a process
# dying during the final move step leaves the target holding its complete
# previous content, never a partial write, and no stray temp file behind.


def _raise_replace(*args, **kwargs):
    raise OSError("boom")


def test_append_pointer_leaves_memory_md_fully_intact_when_the_move_fails_appending_a_new_line(
    store_path, monkeypatch
):
    store_path.mkdir()
    index_path = store_path / "MEMORY.md"
    original_text = (
        "- [Something](something.md) — unrelated\n"
        "- [Another](another.md) — also unrelated\n"
        "- [Third thing](third-thing.md) — a third pointer\n"
    )
    index_path.write_text(original_text)
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="keeps facts about widgets straight"),
    )
    monkeypatch.setattr(Path, "replace", _raise_replace)

    with pytest.raises(Exception):
        write.append_pointer(store_path, entry)

    assert index_path.read_text() == original_text
    assert [p.name for p in store_path.iterdir()] == ["MEMORY.md"]


def test_append_pointer_leaves_memory_md_fully_intact_when_the_move_fails_replacing_a_line_in_place(
    store_path, monkeypatch
):
    store_path.mkdir()
    index_path = store_path / "MEMORY.md"
    original_text = (
        "- [Something](something.md) — unrelated\n"
        "- [Widget fact](widget-fact.md) — old description\n"
        "- [Another](another.md) — also unrelated\n"
    )
    index_path.write_text(original_text)
    old_text = _file_text(name="widget-fact", description="old description")
    new_text = _file_text(name="widget-fact", description="new, more accurate description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )
    monkeypatch.setattr(Path, "replace", _raise_replace)

    with pytest.raises(Exception):
        write.append_pointer(store_path, entry)

    assert index_path.read_text() == original_text
    assert [p.name for p in store_path.iterdir()] == ["MEMORY.md"]


def test_write_memory_update_leaves_the_existing_file_fully_intact_when_the_move_fails(
    store_path, monkeypatch
):
    store_path.mkdir()
    target_path = store_path / "widget-fact.md"
    original_text = _file_text(name="widget-fact", description="old description")
    target_path.write_text(original_text)
    new_text = _file_text(name="widget-fact", description="new description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=original_text
    )
    monkeypatch.setattr(Path, "replace", _raise_replace)

    with pytest.raises(Exception):
        write.write_memory(entry, store_path)

    assert target_path.read_text() == original_text
    assert [p.name for p in store_path.iterdir()] == ["widget-fact.md"]


def _raise_write_text(*args, **kwargs):
    raise OSError("boom")


def test_append_pointer_leaves_no_leftover_tmp_file_when_the_write_step_itself_fails(
    store_path, monkeypatch
):
    store_path.mkdir()
    index_path = store_path / "MEMORY.md"
    original_text = "- [Something](something.md) — unrelated\n"
    index_path.write_text(original_text)
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="keeps facts about widgets straight"),
    )
    monkeypatch.setattr(Path, "write_text", _raise_write_text)

    with pytest.raises(Exception):
        write.append_pointer(store_path, entry)

    assert [p.name for p in store_path.iterdir()] == ["MEMORY.md"]

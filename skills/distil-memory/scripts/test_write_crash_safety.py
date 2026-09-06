"""Tests for write.py: the crash safety of its atomic writes, and the rollback
that puts the store back when the MEMORY.md step fails after the memory file
has already landed."""

import io
import json
import os
import sys
import uuid
from pathlib import Path

import proposal
import write

import pytest

from write_test_helpers import _entry, _file_text, _parser_message, store_path


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


def test_write_memory_rejects_malformed_file_text_before_it_reaches_the_write_step(
    store_path, monkeypatch
):
    store_path.mkdir()
    malformed = "---\nname: [unclosed\n---\n\nBody.\n"
    parser_message = _parser_message(malformed)
    entry = _entry(name="widget-fact", kind="new", file_text=malformed)
    monkeypatch.setattr(Path, "write_text", _raise_write_text)

    with pytest.raises(write.WriteError) as raised:
        write.write_memory(entry, store_path)

    assert parser_message in str(raised.value)
    assert isinstance(raised.value.__cause__, proposal.ProposalError)
    assert list(store_path.iterdir()) == []


def test_an_index_that_cannot_be_read_leaves_no_memory_file_behind(store_path, monkeypatch):
    store_path.mkdir()
    unrelated_path = store_path / "other-thing.md"
    unrelated_text = _file_text(name="other-thing", description="something unrelated")
    unrelated_path.write_text(unrelated_text)
    (store_path / "MEMORY.md").mkdir()
    entry = _entry(name="widget-fact")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    assert not (store_path / "widget-fact.md").exists()
    # the run gives up on a store it cannot index, it does not clear it out
    assert unrelated_path.read_text() == unrelated_text
    assert (store_path / "MEMORY.md").is_dir()
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "other-thing.md"]


# Writing a memory and updating MEMORY.md is one operation: either both land or
# neither does. The faults below fail only the index step, so the memory file is
# already on disk when the failure arrives and the store has to be put back.

_REAL_REPLACE = Path.replace
_REAL_PATH_UNLINK = Path.unlink
_REAL_OS_UNLINK = os.unlink
_REAL_OS_REMOVE = os.remove


def _replace_failing_on_index(fault_message):
    """Fail only the move that puts content at MEMORY.md; let every other move run.

    The caller mints a fault message unique to its own run, so stderr can only
    carry it by reporting the exception that actually arrived.
    """

    def _replace(self, target, *args, **kwargs):
        if Path(target).name == "MEMORY.md":
            raise OSError(fault_message)
        return _REAL_REPLACE(self, target, *args, **kwargs)

    return _replace


def _break_removal_of_the_memory_file(monkeypatch, fault_message):
    """Make deleting widget-fact.md impossible, whichever call the rollback uses.

    The refusal reads like a real unlink failure: it carries the path it
    refused, so whoever reports it also names the file left behind.
    """

    def _refuse_path_unlink(self, *args, **kwargs):
        if self.name == "widget-fact.md":
            raise OSError(f"{fault_message}: {self}")
        return _REAL_PATH_UNLINK(self, *args, **kwargs)

    def _refuse_os_unlink(path, *args, **kwargs):
        if Path(path).name == "widget-fact.md":
            raise OSError(f"{fault_message}: {path}")
        return _REAL_OS_UNLINK(path, *args, **kwargs)

    def _refuse_os_remove(path, *args, **kwargs):
        if Path(path).name == "widget-fact.md":
            raise OSError(f"{fault_message}: {path}")
        return _REAL_OS_REMOVE(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", _refuse_path_unlink)
    monkeypatch.setattr(os, "unlink", _refuse_os_unlink)
    monkeypatch.setattr(os, "remove", _refuse_os_remove)


def test_main_write_removes_only_the_new_memory_file_when_the_pointer_write_fails_and_a_retry_then_succeeds(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    unrelated_path = store_path / "other-thing.md"
    unrelated_text = _file_text(name="other-thing", description="something unrelated")
    unrelated_path.write_text(unrelated_text)
    index_path = store_path / "MEMORY.md"
    unrelated_line = "- [Other thing](other-thing.md) — something unrelated"
    index_path.write_text(unrelated_line + "\n")
    original_index_bytes = index_path.read_bytes()
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="keeps facts about widgets straight"),
    )
    index_fault = f"index boom {uuid.uuid4()}"
    monkeypatch.setattr(Path, "replace", _replace_failing_on_index(index_fault))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    failed = capsys.readouterr()
    assert index_fault in failed.err
    assert "Traceback" not in failed.err
    assert failed.out == ""
    # only the file this run created goes away: the memories the store already
    # held, and the index itself, come through byte for byte
    assert not (store_path / "widget-fact.md").exists()
    assert unrelated_path.read_text() == unrelated_text
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "other-thing.md"]

    monkeypatch.setattr(Path, "replace", _REAL_REPLACE)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    retry_status = write.main(["write", "--store", str(store_path)])

    assert retry_status == 0
    retried = capsys.readouterr()
    lines = retried.out.splitlines()
    assert lines[0] == str(store_path / "widget-fact.md")
    assert lines[1] == "- [Widget fact](widget-fact.md) — keeps facts about widgets straight"
    assert (store_path / "widget-fact.md").read_text() == entry["file_text"]
    assert index_path.read_text().splitlines() == [unrelated_line, lines[1]]


def test_main_write_restores_the_updated_targets_original_text_and_the_index_when_the_pointer_write_fails_and_a_retry_then_succeeds(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    target_path = store_path / "widget-fact.md"
    original_text = _file_text(name="widget-fact", description="old description")
    target_path.write_text(original_text)
    index_path = store_path / "MEMORY.md"
    index_path.write_text(
        "- [Something](something.md) — unrelated\n"
        "- [Widget fact](widget-fact.md) — old description\n"
    )
    original_index_bytes = index_path.read_bytes()
    new_text = _file_text(name="widget-fact", description="new, more accurate description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=original_text
    )
    index_fault = f"index boom {uuid.uuid4()}"
    monkeypatch.setattr(Path, "replace", _replace_failing_on_index(index_fault))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    failed = capsys.readouterr()
    assert index_fault in failed.err
    assert "Traceback" not in failed.err
    assert failed.out == ""
    assert target_path.read_text() == original_text
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "widget-fact.md"]

    monkeypatch.setattr(Path, "replace", _REAL_REPLACE)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    retry_status = write.main(["write", "--store", str(store_path)])

    assert retry_status == 0
    retried = capsys.readouterr()
    lines = retried.out.splitlines()
    assert lines[0] == str(target_path)
    assert lines[1] == "- [Widget fact](widget-fact.md) — new, more accurate description"
    assert target_path.read_text() == new_text
    assert index_path.read_text().splitlines() == [
        "- [Something](something.md) — unrelated",
        "- [Widget fact](widget-fact.md) — new, more accurate description",
    ]


def test_main_write_restores_the_target_named_by_kind_when_the_pointer_write_fails_even_when_the_file_texts_own_name_field_differs(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    target_path = store_path / "queue-cursor.md"
    original_text = _file_text(name="queue-cursor", description="old description")
    target_path.write_text(original_text)
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Queue cursor](queue-cursor.md) — old description\n")
    original_index_bytes = index_path.read_bytes()
    new_text = _file_text(name="widget-fact", description="new, more accurate description")
    entry = _entry(
        name="queue-cursor",
        kind="update queue-cursor",
        file_text=new_text,
        existing_text=original_text,
    )
    index_fault = f"index boom {uuid.uuid4()}"
    monkeypatch.setattr(Path, "replace", _replace_failing_on_index(index_fault))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    assert index_fault in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    # the file kind named is the file that has to come back, and the name the
    # file_text carries never becomes a path of its own
    assert target_path.read_text() == original_text
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "queue-cursor.md"]


def test_main_write_restores_the_targets_bytes_from_disk_when_the_pointer_write_fails_and_the_entrys_existing_text_is_stale(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    target_path = store_path / "widget-fact.md"
    text_on_disk = _file_text(name="widget-fact", description="what the store really holds")
    target_path.write_text(text_on_disk)
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Widget fact](widget-fact.md) — what the store really holds\n")
    original_index_bytes = index_path.read_bytes()
    # the entry's own copy of the previous text is stale: the store moved on
    # after the proposal was built, so only the bytes on disk are the truth
    stale_text = _file_text(name="widget-fact", description="a description from two runs ago")
    assert stale_text != text_on_disk
    new_text = _file_text(name="widget-fact", description="new, more accurate description")
    entry = _entry(
        name="widget-fact",
        kind="update widget-fact",
        file_text=new_text,
        existing_text=stale_text,
    )
    index_fault = f"index boom {uuid.uuid4()}"
    monkeypatch.setattr(Path, "replace", _replace_failing_on_index(index_fault))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    assert index_fault in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert target_path.read_text() == text_on_disk
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "widget-fact.md"]


def test_main_write_leaves_the_update_target_and_the_index_untouched_when_the_file_text_will_not_parse(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    target_path = store_path / "widget-fact.md"
    original_text = _file_text(name="widget-fact", description="old description")
    target_path.write_text(original_text)
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Widget fact](widget-fact.md) — old description\n")
    original_index_bytes = index_path.read_bytes()
    malformed = "---\n- a\n- b\n---\n\nBody.\n"
    parser_message = _parser_message(malformed)
    entry = _entry(
        name="widget-fact",
        kind="update widget-fact",
        file_text=malformed,
        existing_text=original_text,
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    assert parser_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert target_path.read_text() == original_text
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "widget-fact.md"]


def test_main_write_reports_both_the_pointer_error_and_the_rollback_error_when_the_rollback_itself_fails(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    entry = _entry(name="widget-fact", kind="new")
    index_fault = f"index boom {uuid.uuid4()}"
    rollback_fault = f"rollback boom {uuid.uuid4()}"
    monkeypatch.setattr(Path, "replace", _replace_failing_on_index(index_fault))
    _break_removal_of_the_memory_file(monkeypatch, rollback_fault)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    assert index_fault in captured.err
    assert rollback_fault in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    # the memory file the rollback could not remove is still there, so stderr
    # has to name it and must not claim the store was put back
    assert (store_path / "widget-fact.md").exists()
    assert "widget-fact.md" in captured.err
    assert "rolled back" not in captured.err
    assert sorted(p.name for p in store_path.iterdir()) == ["widget-fact.md"]


# The index step can fail on the entry itself, not just on the filesystem: the
# pointer line is built from frontmatter, and an entry whose frontmatter cannot
# yield a description reaches that step only after the memory file has landed.
# These two faults need no monkeypatching at all, and the store still has to be
# put back exactly as it was.


def test_main_write_removes_the_new_memory_file_and_reports_the_reason_when_the_file_text_carries_no_description(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    unrelated_path = store_path / "other-thing.md"
    unrelated_text = _file_text(name="other-thing", description="something unrelated")
    unrelated_path.write_text(unrelated_text)
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Other thing](other-thing.md) — something unrelated\n")
    original_index_bytes = index_path.read_bytes()
    # frontmatter the parser happily accepts, carrying everything except the one
    # key the pointer line is built from
    no_description = "---\nname: widget-fact\n---\n\nBody.\n"
    assert "description" not in proposal.parse_frontmatter(no_description)
    entry = _entry(name="widget-fact", kind="new", file_text=no_description)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert not (store_path / "widget-fact.md").exists()
    assert unrelated_path.read_text() == unrelated_text
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "other-thing.md"]


def test_main_write_restores_the_update_targets_original_bytes_and_reports_the_reason_when_the_entrys_existing_text_will_not_parse(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    target_path = store_path / "widget-fact.md"
    original_text = _file_text(name="widget-fact", description="old description")
    target_path.write_text(original_text)
    original_target_bytes = target_path.read_bytes()
    index_path = store_path / "MEMORY.md"
    index_path.write_text(
        "- [Something](something.md) — unrelated\n"
        "- [Widget fact](widget-fact.md) — old description\n"
    )
    original_index_bytes = index_path.read_bytes()
    # the new text is faultless; the entry's own copy of the previous text is the
    # broken half, and it is only needed after the target has been overwritten
    new_text = _file_text(name="widget-fact", description="new, more accurate description")
    proposal.parse_frontmatter(new_text)
    unparseable_existing = "no frontmatter here\n"
    assert _parser_message(unparseable_existing)
    entry = _entry(
        name="widget-fact",
        kind="update widget-fact",
        file_text=new_text,
        existing_text=unparseable_existing,
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert target_path.read_bytes() == original_target_bytes
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "widget-fact.md"]

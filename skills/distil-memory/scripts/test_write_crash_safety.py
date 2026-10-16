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

    with pytest.raises(OSError, match="boom"):
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

    with pytest.raises(OSError, match="boom"):
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

    with pytest.raises(write.WriteError, match="boom") as raised:
        write.write_memory(entry, store_path)

    assert isinstance(raised.value.__cause__, OSError)
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

    with pytest.raises(OSError, match="boom"):
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


# Every rollback case below starts from the store files in `before`, feeds one
# entry, and fails it at the index step: either the MEMORY.md move faults
# (`reason` None, so the run's own minted fault message is what stderr must
# carry), or the entry's frontmatter cannot yield what the pointer line needs,
# which reaches that step only after the memory file has landed and needs no
# monkeypatching at all. Either way the store must come back byte for byte. A
# case with `retry` then runs the same entry again with the fault gone and
# checks the pointer it prints and the store it lands in.

_OTHER_TEXT = _file_text(name="other-thing", description="something unrelated")
_OTHER_LINE = "- [Other thing](other-thing.md) — something unrelated\n"
_OLD_TEXT = _file_text(name="widget-fact", description="old description")
_NEW_TEXT = _file_text(name="widget-fact", description="new, more accurate description")
_SOMETHING_LINE = "- [Something](something.md) — unrelated\n"
_OLD_LINE = "- [Widget fact](widget-fact.md) — old description\n"
_NEW_POINTER = "- [Widget fact](widget-fact.md) — new, more accurate description"
_KEEPS_TEXT = _file_text(name="widget-fact", description="keeps facts about widgets straight")
_KEEPS_POINTER = "- [Widget fact](widget-fact.md) — keeps facts about widgets straight"
_DEFAULT_POINTER = "- [Widget fact](widget-fact.md) — a fact worth keeping"
_QUEUE_CURSOR_TEXT = _file_text(name="queue-cursor", description="old description")
_ON_DISK_TEXT = _file_text(name="widget-fact", description="what the store really holds")
_UNPARSEABLE_EXISTING = "no frontmatter here\n"

_ROLLBACK_CASES = [
    pytest.param(
        {"other-thing.md": _OTHER_TEXT, "MEMORY.md": _OTHER_LINE},
        _entry(name="widget-fact", kind="new", file_text=_KEEPS_TEXT),
        None,
        (
            _KEEPS_POINTER,
            {
                "other-thing.md": _OTHER_TEXT,
                "MEMORY.md": _OTHER_LINE + _KEEPS_POINTER + "\n",
                "widget-fact.md": _KEEPS_TEXT,
            },
        ),
        id="removes_only_the_new_memory_file_when_the_pointer_write_fails_and_a_retry_then_succeeds",
    ),
    # the store had no index when the run started, so it owes that absence back
    pytest.param(
        {},
        _entry(name="widget-fact", kind="new"),
        None,
        (
            _DEFAULT_POINTER,
            {"widget-fact.md": _file_text(), "MEMORY.md": _DEFAULT_POINTER + "\n"},
        ),
        id="leaves_a_store_that_had_no_index_without_one_when_the_pointer_write_fails_and_a_retry_then_succeeds",
    ),
    pytest.param(
        {"widget-fact.md": _OLD_TEXT, "MEMORY.md": _SOMETHING_LINE + _OLD_LINE},
        _entry(
            name="widget-fact", kind="update widget-fact", file_text=_NEW_TEXT, existing_text=_OLD_TEXT
        ),
        None,
        (
            _NEW_POINTER,
            {"widget-fact.md": _NEW_TEXT, "MEMORY.md": _SOMETHING_LINE + _NEW_POINTER + "\n"},
        ),
        id="restores_the_updated_targets_original_text_and_the_index_when_the_pointer_write_fails_and_a_retry_then_succeeds",
    ),
    # the file kind named is the file that has to come back, and the name the
    # file_text carries never becomes a path of its own
    pytest.param(
        {
            "queue-cursor.md": _QUEUE_CURSOR_TEXT,
            "MEMORY.md": "- [Queue cursor](queue-cursor.md) — old description\n",
        },
        _entry(
            name="queue-cursor",
            kind="update queue-cursor",
            file_text=_NEW_TEXT,
            existing_text=_QUEUE_CURSOR_TEXT,
        ),
        None,
        None,
        id="restores_the_target_named_by_kind_when_the_pointer_write_fails_even_when_the_file_texts_own_name_field_differs",
    ),
    # the entry's own copy of the previous text is stale: the store moved on
    # after the proposal was built, so only the bytes on disk are the truth
    pytest.param(
        {
            "widget-fact.md": _ON_DISK_TEXT,
            "MEMORY.md": "- [Widget fact](widget-fact.md) — what the store really holds\n",
        },
        _entry(
            name="widget-fact",
            kind="update widget-fact",
            file_text=_NEW_TEXT,
            existing_text=_file_text(name="widget-fact", description="a description from two runs ago"),
        ),
        None,
        None,
        id="restores_the_targets_bytes_from_disk_when_the_pointer_write_fails_and_the_entrys_existing_text_is_stale",
    ),
    # the memory on disk was written with CRLF line endings, so a rollback that
    # snapshots it as text and writes it back loses every \r without noticing;
    # the proposal's copy of the previous text carries plain newlines
    pytest.param(
        {"widget-fact.md": _OLD_TEXT.replace("\n", "\r\n"), "MEMORY.md": _OLD_LINE},
        _entry(
            name="widget-fact", kind="update widget-fact", file_text=_NEW_TEXT, existing_text=_OLD_TEXT
        ),
        None,
        None,
        id="restores_the_update_targets_crlf_bytes_exactly_when_the_pointer_write_fails",
    ),
    # frontmatter the parser happily accepts, carrying everything except the
    # one key the pointer line is built from; that key is the whole reason, so
    # a refusal that does not name it leaves the caller guessing
    pytest.param(
        {"other-thing.md": _OTHER_TEXT, "MEMORY.md": _OTHER_LINE},
        _entry(name="widget-fact", kind="new", file_text="---\nname: widget-fact\n---\n\nBody.\n"),
        "description",
        None,
        id="removes_the_new_memory_file_and_reports_the_reason_when_the_file_text_carries_no_description",
    ),
    # the new text is faultless; the entry's own copy of the previous text is
    # the broken half, needed only after the target has been overwritten, and
    # the parser's own complaint is what says which half is broken
    pytest.param(
        {"widget-fact.md": _OLD_TEXT, "MEMORY.md": _SOMETHING_LINE + _OLD_LINE},
        _entry(
            name="widget-fact",
            kind="update widget-fact",
            file_text=_NEW_TEXT,
            existing_text=_UNPARSEABLE_EXISTING,
        ),
        _parser_message(_UNPARSEABLE_EXISTING),
        None,
        id="restores_the_update_targets_original_bytes_and_reports_the_reason_when_the_entrys_existing_text_will_not_parse",
    ),
]


def _store_bytes(store):
    return {p.name: p.read_bytes() for p in store.iterdir()}


def _encoded(files):
    return {name: text.encode() for name, text in files.items()}


@pytest.mark.parametrize("before, entry, reason, retry", _ROLLBACK_CASES)
def test_main_write_rolls_the_store_back_byte_for_byte_when_the_index_step_fails(
    store_path, monkeypatch, capsys, before, entry, reason, retry
):
    store_path.mkdir()
    for name, text in before.items():
        (store_path / name).write_bytes(text.encode())
    if reason is None:
        reason = f"index boom {uuid.uuid4()}"
        monkeypatch.setattr(Path, "replace", _replace_failing_on_index(reason))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    failed = capsys.readouterr()
    assert reason in failed.err
    assert "Traceback" not in failed.err
    assert failed.out == ""
    # only the file this run wrote goes back, to the bytes it held: the
    # memories the store already held, and the index itself, come through
    # byte for byte
    assert _store_bytes(store_path) == _encoded(before)

    if retry is None:
        return
    pointer, after = retry
    monkeypatch.setattr(Path, "replace", _REAL_REPLACE)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    retry_status = write.main(["write", "--store", str(store_path)])

    assert retry_status == 0
    assert capsys.readouterr().out.splitlines() == [str(store_path / "widget-fact.md"), pointer]
    assert _store_bytes(store_path) == _encoded(after)


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


def _assert_stderr_is_exactly_the_two_faults(err, index_fault, rollback_report):
    # one line per fault, each pinned whole: no extra line, and no text added
    # to either line, is left to claim the store was put back
    assert err.splitlines() == [index_fault, f"rollback failed: {rollback_report}"]


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
    # has to name it
    assert (store_path / "widget-fact.md").exists()
    _assert_stderr_is_exactly_the_two_faults(
        captured.err, index_fault, f"{rollback_fault}: {store_path / 'widget-fact.md'}"
    )
    assert sorted(p.name for p in store_path.iterdir()) == ["widget-fact.md"]


def test_main_write_reports_both_the_pointer_error_and_the_rollback_error_when_restoring_an_updated_target_fails(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    target_path = store_path / "widget-fact.md"
    original_text = _file_text(name="widget-fact", description="old description")
    target_path.write_text(original_text)
    (store_path / "MEMORY.md").write_text("- [Widget fact](widget-fact.md) — old description\n")
    new_text = _file_text(name="widget-fact", description="new, more accurate description")
    entry = _entry(kind="update widget-fact", file_text=new_text, existing_text=original_text)
    index_fault = f"index boom {uuid.uuid4()}"
    rollback_fault = f"rollback boom {uuid.uuid4()}"

    refused = []

    # the rollback of an update is the only write in this run that passes bytes
    def _refuse_to_write_the_previous_bytes_back(self, *args, **kwargs):
        refused.append(self)
        raise OSError(f"{rollback_fault}: {self}")

    monkeypatch.setattr(Path, "replace", _replace_failing_on_index(index_fault))
    monkeypatch.setattr(Path, "write_bytes", _refuse_to_write_the_previous_bytes_back)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    assert index_fault in captured.err
    assert rollback_fault in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    # the target still holds this run's text, so stderr must not claim otherwise
    assert target_path.read_text() == new_text
    _assert_stderr_is_exactly_the_two_faults(
        captured.err, index_fault, f"{rollback_fault}: {refused[0]}"
    )
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "widget-fact.md"]


# An entry whose envelope is malformed cannot even name the file it targets, so
# the run has nothing to write and nothing to put back. It still owes the caller
# a reason and an untouched store, not a traceback.


def test_main_write_leaves_the_store_untouched_and_reports_the_reason_when_the_entry_carries_no_kind(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    unrelated_path = store_path / "other-thing.md"
    unrelated_text = _file_text(name="other-thing", description="something unrelated")
    unrelated_path.write_text(unrelated_text)
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Other thing](other-thing.md) — something unrelated\n")
    original_index_bytes = index_path.read_bytes()
    # the key that says whether this is a new memory or an update is simply
    # missing, so the store cannot work out which file the entry is about
    malformed_envelope = {k: v for k, v in _entry(name="widget-fact").items() if k != "kind"}
    assert "kind" not in malformed_envelope
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(malformed_envelope)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    # the key the envelope is missing is the one thing that tells the caller
    # what to put back before re-running the same write
    assert "kind" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert not (store_path / "widget-fact.md").exists()
    assert unrelated_path.read_text() == unrelated_text
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "other-thing.md"]

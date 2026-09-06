"""Tests for write.py: the refusals it owes when the store's own files defeat
the run before anything is written, an index or a target it cannot decode,
cannot open, or cannot even probe."""

import io
import json
import os
import sys
import uuid
from pathlib import Path

import write

import pytest

from write_test_helpers import _entry, _file_text, store_path


# The store's own files can defeat the run before it writes anything: an index
# or a target the process cannot decode or cannot open. That is a reason to
# refuse, not a reason to crash, and refusing means the store keeps every byte
# it had, so the caller can repair it and re-run the same write.


def _refuses_to_decode(raw):
    """These bytes really are unreadable as UTF-8, not merely suspicious-looking."""
    try:
        raw.decode()
    except UnicodeDecodeError:
        return True
    return False


def _not_utf_8_flavours(prefix):
    """Four unrelated ways to be undecodable, appended to otherwise readable text.

    They share no byte pattern, so nothing short of decoding tells all four
    apart from a file the store can read.
    """
    return [
        pytest.param(prefix.encode() + b"\xff\xfe not utf-8\n", id="utf-16-byte-order-mark"),
        pytest.param(prefix.encode() + b"\x80 not utf-8\n", id="bare-continuation-byte"),
        pytest.param(prefix.encode() + b"\xc3 not utf-8\n", id="truncated-two-byte-sequence"),
        pytest.param((prefix + "café\n").encode("utf-16-le"), id="utf-16le-without-a-bom"),
    ]


@pytest.mark.parametrize("original_index_bytes", _not_utf_8_flavours("- [X](x.md) "))
def test_main_write_refuses_a_store_whose_index_is_not_valid_utf_8_and_a_repaired_index_then_lets_the_same_write_through(
    original_index_bytes, store_path, monkeypatch, capsys
):
    store_path.mkdir()
    index_path = store_path / "MEMORY.md"
    assert _refuses_to_decode(original_index_bytes)
    index_path.write_bytes(original_index_bytes)
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="keeps facts about widgets straight"),
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    failed = capsys.readouterr()
    # a refusal that does not name the file it choked on tells the caller
    # nothing about what to repair
    assert "MEMORY.md" in failed.err
    assert "Traceback" not in failed.err
    assert failed.out == ""
    assert not (store_path / "widget-fact.md").exists()
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md"]

    # the recovery is to repair the index and re-run the same write, which only
    # works while no memory file from the refused run is left in the way
    index_path.write_text("- [X](x.md) — a readable pointer\n")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    retry_status = write.main(["write", "--store", str(store_path)])

    assert retry_status == 0
    retried = capsys.readouterr()
    lines = retried.out.splitlines()
    assert lines[0] == str(store_path / "widget-fact.md")
    assert lines[1] == "- [Widget fact](widget-fact.md) — keeps facts about widgets straight"
    assert (store_path / "widget-fact.md").read_text() == entry["file_text"]
    assert index_path.read_text().splitlines() == ["- [X](x.md) — a readable pointer", lines[1]]


@pytest.mark.parametrize(
    "original_target_bytes",
    _not_utf_8_flavours(_file_text(name="queue-cursor", description="old description")),
)
def test_main_write_refuses_an_update_whose_target_bytes_are_not_valid_utf_8_and_leaves_both_files_byte_identical(
    original_target_bytes, store_path, monkeypatch, capsys
):
    store_path.mkdir()
    # a stem no other test in this module uses, so a name in stderr can only
    # have come from this run and not from a literal in the implementation
    target_path = store_path / "queue-cursor.md"
    assert _refuses_to_decode(original_target_bytes)
    target_path.write_bytes(original_target_bytes)
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Queue cursor](queue-cursor.md) — old description\n")
    original_index_bytes = index_path.read_bytes()
    entry = _entry(
        name="queue-cursor",
        kind="update queue-cursor",
        file_text=_file_text(name="queue-cursor", description="new, more accurate description"),
        existing_text=_file_text(name="queue-cursor", description="old description"),
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    # the memory it could not read is the one thing the caller has to hear
    # about, and only the decode failure itself can say why it could not
    assert target_path.name in captured.err
    assert "utf-8" in captured.err
    assert "codec" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    # nothing had been written when the read failed, so the refusal costs the
    # store nothing: both files keep the bytes they came in with
    assert target_path.read_bytes() == original_target_bytes
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "queue-cursor.md"]


@pytest.mark.skipif(os.geteuid() == 0, reason="root opens a 0o000 file whatever its mode says")
def test_main_write_refuses_an_update_whose_target_cannot_be_read_and_leaves_both_files_byte_identical(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    # a stem no other test in this module uses, so a name in stderr can only
    # have come from this run and not from a literal in the implementation
    target_path = store_path / "queue-cursor.md"
    original_text = _file_text(name="queue-cursor", description="old description")
    target_path.write_text(original_text)
    original_target_bytes = target_path.read_bytes()
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Queue cursor](queue-cursor.md) — old description\n")
    original_index_bytes = index_path.read_bytes()
    entry = _entry(
        name="queue-cursor",
        kind="update queue-cursor",
        file_text=_file_text(name="queue-cursor", description="new, more accurate description"),
        existing_text=original_text,
    )
    target_path.chmod(0o000)
    try:
        target_path.read_bytes()
    except OSError as exc:
        # the OS's own refusal is the reason, and holding its exact text here
        # keeps the assertion honest on a machine that words it differently
        refusal = str(exc)
    else:
        pytest.fail(f"expected {target_path} to be unopenable at mode 0o000")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert target_path.exists()
    target_path.chmod(0o644)
    assert status == 1
    captured = capsys.readouterr()
    # the memory it could not open is the one thing the caller has to hear
    # about, and the refusal it hit is the one thing that says why
    assert target_path.name in captured.err
    assert refusal in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert target_path.read_bytes() == original_target_bytes
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "queue-cursor.md"]


@pytest.mark.skipif(
    os.geteuid() == 0, reason="root traverses a 0o000 directory whatever its mode says"
)
def test_main_write_refuses_an_update_whose_target_cannot_even_be_probed_and_leaves_both_files_byte_identical(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    target_path = store_path / "widget-fact.md"
    original_text = _file_text(name="widget-fact", description="old description")
    target_path.write_text(original_text)
    original_target_bytes = target_path.read_bytes()
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Widget fact](widget-fact.md) — old description\n")
    original_index_bytes = index_path.read_bytes()
    entry = _entry(
        name="widget-fact",
        kind="update widget-fact",
        file_text=_file_text(name="widget-fact", description="new, more accurate description"),
        existing_text=original_text,
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))
    store_path.chmod(0o000)

    try:
        status = write.main(["write", "--store", str(store_path)])
    finally:
        # a store left at 0o000 defeats pytest's own tmp_path cleanup for every
        # later test, so it goes back whatever the call did
        store_path.chmod(0o755)

    assert status == 1
    captured = capsys.readouterr()
    # a refusal that names no path leaves the caller nothing to repair, which is
    # no better than the traceback it replaces: the store it could not search is
    # the one thing that has to reach stderr
    assert captured.err != ""
    assert str(store_path) in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    # the probe fails before anything is written, so the refusal costs the store
    # nothing: both files keep the bytes they came in with
    assert target_path.read_bytes() == original_target_bytes
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "widget-fact.md"]


_REAL_IS_FILE = Path.is_file


def _probe_failing_on(name, fault_message):
    """Fail only the existence probe of one file; let every other probe answer.

    The caller mints a fault message unique to its own run, so stderr can only
    carry it by reporting the exception that actually arrived.
    """

    def _is_file(self, *args, **kwargs):
        if self.name == name:
            raise OSError(fault_message)
        return _REAL_IS_FILE(self, *args, **kwargs)

    return _is_file


def test_main_write_refuses_an_update_and_reports_the_probes_own_error_when_the_probe_itself_fails(
    store_path, monkeypatch, capsys
):
    store_path.mkdir()
    target_path = store_path / "widget-fact.md"
    original_text = _file_text(name="widget-fact", description="old description")
    target_path.write_text(original_text)
    original_target_bytes = target_path.read_bytes()
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Widget fact](widget-fact.md) — old description\n")
    original_index_bytes = index_path.read_bytes()
    entry = _entry(
        name="widget-fact",
        kind="update widget-fact",
        file_text=_file_text(name="widget-fact", description="new, more accurate description"),
        existing_text=original_text,
    )
    probe_fault = f"probe boom {uuid.uuid4()}"
    monkeypatch.setattr(Path, "is_file", _probe_failing_on(target_path.name, probe_fault))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    # this text exists nowhere but in this run's own fault, so stderr can only
    # carry it by repeating what the probe actually reported
    assert probe_fault in captured.err
    # and repeating the fault without naming the file it happened to still
    # leaves the caller with nothing to repair, as the sibling refusals say
    assert target_path.name in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert target_path.read_bytes() == original_target_bytes
    assert index_path.read_bytes() == original_index_bytes
    assert sorted(p.name for p in store_path.iterdir()) == ["MEMORY.md", "widget-fact.md"]

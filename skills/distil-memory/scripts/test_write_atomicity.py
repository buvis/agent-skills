"""Tests for write.py that observe its writes, not just their outcome.

The crash-safety suite faults a move so it never runs, which only proves the
target survives a move that did not happen. These tests let the real move run
and then fail, refuse every write call outright, and change the store behind a
run's back, so an implementation that reaches the right end state by the wrong
route is caught.
"""

import builtins
import io
import json
import sys
from pathlib import Path

import write

import pytest

from write_test_helpers import _entry, _file_text, store_path

_REAL_REPLACE = Path.replace


def _rename_then_raise(snapshots):
    """Run the real move, record what the target holds that instant, then fail.

    A process killed one instruction after the move leaves exactly what the
    snapshot holds, so only a complete file is acceptable there.
    """

    def _replace(self, target, *args, **kwargs):
        _REAL_REPLACE(self, target, *args, **kwargs)
        snapshots[Path(target).name] = Path(target).read_bytes()
        raise OSError("crash right after the move")

    return _replace


def _write_the_memory_file(store):
    entry = _entry(name="widget-fact", kind="new")
    with pytest.raises(write.WriteError):
        write.write_memory(entry, store)
    return "widget-fact.md", entry["file_text"].encode()


def _write_the_index(store):
    index_text = "- [Something](something.md) — unrelated\n"
    (store / "MEMORY.md").write_text(index_text)
    entry = _entry(name="widget-fact", kind="new")
    with pytest.raises(OSError):
        write.append_pointer(store, entry)
    new_line = "- [Widget fact](widget-fact.md) — a fact worth keeping\n"
    return "MEMORY.md", (index_text + new_line).encode()


@pytest.mark.parametrize("write_one", [_write_the_memory_file, _write_the_index])
def test_atomic_write_target_is_complete_the_instant_the_rename_lands(
    store_path, monkeypatch, write_one
):
    store_path.mkdir()
    snapshots = {}
    monkeypatch.setattr(Path, "replace", _rename_then_raise(snapshots))

    name, expected = write_one(store_path)

    # a move that puts an empty or partial file in place and fills it after
    # leaves the target short at exactly this instant
    assert snapshots == {name: expected}
    assert (store_path / name).read_bytes() == expected
    assert not list(store_path.glob("*.tmp"))


def _realistic_malformed_text():
    # real memory files run to hundreds or thousands of bytes, so a refusal
    # that only looks at short files must still meet this one
    text = _file_text(
        description="[unclosed bracket in a description",
        body="Body text.\n\n" + "Detail line.\n" * 40,
    )
    assert len(text) >= 200
    return text


def test_a_realistic_size_malformed_memory_is_refused(store_path):
    store_path.mkdir()
    entry = _entry(name="widget-fact", kind="new", file_text=_realistic_malformed_text())

    with pytest.raises(write.WriteError):
        write.write_memory(entry, store_path)

    assert list(store_path.iterdir()) == []


def test_a_refused_memory_triggers_no_write_call(store_path, monkeypatch, capsys):
    store_path.mkdir()
    entry = _entry(name="widget-fact", kind="new", file_text=_realistic_malformed_text())
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    def _no_write(*args, **kwargs):
        pytest.fail("a refused memory reached a write call")

    # every route to the disk: the module's own writer, Path's helpers, and
    # open() whether called as a builtin or through Path.open
    monkeypatch.setattr(write, "_atomic_write", _no_write)
    monkeypatch.setattr(Path, "write_text", _no_write)
    monkeypatch.setattr(Path, "write_bytes", _no_write)
    monkeypatch.setattr(builtins, "open", _no_write)
    monkeypatch.setattr(io, "open", _no_write)

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    assert capsys.readouterr().err.strip() != ""
    assert list(store_path.iterdir()) == []

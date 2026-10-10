"""Tests for write.py: the main() CLI, which reads one entry from stdin,
writes its memory file and upserts the store's MEMORY.md pointer line."""

import io
import json
import sys

import docket
import proposal
import write

import pytest

from write_test_helpers import _entry, _file_text, _parser_message, store_path


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


def test_main_write_reports_a_pointer_failure_to_stderr_and_returns_one_without_a_traceback(
    tmp_path, store_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    store_path.mkdir()
    entry = _entry(name="widget-fact", kind="new")

    def fail_to_append(store, entry):
        raise OSError("index disk is full")

    monkeypatch.setattr(write, "append_pointer", fail_to_append)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    assert "index disk is full" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert list(store_path.iterdir()) == []


def test_main_write_run_twice_with_the_same_new_entry_leaves_memory_and_index_bytes_identical(
    tmp_path, store_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    store_path.mkdir()
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="keeps facts about widgets straight"),
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))
    assert write.main(["write", "--store", str(store_path)]) == 0
    capsys.readouterr()
    memory_bytes = (store_path / "widget-fact.md").read_bytes()
    index_bytes = (store_path / "MEMORY.md").read_bytes()
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    second = write.main(["write", "--store", str(store_path)])

    assert second == 0
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [str(store_path / "widget-fact.md"), "MEMORY.md: unchanged"]
    assert (store_path / "widget-fact.md").read_bytes() == memory_bytes
    assert (store_path / "MEMORY.md").read_bytes() == index_bytes
    assert index_bytes.decode().count("widget-fact.md") == 1


def test_main_write_recovers_a_missing_pointer_for_an_already_written_unchanged_description_update(
    tmp_path, store_path, monkeypatch, capsys
):
    # a previous run wrote the update but never reached the index
    monkeypatch.chdir(tmp_path)
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="keeps facts about widgets straight")
    new_text = _file_text(
        name="widget-fact", description="keeps facts about widgets straight", body="Updated body."
    )
    (store_path / "widget-fact.md").write_text(new_text)
    (store_path / "MEMORY.md").write_text("- [Something](something.md) — unrelated\n")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 0
    pointer = "- [Widget fact](widget-fact.md) — keeps facts about widgets straight"
    assert capsys.readouterr().out.splitlines() == [str(store_path / "widget-fact.md"), pointer]
    assert (store_path / "MEMORY.md").read_text().splitlines() == [
        "- [Something](something.md) — unrelated",
        pointer,
    ]
    assert (store_path / "widget-fact.md").read_text() == new_text
    assert write.published(entry, store_path) is True


@pytest.mark.parametrize(
    ("malformed", "expected_message"),
    [
        pytest.param(
            "no frontmatter here\n",
            "file does not open with a --- frontmatter marker",
            id="no-opening-marker",
        ),
        pytest.param(
            "---\n- a\n- b\n---\n\nBody.\n",
            "frontmatter is not a YAML mapping",
            id="sequence-not-mapping",
        ),
    ],
)
def test_main_write_reports_the_frontmatter_parse_failure_and_returns_one_leaving_the_store_empty(
    tmp_path, store_path, monkeypatch, capsys, malformed, expected_message
):
    monkeypatch.chdir(tmp_path)
    store_path.mkdir()
    assert _parser_message(malformed) == expected_message
    entry = _entry(name="widget-fact", kind="new", file_text=malformed)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert list(store_path.iterdir()) == []


def _tree_bytes(root):
    """Every path under `root`, mapped to its bytes (None for a directory)."""
    return {
        str(path.relative_to(root)): None if path.is_dir() else path.read_bytes()
        for path in root.rglob("*")
    }


def _refuse_disk_change(*args, **kwargs):
    pytest.fail("the store was written to before the entry was refused")


@pytest.mark.parametrize("kind", [None, 42, [], {}], ids=["null", "int", "list", "dict"])
@pytest.mark.parametrize("name", ["widget-fact", "gadget-fact"])
@pytest.mark.parametrize("seeded", [True, False], ids=["seeded-store", "empty-store"])
def test_main_write_refuses_a_kind_that_is_not_a_string_and_returns_one_without_touching_disk(
    tmp_path, store_path, monkeypatch, capsys, kind, name, seeded
):
    monkeypatch.chdir(tmp_path)
    store_path.mkdir()
    if seeded:
        (store_path / "widget-fact.md").write_text(
            _file_text(name="widget-fact", description="keeps facts about widgets straight")
        )
        (store_path / "MEMORY.md").write_text(
            "- [Widget fact](widget-fact.md) — keeps facts about widgets straight\n"
        )
    before = _tree_bytes(tmp_path)
    try:
        proposal.updated_name(kind)
    except AttributeError as exc:
        expected_message = str(exc)
    else:
        pytest.fail(f"expected proposal.updated_name to raise AttributeError for {kind!r}")
    for method in ("write_text", "write_bytes", "replace", "unlink"):
        monkeypatch.setattr(write.Path, method, _refuse_disk_change)
    entry = _entry(name=name, kind=kind)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    assert status == 1
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    monkeypatch.undo()
    assert _tree_bytes(tmp_path) == before


def _seed_store(store_path):
    store_path.mkdir()
    (store_path / "widget-fact.md").write_text(
        _file_text(name="widget-fact", description="keeps facts about widgets straight")
    )
    (store_path / "MEMORY.md").write_text(
        "- [Widget fact](widget-fact.md) — keeps facts about widgets straight\n"
    )


def _assert_refused_with_a_reason_and_store_untouched(status, capsys, tmp_path, before):
    assert status == 1
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert _tree_bytes(tmp_path) == before


def test_main_write_refuses_a_name_that_sanitises_to_an_empty_stem_and_returns_one_with_a_reason(
    tmp_path, store_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    _seed_store(store_path)
    before = _tree_bytes(tmp_path)
    entry = _entry(name="!!!", kind="new", file_text=_file_text(name='"!!!"'))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    _assert_refused_with_a_reason_and_store_untouched(status, capsys, tmp_path, before)


@pytest.mark.parametrize(
    "stdin_text",
    ["this is not json", "", '{"name": "widget-fact", "kind": '],
    ids=["plain-text", "empty", "truncated-json"],
)
def test_main_write_refuses_stdin_that_is_not_valid_json_and_returns_one_with_a_reason(
    tmp_path, store_path, monkeypatch, capsys, stdin_text
):
    monkeypatch.chdir(tmp_path)
    _seed_store(store_path)
    before = _tree_bytes(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_text))

    status = write.main(["write", "--store", str(store_path)])

    _assert_refused_with_a_reason_and_store_untouched(status, capsys, tmp_path, before)


@pytest.mark.parametrize("stdin_text", ["null", "[]"], ids=["null", "list"])
def test_main_write_refuses_a_json_envelope_that_is_not_an_object_and_returns_one_with_a_reason(
    tmp_path, store_path, monkeypatch, capsys, stdin_text
):
    monkeypatch.chdir(tmp_path)
    _seed_store(store_path)
    before = _tree_bytes(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_text))

    status = write.main(["write", "--store", str(store_path)])

    _assert_refused_with_a_reason_and_store_untouched(status, capsys, tmp_path, before)


def test_main_write_refuses_stdin_that_is_not_utf8_and_returns_one_with_a_reason(
    tmp_path, store_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    _seed_store(store_path)
    before = _tree_bytes(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"\xff\xfe{}"), encoding="utf-8"))

    status = write.main(["write", "--store", str(store_path)])

    _assert_refused_with_a_reason_and_store_untouched(status, capsys, tmp_path, before)


def test_main_write_rolls_back_an_update_whose_existing_text_is_null_and_returns_one_with_a_reason(
    tmp_path, store_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    _seed_store(store_path)
    before = _tree_bytes(tmp_path)
    new_text = _file_text(name="widget-fact", description="a changed hook", body="New body.")
    entry = _entry(name="widget-fact", kind="update widget-fact", file_text=new_text)
    assert entry["existing_text"] is None
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(entry)))

    status = write.main(["write", "--store", str(store_path)])

    _assert_refused_with_a_reason_and_store_untouched(status, capsys, tmp_path, before)

"""Tests for write.py: the main() CLI, which reads one entry from stdin,
writes its memory file and upserts the store's MEMORY.md pointer line."""

import io
import json
import sys

import docket
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

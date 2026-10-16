"""Tests for docket.py: pins that docket's CLI exits 1 with a stderr reason
instead of raising a traceback when the proposals directory holds bytes that
are not UTF-8 or a batch whose shape is wrong, and that such a refusal saves
nothing to the queue."""

import json

import docket

import pytest


@pytest.fixture
def queue_path(tmp_path):
    return tmp_path / "queue.json"


def _record(name, line_no, file=None):
    """One proposals.json record, the shape save reads from a proposals dir."""
    return {
        "name": name,
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": line_no,
        "evidence_text": f"evidence for {name.split('-')[0]}",
        "existing_text": None,
        "file": file or f"{name}.md",
    }


def _proposals_dir(tmp_path):
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    return proposals_dir


def _assert_refused(capsys, queue_path, *needles):
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    for needle in needles:
        assert needle in captured.err
    assert captured.out == ""
    assert not queue_path.exists()


def _save(proposals_dir, queue_path):
    return docket.main(["save", "--proposals-dir", str(proposals_dir), "--queue", str(queue_path)])


def test_save_refuses_a_latin1_proposals_file(tmp_path, monkeypatch, capsys, queue_path):
    monkeypatch.chdir(tmp_path)
    proposals_dir = _proposals_dir(tmp_path)
    (proposals_dir / "proposals.json").write_bytes('[{"name": "caf\xe9"}]'.encode("latin-1"))

    assert _save(proposals_dir, queue_path) == 1

    _assert_refused(capsys, queue_path, "proposals.json")


def test_save_refuses_a_latin1_sibling(tmp_path, monkeypatch, capsys, queue_path):
    monkeypatch.chdir(tmp_path)
    proposals_dir = _proposals_dir(tmp_path)
    (proposals_dir / "cafe-note.md").write_bytes("caf\xe9 body\n".encode("latin-1"))
    (proposals_dir / "proposals.json").write_text(json.dumps([_record("cafe-note", 1)]))

    assert _save(proposals_dir, queue_path) == 1

    _assert_refused(capsys, queue_path, "cafe-note.md")


def test_save_refuses_an_object_top_level(tmp_path, monkeypatch, capsys, queue_path):
    monkeypatch.chdir(tmp_path)
    proposals_dir = _proposals_dir(tmp_path)
    (proposals_dir / "proposals.json").write_text(json.dumps({"name": "x"}))

    assert _save(proposals_dir, queue_path) == 1

    _assert_refused(capsys, queue_path, "list")


def test_save_refuses_a_non_object_record(tmp_path, monkeypatch, capsys, queue_path):
    monkeypatch.chdir(tmp_path)
    proposals_dir = _proposals_dir(tmp_path)
    (proposals_dir / "proposals.json").write_text(json.dumps(["just a string"]))

    assert _save(proposals_dir, queue_path) == 1

    _assert_refused(capsys, queue_path, "position 0")


def test_save_refuses_a_record_missing_file(tmp_path, monkeypatch, capsys, queue_path):
    monkeypatch.chdir(tmp_path)
    proposals_dir = _proposals_dir(tmp_path)
    record = _record("gizmo-note", 1)
    del record["file"]
    (proposals_dir / "gizmo-note.md").write_text("---\nname: gizmo-note\n---\n\nBody.\n")
    (proposals_dir / "proposals.json").write_text(json.dumps([record]))

    assert _save(proposals_dir, queue_path) == 1

    _assert_refused(capsys, queue_path, "missing file", "position 0")


def test_save_refuses_a_record_missing_evidence_text_after_readable_records(
    tmp_path, monkeypatch, capsys, queue_path
):
    monkeypatch.chdir(tmp_path)
    proposals_dir = _proposals_dir(tmp_path)
    names = ["gear-note", "spindle-note", "lever-note"]
    for name in names:
        (proposals_dir / f"{name}.md").write_text(f"---\nname: {name}\n---\n\nBody.\n")
    records = [_record(name, n) for n, name in enumerate(names, start=1)]
    del records[2]["evidence_text"]
    (proposals_dir / "proposals.json").write_text(json.dumps(records))

    assert _save(proposals_dir, queue_path) == 1

    _assert_refused(capsys, queue_path, "missing evidence_text", "position 2")

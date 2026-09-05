"""Tests for docket.py: the main() CLI subcommands (save, start, next,
decide, cursor), including the --queue flag."""

import json

import docket

import pytest


def _proposal(transcript="t.jsonl", line_no=1, name=None, file_text=None):
    label = name or f"name-{line_no}"
    return {
        "name": label,
        "kind": "new",
        "transcript": transcript,
        "line_no": line_no,
        "evidence_text": f"evidence for line {line_no}",
        "file_text": file_text or f"file text for {label}",
        "existing_text": None,
    }


# main() CLI wiring. These subcommands resolve the queue file from the
# working directory (no path= is passed through), so every test below
# chdirs into tmp_path first and reads the queue back the same way (no
# explicit path=), never touching a real queue file.


def test_main_save_reads_proposals_json_and_sibling_files_and_prints_added_n_of_m(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "widget-fact.md").write_text("---\nname: widget-fact\n---\n\nBody text.\n")
    record = {
        "name": "widget-fact",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 7,
        "evidence_text": "evidence for widget",
        "existing_text": "prior text",
        "file": "widget-fact.md",
    }
    (proposals_dir / "proposals.json").write_text(json.dumps([record]))

    exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "added 1 of 1" in captured.out

    entries = docket.load(path=proposals_dir.parent / "distil-memory-queue.json")["entries"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["name"] == "widget-fact"
    assert entry["kind"] == "new"
    assert entry["transcript"] == "t.jsonl"
    assert entry["line_no"] == 7
    assert entry["evidence_text"] == "evidence for widget"
    assert entry["existing_text"] == "prior text"
    assert entry["file_text"] == "---\nname: widget-fact\n---\n\nBody text.\n"


def test_main_save_ingests_a_record_whose_existing_text_key_is_absent(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "new-fact.md").write_text("---\nname: new-fact\n---\n\nBody text.\n")
    record = {
        "name": "new-fact",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 1,
        "evidence_text": "some evidence",
        "file": "new-fact.md",
    }
    (proposals_dir / "proposals.json").write_text(json.dumps([record]))

    exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "added 1 of 1" in captured.out
    entries = docket.load(path=proposals_dir.parent / "distil-memory-queue.json")["entries"]
    assert len(entries) == 1
    assert entries[0]["name"] == "new-fact"


def test_main_save_prints_added_n_of_m_counting_m_as_every_record_read_not_just_new_ones(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "a.md").write_text("a text")
    (proposals_dir / "b.md").write_text("b text")
    record_a = {
        "name": "fact-a",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 1,
        "evidence_text": "ev-a",
        "existing_text": None,
        "file": "a.md",
    }
    (proposals_dir / "proposals.json").write_text(json.dumps([record_a]))
    first_exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])
    assert first_exit_code == 0
    capsys.readouterr()

    record_b = {
        "name": "fact-b",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 2,
        "evidence_text": "ev-b",
        "existing_text": None,
        "file": "b.md",
    }
    (proposals_dir / "proposals.json").write_text(json.dumps([record_a, record_b]))

    exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "added 1 of 2" in captured.out


def test_main_start_returns_zero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    exit_code = docket.main(["start"])

    assert exit_code == 0


def test_main_next_prints_the_next_undecided_entry_as_one_line_of_json_and_returns_zero(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(transcript="t.jsonl", line_no=1)])

    exit_code = docket.main(["next"])

    assert exit_code == 0
    captured = capsys.readouterr()
    lines = captured.out.strip("\n").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["id"] == docket.slice_key("t.jsonl", 1)


def test_main_next_prints_nothing_and_returns_one_when_nothing_is_available(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)

    exit_code = docket.main(["next"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""


def test_main_decide_kept_records_the_decision_and_returns_zero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(transcript="t.jsonl", line_no=1)])
    entry_id = docket.slice_key("t.jsonl", 1)

    exit_code = docket.main(["decide", entry_id, "kept"])

    assert exit_code == 0
    assert docket.load()["entries"][0]["decision"] == "kept"


def test_main_decide_dropped_records_the_decision_and_returns_zero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(transcript="t.jsonl", line_no=1)])
    entry_id = docket.slice_key("t.jsonl", 1)

    exit_code = docket.main(["decide", entry_id, "dropped"])

    assert exit_code == 0
    assert docket.load()["entries"][0]["decision"] == "dropped"


def test_main_decide_with_file_flag_replaces_the_entrys_stored_file_text(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(transcript="t.jsonl", line_no=1, file_text="original")])
    entry_id = docket.slice_key("t.jsonl", 1)
    replacement = tmp_path / "replacement.md"
    replacement.write_text("edited content")

    exit_code = docket.main(["decide", entry_id, "kept", "--file", str(replacement)])

    assert exit_code == 0
    assert docket.load()["entries"][0]["file_text"] == "edited content"


def test_main_cursor_prints_the_lifetime_decision_count_and_returns_zero(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(transcript="t.jsonl", line_no=1)])
    docket.decide(docket.slice_key("t.jsonl", 1), "kept")

    exit_code = docket.main(["cursor"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "1"


def test_main_decide_reports_the_queue_errors_message_to_stderr_and_returns_one_for_an_unknown_id(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(transcript="t.jsonl", line_no=1)])
    try:
        docket.decide("does-not-exist:99", "kept")
    except docket.QueueError as exc:
        expected_message = str(exc)
    else:
        pytest.fail("expected docket.decide to raise QueueError for an unknown id")

    exit_code = docket.main(["decide", "does-not-exist:99", "kept"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_decide_reports_the_queue_errors_message_to_stderr_and_returns_one_for_an_already_decided_entry(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(transcript="t.jsonl", line_no=1)])
    entry_id = docket.slice_key("t.jsonl", 1)
    docket.decide(entry_id, "kept")
    try:
        docket.decide(entry_id, "kept")
    except docket.QueueError as exc:
        expected_message = str(exc)
    else:
        pytest.fail("expected docket.decide to raise QueueError for an already-decided entry")

    exit_code = docket.main(["decide", entry_id, "kept"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_save_carries_a_records_dedup_error_into_the_stored_entry(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "widget-fact.md").write_text("---\nname: widget-fact\n---\n\nBody text.\n")
    record = {
        "name": "widget-fact",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 7,
        "evidence_text": "evidence for widget",
        "existing_text": None,
        "dedup_error": "could not compare against existing memories: index unavailable",
        "file": "widget-fact.md",
    }
    (proposals_dir / "proposals.json").write_text(json.dumps([record]))

    exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])

    assert exit_code == 0
    entries = docket.load(path=proposals_dir.parent / "distil-memory-queue.json")["entries"]
    assert len(entries) == 1
    assert entries[0]["dedup_error"] == "could not compare against existing memories: index unavailable"


def test_main_save_ingests_a_record_whose_dedup_error_key_is_absent_and_stores_none(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "new-fact.md").write_text("---\nname: new-fact\n---\n\nBody text.\n")
    record = {
        "name": "new-fact",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 1,
        "evidence_text": "some evidence",
        "file": "new-fact.md",
    }
    (proposals_dir / "proposals.json").write_text(json.dumps([record]))

    exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])

    assert exit_code == 0
    entries = docket.load(path=proposals_dir.parent / "distil-memory-queue.json")["entries"]
    assert len(entries) == 1
    assert entries[0]["dedup_error"] is None


def test_main_save_keeps_each_entrys_dedup_error_matched_to_the_right_entry_in_a_mixed_batch(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "a.md").write_text("a text")
    (proposals_dir / "b.md").write_text("b text")
    record_with_error = {
        "name": "fact-a",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 1,
        "evidence_text": "ev-a",
        "existing_text": None,
        "dedup_error": "ambiguous match against fact-a-old",
        "file": "a.md",
    }
    record_without_error = {
        "name": "fact-b",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 2,
        "evidence_text": "ev-b",
        "existing_text": None,
        "file": "b.md",
    }
    (proposals_dir / "proposals.json").write_text(
        json.dumps([record_with_error, record_without_error])
    )

    exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])

    assert exit_code == 0
    entries = docket.load(path=proposals_dir.parent / "distil-memory-queue.json")["entries"]
    assert len(entries) == 2
    entry_a = next(e for e in entries if e["name"] == "fact-a")
    entry_b = next(e for e in entries if e["name"] == "fact-b")
    assert entry_a["dedup_error"] == "ambiguous match against fact-a-old"
    assert entry_b["dedup_error"] is None


# --queue CLI flag. save, next, decide, and cursor here are exercised through
# docket.main() with an explicit --queue pointing at a path other than the
# cwd-derived default, so a subcommand that silently falls back to the
# default location is caught two ways: the assertion on queue_path's own
# contents, and the assertion that the default report dir was never created.


def test_main_save_next_decide_and_cursor_with_queue_flag_all_operate_on_the_given_path(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    queue_path = tmp_path / "elsewhere" / "q.json"
    default_report_dir = tmp_path / "dev" / "local" / "audit-results"
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "widget-fact.md").write_text("---\nname: widget-fact\n---\n\nBody text.\n")
    record = {
        "name": "widget-fact",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 7,
        "evidence_text": "evidence for widget",
        "existing_text": None,
        "file": "widget-fact.md",
    }
    (proposals_dir / "proposals.json").write_text(json.dumps([record]))

    save_exit = docket.main(
        ["save", "--proposals-dir", str(proposals_dir), "--queue", str(queue_path)]
    )

    assert save_exit == 0
    assert not default_report_dir.exists()
    saved_entries = docket.load(path=queue_path)["entries"]
    assert len(saved_entries) == 1
    assert saved_entries[0]["id"] == docket.slice_key("t.jsonl", 7)
    assert saved_entries[0]["decision"] == "undecided"

    capsys.readouterr()
    next_exit = docket.main(["next", "--queue", str(queue_path)])

    assert next_exit == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["id"] == docket.slice_key("t.jsonl", 7)

    decide_exit = docket.main(["decide", payload["id"], "kept", "--queue", str(queue_path)])

    assert decide_exit == 0
    assert docket.load(path=queue_path)["entries"][0]["decision"] == "kept"

    capsys.readouterr()
    cursor_exit = docket.main(["cursor", "--queue", str(queue_path)])

    assert cursor_exit == 0
    assert capsys.readouterr().out.strip() == "1"
    assert not default_report_dir.exists()


def test_main_start_with_queue_flag_re_arms_the_per_run_cap_at_the_given_path(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    queue_path = tmp_path / "elsewhere" / "q.json"
    default_report_dir = tmp_path / "dev" / "local" / "audit-results"
    proposals = [
        _proposal(transcript="t.jsonl", line_no=n) for n in range(1, docket.PER_RUN_CAP + 3)
    ]
    docket.save(proposals, path=queue_path)
    for _ in range(docket.PER_RUN_CAP):
        entry = docket.next_undecided(path=queue_path)
        docket.decide(entry["id"], "kept", path=queue_path)
    assert docket.next_undecided(path=queue_path) is None

    exit_code = docket.main(["start", "--queue", str(queue_path)])

    assert exit_code == 0
    assert docket.next_undecided(path=queue_path) is not None
    assert not default_report_dir.exists()


# save's default queue path when --queue is absent. Unlike the other
# subcommands (which fall back to _report_dir()'s cwd walk), save without
# --queue derives the queue path from --proposals-dir's parent, not cwd.


def test_main_save_without_queue_flag_derives_queue_path_from_proposals_dir_parent(
    tmp_path, monkeypatch
):
    repo_a_proposals = tmp_path / "repo_a" / "proposals"
    repo_a_proposals.mkdir(parents=True)
    repo_b = tmp_path / "repo_b"
    repo_b.mkdir()
    monkeypatch.chdir(repo_b)
    (repo_a_proposals / "widget-fact.md").write_text("---\nname: widget-fact\n---\n\nBody text.\n")
    record = {
        "name": "widget-fact",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 7,
        "evidence_text": "evidence for widget",
        "existing_text": None,
        "file": "widget-fact.md",
    }
    (repo_a_proposals / "proposals.json").write_text(json.dumps([record]))

    exit_code = docket.main(["save", "--proposals-dir", str(repo_a_proposals)])

    assert exit_code == 0
    assert (tmp_path / "repo_a" / "distil-memory-queue.json").exists() is True
    assert not list(repo_b.rglob("distil-memory-queue.json"))

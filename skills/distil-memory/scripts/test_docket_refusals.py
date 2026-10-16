"""Tests for docket.py: main()'s refusals when the proposals directory or the
decide --file cannot be read."""

import json
from pathlib import Path

import docket

import pytest

from docket_test_helpers import make_proposal as _proposal


@pytest.fixture
def queue_path(tmp_path):
    return tmp_path / "queue.json"


def _record(name, line_no, file=None):
    """One proposals.json record, the shape save reads from a proposals dir.

    A record names the sibling file carrying its text, so `file` defaults to
    the record's own name and is only spelled out by a test that needs it to
    name a file that is not there.
    """
    return {
        "name": name,
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": line_no,
        "evidence_text": f"evidence for {name.split('-')[0]}",
        "existing_text": None,
        "file": file or f"{name}.md",
    }


# An unreadable PROPOSALS directory is a refusal (exit 1), not a queue fault
# (exit 2) and never a traceback. The three ways in: the directory is absent,
# proposals.json is not JSON, and a record names a sibling file that is not
# there. A refusal is all-or-nothing: the queue must gain nothing. The wording
# of the messages is not pinned, only that stderr carries something and that it
# names the path or filename that actually failed, so one constant string
# cannot stand in for three different faults.


def test_main_save_refuses_a_missing_proposals_directory_rather_than_crashing(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    missing_dir = tmp_path / "gone"

    exit_code = docket.main(["save", "--proposals-dir", str(missing_dir)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    assert str(missing_dir) in captured.err
    assert captured.out == ""


def test_main_save_refuses_a_proposals_json_that_does_not_hold_valid_json_rather_than_crashing(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "proposals.json").write_text("not json at all")

    exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    assert str(proposals_dir) in captured.err
    # The message must name the file that failed to parse, not just the
    # directory: three different faults reported with one constant string
    # tell the operator nothing about which one they hit.
    assert "proposals.json" in captured.err
    assert captured.out == ""


def test_main_save_refuses_the_whole_batch_when_one_record_names_an_absent_file(
    tmp_path, monkeypatch, capsys, queue_path
):
    # A MIXED batch is the only shape that tells the two answers apart: with a
    # single record, "refuse the batch" and "silently drop the record, then
    # refuse because nothing is left" look identical from outside. Here the
    # first record's sibling is on disk and the second's is not, so a refusal
    # that half-applies leaves one entry in the queue and is caught.
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "gadget-note.md").write_text("---\nname: gadget-note\n---\n\nGadget.\n")
    readable_record = _record("gadget-note", 7)
    absent_record = _record("cog-note", 8, file="never-written.md")
    (proposals_dir / "proposals.json").write_text(json.dumps([readable_record, absent_record]))

    exit_code = docket.main(
        ["save", "--proposals-dir", str(proposals_dir), "--queue", str(queue_path)]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    # The message must name the sibling that was missing, so the operator can
    # find it without re-reading proposals.json themselves.
    assert "never-written.md" in captured.err
    assert captured.out == ""
    # All or nothing: the readable half of the batch must not have landed.
    assert docket.load(path=queue_path)["entries"] == []


def test_main_save_keeps_exit_2_for_the_queue_alone_and_answers_a_bad_proposals_dir_with_exit_1(
    tmp_path, monkeypatch, capsys
):
    # The boundary that matters: 2 means "the review queue file itself is
    # unreadable" and nothing else, so the same command with a healthy queue
    # and an unreadable proposals directory must answer with a different,
    # smaller code.
    monkeypatch.chdir(tmp_path)
    corrupt_queue = tmp_path / "corrupt-queue.json"
    corrupt_queue.write_text('{"cursor": 0, "entries": [')
    readable_proposals = tmp_path / "readable"
    readable_proposals.mkdir()
    (readable_proposals / "flange-fact.md").write_text("---\nname: flange-fact\n---\n\nBody.\n")
    record = _record("flange-fact", 7)
    (readable_proposals / "proposals.json").write_text(json.dumps([record]))

    queue_fault = docket.main(
        ["save", "--proposals-dir", str(readable_proposals), "--queue", str(corrupt_queue)]
    )

    assert queue_fault == 2
    assert capsys.readouterr().err.strip() != ""

    proposals_fault = docket.main(
        [
            "save",
            "--proposals-dir",
            str(tmp_path / "gone"),
            "--queue",
            str(tmp_path / "healthy-queue.json"),
        ]
    )

    assert proposals_fault == 1
    assert proposals_fault != queue_fault
    captured = capsys.readouterr()
    assert captured.err.strip() != ""


def test_main_save_still_returns_zero_and_prints_added_n_of_m_for_a_readable_proposals_dir(
    tmp_path, monkeypatch, capsys
):
    # Two records, not one: with a single record "added 1 of 1" cannot tell a
    # denominator counting the records READ from one counting the proposals
    # BUILT, and those two differ exactly when a record is quietly dropped.
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "widget-fact.md").write_text("---\nname: widget-fact\n---\n\nBody text.\n")
    (proposals_dir / "sprocket-fact.md").write_text("---\nname: sprocket-fact\n---\n\nMore.\n")
    records = [_record("widget-fact", 7), _record("sprocket-fact", 8)]
    (proposals_dir / "proposals.json").write_text(json.dumps(records))

    exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "added 2 of 2" in captured.out
    assert captured.err == ""
    entries = docket.load(path=proposals_dir.parent / "distil-memory-queue.json")["entries"]
    assert len(entries) == 2
    assert {entry["name"]: entry["file_text"] for entry in entries} == {
        "widget-fact": "---\nname: widget-fact\n---\n\nBody text.\n",
        "sprocket-fact": "---\nname: sprocket-fact\n---\n\nMore.\n",
    }


def test_main_save_reads_an_empty_proposals_list_as_nothing_to_add_not_as_a_refusal(
    tmp_path, monkeypatch, capsys, queue_path
):
    # A run that proposed nothing is a normal, successful run. Folding it into
    # the refusal path would make every quiet window look like a fault.
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "proposals.json").write_text("[]")

    exit_code = docket.main(
        ["save", "--proposals-dir", str(proposals_dir), "--queue", str(queue_path)]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "added 0 of 0" in captured.out
    assert captured.err == ""
    assert docket.load(path=queue_path)["entries"] == []


def _write_batch(proposals_dir, names, absent):
    """A proposals dir whose records are `names`, every sibling on disk except `absent`."""
    proposals_dir.mkdir()
    for name in names:
        if name != absent:
            (proposals_dir / f"{name}.md").write_text(f"---\nname: {name}\n---\n\nBody.\n")
    records = [_record(name, n) for n, name in enumerate(names, start=1)]
    (proposals_dir / "proposals.json").write_text(json.dumps(records))


def test_save_blames_only_the_absent_middle_sibling(tmp_path, monkeypatch, capsys, queue_path):
    # The failing record sits between two innocent ones, so a handler that
    # blames the first or the last record it saw names an innocent file.
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    _write_batch(proposals_dir, ["gear-note", "spindle-note", "lever-note"], absent="spindle-note")

    exit_code = docket.main(
        ["save", "--proposals-dir", str(proposals_dir), "--queue", str(queue_path)]
    )

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "spindle-note.md" in err
    assert "gear-note.md" not in err
    assert "lever-note.md" not in err


def test_save_never_partially_saves_after_three_readable_records(
    tmp_path, monkeypatch, capsys, queue_path
):
    # Three proposals are already built when the absent sibling is met, so a
    # refusal that keeps what it has would have something to save.
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    names = ["gear-note", "spindle-note", "lever-note", "ratchet-note"]
    _write_batch(proposals_dir, names, absent="ratchet-note")

    def _no_save(*args, **kwargs):
        pytest.fail("a refused batch reached the queue writer")

    monkeypatch.setattr(docket, "save", _no_save)
    monkeypatch.setattr(docket, "_save_queue", _no_save)

    exit_code = docket.main(
        ["save", "--proposals-dir", str(proposals_dir), "--queue", str(queue_path)]
    )

    assert exit_code == 1
    assert "ratchet-note.md" in capsys.readouterr().err
    assert docket.load(path=queue_path)["entries"] == []


def test_save_missing_dir_names_the_directory_not_proposals_json(
    tmp_path, monkeypatch, capsys, queue_path
):
    # What the operator has to fix is the directory; naming a file inside it
    # sends them looking for a file in a directory that is not there.
    monkeypatch.chdir(tmp_path)
    missing_dir = tmp_path / "gone"

    exit_code = docket.main(
        ["save", "--proposals-dir", str(missing_dir), "--queue", str(queue_path)]
    )

    assert exit_code == 1
    err = capsys.readouterr().err
    assert str(missing_dir) in err
    assert "proposals.json" not in err


# A decide whose --file cannot be read is a refusal (exit 1), not a queue fault
# (exit 2) and never a traceback. The two ways in: the path is absent, and the
# path is there but cannot be read as a file. A refusal is all-or-nothing: the
# entry stays undecided AND the sitting's lifetime cursor stays put, because a
# refusal that already counted a decision has half-applied. The wording of the
# message is not pinned, only that stderr carries something and that it names
# the file whose read actually failed, so one constant string cannot stand in
# for every fault. The filenames below differ from the ones the success tests
# use, so a guard keying on a literal name cannot pass.


def test_main_decide_refuses_a_file_flag_naming_a_missing_file_and_leaves_the_entry_undecided(
    tmp_path, monkeypatch, capsys, queue_path
):
    monkeypatch.chdir(tmp_path)
    docket.save(
        [_proposal(transcript="t.jsonl", line_no=1, file_text="original")], path=queue_path
    )
    entry_id = docket.slice_key("t.jsonl", 1)
    missing = tmp_path / "gone.md"
    assert not missing.exists()

    exit_code = docket.main(
        ["decide", entry_id, "kept", "--file", str(missing), "--queue", str(queue_path)]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    assert "gone.md" in captured.err
    assert captured.out == ""
    entry = docket.load(path=queue_path)["entries"][0]
    assert entry["decision"] == "undecided"
    assert entry["file_text"] == "original"


def test_main_decide_refusing_an_unreadable_file_writes_nothing_to_the_queue_file(
    tmp_path, monkeypatch, capsys, queue_path
):
    # All-or-nothing at its widest observable point: the queue file's bytes are
    # the same before and after. That subsumes the entry's decision, the
    # lifetime cursor, the sitting's own decision count, and any field added
    # later, so a refusal cannot half-apply through a counter no test names yet.
    # The cursor starts at 1, not 0, so a bump would read 2 and a reset 0.
    monkeypatch.chdir(tmp_path)
    docket.save(
        [_proposal(transcript="t.jsonl", line_no=n) for n in (1, 2)], path=queue_path
    )
    docket.decide(docket.slice_key("t.jsonl", 1), "kept", path=queue_path)
    cursor_before = docket.cursor(path=queue_path)
    assert cursor_before == 1
    queue_bytes_before = queue_path.read_bytes()

    exit_code = docket.main(
        [
            "decide",
            docket.slice_key("t.jsonl", 2),
            "kept",
            "--file",
            str(tmp_path / "vanished.md"),
            "--queue",
            str(queue_path),
        ]
    )

    assert exit_code == 1
    assert capsys.readouterr().err.strip() != ""
    assert queue_path.read_bytes() == queue_bytes_before
    assert docket.cursor(path=queue_path) == cursor_before
    second = next(e for e in docket.load(path=queue_path)["entries"] if e["line_no"] == 2)
    assert second["decision"] == "undecided"


def test_main_decide_names_the_file_whose_read_failed_rather_than_one_constant_message(
    tmp_path, monkeypatch, capsys, queue_path
):
    # Two refusals over two different absent paths: a cause-blind constant
    # message, or one that blames some other file, fails the second half.
    monkeypatch.chdir(tmp_path)
    docket.save(
        [_proposal(transcript="t.jsonl", line_no=n) for n in (1, 2)], path=queue_path
    )

    first_exit = docket.main(
        [
            "decide",
            docket.slice_key("t.jsonl", 1),
            "kept",
            "--file",
            str(tmp_path / "absent-alpha.md"),
            "--queue",
            str(queue_path),
        ]
    )

    assert first_exit == 1
    first_err = capsys.readouterr().err
    assert "absent-alpha.md" in first_err

    second_exit = docket.main(
        [
            "decide",
            docket.slice_key("t.jsonl", 2),
            "dropped",
            "--file",
            str(tmp_path / "absent-beta.md"),
            "--queue",
            str(queue_path),
        ]
    )

    assert second_exit == 1
    second_err = capsys.readouterr().err
    assert "absent-beta.md" in second_err
    assert "absent-alpha.md" not in second_err


def test_main_decide_refuses_a_file_flag_that_exists_but_cannot_be_read_as_a_file(
    tmp_path, monkeypatch, capsys, queue_path
):
    # "Missing" is not the whole fault: a path that is there but unreadable
    # crashes the same way, so a guard that only asks whether the path exists
    # is not enough. The message has to name the cause it actually met too, not
    # only echo back the argument it was handed: a path that is present and a
    # directory must not be reported as absent.
    monkeypatch.chdir(tmp_path)
    docket.save(
        [_proposal(transcript="t.jsonl", line_no=1, file_text="original")], path=queue_path
    )
    entry_id = docket.slice_key("t.jsonl", 1)
    unreadable = tmp_path / "not-a-file.md"
    unreadable.mkdir()
    assert unreadable.exists()

    exit_code = docket.main(
        ["decide", entry_id, "kept", "--file", str(unreadable), "--queue", str(queue_path)]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    assert "not-a-file.md" in captured.err
    assert "directory" in captured.err.lower()
    assert captured.out == ""
    entry = docket.load(path=queue_path)["entries"][0]
    assert entry["decision"] == "undecided"
    assert entry["file_text"] == "original"


def test_main_decide_refuses_a_regular_file_the_process_is_not_allowed_to_read(
    tmp_path, monkeypatch, capsys, queue_path, deny_access
):
    # A real file, of the right shape, that still cannot be read. Nothing about
    # the path says so, so only attempting the read finds this fault: a guard
    # that inspects the path instead of trying it crashes here.
    monkeypatch.chdir(tmp_path)
    docket.save(
        [_proposal(transcript="t.jsonl", line_no=1, file_text="original")], path=queue_path
    )
    entry_id = docket.slice_key("t.jsonl", 1)
    forbidden = tmp_path / "locked-note.md"
    forbidden.write_text("body nobody may read")
    deny_access(forbidden)
    assert forbidden.is_file()

    exit_code = docket.main(
        ["decide", entry_id, "kept", "--file", str(forbidden), "--queue", str(queue_path)]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    assert "locked-note.md" in captured.err
    assert captured.out == ""
    entry = docket.load(path=queue_path)["entries"][0]
    assert entry["decision"] == "undecided"
    assert entry["file_text"] == "original"


def test_main_decide_keeps_exit_2_for_the_queue_alone_and_answers_a_bad_file_with_exit_1(
    tmp_path, monkeypatch, capsys, queue_path
):
    # The boundary that matters: 2 means "the review queue file itself is
    # unreadable" and nothing else. A healthy queue with an unreadable --file
    # must answer with a different, smaller code, and a corrupt queue with a
    # perfectly readable --file must still answer 2.
    monkeypatch.chdir(tmp_path)
    corrupt_queue = tmp_path / "corrupt-queue.json"
    corrupt_queue.write_text('{"cursor": 0, "entries": [')
    readable = tmp_path / "still-here.md"
    readable.write_text("replacement body")

    queue_fault = docket.main(
        [
            "decide",
            docket.slice_key("t.jsonl", 1),
            "kept",
            "--file",
            str(readable),
            "--queue",
            str(corrupt_queue),
        ]
    )

    assert queue_fault == 2
    assert capsys.readouterr().err.strip() != ""

    docket.save(
        [_proposal(transcript="t.jsonl", line_no=1, file_text="original")], path=queue_path
    )

    file_fault = docket.main(
        [
            "decide",
            docket.slice_key("t.jsonl", 1),
            "kept",
            "--file",
            str(tmp_path / "never-written.md"),
            "--queue",
            str(queue_path),
        ]
    )

    assert file_fault == 1
    assert file_fault != queue_fault
    assert capsys.readouterr().err.strip() != ""
    assert docket.load(path=queue_path)["entries"][0]["decision"] == "undecided"


def test_main_decide_with_both_faults_at_once_reports_the_file_it_reaches_first(
    tmp_path, monkeypatch, capsys
):
    # Both the --file and the queue are broken. The command reads the file
    # first and the queue second, so the file fault is the one it meets and the
    # answer is the refusal, exit 1, naming that file. Pinning it stops the two
    # reads being reordered, which would silently turn every bad --file over a
    # shaky queue into a queue fault.
    monkeypatch.chdir(tmp_path)
    corrupt_queue = tmp_path / "also-corrupt-queue.json"
    corrupt_queue.write_text('{"cursor": 0, "entries": [')

    exit_code = docket.main(
        [
            "decide",
            docket.slice_key("t.jsonl", 1),
            "kept",
            "--file",
            str(tmp_path / "missing-too.md"),
            "--queue",
            str(corrupt_queue),
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "missing-too.md" in captured.err
    assert captured.out == ""


def test_main_decide_still_returns_zero_and_replaces_file_text_for_a_readable_file(
    tmp_path, monkeypatch, capsys, queue_path
):
    monkeypatch.chdir(tmp_path)
    docket.save(
        [_proposal(transcript="t.jsonl", line_no=1, file_text="original")], path=queue_path
    )
    entry_id = docket.slice_key("t.jsonl", 1)
    edited = tmp_path / "edited-note.md"
    edited.write_text("edited body")

    exit_code = docket.main(
        ["decide", entry_id, "kept", "--file", str(edited), "--queue", str(queue_path)]
    )

    assert exit_code == 0
    assert capsys.readouterr().err == ""
    entry = docket.load(path=queue_path)["entries"][0]
    assert entry["decision"] == "kept"
    assert entry["file_text"] == "edited body"
    assert docket.cursor(path=queue_path) == 1


def test_main_decide_without_a_file_flag_still_returns_zero_and_leaves_file_text_alone(
    tmp_path, monkeypatch, capsys, queue_path
):
    monkeypatch.chdir(tmp_path)
    docket.save(
        [_proposal(transcript="t.jsonl", line_no=1, file_text="original")], path=queue_path
    )
    entry_id = docket.slice_key("t.jsonl", 1)

    exit_code = docket.main(["decide", entry_id, "dropped", "--queue", str(queue_path)])

    assert exit_code == 0
    assert capsys.readouterr().err == ""
    entry = docket.load(path=queue_path)["entries"][0]
    assert entry["decision"] == "dropped"
    assert entry["file_text"] == "original"


# How decide treats the --file read itself: an empty note is a note, a refusal
# writes nothing at all, an interrupt is the user's and not a refusal, and the
# note is read once, before the queue is touched.


def _queue_with_one_entry(queue_path):
    docket.save(
        [_proposal(transcript="t.jsonl", line_no=1, file_text="original")], path=queue_path
    )
    return docket.slice_key("t.jsonl", 1)


def _counting_reads_of(monkeypatch, note):
    real_read_text = Path.read_text
    reads = []

    def _read_text(self, *args, **kwargs):
        if self == note:
            reads.append(self)
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _read_text)
    return reads


def test_decide_accepts_an_empty_file(tmp_path, monkeypatch, capsys, queue_path):
    # an empty note is still the text the user chose, not "no --file given"
    monkeypatch.chdir(tmp_path)
    entry_id = _queue_with_one_entry(queue_path)
    empty = tmp_path / "blank-note.md"
    empty.write_text("")

    exit_code = docket.main(
        ["decide", entry_id, "kept", "--file", str(empty), "--queue", str(queue_path)]
    )

    assert exit_code == 0
    assert capsys.readouterr().err == ""
    entry = docket.load(path=queue_path)["entries"][0]
    assert entry["decision"] == "kept"
    assert entry["file_text"] == ""


def test_decide_refusal_never_calls_save_queue(tmp_path, monkeypatch, capsys, queue_path):
    # equal bytes after a refusal could still be a load-and-save round trip,
    # which reverts any decision a peer wrote in between: forbid the write
    monkeypatch.chdir(tmp_path)
    entry_id = _queue_with_one_entry(queue_path)

    def _no_save(*args, **kwargs):
        pytest.fail("a refused decide wrote the queue")

    monkeypatch.setattr(docket, "_save_queue", _no_save)

    exit_code = docket.main(
        [
            "decide",
            entry_id,
            "kept",
            "--file",
            str(tmp_path / "nowhere.md"),
            "--queue",
            str(queue_path),
        ]
    )

    assert exit_code == 1
    assert "nowhere.md" in capsys.readouterr().err


def test_decide_propagates_keyboard_interrupt(tmp_path, monkeypatch, queue_path):
    monkeypatch.chdir(tmp_path)
    entry_id = _queue_with_one_entry(queue_path)
    note = tmp_path / "interrupted-note.md"
    note.write_text("body")
    real_read_text = Path.read_text

    def _interrupted(self, *args, **kwargs):
        if self == note:
            raise KeyboardInterrupt
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _interrupted)

    with pytest.raises(KeyboardInterrupt):
        docket.main(["decide", entry_id, "kept", "--file", str(note), "--queue", str(queue_path)])

    monkeypatch.setattr(Path, "read_text", real_read_text)
    assert docket.load(path=queue_path)["entries"][0]["decision"] == "undecided"


def test_decide_reads_the_file_once(tmp_path, monkeypatch, capsys, queue_path):
    # a second read can see different bytes than the first, so the text that
    # lands must come from the one read that was checked
    monkeypatch.chdir(tmp_path)
    entry_id = _queue_with_one_entry(queue_path)
    note = tmp_path / "read-once-note.md"
    note.write_text("edited body")
    reads = _counting_reads_of(monkeypatch, note)

    exit_code = docket.main(
        ["decide", entry_id, "kept", "--file", str(note), "--queue", str(queue_path)]
    )

    assert reads == [note]
    assert exit_code == 0
    assert capsys.readouterr().err == ""


def test_decide_both_faults_loads_nothing_before_refusing(tmp_path, monkeypatch, capsys):
    # the order of the two reads, not just which fault is reported: the
    # refusal must arrive before the queue is read at all
    monkeypatch.chdir(tmp_path)
    corrupt_queue = tmp_path / "broken-queue.json"
    corrupt_queue.write_text('{"cursor": 0, "entries": [')
    real_load = docket.load
    loads = []

    def _counting_load(*args, **kwargs):
        loads.append(args or kwargs)
        return real_load(*args, **kwargs)

    monkeypatch.setattr(docket, "load", _counting_load)

    exit_code = docket.main(
        [
            "decide",
            docket.slice_key("t.jsonl", 1),
            "kept",
            "--file",
            str(tmp_path / "absent-note.md"),
            "--queue",
            str(corrupt_queue),
        ]
    )

    assert exit_code == 1
    assert loads == []
    assert "absent-note.md" in capsys.readouterr().err

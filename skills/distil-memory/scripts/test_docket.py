"""Tests for docket.py: the proposal queue's persistence, undecided cursor,
rejection record, and per-run decision cap."""

import json
import os

import docket

import pytest

from docket_test_helpers import make_proposal as _proposal


@pytest.fixture
def queue_path(tmp_path):
    return tmp_path / "queue.json"


def _decide_until_capped(queue_path):
    decided = []
    while True:
        entry = docket.next_undecided(path=queue_path)
        if entry is None:
            break
        docket.decide(entry["id"], "kept", path=queue_path)
        decided.append(entry["id"])
    return decided


def test_slice_key_joins_transcript_and_line_no_with_a_colon():
    assert docket.slice_key("sessions/abc.jsonl", 42) == "sessions/abc.jsonl:42"


def test_load_of_a_missing_file_returns_an_empty_queue_without_raising(queue_path):
    assert not queue_path.exists()

    assert docket.load(path=queue_path) == {"cursor": 0, "entries": []}


def test_save_returns_the_count_of_newly_added_entries(queue_path):
    proposals = [_proposal(line_no=n) for n in range(1, 6)]

    added = docket.save(proposals, path=queue_path)

    assert added == 5
    assert len(docket.load(path=queue_path)["entries"]) == 5


def test_save_stamps_new_entries_with_id_undecided_decision_and_rubric_version(queue_path):
    docket.save([_proposal(transcript="t.jsonl", line_no=7, name="widget-fact")], path=queue_path)

    entry = docket.load(path=queue_path)["entries"][0]

    assert entry["id"] == docket.slice_key("t.jsonl", 7)
    assert entry["decision"] == "undecided"
    assert entry["rubric_version"] == docket.RUBRIC_VERSION
    assert entry["name"] == "widget-fact"
    assert entry["transcript"] == "t.jsonl"
    assert entry["line_no"] == 7


def test_save_skips_resubmitting_a_slice_key_already_queued_undecided(queue_path):
    proposal = _proposal(transcript="t.jsonl", line_no=3)
    docket.save([proposal], path=queue_path)

    added = docket.save([proposal], path=queue_path)

    assert added == 0
    assert len(docket.load(path=queue_path)["entries"]) == 1


def test_save_skips_resubmitting_a_slice_key_already_decided_kept(queue_path):
    proposal = _proposal(transcript="t.jsonl", line_no=4)
    docket.save([proposal], path=queue_path)
    docket.decide(docket.slice_key("t.jsonl", 4), "kept", path=queue_path)

    added = docket.save([proposal], path=queue_path)

    assert added == 0
    assert len(docket.load(path=queue_path)["entries"]) == 1


def test_save_skips_resubmitting_a_slice_key_already_decided_dropped(queue_path):
    # This is the unambiguous half of "a dropped proposal is filtered out on a
    # second run over the same window": same rubric version, same slice_key.
    proposal = _proposal(transcript="t.jsonl", line_no=5)
    docket.save([proposal], path=queue_path)
    docket.decide(docket.slice_key("t.jsonl", 5), "dropped", path=queue_path)

    added = docket.save([proposal], path=queue_path)

    assert added == 0
    assert len(docket.load(path=queue_path)["entries"]) == 1


def test_save_adds_a_new_entry_stamped_with_the_bumped_rubric_version_after_a_drop(
    queue_path, monkeypatch
):
    # The other half of "a dropped proposal is filtered out on a second run
    # over the same window; bumping the rubric version makes it eligible
    # again" - pinned end to end through save(), not just rejected().
    proposal = _proposal(transcript="t.jsonl", line_no=6)
    docket.save([proposal], path=queue_path)
    key = docket.slice_key("t.jsonl", 6)
    docket.decide(key, "dropped", path=queue_path)

    added_same_version = docket.save([proposal], path=queue_path)

    assert added_same_version == 0
    assert docket.rejected(key, "2", path=queue_path) is False

    monkeypatch.setattr(docket, "RUBRIC_VERSION", "2")
    added_after_bump = docket.save([proposal], path=queue_path)

    assert added_after_bump == 1
    matching_entries = [e for e in docket.load(path=queue_path)["entries"] if e["id"] == key]
    assert len(matching_entries) == 2
    new_entry = next(e for e in matching_entries if e["decision"] == "undecided")
    assert new_entry["rubric_version"] == "2"


def test_save_only_counts_the_genuinely_new_entries_in_a_mixed_batch(queue_path):
    already_queued = _proposal(transcript="t.jsonl", line_no=1)
    docket.save([already_queued], path=queue_path)

    added = docket.save(
        [already_queued, _proposal(transcript="t.jsonl", line_no=2)], path=queue_path
    )

    assert added == 1
    assert len(docket.load(path=queue_path)["entries"]) == 2


def test_next_undecided_returns_none_for_an_empty_queue(queue_path):
    assert docket.next_undecided(path=queue_path) is None


def test_next_undecided_returns_the_third_proposal_after_deciding_the_first_two_and_reloading(
    queue_path,
):
    proposals = [_proposal(transcript="t.jsonl", line_no=n) for n in range(1, 6)]
    docket.save(proposals, path=queue_path)

    first = docket.next_undecided(path=queue_path)
    docket.decide(first["id"], "kept", path=queue_path)

    second = docket.next_undecided(path=queue_path)
    docket.decide(second["id"], "dropped", path=queue_path)

    third = docket.next_undecided(path=queue_path)

    assert third["id"] == docket.slice_key("t.jsonl", 3)
    assert third["id"] not in {first["id"], second["id"]}


def test_next_undecided_never_returns_an_already_decided_entry_again(queue_path):
    proposals = [_proposal(transcript="t.jsonl", line_no=n) for n in range(1, 4)]
    docket.save(proposals, path=queue_path)

    seen = []
    for _ in range(3):
        entry = docket.next_undecided(path=queue_path)
        docket.decide(entry["id"], "kept", path=queue_path)
        seen.append(entry["id"])

    assert len(set(seen)) == 3
    assert docket.next_undecided(path=queue_path) is None


def test_decide_kept_sets_decision_and_increments_the_lifetime_cursor(queue_path):
    docket.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    entry_id = docket.slice_key("t.jsonl", 1)

    docket.decide(entry_id, "kept", path=queue_path)

    entry = docket.load(path=queue_path)["entries"][0]
    assert entry["decision"] == "kept"
    assert docket.cursor(path=queue_path) == 1


def test_decide_dropped_sets_decision_to_dropped(queue_path):
    docket.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    entry_id = docket.slice_key("t.jsonl", 1)

    docket.decide(entry_id, "dropped", path=queue_path)

    entry = docket.load(path=queue_path)["entries"][0]
    assert entry["decision"] == "dropped"


def test_decide_replaces_file_text_when_given(queue_path):
    docket.save(
        [_proposal(transcript="t.jsonl", line_no=1, file_text="original")], path=queue_path
    )
    entry_id = docket.slice_key("t.jsonl", 1)

    docket.decide(entry_id, "kept", file_text="edited", path=queue_path)

    entry = docket.load(path=queue_path)["entries"][0]
    assert entry["file_text"] == "edited"


def test_decide_leaves_file_text_untouched_when_not_given(queue_path):
    docket.save(
        [_proposal(transcript="t.jsonl", line_no=1, file_text="original")], path=queue_path
    )
    entry_id = docket.slice_key("t.jsonl", 1)

    docket.decide(entry_id, "kept", path=queue_path)

    entry = docket.load(path=queue_path)["entries"][0]
    assert entry["file_text"] == "original"


def test_decide_raises_for_an_unknown_entry_id(queue_path):
    docket.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)

    with pytest.raises(docket.QueueError):
        docket.decide("does-not-exist:99", "kept", path=queue_path)


def test_decide_raises_when_state_is_undecided(queue_path):
    docket.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    entry_id = docket.slice_key("t.jsonl", 1)

    with pytest.raises(docket.QueueError):
        docket.decide(entry_id, "undecided", path=queue_path)


def test_decide_raises_when_the_entry_is_already_decided(queue_path):
    docket.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    entry_id = docket.slice_key("t.jsonl", 1)
    docket.decide(entry_id, "kept", path=queue_path)

    with pytest.raises(docket.QueueError):
        docket.decide(entry_id, "dropped", path=queue_path)


def test_cursor_starts_at_zero_for_a_new_queue(queue_path):
    assert docket.cursor(path=queue_path) == 0


def test_cursor_counts_every_decide_call_over_the_queues_lifetime(queue_path):
    proposals = [_proposal(transcript="t.jsonl", line_no=n) for n in range(1, 4)]
    docket.save(proposals, path=queue_path)

    for n in range(1, 4):
        docket.decide(docket.slice_key("t.jsonl", n), "kept", path=queue_path)

    assert docket.cursor(path=queue_path) == 3


def test_advance_without_a_new_cursor_leaves_the_lifetime_cursor_unchanged(queue_path):
    docket.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    docket.decide(docket.slice_key("t.jsonl", 1), "kept", path=queue_path)

    docket.advance(path=queue_path)

    assert docket.cursor(path=queue_path) == 1


def test_advance_with_a_new_cursor_force_sets_the_lifetime_cursor(queue_path):
    docket.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    docket.decide(docket.slice_key("t.jsonl", 1), "kept", path=queue_path)

    docket.advance(new_cursor=99, path=queue_path)

    assert docket.cursor(path=queue_path) == 99


def test_advance_resets_session_progress_so_the_per_run_cap_unlocks_again(queue_path):
    proposals = [
        _proposal(transcript="t.jsonl", line_no=n) for n in range(1, docket.PER_RUN_CAP + 3)
    ]
    docket.save(proposals, path=queue_path)

    decided = set()
    for _ in range(docket.PER_RUN_CAP):
        entry = docket.next_undecided(path=queue_path)
        docket.decide(entry["id"], "kept", path=queue_path)
        decided.add(entry["id"])

    # Cap reached: undecided entries remain, but next_undecided must not hand
    # out an eleventh in this sitting.
    assert docket.next_undecided(path=queue_path) is None

    docket.advance(path=queue_path)

    entry = docket.next_undecided(path=queue_path)
    assert entry is not None
    assert entry["decision"] == "undecided"
    assert entry["id"] not in decided


def test_advance_with_new_cursor_also_resets_session_progress(queue_path):
    proposals = [
        _proposal(transcript="t.jsonl", line_no=n) for n in range(1, docket.PER_RUN_CAP + 3)
    ]
    docket.save(proposals, path=queue_path)

    for _ in range(docket.PER_RUN_CAP):
        entry = docket.next_undecided(path=queue_path)
        docket.decide(entry["id"], "kept", path=queue_path)

    assert docket.next_undecided(path=queue_path) is None

    docket.advance(new_cursor=500, path=queue_path)

    assert docket.cursor(path=queue_path) == 500
    assert docket.next_undecided(path=queue_path) is not None


def test_per_run_cap_yields_ten_of_twenty_five_and_a_second_run_advances_past_them(queue_path):
    # The cap is PER SITTING, not a one-time gate: advance() "unlocks the next
    # PER_RUN_CAP calls" (the module's own advance() contract), so a queue of
    # 25 is drainable over SEVERAL capped sittings (10 + 10 + 5), matching the
    # PRD's stated "several capped runs" scenario for large batches. A second
    # run of unlimited length (deciding all 15 remaining without a second
    # advance()) would require the cap to disappear after one lift, which
    # contradicts "unlocking the NEXT PER_RUN_CAP calls."
    proposals = [_proposal(transcript="t.jsonl", line_no=n) for n in range(1, 26)]
    docket.save(proposals, path=queue_path)

    decided_first_run = _decide_until_capped(queue_path)

    assert len(decided_first_run) == docket.PER_RUN_CAP
    assert docket.cursor(path=queue_path) == 10

    remaining_after_first_run = [
        e for e in docket.load(path=queue_path)["entries"] if e["decision"] == "undecided"
    ]
    assert len(remaining_after_first_run) == 15

    docket.advance(path=queue_path)
    decided_second_run = _decide_until_capped(queue_path)

    # "a second run advances past them" (verbatim PRD acceptance text): the
    # cursor must move past the first 10, but a second capped sitting cannot
    # drain more than PER_RUN_CAP more even though 15 remain.
    assert len(decided_second_run) == docket.PER_RUN_CAP
    assert docket.cursor(path=queue_path) == 20
    assert set(decided_first_run).isdisjoint(decided_second_run)

    remaining_after_second_run = [
        e for e in docket.load(path=queue_path)["entries"] if e["decision"] == "undecided"
    ]
    assert len(remaining_after_second_run) == 5

    docket.advance(path=queue_path)
    decided_third_run = _decide_until_capped(queue_path)

    assert len(decided_third_run) == 5
    assert docket.cursor(path=queue_path) == 25
    all_decided = set(decided_first_run) | set(decided_second_run) | set(decided_third_run)
    assert len(all_decided) == 25


def test_rejected_is_false_for_an_unknown_key(queue_path):
    assert docket.rejected("nothing:1", docket.RUBRIC_VERSION, path=queue_path) is False


def test_rejected_is_false_when_the_entry_is_not_dropped(queue_path):
    docket.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    key = docket.slice_key("t.jsonl", 1)

    assert docket.rejected(key, docket.RUBRIC_VERSION, path=queue_path) is False

    docket.decide(key, "kept", path=queue_path)

    assert docket.rejected(key, docket.RUBRIC_VERSION, path=queue_path) is False


def test_rejected_is_true_for_a_dropped_entry_at_the_same_rubric_version(queue_path):
    docket.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    key = docket.slice_key("t.jsonl", 1)
    docket.decide(key, "dropped", path=queue_path)

    assert docket.rejected(key, docket.RUBRIC_VERSION, path=queue_path) is True


def test_rejected_is_false_when_the_rubric_version_does_not_match(queue_path):
    # The unambiguous half of "bumping the rubric version makes it eligible
    # again": rejected() itself must stop reporting a rejection once the
    # caller asks about a different rubric version.
    docket.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    key = docket.slice_key("t.jsonl", 1)
    docket.decide(key, "dropped", path=queue_path)

    assert docket.rejected(key, "some-other-version", path=queue_path) is False


def test_a_corrupt_queue_is_named_as_corrupt_rather_than_read_as_drained(queue_path):
    queue_path.write_text('{"cursor": 0, "entries": [')

    with pytest.raises(docket.QueueError):
        docket.next_undecided(path=queue_path)


def test_an_empty_queue_file_is_named_as_corrupt_rather_than_read_as_drained(queue_path):
    queue_path.write_text("")

    with pytest.raises(docket.QueueError) as exc_info:
        docket.next_undecided(path=queue_path)

    message = str(exc_info.value)
    assert message
    assert "empty" in message.lower()


def test_a_top_level_json_list_is_named_as_corrupt_rather_than_read_as_drained(queue_path):
    queue_path.write_text("[]")

    with pytest.raises(docket.QueueError) as exc_info:
        docket.next_undecided(path=queue_path)

    message = str(exc_info.value)
    assert message
    assert any(hint in message.lower() for hint in ("dict", "object", "mapping", "list"))


def test_a_queue_missing_the_entries_key_is_named_as_corrupt_rather_than_read_as_drained(
    queue_path,
):
    queue_path.write_text('{"cursor": 0}')

    with pytest.raises(docket.QueueError) as exc_info:
        docket.next_undecided(path=queue_path)

    message = str(exc_info.value)
    assert message
    assert "entries" in message.lower()


def test_a_non_dict_entry_in_entries_is_named_as_corrupt_rather_than_read_as_drained(queue_path):
    queue_path.write_text('{"cursor": 0, "entries": ["not-a-dict"]}')

    with pytest.raises(docket.QueueError) as exc_info:
        docket.next_undecided(path=queue_path)

    message = str(exc_info.value)
    assert message
    assert any(hint in message.lower() for hint in ("entry", "entries", "dict"))


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
    readable_record = {
        "name": "gadget-note",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 7,
        "evidence_text": "evidence for gadget",
        "existing_text": None,
        "file": "gadget-note.md",
    }
    absent_record = {
        "name": "cog-note",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 8,
        "evidence_text": "evidence for cog",
        "existing_text": None,
        "file": "never-written.md",
    }
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
    record = {
        "name": "flange-fact",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 7,
        "evidence_text": "evidence for flange",
        "existing_text": None,
        "file": "flange-fact.md",
    }
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
    records = [
        {
            "name": "widget-fact",
            "kind": "new",
            "transcript": "t.jsonl",
            "line_no": 7,
            "evidence_text": "evidence for widget",
            "existing_text": None,
            "file": "widget-fact.md",
        },
        {
            "name": "sprocket-fact",
            "kind": "new",
            "transcript": "t.jsonl",
            "line_no": 8,
            "evidence_text": "evidence for sprocket",
            "existing_text": None,
            "file": "sprocket-fact.md",
        },
    ]
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


@pytest.mark.skipif(
    os.geteuid() == 0, reason="root reads a mode 000 file, so there is no refusal to observe"
)
def test_main_decide_refuses_a_regular_file_the_process_is_not_allowed_to_read(
    tmp_path, monkeypatch, capsys, queue_path
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
    forbidden.chmod(0o000)
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

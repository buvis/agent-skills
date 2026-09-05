"""Tests for docket.py: the proposal queue's persistence, undecided cursor,
rejection record, and per-run decision cap."""

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

    entries = docket.load()["entries"]
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
    entries = docket.load()["entries"]
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
    entries = docket.load()["entries"]
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
    entries = docket.load()["entries"]
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
    entries = docket.load()["entries"]
    assert len(entries) == 2
    entry_a = next(e for e in entries if e["name"] == "fact-a")
    entry_b = next(e for e in entries if e["name"] == "fact-b")
    assert entry_a["dedup_error"] == "ambiguous match against fact-a-old"
    assert entry_b["dedup_error"] is None


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


# main() exit codes for an unreadable queue. Exit 1 means "nothing left to
# decide" (drained or capped), exit 2 means "the queue could not be read", so a
# caller polling `next` can tell a finished walkthrough from a broken one.
#
# Two techniques below, on purpose. `next` (the primary caller) and `decide`
# (the only subcommand that also has an exit 1 of its own) go through a REAL
# corrupt file on disk, over every corruption shape load() recognises, so the
# unmocked path is proved end to end and no single byte string can be
# special-cased. `cursor`, `start`, `save` and one extra `decide` case make
# load() raise a QueueError carrying a sentinel string this file could not
# otherwise produce, which pins the reported message to the exception that was
# actually raised rather than to one the test (or the implementation) could
# reconstruct from the queue file.


_CORRUPT_QUEUE_SHAPES = {
    "truncated-json": '{"cursor": 0, "entries": [',
    "truncated-json-trailing-newline": '{"cursor": 0, "entries": [\n',
    "empty-file": "",
    "top-level-list": "[]",
    "missing-entries-key": '{"cursor": 0}',
    "non-dict-entry": '{"cursor": 0, "entries": ["not-a-dict"]}',
}


def _corrupt_the_working_directory_queue(tmp_path, text):
    queue_file = tmp_path / "dev" / "local" / "audit-results" / "distil-memory-queue.json"
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    queue_file.write_text(text)
    return queue_file


def _corrupt_queue_error_message():
    try:
        docket.load()
    except docket.QueueError as exc:
        return str(exc)
    pytest.fail("expected docket.load to raise QueueError for a corrupt queue file")


def _load_raising(message):
    """A stand-in for docket.load() that fails the way a corrupt queue file
    makes it fail, with a message no other code path could invent."""

    def _explode(path=None):
        raise docket.QueueError(message)

    return _explode


@pytest.mark.parametrize(
    "corrupt_text", list(_CORRUPT_QUEUE_SHAPES.values()), ids=list(_CORRUPT_QUEUE_SHAPES)
)
def test_main_next_returns_two_and_reports_the_error_when_the_queue_is_unreadable(
    corrupt_text, tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    _corrupt_the_working_directory_queue(tmp_path, corrupt_text)
    expected_message = _corrupt_queue_error_message()

    exit_code = docket.main(["next"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_cursor_returns_two_and_reports_the_error_when_the_queue_is_unreadable(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    sentinel = "cursor-cannot-read-the-queue-9f3c1a"
    monkeypatch.setattr(docket, "load", _load_raising(sentinel))

    exit_code = docket.main(["cursor"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert sentinel in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_start_returns_two_and_reports_the_error_when_the_queue_is_unreadable(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    sentinel = "start-cannot-read-the-queue-2b7e40"
    monkeypatch.setattr(docket, "load", _load_raising(sentinel))

    exit_code = docket.main(["start"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert sentinel in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_save_returns_two_and_reports_the_error_when_the_queue_is_unreadable(
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
        "existing_text": None,
        "file": "widget-fact.md",
    }
    (proposals_dir / "proposals.json").write_text(json.dumps([record]))
    sentinel = "save-cannot-read-the-queue-c05d86"
    monkeypatch.setattr(docket, "load", _load_raising(sentinel))

    exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert sentinel in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


_DECIDE_UNREADABLE_QUEUE_CASES = {
    **{
        f"corrupt-file-{shape}": ("corrupt-file", text)
        for shape, text in _CORRUPT_QUEUE_SHAPES.items()
    },
    # A sentinel worded like a refused decision ("no undecided entry with id
    # ..." is what a refusal reads like). The split between exit 1 and exit 2
    # has to follow which call failed, not which words the message happens to
    # carry, so this must still be exit 2.
    "load-raises-a-refusal-shaped-message": (
        "load-raises",
        "decide-entry-lookup-failed-6a41ef",
    ),
}


@pytest.mark.parametrize(
    "failure,payload",
    list(_DECIDE_UNREADABLE_QUEUE_CASES.values()),
    ids=list(_DECIDE_UNREADABLE_QUEUE_CASES),
)
def test_main_decide_returns_two_rather_than_one_when_the_queue_is_unreadable(
    failure, payload, tmp_path, monkeypatch, capsys
):
    # A refused decision against a readable queue stays exit 1 (tested above);
    # a queue that cannot be read at all is a different failure and must not be
    # reported as one more refusal, whatever its message says.
    monkeypatch.chdir(tmp_path)
    if failure == "corrupt-file":
        _corrupt_the_working_directory_queue(tmp_path, payload)
        expected_message = _corrupt_queue_error_message()
    else:
        monkeypatch.setattr(docket, "load", _load_raising(payload))
        expected_message = payload

    exit_code = docket.main(["decide", docket.slice_key("t.jsonl", 1), "kept"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_decide_does_not_report_a_missing_file_argument_as_an_unreadable_queue(
    tmp_path, monkeypatch
):
    # Exit 2 means "the queue could not be read", not "something went wrong":
    # a --file path that does not exist has nothing to do with the queue, so it
    # must not be swallowed into that exit code.
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(transcript="t.jsonl", line_no=1)])
    entry_id = docket.slice_key("t.jsonl", 1)

    with pytest.raises(FileNotFoundError):
        docket.main(["decide", entry_id, "kept", "--file", str(tmp_path / "does-not-exist.md")])


def test_main_next_still_returns_one_with_empty_stdout_when_every_entry_is_decided(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(transcript="t.jsonl", line_no=n) for n in range(1, 3)])
    for n in range(1, 3):
        docket.decide(docket.slice_key("t.jsonl", n), "kept")
    capsys.readouterr()

    exit_code = docket.main(["next"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""

"""Tests for queue.py: the proposal queue's persistence, undecided cursor,
rejection record, and per-run decision cap."""

import queue

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


def test_per_run_cap_constant_is_ten():
    assert queue.PER_RUN_CAP == 10


def test_rubric_version_constant_is_one():
    assert queue.RUBRIC_VERSION == "1"


def test_slice_key_joins_transcript_and_line_no_with_a_colon():
    assert queue.slice_key("sessions/abc.jsonl", 42) == "sessions/abc.jsonl:42"


def test_load_of_a_missing_file_returns_an_empty_queue_without_raising(queue_path):
    assert not queue_path.exists()

    assert queue.load(path=queue_path) == {"cursor": 0, "entries": []}


def test_save_returns_the_count_of_newly_added_entries(queue_path):
    proposals = [_proposal(line_no=n) for n in range(1, 6)]

    added = queue.save(proposals, path=queue_path)

    assert added == 5
    assert len(queue.load(path=queue_path)["entries"]) == 5


def test_save_stamps_new_entries_with_id_undecided_decision_and_rubric_version(queue_path):
    queue.save([_proposal(transcript="t.jsonl", line_no=7, name="widget-fact")], path=queue_path)

    entry = queue.load(path=queue_path)["entries"][0]

    assert entry["id"] == queue.slice_key("t.jsonl", 7)
    assert entry["decision"] == "undecided"
    assert entry["rubric_version"] == queue.RUBRIC_VERSION
    assert entry["name"] == "widget-fact"
    assert entry["transcript"] == "t.jsonl"
    assert entry["line_no"] == 7


def test_save_skips_resubmitting_a_slice_key_already_queued_undecided(queue_path):
    proposal = _proposal(transcript="t.jsonl", line_no=3)
    queue.save([proposal], path=queue_path)

    added = queue.save([proposal], path=queue_path)

    assert added == 0
    assert len(queue.load(path=queue_path)["entries"]) == 1


def test_save_skips_resubmitting_a_slice_key_already_decided_kept(queue_path):
    proposal = _proposal(transcript="t.jsonl", line_no=4)
    queue.save([proposal], path=queue_path)
    queue.decide(queue.slice_key("t.jsonl", 4), "kept", path=queue_path)

    added = queue.save([proposal], path=queue_path)

    assert added == 0
    assert len(queue.load(path=queue_path)["entries"]) == 1


def test_save_skips_resubmitting_a_slice_key_already_decided_dropped(queue_path):
    # This is the unambiguous half of "a dropped proposal is filtered out on a
    # second run over the same window": same rubric version, same slice_key.
    proposal = _proposal(transcript="t.jsonl", line_no=5)
    queue.save([proposal], path=queue_path)
    queue.decide(queue.slice_key("t.jsonl", 5), "dropped", path=queue_path)

    added = queue.save([proposal], path=queue_path)

    assert added == 0
    assert len(queue.load(path=queue_path)["entries"]) == 1


def test_save_adds_a_new_entry_stamped_with_the_bumped_rubric_version_after_a_drop(
    queue_path, monkeypatch
):
    # The other half of "a dropped proposal is filtered out on a second run
    # over the same window; bumping the rubric version makes it eligible
    # again" - pinned end to end through save(), not just rejected().
    proposal = _proposal(transcript="t.jsonl", line_no=6)
    queue.save([proposal], path=queue_path)
    key = queue.slice_key("t.jsonl", 6)
    queue.decide(key, "dropped", path=queue_path)

    added_same_version = queue.save([proposal], path=queue_path)

    assert added_same_version == 0
    assert queue.rejected(key, "2", path=queue_path) is False

    monkeypatch.setattr(queue, "RUBRIC_VERSION", "2")
    added_after_bump = queue.save([proposal], path=queue_path)

    assert added_after_bump == 1
    matching_entries = [e for e in queue.load(path=queue_path)["entries"] if e["id"] == key]
    assert len(matching_entries) == 2
    new_entry = next(e for e in matching_entries if e["decision"] == "undecided")
    assert new_entry["rubric_version"] == "2"


def test_save_only_counts_the_genuinely_new_entries_in_a_mixed_batch(queue_path):
    already_queued = _proposal(transcript="t.jsonl", line_no=1)
    queue.save([already_queued], path=queue_path)

    added = queue.save(
        [already_queued, _proposal(transcript="t.jsonl", line_no=2)], path=queue_path
    )

    assert added == 1
    assert len(queue.load(path=queue_path)["entries"]) == 2


def test_next_undecided_returns_none_for_an_empty_queue(queue_path):
    assert queue.next_undecided(path=queue_path) is None


def test_next_undecided_returns_the_third_proposal_after_deciding_the_first_two_and_reloading(
    queue_path,
):
    proposals = [_proposal(transcript="t.jsonl", line_no=n) for n in range(1, 6)]
    queue.save(proposals, path=queue_path)

    first = queue.next_undecided(path=queue_path)
    queue.decide(first["id"], "kept", path=queue_path)

    second = queue.next_undecided(path=queue_path)
    queue.decide(second["id"], "dropped", path=queue_path)

    third = queue.next_undecided(path=queue_path)

    assert third["id"] == queue.slice_key("t.jsonl", 3)
    assert third["id"] not in {first["id"], second["id"]}


def test_next_undecided_never_returns_an_already_decided_entry_again(queue_path):
    proposals = [_proposal(transcript="t.jsonl", line_no=n) for n in range(1, 4)]
    queue.save(proposals, path=queue_path)

    seen = []
    for _ in range(3):
        entry = queue.next_undecided(path=queue_path)
        queue.decide(entry["id"], "kept", path=queue_path)
        seen.append(entry["id"])

    assert len(set(seen)) == 3
    assert queue.next_undecided(path=queue_path) is None


def test_decide_kept_sets_decision_and_increments_the_lifetime_cursor(queue_path):
    queue.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    entry_id = queue.slice_key("t.jsonl", 1)

    queue.decide(entry_id, "kept", path=queue_path)

    entry = queue.load(path=queue_path)["entries"][0]
    assert entry["decision"] == "kept"
    assert queue.cursor(path=queue_path) == 1


def test_decide_dropped_sets_decision_to_dropped(queue_path):
    queue.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    entry_id = queue.slice_key("t.jsonl", 1)

    queue.decide(entry_id, "dropped", path=queue_path)

    entry = queue.load(path=queue_path)["entries"][0]
    assert entry["decision"] == "dropped"


def test_decide_replaces_file_text_when_given(queue_path):
    queue.save(
        [_proposal(transcript="t.jsonl", line_no=1, file_text="original")], path=queue_path
    )
    entry_id = queue.slice_key("t.jsonl", 1)

    queue.decide(entry_id, "kept", file_text="edited", path=queue_path)

    entry = queue.load(path=queue_path)["entries"][0]
    assert entry["file_text"] == "edited"


def test_decide_leaves_file_text_untouched_when_not_given(queue_path):
    queue.save(
        [_proposal(transcript="t.jsonl", line_no=1, file_text="original")], path=queue_path
    )
    entry_id = queue.slice_key("t.jsonl", 1)

    queue.decide(entry_id, "kept", path=queue_path)

    entry = queue.load(path=queue_path)["entries"][0]
    assert entry["file_text"] == "original"


def test_decide_raises_for_an_unknown_entry_id(queue_path):
    queue.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)

    with pytest.raises(queue.QueueError):
        queue.decide("does-not-exist:99", "kept", path=queue_path)


def test_decide_raises_when_state_is_undecided(queue_path):
    queue.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    entry_id = queue.slice_key("t.jsonl", 1)

    with pytest.raises(queue.QueueError):
        queue.decide(entry_id, "undecided", path=queue_path)


def test_decide_raises_when_the_entry_is_already_decided(queue_path):
    queue.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    entry_id = queue.slice_key("t.jsonl", 1)
    queue.decide(entry_id, "kept", path=queue_path)

    with pytest.raises(queue.QueueError):
        queue.decide(entry_id, "dropped", path=queue_path)


def test_cursor_starts_at_zero_for_a_new_queue(queue_path):
    assert queue.cursor(path=queue_path) == 0


def test_cursor_counts_every_decide_call_over_the_queues_lifetime(queue_path):
    proposals = [_proposal(transcript="t.jsonl", line_no=n) for n in range(1, 4)]
    queue.save(proposals, path=queue_path)

    for n in range(1, 4):
        queue.decide(queue.slice_key("t.jsonl", n), "kept", path=queue_path)

    assert queue.cursor(path=queue_path) == 3


def test_advance_without_a_new_cursor_leaves_the_lifetime_cursor_unchanged(queue_path):
    queue.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    queue.decide(queue.slice_key("t.jsonl", 1), "kept", path=queue_path)

    queue.advance(path=queue_path)

    assert queue.cursor(path=queue_path) == 1


def test_advance_with_a_new_cursor_force_sets_the_lifetime_cursor(queue_path):
    queue.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    queue.decide(queue.slice_key("t.jsonl", 1), "kept", path=queue_path)

    queue.advance(new_cursor=99, path=queue_path)

    assert queue.cursor(path=queue_path) == 99


def test_advance_resets_session_progress_so_the_per_run_cap_unlocks_again(queue_path):
    proposals = [
        _proposal(transcript="t.jsonl", line_no=n) for n in range(1, queue.PER_RUN_CAP + 3)
    ]
    queue.save(proposals, path=queue_path)

    decided = set()
    for _ in range(queue.PER_RUN_CAP):
        entry = queue.next_undecided(path=queue_path)
        queue.decide(entry["id"], "kept", path=queue_path)
        decided.add(entry["id"])

    # Cap reached: undecided entries remain, but next_undecided must not hand
    # out an eleventh in this sitting.
    assert queue.next_undecided(path=queue_path) is None

    queue.advance(path=queue_path)

    entry = queue.next_undecided(path=queue_path)
    assert entry is not None
    assert entry["decision"] == "undecided"
    assert entry["id"] not in decided


def test_advance_with_new_cursor_also_resets_session_progress(queue_path):
    proposals = [
        _proposal(transcript="t.jsonl", line_no=n) for n in range(1, queue.PER_RUN_CAP + 3)
    ]
    queue.save(proposals, path=queue_path)

    for _ in range(queue.PER_RUN_CAP):
        entry = queue.next_undecided(path=queue_path)
        queue.decide(entry["id"], "kept", path=queue_path)

    assert queue.next_undecided(path=queue_path) is None

    queue.advance(new_cursor=500, path=queue_path)

    assert queue.cursor(path=queue_path) == 500
    assert queue.next_undecided(path=queue_path) is not None


def test_per_run_cap_yields_ten_of_twenty_five_and_a_second_run_advances_past_them(queue_path):
    # The cap is PER SITTING, not a one-time gate: advance() "unlocks the next
    # PER_RUN_CAP calls" (the module's own advance() contract), so a queue of
    # 25 is drainable over SEVERAL capped sittings (10 + 10 + 5), matching the
    # PRD's stated "several capped runs" scenario for large batches. A second
    # run of unlimited length (deciding all 15 remaining without a second
    # advance()) would require the cap to disappear after one lift, which
    # contradicts "unlocking the NEXT PER_RUN_CAP calls."
    proposals = [_proposal(transcript="t.jsonl", line_no=n) for n in range(1, 26)]
    queue.save(proposals, path=queue_path)

    def _decide_until_capped():
        decided = []
        while True:
            entry = queue.next_undecided(path=queue_path)
            if entry is None:
                break
            queue.decide(entry["id"], "kept", path=queue_path)
            decided.append(entry["id"])
        return decided

    decided_first_run = _decide_until_capped()

    assert len(decided_first_run) == queue.PER_RUN_CAP
    assert queue.cursor(path=queue_path) == 10

    remaining_after_first_run = [
        e for e in queue.load(path=queue_path)["entries"] if e["decision"] == "undecided"
    ]
    assert len(remaining_after_first_run) == 15

    queue.advance(path=queue_path)
    decided_second_run = _decide_until_capped()

    # "a second run advances past them" (verbatim PRD acceptance text): the
    # cursor must move past the first 10, but a second capped sitting cannot
    # drain more than PER_RUN_CAP more even though 15 remain.
    assert len(decided_second_run) == queue.PER_RUN_CAP
    assert queue.cursor(path=queue_path) == 20
    assert set(decided_first_run).isdisjoint(decided_second_run)

    remaining_after_second_run = [
        e for e in queue.load(path=queue_path)["entries"] if e["decision"] == "undecided"
    ]
    assert len(remaining_after_second_run) == 5

    queue.advance(path=queue_path)
    decided_third_run = _decide_until_capped()

    assert len(decided_third_run) == 5
    assert queue.cursor(path=queue_path) == 25
    all_decided = set(decided_first_run) | set(decided_second_run) | set(decided_third_run)
    assert len(all_decided) == 25


def test_rejected_is_false_for_an_unknown_key(queue_path):
    assert queue.rejected("nothing:1", queue.RUBRIC_VERSION, path=queue_path) is False


def test_rejected_is_false_when_the_entry_is_not_dropped(queue_path):
    queue.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    key = queue.slice_key("t.jsonl", 1)

    assert queue.rejected(key, queue.RUBRIC_VERSION, path=queue_path) is False

    queue.decide(key, "kept", path=queue_path)

    assert queue.rejected(key, queue.RUBRIC_VERSION, path=queue_path) is False


def test_rejected_is_true_for_a_dropped_entry_at_the_same_rubric_version(queue_path):
    queue.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    key = queue.slice_key("t.jsonl", 1)
    queue.decide(key, "dropped", path=queue_path)

    assert queue.rejected(key, queue.RUBRIC_VERSION, path=queue_path) is True


def test_rejected_is_false_when_the_rubric_version_does_not_match(queue_path):
    # The unambiguous half of "bumping the rubric version makes it eligible
    # again": rejected() itself must stop reporting a rejection once the
    # caller asks about a different rubric version.
    queue.save([_proposal(transcript="t.jsonl", line_no=1)], path=queue_path)
    key = queue.slice_key("t.jsonl", 1)
    queue.decide(key, "dropped", path=queue_path)

    assert queue.rejected(key, "some-other-version", path=queue_path) is False

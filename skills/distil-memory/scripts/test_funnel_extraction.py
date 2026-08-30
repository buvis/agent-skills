"""Tests for funnel.py's transcript-extraction path: assistant_only, its
private helpers (_iter_entries, _assistant_text_blocks, _MARKER_RE, Slice,
_raw_marker_hits), and the scan()/slice_on_markers() pipeline built on them."""

import dataclasses
import json
from pathlib import Path

import funnel
import pytest


def test_assistant_only_excludes_entries_that_are_not_assistant_type():
    entries = [(1, {"type": "user", "message": {"content": "hello there"}})]

    result = funnel.assistant_only(entries)

    assert result == []


def test_assistant_only_excludes_meta_entries_even_with_real_text():
    entry = {
        "type": "assistant",
        "isMeta": True,
        "message": {"content": [{"type": "text", "text": "meta commentary"}]},
    }

    result = funnel.assistant_only([(1, entry)])

    assert result == []


@pytest.mark.parametrize(
    "compaction_fields",
    [
        {"isCompactSummary": True},
        {"subtype": "compact_boundary"},
        {"attachment": {"type": "compact-summary"}},
    ],
    ids=["isCompactSummary_flag", "subtype_contains_compact", "attachment_type_contains_compact"],
)
def test_assistant_only_excludes_compaction_summary_entries_even_with_real_text(compaction_fields):
    entry = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "summary of prior turns"}]},
        **compaction_fields,
    }

    result = funnel.assistant_only([(1, entry)])

    assert result == []


def test_assistant_only_drops_non_text_block_but_keeps_sibling_text_block():
    entry = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": {}},
                {"type": "text", "text": "here is my actual reply"},
            ]
        },
    }

    result = funnel.assistant_only([(1, entry)])

    assert result == [(1, "here is my actual reply")]


@pytest.mark.parametrize("blank_text", ["", "   "])
def test_assistant_only_excludes_empty_or_whitespace_only_text_blocks(blank_text):
    entry = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": blank_text}]},
    }

    result = funnel.assistant_only([(1, entry)])

    assert result == []


def test_iter_entries_yields_valid_lines_in_order_with_one_indexed_line_numbers_skipping_blank_and_invalid_json(
    tmp_path,
):
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        json.dumps({"type": "user", "text": "first"})
        + "\n"
        + "\n"
        + "not valid json{{{\n"
        + json.dumps({"type": "assistant", "text": "second"})
        + "\n"
    )

    result = list(funnel._iter_entries(path))

    assert result == [
        (1, {"type": "user", "text": "first"}),
        (4, {"type": "assistant", "text": "second"}),
    ]


def test_assistant_text_blocks_returns_single_element_list_when_content_is_a_plain_string():
    entry = {"type": "assistant", "message": {"content": "just a plain string reply"}}

    result = funnel._assistant_text_blocks(entry)

    assert result == ["just a plain string reply"]


def test_assistant_text_blocks_returns_empty_list_for_non_assistant_entry():
    entry = {"type": "user", "message": {"content": "hello there"}}

    result = funnel._assistant_text_blocks(entry)

    assert result == []


@pytest.mark.parametrize(
    "word",
    ["measured", "Verified", "CONFIRMED", "Reproduced", "PROVEN"],
)
def test_marker_re_matches_each_marker_word_case_insensitively(word):
    match = funnel._MARKER_RE.search(word)

    assert match is not None
    assert match.group(0) == word


def test_marker_re_does_not_match_word_that_merely_contains_a_marker_as_unbounded_substring():
    assert funnel._MARKER_RE.search("provenance") is None


def test_slice_exposes_text_transcript_line_no_and_marker_fields():
    path = Path("session.jsonl")

    slice_ = funnel.Slice(text="we measured this", transcript=path, line_no=5, marker="measured")

    assert slice_.text == "we measured this"
    assert slice_.transcript == path
    assert slice_.line_no == 5
    assert slice_.marker == "measured"


def test_slice_is_frozen_and_raises_on_field_mutation():
    slice_ = funnel.Slice(text="we measured this", transcript=Path("session.jsonl"), line_no=5, marker="measured")

    with pytest.raises(dataclasses.FrozenInstanceError):
        slice_.marker = "confirmed"


def test_raw_marker_hits_counts_one_hit_per_assistant_text_block():
    entries = [
        (1, {"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}}),
        (2, {"type": "assistant", "message": {"content": [{"type": "text", "text": "and confirmed that"}]}}),
    ]

    result = funnel._raw_marker_hits(entries)

    assert result == 2


def test_raw_marker_hits_counts_multiple_markers_within_a_single_text_block_as_one_hit():
    entries = [
        (
            1,
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "measured, confirmed, and reproduced"}]},
            },
        ),
    ]

    result = funnel._raw_marker_hits(entries)

    assert result == 1


@pytest.mark.parametrize(
    "exclusion_fields",
    [
        {"isMeta": True},
        {"isCompactSummary": True},
    ],
    ids=["isMeta_entry", "compaction_summary_entry"],
)
def test_raw_marker_hits_counts_hits_inside_entries_that_assistant_only_would_exclude(exclusion_fields):
    entry = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "confirmed in summary"}]},
        **exclusion_fields,
    }

    result = funnel._raw_marker_hits([(1, entry)])

    assert result == 1


def test_raw_marker_hits_ignores_non_assistant_entries():
    entries = [(1, {"type": "user", "message": {"content": "we measured this"}})]

    result = funnel._raw_marker_hits(entries)

    assert result == 0


def test_raw_marker_hits_returns_zero_when_no_marker_words_present():
    entries = [
        (1, {"type": "assistant", "message": {"content": [{"type": "text", "text": "nothing special here"}]}}),
    ]

    result = funnel._raw_marker_hits(entries)

    assert result == 0


def test_scan_returns_a_slice_for_each_surviving_marker_with_correct_transcript_and_line_no(tmp_path):
    path = tmp_path / "transcript.jsonl"
    lines = [
        json.dumps({"type": "user", "message": {"content": "no marker here"}}),
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured the latency"}]}}),
        "",
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "the fix was verified"}]}}),
    ]
    path.write_text("\n".join(lines) + "\n")

    matched_count, kept_slices = funnel.scan([path])

    assert matched_count == 2
    assert kept_slices == [
        funnel.Slice(text="we measured the latency", transcript=path, line_no=2, marker="measured"),
        funnel.Slice(text="the fix was verified", transcript=path, line_no=4, marker="verified"),
    ]


def test_scan_preserves_original_case_of_the_matched_marker_substring(tmp_path):
    path = tmp_path / "transcript.jsonl"
    entry = {"type": "assistant", "message": {"content": [{"type": "text", "text": "Verified by the team"}]}}
    path.write_text(json.dumps(entry) + "\n")

    _, kept_slices = funnel.scan([path])

    assert kept_slices[0].marker == "Verified"


def test_scan_produces_a_single_slice_for_one_surviving_text_block_with_multiple_markers(tmp_path):
    path = tmp_path / "transcript.jsonl"
    entry = {"type": "assistant", "message": {"content": [{"type": "text", "text": "We confirmed and then measured it"}]}}
    path.write_text(json.dumps(entry) + "\n")

    matched_count, kept_slices = funnel.scan([path])

    assert matched_count == 1
    assert kept_slices == [
        funnel.Slice(text="We confirmed and then measured it", transcript=path, line_no=1, marker="confirmed"),
    ]


def test_scan_counts_markers_in_two_separate_text_blocks_of_one_entry_as_two_matched_and_two_kept_slices(tmp_path):
    path = tmp_path / "transcript.jsonl"
    entry = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "text", "text": "we measured this"},
                {"type": "text", "text": "and confirmed that"},
            ]
        },
    }
    path.write_text(json.dumps(entry) + "\n")

    matched_count, kept_slices = funnel.scan([path])

    assert matched_count == 2
    assert kept_slices == [
        funnel.Slice(text="we measured this", transcript=path, line_no=1, marker="measured"),
        funnel.Slice(text="and confirmed that", transcript=path, line_no=1, marker="confirmed"),
    ]


@pytest.mark.parametrize(
    "exclusion_fields",
    [
        {"isMeta": True},
        {"isCompactSummary": True},
    ],
    ids=["isMeta_entry", "compaction_summary_entry"],
)
def test_scan_counts_marker_hit_in_excluded_entry_but_produces_no_slice(tmp_path, exclusion_fields):
    path = tmp_path / "transcript.jsonl"
    entry = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "internally we confirmed this"}]},
        **exclusion_fields,
    }
    path.write_text(json.dumps(entry) + "\n")

    matched_count, kept_slices = funnel.scan([path])

    assert matched_count == 1
    assert kept_slices == []


def test_scan_matched_count_can_exceed_kept_slices_length_when_a_marker_is_excluded(tmp_path):
    path = tmp_path / "transcript.jsonl"
    lines = [
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}}),
        json.dumps(
            {
                "type": "assistant",
                "isMeta": True,
                "message": {"content": [{"type": "text", "text": "confirmed internally"}]},
            }
        ),
    ]
    path.write_text("\n".join(lines) + "\n")

    matched_count, kept_slices = funnel.scan([path])

    assert matched_count == 2
    assert len(kept_slices) == 1
    assert matched_count > len(kept_slices)


def test_scan_aggregates_matched_count_and_slices_across_multiple_transcripts(tmp_path):
    path1 = tmp_path / "t1.jsonl"
    path2 = tmp_path / "t2.jsonl"
    path1.write_text(
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}}) + "\n"
    )
    path2.write_text(
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we confirmed that"}]}}) + "\n"
    )

    matched_count, kept_slices = funnel.scan([path1, path2])

    assert matched_count == 2
    assert kept_slices == [
        funnel.Slice(text="we measured this", transcript=path1, line_no=1, marker="measured"),
        funnel.Slice(text="we confirmed that", transcript=path2, line_no=1, marker="confirmed"),
    ]


def test_scan_returns_zero_count_and_no_slices_for_transcript_with_no_markers(tmp_path):
    path = tmp_path / "transcript.jsonl"
    entry = {"type": "assistant", "message": {"content": [{"type": "text", "text": "nothing notable happened"}]}}
    path.write_text(json.dumps(entry) + "\n")

    matched_count, kept_slices = funnel.scan([path])

    assert matched_count == 0
    assert kept_slices == []


class _TrackedEntry(dict):
    """A dict that logs every `.get()` call - the only way funnel.py reads
    entry fields - onto a shared events list. A "get" event proves scan()
    is actively working on this entry, not just holding a reference pulled
    ahead of time."""

    def __init__(self, data, entry_id, events):
        super().__init__(data)
        self._entry_id = entry_id
        self._events = events

    def get(self, *args, **kwargs):
        self._events.append(("get", self._entry_id))
        return super().get(*args, **kwargs)


def _make_tracking_iter_entries(events):
    """Wrap funnel._iter_entries so scan()'s pull order becomes observable
    through `events`: each call appends a ("called", path) event, and each
    yielded entry appends a ("yielded", entry_id) event and is wrapped in
    _TrackedEntry so later field reads append their own "get" events."""
    real_iter_entries = funnel._iter_entries

    def tracking_iter_entries(p):
        events.append(("called", str(p)))

        def generator():
            for line_no, entry in real_iter_entries(p):
                entry_id = (str(p), line_no)
                events.append(("yielded", entry_id))
                yield line_no, _TrackedEntry(entry, entry_id, events)

        return generator()

    return tracking_iter_entries


def test_scan_finishes_each_entry_before_pulling_the_next_and_reads_each_transcript_once(
    tmp_path, monkeypatch
):
    """The previous version of this test detected materialization only
    through `__length_hint__`, which `list(iterable)` triggers but a list
    comprehension or `tuple(...)` does not - either would still buffer a
    whole transcript before scan() touches the first entry, and slip past
    that check. This version binds to the actual intent: scan() must be
    done acting on entry N (reading its fields to decide match/keep -
    funnel.py touches an entry exclusively via `.get()`) before it pulls
    entry N+1 from the generator."""
    path1 = tmp_path / "t1.jsonl"
    path1.write_text(
        "\n".join(
            [
                json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}}),
                json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we confirmed that"}]}}),
            ]
        )
        + "\n"
    )
    path2 = tmp_path / "t2.jsonl"
    path2.write_text(
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we verified this"}]}}) + "\n"
    )

    events: list[tuple] = []
    monkeypatch.setattr(funnel, "_iter_entries", _make_tracking_iter_entries(events))

    funnel.scan([path1, path2])

    call_count = sum(1 for e in events if e[0] == "called")
    assert call_count == 2

    first_entry_id = (str(path1), 1)
    second_entry_id = (str(path1), 2)
    yielded_second_index = events.index(("yielded", second_entry_id))
    get_events_for_first = [i for i, e in enumerate(events) if e == ("get", first_entry_id)]
    assert get_events_for_first, "scan() never read the first entry's fields"
    assert max(get_events_for_first) < yielded_second_index


def test_slice_on_markers_returns_the_same_slices_as_scan(tmp_path):
    path = tmp_path / "transcript.jsonl"
    lines = [
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}}),
        json.dumps(
            {
                "type": "assistant",
                "isMeta": True,
                "message": {"content": [{"type": "text", "text": "confirmed internally"}]},
            }
        ),
    ]
    path.write_text("\n".join(lines) + "\n")

    _, scan_slices = funnel.scan([path])
    wrapper_slices = funnel.slice_on_markers([path])

    assert wrapper_slices == scan_slices
    assert len(wrapper_slices) == 1

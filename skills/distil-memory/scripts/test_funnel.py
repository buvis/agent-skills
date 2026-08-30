"""Tests for funnel.py, covering assistant_only's exclusion contract and its private helpers."""

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


def test_raw_marker_hits_counts_multiple_markers_within_a_single_text_block_separately():
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

    assert result == 3


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

    assert matched_count == 2
    assert kept_slices == [
        funnel.Slice(text="We confirmed and then measured it", transcript=path, line_no=1, marker="confirmed"),
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

"""Tests for funnel.py, covering assistant_only's exclusion contract and its private helpers."""

import json

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

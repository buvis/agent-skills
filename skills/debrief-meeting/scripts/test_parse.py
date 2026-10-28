"""Rules parse.py must hold: run with `python3 -m pytest scripts/test_parse.py -q`."""

from __future__ import annotations

import zipfile

import parse

VTT = """WEBVTT

00:00:01.000 --> 00:00:04.000
<v Rivera, Alex>Right, let us start with the migration.</v>

00:00:04.500 --> 00:00:09.000
<v Sam Okafor>I think we should pick Postgres.</v>

00:00:08.000 --> 00:00:12.000
<v Rivera, Alex>Agreed, Postgres it is.</v>
"""


def test_reads_voice_tag_speaker_and_timecodes() -> None:
    parsed = parse.parse_cues(VTT, "vtt")
    assert len(parsed) == 3
    assert parsed[0]["speaker"] == "Rivera, Alex"
    assert parsed[0]["t"] == 1.0
    assert parsed[0]["end"] == 4.0
    assert parsed[0]["text"] == "Right, let us start with the migration."


def test_reads_colon_speaker_when_no_voice_tag() -> None:
    parsed = parse.parse_cues(
        "WEBVTT\n\n00:01:00.000 --> 00:01:02.000\nSam Okafor: Sounds good.\n",
        "vtt",
    )
    assert parsed[0]["speaker"] == "Sam Okafor"
    assert parsed[0]["text"] == "Sounds good."


def test_keeps_sentence_with_colon_as_speech_not_speaker() -> None:
    parsed = parse.parse_cues(
        "WEBVTT\n\n00:01:00.000 --> 00:01:02.000\nSo my point is this: we ship.\n",
        "vtt",
    )
    assert parsed[0]["speaker"] is None
    assert parsed[0]["text"] == "So my point is this: we ship."


def test_parses_hour_and_millisecond_stamps() -> None:
    assert parse.to_seconds("01:02:03.500") == 3723.5
    assert parse.to_seconds("2:05") == 125.0
    assert parse.to_seconds("00:00:04,250") == 4.25


def test_merges_comma_swapped_and_abbreviated_names() -> None:
    mapping, merges = parse.canonicalize(
        ["Rivera, Alex", "Alex Rivera", "Alex Rivera", "A. Rivera", "Sam Okafor"],
    )
    assert mapping["Rivera, Alex"] == mapping["Alex Rivera"] == mapping["A. Rivera"]
    assert mapping["Sam Okafor"] == "Sam Okafor"
    assert len(merges) == 1  # only the initial form needs a fuzzy merge


def test_keeps_distinct_people_apart() -> None:
    mapping, _ = parse.canonicalize(["Sam Okafor", "Adam Okafor"])
    assert mapping["Sam Okafor"] != mapping["Adam Okafor"]


def test_strips_role_suffix_from_speaker_name() -> None:
    mapping, _ = parse.canonicalize(["Sam Okafor (Guest)", "Sam Okafor"])
    assert len(set(mapping.values())) == 1


def test_collapses_growing_live_caption_lines() -> None:
    raw = [
        {"t": 0.0, "end": 1.0, "speaker": "A", "text": "we should"},
        {"t": 0.0, "end": 2.0, "speaker": "A", "text": "we should ship it"},
        {"t": 0.0, "end": 3.0, "speaker": "A", "text": "we should ship it today"},
        {"t": 3.0, "end": 4.0, "speaker": "B", "text": "agreed"},
    ]
    out, dropped = parse.dedup_growth(raw)
    assert dropped == 2
    assert [c["text"] for c in out] == ["we should ship it today", "agreed"]
    assert out[0]["end"] == 3.0


def test_keeps_repeated_but_different_lines() -> None:
    raw = [
        {"t": 0.0, "end": 1.0, "speaker": "A", "text": "yes"},
        {"t": 1.0, "end": 2.0, "speaker": "A", "text": "no"},
    ]
    out, dropped = parse.dedup_growth(raw)
    assert dropped == 0
    assert len(out) == 2


def test_speaking_share_sums_to_one_hundred() -> None:
    data = parse.normalize_text(VTT, "vtt")
    assert sum(s["share_words"] for s in data["speakers"]) == 100.0
    assert data["meta"]["has_timecodes"] is True


def test_counts_overlapping_start_as_interruption() -> None:
    data = parse.normalize_text(VTT, "vtt")
    alex = next(s for s in data["speakers"] if s["name"].startswith("Alex"))
    assert alex["interruptions"] == 1  # starts at 8.0 while Sam runs to 9.0


def test_reads_teams_copied_header_layout() -> None:
    text = "Sam Okafor   0:12\nWe need a decision today.\nAlex Rivera   1:40\nLet us vote.\n"
    parsed = parse.parse_cues(text, "text")
    assert [c["speaker"] for c in parsed] == ["Sam Okafor", "Alex Rivera"]
    assert parsed[0]["t"] == 12.0
    assert parsed[1]["t"] == 100.0


def test_reads_bracketed_timestamp_layout() -> None:
    parsed = parse.parse_cues("[00:03:10] Sam Okafor: Ship it.\n", "text")
    assert parsed[0]["t"] == 190.0
    assert parsed[0]["speaker"] == "Sam Okafor"


def test_warns_when_transcript_has_no_timecodes() -> None:
    data = parse.normalize_text("Sam Okafor: hello there\nAlex Rivera: hi\n", "text")
    assert data["meta"]["has_timecodes"] is False
    assert any("no timecodes" in w for w in data["warnings"])


def test_returns_none_for_empty_input() -> None:
    assert parse.normalize_text("", "text") is None


def test_reads_teams_header_with_role_suffix_as_its_own_turn() -> None:
    text = (
        "Okafor, Sam   0:02\nAgenda today.\n"
        "Alex Rivera   0:12\nWorks for me, I have a hard stop.\n"
        "Sam Okafor (Guest)   1:05\nThen Postgres.\n"
    )
    parsed = parse.parse_cues(text, "text")
    assert len(parsed) == 3
    assert parsed[1]["speaker"] == "Alex Rivera"
    assert parsed[1]["text"] == "Works for me, I have a hard stop."
    assert parsed[2]["speaker"] == "Sam Okafor (Guest)"
    assert parsed[2]["text"] == "Then Postgres."


def test_reads_bracketed_timestamp_header_with_role_suffix() -> None:
    parsed = parse.parse_cues("[00:00:12] Sam Okafor (Guest): Then Postgres.\n", "text")
    assert len(parsed) == 1
    assert parsed[0]["speaker"] == "Sam Okafor (Guest)"
    assert parsed[0]["text"] == "Then Postgres."


def test_reads_role_suffixed_header_from_docx(tmp_path) -> None:
    xml = (
        "<w:p><w:r><w:t>Dana Whitfield</w:t></w:r><w:tab/>"
        "<w:r><w:t>0:05</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>First point.</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Dana Whitfield (Contractor)</w:t></w:r><w:tab/>"
        "<w:r><w:t>0:20</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Second point.</w:t></w:r></w:p>"
    )
    docx_path = tmp_path / "t.docx"
    with zipfile.ZipFile(docx_path, "w") as archive:
        archive.writestr("word/document.xml", xml)
    text, fmt = parse.read_source(docx_path)
    parsed = parse.parse_cues(text, fmt)
    assert len(parsed) == 2
    assert parsed[0]["speaker"] == "Dana Whitfield"
    assert parsed[1]["speaker"] == "Dana Whitfield (Contractor)"
    assert parsed[1]["text"] == "Second point."


def test_normalizes_guest_header_without_false_single_speaker_warning() -> None:
    text = (
        "Alex Rivera   0:12\nWorks for me, I have a hard stop.\n"
        "Sam Okafor (Guest)   1:05\nThen Postgres.\n"
    )
    data = parse.normalize_text(text, "text")
    names = {s["name"] for s in data["speakers"]}
    assert names == {"Alex Rivera", "Sam Okafor"}
    assert not any("only one speaker" in w for w in data["warnings"])
    turn_texts = {t["text"] for t in data["turns"]}
    assert "Works for me, I have a hard stop." in turn_texts
    assert "Then Postgres." in turn_texts
    for turn in data["turns"]:
        assert "(Guest)" not in turn["text"]


def test_keeps_parenthetical_remark_in_speech_as_text_not_header() -> None:
    parsed = parse.parse_cues(
        "Sam Okafor: I think (honestly) Postgres is the right call.\n",
        "text",
    )
    assert len(parsed) == 1
    assert parsed[0]["speaker"] == "Sam Okafor"
    assert parsed[0]["text"] == "I think (honestly) Postgres is the right call."


def test_keeps_lowercase_prose_with_parenthetical_as_speech_not_header() -> None:
    parsed = parse.parse_cues("So my point (honestly): we ship.\n", "text")
    assert parsed[0]["speaker"] is None
    assert parsed[0]["text"] == "So my point (honestly): we ship."

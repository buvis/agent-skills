"""Tests for funnel.py, covering assistant_only's exclusion contract and its
private helpers, plus judge()'s subprocess seam and triage()'s cheap-tier pass."""

import dataclasses
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

import corpus
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


def test_judge_model_for_tier_maps_cheap_to_haiku_and_strong_to_sonnet():
    assert funnel._MODEL_FOR_TIER == {"cheap": "haiku", "strong": "sonnet"}


@pytest.mark.parametrize(
    ("tier", "expected_model"),
    [("cheap", "haiku"), ("strong", "sonnet")],
)
def test_judge_invokes_claude_cli_with_model_resolved_from_tier(monkeypatch, tier, expected_model):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    funnel.judge("prompt text", tier)

    assert calls == [
        (
            ["claude", "--print", "--model", expected_model, "prompt text"],
            {"stdin": subprocess.DEVNULL, "capture_output": True, "text": True, "timeout": 120},
        )
    ]


def test_judge_returns_raw_stdout_from_successful_subprocess_run(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="durable\n", stderr="")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    result = funnel.judge("prompt text", "cheap")

    assert result == "durable\n"


def test_judge_raises_runtime_error_with_stderr_message_on_nonzero_exit(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="claude cli exploded")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc_info:
        funnel.judge("prompt text", "cheap")

    assert str(exc_info.value) == "claude cli exploded"


def test_triage_transient_and_durable_constants_have_expected_string_values():
    assert funnel._TRANSIENT == "transient"
    assert funnel._DURABLE == "durable"


def test_triage_prompt_template_formats_with_transient_durable_and_text():
    result = funnel._TRIAGE_PROMPT.format(
        transient=funnel._TRANSIENT, durable=funnel._DURABLE, text="some snippet"
    )

    assert result == (
        "Classify this snippet as exactly one word, 'transient' or 'durable'. "
        "'transient' means it verifies something already known or already "
        "working (a test pass, a build succeeding, a repeated confirmation). "
        "'durable' means it establishes a new fact worth remembering. "
        "Answer with exactly one of those two words, nothing else.\n\nsome snippet"
    )


def test_triage_calls_judge_with_cheap_tier_and_formatted_prompt_for_each_slice():
    calls = []

    def stub_judge(prompt, tier):
        calls.append((prompt, tier))
        return "durable"

    slice_a = funnel.Slice(text="we measured the latency", transcript=Path("t.jsonl"), line_no=1, marker="measured")
    slice_b = funnel.Slice(
        text="the config lives at /etc/foo", transcript=Path("t.jsonl"), line_no=2, marker="confirmed"
    )

    funnel.triage([slice_a, slice_b], judge=stub_judge)

    assert calls == [
        (
            funnel._TRIAGE_PROMPT.format(transient=funnel._TRANSIENT, durable=funnel._DURABLE, text=slice_a.text),
            "cheap",
        ),
        (
            funnel._TRIAGE_PROMPT.format(transient=funnel._TRANSIENT, durable=funnel._DURABLE, text=slice_b.text),
            "cheap",
        ),
    ]


def test_triage_keeps_durable_slice_and_discards_transient_slice_with_correct_discard_count():
    transient_slice = funnel.Slice(
        text="the test suite passed again", transcript=Path("t.jsonl"), line_no=1, marker="confirmed"
    )
    durable_slice = funnel.Slice(
        text="the config lives at /etc/foo", transcript=Path("t.jsonl"), line_no=2, marker="verified"
    )

    def stub_judge(prompt, tier):
        return "transient" if prompt.endswith(transient_slice.text) else "durable"

    survivors, discard_count = funnel.triage([transient_slice, durable_slice], judge=stub_judge)

    assert survivors == [durable_slice]
    assert discard_count == 1


@pytest.mark.parametrize(
    "response",
    ["Durable.", "", "maybe", "not sure at all"],
)
def test_triage_fail_open_survives_any_response_that_is_not_exactly_transient(response):
    slice_ = funnel.Slice(text="a snippet", transcript=Path("t.jsonl"), line_no=1, marker="measured")

    def stub_judge(prompt, tier):
        return response

    survivors, discard_count = funnel.triage([slice_], judge=stub_judge)

    assert survivors == [slice_]
    assert discard_count == 0


@pytest.mark.parametrize(
    "response",
    ["transient", "Transient", "TRANSIENT", "  transient  ", "Transient\n"],
)
def test_triage_discards_response_matching_transient_case_and_whitespace_insensitively(response):
    slice_ = funnel.Slice(text="a snippet", transcript=Path("t.jsonl"), line_no=1, marker="measured")

    def stub_judge(prompt, tier):
        return response

    survivors, discard_count = funnel.triage([slice_], judge=stub_judge)

    assert survivors == []
    assert discard_count == 1


def test_triage_returns_empty_survivors_and_zero_discards_for_empty_slice_list():
    survivors, discard_count = funnel.triage([])

    assert survivors == []
    assert discard_count == 0


def test_triage_never_invokes_default_judges_subprocess_when_a_stub_judge_is_provided(monkeypatch):
    def fail_if_called(cmd, **kwargs):
        raise AssertionError("default judge's subprocess.run must not be called when a stub judge is passed")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)

    slice_ = funnel.Slice(text="a snippet", transcript=Path("t.jsonl"), line_no=1, marker="measured")

    def stub_judge(prompt, tier):
        return "durable"

    survivors, discard_count = funnel.triage([slice_], judge=stub_judge)

    assert survivors == [slice_]
    assert discard_count == 0


class FakeSessionData:
    """Stand-in for the real claude-checkup parser's SessionData: an object
    with `.earliest`/`.latest` datetime-or-None attributes."""

    def __init__(self, latest=None, earliest=None):
        self.latest = latest
        self.earliest = earliest


def make_transcript_parser_module(results_by_filename, *, version="0.3.0"):
    """A parser module stub whose parse_session(path) looks up its result by
    the transcript's filename, and which satisfies assert_contract()."""
    module = ModuleType("stub_transcript_parser")
    module.parse_session = lambda path: results_by_filename[Path(path).name]
    module.SessionData = FakeSessionData
    return module, version


def write_transcript(project_dir: Path, filename: str, content: str = "") -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = project_dir / filename
    transcript_path.write_text(content)
    return transcript_path


def test_render_yield_performs_no_subprocess_calls_or_file_io(monkeypatch):
    def fail_subprocess(*args, **kwargs):
        raise AssertionError("render_yield must not invoke subprocess")

    def fail_open(*args, **kwargs):
        raise AssertionError("render_yield must not perform file I/O")

    monkeypatch.setattr(funnel.subprocess, "run", fail_subprocess)
    monkeypatch.setattr("builtins.open", fail_open)
    counts = {
        "transcripts_read": 3,
        "slices_matched": 2,
        "slices_kept": 1,
        "survivors": 1,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert isinstance(result, str)


def test_render_yield_prints_every_stage_ending_in_zero_when_a_run_finds_nothing():
    counts = {
        "transcripts_read": 0,
        "slices_matched": 0,
        "slices_kept": 0,
        "survivors": 0,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    lines = [line for line in result.splitlines() if line.strip()]
    count_lines = lines[:4]
    assert len(count_lines) == 4
    for line in count_lines:
        assert line.rstrip().endswith("0")


def test_render_yield_prints_key_value_line_for_each_count_when_values_are_nonzero():
    counts = {
        "transcripts_read": 12,
        "slices_matched": 8,
        "slices_kept": 5,
        "survivors": 3,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert "transcripts_read: 12" in result
    assert "slices_matched: 8" in result
    assert "slices_kept: 5" in result
    assert "survivors: 3" in result


def test_render_yield_states_the_resolved_claude_checkup_version():
    counts = {
        "transcripts_read": 12,
        "slices_matched": 8,
        "slices_kept": 5,
        "survivors": 3,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert "claude_checkup_version: 0.2.2" in result


def test_render_yield_renders_none_survivors_as_n_a_for_a_dry_run():
    counts = {
        "transcripts_read": 5,
        "slices_matched": 3,
        "slices_kept": 2,
        "survivors": None,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert "survivors: n/a" in result


def test_render_yield_ends_with_how_to_proceed_line_naming_the_audit_results_directory():
    counts = {
        "transcripts_read": 5,
        "slices_matched": 3,
        "slices_kept": 2,
        "survivors": 1,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    last_line = result.rstrip("\n").splitlines()[-1]
    assert last_line.startswith("How to proceed:")
    assert "dev/local/audit-results/" in last_line


def test_main_passes_days_all_project_flags_through_to_select_transcripts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_select_transcripts(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(corpus, "select_transcripts", fake_select_transcripts)
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "0.2.2"))

    exit_code = funnel.main(["--days", "7", "--all", "--project", "myproj"])

    assert exit_code == 0
    assert calls == [{"days": 7, "all": True, "project": "myproj"}]


def test_main_with_argv_none_falls_back_to_sys_argv_and_default_flags(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["funnel.py", "--dry-run"])
    calls = []

    def fake_select_transcripts(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(corpus, "select_transcripts", fake_select_transcripts)
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "0.2.2"))

    exit_code = funnel.main()

    assert exit_code == 0
    assert calls == [{"days": 30, "all": False, "project": None}]


def test_main_returns_nonzero_and_prints_message_when_select_transcripts_raises_stale_parser_error(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path / "projects")

    def raise_stale(*args, **kwargs):
        raise corpus.StaleParserError("no claude-checkup versions found")

    monkeypatch.setattr(corpus, "resolve_parser", raise_stale)

    exit_code = funnel.main([])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert "no claude-checkup versions found" in (captured.out + captured.err)


def test_main_normal_run_prints_and_writes_report_matching_render_yield_and_reflects_triage_discards(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    project_dir = projects_root / "aaaa-myproj"

    def write_jsonl(filename, texts):
        write_transcript(project_dir, filename, "".join(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}) + "\n" for t in texts))
    now = datetime.now(timezone.utc)
    write_jsonl("t1.jsonl", ["we measured this", "and confirmed that"])
    write_jsonl("t2.jsonl", ["nothing notable here"])

    module, version = make_transcript_parser_module(
        {
            "t1.jsonl": FakeSessionData(latest=now - timedelta(days=1)),
            "t2.jsonl": FakeSessionData(latest=now - timedelta(days=1)),
        }
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    def fake_run(cmd, **kwargs):
        prompt = cmd[-1]
        if prompt.endswith("and confirmed that"):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="transient", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="durable", stderr="")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    exit_code = funnel.main([])

    assert exit_code == 0
    expected_counts = {
        "transcripts_read": 2,
        "slices_matched": 2,
        "slices_kept": 2,
        "survivors": 1,
        "claude_checkup_version": version,
    }
    expected_report = funnel.render_yield(expected_counts)

    captured = capsys.readouterr()
    assert expected_report in captured.out

    report_files = sorted((tmp_path / "dev" / "local" / "audit-results").glob("distil-memory-*.md"))
    assert len(report_files) == 1
    assert report_files[0].read_text() == expected_report


def test_main_dry_run_makes_no_model_call_and_prints_and_writes_report_matching_render_yield(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    project_dir = projects_root / "aaaa-myproj"

    now = datetime.now(timezone.utc)
    write_transcript(
        project_dir,
        "t1.jsonl",
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}})
        + "\n",
    )

    module, version = make_transcript_parser_module(
        {"t1.jsonl": FakeSessionData(latest=now - timedelta(days=1))}
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry run must not invoke subprocess (no model calls of any tier)")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)

    exit_code = funnel.main(["--dry-run"])

    assert exit_code == 0
    expected_counts = {
        "transcripts_read": 1,
        "slices_matched": 1,
        "slices_kept": 1,
        "survivors": None,
        "claude_checkup_version": version,
    }
    expected_report = funnel.render_yield(expected_counts)

    captured = capsys.readouterr()
    assert expected_report in captured.out
    assert "survivors: n/a" in captured.out

    report_files = sorted((tmp_path / "dev" / "local" / "audit-results").glob("distil-memory-*.md"))
    assert len(report_files) == 1
    assert report_files[0].read_text() == expected_report


def test_main_prints_known_counts_and_survivors_n_a_and_writes_stderr_and_returns_nonzero_when_judge_raises_runtime_error(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    project_dir = projects_root / "aaaa-myproj"
    now = datetime.now(timezone.utc)
    write_transcript(
        project_dir,
        "t1.jsonl",
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}})
        + "\n",
    )
    module, version = make_transcript_parser_module(
        {"t1.jsonl": FakeSessionData(latest=now - timedelta(days=1))}
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="claude cli exploded")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    exit_code = funnel.main([])

    assert exit_code != 0
    expected_counts = {
        "transcripts_read": 1,
        "slices_matched": 1,
        "slices_kept": 1,
        "survivors": None,
        "claude_checkup_version": version,
    }
    expected_report = funnel.render_yield(expected_counts)

    captured = capsys.readouterr()
    assert expected_report in captured.out
    assert "survivors: n/a" in captured.out
    assert "claude cli exploded" in captured.err


def test_main_prints_known_counts_and_survivors_n_a_and_writes_stderr_and_returns_nonzero_when_claude_cli_binary_is_absent(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    project_dir = projects_root / "aaaa-myproj"
    now = datetime.now(timezone.utc)
    write_transcript(
        project_dir,
        "t1.jsonl",
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}})
        + "\n",
    )
    module, version = make_transcript_parser_module(
        {"t1.jsonl": FakeSessionData(latest=now - timedelta(days=1))}
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("[Errno 2] No such file or directory: 'claude'")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    exit_code = funnel.main([])

    assert exit_code != 0
    expected_counts = {
        "transcripts_read": 1,
        "slices_matched": 1,
        "slices_kept": 1,
        "survivors": None,
        "claude_checkup_version": version,
    }
    expected_report = funnel.render_yield(expected_counts)

    captured = capsys.readouterr()
    assert expected_report in captured.out
    assert "survivors: n/a" in captured.out
    assert "No such file or directory" in captured.err


def test_main_prints_known_counts_and_survivors_n_a_and_writes_stderr_and_returns_nonzero_when_claude_cli_times_out(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    project_dir = projects_root / "aaaa-myproj"
    now = datetime.now(timezone.utc)
    write_transcript(
        project_dir,
        "t1.jsonl",
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}})
        + "\n",
    )
    module, version = make_transcript_parser_module(
        {"t1.jsonl": FakeSessionData(latest=now - timedelta(days=1))}
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=120)

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    exit_code = funnel.main([])

    assert exit_code != 0
    expected_counts = {
        "transcripts_read": 1,
        "slices_matched": 1,
        "slices_kept": 1,
        "survivors": None,
        "claude_checkup_version": version,
    }
    expected_report = funnel.render_yield(expected_counts)

    captured = capsys.readouterr()
    assert expected_report in captured.out
    assert "survivors: n/a" in captured.out
    assert "timed out after 120 seconds" in captured.err


def test_main_reports_persistence_failure_to_stderr_and_returns_nonzero_when_writing_report_raises_oserror(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    project_dir = projects_root / "aaaa-myproj"
    now = datetime.now(timezone.utc)
    write_transcript(
        project_dir,
        "t1.jsonl",
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}})
        + "\n",
    )
    module, version = make_transcript_parser_module(
        {"t1.jsonl": FakeSessionData(latest=now - timedelta(days=1))}
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="durable", stderr="")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    def raise_oserror(*args, **kwargs):
        raise OSError("no space left on device")

    monkeypatch.setattr(Path, "mkdir", raise_oserror)
    monkeypatch.setattr(Path, "write_text", raise_oserror)

    exit_code = funnel.main([])

    assert exit_code != 0
    expected_counts = {
        "transcripts_read": 1,
        "slices_matched": 1,
        "slices_kept": 1,
        "survivors": 1,
        "claude_checkup_version": version,
    }
    expected_report = funnel.render_yield(expected_counts)

    captured = capsys.readouterr()
    assert expected_report in captured.out
    assert "dev/local/audit-results" in captured.err


def test_main_writes_report_under_the_repository_root_and_prints_its_absolute_path_when_run_from_a_deeply_nested_cwd(
    tmp_path, monkeypatch, capsys
):
    repo_root = tmp_path / "myrepo"
    (repo_root / ".git").mkdir(parents=True)
    nested_cwd = repo_root / "a" / "b" / "c"
    nested_cwd.mkdir(parents=True)
    monkeypatch.chdir(nested_cwd)

    monkeypatch.setattr(corpus, "select_transcripts", lambda **kwargs: [])
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "0.2.2"))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("must not invoke the claude CLI")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)

    exit_code = funnel.main([])

    assert exit_code == 0

    nested_audit_dir = nested_cwd / "dev" / "local" / "audit-results"
    assert not nested_audit_dir.exists()

    report_dir = repo_root / "dev" / "local" / "audit-results"
    report_files = sorted(report_dir.glob("distil-memory-*.md"))
    assert len(report_files) == 1

    # The printed path must be the *absolute* path to the file that was
    # actually written. A relative print (e.g. bare "dev/local/audit-results/...")
    # would not equal this string, which already carries the tmp_path prefix.
    captured = capsys.readouterr()
    assert str(report_files[0]) in captured.out


def test_main_falls_back_to_cwd_dev_local_audit_results_when_no_ancestor_directory_contains_a_git_entry(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(corpus, "select_transcripts", lambda **kwargs: [])
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "0.2.2"))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("must not invoke the claude CLI")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)

    exit_code = funnel.main([])

    assert exit_code == 0
    report_files = sorted((tmp_path / "dev" / "local" / "audit-results").glob("distil-memory-*.md"))
    assert len(report_files) == 1


def test_main_help_declares_exactly_the_days_all_project_and_dry_run_flags(capsys):
    with pytest.raises(SystemExit):
        funnel.main(["--help"])

    captured = capsys.readouterr()
    help_text = captured.out + captured.err
    long_flags = set(re.findall(r"--[a-z][a-z-]*", help_text))

    assert long_flags == {"--days", "--all", "--project", "--dry-run", "--help"}


def test_main_calls_resolve_parser_exactly_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    projects_root.mkdir()
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    module, version = make_transcript_parser_module({})
    calls = []

    def counting_resolve(*args, **kwargs):
        calls.append((args, kwargs))
        return module, version

    monkeypatch.setattr(corpus, "resolve_parser", counting_resolve)

    exit_code = funnel.main([])

    assert exit_code == 0
    assert len(calls) == 1


def test_main_returns_zero_when_resolve_parser_succeeds_on_first_call_and_would_raise_on_a_second(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    projects_root.mkdir()
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    module, version = make_transcript_parser_module({})
    calls = []

    def succeed_once_then_raise(*args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) == 1:
            return module, version
        raise corpus.StaleParserError("a second resolve must never happen")

    monkeypatch.setattr(corpus, "resolve_parser", succeed_once_then_raise)

    exit_code = funnel.main([])

    assert exit_code == 0


def test_main_returns_one_and_prints_message_to_stderr_when_resolve_parser_raises_on_the_first_call(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path / "claude_projects")

    def raise_immediately(*args, **kwargs):
        raise corpus.StaleParserError("claude-checkup cache is empty")

    monkeypatch.setattr(corpus, "resolve_parser", raise_immediately)

    exit_code = funnel.main([])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "claude-checkup cache is empty" in captured.err


def test_main_yield_report_states_the_version_from_the_single_resolution_that_selected_transcripts(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    project_dir = projects_root / "aaaa-myproj"
    now = datetime.now(timezone.utc)
    write_transcript(
        project_dir,
        "t1.jsonl",
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}})
        + "\n",
    )
    versions = iter(["0.9.9", "0.0.1"])

    def resolve_with_a_distinct_version_per_call(*args, **kwargs):
        version = next(versions)
        module, _ = make_transcript_parser_module(
            {"t1.jsonl": FakeSessionData(latest=now - timedelta(days=1))}, version=version
        )
        return module, version

    monkeypatch.setattr(corpus, "resolve_parser", resolve_with_a_distinct_version_per_call)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="durable", stderr="")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    exit_code = funnel.main([])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "claude_checkup_version: 0.9.9" in captured.out
    assert "claude_checkup_version: 0.0.1" not in captured.out

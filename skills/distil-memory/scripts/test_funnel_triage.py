"""Tests for funnel.py's judgment path: judge()'s subprocess seam and
triage()'s cheap-tier pass over a list of Slices."""

import subprocess
from pathlib import Path

import funnel
import pytest


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

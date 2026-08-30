"""Tests for the reason distil.py puts on a Discard: it names the failure it
stands for, it stops at the end of the DISCARD line, and it never carries the
slice text into a file whoever triages the run will read."""

import subprocess

import distil
import funnel
import pytest
from distil_test_helpers import MISSING_DESCRIPTION as _MISSING_DESCRIPTION
from distil_test_helpers import make_slice as _slice

_SENTINEL = "SENTINEL-TRANSCRIPT-SLICE-9f3c1a-do-not-leak"


@pytest.fixture(autouse=True)
def never_reach_the_real_model(monkeypatch):
    """No test in this file may invoke the claude CLI. distil() captures its
    judge as a default argument bound at import time, so the seam that actually
    stops a real call is funnel's subprocess.run, not funnel.judge."""

    def fail_if_called(cmd, **kwargs):
        raise AssertionError("no test may reach the real claude CLI")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)


def _judge_raising_runtime_error(prompt, tier):
    raise RuntimeError(f"claude cli exploded while handling {_SENTINEL}")


def _judge_raising_timeout(prompt, tier):
    raise subprocess.TimeoutExpired(
        cmd=["claude", "--print", "--model", "sonnet", _SENTINEL], timeout=120
    )


def _judge_raising_os_error(prompt, tier):
    raise OSError(f"[Errno 5] Input/output error on {_SENTINEL}")


def _judge_returning_nothing(prompt, tier):
    return ""


def _judge_returning_garbage(prompt, tier):
    return "the model rambled instead of answering"


def _judge_returning_invalid_file(prompt, tier):
    return _MISSING_DESCRIPTION


def _judge_returning_a_bare_discard(prompt, tier):
    return distil.DISCARD_PREFIX


def _judge_returning_a_bare_discard_then_the_slice(prompt, tier):
    return (
        f"{distil.DISCARD_PREFIX}\n"
        f"For reference, the snippet said: we measured {_SENTINEL} at four milliseconds"
    )


def _judge_returning_a_padded_discard_then_the_slice(prompt, tier):
    """The same answer with whitespace between the token and the newline: the
    line still states no reason, and the snippet still sits underneath it."""
    return (
        f"{distil.DISCARD_PREFIX}  \t \n"
        f"For reference, the snippet said: we measured {_SENTINEL} at four milliseconds"
    )


@pytest.mark.parametrize(
    "stub_judge",
    [
        _judge_raising_runtime_error,
        _judge_raising_timeout,
        _judge_raising_os_error,
        _judge_returning_garbage,
        _judge_returning_invalid_file,
        _judge_returning_a_bare_discard,
        _judge_returning_a_bare_discard_then_the_slice,
        _judge_returning_a_padded_discard_then_the_slice,
    ],
    ids=[
        "runtime-error",
        "timeout",
        "os-error",
        "garbage",
        "invalid-file",
        "bare-discard",
        "bare-discard-then-the-slice",
        "padded-discard-then-the-slice",
    ],
)
def test_no_discard_reason_ever_embeds_the_slice_text(stub_judge):
    slice_ = _slice(f"we measured {_SENTINEL} at four milliseconds")

    result = distil.distil(slice_, [], judge=stub_judge)

    assert isinstance(result, distil.Discard)
    assert _SENTINEL not in result.reason


def test_a_discard_reason_stops_at_the_end_of_the_discard_line():
    """The reason is the rest of the LINE, not the rest of the answer. A model
    that states its verdict and then restates the snippet it turned down writes
    that snippet into a reason that is saved to disk and read later by whoever
    triages the run, which is exactly what the no-slice-text rule forbids."""
    slice_ = _slice(f"we measured {_SENTINEL} at four milliseconds")

    def stub_judge(prompt, tier):
        return (
            f"{distil.DISCARD_PREFIX} verifies a test run that already passed\n"
            f"For reference, the snippet said: we measured {_SENTINEL} at four milliseconds"
        )

    result = distil.distil(slice_, [], judge=stub_judge)

    assert isinstance(result, distil.Discard)
    assert result.reason == "verifies a test run that already passed"
    assert _SENTINEL not in result.reason


# A DISCARD line states no reason whenever nothing but whitespace follows the
# token on it. The answers are built from those two parts - the padding that
# ends the line, and whatever prose the model wrote underneath - so the rule
# covers the shapes this file never wrote down. Three hand-picked literals can
# be memorised; a padding one space wider than the fixtures cannot.
_BLANK_DISCARD_PADDINGS = (
    ("", "nothing-after-the-token"),
    (" ", "one-space-after-the-token"),
    ("\t", "one-tab-after-the-token"),
    ("  \t  ", "mixed-whitespace-after-the-token"),
)
_BLANK_DISCARD_TAILS = (
    ("", "end-of-answer"),
    ("\nwe clocked the reindex at nine hundred milliseconds", "prose-on-the-next-line"),
    (
        "\n\nwe clocked the reindex at nine hundred milliseconds"
        "\nplus a stray remark about zsh completions",
        "prose-further-down",
    ),
)
_BLANK_DISCARD_ANSWERS = [
    pytest.param(f"{distil.DISCARD_PREFIX}{padding}{tail}", id=f"{padding_id}-{tail_id}")
    for padding, padding_id in _BLANK_DISCARD_PADDINGS
    for tail, tail_id in _BLANK_DISCARD_TAILS
]


@pytest.mark.parametrize("answer", _BLANK_DISCARD_ANSWERS)
def test_a_discard_whose_line_states_no_reason_still_carries_one_saying_so(answer):
    """Every discard carries a reason: the run's report promises "discards with
    reasons", and an empty string is not one. A model that ends its DISCARD line
    without words states no reason, so the discard says that instead of
    persisting a blank field nobody can act on.

    Whitespace does not make it a different case, and neither does prose
    underneath. The reason is the rest of the DISCARD LINE, so a line holding
    nothing but padding states nothing however much follows below, and reaching
    onto a later line to fill the gap is how the model's own restatement of the
    snippet ends up on disk.

    So the reason these answers produce is pinned to the one the bare token
    produces - identical, whatever the padding, whatever came after. That admits
    no borrowed tail at all, not even a truncated one."""
    slice_ = _slice("we measured the cache at 4ms")

    def stub_judge(prompt, tier):
        return answer

    result = distil.distil(slice_, [], judge=stub_judge)
    bare = distil.distil(slice_, [], judge=_judge_returning_a_bare_discard)

    assert isinstance(result, distil.Discard)
    assert result.slice_ is slice_
    assert result.reason.strip() != ""
    assert any(word in result.reason.lower() for word in ("reason", "explanation", "unexplained"))
    assert result.reason == bare.reason


def test_a_discard_reason_the_model_states_reaches_the_discard_unchanged():
    """Filling in the blank case must not become overwriting every case. One
    constant reason on every discard reads as an empty one to whoever triages
    the run: the words the model chose are the only thing that says WHY this
    slice was turned down, so they survive verbatim and differ from what a
    reasonless answer leaves behind."""
    slice_ = _slice("we measured the cache at 4ms")
    stated = "the snippet names a build that has already finished"

    def stub_judge_with_a_reason(prompt, tier):
        return f"{distil.DISCARD_PREFIX} {stated}"

    with_reason = distil.distil(slice_, [], judge=stub_judge_with_a_reason)
    without_reason = distil.distil(slice_, [], judge=_judge_returning_a_bare_discard)

    assert isinstance(with_reason, distil.Discard)
    assert isinstance(without_reason, distil.Discard)
    assert with_reason.reason == stated
    assert without_reason.reason.strip() != ""
    assert without_reason.reason != with_reason.reason


def test_discard_reasons_distinguish_the_failure_modes_they_name():
    """A reason is written to disk and read later by whoever triages the run.
    One constant string - "discarded", "no proposal" - satisfies every
    not-empty assertion in this file and tells that reader nothing about which
    of these six ways the slice failed. Two constants, one per code path, tell
    them barely more, so each of the six failures needs its own reason, and the
    timeout has to say it timed out rather than just differ from its
    neighbours."""
    slice_ = _slice("we measured the cache at 4ms")
    failures = {
        "empty-response": _judge_returning_nothing,
        "garbage-response": _judge_returning_garbage,
        "invalid-file": _judge_returning_invalid_file,
        "runtime-error": _judge_raising_runtime_error,
        "timeout": _judge_raising_timeout,
        "os-error": _judge_raising_os_error,
    }

    reasons = {}
    for failure, stub_judge in failures.items():
        result = distil.distil(slice_, [], judge=stub_judge)
        assert isinstance(result, distil.Discard)
        reasons[failure] = result.reason.strip()

    assert len(set(reasons.values())) == len(failures)
    assert any(word in reasons["timeout"].lower() for word in ("timeout", "timed out"))

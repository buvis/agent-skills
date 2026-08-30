"""Tests for proposal.excerpt(): the window it cuts around the marker in a
slice too long to show whole."""

import proposal
import pytest

_MARKER = "measured"

# Every marker the window must anchor on. Anchoring is asserted against each of
# them, so a window that looks for one hardcoded word cannot answer these.
_MARKERS = ["measured", "benchmarked", "91 percent"]

# The contract says "an ellipsis" without pinning the glyph, so both spellings
# count wherever a cut end is asserted.
_ELLIPSES = ("...", "…")


def _filler(total):
    """`total` characters of prose with no repeating substring, so "this window
    reached offset N" is a real assertion rather than a filler coincidence."""
    return " ".join(f"w{index:04d}" for index in range(total // 6 + 2))[:total]


def _text_with_marker_at(offset, total, marker=_MARKER):
    base = _filler(total)
    return base[:offset] + marker + base[offset + len(marker) :]


def _without_ellipses(text):
    for mark in _ELLIPSES:
        if text.startswith(mark):
            text = text[len(mark) :]
            break
    for mark in _ELLIPSES:
        if text.endswith(mark):
            text = text[: -len(mark)]
            break
    return text


@pytest.mark.parametrize(
    ("label", "length"),
    [
        ("under the limit", proposal.EVIDENCE_EXCERPT_CHARS - 1),
        ("exactly at the limit", proposal.EVIDENCE_EXCERPT_CHARS),
    ],
)
def test_excerpt_returns_text_within_the_limit_unchanged_and_unmarked(label, length):
    text = _text_with_marker_at(length - len(_MARKER) - 1, length)

    assert proposal.excerpt(text, _MARKER) == text


@pytest.mark.parametrize("marker", _MARKERS)
def test_excerpt_keeps_a_marker_that_sits_past_the_leading_window(marker):
    # Head truncation would cut this marker away entirely: it starts well past
    # EVIDENCE_EXCERPT_CHARS, and the sentence around it is what justifies the slice.
    width = proposal.EVIDENCE_EXCERPT_CHARS
    offset = width * 2 + 300
    text = _text_with_marker_at(offset, width * 5, marker)

    window = proposal.excerpt(text, marker)

    assert marker in window
    assert text[offset - 100 : offset] in window
    assert text[offset + len(marker) : offset + len(marker) + 100] in window
    assert window.startswith(_ELLIPSES)
    assert window.endswith(_ELLIPSES)
    assert _without_ellipses(window) in text


@pytest.mark.parametrize("marker", _MARKERS)
def test_excerpt_gives_a_marker_near_the_start_a_full_width_window_anchored_there(marker):
    width = proposal.EVIDENCE_EXCERPT_CHARS
    text = _text_with_marker_at(10, width * 5, marker)

    window = proposal.excerpt(text, marker)

    assert window.startswith(text[:60])
    assert not window.startswith(_ELLIPSES)
    assert window.endswith(_ELLIPSES)
    # A window merely centred on offset 10 would stop around offset 310. A
    # clamped, full-width one runs to the far end of the budget.
    assert text[width - 60 : width - 10] in window


@pytest.mark.parametrize("marker", _MARKERS)
def test_excerpt_gives_a_marker_near_the_end_a_full_width_window_anchored_there(marker):
    width = proposal.EVIDENCE_EXCERPT_CHARS
    total = width * 5
    text = _text_with_marker_at(total - len(marker) - 5, total, marker)

    window = proposal.excerpt(text, marker)

    assert window.endswith(text[-60:])
    assert not window.endswith(_ELLIPSES)
    assert window.startswith(_ELLIPSES)
    assert text[total - width + 10 : total - width + 60] in window


def test_excerpt_falls_back_to_the_leading_window_when_the_marker_is_absent():
    width = proposal.EVIDENCE_EXCERPT_CHARS
    text = _filler(width * 5)
    assert "reproduced" not in text

    window = proposal.excerpt(text, "reproduced")

    assert window.startswith(text[:60])
    assert not window.startswith(_ELLIPSES)
    assert window.endswith(_ELLIPSES)
    assert text[width - 60 : width - 10] in window


def test_excerpt_sizes_the_window_from_the_caller_supplied_width():
    text = _text_with_marker_at(1500, proposal.EVIDENCE_EXCERPT_CHARS * 5)

    window = proposal.excerpt(text, _MARKER, 80)

    assert _MARKER in window
    assert len(window) < proposal.EVIDENCE_EXCERPT_CHARS
    assert _without_ellipses(window) in text

"""
Trim tests for the survey brief generator (run.py).

Covers _encoded_len's byte-length contract and _trim_lines_to_budget's
whole-line trimming, largest-fitting-prefix choice, empty-prefix fallback, and
trailing blank/header cleanup.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run


# ---------------------------------------------------------------------------
# _encoded_len: UTF-8 byte length of the newline-joined lines
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "lines, expected",
    [
        ([], 0),
        ([""], 0),
        (["", ""], 1),
        (["abc"], 3),
        (["ab", "cd"], 5),
        (["a", "", "b"], 4),
        # Multi-byte: bytes, not characters. "é" is 2 bytes, "€" is 3.
        (["é"], 2),
        (["é", "€"], 6),
    ],
)
def test_encoded_len_counts_utf8_bytes_of_newline_joined_lines(lines, expected):
    assert run._encoded_len(lines) == expected, (
        f"_encoded_len({lines!r}) must equal len('\\n'.join(lines).encode()) "
        f"== {expected}"
    )


def test_encoded_len_does_not_mutate_its_input():
    lines = ["## A", "", "- x"]
    snapshot = list(lines)
    run._encoded_len(lines)
    assert lines == snapshot, "_encoded_len must be pure and leave its input intact"


# ---------------------------------------------------------------------------
# _trim_lines_to_budget: largest fitting prefix of whole lines
# ---------------------------------------------------------------------------

# Prefix byte lengths: "a"=1, "a\nbb"=4, "a\nbb\nccc"=8, full=13.
_GRADED = "a\nbb\nccc\ndddd"


@pytest.mark.parametrize(
    "max_bytes, expected",
    [
        (13, "a\nbb\nccc\ndddd"),
        (12, "a\nbb\nccc"),
        (8, "a\nbb\nccc"),
        (7, "a\nbb"),
        (4, "a\nbb"),
        (3, "a"),
        (1, "a"),
    ],
)
def test_trim_keeps_largest_prefix_of_whole_lines_that_fits(max_bytes, expected):
    result = run._trim_lines_to_budget(_GRADED, max_bytes)
    assert result == expected, (
        f"budget {max_bytes}: must keep the longest whole-line prefix that fits, "
        f"expected {expected!r}, got {result!r}"
    )
    assert len(result.encode()) <= max_bytes


def test_trim_returns_content_unchanged_when_it_fits_exactly():
    content = "## A\n\n- x\n- y"
    budget = len(content.encode())
    assert run._trim_lines_to_budget(content, budget) == content, \
        "content exactly at the budget fits (<=) and must not lose a line"
    assert run._trim_lines_to_budget(content, budget - 1) == "## A\n\n- x", \
        "one byte under the budget must drop exactly the last whole line"


def test_trim_measures_budget_in_bytes_not_characters():
    # "ab\néé" is 5 characters but 7 bytes; a char-count budget would keep it.
    assert run._trim_lines_to_budget("ab\néé", 5) == "ab"
    assert run._trim_lines_to_budget("ab\néé", 7) == "ab\néé"


# ---------------------------------------------------------------------------
# _trim_lines_to_budget: empty input and the empty-prefix (k=0) fallback
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("max_bytes", [0, 5, 100])
def test_trim_empty_content_returns_empty_string(max_bytes):
    assert run._trim_lines_to_budget("", max_bytes) == ""


@pytest.mark.parametrize("max_bytes", [0, 2])
def test_trim_returns_empty_when_first_line_alone_exceeds_budget(max_bytes):
    assert run._trim_lines_to_budget("abc\nd", max_bytes) == "", \
        "no line fits, so the empty prefix is the result"


def test_trim_returns_empty_for_negative_budget():
    """The empty prefix is valid even when its 0 bytes exceed the budget."""
    assert run._trim_lines_to_budget("a\nb", -1) == ""
    assert run._trim_lines_to_budget("", -10) == ""


# ---------------------------------------------------------------------------
# _trim_lines_to_budget: trailing blank / dangling header cleanup
# ---------------------------------------------------------------------------

def test_trim_cleanup_strips_alternating_blanks_and_headers_repeatedly():
    content = "## A\n\n- x\n\n## B\n\n- y"
    # Budget drops "- y" only; the tail is then "", "## B", "" and each must go.
    budget = len("## A\n\n- x\n\n## B\n".encode())
    assert run._trim_lines_to_budget(content, budget) == "## A\n\n- x", \
        "cleanup must repeat until the last line is neither blank nor a '## ' header"


@pytest.mark.parametrize(
    "content, expected",
    [
        # Cleanup applies even when nothing needed trimming for size.
        ("- x\n", "- x"),
        ("- x\n\n\n", "- x"),
        ("## A\n\n- x\n\n## B\n", "## A\n\n- x"),
        # Only headers and blanks: nothing survives.
        ("## A\n\n## B\n", ""),
        # Interior blank lines are kept; only the tail is cleaned.
        ("## A\n\n- x\n\n- y", "## A\n\n- x\n\n- y"),
        # A deeper heading is not a "## " header and stays.
        ("- x\n### Sub", "- x\n### Sub"),
    ],
)
def test_trim_cleanup_drops_only_trailing_blanks_and_dangling_headers(content, expected):
    assert run._trim_lines_to_budget(content, 1000) == expected


@pytest.mark.parametrize(
    "content, max_bytes, expected",
    [
        # Already under budget: the whitespace-only tail is not "" and stays.
        ("- x\n   ", 1000, "- x\n   "),
        ("- x\n\t", 1000, "- x\n\t"),
        # Exposed by the size trim: " " becomes the tail and still stays.
        ("- x\n \n- y", len("- x\n ".encode()), "- x\n "),
    ],
)
def test_trim_cleanup_keeps_whitespace_only_trailing_line(content, max_bytes, expected):
    """Cleanup strips only an exactly empty line, not one that is merely blank."""
    assert run._trim_lines_to_budget(content, max_bytes) == expected, (
        "cleanup must test lines[-1] == '', not lines[-1].strip() == ''"
    )


@pytest.mark.parametrize(
    "content",
    [
        "- x\n  ## indented",
        "- x\n\t## tabbed",
        "- x\n##nospace",
    ],
)
def test_trim_cleanup_keeps_trailing_line_not_starting_with_literal_header(content):
    """Cleanup strips only lines that start with the literal '## '."""
    assert run._trim_lines_to_budget(content, 1000) == content, (
        "cleanup must test lines[-1].startswith('## ') with no whitespace "
        "tolerance; an indented or space-less '##' line is not a header"
    )



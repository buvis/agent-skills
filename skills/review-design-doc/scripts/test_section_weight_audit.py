"""
Help-flag and regression tests for section_weight_audit.py's CLI entry point.

Covers -h/--help recognized as the first argument (one-line usage on stdout,
exit 0, no scan run before the file-validity check), and that the existing
argument-count, file-validity, and normal-scan behaviors are unchanged.
"""

import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent / "section_weight_audit.py"


def _run(args):
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Help: both spellings, as the sole argument
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_flag_exits_zero_with_one_line_usage_and_no_scan(flag):
    result = _run([flag])

    assert result.returncode == 0, (
        f"{flag} must exit 0, got {result.returncode}; stderr={result.stderr!r}"
    )
    lines = result.stdout.strip("\n").splitlines()
    assert len(lines) == 1, (
        f"{flag} must print exactly one usage line, got {lines!r}"
    )
    assert "section_weight_audit.py" in lines[0], (
        f"usage line must name the script, got {lines[0]!r}"
    )
    assert "SUMMARY:" not in result.stdout, f"{flag} must not run the scan"
    assert result.stderr == "", f"{flag} must not write to stderr"


def test_help_flag_runs_before_file_validity_check():
    # "-h" is not an existing file; if the file check ran first, this would
    # exit 1 with "error: not a file: -h" instead of succeeding as help.
    result = _run(["-h"])

    assert result.returncode == 0
    assert "error: not a file" not in result.stderr


# ---------------------------------------------------------------------------
# Near-miss: strings resembling -h/--help must not be swallowed by a
# startswith('-h') or substring-based check; they must still hit the
# unchanged file-validity error.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("near_miss", ["--helpful", "-H", "help"])
def test_near_miss_help_spelling_falls_through_to_file_check(near_miss):
    result = _run([near_miss])

    assert result.returncode == 1
    assert f"error: not a file: {near_miss}" in result.stderr


# ---------------------------------------------------------------------------
# Normal invocation: unchanged argument-count, file-validity, and scan output
# ---------------------------------------------------------------------------

def test_missing_argument_still_exits_2_with_usage_on_stderr():
    result = _run([])

    assert result.returncode == 2
    assert result.stdout == ""
    assert "usage: section_weight_audit.py <path/to/doc.md>" in result.stderr


def test_invalid_file_path_still_exits_1_with_error_on_stderr(tmp_path):
    missing = tmp_path / "missing.md"

    result = _run([str(missing)])

    assert result.returncode == 1
    assert f"error: not a file: {missing}" in result.stderr


def test_normal_invocation_on_valid_doc_still_scans_and_exits_0(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("## A\n\nsome words here\n\n## B\n\nmore words here too\n")

    result = _run([str(doc)])

    assert result.returncode == 0
    assert "SUMMARY:" in result.stdout
    assert result.stderr == ""

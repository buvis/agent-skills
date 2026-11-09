"""
Help-flag tests for the survey entry point (run.py).

Covers -h/--help recognized as the first argument: a one-line usage message
on stdout, exit 0, and no brief printed. Also covers that normal invocation
(no help flag, or a non-help argument) still surveys and prints a brief, per
run.py's existing contract of ignoring arguments it does not recognize.
"""

import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent / "run.py"


def _run(args, cwd):
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Help: both spellings, as the sole argument
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_flag_exits_zero_with_one_line_usage_and_no_brief(flag, tmp_path):
    result = _run([flag], cwd=tmp_path)

    assert result.returncode == 0, (
        f"{flag} must exit 0, got {result.returncode}; stderr={result.stderr!r}"
    )
    lines = result.stdout.strip("\n").splitlines()
    assert len(lines) == 1, (
        f"{flag} must print exactly one usage line, got {lines!r}"
    )
    assert "run.py" in lines[0], (
        f"usage line must name the script, got {lines[0]!r}"
    )
    assert "## Where things live" not in result.stdout, (
        f"{flag} must not print the survey brief"
    )


def test_help_flag_does_not_survey_non_empty_directory(tmp_path):
    # run.py prints the brief only to stdout, never to a file; pin that by
    # surveying a non-empty directory and asserting the brief never appears
    # and the directory listing is unchanged, rather than an empty-directory
    # check that a help invocation would pass even if it wrote to a file.
    (tmp_path / "thing.py").write_text("def thing():\n    pass\n")
    before = sorted(tmp_path.iterdir())

    result = _run(["-h"], cwd=tmp_path)

    after = sorted(tmp_path.iterdir())
    assert before == after, "help must not scan or write into the surveyed directory"
    assert "## Where things live" not in result.stdout, "help must not print the brief"


# ---------------------------------------------------------------------------
# Near-miss: strings that resemble -h/--help but are not exact matches must
# not be swallowed by a startswith('-h') or substring-based check.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("near_miss", ["-help", "--helpful", "help", "-H"])
def test_near_miss_help_spelling_falls_through_to_normal_survey(near_miss, tmp_path):
    result = _run([near_miss], cwd=tmp_path)

    assert result.returncode == 0
    assert "## Where things live" in result.stdout, (
        f"{near_miss!r} is not -h/--help; run.py must ignore it and survey as before"
    )


# ---------------------------------------------------------------------------
# Normal invocation: unchanged behavior
# ---------------------------------------------------------------------------

def test_normal_invocation_with_no_args_still_surveys_and_prints_brief(tmp_path):
    (tmp_path / "thing.py").write_text("def thing():\n    pass\n")

    result = _run([], cwd=tmp_path)

    assert result.returncode == 0
    assert "## Where things live" in result.stdout
    assert "## Naming conventions" in result.stdout
    assert "## Error-handling style" in result.stdout

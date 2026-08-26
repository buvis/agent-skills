"""build.sh must resolve every path from its argument, never from the cwd.

A Bash tool call starts in its own working directory, so a build script that
reads relative paths silently assembles the wrong thing (or nothing) when the
caller is somewhere else. These tests run it from an unrelated cwd.
"""

import subprocess
from pathlib import Path

BUILD = Path(__file__).resolve().parents[1] / "references" / "build.sh"


def run(*args, cwd):
    return subprocess.run(["bash", str(BUILD), *args], cwd=cwd, capture_output=True, text=True)


def make_course(root: Path) -> Path:
    course = root / "course-name"
    (course / "modules").mkdir(parents=True)
    (course / "_base.html").write_text("BASE\n")
    (course / "modules" / "01-a.html").write_text("M1\n")
    (course / "modules" / "02-b.html").write_text("M2\n")
    (course / "_footer.html").write_text("FOOT\n")
    return course


def test_assembles_in_order_from_an_unrelated_cwd(tmp_path):
    course = make_course(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    result = run(str(course), cwd=elsewhere)

    assert result.returncode == 0, result.stderr
    assert (course / "index.html").read_text() == "BASE\nM1\nM2\nFOOT\n"
    assert not (elsewhere / "index.html").exists()


def test_refuses_without_a_course_directory(tmp_path):
    course = make_course(tmp_path)

    result = run(cwd=course)

    assert result.returncode != 0
    assert "usage" in result.stderr.lower()
    assert not (course / "index.html").exists()


def test_refuses_a_directory_with_no_modules(tmp_path):
    empty = tmp_path / "not-a-course"
    empty.mkdir()

    result = run(str(empty), cwd=tmp_path)

    assert result.returncode != 0
    assert "modules" in result.stderr
    assert not (empty / "index.html").exists()

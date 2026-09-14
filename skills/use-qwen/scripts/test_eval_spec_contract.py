"""Tests for eval_harness/spec.py: the repo and anchor path contracts, the kind
check against the classified writable list, UTF-8 reads and task-dir names."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from eval_harness import attempt
from eval_harness import prompts
from eval_harness import spec
from test_eval_spec import _assert_blames_only, _load, _payload, _tdd_payload


# The repository root is absolute in every host's spelling: a Windows form is
# accepted on a POSIX host too, because this is a check on the string, not a
# lookup on the filesystem. A colon alone does not make a drive root (`xy:/y`
# is no drive: a drive is one letter, in either case), and a drive letter with
# no separator behind it (`C:repo`) is drive-relative.
ABSOLUTE_REPOS = ["/repo/root", "C:\\repo\\root", "C:/repo/root", "d:/repo/root"]
RELATIVE_REPOS = [
    "repo/root", "./repo", "../repo", "repo", "~/repo", "a:b", "repo:root", "xy:/y", "C:repo",
    "1:/repo", "?:/repo",
]

# An anchor path is slash-form and repo-relative: no root, no drive (whatever
# its letter or separator), no backslash separator and no `..` segment
# anywhere in it - leading, inner, trailing or alone.
ILLEGAL_ANCHOR_PATHS = [
    pytest.param("/src/mod.py", id="leading-slash"),
    pytest.param("C:\\src\\mod.py", id="windows-drive"),
    pytest.param("D:/src/mod.py", id="windows-drive-forward-slash"),
    pytest.param("d:\\src\\mod.py", id="lowercase-drive"),
    pytest.param("d:/src/mod.py", id="lowercase-drive-forward-slash"),
    pytest.param("src\\mod.py", id="backslash-separator"),
    pytest.param("../src/mod.py", id="leading-parent"),
    pytest.param("src/../mod.py", id="inner-parent"),
    pytest.param("src/../../mod.py", id="double-parent"),
    pytest.param("pkg/deep/../mod.py", id="deep-inner-parent"),
    pytest.param("a/b/c/../../d.py", id="deep-double-parent"),
    pytest.param("src/..", id="trailing-parent"),
    pytest.param("..", id="parent-alone"),
]
# The `..` rule is per segment: a segment that merely CONTAINS two dots is a
# plain directory name.
LEGAL_ANCHOR_PATHS = ["src/mod.py", "pkg/deep/mod.py", "src/a..b/mod.py"]

# Task directory names without an integer prefix: letters, no hyphen at all,
# a letter before the hyphen, nothing before it, a decimal, and the spellings
# `int()` would forgive (a sign, a leading space, an underscore separator).
BAD_TASK_DIR_NAMES = ["abc-slug", "7", "x-1", "-slug", "1.5-half", "+7-fix", " 7-fix", "1_0-half"]

NON_ASCII_TASK_TEXT = "Oprav parser — přijímá čárky"
NON_ASCII_INSTRUCTIONS = "Pracuj podle seřazeného seznamu — žádné zkratky."

# Each script reaches exactly one of the two reads, so a failure names the
# file whose read is still implicit.
LOAD_SPEC_SCRIPT = """\
import sys
from pathlib import Path

from eval_harness import spec

print(spec.load_spec(Path(sys.argv[1]), "description").task_text)
"""

LOAD_REFERENCES_SCRIPT = """\
import sys
from pathlib import Path

from eval_harness import prompts

for reference in prompts.load_dispatch_references(Path(sys.argv[1])):
    print(reference.instructions)
"""


# -- helpers ---------------------------------------------------------------


def _payload_for(shape, **overrides):
    return _tdd_payload(**overrides) if shape == "tdd" else _payload(**overrides)


def _anchor(path):
    return {"path": path, "symbol": "parse", "start_line": 10, "end_line": 42}


def _run_with_implicit_encoding_as_error(script, target):
    """Run `script` on `target` in a fresh interpreter that turns every read
    made without an explicit encoding into an error.

    macOS forces UTF-8 as the locale encoding, so a locale trick cannot see
    the missing argument; the interpreter flag can, on every host.
    """
    return subprocess.run(
        [
            sys.executable,
            "-X",
            "warn_default_encoding",
            "-W",
            "error::EncodingWarning",
            "-c",
            script,
            str(target),
        ],
        cwd=Path(spec.__file__).resolve().parent.parent,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


# -- load_spec: repo is absolute -------------------------------------------


@pytest.mark.parametrize("shape", ["description", "tdd"])
@pytest.mark.parametrize("repo", ABSOLUTE_REPOS)
def test_accepts_an_absolute_repo_in_posix_or_windows_form_on_every_host(
    tmp_path, shape, repo
):
    loaded = _load(tmp_path, _payload_for(shape, repo=repo), shape)

    assert loaded.repo == Path(repo)


@pytest.mark.parametrize("shape", ["description", "tdd"])
@pytest.mark.parametrize("repo", RELATIVE_REPOS)
def test_refuses_a_relative_repo_by_name(tmp_path, shape, repo):
    with pytest.raises(spec.SpecError) as exc_info:
        _load(tmp_path, _payload_for(shape, repo=repo), shape)

    _assert_blames_only(exc_info, "repo", shape)


# -- load_spec: anchor paths are slash-form and repo-relative --------------


@pytest.mark.parametrize("path", ILLEGAL_ANCHOR_PATHS)
def test_refuses_an_absolute_backslash_or_traversing_anchor_path_by_name(tmp_path, path):
    body = _tdd_payload(read_anchors=[_anchor(path)])

    with pytest.raises(spec.SpecError) as exc_info:
        _load(tmp_path, body, "tdd")

    _assert_blames_only(exc_info, "read_anchors", "tdd")


@pytest.mark.parametrize("path", LEGAL_ANCHOR_PATHS)
def test_loads_a_slash_form_repo_relative_anchor_path(tmp_path, path):
    loaded = _load(tmp_path, _tdd_payload(read_anchors=[_anchor(path)]), "tdd")

    assert [anchor.path for anchor in loaded.read_anchors] == [path]


# -- classify_paths: a declared kind agrees with the final writable count --


@pytest.mark.parametrize(
    "declared,changed",
    [
        ("single-file", ["src/a.py", "src/b.py"]),
        ("multi-file", ["src/only.py"]),
        ("single-file", ["src/a.py", "src/b.py", "src/c.py"]),
        # Only an oracle path changed: the writable count is zero, not one.
        ("single-file", ["tests/test_a.py"]),
        ("single-file", [f"src/gen{i}.py" for i in range(7)]),
    ],
    ids=[
        "single-file-over-two",
        "multi-file-over-one",
        "single-file-over-three",
        "single-file-over-none",
        "single-file-over-seven",
    ],
)
def test_refuses_a_declared_kind_that_contradicts_the_classified_writable_count(
    tmp_path, declared, changed
):
    # No writable override, so load time has nothing to compare the kind with;
    # the classified list is the first place the contradiction can be seen. The
    # counts run from zero past two, so a check that only fires on one or two
    # writable paths is caught.
    loaded = _load(tmp_path, _payload(kind=declared))

    with pytest.raises(spec.SpecError) as exc_info:
        spec.classify_paths(changed, loaded)

    _assert_blames_only(exc_info, "kind")


def test_compares_the_declared_kind_with_the_writable_count_after_the_oracle_split(
    tmp_path,
):
    # Two changed paths, one of them a test: single-file is right once the
    # oracle path has been split off, so a count taken before the split would
    # wrongly refuse.
    loaded = _load(tmp_path, _payload(kind="single-file"))

    writable, oracle = spec.classify_paths(["src/only.py", "tests/test_only.py"], loaded)

    assert (writable, oracle) == (["src/only.py"], ["tests/test_only.py"])


def test_keeps_a_declared_multi_file_kind_over_two_classified_writable_paths(tmp_path):
    loaded = _load(tmp_path, _payload(kind="multi-file"))

    writable, oracle = spec.classify_paths(["src/b.py", "tests/test_a.py", "src/a.py"], loaded)

    assert writable == ["src/a.py", "src/b.py"]
    assert oracle == ["tests/test_a.py"]


@pytest.mark.parametrize(
    "changed", [["src/only.py"], ["src/a.py", "src/b.py"]], ids=["one", "two"]
)
def test_never_consults_the_kind_when_the_spec_declares_none(tmp_path, changed):
    loaded = _load(tmp_path, _payload())

    writable, oracle = spec.classify_paths(changed, loaded)

    assert writable == sorted(changed)
    assert oracle == []


def test_compares_the_declared_kind_with_the_writable_list_after_the_override(tmp_path):
    # The override wins wholesale, so the FINAL list is the one path it names:
    # single-file agrees with it, however many paths the commit range changed.
    loaded = _load(tmp_path, _payload(writable=["only/this.py"], kind="single-file"))

    writable, oracle = spec.classify_paths(["src/a.py", "src/b.py"], loaded)

    assert (writable, oracle) == (["only/this.py"], [])


# -- UTF-8 reads -----------------------------------------------------------


def test_refuses_a_spec_json_that_is_not_valid_utf8(tmp_path):
    # A bad byte is a malformed file, never silently replaced text.
    spec_dir = tmp_path / "tasks" / "7-fix-the-parser"
    spec_dir.mkdir(parents=True)
    body = json.dumps(_payload(task_text="cafX")).encode("utf-8").replace(b"cafX", b"caf\xe9")
    (spec_dir / "spec.json").write_bytes(body)

    with pytest.raises(spec.SpecError) as exc_info:
        spec.load_spec(spec_dir, "description")

    assert "spec.json" in str(exc_info.value)


def test_refuses_a_dispatch_references_json_that_is_not_valid_utf8(tmp_path):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "dispatch-references.json").write_bytes(
        b'[{"name": "ivan", "version": "vtwo", "instructions": "caf\xe9", "provenance": "d"}]')

    with pytest.raises(spec.SpecError) as exc_info:
        prompts.load_dispatch_references(evidence_dir)

    assert "dispatch-references.json" in str(exc_info.value)


def test_reads_spec_json_as_utf8_on_every_host(tmp_path):
    spec_dir = tmp_path / "tasks" / "7-fix-the-parser"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.json").write_text(
        json.dumps(_payload(task_text=NON_ASCII_TASK_TEXT), ensure_ascii=False),
        encoding="utf-8",
    )

    completed = _run_with_implicit_encoding_as_error(LOAD_SPEC_SCRIPT, spec_dir)

    assert completed.returncode == 0, completed.stderr
    assert NON_ASCII_TASK_TEXT in completed.stdout


def test_reads_dispatch_references_json_as_utf8_on_every_host(tmp_path):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    payload = [
        {
            "name": "ivan",
            "version": "vtwo",
            "instructions": NON_ASCII_INSTRUCTIONS,
            "provenance": "docs/dispatch.md",
        }
    ]
    (evidence_dir / "dispatch-references.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    completed = _run_with_implicit_encoding_as_error(LOAD_REFERENCES_SCRIPT, evidence_dir)

    assert completed.returncode == 0, completed.stderr
    assert NON_ASCII_INSTRUCTIONS in completed.stdout


# -- the task directory name -----------------------------------------------


@pytest.mark.parametrize("dir_name", BAD_TASK_DIR_NAMES)
def test_refuses_a_task_directory_without_an_integer_prefix_by_name(tmp_path, dir_name):
    with pytest.raises(spec.SpecError) as exc_info:
        _load(tmp_path, _payload(), dir_name=dir_name)

    # The spec.json inside is valid, so the message blames the directory name
    # and none of the keys that are right.
    _assert_blames_only(exc_info, dir_name)


@pytest.mark.parametrize("bad_name", BAD_TASK_DIR_NAMES)
def test_task_dirs_refuses_a_task_directory_without_an_integer_prefix_by_name(
    tmp_path, bad_name
):
    for name in ("1-calc", bad_name, "2-other"):
        (tmp_path / "tasks" / name).mkdir(parents=True)

    with pytest.raises(spec.SpecError) as exc_info:
        attempt._task_dirs(tmp_path)

    message = str(exc_info.value)
    assert bad_name in message
    # The two well-named siblings are not the problem, so they stay out of it.
    assert "1-calc" not in message
    assert "2-other" not in message


def test_task_dirs_orders_by_integer_prefix_not_by_text(tmp_path):
    for name in ("1-calc", "10-ten", "2-other"):
        (tmp_path / "tasks" / name).mkdir(parents=True)

    ordered = attempt._task_dirs(tmp_path)

    assert ordered == [tmp_path / "tasks" / name for name in ("1-calc", "2-other", "10-ten")]

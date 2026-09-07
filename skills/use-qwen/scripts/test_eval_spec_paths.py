"""Tests for eval_harness/spec.py: path classification."""
import json

import pytest

from eval_harness import spec


_ABSENT = object()

# The pinned test-path rules. These are TRANSCRIBED from another project's
# router, not imported, so they are enumerated here one case each: any drift
# in spec.py's copy shows up as a failure of a named case rather than as a
# silent behaviour change.
TEST_SEGMENTS = [
    "test",
    "tests",
    "__tests__",
    "spec",
    "specs",
    "fixtures",
    "__fixtures__",
    "__snapshots__",
    "testdata",
]

JS_EXTENSIONS = ["js", "jsx", "ts", "tsx", "mjs", "cjs"]

# The basename rules are globs, so they are written here as templates over a
# file stem and exercised with several unrelated stems. A set of the literal
# filenames named in this file would leave `test_bar.py` or `Widget.test.tsx`
# unclassified; only a real glob passes every stem.
BASENAME_TEMPLATES = [
    "conftest.py",
    "test_{stem}.py",
    "{stem}_test.py",
    "{stem}_test.go",
    "{stem}_spec.rb",
    "{stem}Test.java",
    "{stem}Tests.java",
    "test_{stem}.sh",
    "{stem}_test.sh",
] + [f"{{stem}}.test.{ext}" for ext in JS_EXTENSIONS] + [
    f"{{stem}}.spec.{ext}" for ext in JS_EXTENSIONS
]

STEMS = ["foo", "bar", "Widget"]

TEST_BASENAMES = list(
    dict.fromkeys(
        template.format(stem=stem)
        for stem in STEMS
        for template in BASENAME_TEMPLATES
    )
)

# Every pinned segment is checked in each of these (prefix, file stem) shapes,
# and every pinned basename in each of these directories, so no fixed list of
# whole paths can stand in for the rules.
SEGMENT_CONTEXTS = [
    ("", "anything_else"),
    ("src", "mod"),
    ("pkg/core", "widget"),
    ("lib/deep/nested", "handler"),
]

BASENAME_DIRECTORIES = ["", "src", "pkg/core/deep"]


# -- helpers ---------------------------------------------------------------


def _payload(**overrides):
    """A minimal spec payload valid for both shapes; pass _ABSENT to drop a key."""
    body = {
        "repo": "/repo/root",
        "first": "aaaaaaa",
        "last": "bbbbbbb",
        "raw_test_cmd": ["pytest", "-q"],
        "task_text": "make the failing tests pass",
    }
    for key, value in overrides.items():
        if value is _ABSENT:
            body.pop(key, None)
        else:
            body[key] = value
    return body


def _write_spec(tmp_path, body, dir_name="7-fix-the-parser"):
    spec_dir = tmp_path / "tasks" / dir_name
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.json").write_text(json.dumps(body))
    return spec_dir


def _load(tmp_path, body, shape="description", dir_name="7-fix-the-parser"):
    return spec.load_spec(_write_spec(tmp_path, body, dir_name), shape)


# -- classify_paths: pinned directory segments -----------------------------


@pytest.mark.parametrize("segment", TEST_SEGMENTS)
def test_treats_each_pinned_directory_segment_as_oracle(tmp_path, segment):
    # The prefix above the segment and the file below it both vary, including
    # the repo root as a prefix, so the rule has to look at the segments.
    loaded = _load(tmp_path, _payload())
    changed = [
        f"{prefix}/{segment}/{stem}.py" if prefix else f"{segment}/{stem}.py"
        for prefix, stem in SEGMENT_CONTEXTS
    ]

    writable, oracle = spec.classify_paths(changed, loaded)

    assert writable == []
    assert oracle == sorted(changed)


@pytest.mark.parametrize(
    "path",
    [
        "src/Tests/mod.py",  # segment match is case-sensitive
        "src/testsuite/mod.py",  # and exact, not a prefix
        "src/spectrum/mod.py",
        "src/helpers/mod.py",
    ],
)
def test_keeps_a_directory_that_is_not_a_pinned_segment_writable(tmp_path, path):
    loaded = _load(tmp_path, _payload())

    writable, oracle = spec.classify_paths([path], loaded)

    assert writable == [path]
    assert oracle == []


def test_never_reads_the_last_segment_as_a_directory_segment(tmp_path):
    # A source file literally named "tests" is judged by the basename rule,
    # which none of the globs match, so it stays writable.
    loaded = _load(tmp_path, _payload())

    writable, oracle = spec.classify_paths(["src/tests"], loaded)

    assert writable == ["src/tests"]
    assert oracle == []


def test_matches_a_pinned_segment_at_any_depth_above_the_file(tmp_path):
    loaded = _load(tmp_path, _payload())
    changed = ["a/tests/b/c/mod.py"]

    writable, oracle = spec.classify_paths(changed, loaded)

    assert writable == []
    assert oracle == ["a/tests/b/c/mod.py"]


# -- classify_paths: pinned basename globs ---------------------------------


@pytest.mark.parametrize("basename", TEST_BASENAMES)
def test_treats_each_pinned_basename_glob_as_oracle(tmp_path, basename):
    # Same basename under three directories, the repo root included, so the
    # glob has to be applied to the last segment wherever the file sits.
    loaded = _load(tmp_path, _payload())
    changed = [
        f"{directory}/{basename}" if directory else basename
        for directory in BASENAME_DIRECTORIES
    ]

    writable, oracle = spec.classify_paths(changed, loaded)

    assert writable == []
    assert oracle == sorted(changed)


@pytest.mark.parametrize(
    "path",
    [
        "src/foo.test.py",  # .py is not one of the js/ts extensions
        "src/foo.spec.rb",  # only *_spec.rb is pinned, not *.spec.rb
        "src/mytest.py",  # *_test.py needs the underscore
        "src/TEST_foo.py",  # basename globs are case-sensitive
        "src/conftest.js",
        "src/FooTest.py",  # *Test.java is java-only
        "src/widget.py",
        "src/Widget.tsx",
    ],
)
def test_keeps_a_basename_that_matches_no_pinned_glob_writable(tmp_path, path):
    loaded = _load(tmp_path, _payload())

    writable, oracle = spec.classify_paths([path], loaded)

    assert writable == [path]
    assert oracle == []


# -- classify_paths: output shape and overrides ----------------------------


def test_returns_both_lists_sorted_and_in_slash_form(tmp_path):
    loaded = _load(tmp_path, _payload())
    # The last three arrive with backslash separators: slash-form is a promise
    # about the output, so they must come back normalised, and the segment rule
    # has to see the segments inside them.
    changed = [
        "src/z.py",
        "pkg/a.py",
        "tests/z_mod.py",
        "src/a_test.py",
        r"src\tests\x_test.py",
        r"lib\__tests__\helper.py",
        r"pkg\core\widget.py",
    ]

    writable, oracle = spec.classify_paths(changed, loaded)

    assert isinstance(writable, list) and isinstance(oracle, list)
    assert writable == ["pkg/a.py", "pkg/core/widget.py", "src/z.py"]
    assert oracle == [
        "lib/__tests__/helper.py",
        "src/a_test.py",
        "src/tests/x_test.py",
        "tests/z_mod.py",
    ]
    assert all("\\" not in path for path in writable + oracle)


def test_writable_override_replaces_the_derived_writable_list_wholesale(tmp_path):
    loaded = _load(tmp_path, _payload(writable=["only/this.py"]))
    changed = ["src/a.py", "src/b.py", "tests/a_test.py"]

    writable, oracle = spec.classify_paths(changed, loaded)

    assert writable == ["only/this.py"]
    assert oracle == ["tests/a_test.py"]


def test_oracle_override_replaces_the_derived_oracle_list_wholesale(tmp_path):
    loaded = _load(tmp_path, _payload(oracle=["golden/expected.txt"]))
    changed = ["src/a.py", "src/b.py", "tests/a_test.py"]

    writable, oracle = spec.classify_paths(changed, loaded)

    assert oracle == ["golden/expected.txt"]
    assert writable == ["src/a.py", "src/b.py"]


def test_overrides_are_returned_sorted(tmp_path):
    body = _payload(
        writable=["src/z.py", "src/a.py"], oracle=["t/z.txt", "t/a.txt"]
    )
    loaded = _load(tmp_path, body)

    writable, oracle = spec.classify_paths(["unrelated/file.py"], loaded)

    assert writable == ["src/a.py", "src/z.py"]
    assert oracle == ["t/a.txt", "t/z.txt"]


def test_overrides_are_returned_in_slash_form(tmp_path):
    # Slash-form is promised for BOTH returned lists unconditionally, so an
    # override carrying backslashes is normalised exactly like a derived path.
    body = _payload(
        writable=[r"pkg\core\widget.py", r"pkg\a.py"],
        oracle=[r"t\golden\z.txt", r"t\a.txt"],
    )
    loaded = _load(tmp_path, body)

    writable, oracle = spec.classify_paths(["unrelated/file.py"], loaded)

    assert writable == ["pkg/a.py", "pkg/core/widget.py"]
    assert oracle == ["t/a.txt", "t/golden/z.txt"]
    assert all("\\" not in path for path in writable + oracle)


def test_overrides_are_sorted_after_normalisation_not_before(tmp_path):
    # "\" (0x5C) and "/" (0x2F) sort on opposite sides of "0" (0x30), so these
    # two entries come back in the other order if the sort runs on raw text.
    loaded = _load(tmp_path, _payload(writable=[r"pkg\a.py", "pkg0.py"]))

    writable, _ = spec.classify_paths(["unrelated/file.py"], loaded)

    assert writable == ["pkg/a.py", "pkg0.py"]

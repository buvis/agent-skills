"""Tests for eval_harness/spec.py: spec parsing and validation."""
import json
from pathlib import Path

import pytest

from eval_harness import spec


_ABSENT = object()


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


# Whole valid payloads that share no field value with each other or with the
# defaults above. Nothing here may be treated as "the" good spec: a loader
# that recognises one blessed payload, or that answers from constants instead
# of from the file, fails the round-trip below on the other rows.
VALID_PAYLOADS = [
    {
        "repo": "/repo/root",
        "first": "aaaaaaa",
        "last": "bbbbbbb",
        "raw_test_cmd": ["pytest", "-q"],
        "task_text": "make the failing tests pass",
    },
    {
        "repo": "/home/me/proj",
        "first": "deadbee",
        "last": "f00dcaf",
        "raw_test_cmd": ["cargo", "test"],
        "task_text": "port the tokenizer to Rust",
    },
    {
        "repo": "/srv/checkout/api-gateway",
        "first": "0123456789abcdef0123",
        "last": "fedcba9876543210fedc",
        "raw_test_cmd": ["npm", "run", "test", "--", "--silent"],
        "task_text": "teach the client to retry on 429",
    },
]


def _tdd_payload(**overrides):
    body = _payload(
        architecture="one module, no I/O",
        invariants=["pure functions only"],
        read_anchors=[
            {
                "path": "src/mod.py",
                "symbol": "parse",
                "start_line": 10,
                "end_line": 42,
            }
        ],
    )
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


# Siblings that are present and correct in the payloads above, ordered so the
# two picked for a given key are the distinctive ones.
_INNOCENT_KEYS = {
    "description": ("raw_test_cmd", "task_text", "repo", "first", "last"),
    "tdd": ("invariants", "architecture", "read_anchors", "raw_test_cmd", "task_text"),
}


def _assert_blames_only(exc_info, key, shape="description"):
    """The message names the offending key and none of its valid siblings.

    A single message that lists every key it might have meant satisfies "names
    the key" for every failure at once while telling a caller nothing, so the
    siblings that are correct in this very spec have to stay out of it.
    """
    message = str(exc_info.value)
    assert key in message
    for other in [name for name in _INNOCENT_KEYS[shape] if name != key][:2]:
        assert other not in message, (
            f"{other!r} is valid in this spec, but the message blames it too: "
            f"{message!r}"
        )


# -- load_spec: happy paths ------------------------------------------------


@pytest.mark.parametrize("body", VALID_PAYLOADS, ids=["pytest", "cargo", "npm"])
def test_loads_each_declared_field_back_out_of_a_description_spec(tmp_path, body):
    loaded = _load(tmp_path, _payload(**body))

    assert loaded.repo == Path(body["repo"])
    assert loaded.first == body["first"]
    assert loaded.last == body["last"]
    assert loaded.task_text == body["task_text"]
    assert loaded.raw_test_cmd == tuple(body["raw_test_cmd"])
    assert loaded.writable is None
    assert loaded.oracle is None
    assert loaded.pins == ()


@pytest.mark.parametrize(
    "repo", ["/repo/root", "/home/me/proj", "/srv/checkout/api-gateway"]
)
def test_stores_repo_as_a_path_object(tmp_path, repo):
    loaded = _load(tmp_path, _payload(repo=repo))

    assert isinstance(loaded.repo, Path)
    assert loaded.repo == Path(repo)


@pytest.mark.parametrize(
    "dir_name,task_id,slug",
    [
        ("7-fix-the-parser", 7, "fix-the-parser"),
        ("12-solo", 12, "solo"),
        ("9-other", 9, "other"),
        ("0-zero", 0, "zero"),
        ("3-port-to-rust", 3, "port-to-rust"),
        ("104-teach-the-client-to-retry", 104, "teach-the-client-to-retry"),
    ],
)
def test_parses_task_id_and_slug_splitting_on_the_first_hyphen_only(
    tmp_path, dir_name, task_id, slug
):
    loaded = _load(tmp_path, _payload(), dir_name=dir_name)

    assert loaded.task_id == task_id
    assert loaded.slug == slug


def test_loads_a_tdd_spec_with_its_read_anchors(tmp_path):
    body = _tdd_payload(
        read_anchors=[
            {
                "path": "src/mod.py",
                "symbol": "parse",
                "start_line": 10,
                "end_line": 42,
            },
            # end_line == start_line is the inclusive boundary of end >= start.
            {
                "path": "src/other.py",
                "symbol": "CONST",
                "start_line": 5,
                "end_line": 5,
            },
        ]
    )

    loaded = _load(tmp_path, body, shape="tdd")

    assert loaded.architecture == "one module, no I/O"
    assert loaded.invariants == ("pure functions only",)
    assert loaded.read_anchors == (
        spec.ReadAnchor(
            path="src/mod.py", symbol="parse", start_line=10, end_line=42
        ),
        spec.ReadAnchor(
            path="src/other.py", symbol="CONST", start_line=5, end_line=5
        ),
    )


# The anchors here share no path, symbol or line number with the ones above or
# with each other, so `start_line >= 1` and `end_line >= start_line` have to be
# computed: a loader that only recognises the anchors written elsewhere in this
# file rejects every row.
@pytest.mark.parametrize(
    "architecture,invariants,anchor",
    [
        (
            "two crates, one binary",
            ["no allocation in the hot loop", "errors bubble up"],
            {"path": "lib/x.rs", "symbol": "main", "start_line": 1, "end_line": 1000},
        ),
        (
            "a single React component tree",
            ["props stay read-only"],
            {
                "path": "app/Widget.tsx",
                "symbol": "Widget",
                "start_line": 812,
                "end_line": 813,
            },
        ),
        (
            "handlers over a shared store",
            ["handlers stay stateless", "no globals", "context comes first"],
            {
                "path": "pkg/core/handler.go",
                "symbol": "ServeHTTP",
                "start_line": 37,
                "end_line": 37,
            },
        ),
    ],
)
def test_loads_the_tdd_fields_back_out_of_the_spec(
    tmp_path, architecture, invariants, anchor
):
    body = _tdd_payload(
        architecture=architecture, invariants=invariants, read_anchors=[anchor]
    )

    loaded = _load(tmp_path, body, shape="tdd")

    assert loaded.architecture == architecture
    assert loaded.invariants == tuple(invariants)
    (got,) = loaded.read_anchors
    assert got.path == anchor["path"]
    assert got.symbol == anchor["symbol"]
    assert got.start_line == anchor["start_line"]
    assert got.end_line == anchor["end_line"]


def test_description_shape_does_not_require_the_tdd_only_fields(tmp_path):
    loaded = _load(tmp_path, _payload(), shape="description")

    assert loaded.architecture is None
    assert loaded.invariants == ()
    assert loaded.read_anchors == ()


# -- load_spec: required fields --------------------------------------------


def test_rejects_a_missing_spec_json(tmp_path):
    # The directory is there, the spec.json is not: a missing spec is a spec
    # error, not a bare filesystem error escaping to the caller.
    spec_dir = tmp_path / "tasks" / "7-fix-the-parser"
    spec_dir.mkdir(parents=True)

    with pytest.raises(spec.SpecError) as exc_info:
        spec.load_spec(spec_dir, "description")

    assert not isinstance(exc_info.value, FileNotFoundError)


@pytest.mark.parametrize(
    "text",
    ['{"repo": "/repo/root"', "", "   ", '{"repo": "/repo/root",}', "{'repo': 1}"],
    ids=["truncated", "empty", "blank", "trailing-comma", "single-quoted"],
)
def test_rejects_a_spec_json_that_does_not_parse(tmp_path, text):
    # "missing or malformed" covers both; a JSONDecodeError reaching the caller
    # is the parser leaking, not the loader reporting.
    spec_dir = tmp_path / "tasks" / "7-fix-the-parser"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.json").write_text(text)

    with pytest.raises(spec.SpecError) as exc_info:
        spec.load_spec(spec_dir, "description")

    assert not isinstance(exc_info.value, json.JSONDecodeError)


@pytest.mark.parametrize("shape", ["tdd", "description"])
@pytest.mark.parametrize(
    "key", ["repo", "first", "last", "raw_test_cmd", "task_text"]
)
def test_rejects_a_spec_missing_a_field_required_by_both_shapes(
    tmp_path, shape, key
):
    body = _tdd_payload(**{key: _ABSENT}) if shape == "tdd" else _payload(
        **{key: _ABSENT}
    )

    with pytest.raises(spec.SpecError) as exc_info:
        _load(tmp_path, body, shape=shape)

    _assert_blames_only(exc_info, key, shape)


@pytest.mark.parametrize("key", ["architecture", "invariants", "read_anchors"])
def test_rejects_a_tdd_spec_missing_a_tdd_only_field(tmp_path, key):
    with pytest.raises(spec.SpecError) as exc_info:
        _load(tmp_path, _tdd_payload(**{key: _ABSENT}), shape="tdd")

    _assert_blames_only(exc_info, key, "tdd")


# -- load_spec: field types ------------------------------------------------


# Each key is offered several unrelated wrong types, so a check that merely
# knows the handful of bad values these tests happen to pass cannot stand in
# for a type check. The other direction is closed by the round-trip tests
# above: the accepted values vary too, so a check that knows the handful of
# GOOD values named in this file cannot stand in for one either.
@pytest.mark.parametrize(
    "shape,key,value",
    [
        ("description", "repo", 5),
        ("description", "repo", None),
        ("description", "repo", {"path": "/repo/root"}),
        ("description", "repo", 3.5),
        ("description", "repo", ["/repo/root"]),
        ("description", "first", 5),
        ("description", "first", None),
        ("description", "first", 3.5),
        ("description", "first", {"sha": "aaaaaaa"}),
        ("description", "last", ["bbbbbbb"]),
        ("description", "last", None),
        ("description", "last", 3.5),
        ("description", "last", {}),
        ("description", "task_text", 5),
        ("description", "task_text", None),
        ("description", "task_text", {}),
        ("description", "task_text", ["make the failing tests pass"]),
        ("description", "pins", "one,two"),
        ("description", "pins", 5),
        ("description", "pins", [5]),
        ("description", "pins", [["one"]]),
        ("description", "writable", "src/a.py"),
        ("description", "writable", 5),
        ("description", "writable", {"paths": ["src/a.py"]}),
        ("description", "writable", [5]),
        ("description", "writable", [["src/a.py"]]),
        ("description", "oracle", "tests/a_test.py"),
        ("description", "oracle", 3.5),
        ("description", "oracle", {"paths": ["tests/a_test.py"]}),
        ("description", "oracle", [5]),
        ("description", "oracle", [["tests/a_test.py"]]),
        ("tdd", "architecture", 5),
        ("tdd", "architecture", ""),
        ("tdd", "architecture", None),
        ("tdd", "architecture", []),
        ("tdd", "architecture", {"text": "one module"}),
        ("tdd", "invariants", "pure functions only"),
        ("tdd", "invariants", [5]),
        ("tdd", "invariants", None),
        ("tdd", "invariants", {}),
        ("tdd", "invariants", [["pure functions only"]]),
        ("tdd", "read_anchors", "src/mod.py:10-42"),
        ("tdd", "read_anchors", None),
        ("tdd", "read_anchors", 5),
        ("tdd", "read_anchors", [None]),
        ("tdd", "read_anchors", [["src/mod.py"]]),
    ],
)
def test_rejects_a_field_of_the_wrong_type_and_names_it(tmp_path, shape, key, value):
    body = _tdd_payload(**{key: value}) if shape == "tdd" else _payload(
        **{key: value}
    )

    with pytest.raises(spec.SpecError) as exc_info:
        _load(tmp_path, body, shape=shape)

    _assert_blames_only(exc_info, key, shape)


@pytest.mark.parametrize("key", ["raw_test_cmd", "warmup"])
@pytest.mark.parametrize(
    "value",
    [
        [],  # empty list
        "pytest -q",  # not a list
        5,  # not a list either
        {"cmd": "pytest"},  # nor is a mapping
        ["pytest", ""],  # empty string element
        ["pytest", 5],  # non-string element
        ["pytest", None],  # nor is null a string
        [["pytest"], "-q"],  # nor is a nested list
    ],
    ids=[
        "empty-list",
        "non-list-str",
        "non-list-int",
        "non-list-dict",
        "empty-element",
        "int-element",
        "none-element",
        "nested-list-element",
    ],
)
def test_rejects_a_malformed_command_list_and_names_it(tmp_path, key, value):
    with pytest.raises(spec.SpecError) as exc_info:
        _load(tmp_path, _payload(**{key: value}))

    _assert_blames_only(exc_info, key)


def test_warmup_defaults_to_an_empty_tuple_when_absent(tmp_path):
    loaded = _load(tmp_path, _payload())

    assert loaded.warmup == ()


@pytest.mark.parametrize(
    "warmup",
    [
        ["uv", "sync", "--frozen"],
        ["cargo", "fetch"],
        ["make", "deps", "-j4", "--quiet"],
    ],
)
def test_keeps_warmup_command_order(tmp_path, warmup):
    loaded = _load(tmp_path, _payload(warmup=warmup))

    assert loaded.warmup == tuple(warmup)


@pytest.mark.parametrize(
    "pins",
    [
        ["src/parser.py", "docs/design.md"],
        ["pkg/core/handler.go", "README"],
        ["one", "two"],
    ],
)
def test_keeps_the_pins_list_in_order(tmp_path, pins):
    loaded = _load(tmp_path, _payload(pins=pins))

    assert loaded.pins == tuple(pins)


# -- load_spec: read_anchors entries ---------------------------------------


# The line-number cases spread across the whole domain - far negatives, a zero
# and a negative end, and an end-before-start pair whose numbers share nothing
# with the others - so no list of the specific numbers used here covers them.
@pytest.mark.parametrize(
    "anchor",
    [
        {
            "path": "src/mod.py",
            "symbol": "parse",
            "start_line": 10,
            "end_line": 42,
            "note": "extra key",
        },
        {"path": "src/mod.py", "start_line": 10, "end_line": 42},  # missing symbol
        {"path": "src/mod.py", "symbol": "parse", "start_line": 0, "end_line": 42},
        {"path": "src/mod.py", "symbol": "parse", "start_line": -2, "end_line": 42},
        {"path": "src/mod.py", "symbol": "parse", "start_line": -999, "end_line": 42},
        {"path": "src/mod.py", "symbol": "parse", "start_line": 7, "end_line": 0},
        {"path": "src/mod.py", "symbol": "parse", "start_line": 1, "end_line": -5},
        {"path": "src/mod.py", "symbol": "parse", "start_line": 10, "end_line": 9},
        {"path": "src/mod.py", "symbol": "parse", "start_line": 100, "end_line": 1},
        {"path": "src/mod.py", "symbol": "parse", "start_line": 640, "end_line": 3},
        {"path": "src/mod.py", "symbol": "parse", "start_line": "10", "end_line": 42},
    ],
    ids=[
        "extra-key",
        "missing-key",
        "zero-start",
        "negative-start",
        "far-negative-start",
        "zero-end",
        "negative-end",
        "end-before-start",
        "end-far-before-start",
        "end-far-before-a-large-start",
        "non-int-start",
    ],
)
def test_rejects_a_malformed_read_anchor(tmp_path, anchor):
    with pytest.raises(spec.SpecError) as exc_info:
        _load(tmp_path, _tdd_payload(read_anchors=[anchor]), shape="tdd")

    _assert_blames_only(exc_info, "read_anchors", "tdd")


# -- load_spec: reading_budget_tokens --------------------------------------


@pytest.mark.parametrize("value", [0, -1, -100000, 100001, 250000, "100", 3.5, [100]])
def test_rejects_an_out_of_range_or_non_int_reading_budget(tmp_path, value):
    with pytest.raises(spec.SpecError) as exc_info:
        _load(tmp_path, _payload(reading_budget_tokens=value))

    _assert_blames_only(exc_info, "reading_budget_tokens")


# The interior values matter as much as the endpoints: a check that accepts
# only the two bounds rejects every budget a real spec would carry.
@pytest.mark.parametrize("value", [1, 2, 3, 4096, 50000, 99999, 100000])
def test_accepts_any_reading_budget_within_the_inclusive_bounds(tmp_path, value):
    loaded = _load(tmp_path, _payload(reading_budget_tokens=value))

    assert loaded.reading_budget_tokens == value


def test_reading_budget_defaults_to_100000_when_absent(tmp_path):
    loaded = _load(tmp_path, _payload())

    assert loaded.reading_budget_tokens == 100000


# -- derive_kind and the declared kind -------------------------------------


# The generated rows below are built, not spelled out, so the answer has to
# come from the length of the list rather than from recognising the particular
# lists this file happens to name.
@pytest.mark.parametrize(
    "writable,expected",
    [
        (["only/this.py"], "single-file"),
        (["src/other.rs"], "single-file"),
        (["deep/nested/dir/widget.ts"], "single-file"),
        (["a.py", "b.py"], "multi-file"),
        (["x/one.py", "y/two.py", "z/three.py"], "multi-file"),
        ([], "multi-file"),
    ]
    + [([f"gen{i}.py"], "single-file") for i in (0, 4, 17, 233)]
    + [([f"gen{i}.py" for i in range(n)], "multi-file") for n in (0, 2, 3, 7, 40)],
)
def test_derive_kind_is_single_file_only_for_exactly_one_path(writable, expected):
    assert spec.derive_kind(writable) == expected


@pytest.mark.parametrize(
    "writable,expected",
    [
        (["only/this.py"], "single-file"),
        (["pkg/core/handler.go"], "single-file"),
        (["a.py", "b.py"], "multi-file"),
        (["x/one.py", "y/two.py", "z/three.py"], "multi-file"),
    ]
    + [([f"gen{i}.py"], "single-file") for i in (5, 88)]
    + [([f"gen{i}.py" for i in range(n)], "multi-file") for n in (2, 6)],
)
def test_derives_kind_from_the_writable_override_when_kind_is_absent(
    tmp_path, writable, expected
):
    loaded = _load(tmp_path, _payload(writable=writable))

    assert loaded.kind == expected


@pytest.mark.parametrize(
    "writable,declared",
    [
        (["a.py", "b.py"], "single-file"),
        (["x/one.py", "y/two.py", "z/three.py"], "single-file"),
        (["only/this.py"], "multi-file"),
        ([f"gen{i}.py" for i in range(5)], "single-file"),
        (["gen9.py"], "multi-file"),
    ],
)
def test_rejects_a_declared_kind_that_contradicts_the_writable_list(
    tmp_path, writable, declared
):
    body = _payload(writable=writable, kind=declared)

    with pytest.raises(spec.SpecError) as exc_info:
        _load(tmp_path, body)

    _assert_blames_only(exc_info, "kind")


# Membership stands on its own: a value outside the pair is rejected whether or
# not there is a writable override to compare it against.
@pytest.mark.parametrize(
    "writable", [_ABSENT, ["only/this.py"]], ids=["no-override", "with-override"]
)
@pytest.mark.parametrize(
    "declared",
    ["one-file", "singlefile", "", "SINGLE-FILE", "single file", "multi_file", "files"],
)
def test_rejects_a_kind_outside_the_two_allowed_values(tmp_path, declared, writable):
    body = _payload(writable=writable, kind=declared)

    with pytest.raises(spec.SpecError) as exc_info:
        _load(tmp_path, body)

    _assert_blames_only(exc_info, "kind")


@pytest.mark.parametrize(
    "writable,declared",
    [
        (["a.py", "b.py"], "multi-file"),
        (["only/this.py"], "single-file"),
        (["x/one.py", "y/two.py", "z/three.py"], "multi-file"),
        (["gen42.py"], "single-file"),
    ],
)
def test_keeps_a_declared_kind_that_agrees_with_the_writable_list(
    tmp_path, writable, declared
):
    loaded = _load(tmp_path, _payload(writable=writable, kind=declared))

    assert loaded.kind == declared

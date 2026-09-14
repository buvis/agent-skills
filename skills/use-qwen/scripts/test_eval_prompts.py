"""Tests for eval_harness/prompts.py: both prompt shapes and dispatch references."""
import hashlib
import json
from pathlib import Path

import pytest

from eval_harness import prompts
from eval_harness import spec


_ABSENT = object()
_RENAMED = object()

# The key a renamed entry carries in place of `name`.
RENAMED_KEY = "nombre"

# One task, rendered in both shapes. The anchors are deliberately NOT in path
# order and the second one starts above the first, so a render that sorts them
# fails the byte-exact case instead of passing by accident. Every anchor sits
# outside the writable and oracle lists: an anchor is read-only context, and
# one naming an editable or test path is refused (see the anchor section).
TASK_TEXT = "Fix the parser so it accepts trailing commas."
ARCHITECTURE = "The parser is a recursive descent over a token stream."
INVARIANTS = ("Tokens are never mutated.", "Errors carry the offending line.")
ANCHORS = (
    spec.ReadAnchor("src/lexer.py", "tokenize", 10, 42),
    spec.ReadAnchor("src/ast.py", "Node", 5, 9),
)
PINS = ("pkg==2.0", "tool>=3.0")
WRITABLE = ["src/parser.py", "src/tokens.py"]
ORACLE = ["tests/test_parser.py"]
BUDGET = 8000

# A second task with a different SHAPE, not just different words: one writable
# path instead of two, two oracle paths instead of one, one pin, one invariant,
# a single-line anchor and a smaller budget. Every section length differs, so a
# render that replays remembered bytes cannot satisfy both tasks.
OTHER_TASK_TEXT = "Teach the loader to accept a missing manifest."
OTHER_ARCHITECTURE = "The loader reads a manifest, then builds an index in one pass."
OTHER_INVARIANTS = ("The manifest is parsed once.",)
OTHER_ANCHORS = (
    spec.ReadAnchor("src/manifest.py", "load", 3, 3),
    spec.ReadAnchor("src/index.py", "Index", 200, 204),
)
OTHER_PINS = ("lib==1.1",)
OTHER_WRITABLE = ["src/loader.py"]
OTHER_ORACLE = ["tests/test_loader.py", "tests/test_index.py"]
OTHER_BUDGET = 500

OTHER_TASK = dict(
    task_text=OTHER_TASK_TEXT,
    architecture=OTHER_ARCHITECTURE,
    invariants=OTHER_INVARIANTS,
    read_anchors=OTHER_ANCHORS,
    pins=OTHER_PINS,
    reading_budget_tokens=OTHER_BUDGET,
)

CLOSING_LINE = (
    "Read only the relevant files, the failing tests and those anchors, "
    "with narrow symbol or line-range reads and no recursive exploration."
)

IVAN = prompts.DispatchReference(
    name="ivan",
    version="v2",
    instructions="Work the ordered task list; stop at the first red test.",
)
SUBAGENT = prompts.DispatchReference(
    name="subagent-dispatch",
    version="v3",
    instructions="Verify every surface you touched.\nName the file and the check.",
)

DESCRIPTION_EXPECTED = "\n".join(
    [
        TASK_TEXT,
        "You are working in the repository root: the current working directory. Files to edit:",
        "src/parser.py",
        "src/tokens.py",
        "pkg==2.0",
        "tool>=3.0",
        "Edit only inside this repository. Do not commit.",
    ]
)

OTHER_DESCRIPTION_EXPECTED = "\n".join(
    [
        OTHER_TASK_TEXT,
        "You are working in the repository root: the current working directory. Files to edit:",
        "src/loader.py",
        "lib==1.1",
        "Edit only inside this repository. Do not commit.",
    ]
)

NO_PINS_EXPECTED = "\n".join(
    [
        TASK_TEXT,
        "You are working in the repository root: the current working directory. Files to edit:",
        "src/parser.py",
        "src/tokens.py",
        "none",
        "Edit only inside this repository. Do not commit.",
    ]
)

TDD_BODY = "\n".join(
    [
        "Failing tests exist at:",
        "tests/test_parser.py",
        "Make all failing tests pass.",
        "Architecture:",
        ARCHITECTURE,
        "Key invariants:",
        "Tokens are never mutated.",
        "Errors carry the offending line.",
        "1. Do NOT modify test files",
        "2. Read the tests to understand expected behavior",
        "3. Implement minimal code to pass all tests",
        "4. Follow existing patterns and conventions",
        "5. Run tests after implementation to verify",
        "Relevant files:",
        "src/parser.py",
        "src/tokens.py",
        "Read-only anchors:",
        "src/lexer.py:tokenize lines 10-42",
        "src/ast.py:Node lines 5-9",
        "Reading budget: 8000 input tokens.",
        CLOSING_LINE,
    ]
)

OTHER_TDD_BODY = "\n".join(
    [
        "Failing tests exist at:",
        "tests/test_loader.py",
        "tests/test_index.py",
        "Make all failing tests pass.",
        "Architecture:",
        OTHER_ARCHITECTURE,
        "Key invariants:",
        "The manifest is parsed once.",
        "1. Do NOT modify test files",
        "2. Read the tests to understand expected behavior",
        "3. Implement minimal code to pass all tests",
        "4. Follow existing patterns and conventions",
        "5. Run tests after implementation to verify",
        "Relevant files:",
        "src/loader.py",
        "Read-only anchors:",
        "src/manifest.py:load lines 3-3",
        "src/index.py:Index lines 200-204",
        "Reading budget: 500 input tokens.",
        CLOSING_LINE,
    ]
)

# (spec overrides, writable paths, oracle paths, expected bytes) for each task.
DESCRIPTION_TASKS = [
    pytest.param({}, WRITABLE, ORACLE, DESCRIPTION_EXPECTED, id="parser-task"),
    pytest.param(
        OTHER_TASK,
        OTHER_WRITABLE,
        OTHER_ORACLE,
        OTHER_DESCRIPTION_EXPECTED,
        id="loader-task",
    ),
]

TDD_TASKS = [
    pytest.param({}, WRITABLE, ORACLE, TDD_BODY, id="parser-task"),
    pytest.param(OTHER_TASK, OTHER_WRITABLE, OTHER_ORACLE, OTHER_TDD_BODY, id="loader-task"),
]

# Every marker the refusal rule names, each one opening its own line.
LEAKED_LINES = [
    "diff --git a/src/parser.py b/src/parser.py",
    "@@ -10,3 +10,5 @@",
    "+++ b/src/parser.py",
    "--- a/src/parser.py",
    "Acceptance: the parser accepts trailing commas.",
    "Acceptance criteria: every listed test passes.",
]

# The same markers opening a line, with content that appears nowhere else in
# this file: the rule is about how a line STARTS, not about these exact strings.
NOVEL_LEAKED_LINES = [
    "diff --git a/other/file.rs b/other/file.rs",
    "@@ -1 +1 @@ fn other()",
    "+++ b/other/file.rs",
    "--- a/other/file.rs",
    "Acceptance: the other suite is green.",
    "Acceptance criteria: the other suite stays green.",
]

# The tdd context fields the harness author writes, paired with the key a
# refusal names: a leak reaches the model through the architecture text or
# either half of an anchor. The task text, the pins and the invariants are the
# operator's verbatim material and render as given, markers included. The
# anchor planted here sits outside the writable and oracle lists, so the only
# reason to refuse it is the leak. The leak sits at every position a reader
# could skip: the first, a middle or the last line of the architecture, and
# the first, a middle or the last anchor.
LEAK_CARRIERS = {
    "architecture-last-line": (
        "architecture",
        lambda leak: {"architecture": "%s\n%s" % (ARCHITECTURE, leak)},
    ),
    "architecture-first-line": (
        "architecture",
        lambda leak: {"architecture": "%s\n%s" % (leak, ARCHITECTURE)},
    ),
    "architecture-middle-line": (
        "architecture",
        lambda leak: {"architecture": "%s\n%s\nThe tokens are immutable." % (ARCHITECTURE, leak)},
    ),
    "anchor-symbol-last": (
        "read_anchors",
        lambda leak: {"read_anchors": ANCHORS + (spec.ReadAnchor("src/errors.py", leak, 1, 2),)},
    ),
    "anchor-symbol-first": (
        "read_anchors",
        lambda leak: {"read_anchors": (spec.ReadAnchor("src/errors.py", leak, 1, 2),) + ANCHORS},
    ),
    "anchor-path-last": (
        "read_anchors",
        lambda leak: {"read_anchors": ANCHORS + (spec.ReadAnchor(leak, "run", 1, 2),)},
    ),
    "anchor-path-middle": (
        "read_anchors",
        lambda leak: {"read_anchors": ANCHORS[:1] + (spec.ReadAnchor(leak, "run", 1, 2),)
                      + ANCHORS[1:]},
    ),
}

# Text that names a marker without leaking anything: markers buried mid-line,
# and a line that opens with the bare word `Acceptance` - the markers are
# `Acceptance:` and `Acceptance criteria`, neither of which this is.
ALLOWED_ARCHITECTURES = [
    pytest.param("Run diff --git before you touch @@ any of it.", id="markers-mid-line"),
    pytest.param(
        "%s\nAcceptance testing happens downstream." % ARCHITECTURE,
        id="line-opening-on-the-bare-word",
    ),
]

# Architecture prose whose lines OPEN with a bare marker character. Every patch
# marker carries a trailing space (`--- `, `@@ `, `+++ `), so a markdown rule and
# a decorator line are ordinary text and still reach the model.
BARE_MARKER_ARCHITECTURES = [
    pytest.param("%s\n---\nThe tokenizer sits underneath." % ARCHITECTURE, id="markdown-rule"),
    pytest.param("%s\n@@decorator wraps the entry point." % ARCHITECTURE, id="decorator-line"),
]

# (broken key, replacement value, key names the message may cite, a key it may not)
MALFORMED_ENTRIES = [
    pytest.param("version", _ABSENT, ("version",), "provenance", id="missing-key"),
    pytest.param(
        "provenance", _ABSENT, ("provenance",), "instructions", id="missing-provenance"
    ),
    pytest.param("notes", "extra", ("notes",), "provenance", id="extra-key"),
    pytest.param("version", 7, ("version",), "provenance", id="non-string"),
    pytest.param("instructions", "", ("instructions",), "provenance", id="empty"),
    pytest.param("provenance", None, ("provenance",), "instructions", id="null"),
    pytest.param("name", _RENAMED, ("name", RENAMED_KEY), "provenance", id="renamed-key"),
]


# -- helpers ---------------------------------------------------------------


def _spec(**overrides):
    """A Spec carrying everything both shapes render; override any field."""
    fields = dict(
        task_id=7,
        slug="fix-the-parser",
        repo=Path("/repo/root"),
        first="aaaaaaa",
        last="bbbbbbb",
        raw_test_cmd=("pytest", "-q"),
        task_text=TASK_TEXT,
        writable=None,
        oracle=None,
        pins=PINS,
        warmup=(),
        kind="multi-file",
        architecture=ARCHITECTURE,
        invariants=INVARIANTS,
        read_anchors=ANCHORS,
        reading_budget_tokens=BUDGET,
    )
    fields.update(overrides)
    return spec.Spec(**fields)


def _render(shape, references=(), writable_paths=None, oracle_paths=None, **overrides):
    return prompts.render_prompt(
        _spec(**overrides),
        shape,
        list(WRITABLE if writable_paths is None else writable_paths),
        list(ORACLE if oracle_paths is None else oracle_paths),
        references,
    )


def _block(reference):
    """The expected text of one dispatch-reference block."""
    return "Dispatch reference: %s %s\n%s" % (
        reference.name,
        reference.version,
        reference.instructions,
    )


def _expected_tdd(body, references):
    return "\n".join([body] + [_block(reference) for reference in references])


def _body(name, **overrides):
    """One valid dispatch-references.json entry; every value is digit-free."""
    entry = {
        "name": name,
        "version": "vtwo",
        "instructions": "Work the ordered task list.",
        "provenance": "docs/dispatch.md",
    }
    entry.update(overrides)
    return entry


def _malformed(key, value):
    """An entry broken at one key: dropped, added, renamed or given a bad value."""
    entry = _body("reviewer")
    if value is _ABSENT:
        entry.pop(key)
    elif value is _RENAMED:
        entry[RENAMED_KEY] = entry.pop(key)
    else:
        entry[key] = value
    return entry


def _carries_real_text(references):
    """Whether every reference carries non-empty text in all three fields."""
    return all(
        isinstance(getattr(reference, field), str) and getattr(reference, field)
        for reference in references
        for field in ("name", "version", "instructions")
    )


def _evidence(tmp_path, payload=_ABSENT):
    """An evidence dir, with dispatch-references.json only when payload is given."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    if payload is not _ABSENT:
        (evidence_dir / "dispatch-references.json").write_text(json.dumps(payload))
    return evidence_dir


def _both_entries():
    return [_body("ivan"), _body("subagent-dispatch")]


# -- the description shape -------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "writable_paths", "oracle_paths", "expected"), DESCRIPTION_TASKS
)
def test_description_shape_renders_task_writable_pins_then_the_edit_rule(
    overrides, writable_paths, oracle_paths, expected
):
    rendered = _render(
        "description", writable_paths=writable_paths, oracle_paths=oracle_paths, **overrides
    )

    assert rendered == expected


def test_description_shape_renders_no_reference_block():
    # Same bytes as the render with no references at all: the description shape
    # drops them even when the operator vendored some.
    assert _render("description", references=(IVAN, SUBAGENT)) == DESCRIPTION_EXPECTED


def test_pins_block_renders_the_literal_none_when_the_spec_has_no_pins():
    assert _render("description", pins=()) == NO_PINS_EXPECTED


# -- the tdd shape ---------------------------------------------------------


@pytest.mark.parametrize(("overrides", "writable_paths", "oracle_paths", "body"), TDD_TASKS)
def test_tdd_shape_renders_the_ordered_sections_then_the_reference_blocks(
    overrides, writable_paths, oracle_paths, body
):
    rendered = _render(
        "tdd",
        references=(IVAN, SUBAGENT),
        writable_paths=writable_paths,
        oracle_paths=oracle_paths,
        **overrides
    )

    assert rendered == _expected_tdd(body, (IVAN, SUBAGENT))


def test_tdd_shape_renders_the_paths_it_was_given_and_no_others():
    rendered = _render(
        "tdd",
        references=(IVAN, SUBAGENT),
        writable_paths=["a.py"],
        oracle_paths=["t/x.py"],
        read_anchors=(spec.ReadAnchor("b.py", "run", 1, 2),),
    )

    assert "a.py" in rendered
    assert "t/x.py" in rendered
    assert "b.py:run lines 1-2" in rendered
    # The paths of some other task must not survive into this prompt.
    assert "src/parser.py" not in rendered
    assert "src/tokens.py" not in rendered
    assert "tests/test_parser.py" not in rendered
    assert "src/lexer.py" not in rendered


def test_states_the_reading_budget_the_spec_carries():
    rendered = _render("tdd", references=(IVAN, SUBAGENT), reading_budget_tokens=500)

    assert "Reading budget: 500 input tokens." in rendered
    assert "Reading budget: 8000 input tokens." not in rendered


def test_renders_the_invariants_the_spec_carries_and_no_others():
    rendered = _render("tdd", references=(IVAN, SUBAGENT), invariants=("Only this one.",))

    assert "Only this one." in rendered
    assert all(invariant not in rendered for invariant in INVARIANTS)


def test_tdd_shape_omits_the_task_text_and_the_pins():
    rendered = _render("tdd", references=(IVAN, SUBAGENT))

    assert TASK_TEXT not in rendered
    assert all(pin not in rendered for pin in PINS)
    # Dropping the pins changes nothing, so neither the pins nor the `none`
    # placeholder that stands in for them reaches the tdd prompt.
    assert _render("tdd", references=(IVAN, SUBAGENT), pins=()) == rendered


def test_renders_reference_blocks_in_array_order():
    forward = _render("tdd", references=(IVAN, SUBAGENT))
    reversed_order = _render("tdd", references=(SUBAGENT, IVAN))

    assert forward != reversed_order
    assert reversed_order == _expected_tdd(TDD_BODY, (SUBAGENT, IVAN))


@pytest.mark.parametrize(("overrides", "writable_paths", "oracle_paths", "body"), TDD_TASKS)
def test_renders_the_same_bytes_for_every_engine_copy(
    overrides, writable_paths, oracle_paths, body
):
    # Two engines get the same task, so each renders its own copy from its own
    # Spec object. The prompt names no engine, so the digests must agree.
    first = _render(
        "tdd",
        references=(IVAN, SUBAGENT),
        writable_paths=writable_paths,
        oracle_paths=oracle_paths,
        **overrides
    )
    second = _render(
        "tdd",
        references=(IVAN, SUBAGENT),
        writable_paths=writable_paths,
        oracle_paths=oracle_paths,
        **overrides
    )

    assert hashlib.sha256(first.encode("utf-8")).hexdigest() == (
        hashlib.sha256(second.encode("utf-8")).hexdigest()
    )
    assert first == _expected_tdd(body, (IVAN, SUBAGENT))


# -- refusing an unknown shape ---------------------------------------------


def test_refuses_a_shape_that_is_neither_description_nor_tdd():
    # A typo'd or invented shape is refused, not quietly served the tdd prompt
    # (which would hand a description task the failing-test instructions).
    with pytest.raises(spec.SpecError):
        _render("banana", references=(IVAN, SUBAGENT))


# -- refusing leaked solution text -----------------------------------------


@pytest.mark.parametrize("carrier", sorted(LEAK_CARRIERS))
@pytest.mark.parametrize("leaked", LEAKED_LINES + NOVEL_LEAKED_LINES)
def test_refuses_leaked_solution_text_in_the_architecture_or_an_anchor(carrier, leaked):
    # The architecture text and either half of an anchor are the harness
    # author's context, so a leak in any of them is refused, and the refusal
    # names the key it travelled in and not the other one. The novel lines put
    # unknown-to-the-test content behind each marker in every carrier: the rule
    # reads the start of each line, it does not recognise a fixed list of
    # strings.
    key, plant = LEAK_CARRIERS[carrier]
    other = "read_anchors" if key == "architecture" else "architecture"

    with pytest.raises(spec.SpecError) as raised:
        _render("tdd", references=(IVAN, SUBAGENT), **plant(leaked))

    message = str(raised.value)
    assert key in message
    assert other not in message


@pytest.mark.parametrize("leaked", LEAKED_LINES + NOVEL_LEAKED_LINES)
def test_renders_the_task_text_as_given_leak_markers_included(leaked):
    # The task text is the verbatim ledger line plus its acceptance bullets, so
    # a description spec whose task text opens a line with `Acceptance:` (or a
    # patch marker) renders, and that line reaches the model byte for byte.
    task_text = "%s\n%s" % (TASK_TEXT, leaked)

    rendered = _render("description", task_text=task_text)

    assert rendered == DESCRIPTION_EXPECTED.replace(TASK_TEXT, task_text, 1)


@pytest.mark.parametrize("leaked", LEAKED_LINES + NOVEL_LEAKED_LINES)
def test_renders_a_pin_as_given_leak_markers_included(leaked):
    # The pins are the operator's material, not the harness author's context,
    # so a marker among them is rendered in place, not refused.
    rendered = _render("description", pins=PINS + (leaked,))

    assert rendered == DESCRIPTION_EXPECTED.replace(PINS[-1], "%s\n%s" % (PINS[-1], leaked), 1)


@pytest.mark.parametrize("leaked", LEAKED_LINES + NOVEL_LEAKED_LINES)
def test_renders_an_invariant_as_given_leak_markers_included(leaked):
    # Same for the invariants in the tdd shape: the extra invariant lands right
    # after the last one, marker and all.
    rendered = _render("tdd", references=(IVAN, SUBAGENT), invariants=INVARIANTS + (leaked,))

    body = TDD_BODY.replace(INVARIANTS[-1], "%s\n%s" % (INVARIANTS[-1], leaked), 1)
    assert rendered == _expected_tdd(body, (IVAN, SUBAGENT))


@pytest.mark.parametrize("architecture", BARE_MARKER_ARCHITECTURES)
def test_allows_architecture_lines_opening_with_a_bare_marker_character(architecture):
    # A markdown rule and a decorator open a line with the characters a patch
    # marker starts with, but neither carries the trailing space the marker
    # needs, so both are ordinary prose and still render.
    rendered = _render("tdd", references=(IVAN, SUBAGENT), architecture=architecture)

    assert architecture in rendered


@pytest.mark.parametrize("architecture", ALLOWED_ARCHITECTURES)
def test_allows_prose_that_names_a_marker_without_leaking(architecture):
    # A patch marker only counts when it opens a line, and the acceptance
    # markers are `Acceptance:` and `Acceptance criteria` - a line opening on
    # the bare word `Acceptance` is ordinary prose and still renders.
    rendered = _render("tdd", references=(IVAN, SUBAGENT), architecture=architecture)

    assert architecture in rendered


# -- refusing an anchor on an editable or test path ------------------------


# Where the offending anchor sits among the sound ones: every anchor is
# checked, not the last one alone.
ANCHOR_POSITIONS = [
    pytest.param(lambda bad: (bad,) + ANCHORS, id="first"),
    pytest.param(lambda bad: ANCHORS[:1] + (bad,) + ANCHORS[1:], id="middle"),
    pytest.param(lambda bad: ANCHORS + (bad,), id="last"),
]

# (anchor path, writable list handed in): each anchor shares a stem, a proper
# prefix or a whole name with a writable path without being one of them, in
# both directions. Membership is whole-path equality, so every row renders.
RESEMBLING_ANCHORS = [
    pytest.param("src/parser_types.py", WRITABLE, id="shared-stem"),
    pytest.param("src/parser", WRITABLE, id="anchor-is-a-bare-prefix"),
    pytest.param("src/parser.pyi", WRITABLE, id="writable-is-a-prefix"),
    pytest.param("src/parser.py", ["src/parser.pyi"], id="anchor-is-a-prefix"),
]


@pytest.mark.parametrize("place", ANCHOR_POSITIONS)
@pytest.mark.parametrize(
    ("anchor_path", "oracle_paths"),
    [
        pytest.param(WRITABLE[0], ORACLE, id="writable-path"),
        pytest.param(ORACLE[0], ORACLE, id="oracle-path"),
        pytest.param("golden/expected.txt", ["golden/expected.txt"], id="overridden-oracle-path"),
    ],
)
def test_refuses_an_anchor_on_a_writable_or_oracle_path_it_was_handed(
        anchor_path, oracle_paths, place):
    # An anchor is read-only context outside the files the model edits and the
    # tests it must not touch, so one naming a path from either classified list
    # is refused by name. The lists are the ones handed in: this Spec carries no
    # writable or oracle override of its own, and `golden/expected.txt` is an
    # oracle only because the handed list says so (no test-path rule names it).
    anchors = place(spec.ReadAnchor(anchor_path, "run", 1, 2))

    with pytest.raises(spec.SpecError) as raised:
        _render("tdd", references=(IVAN, SUBAGENT), oracle_paths=oracle_paths,
                read_anchors=anchors)

    message = str(raised.value)
    assert "read_anchors" in message
    assert "architecture" not in message


def test_renders_an_anchor_that_looks_like_a_test_path_but_is_in_neither_list():
    # Membership is against the handed lists, not the test-path heuristic: a
    # file named like a test that the classifier never listed is fair context.
    anchor = spec.ReadAnchor("src/x_test.py", "Token", 1, 4)

    rendered = _render("tdd", references=(IVAN, SUBAGENT), read_anchors=ANCHORS + (anchor,))

    assert "src/x_test.py:Token lines 1-4" in rendered


@pytest.mark.parametrize(("anchor_path", "writable_paths"), RESEMBLING_ANCHORS)
def test_renders_an_anchor_that_merely_resembles_a_writable_path(anchor_path, writable_paths):
    anchor = spec.ReadAnchor(anchor_path, "Token", 1, 4)

    rendered = _render(
        "tdd",
        references=(IVAN, SUBAGENT),
        writable_paths=writable_paths,
        read_anchors=ANCHORS + (anchor,),
    )

    assert "%s:Token lines 1-4" % anchor_path in rendered


# -- loading the operator-vendored references ------------------------------


@pytest.mark.parametrize("shape", ["description", "tdd"])
def test_loads_every_reference_in_array_order(tmp_path, shape):
    payload = [_body("subagent-dispatch", version="vthree"), _body("ivan")]

    loaded = prompts.load_dispatch_references(_evidence(tmp_path, payload), shape=shape)

    assert isinstance(loaded, tuple)
    assert [reference.name for reference in loaded] == ["subagent-dispatch", "ivan"]
    assert [reference.version for reference in loaded] == ["vthree", "vtwo"]
    assert all(reference.instructions == "Work the ordered task list." for reference in loaded)
    # Every field carries the vendored text, so no field was silently dropped.
    assert _carries_real_text(loaded)


def test_loads_an_extra_reference_beside_the_two_mandatory_ones_for_the_tdd_shape(tmp_path):
    # The tdd roster is a floor, not an exact pair: a third vendored reference
    # loads, in array order, alongside the two the shape requires.
    payload = _both_entries() + [_body("reviewer")]

    loaded = prompts.load_dispatch_references(_evidence(tmp_path, payload), shape="tdd")

    assert [reference.name for reference in loaded] == ["ivan", "subagent-dispatch", "reviewer"]
    assert _carries_real_text(loaded)


def test_returns_no_references_when_the_file_is_absent_for_the_description_shape(tmp_path):
    # Called without the keyword: the default shape is the description one.
    assert prompts.load_dispatch_references(_evidence(tmp_path)) == ()


def test_renders_the_description_shape_with_no_references_file_present(tmp_path):
    loaded = prompts.load_dispatch_references(_evidence(tmp_path))

    assert _render("description", references=loaded) == DESCRIPTION_EXPECTED


def test_refuses_a_references_file_that_is_not_valid_json(tmp_path):
    # A vendored file the operator broke while editing is a spec failure, not a
    # raw parser crash: absent means no references, unreadable means refused.
    evidence_dir = _evidence(tmp_path)
    (evidence_dir / "dispatch-references.json").write_text("{not json")

    with pytest.raises(spec.SpecError):
        prompts.load_dispatch_references(evidence_dir)


def test_requires_a_references_file_for_the_tdd_shape(tmp_path):
    with pytest.raises(spec.SpecError):
        prompts.load_dispatch_references(_evidence(tmp_path), shape="tdd")


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param([], id="empty-array"),
        pytest.param([_body("ivan")], id="no-subagent-dispatch"),
        pytest.param([_body("subagent-dispatch")], id="no-ivan"),
        pytest.param([_body("reviewer")], id="neither"),
        pytest.param([_body("reviewer"), _body("linter")], id="two-but-neither"),
    ],
)
def test_requires_both_mandatory_entries_for_the_tdd_shape(tmp_path, payload):
    with pytest.raises(spec.SpecError):
        prompts.load_dispatch_references(_evidence(tmp_path, payload), shape="tdd")


def test_refuses_two_references_sharing_a_name_for_the_tdd_shape(tmp_path):
    payload = _both_entries() + [_body("ivan", version="vthree")]

    with pytest.raises(spec.SpecError):
        prompts.load_dispatch_references(_evidence(tmp_path, payload), shape="tdd")


@pytest.mark.parametrize("owned", ["pi", "claude"])
def test_refuses_a_reference_name_the_versions_map_already_owns(tmp_path, owned):
    payload = _both_entries() + [_body(owned)]

    with pytest.raises(spec.SpecError):
        prompts.load_dispatch_references(_evidence(tmp_path, payload), shape="tdd")


# -- per-key validation of dispatch-references.json ------------------------


@pytest.mark.parametrize("shape", ["description", "tdd"])
@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize(("key", "value", "named", "absent"), MALFORMED_ENTRIES)
def test_names_the_index_and_key_of_a_malformed_entry(
    tmp_path, shape, position, key, value, named, absent
):
    # Both mandatory entries are present and every value in the payload is
    # digit-free, so the position digit in the message can only be the index of
    # the entry that broke - wherever in the array it sits.
    payload = _both_entries()
    payload.insert(position, _malformed(key, value))

    with pytest.raises(spec.SpecError) as raised:
        prompts.load_dispatch_references(_evidence(tmp_path, payload), shape=shape)

    message = str(raised.value)
    assert str(position) in message
    assert any(candidate in message for candidate in named)
    # A message reciting every index and every key would point the operator at
    # nothing, so the sound entries and their untouched keys stay out of it.
    assert all(str(other) not in message for other in {0, 1, 2} - {position})
    assert absent not in message


def test_refuses_a_top_level_object_instead_of_an_array(tmp_path):
    payload = {"references": _both_entries()}

    with pytest.raises(spec.SpecError) as raised:
        prompts.load_dispatch_references(_evidence(tmp_path, payload))

    message = str(raised.value).lower()
    # The complaint is that the top-level value is not an array, not that some
    # entry inside it is malformed.
    assert "array" in message
    assert "provenance" not in message

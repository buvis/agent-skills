"""The candidate prompts of the qwen evaluation harness: both shapes, one renderer.

The only file this module reads is the dispatch-references.json inside the
evidence directory it is handed: no git, no subprocess, no network. Every
rejection names the offending key, and for that file the offending array index
too, so an operator learns which entry to fix.
"""
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .spec import ReadAnchor, Spec, SpecError

SHAPES = ("description", "tdd")

_ROOT_LINE = ("You are working in the repository root: the current working directory. "
              "Files to edit:")
_EDIT_RULE = "Edit only inside this repository. Do not commit."
_NO_PINS = "none"
_TDD_STEPS = ("1. Do NOT modify test files",
              "2. Read the tests to understand expected behavior",
              "3. Implement minimal code to pass all tests",
              "4. Follow existing patterns and conventions",
              "5. Run tests after implementation to verify")
_CLOSING_LINE = ("Read only the relevant files, the failing tests and those anchors, "
                 "with narrow symbol or line-range reads and no recursive exploration.")

# A marker counts only where it opens a line: the same text mid-sentence is prose.
_LEAK_MARKERS = ("diff --git", "@@ ", "+++ ", "--- ", "Acceptance:", "Acceptance criteria")

_REFERENCES_FILE = "dispatch-references.json"
_REFERENCE_KEYS = ("name", "version", "instructions", "provenance")
_MANDATORY_NAMES = ("ivan", "subagent-dispatch")
# The run record's versions map already owns these names, so a vendored
# reference may not claim one and shadow the recorded tool version.
_RESERVED_NAMES = ("pi", "claude")


@dataclass(frozen=True)
class DispatchReference:
    name: str
    version: str
    instructions: str


def _fail(key: str, value: object) -> None:
    raise SpecError("%s: %r" % (key, value))


# -- rendering -------------------------------------------------------------


def _context_texts(spec: Spec) -> dict[str, tuple[str, ...]]:
    """The tdd context the harness author writes, by key: the architecture and the anchors.

    The task text, the pins and the invariants are the operator's verbatim
    material (the task text carries its acceptance bullets by contract), so
    they render as given and are not listed here.
    """
    return {"architecture": (spec.architecture,),
            "read_anchors": tuple(field for anchor in spec.read_anchors
                                  for field in (anchor.path, anchor.symbol))}


def _refuse_leaks(spec: Spec) -> None:
    """Refuse a tdd context that carries a patch hunk or an acceptance criterion."""
    for key, texts in _context_texts(spec).items():
        for text in texts:
            if any(line.startswith(_LEAK_MARKERS) for line in text.split("\n")):
                _fail(key, text)


def _refuse_listed_anchors(spec: Spec, writable: list[str], oracle: list[str]) -> None:
    """Refuse an anchor on a path the candidate edits or a test it must not touch."""
    for anchor in spec.read_anchors:
        if anchor.path in writable or anchor.path in oracle:
            _fail("read_anchors", anchor)


def _anchor_line(anchor: ReadAnchor) -> str:
    return "%s:%s lines %d-%d" % (anchor.path, anchor.symbol, anchor.start_line, anchor.end_line)


def _reference_block(reference: DispatchReference) -> str:
    return "Dispatch reference: %s %s\n%s" % (reference.name, reference.version,
                                              reference.instructions)


def _description_lines(spec: Spec, writable: list[str]) -> list[str]:
    return ([spec.task_text, _ROOT_LINE] + list(writable)
            + (list(spec.pins) or [_NO_PINS]) + [_EDIT_RULE])


def _tdd_lines(spec: Spec, writable: list[str], oracle: list[str],
               references: Sequence[DispatchReference]) -> list[str]:
    return (["Failing tests exist at:"] + list(oracle)
            + ["Make all failing tests pass.", "Architecture:", spec.architecture,
               "Key invariants:"] + list(spec.invariants) + list(_TDD_STEPS)
            + ["Relevant files:"] + list(writable)
            + ["Read-only anchors:"] + [_anchor_line(anchor) for anchor in spec.read_anchors]
            + ["Reading budget: %d input tokens." % spec.reading_budget_tokens, _CLOSING_LINE]
            + [_reference_block(reference) for reference in references])


def render_prompt(spec: Spec, shape: str, writable: list[str], oracle: list[str],
                  references: Sequence[DispatchReference]) -> str:
    """Render one candidate prompt; the description shape drops the references."""
    if shape not in SHAPES:
        _fail("shape", shape)
    if shape == "description":
        return "\n".join(_description_lines(spec, writable))
    _refuse_leaks(spec)
    _refuse_listed_anchors(spec, writable, oracle)
    return "\n".join(_tdd_lines(spec, writable, oracle, references))


# -- the operator-vendored dispatch references -----------------------------


def _vendored(evidence_dir: Path, shape: str) -> list:
    """The vendored array; an absent file is an empty roster for every shape but tdd."""
    path = evidence_dir / _REFERENCES_FILE
    if not path.exists():
        if shape == "tdd":
            raise SpecError("%s: missing" % _REFERENCES_FILE)
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SpecError("%s: %s" % (_REFERENCES_FILE, exc)) from exc
    if not isinstance(value, list):
        raise SpecError("%s: not an array" % _REFERENCES_FILE)
    return value


def _reference(index: int, entry: object) -> DispatchReference:
    """One validated entry; a rejection names its array index and its key, nothing else."""
    where = "references[%d]" % index
    if not isinstance(entry, dict):
        _fail(where, entry)
    for key in _REFERENCE_KEYS:
        if key not in entry:
            raise SpecError("%s.%s: missing" % (where, key))
    for key, value in entry.items():
        if key not in _REFERENCE_KEYS or not isinstance(value, str) or value == "":
            _fail("%s.%s" % (where, key), value)
    return DispatchReference(entry["name"], entry["version"], entry["instructions"])


def _check_roster(references: tuple[DispatchReference, ...]) -> None:
    """The tdd roster: both mandatory names, no repeat, no name the versions map owns."""
    names = [reference.name for reference in references]
    for name in _MANDATORY_NAMES:
        if name not in names:
            raise SpecError("references: %r missing" % name)
    for name in names:
        if names.count(name) > 1 or name in _RESERVED_NAMES:
            _fail("references", name)


def load_dispatch_references(evidence_dir: Path, *,
                             shape: str = "description") -> tuple[DispatchReference, ...]:
    """Load the vendored dispatch references in array order, validating each entry first."""
    references = tuple(_reference(index, entry)
                       for index, entry in enumerate(_vendored(evidence_dir, shape)))
    if shape == "tdd":
        _check_roster(references)
    return references

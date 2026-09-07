"""The task spec of the qwen evaluation harness: loading, validation, path routing.

The only file this module reads is the spec.json inside the directory it is
handed: no git, no subprocess, no network. Every rejection names the offending
key and nothing else, so a caller learns which field to fix.
"""
import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path

# Transcribed from the router these rules come from, never imported, so a drift
# between the two copies surfaces as a failing case instead of silent agreement.
TEST_SEGMENTS = ("test", "tests", "__tests__", "spec", "specs", "fixtures", "__fixtures__",
                 "__snapshots__", "testdata")
_JS_EXTENSIONS = ("js", "jsx", "ts", "tsx", "mjs", "cjs")
TEST_BASENAME_GLOBS = (("conftest.py", "test_*.py", "*_test.py", "*_test.go", "*_spec.rb",
                        "*Test.java", "*Tests.java", "test_*.sh", "*_test.sh")
                       + tuple("*.test.%s" % ext for ext in _JS_EXTENSIONS)
                       + tuple("*.spec.%s" % ext for ext in _JS_EXTENSIONS))

KINDS = ("single-file", "multi-file")
MAX_READING_BUDGET_TOKENS = 100000

_REQUIRED_KEYS = ("repo", "first", "last", "raw_test_cmd", "task_text")
_TDD_KEYS = ("architecture", "invariants", "read_anchors")
_ANCHOR_KEYS = ("path", "symbol", "start_line", "end_line")


class SpecError(ValueError):
    """Raised when a spec.json is missing or malformed. str() names the key."""


@dataclass(frozen=True)
class ReadAnchor:
    path: str
    symbol: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class Spec:
    task_id: int
    slug: str
    repo: Path
    first: str
    last: str
    raw_test_cmd: tuple[str, ...]
    task_text: str
    writable: tuple[str, ...] | None
    oracle: tuple[str, ...] | None
    pins: tuple[str, ...]
    warmup: tuple[str, ...]
    kind: str
    architecture: str | None
    invariants: tuple[str, ...]
    read_anchors: tuple[ReadAnchor, ...]
    reading_budget_tokens: int


def _fail(key: str, value: object) -> None:
    raise SpecError("%s: %r" % (key, value))


def _is_text(value: object) -> bool:
    return isinstance(value, str) and value != ""


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _read(spec_dir: Path) -> dict:
    try:
        body = json.loads((spec_dir / "spec.json").read_text())
    except (OSError, ValueError) as exc:
        raise SpecError("spec.json: %s" % exc) from exc
    if not isinstance(body, dict):
        raise SpecError("spec.json: %r" % body)
    return body


def _require_present(body: dict, keys: tuple[str, ...]) -> None:
    for key in keys:
        if key not in body:
            raise SpecError("%s: missing" % key)


def _text(body: dict, key: str) -> str:
    value = body[key]
    if not _is_text(value):
        _fail(key, value)
    return value


def _text_tuple(body: dict, key: str) -> tuple[str, ...] | None:
    """A list of non-empty strings, or None when the key is absent."""
    if key not in body:
        return None
    value = body[key]
    if not isinstance(value, list) or not all(_is_text(item) for item in value):
        _fail(key, value)
    return tuple(value)


def _command(body: dict, key: str) -> tuple[str, ...]:
    """A non-empty argv list; an absent key means no command at all."""
    if key not in body:
        return ()
    value = body[key]
    if not isinstance(value, list) or not value or not all(_is_text(a) for a in value):
        _fail(key, value)
    return tuple(value)


def _anchor(entry: object) -> ReadAnchor:
    if not isinstance(entry, dict) or set(entry) != set(_ANCHOR_KEYS):
        _fail("read_anchors", entry)
    start, end = entry["start_line"], entry["end_line"]
    if not _is_text(entry["path"]) or not _is_text(entry["symbol"]):
        _fail("read_anchors", entry)
    if not _is_int(start) or not _is_int(end) or start < 1 or end < start:
        _fail("read_anchors", entry)
    return ReadAnchor(entry["path"], entry["symbol"], start, end)


def _anchors(body: dict) -> tuple[ReadAnchor, ...]:
    value = body["read_anchors"]
    if not isinstance(value, list):
        _fail("read_anchors", value)
    return tuple(_anchor(entry) for entry in value)


def _kind(body: dict, writable: tuple[str, ...] | None) -> str:
    """The declared kind when it agrees with the writable override, else the derived one."""
    derived = derive_kind(list(writable or []))
    declared = body.get("kind")
    if declared is None:
        return derived
    if declared not in KINDS or (writable is not None and declared != derived):
        _fail("kind", declared)
    return declared


def _budget(body: dict) -> int:
    value = body.get("reading_budget_tokens", MAX_READING_BUDGET_TOKENS)
    if not _is_int(value) or not 1 <= value <= MAX_READING_BUDGET_TOKENS:
        _fail("reading_budget_tokens", value)
    return value


def derive_kind(writable: list[str]) -> str:
    """Exactly one writable path makes a single-file task; anything else is multi-file."""
    return "single-file" if len(writable) == 1 else "multi-file"


def load_spec(spec_dir: Path, shape: str) -> Spec:
    """Load and validate the spec.json of a task directory named <task_id>-<slug>."""
    body = _read(spec_dir)
    _require_present(body, _REQUIRED_KEYS + (_TDD_KEYS if shape == "tdd" else ()))
    task_id, slug = spec_dir.name.split("-", 1)
    writable = _text_tuple(body, "writable")
    return Spec(
        task_id=int(task_id),
        slug=slug,
        repo=Path(_text(body, "repo")),
        first=_text(body, "first"),
        last=_text(body, "last"),
        raw_test_cmd=_command(body, "raw_test_cmd"),
        task_text=_text(body, "task_text"),
        writable=writable,
        oracle=_text_tuple(body, "oracle"),
        pins=_text_tuple(body, "pins") or (),
        warmup=_command(body, "warmup"),
        kind=_kind(body, writable),
        architecture=_text(body, "architecture") if shape == "tdd" else None,
        invariants=_text_tuple(body, "invariants") if shape == "tdd" else (),
        read_anchors=_anchors(body) if shape == "tdd" else (),
        reading_budget_tokens=_budget(body),
    )


def _is_test_path(path: str) -> bool:
    """A pinned segment anywhere above the file, or a pinned basename glob."""
    segments = path.split("/")
    if any(segment in TEST_SEGMENTS for segment in segments[:-1]):
        return True
    return any(fnmatch.fnmatchcase(segments[-1], glob) for glob in TEST_BASENAME_GLOBS)


def _slash_sorted(paths: list[str]) -> list[str]:
    """Slash-form is promised for both returned lists, overrides included."""
    return sorted(path.replace("\\", "/") for path in paths)


def classify_paths(changed: list[str], spec: Spec) -> tuple[list[str], list[str]]:
    """Split changed paths into (writable, oracle); either spec override wins wholesale."""
    writable, oracle = [], []
    for raw in changed:
        path = raw.replace("\\", "/")
        (oracle if _is_test_path(path) else writable).append(path)
    if spec.writable is not None:
        writable = list(spec.writable)
    if spec.oracle is not None:
        oracle = list(spec.oracle)
    return _slash_sorted(writable), _slash_sorted(oracle)

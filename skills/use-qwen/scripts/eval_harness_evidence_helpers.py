"""Constants, builders and fixtures shared by the eval_harness evidence test modules.

The `vet` and `run` drivers are a later task, so every record they would have
written (`vetting.json`, `runs/<r>/...`) is hand-built here from the record
builders in test_eval_records.

The fixture repo's task is its second commit, so the spec names that commit as
both `first` and `last`: the sealed template is `first^`, the base commit that
holds the broken `calc.py`. The task commit also widens the oracle, so the
changed set carries one test path for `classify_paths` to file as oracle.
"""
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from eval_harness import evidence

import eval_harness_fixtures

# `bare_ci` is a fixture: pytest resolves it from this module's own namespace,
# so it has to be imported even though nothing here calls it.
from eval_harness_fixture_helpers import _git, bare_ci
from eval_harness_record_helpers import run_record, sealed_record
from test_eval_records import attempt, vetting

DESCRIPTION_LABELS = {
    "spec",
    "dispatch_references",
    "canonical_patch",
    "manifest",
    "oracle",
    "pretask",
    "prompt:description",
}

REFERENCES = [
    {
        "name": "ivan",
        "version": "1",
        "instructions": "Make the failing tests pass.",
        "provenance": "vendored",
    },
    {
        "name": "subagent-dispatch",
        "version": "1",
        "instructions": "Read narrowly.",
        "provenance": "vendored",
    },
]

TDD_FIELDS = {
    "architecture": "one module, one function",
    "invariants": ["add(a, b) == add(b, a)"],
    "read_anchors": [{"path": "calc.py", "symbol": "add", "start_line": 1, "end_line": 5}],
}

# Names git quotes in its default path output, one per escape class: a
# non-ASCII letter (octal escapes), a double quote (`\"`), a real TAB (`\t`),
# and a second non-ASCII spelling with other octal escapes. Undoing one class
# by hand leaves the others quoted. No backslash in any name: the record
# contract keeps paths in slash form and refuses one. Byte order, which is
# both git's and Python's order for these four.
QUOTED_NAMES = ("café.py", 'say "hi".py', "tab\there.py", "Ærø.py")

# The same four, one per line, as git's default listing spells them.
QUOTED_LISTING = (
    '"caf\\303\\251.py"\n'
    '"say \\"hi\\".py"\n'
    '"tab\\there.py"\n'
    '"\\303\\206r\\303\\270.py"\n'
)


# -- helpers ---------------------------------------------------------------


def _write_json(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_bytes(repo: Path, *args: str) -> bytes:
    """Git's stdout in `repo`, byte for byte."""
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=True, timeout=60
    ).stdout


def _literal(names) -> list:
    """The names as pathspecs git takes literally: a plain pathspec reads glob
    and escape characters, and these names are file names, not patterns."""
    return [f":(literal){name}" for name in names]


def _record_git_argv(monkeypatch) -> list:
    """Every argv `subprocess.run` is handed from here on, each call still made.

    Whichever helper a module runs git through, the command ends here. A
    reader that parses git's quoted text form has no reason to pass `-z`, so
    the argv is where that mechanism shows.
    """
    real_run = subprocess.run
    recorded = []

    def run(*popenargs, **kwargs):
        recorded.append(list(popenargs[0] if popenargs else kwargs["args"]))
        return real_run(*popenargs, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    return recorded


# Every way git is asked to print paths as a listing rather than as a patch. A
# reader that parses the quoted text form can reach for any of them; the
# `-z` pin has to cover the whole set or a decoy `-z` call beside a text one
# passes it.
_PATH_LISTING_FLAGS = ("--name-only", "--name-status", "--raw", "--numstat", "--stat",
                       "--summary", "--dirstat")
_PATH_LISTING_COMMANDS = ("ls-files", "ls-tree", "status", "diff-tree", "diff-index",
                          "diff-files")


def _path_listings(recorded: list) -> list:
    """The recorded commands that asked git to print paths as a listing."""
    return [argv for argv in recorded
            if any(flag in argv for flag in _PATH_LISTING_FLAGS)
            or any(command in argv for command in _PATH_LISTING_COMMANDS)]


def _snapshot(root: Path) -> dict:
    """Every path under `root`: a file's bytes, or None for a directory."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


def _files_under(root: Path) -> list:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def _spec_doc(info: dict, *, tdd: bool = False) -> dict:
    doc = {
        "repo": str(info["repo"]),
        "first": info["last"],
        "last": info["last"],
        "raw_test_cmd": ["python -m pytest -q"],
        "task_text": "make add() sum its arguments",
    }
    if tdd:
        doc.update(TDD_FIELDS)
    return doc


def _third_commit(info: dict) -> str:
    """Grow the fixture task by one more commit: touch the impl, add a helper.

    The added file is the tell: only a sealer that asks git for the range's
    changed set sees a path the fixture's own two commits never mention.
    """
    repo = info["repo"]
    impl = repo / info["impl"]
    impl.write_text(impl.read_text(encoding="utf-8") + "# reviewed\n", encoding="utf-8")
    (repo / "helper.py").write_text("def twice(value):\n    return 2 * value\n", encoding="utf-8")
    _git(repo, "add", info["impl"], "helper.py")
    _git(repo, *eval_harness_fixtures.IDENTITY, "commit", "-m", "task: annotate add(), add helper")
    return _git(repo, "rev-parse", "HEAD")


def _make_tdd(bundle) -> None:
    """Turn the bundle's task tdd-capable: the spec's tdd keys and the roster."""
    _write_json(bundle.task / "spec.json", _spec_doc(bundle.info, tdd=True))
    _write_json(bundle.root / "dispatch-references.json", REFERENCES)


def _vet(bundle, seal) -> dict:
    """What the vet driver would leave behind once the seal passed vetting."""
    record = vetting(
        template_sha=seal.template_sha,
        gate_bound_s=1800,
        inputs_sha256=seal.inputs_sha256,
        shapes=list(seal.shapes),
        ready=True,
    )
    _write_json(bundle.task / "vetting.json", record)
    return record


def _seal_and_vet(bundle, shapes=("description",)):
    seal = evidence.seal_inputs(bundle.root, bundle.task, shapes)
    _vet(bundle, seal)
    return seal


def _write_artifacts(where: Path, record: dict) -> None:
    """Every durable artifact `record` proves its attempt produced.

    The prompt and status land for every attempt; the rest follow the stages
    the record says ran: a baseline leaves its output, exit code and the
    sealed record it was measured against, a change leaves its patch, and each
    gate that ran leaves its output and exit code. Clone directories are
    reconstructible, so a bundle never has to carry them.
    """
    (where / "prompt.txt").write_bytes(b"ok\n")
    (where / "status.txt").write_bytes(b"ok\n")
    if record["baseline"] is not None:
        (where / "baseline.txt").write_bytes(b"ok\n")
        (where / "baseline.rc").write_bytes(b"1\n")
        _write_json(where / "sealed.json", sealed_record())
    if record["changed"] is not None:
        (where / "diff.patch").write_bytes(b"")
    for label, result in record["gates"].items():
        if result is not None:
            (where / f"{label}.txt").write_bytes(b"ok\n")
            (where / f"{label}.rc").write_bytes(b"0\n")


def _write_attempt(run: Path, attempt_id: str, **over) -> Path:
    """What the run driver leaves behind for one attempt: its record and the
    artifacts that record implies. `over` reaches the `attempt()` builder."""
    number, engine, ordinal = attempt_id.split("-")
    where = run / attempt_id
    where.mkdir()
    record = attempt(
        task=int(number),
        engine=engine,
        clone=str(where / "clone"),
        **{"attempt": int(ordinal[1:]), **over},
    )
    _write_json(where / "attempt.json", record)
    _write_artifacts(where, record)
    return where


def _build_run(bundle, seal, ids=("1-cmd1-a1",), *, marker="complete") -> Path:
    """What the run driver would leave behind for a run that ran `ids`."""
    run = bundle.root / "runs" / "r1"
    run.mkdir(parents=True)
    _write_json(run / "run.json", run_record(run_id=run.name))
    _write_json(run / "sealed-inputs.json", {"1-calc": seal.inputs_sha256})
    for attempt_id in ids:
        _write_attempt(run, attempt_id)
    header = (
        "finished: 2026-09-13T12:00:00Z"
        if marker == "complete"
        else "reason: operator stopped the run"
    )
    (run / f"{marker}.txt").write_text(
        f"attempts: {len(ids)}\n{header}\n" + "".join(f"{i}\n" for i in ids),
        encoding="utf-8",
    )
    return run


def _completed_bundle(bundle, ids=("1-cmd1-a1",)) -> Path:
    return _build_run(bundle, _seal_and_vet(bundle), ids)


def _verify(root: Path, capsys) -> tuple:
    rc = evidence.verify(root)
    return rc, capsys.readouterr().out.splitlines()


def _touch_json(path: Path) -> None:
    """Rewrite a JSON file with the same content and different bytes."""
    path.write_text(json.dumps(_read_json(path), indent=4), encoding="utf-8")


def _append(path: Path) -> None:
    path.write_bytes(path.read_bytes() + b"\n")


# One edit per sealed input, keyed by the label the edit must move.
MUTATIONS = {
    "edit-spec": (
        "spec",
        lambda b: _write_json(
            b.task / "spec.json",
            dict(_read_json(b.task / "spec.json"), task_text="make add() multiply"),
        ),
    ),
    "edit-dispatch-references": (
        "dispatch_references",
        lambda b: _write_json(
            b.root / "dispatch-references.json", [dict(r, version="2") for r in REFERENCES]
        ),
    ),
    "edit-canonical-patch": ("canonical_patch", lambda b: _append(b.task / "canonical.patch")),
    "reindent-manifest": ("manifest", lambda b: _touch_json(b.task / "manifest.json")),
    # An empty writable map, the other keys kept: the record still validates,
    # so only a seal over the file's bytes tells it from the vetted one.
    "edit-pretask": (
        "pretask",
        lambda b: _write_json(
            b.task / "pretask.json", dict(_read_json(b.task / "pretask.json"), writable={})
        ),
    ),
    # The same record in different bytes: a seal over a re-dump of the parsed
    # document would not move, the way the manifest's does not.
    "reindent-pretask": ("pretask", lambda b: _touch_json(b.task / "pretask.json")),
    "replace-oracle-file": (
        "oracle",
        lambda b: (b.task / "oracle" / "test_calc.py").write_text(
            eval_harness_fixtures.ORACLE, encoding="utf-8"
        ),
    ),
    "add-oracle-file": (
        "oracle",
        lambda b: (b.task / "oracle" / "extra_test.py").write_text(
            "def test_extra(): pass\n", encoding="utf-8"
        ),
    ),
    "remove-oracle-file": ("oracle", lambda b: (b.task / "oracle" / "test_calc.py").unlink()),
    "edit-description-prompt": (
        "prompt:description",
        lambda b: _append(b.task / "prompts" / "description.txt"),
    ),
    "edit-tdd-prompt": ("prompt:tdd", lambda b: _append(b.task / "prompts" / "tdd.txt")),
}

RECHECK_CASES = [
    "edit-spec",
    "edit-dispatch-references",
    "replace-oracle-file",
    "add-oracle-file",
    "edit-canonical-patch",
    "edit-pretask",
    "reindent-pretask",
]


# -- fixtures --------------------------------------------------------------


@pytest.fixture
def task_repo(tmp_path, bare_ci):
    root = tmp_path / "fixture"
    root.mkdir()
    return eval_harness_fixtures.build_fixture_repo(root, change_test=True)


@pytest.fixture
def bundle(tmp_path, task_repo):
    """A fresh evidence dir holding one unsealed task, `tasks/1-calc`."""
    evidence_dir = tmp_path / "evidence"
    task_dir = evidence_dir / "tasks" / "1-calc"
    task_dir.mkdir(parents=True)
    _write_json(task_dir / "spec.json", _spec_doc(task_repo))
    return SimpleNamespace(root=evidence_dir, task=task_dir, info=task_repo)

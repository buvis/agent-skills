"""Tests for `eval_harness.evidence`: sealing the inputs a run consumes and
verifying a restored bundle.

The `vet` and `run` drivers are a later task, so every record they would have
written (`vetting.json`, `runs/<r>/...`) is hand-built here from the record
builders in test_eval_records.

The fixture repo's task is its second commit, so the spec names that commit as
both `first` and `last`: the sealed template is `first^`, the base commit that
holds the broken `calc.py`. The task commit also widens the oracle, so the
changed set carries one test path for `classify_paths` to file as oracle. One
test grows the task by a third commit, so `first` and `last` stop coinciding.
"""
import dataclasses
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from eval_harness import evidence, prompts, records, spec, trees

import eval_harness_fixtures

# `bare_ci` is a fixture: pytest resolves it from this module's own namespace,
# so it has to be imported even though nothing here calls it.
from eval_harness_fixture_helpers import _git, bare_ci
from test_eval_records import attempt, vetting

DESCRIPTION_LABELS = {
    "spec",
    "dispatch_references",
    "canonical_patch",
    "manifest",
    "oracle",
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


def _write_attempt(run: Path, attempt_id: str) -> Path:
    number, engine, ordinal = attempt_id.split("-")
    where = run / attempt_id
    where.mkdir()
    record = attempt(
        task=int(number),
        engine=engine,
        clone=str(where / "clone"),
        **{"attempt": int(ordinal[1:])},
    )
    _write_json(where / "attempt.json", record)
    return where


def _build_run(bundle, seal, ids=("1-cmd1-a1",), *, marker="complete") -> Path:
    """What the run driver would leave behind for a run that ran `ids`."""
    run = bundle.root / "runs" / "r1"
    run.mkdir(parents=True)
    _write_json(run / "run.json", dict.fromkeys(records.RUN_KEYS))
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


# -- default_shapes --------------------------------------------------------


def test_default_shapes_offers_description_alone_for_a_plain_spec(bundle):
    assert evidence.default_shapes(bundle.task) == ("description",)


def test_default_shapes_adds_tdd_when_the_spec_carries_the_tdd_keys(bundle):
    _write_json(bundle.task / "spec.json", _spec_doc(bundle.info, tdd=True))
    assert evidence.default_shapes(bundle.task) == ("description", "tdd")

    # Presence is the whole test: whether the values hold up is sealing's job.
    hollow = dict(_spec_doc(bundle.info, tdd=True), architecture="")
    _write_json(bundle.task / "spec.json", hollow)
    assert evidence.default_shapes(bundle.task) == ("description", "tdd")


@pytest.mark.parametrize(
    "keys",
    [
        ("architecture",),
        ("invariants",),
        ("read_anchors",),
        ("architecture", "invariants"),
        ("architecture", "read_anchors"),
        ("invariants", "read_anchors"),
    ],
    ids="+".join,
)
def test_default_shapes_withholds_tdd_while_any_tdd_key_is_absent(bundle, keys):
    partial = dict(_spec_doc(bundle.info), **{key: TDD_FIELDS[key] for key in keys})
    _write_json(bundle.task / "spec.json", partial)

    # All three or nothing: a spec that sealing would refuse for tdd must not
    # be offered tdd on the strength of one key.
    assert evidence.default_shapes(bundle.task) == ("description",)


# -- seal_inputs -----------------------------------------------------------


def test_seal_writes_every_input_a_run_consumes_and_signs_what_is_on_disk(bundle):
    seal = evidence.seal_inputs(bundle.root, bundle.task, evidence.default_shapes(bundle.task))

    for name in (
        "pretask.json",
        "manifest.json",
        "canonical.patch",
        "oracle/test_calc.py",
        "prompts/description.txt",
    ):
        assert (bundle.task / name).is_file(), name
    assert (bundle.task / "template").is_dir()
    assert not (bundle.task / "prompts" / "tdd.txt").exists()
    # The vet driver writes these two. A sealer that writes them marks a task
    # ready that nobody vetted.
    assert not (bundle.task / "vetting.json").exists()
    assert not (bundle.task / "ready").exists()

    assert isinstance(seal, evidence.Seal)
    assert [field.name for field in dataclasses.fields(seal)] == [
        "template_sha",
        "writable",
        "oracle",
        "shapes",
        "inputs_sha256",
    ]
    assert seal.template_sha == trees.head_sha(bundle.task / "template")
    assert seal.writable == ("calc.py",)
    assert seal.oracle == ("test_calc.py",)
    assert seal.shapes == ("description",)
    assert set(seal.inputs_sha256) == DESCRIPTION_LABELS
    assert seal.inputs_sha256["dispatch_references"] == "absent"
    assert seal.inputs_sha256 == evidence.inputs_sha256(
        bundle.root, bundle.task, ("description",)
    )


def test_seal_records_the_template_it_built_in_pretask_and_manifest(bundle):
    seal = evidence.seal_inputs(bundle.root, bundle.task, ("description",))
    template = bundle.task / "template"

    pretask = _read_json(bundle.task / "pretask.json")
    assert records.validate_record("pretask", pretask) is None
    assert pretask == {
        "head_sha": seal.template_sha,
        "writable": trees.hash_paths(template, ["calc.py"]),
        "oracle": trees.hash_paths(template, ["test_calc.py"]),
    }
    # The template is the tree before the task: the broken impl and the
    # original oracle, and both digests are real, not "absent".
    assert pretask["writable"]["calc.py"] == _sha256(
        eval_harness_fixtures.BROKEN_IMPL.encode("utf-8")
    )
    assert pretask["oracle"]["test_calc.py"] == _sha256(
        eval_harness_fixtures.ORACLE.encode("utf-8")
    )
    assert _read_json(bundle.task / "manifest.json") == trees.build_manifest(template)


def test_seal_cuts_the_canonical_patch_over_the_writable_paths_only(bundle):
    info = bundle.info
    evidence.seal_inputs(bundle.root, bundle.task, ("description",))

    patch = (bundle.task / "canonical.patch").read_bytes()

    assert patch == _git_bytes(
        info["repo"], "diff", "--binary", f"{info['last']}^", info["last"], "--", "calc.py"
    )
    assert patch.startswith(b"diff --git ")
    assert b"a/calc.py" in patch
    # The task commit changed the test too; it is oracle, so the patch never
    # carries it.
    assert b"test_calc.py" not in patch


def test_seal_copies_each_oracle_path_as_the_task_commit_left_it(bundle):
    info = bundle.info
    evidence.seal_inputs(bundle.root, bundle.task, ("description",))

    copied = (bundle.task / "oracle" / "test_calc.py").read_bytes()

    assert copied == _git_bytes(info["repo"], "show", f"{info['last']}:test_calc.py")
    assert copied == eval_harness_fixtures.WIDENED_ORACLE.encode("utf-8")
    # `<last>`, not the template: the oracle is the test the task ends with.
    assert copied != (bundle.task / "template" / "test_calc.py").read_bytes()
    assert _files_under(bundle.task / "oracle") == ["test_calc.py"]


def test_seal_takes_the_writable_and_oracle_lists_from_the_spec_when_it_overrides(bundle):
    info = bundle.info
    _write_json(
        bundle.task / "spec.json",
        dict(_spec_doc(info), writable=["calc.py", "test_calc.py"], oracle=[]),
    )

    seal = evidence.seal_inputs(bundle.root, bundle.task, ("description",))

    # The override moves the test file over to writable; a sealer that
    # hardcodes the fixture's split still files it as oracle.
    assert seal.writable == ("calc.py", "test_calc.py")
    assert seal.oracle == ()
    assert _files_under(bundle.task / "oracle") == []
    pretask = _read_json(bundle.task / "pretask.json")
    assert pretask["oracle"] == {}
    assert pretask["writable"] == trees.hash_paths(
        bundle.task / "template", ["calc.py", "test_calc.py"]
    )
    patch = (bundle.task / "canonical.patch").read_bytes()
    assert patch == _git_bytes(
        info["repo"],
        "diff",
        "--binary",
        f"{info['last']}^",
        info["last"],
        "--",
        "calc.py",
        "test_calc.py",
    )
    assert b"a/test_calc.py" in patch
    assert seal.inputs_sha256["oracle"] == _sha256(b"")


def test_seal_spans_the_whole_task_range_from_before_first_to_last(bundle):
    info = bundle.info
    repo = info["repo"]
    third = _third_commit(info)
    _write_json(bundle.task / "spec.json", dict(_spec_doc(info), first=info["last"], last=third))

    seal = evidence.seal_inputs(bundle.root, bundle.task, ("description",))

    # The changed set comes from git over the whole range: the helper only the
    # third commit adds is writable, and a sealer that hardcodes the fixture's
    # two paths never lists it.
    assert seal.writable == ("calc.py", "helper.py")
    assert seal.oracle == ("test_calc.py",)
    # The template is the tree before `first`, the base commit: a sealer that
    # steps back from `last` instead seals the already-fixed impl.
    template = bundle.task / "template"
    assert (template / "calc.py").read_bytes() == eval_harness_fixtures.BROKEN_IMPL.encode("utf-8")
    assert not (template / "helper.py").exists()
    pretask = _read_json(bundle.task / "pretask.json")
    assert set(pretask["writable"]) == {"calc.py", "helper.py"}
    assert pretask["writable"] == trees.hash_paths(template, ["calc.py", "helper.py"])
    assert pretask["writable"]["helper.py"] == "absent"
    patch = (bundle.task / "canonical.patch").read_bytes()
    assert patch == _git_bytes(
        repo, "diff", "--binary", f"{info['last']}^", third, "--", "calc.py", "helper.py"
    )
    assert patch != _git_bytes(
        repo, "diff", "--binary", f"{third}^", third, "--", "calc.py", "helper.py"
    )
    assert b"# reviewed" in patch
    assert b"a/helper.py" in patch
    copied = (bundle.task / "oracle" / "test_calc.py").read_bytes()
    assert copied == _git_bytes(repo, "show", f"{third}:test_calc.py")


def test_seal_writes_the_rendered_prompt_byte_for_byte(bundle):
    seal = evidence.seal_inputs(bundle.root, bundle.task, ("description",))

    expected = prompts.render_prompt(
        spec.load_spec(bundle.task, "description"),
        "description",
        list(seal.writable),
        list(seal.oracle),
        prompts.load_dispatch_references(bundle.root, shape="description"),
    )
    written = (bundle.task / "prompts" / "description.txt").read_bytes()
    assert written == expected.encode("utf-8")
    assert seal.inputs_sha256["prompt:description"] == _sha256(written)


def test_seal_adds_tdd_only_when_the_spec_supports_it_and_the_caller_asks(bundle):
    _make_tdd(bundle)

    seal = evidence.seal_inputs(bundle.root, bundle.task, ("tdd", "description"))

    assert seal.shapes == ("description", "tdd")
    assert set(seal.inputs_sha256) == DESCRIPTION_LABELS | {"prompt:tdd"}
    expected = prompts.render_prompt(
        spec.load_spec(bundle.task, "tdd"),
        "tdd",
        list(seal.writable),
        list(seal.oracle),
        prompts.load_dispatch_references(bundle.root, shape="tdd"),
    )
    written = (bundle.task / "prompts" / "tdd.txt").read_bytes()
    assert written == expected.encode("utf-8")
    assert seal.inputs_sha256["prompt:tdd"] == _sha256(written)
    assert seal.inputs_sha256 == evidence.inputs_sha256(
        bundle.root, bundle.task, ("description", "tdd")
    )

    only = evidence.seal_inputs(bundle.root, bundle.task, ("description",))

    assert only.shapes == ("description",)
    assert set(only.inputs_sha256) == DESCRIPTION_LABELS
    assert not (bundle.task / "prompts" / "tdd.txt").exists()


@pytest.mark.parametrize(
    "shapes", [(), ("spec",), ("TDD",), ("description", "description"), ("tdd", "tdd")]
)
def test_seal_refuses_a_shape_list_outside_the_two_shapes(bundle, shapes):
    assert issubclass(evidence.EvidenceError, RuntimeError)
    before = _snapshot(bundle.task)

    with pytest.raises(evidence.EvidenceError) as caught:
        evidence.seal_inputs(bundle.root, bundle.task, shapes)

    assert "shapes" in str(caught.value)
    assert _snapshot(bundle.task) == before


@pytest.mark.parametrize("kind", ["empty-directory", "file", "populated-directory"])
def test_seal_refuses_an_evidence_dir_that_already_holds_runs(bundle, kind):
    runs = bundle.root / "runs"
    if kind == "file":
        runs.write_text("", encoding="utf-8")
    else:
        runs.mkdir()
    if kind == "populated-directory":
        (runs / "r1").mkdir()
    before = _snapshot(bundle.task)

    with pytest.raises(evidence.EvidenceError) as caught:
        evidence.seal_inputs(bundle.root, bundle.task, ("description",))

    # A run already consumed the old seal; a new seal under it would silently
    # change what that run's records claim to have measured.
    assert "runs/" in str(caught.value)
    assert "fresh" in str(caught.value)
    assert _snapshot(bundle.task) == before


def test_seal_propagates_the_spec_error_for_tdd_on_a_spec_without_the_tdd_keys(bundle):
    _write_json(bundle.root / "dispatch-references.json", REFERENCES)
    before = _snapshot(bundle.task)

    with pytest.raises(spec.SpecError) as caught:
        evidence.seal_inputs(bundle.root, bundle.task, ("description", "tdd"))

    assert any(key in str(caught.value) for key in TDD_FIELDS)
    assert _snapshot(bundle.task) == before


def test_tdd_seal_without_references_writes_nothing_and_description_still_seals(bundle):
    _write_json(bundle.task / "spec.json", _spec_doc(bundle.info, tdd=True))
    assert not (bundle.root / "dispatch-references.json").exists()
    before = _snapshot(bundle.task)

    with pytest.raises(spec.SpecError):
        evidence.seal_inputs(bundle.root, bundle.task, ("description", "tdd"))

    # Every prompt renders before the first byte lands, so a refused tdd
    # request leaves no half-sealed task behind.
    assert _snapshot(bundle.task) == before

    seal = _seal_and_vet(bundle, ("description",))

    assert seal.inputs_sha256["dispatch_references"] == "absent"
    assert evidence.recheck_inputs(bundle.root, bundle.task) == seal.inputs_sha256


def test_resealing_replaces_the_sealed_set_wholesale(bundle):
    _make_tdd(bundle)
    first = evidence.seal_inputs(bundle.root, bundle.task, ("description", "tdd"))
    for stale in ("oracle/stale_test.py", "template/junk.txt", "prompts/junk.txt"):
        (bundle.task / stale).write_text("gone next seal\n", encoding="utf-8")

    second = evidence.seal_inputs(bundle.root, bundle.task, ("description",))

    assert _files_under(bundle.task / "oracle") == ["test_calc.py"]
    assert _files_under(bundle.task / "prompts") == ["description.txt"]
    assert not (bundle.task / "template" / "junk.txt").exists()
    template = bundle.task / "template"
    assert _read_json(bundle.task / "manifest.json") == trees.build_manifest(template)
    # Same inputs, same digests: the labels both seals share agree.
    assert second.inputs_sha256 == {
        label: digest for label, digest in first.inputs_sha256.items() if label != "prompt:tdd"
    }
    assert second.inputs_sha256 == evidence.inputs_sha256(
        bundle.root, bundle.task, ("description",)
    )


# -- inputs_sha256 ---------------------------------------------------------


def test_inputs_sha256_signs_each_input_by_its_bytes(bundle):
    _make_tdd(bundle)
    task = bundle.task

    seal = evidence.seal_inputs(bundle.root, task, ("description", "tdd"))

    oracle_digest = _sha256((task / "oracle" / "test_calc.py").read_bytes())
    assert seal.inputs_sha256 == {
        "spec": _sha256((task / "spec.json").read_bytes()),
        "dispatch_references": _sha256((bundle.root / "dispatch-references.json").read_bytes()),
        "canonical_patch": _sha256((task / "canonical.patch").read_bytes()),
        "manifest": _sha256((task / "manifest.json").read_bytes()),
        "oracle": _sha256(f"test_calc.py\0{oracle_digest}\n".encode()),
        "prompt:description": _sha256((task / "prompts" / "description.txt").read_bytes()),
        "prompt:tdd": _sha256((task / "prompts" / "tdd.txt").read_bytes()),
    }


def test_oracle_label_signs_every_file_under_oracle_in_sorted_slash_order(bundle):
    evidence.seal_inputs(bundle.root, bundle.task, ("description",))
    oracle = bundle.task / "oracle"
    (oracle / "tests").mkdir()
    (oracle / "tests" / "test_deep.py").write_bytes(b"def test_deep(): pass\n")
    (oracle / "a_test.py").write_bytes(b"def test_a(): pass\n")
    entries = _files_under(oracle)
    assert entries == ["a_test.py", "test_calc.py", "tests/test_deep.py"]
    expected = b"".join(
        f"{rel}\0{_sha256((oracle / rel).read_bytes())}\n".encode() for rel in entries
    )

    signed = evidence.inputs_sha256(bundle.root, bundle.task, ("description",))
    assert signed["oracle"] == _sha256(expected)

    shutil.rmtree(oracle)
    oracle.mkdir()
    empty = evidence.inputs_sha256(bundle.root, bundle.task, ("description",))
    assert empty["oracle"] == _sha256(b"")


@pytest.mark.parametrize("name", list(MUTATIONS))
def test_editing_one_input_moves_exactly_its_label(bundle, name):
    label, mutate = MUTATIONS[name]
    _make_tdd(bundle)
    shapes = ("description", "tdd")
    before = evidence.seal_inputs(bundle.root, bundle.task, shapes).inputs_sha256

    mutate(bundle)
    after = evidence.inputs_sha256(bundle.root, bundle.task, shapes)

    assert set(after) == set(before)
    assert {key for key in before if before[key] != after[key]} == {label}


@pytest.mark.parametrize(
    "relpath, label",
    [
        ("canonical.patch", "canonical_patch"),
        ("manifest.json", "manifest"),
        ("prompts/description.txt", "prompt:description"),
        ("prompts/tdd.txt", "prompt:tdd"),
    ],
)
def test_inputs_sha256_names_the_label_whose_file_is_missing(bundle, relpath, label):
    _make_tdd(bundle)
    evidence.seal_inputs(bundle.root, bundle.task, ("description", "tdd"))
    (bundle.task / relpath).unlink()

    with pytest.raises(evidence.EvidenceError) as caught:
        evidence.inputs_sha256(bundle.root, bundle.task, ("description", "tdd"))

    assert label in str(caught.value)


# -- recheck_inputs --------------------------------------------------------


def test_recheck_returns_the_vetted_seal_when_nothing_moved(bundle):
    seal = _seal_and_vet(bundle)
    vetted = _read_json(bundle.task / "vetting.json")["inputs_sha256"]

    result = evidence.recheck_inputs(bundle.root, bundle.task)

    assert result == vetted
    assert result == seal.inputs_sha256


@pytest.mark.parametrize("name", RECHECK_CASES)
def test_recheck_names_the_moved_label_and_sends_the_task_back_to_vet(bundle, name):
    label, mutate = MUTATIONS[name]
    _make_tdd(bundle)
    _seal_and_vet(bundle, ("description", "tdd"))

    mutate(bundle)

    with pytest.raises(evidence.EvidenceError) as caught:
        evidence.recheck_inputs(bundle.root, bundle.task)
    assert label in str(caught.value)
    assert "re-run vet" in str(caught.value)


def test_recheck_names_the_first_moved_label_in_sorted_order(bundle):
    _seal_and_vet(bundle)
    MUTATIONS["edit-spec"][1](bundle)
    MUTATIONS["edit-canonical-patch"][1](bundle)

    with pytest.raises(evidence.EvidenceError) as caught:
        evidence.recheck_inputs(bundle.root, bundle.task)

    assert "canonical_patch" in str(caught.value)
    assert "re-run vet" in str(caught.value)


@pytest.mark.parametrize(
    "side, label", [("vetting-only", "aaa-unknown"), ("disk-only", "canonical_patch")]
)
def test_recheck_reads_a_label_on_one_side_only_as_a_difference(bundle, side, label):
    _seal_and_vet(bundle)
    doc = _read_json(bundle.task / "vetting.json")
    if side == "vetting-only":
        doc["inputs_sha256"] = {label: "0" * 64, **doc["inputs_sha256"]}
    else:
        del doc["inputs_sha256"][label]
    _write_json(bundle.task / "vetting.json", doc)

    with pytest.raises(evidence.EvidenceError) as caught:
        evidence.recheck_inputs(bundle.root, bundle.task)

    assert label in str(caught.value)
    assert "re-run vet" in str(caught.value)


@pytest.mark.parametrize("state", ["absent", "garbage"])
def test_recheck_refuses_a_task_without_a_readable_vetting_json(bundle, state):
    evidence.seal_inputs(bundle.root, bundle.task, ("description",))
    if state == "garbage":
        (bundle.task / "vetting.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(evidence.EvidenceError) as caught:
        evidence.recheck_inputs(bundle.root, bundle.task)

    assert "vetting.json" in str(caught.value)


# -- verify ----------------------------------------------------------------


def test_verify_passes_a_complete_bundle_and_leaves_it_untouched(bundle, capsys):
    _make_tdd(bundle)
    seal = _seal_and_vet(bundle, ("description", "tdd"))
    _build_run(bundle, seal, ("1-cmd1-a1", "1-sonnet-a1"))
    before = _snapshot(bundle.root)

    assert _verify(bundle.root, capsys) == (0, [])
    assert _snapshot(bundle.root) == before


def test_verify_passes_a_vetted_only_bundle(bundle, capsys):
    _seal_and_vet(bundle)
    assert not (bundle.root / "runs").exists()

    assert _verify(bundle.root, capsys) == (0, [])


def test_verify_accepts_a_halted_run_as_complete_evidence(bundle, capsys):
    _build_run(bundle, _seal_and_vet(bundle), marker="halted")

    assert _verify(bundle.root, capsys) == (0, [])


def test_verify_rechecks_the_shapes_the_vetting_names_not_the_ones_the_spec_allows(
    bundle, capsys
):
    _write_json(bundle.task / "spec.json", _spec_doc(bundle.info, tdd=True))
    assert not (bundle.root / "dispatch-references.json").exists()
    seal = _seal_and_vet(bundle, ("description",))
    _build_run(bundle, seal)
    assert not (bundle.task / "prompts" / "tdd.txt").exists()

    # The spec could carry tdd, but nobody sealed it. A verifier that recomputes
    # the seal over what the spec allows instead of what vetting.json records
    # goes looking for a prompts/tdd.txt that never existed.
    assert _verify(bundle.root, capsys) == (0, [])


@pytest.mark.parametrize("state", ["no-such-directory", "no-tasks"])
def test_verify_reports_an_evidence_dir_without_tasks_as_missing(tmp_path, bare_ci, capsys, state):
    root = tmp_path / "evidence"
    if state == "no-tasks":
        root.mkdir()

    # Nothing to check is not the same as nothing wrong: a restore that lost
    # the tasks tree (or landed nowhere) is a finding, not a clean bundle.
    assert _verify(root, capsys) == (1, ["tasks: missing"])


def test_verify_reports_a_sealed_but_unvetted_task_as_missing_its_vetting(bundle, capsys):
    evidence.seal_inputs(bundle.root, bundle.task, ("description",))
    assert not (bundle.task / "vetting.json").exists()

    # A finding line, not an exception: verify keeps reporting.
    assert _verify(bundle.root, capsys) == (1, ["tasks/1-calc/vetting.json: missing"])


@pytest.mark.parametrize(
    "spoil",
    [
        lambda doc: {key: value for key, value in doc.items() if key != "baseline"},
        lambda doc: dict(doc, warmup="no"),
    ],
    ids=["missing-key", "off-domain-warmup"],
)
def test_verify_reports_a_vetting_record_the_record_contract_rejects_as_invalid(
    bundle, capsys, spoil
):
    _seal_and_vet(bundle)
    doc = spoil(_read_json(bundle.task / "vetting.json"))
    # The file still parses and still carries `shapes` and `inputs_sha256`;
    # only the record contract tells it from a vetting record, and the
    # off-domain case keeps every key, so a key-set comparison waves it through.
    with pytest.raises(records.RecordError):
        records.validate_record("vetting", doc)
    _write_json(bundle.task / "vetting.json", doc)

    rc, lines = _verify(bundle.root, capsys)

    assert rc == 1
    assert len(lines) == 1
    assert lines[0].startswith("tasks/1-calc/vetting.json: invalid")


def test_verify_reports_a_vetting_record_that_names_another_template(bundle, capsys):
    _seal_and_vet(bundle)
    doc = _read_json(bundle.task / "vetting.json")
    # A real commit, just not the sealed one: the check is record against
    # record (vetting's template_sha against pretask's head_sha), not a shape
    # test a placeholder sha would fail on its own.
    other = bundle.info["last"]
    assert other != _read_json(bundle.task / "pretask.json")["head_sha"]
    _write_json(bundle.task / "vetting.json", dict(doc, template_sha=other))

    assert _verify(bundle.root, capsys) == (
        1,
        ["tasks/1-calc/vetting.json: mismatch template_sha"],
    )


def test_verify_reports_a_lost_canonical_patch_once_instead_of_raising(bundle, capsys):
    _seal_and_vet(bundle)
    (bundle.task / "canonical.patch").unlink()

    # inputs_sha256 would raise here. verify reports the file and moves on,
    # and although both the file check and the seal recheck miss it, the
    # path lands once.
    rc, lines = _verify(bundle.root, capsys)

    assert rc == 1
    assert "tasks/1-calc/canonical.patch: missing" in lines
    assert lines.count("tasks/1-calc/canonical.patch: missing") == 1


def test_verify_catches_an_attempt_the_restore_lost(bundle, tmp_path, capsys):
    _completed_bundle(bundle, ("1-cmd1-a1", "1-cmd1-a2"))
    restored = tmp_path / "restored"
    shutil.copytree(bundle.root, restored)
    shutil.rmtree(restored / "runs" / "r1" / "1-cmd1-a2")

    rc, lines = _verify(restored, capsys)

    # complete.txt says two attempts ran and one is gone. A check that only
    # validates what is present would call this restore intact.
    assert rc == 1
    assert lines[0] == "runs/r1/1-cmd1-a2: missing"
    assert _verify(bundle.root, capsys) == (0, [])


def test_verify_reports_a_truncated_attempt_record_as_invalid(bundle, capsys):
    run = _completed_bundle(bundle)
    record = run / "1-cmd1-a1" / "attempt.json"
    whole = record.read_bytes()
    record.write_bytes(whole[: len(whole) // 2])

    rc, lines = _verify(bundle.root, capsys)

    assert rc == 1
    assert len(lines) == 1
    assert lines[0].startswith("runs/r1/1-cmd1-a1/attempt.json: invalid")


@pytest.mark.parametrize(
    "record",
    [{"task": 1}, attempt(task=1, engine="bogus"), attempt(task=1, outcome="MAYBE")],
    ids=["key-set", "off-domain-engine", "off-domain-outcome"],
)
def test_verify_reports_well_formed_json_that_is_not_an_attempt_record_as_invalid(
    bundle, capsys, record
):
    run = _completed_bundle(bundle)
    # Parses fine; only the record contract tells it from an attempt. The two
    # full-key records carry a value no attempt field may hold, so a key-set
    # comparison accepts them (and the bogus engine would then surface as a
    # directory mismatch, not the invalid record it is).
    with pytest.raises(records.RecordError):
        records.validate_record("attempt", record)
    _write_json(run / "1-cmd1-a1" / "attempt.json", record)

    rc, lines = _verify(bundle.root, capsys)

    assert rc == 1
    assert len(lines) == 1
    assert lines[0].startswith("runs/r1/1-cmd1-a1/attempt.json: invalid")


@pytest.mark.parametrize(
    "over, field",
    [
        ({"task": 2}, "task"),
        ({"engine": "sonnet"}, "engine"),
        ({"attempt": 2}, "attempt"),
        ({"engine": "sonnet", "attempt": 2}, "engine"),
    ],
    ids=["task", "engine", "attempt", "engine-before-attempt"],
)
def test_verify_reports_an_attempt_record_that_disagrees_with_its_directory(
    bundle, capsys, over, field
):
    run = _completed_bundle(bundle)
    record_path = run / "1-cmd1-a1" / "attempt.json"
    record = dict(_read_json(record_path), **over)
    # A valid record in the wrong directory: the finding is mismatch, never
    # invalid.
    assert records.validate_record("attempt", record) is None
    _write_json(record_path, record)

    assert _verify(bundle.root, capsys) == (
        1,
        [f"runs/r1/1-cmd1-a1/attempt.json: mismatch {field}"],
    )


def test_verify_reports_a_run_without_its_run_record_as_missing(bundle, capsys):
    run = _completed_bundle(bundle)
    (run / "run.json").unlink()

    assert _verify(bundle.root, capsys) == (1, ["runs/r1/run.json: missing"])


def test_verify_reports_a_run_record_that_is_not_a_run_record_as_invalid(bundle, capsys):
    run = _completed_bundle(bundle)
    _write_json(run / "run.json", {})

    rc, lines = _verify(bundle.root, capsys)

    assert rc == 1
    assert lines[0].startswith("runs/r1/run.json: invalid")


def test_verify_reports_a_run_without_its_sealed_inputs_as_missing(bundle, capsys):
    run = _completed_bundle(bundle)
    (run / "sealed-inputs.json").unlink()

    # Without it nothing ties the run to the seal it consumed; silence here
    # would let a run claim any inputs at all.
    assert _verify(bundle.root, capsys) == (1, ["runs/r1/sealed-inputs.json: missing"])


def test_verify_reports_a_sealed_inputs_entry_for_a_task_the_bundle_lacks(bundle, capsys):
    run = _completed_bundle(bundle)
    doc = _read_json(run / "sealed-inputs.json")
    _write_json(run / "sealed-inputs.json", {**doc, "9-ghost": {}})

    assert _verify(bundle.root, capsys) == (
        1,
        ["runs/r1/sealed-inputs.json: missing 9-ghost"],
    )


def test_verify_reports_a_mutated_spec_against_the_task_and_the_run(bundle, capsys):
    _completed_bundle(bundle)
    MUTATIONS["edit-spec"][1](bundle)

    assert _verify(bundle.root, capsys) == (
        1,
        [
            "tasks/1-calc/vetting.json: mismatch spec",
            "runs/r1/sealed-inputs.json: mismatch 1-calc spec",
        ],
    )


def test_verify_reports_a_template_that_drifted_from_its_manifest(bundle, capsys):
    _completed_bundle(bundle)
    (bundle.task / "template" / "calc.py").write_text(
        eval_harness_fixtures.FIXED_IMPL, encoding="utf-8"
    )

    assert _verify(bundle.root, capsys) == (1, ["tasks/1-calc/manifest.json: mismatch calc.py"])


def test_verify_reports_a_run_with_no_marker_as_interrupted_not_missing(bundle, capsys):
    run = _completed_bundle(bundle)
    (run / "complete.txt").unlink()
    # The attempt that was in flight when the run died: a directory, no record.
    (run / "1-cmd1-a2").mkdir()

    assert _verify(bundle.root, capsys) == (1, ["runs/r1: interrupted"])


def test_verify_reports_an_attempt_the_inventory_does_not_name_as_extra(bundle, capsys):
    run = _completed_bundle(bundle)
    _write_attempt(run, "1-cmd2-a1")

    assert _verify(bundle.root, capsys) == (1, ["runs/r1/1-cmd2-a1: extra"])


@pytest.mark.parametrize("marker", ["complete", "halted"])
def test_verify_rejects_a_marker_whose_count_disagrees_with_its_inventory(
    bundle, capsys, marker
):
    run = _build_run(bundle, _seal_and_vet(bundle), marker=marker)
    marker_file = run / f"{marker}.txt"
    text = marker_file.read_text(encoding="utf-8")
    assert text.startswith("attempts: 1\n")
    marker_file.write_text(text.replace("attempts: 1\n", "attempts: 99\n", 1), encoding="utf-8")

    rc, lines = _verify(bundle.root, capsys)

    assert rc == 1
    assert lines[0].startswith(f"runs/r1/{marker}.txt: invalid")


def test_verify_never_reads_a_clone_directory(bundle, capsys):
    run = _completed_bundle(bundle)
    clones = [run / "1-cmd1-a1" / name for name in ("clone", "baseline-clone", "gate-clone")]
    for clone in clones:
        (clone / ".git").mkdir(parents=True)
        (clone / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        # A record-shaped file that is not a record: read it and the bundle
        # looks broken.
        (clone / "attempt.json").write_text("{not json", encoding="utf-8")
    before = _snapshot(bundle.root)

    assert _verify(bundle.root, capsys) == (0, [])
    assert _snapshot(bundle.root) == before

    for clone in clones:
        shutil.rmtree(clone)
    assert _verify(bundle.root, capsys) == (0, [])

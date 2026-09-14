"""Tests for `eval_harness.evidence`: sealing the inputs a run consumes,
signing them and rechecking the seal. `verify` has its own module,
test_eval_evidence_verify.

The `vet` driver is a later task, so the `vetting.json` it would have written
is hand-built by the builders in eval_harness_evidence_helpers from the record
builders in test_eval_records.

The fixture repo's task is its second commit, so the spec names that commit as
both `first` and `last`: the sealed template is `first^`, the base commit that
holds the broken `calc.py`. The task commit also widens the oracle, so the
changed set carries one test path for `classify_paths` to file as oracle. One
test grows the task by a third commit, so `first` and `last` stop coinciding.
"""
import dataclasses
import os
import shutil

import pytest

from eval_harness import evidence, prompts, records, spec, trees

import eval_harness_fixtures

# `bare_ci`, `task_repo` and `bundle` are fixtures: pytest resolves them from
# this module's own namespace, so they have to be imported even though nothing
# here calls them.
from eval_harness_evidence_helpers import (
    DESCRIPTION_LABELS,
    MUTATIONS,
    QUOTED_LISTING,
    QUOTED_NAMES,
    RECHECK_CASES,
    REFERENCES,
    TDD_FIELDS,
    _files_under,
    _git_bytes,
    _literal,
    _make_tdd,
    _path_listings,
    _read_json,
    _record_git_argv,
    _seal_and_vet,
    _sha256,
    _snapshot,
    _spec_doc,
    _third_commit,
    _write_json,
    bare_ci,
    bundle,
    task_repo,
)
from eval_harness_fixture_helpers import _git


def _commit_quoted_names(info: dict) -> str:
    """Grow the fixture task by two commits over the quoted names: one that
    adds every file, one that edits them. Sealing the second alone puts each
    in the template (a real digest, not "absent") and in the changed set."""
    repo = info["repo"]
    for body in ("def before():\n    return 1\n", "def after():\n    return 2\n"):
        for name in QUOTED_NAMES:
            (repo / name).write_text(body, encoding="utf-8")
        _git(repo, "add", "--", *_literal(QUOTED_NAMES))
        _git(repo, *eval_harness_fixtures.IDENTITY, "commit", "-m", "task: touch quoted names")
    return _git(repo, "rev-parse", "HEAD")


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


@pytest.mark.skipif(os.name == "nt", reason="a TAB in a filename is not legal on Windows")
def test_seal_keeps_a_filename_git_would_quote_in_its_real_spelling(bundle, monkeypatch):
    info = bundle.info
    repo = info["repo"]
    task_commit = _commit_quoted_names(info)
    _write_json(
        bundle.task / "spec.json", dict(_spec_doc(info), first=task_commit, last=task_commit)
    )
    # The control: git's default path output does quote every one of the
    # names, so a sealer that reads that output as literal paths goes looking
    # for files called `"caf\303\251.py"`, `"tab\there.py"` and the like.
    listed = _git_bytes(repo, "diff", "--name-only", f"{task_commit}^", task_commit)
    assert listed == QUOTED_LISTING.encode("utf-8")
    recorded = _record_git_argv(monkeypatch)

    seal = evidence.seal_inputs(bundle.root, bundle.task, ("description",))

    # The path bytes, not the quoted text: the listing the seal asks git for
    # is NUL-delimited, the one form that carries a name as it is. Unquoting
    # the text by hand covers the escapes its author thought of and no more.
    listings = _path_listings(recorded)
    assert listings, "the seal never asked git for the changed paths"
    for argv in listings:
        assert "-z" in argv, argv
    # The names the repository holds: decoded from the path bytes, never the
    # octal escapes, the backslash escapes, or the surrounding quotes.
    assert seal.writable == QUOTED_NAMES
    assert seal.oracle == ()
    template = bundle.task / "template"
    pretask = _read_json(bundle.task / "pretask.json")
    assert set(pretask["writable"]) == set(QUOTED_NAMES)
    for name in QUOTED_NAMES:
        assert (template / name).is_file(), name
        assert pretask["writable"][name] == _sha256((template / name).read_bytes())
        assert pretask["writable"][name] == _sha256(b"def before():\n    return 1\n")
    patch = (bundle.task / "canonical.patch").read_bytes()
    # Every file's hunks, and nothing else: a path git cannot resolve diffs to
    # nothing, so a patch cut over the quoted spellings is empty.
    assert patch.startswith(b"diff --git ")
    assert patch.count(b"diff --git ") == len(QUOTED_NAMES)
    assert patch.count(b"\n-def before():") == len(QUOTED_NAMES)
    assert patch.count(b"\n+def after():") == len(QUOTED_NAMES)
    assert b"calc.py" not in patch


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
        "pretask": _sha256((task / "pretask.json").read_bytes()),
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
        # A lost pretask.json is an error like any other lost input, never a
        # label signed "absent" the way an optional file is.
        ("pretask.json", "pretask"),
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


def test_recheck_refuses_a_pretask_rewritten_after_vet(bundle):
    seal = _seal_and_vet(bundle)
    assert "pretask" in seal.inputs_sha256
    MUTATIONS["edit-pretask"][1](bundle)
    # Still a pretask record the contract accepts, with the head it was sealed
    # at: emptying the writable map is what changes every later overlay and
    # observation, and only the seal over the file's bytes can refuse it.
    rewritten = _read_json(bundle.task / "pretask.json")
    assert records.validate_record("pretask", rewritten) is None
    assert rewritten["writable"] == {}
    assert rewritten["head_sha"] == seal.template_sha

    with pytest.raises(evidence.EvidenceError) as caught:
        evidence.recheck_inputs(bundle.root, bundle.task)

    assert str(caught.value).startswith("pretask")
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
    "side, label",
    [
        ("vetting-only", "aaa-unknown"),
        ("disk-only", "canonical_patch"),
        # A vetting record from before the label existed is not grandfathered:
        # the disk signs pretask, the record does not, and that is a difference.
        ("disk-only", "pretask"),
    ],
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

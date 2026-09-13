"""Tests for `eval_harness.evidence.verify`: proving a restored bundle intact.

The `vet` and `run` drivers are a later task, so every record they would have
written (`vetting.json`, `runs/<r>/...`) is hand-built by the builders in
eval_harness_evidence_helpers from the record builders in test_eval_records.
"""
import shutil

import pytest

from eval_harness import evidence, records

import eval_harness_fixtures

# `bare_ci`, `task_repo` and `bundle` are fixtures: pytest resolves them from
# this module's own namespace, so they have to be imported even though nothing
# here calls them.
from eval_harness_evidence_helpers import (
    MUTATIONS,
    _build_run,
    _completed_bundle,
    _make_tdd,
    _read_json,
    _seal_and_vet,
    _snapshot,
    _spec_doc,
    _verify,
    _write_attempt,
    _write_json,
    bare_ci,
    bundle,
    task_repo,
)
from test_eval_records import attempt


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

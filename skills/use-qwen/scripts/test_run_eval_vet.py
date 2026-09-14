"""Vet and tdd-seal tests for eval_harness/attempt.py and the run_eval_harness CLI.

What a vet leaves behind and what a tdd attempt can rely on: an oracle that lives
in a directory the template lacks still dispatches, an oracle overlay that changes
nothing still commits, a re-vet drops its stale `ready` before any work, one
deadline covers the whole warmup list, and every check runs under the gate lock.
Every case that mutates the shared bundle works on a copy of the one vetted once
per module (P13).
"""
import contextlib
import hashlib
import shlex
import sys
from pathlib import Path

import pytest

import run_eval_harness
from eval_harness import attempt, evidence, records, runner, trees
from eval_harness_evidence_helpers import _read_json, _snapshot, _write_json
from eval_harness_fixtures import BROKEN_IMPL, FIXED_IMPL, IDENTITY, _git, build_fixture_repo

# The last three names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_run_helpers import (
    _copy,
    _engine,
    _marker,
    _new_bundle,
    _run_direct,
    _spy_engine_probes,
    scratch,
    shim,
    vetted,
)

# An oracle the task commit adds two directories deep, under a tree the base commit never
# had: both `tests` and `tests/unit` have to be derived from the oracle path's parents.
NESTED_ORACLE_PATH = "tests/unit/test_new.py"
NESTED_ORACLE = (
    "from calc import add\n\n\ndef test_add_returns_the_sum_of_its_arguments():\n"
    "    assert add(2, 3) == 5\n"
)
# Two segments of 1.2 s: 2.4 s as a list, which a 2 s bound cannot cover and a 5 s one can.
SLOW_WARMUP = ["sleep 1.2", "sleep 1.2"]
# The same two, then a short third: under 2 s the MIDDLE segment is the one that runs out,
# and the third never runs - a budget that only the last segment inherits would run all three.
MIDDLE_OVERRUN_WARMUP = [*SLOW_WARMUP, "sleep 0.1"]
# A short segment then a long one: 1.4 s as a list, which 2 s covers only when the second
# gets what the first left (about 1.8 s), not a fixed slice of the bound.
UNEVEN_WARMUP = ["sleep 0.1", "sleep 1.3"]
# Three equal segments: 2.1 s as a list, so under 2 s the third is the one that runs out,
# whether or not the clone before each segment counts against the budget.
TRIPLE_WARMUP = ["sleep 0.7", "sleep 0.7", "sleep 0.7"]
# Labels a stale marker may hold; the refusal has to name whichever it finds.
STALE_LABELS = ["own", "gate", "baseline"]
# The writable set of the lock-observed task: necessity runs once per path, so the lock is
# taken twice for it (`notes.md` never exists; it seals as `absent`).
LOCKED_WRITABLE = ["calc.py", "notes.md"]
# The checks a vet runs, in order; each holds the gate lock under its own label.
VET_CHECKS = ["warmup", "baseline", "canonical", "necessity", "necessity"]
# What a vetted task dir holds: the lock marker lives at the bundle root, never here.
VETTED_TASK_ENTRIES = [
    "canonical.patch", "manifest.json", "oracle", "pretask.json", "prompts", "ready",
    "spec.json", "template", "vetting.json",
]
# Spec kwargs under which the tdd overlay changes nothing on the default fixture: the
# root test listed as the oracle (rewritten byte-identical), or no oracle at all.
UNCHANGED_OVERLAYS = {"listed-identical": {"oracle": ["test_calc.py"]}, "empty": {}}
# The two ways to vet a bundle; both must drop or keep `ready` the same way.
ENTRY_POINTS = ["direct", "cli"]


# -- helpers ------------------------------------------------------------------


def _nested_oracle_repo(root: Path) -> dict:
    """A fixture repo whose base commit holds only `calc.py` (broken) and whose task commit
    fixes it and adds `tests/test_new.py`: no `tests/__init__.py`, no root test file.
    """
    _git(root, *IDENTITY, "init")
    (root / "calc.py").write_text(BROKEN_IMPL, encoding="utf-8")
    _git(root, "add", "calc.py")
    _git(root, *IDENTITY, "commit", "-m", "base: add() subtracts and nothing tests it")
    first = _git(root, "rev-parse", "HEAD")
    (root / "calc.py").write_text(FIXED_IMPL, encoding="utf-8")
    (root / NESTED_ORACLE_PATH).parent.mkdir(parents=True)
    (root / NESTED_ORACLE_PATH).write_text(NESTED_ORACLE, encoding="utf-8")
    _git(root, "add", "calc.py", NESTED_ORACLE_PATH)
    _git(root, *IDENTITY, "commit", "-m", "task: make add() sum its arguments, tested under tests/")
    last = _git(root, "rev-parse", "HEAD")
    return {"repo": root, "first": first, "last": last}


def _unchanged_oracle_repo(root: Path) -> dict:
    """The default fixture: the task commit changes only `calc.py`, so the root test file is
    byte-identical in the template and the task commit."""
    return build_fixture_repo(root, change_test=False)


def _marker_log_segment(log: Path, marker: Path) -> str:
    """A segment that appends the lock marker's content to `log`; fails when no marker exists."""
    script = 'import sys; open(sys.argv[1], "a").write(open(sys.argv[2]).read())'
    return " ".join(
        [shlex.quote(sys.executable), "-c", shlex.quote(script), shlex.quote(str(log)),
         shlex.quote(str(marker))]
    )


def _spy_gate_lock(monkeypatch) -> list:
    """Wrap the real `runner.gate_lock`; the list records `(run_dir, label)` per acquisition."""
    acquired = []
    real = runner.gate_lock

    @contextlib.contextmanager
    def record_then_lock(run_dir, label):
        acquired.append((Path(run_dir), label))
        with real(run_dir, label):
            yield

    monkeypatch.setattr(runner, "gate_lock", record_then_lock)
    return acquired


def _vet(root: Path, entry: str) -> int:
    """`attempt.vet` at the default bound, or the CLI's `vet` at its default."""
    if entry == "cli":
        return run_eval_harness.main(["vet", str(root)])
    return attempt.vet(root, 1800.0)


def _attempt_record(root: Path, run_id: str) -> dict:
    return _read_json(root / "runs" / run_id / "1-cmd1-a1" / "attempt.json")


# -- fixtures -----------------------------------------------------------------


@pytest.fixture(scope="module")
def nested(scratch):
    """The nested-oracle bundle, vetted once by `attempt.vet`; its rc is asserted per case."""
    bundle = _new_bundle(scratch, "nested", {"1-calc": {}}, build=_nested_oracle_repo)
    bundle.task = bundle.root / "tasks" / "1-calc"
    bundle.rc = attempt.vet(bundle.root, 1800.0)
    return bundle


# -- a tdd oracle in a directory the template lacks -----------------------------


def test_a_tdd_oracle_in_a_directory_the_template_lacks_dispatches_and_passes(
    tmp_path, nested, shim, monkeypatch
):
    assert nested.rc == 0
    assert (nested.task / "ready").exists()
    root = _copy(nested.root, tmp_path.resolve() / "bundle")
    _spy_engine_probes(monkeypatch, "nested")

    rc = _run_direct(root, "nested", [_engine(shim, "pass")], "tdd")

    where = root / "runs" / "nested" / "1-cmd1-a1"
    record = _read_json(where / "attempt.json")
    assert rc == 0
    assert _marker(root / "runs" / "nested" / "complete.txt")[1] == ["1-cmd1-a1"]
    records.validate_record("attempt", record)
    # `tests/` is expected now: derived from the sealed oracle, not read off the template
    assert record["prep"] == {"status": "ok", "differing_paths": []}
    assert record["outcome"] == "PASS"
    assert record["oracle_intact"] is True
    assert record["gates"]["gate"]["rc"] == 0
    assert _read_json(where / "sealed.json")["oracle"] == {
        NESTED_ORACLE_PATH: hashlib.sha256(NESTED_ORACLE.encode("utf-8")).hexdigest(),
    }


def test_an_unexpected_sibling_inside_the_new_oracle_directory_is_still_a_prep_mismatch(
    tmp_path, nested, shim, monkeypatch
):
    root = _copy(nested.root, tmp_path.resolve() / "bundle")
    real_overlay_oracle = trees.overlay_oracle

    def overlay_and_leave_siblings(evidence_dir, clone, oracle):
        real_overlay_oracle(evidence_dir, clone, oracle)
        (Path(clone) / "tests" / "extra.txt").write_text("unlisted\n", encoding="utf-8")
        (Path(clone) / "tests" / "stray").mkdir()
        # a top-level directory too: an expected set read off the live clone would take it
        (Path(clone) / "stray").mkdir()

    monkeypatch.setattr(trees, "overlay_oracle", overlay_and_leave_siblings)
    _spy_engine_probes(monkeypatch, "nested-extra")

    rc = _run_direct(root, "nested-extra", [_engine(shim, "pass")], "tdd")

    record = _attempt_record(root, "nested-extra")
    assert rc == 0
    records.validate_record("attempt", record)
    # the derived directory entries are accepted; the file and the two directories nobody
    # listed are not, and `tests` and `tests/unit` themselves stay off the list
    assert record["prep"] == {
        "status": "PREP_MISMATCH",
        "differing_paths": ["stray", "tests/extra.txt", "tests/stray"],
    }
    assert record["validity"].startswith("DISCARDED")
    assert record["engine_run"]["launch"] == "not-started"
    assert record["gates"]["gate"] is None


# -- an unchanged oracle overlay -----------------------------------------------


@pytest.mark.parametrize("case", list(UNCHANGED_OVERLAYS))
def test_an_unchanged_oracle_overlay_commits_empty_and_the_attempt_runs_to_a_record(
    scratch, shim, monkeypatch, capsys, case
):
    bundle = _new_bundle(
        scratch, f"unchanged-{case}", {"1-calc": UNCHANGED_OVERLAYS[case]},
        build=_unchanged_oracle_repo,
    )
    task = bundle.root / "tasks" / "1-calc"

    vet_rc = attempt.vet(bundle.root, 1800.0)

    assert vet_rc == 0, capsys.readouterr().err
    assert (task / "ready").exists()
    assert _read_json(task / "vetting.json")["shapes"] == ["description", "tdd"]
    _spy_engine_probes(monkeypatch, case)

    rc = _run_direct(bundle.root, case, [_engine(shim, "pass")], "tdd")

    run = bundle.root / "runs" / case
    record = _attempt_record(bundle.root, case)
    assert rc == 0
    assert _marker(run / "complete.txt")[1] == ["1-cmd1-a1"]
    assert not (run / "halted.txt").exists()
    records.validate_record("attempt", record)
    assert record["prep"]["status"] == "ok"
    assert record["outcome"] == "PASS"
    # the tdd gate rebuilds the overlay on a fresh template: the same empty commit, green
    assert record["gates"]["gate"]["rc"] == 0
    # the overlay commit still lands, empty: the sealed head is not the pretask head
    sealed = _read_json(run / "1-cmd1-a1" / "sealed.json")
    assert sealed["head_sha"] != _read_json(task / "pretask.json")["head_sha"]


# -- a stale `ready` on re-vet --------------------------------------------------


@pytest.mark.parametrize("entry", ENTRY_POINTS)
def test_a_re_vet_whose_seal_is_refused_leaves_no_ready_behind(tmp_path, vetted, capsys, entry):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    task = root / "tasks" / "1-calc"
    assert (task / "ready").exists()
    # a path the task commit does not hold: sealing is refused before any check runs
    spec = _read_json(task / "spec.json")
    _write_json(task / "spec.json", dict(spec, oracle=["missing_test.py"]))

    rc = _vet(root, entry)

    err = capsys.readouterr().err
    assert rc == 1
    assert "1-calc" in err and "missing_test.py" in err and "oracle" in err, err
    assert not (task / "ready").exists()


def test_a_re_vet_refused_for_any_reason_leaves_no_ready_behind(
    tmp_path, vetted, capsys, monkeypatch
):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    task = root / "tasks" / "1-calc"
    assert (task / "ready").exists()
    ready_when_sealing = []

    def refuse_to_seal(*_args, **_kwargs):
        ready_when_sealing.append((task / "ready").exists())
        raise evidence.EvidenceError("boom")

    # a refusal that names neither the oracle nor a path: the seal itself is what failed
    monkeypatch.setattr(evidence, "seal_inputs", refuse_to_seal)

    rc = attempt.vet(root, 1800.0)

    err = capsys.readouterr().err
    assert rc == 1
    assert "1-calc" in err and "boom" in err, err
    # gone on any seal refusal, not only on one whose text happens to mention the oracle,
    # and gone BEFORE the seal is attempted: a seal that dies mid-way leaves no marker either
    assert not (task / "ready").exists()
    assert ready_when_sealing == [False]


@pytest.mark.parametrize("entry", ENTRY_POINTS)
def test_the_existing_runs_refusal_comes_first_and_leaves_the_bundle_untouched(
    tmp_path, vetted, capsys, entry
):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    task = root / "tasks" / "1-calc"
    (root / "runs").mkdir()
    before = _snapshot(task)
    assert "ready" in before and "vetting.json" in before

    rc = _vet(root, entry)

    err = capsys.readouterr().err
    assert rc == 1
    assert "runs" in err, err
    # byte for byte: `ready` still there, `vetting.json` unchanged, nothing sealed anew
    assert _snapshot(task) == before


# -- one deadline over the warmup list ----------------------------------------


def test_one_deadline_covers_the_ordered_warmup_list(scratch, capsys):
    bundle = _new_bundle(scratch, "warm-budget", {"1-calc": {"warmup": MIDDLE_OVERRUN_WARMUP}})
    task = bundle.root / "tasks" / "1-calc"

    rc = attempt.vet(bundle.root, 2.0)

    err = capsys.readouterr().err
    record = _read_json(task / "vetting.json")
    assert rc == 1
    assert "1-calc" in err and "warmup" in err, err
    assert not (task / "ready").exists()
    records.validate_record("vetting", record)
    assert record["ready"] is False
    # the list stopped at the second segment: the third never ran
    assert len(record["warmup"]) == 2, record["warmup"]
    first, second = record["warmup"]
    assert (first["rc"], first["timed_out"]) == (0, False)
    # only what was left of the 2 s after the first segment, not a fresh 2 s
    assert (second["rc"], second["timed_out"]) == (None, True)
    assert second["wall_s"] < 1.5, second
    assert (record["baseline"], record["canonical"], record["necessity"]) == (None, None, {})


def test_the_same_warmup_list_passes_under_a_bound_that_covers_it(scratch, capsys, monkeypatch):
    bundle = _new_bundle(scratch, "warm-fits", {"1-calc": {"warmup": SLOW_WARMUP}})
    task = bundle.root / "tasks" / "1-calc"
    acquired = _spy_gate_lock(monkeypatch)

    rc = attempt.vet(bundle.root, 5.0)

    assert rc == 0, capsys.readouterr().err
    assert (task / "ready").exists()
    record = _read_json(task / "vetting.json")
    assert [result["rc"] for result in record["warmup"]] == [0, 0]
    assert all(result["wall_s"] >= 1.0 for result in record["warmup"]), record["warmup"]
    # the label follows the check being run, not a fixed position: two warmups, one path
    assert [label for _run_dir, label in acquired] == [
        "warmup", "warmup", "baseline", "canonical", "necessity",
    ]


def test_a_later_warmup_segment_gets_what_the_earlier_ones_left_of_the_bound(scratch, capsys):
    bundle = _new_bundle(scratch, "warm-uneven", {"1-calc": {"warmup": UNEVEN_WARMUP}})
    task = bundle.root / "tasks" / "1-calc"

    rc = attempt.vet(bundle.root, 2.0)

    assert rc == 0, capsys.readouterr().err
    assert (task / "ready").exists()
    record = _read_json(task / "vetting.json")
    # the ~1.8 s left after a 0.1 s segment covers 1.3 s; a fixed half of 2 s would not
    assert [(r["rc"], r["timed_out"]) for r in record["warmup"]] == [(0, False), (0, False)]


def test_the_warmup_budget_runs_down_across_every_earlier_segment(scratch, capsys):
    bundle = _new_bundle(scratch, "warm-triple", {"1-calc": {"warmup": TRIPLE_WARMUP}})
    task = bundle.root / "tasks" / "1-calc"

    rc = attempt.vet(bundle.root, 2.0)

    err = capsys.readouterr().err
    record = _read_json(task / "vetting.json")
    assert rc == 1
    assert "1-calc" in err and "warmup" in err, err
    assert len(record["warmup"]) == 3, record["warmup"]
    first, second, third = record["warmup"]
    assert (first["rc"], second["rc"]) == (0, 0)
    # what the first two left of the 2 s, not the bound minus the previous segment alone
    assert third["timed_out"] is True
    assert third["wall_s"] < 0.8, third
    assert record["baseline"] is None


# -- every check under the gate lock --------------------------------------------


def test_every_vet_check_holds_the_gate_lock_under_its_own_label_and_releases_it(
    scratch, capsys, monkeypatch
):
    root = scratch / "locked"
    log = scratch / "locked-labels.log"
    # the same segment warms up and leads the test command, so it runs at every check
    segment = _marker_log_segment(log, root / runner.GATE_MARKER)
    tasks = {"1-calc": {"warmup": [segment], "segments": (segment,), "writable": LOCKED_WRITABLE}}
    bundle = _new_bundle(scratch, "locked", tasks)
    assert bundle.root == root
    task = bundle.root / "tasks" / "1-calc"
    acquired = _spy_gate_lock(monkeypatch)

    rc = attempt.vet(bundle.root, 1800.0)

    assert rc == 0, capsys.readouterr().err
    # one line per check, in order: necessity ran once per writable path
    assert log.read_text(encoding="utf-8").splitlines() == VET_CHECKS
    # the real lock, taken at the bundle root once per check, in the same order
    assert acquired == [(root, label) for label in VET_CHECKS]
    assert set(_read_json(task / "vetting.json")["necessity"]) == set(LOCKED_WRITABLE)
    # released after each check: the marker is gone, and it never lived in the task dir
    assert not (root / runner.GATE_MARKER).exists()
    assert sorted(path.name for path in task.iterdir()) == VETTED_TASK_ENTRIES


@pytest.mark.parametrize("label", STALE_LABELS)
def test_a_stale_gate_marker_makes_vet_refuse_before_any_check(scratch, label):
    bundle = _new_bundle(scratch, f"stale-lock-{label}", {"1-calc": {}})
    task = bundle.root / "tasks" / "1-calc"
    (bundle.root / runner.GATE_MARKER).write_text(label + "\n", encoding="utf-8")

    with pytest.raises(runner.GateConcurrencyError) as raised:
        attempt.vet(bundle.root, 1800.0)

    # the refusal names whatever the marker holds, not one literal it happens to match
    assert label in str(raised.value), raised.value
    assert not (task / "ready").exists()
    assert not (task / "vetting.json").exists()

"""Tests for eval_harness/gates.py: the per-attempt baseline, the observation of
a candidate's work, and the gate/own/ablate scoring gates.

The run driver is a later task, so every attempt directory here is built by
hand: a fresh clone of the sealed template, the fake engine working in it, then
the functions under test called on it directly.
"""
import dataclasses
import shlex
import sys
import time
from pathlib import Path

import pytest

from eval_harness import gates, records, runner, trees

# `bare_ci`, `task_repo` and `bundle` are fixtures: pytest resolves them from
# this module's own namespace, so they have to be imported even though nothing
# here calls them.
from eval_harness_evidence_helpers import _make_tdd, _seal_and_vet, bundle, task_repo
from eval_harness_fixture_helpers import _git, _run_engine, bare_ci
from eval_harness_fixtures import BROKEN_IMPL, FIXED_IMPL, ORACLE, WIDENED_ORACLE
from test_eval_records import attempt, description_attempt, failing_tests

# One segment, the interpreter running this suite: no login profile has to
# resolve `python` for the gate's `bash -lc`.
TEST_CMD = (shlex.quote(sys.executable) + " -m pytest -q -p no:cacheprovider",)
NEEDED = {"result": failing_tests(), "holds": True}
NOT_NEEDED = {"result": None, "holds": False}
NECESSITY_HOLDS = {"calc.py": NEEDED}
STATUS = ("status", "--porcelain", "--untracked-files=all")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _output(site, label: str) -> str:
    return (site.attempt_dir / f"{label}.txt").read_bytes().decode("utf-8", "replace")


def _rc_file(site, label: str) -> str:
    return _text(site.attempt_dir / f"{label}.rc")


def _wrote_nothing(site, label: str) -> bool:
    """No tree, no output, no exit code: the on-disk form of a gate that never ran."""
    return not any(
        (site.attempt_dir / name).exists()
        for name in (f"{label}-clone", f"{label}.txt", f"{label}.rc")
    )


def _append_to(log: Path) -> str:
    """A segment that records where it ran, in a log outside every clone."""
    return f"pwd -P >> {shlex.quote(str(log))}"


def _resolved(path: Path) -> str:
    return str(path.resolve())


def _tree_outside_git(root: Path) -> dict:
    """Every path under `root` but `.git/`: a file's bytes, None for a directory."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
        if ".git" not in path.relative_to(root).parts
    }


def _reset_clone(site) -> None:
    """Put the dispatch clone back to its sealed head, after `observe` recorded it.

    From here on `diff.patch` is the only record of the candidate's work: a
    gate that copies the clone instead of replaying the patch rebuilds the bare
    template, and the assertions that follow see it.
    """
    clone = site.attempt_dir / "clone"
    _git(clone, "checkout", "--", ".")
    _git(clone, "clean", "-fdq")
    assert _git(clone, *STATUS) == ""


def _tamper_preimage(patch: Path) -> None:
    """Alter one removed line: still a `diff --git` patch, no longer one that applies."""
    lines = _text(patch).splitlines(keepends=True)
    removed = [
        i for i, line in enumerate(lines) if line.startswith("-") and not line.startswith("---")
    ]
    assert removed, "the patch removes no line to alter"
    lines[removed[0]] = lines[removed[0]].rstrip("\n") + " (never in the tree)\n"
    patch.write_text("".join(lines), encoding="utf-8")


def _sealed_task(bundle, shape: str):
    if shape == "tdd":
        _make_tdd(bundle)
        return _seal_and_vet(bundle, shapes=("description", "tdd"))
    return _seal_and_vet(bundle)


def _site(
    bundle, seal, shape, attempt_id="1-cmd1-a1", test_cmd=TEST_CMD, gate_bound_s=120.0, writable=None
):
    run_dir = bundle.root / "runs" / "r1"
    attempt_dir = run_dir / attempt_id
    attempt_dir.mkdir(parents=True)
    # Positional, in the contract's field order.
    return gates.GateSite(
        attempt_dir,
        run_dir,
        bundle.task,
        shape,
        seal.writable if writable is None else writable,
        seal.oracle,
        test_cmd,
        gate_bound_s,
    )


def _dispatch(site, mode: str) -> dict:
    """The dispatch clone as the run driver seals it, then the engine's work in it.

    Returns the parsed `sealed.json` the driver would have written: the head and
    the hashes measured on the clone before the engine ran.
    """
    clone = Path(trees.fresh_clone(site.task_dir / "template", site.attempt_dir / "clone"))
    if site.shape == "tdd":
        trees.overlay_oracle(site.task_dir, clone, site.oracle)
        trees.commit_all(clone, "tdd: the vetted oracle the candidate works against")
    sealed = {
        "head_sha": trees.head_sha(clone),
        "writable": trees.hash_paths(clone, site.writable),
        "oracle": trees.hash_paths(clone, site.oracle),
    }
    done = _run_engine(mode, clone, site.attempt_dir, site.attempt_dir / "beat.txt")
    assert done.returncode == 0, done.stderr
    return sealed


def _attempt(bundle, shape, mode, **site_overrides):
    seal = _sealed_task(bundle, shape)
    site = _site(bundle, seal, shape, **site_overrides)
    return site, _dispatch(site, mode)


def _observed(bundle, shape, mode, necessity=NECESSITY_HOLDS, **site_overrides):
    site, sealed = _attempt(bundle, shape, mode, **site_overrides)
    return site, gates.observe(site, sealed, necessity)


# -- observe ---------------------------------------------------------------


def test_observe_reports_a_noop_candidate_as_no_change_with_an_empty_patch(bundle):
    site, seen = _observed(bundle, "description", "noop")

    assert set(seen) == {"changed", "stray", "dropped", "oracle_intact"}
    assert seen["changed"] == []
    assert seen["stray"] == []
    # The one writable file is untouched and its necessity held: that is a drop.
    assert seen["dropped"] == ["calc.py"]
    assert seen["oracle_intact"] is None
    patch = site.attempt_dir / "diff.patch"
    # Present and empty, not absent: "no patch" and "nothing to patch" differ.
    assert patch.is_file()
    assert patch.stat().st_size == 0


@pytest.mark.parametrize("shape, oracle_intact", [("description", None), ("tdd", True)])
def test_observe_files_an_edit_outside_writable_and_oracle_as_stray(bundle, shape, oracle_intact):
    site, sealed = _attempt(bundle, shape, "stray")

    seen = gates.observe(site, sealed, NECESSITY_HOLDS)

    by_path = {record["path"]: record for record in seen["changed"]}
    assert set(by_path) == {"calc.py", "stray.txt"}
    assert by_path["calc.py"]["status"] == "M"
    assert by_path["stray.txt"]["status"] == "A"
    for record in seen["changed"]:
        assert set(record) == {"status", "path", "old_path"}
        assert record["old_path"] is None
    assert seen["stray"] == ["stray.txt"]
    assert seen["dropped"] == []
    # A stray is no oracle edit: in tdd the oracle still reads intact.
    assert seen["oracle_intact"] is oracle_intact
    # The patch on disk is the snapshot's patch, byte for byte.
    changed, diff_text = trees.snapshot(site.attempt_dir / "clone", sealed["head_sha"])
    assert seen["changed"] == changed
    assert (site.attempt_dir / "diff.patch").read_bytes() == diff_text.encode("utf-8")
    assert diff_text.startswith("diff --git ")


@pytest.mark.parametrize("mode, necessity, expected", [
    ("drop", NECESSITY_HOLDS, ["calc.py"]),
    ("drop", {"calc.py": NOT_NEEDED}, []),
    # A result on file and `holds` false: the flag decides, not the result.
    ("drop", {"calc.py": {"result": failing_tests(), "holds": False}}, []),
    ("drop", {}, []),
    ("pass", NECESSITY_HOLDS, []),
])
def test_observe_drops_a_skipped_writable_only_when_its_necessity_held(
    bundle, mode, necessity, expected
):
    _, seen = _observed(bundle, "description", mode, necessity)

    assert seen["dropped"] == expected
    # `drop` wrote notes.md and left calc.py alone: the drop is about what the
    # engine skipped, the stray about where it went instead.
    assert seen["stray"] == (["notes.md"] if mode == "drop" else [])


@pytest.mark.parametrize("mode, writable, necessity, stray, dropped", [
    # stray.txt made writable: the engine's extra file is an allowed edit, and
    # an edit is never a drop however much its necessity held.
    ("stray", ("calc.py", "stray.txt"), {"calc.py": NEEDED, "stray.txt": NEEDED}, [], []),
    # `drop` wrote notes.md, allowed here, and skipped calc.py, still needed.
    ("drop", ("calc.py", "notes.md"), {"calc.py": NEEDED, "notes.md": NEEDED}, [], ["calc.py"]),
    # Two skipped and needed: sorted, not in the site's order.
    ("noop", ("notes.md", "calc.py"), {"calc.py": NEEDED, "notes.md": NEEDED}, [],
     ["calc.py", "notes.md"]),
    ("noop", ("notes.md", "calc.py"), {"calc.py": NEEDED, "notes.md": NOT_NEEDED}, [], ["calc.py"]),
])
def test_observe_takes_the_writable_set_from_the_site(
    bundle, mode, writable, necessity, stray, dropped
):
    _, seen = _observed(bundle, "description", mode, necessity, writable=writable)

    assert seen["stray"] == stray
    assert seen["dropped"] == dropped


@pytest.mark.parametrize("shape, mode", [("description", "vacuous"), ("tdd", "mutate-test")])
def test_observe_never_files_an_oracle_edit_as_stray(bundle, shape, mode):
    _, seen = _observed(bundle, shape, mode)

    # The edit was seen, it just is not a stray: it reaches `changed`.
    assert [record["path"] for record in seen["changed"]] == ["test_calc.py"]
    assert seen["stray"] == []
    assert seen["dropped"] == ["calc.py"]


@pytest.mark.parametrize("shape, mode, expected", [
    ("tdd", "pass", True),
    ("tdd", "noop", True),
    ("tdd", "stray", True),
    ("tdd", "mutate-test", False),
    ("description", "mutate-test", None),
])
def test_observe_reports_oracle_intact_in_tdd_and_null_in_description(
    bundle, shape, mode, expected
):
    _, seen = _observed(bundle, shape, mode)

    assert seen["oracle_intact"] is expected


def test_observe_judges_the_oracle_against_the_sealed_hashes(bundle):
    site, sealed = _attempt(bundle, "tdd", "pass")
    # Well-formed and wrong: the template's oracle hashes, from before the overlay.
    stale = trees.hash_paths(site.task_dir / "template", site.oracle)
    assert stale != sealed["oracle"]

    assert gates.observe(site, sealed, NECESSITY_HOLDS)["oracle_intact"] is True
    assert gates.observe(site, dict(sealed, oracle=stale), NECESSITY_HOLDS)["oracle_intact"] is False


def test_observe_judges_every_oracle_path_the_site_names(bundle):
    site, sealed = _attempt(bundle, "tdd", "pass")
    clone = site.attempt_dir / "clone"
    # A second oracle path the sealed clone never held: the seal records its
    # absence (measured after a `pass`, which touches no oracle path).
    wide = ("test_calc.py", "test_extra.py")
    site = dataclasses.replace(site, oracle=wide)
    sealed = dict(sealed, oracle=trees.hash_paths(clone, wide))
    assert set(sealed["oracle"]) == set(wide)
    assert not (clone / "test_extra.py").exists()

    untouched = gates.observe(site, sealed, NECESSITY_HOLDS)
    (clone / "test_extra.py").write_text("def test_extra():\n    pass\n", encoding="utf-8")
    written = gates.observe(site, sealed, NECESSITY_HOLDS)

    assert untouched["oracle_intact"] is True
    assert written["oracle_intact"] is False
    # An oracle-listed path is never stray, and creating one is an oracle edit.
    assert untouched["stray"] == written["stray"] == []
    assert "test_extra.py" in [record["path"] for record in written["changed"]]
    assert untouched["dropped"] == written["dropped"] == []


def test_observe_measures_against_the_sealed_head_not_the_clone_s_current_one(bundle):
    site, sealed = _attempt(bundle, "description", "pass")
    clone = site.attempt_dir / "clone"
    # The candidate committed its own work: HEAD moved, the sealed sha did not.
    trees.commit_all(clone, "candidate: committed its fix")
    assert trees.head_sha(clone) != sealed["head_sha"]
    assert _git(clone, *STATUS) == ""

    seen = gates.observe(site, sealed, NECESSITY_HOLDS)

    assert seen["changed"] == [{"status": "M", "path": "calc.py", "old_path": None}]
    assert seen["dropped"] == []
    assert _text(site.attempt_dir / "diff.patch").startswith("diff --git a/calc.py")


def test_observe_leaves_the_clone_as_the_engine_left_it(bundle):
    site, sealed = _attempt(bundle, "description", "stray")
    clone = site.attempt_dir / "clone"
    before = _tree_outside_git(clone)
    status_before = _git(clone, *STATUS)
    # The engine's new file is untracked: the case a snapshot that stages
    # intent-to-add entries and forgets to unstage them would leave dirty.
    assert "?? stray.txt" in status_before

    gates.observe(site, sealed, NECESSITY_HOLDS)

    assert _tree_outside_git(clone) == before
    assert _git(clone, *STATUS) == status_before


# -- baseline --------------------------------------------------------------


def test_baseline_runs_the_vetted_oracle_in_each_attempt_s_own_clone(bundle):
    seal = _seal_and_vet(bundle)
    log = bundle.root / "where-baselines-ran.txt"
    test_cmd = (_append_to(log), *TEST_CMD)
    first = _site(bundle, seal, "description", "1-cmd1-a1", test_cmd=test_cmd)
    second = _site(bundle, seal, "description", "1-cmd1-a2", test_cmd=test_cmd)
    assert (first.run_dir, first.task_dir) == (second.run_dir, second.task_dir)

    results = [gates.run_baseline(site) for site in (first, second)]

    # Two attempts, two trees: one shared baseline tree would print one line twice.
    lines = _text(log).splitlines()
    assert lines == [_resolved(site.attempt_dir / "baseline-clone") for site in (first, second)]
    assert lines[0] != lines[1]
    for site, result in zip((first, second), results):
        baseline_clone = site.attempt_dir / "baseline-clone"
        assert _text(baseline_clone / "test_calc.py") == WIDENED_ORACLE
        assert _text(baseline_clone / "calc.py") == BROKEN_IMPL
        # The dispatch clone is no part of the baseline: it was never even made.
        assert not (site.attempt_dir / "clone").exists()
        assert result.rc not in (0, None)
        assert result.timed_out is False
        assert result.failure_kind == "test"
        assert result.first_failure is not None
        assert 0 < result.wall_s
        assert tuple(result.as_json()) == records.COMMAND_RESULT_KEYS
        assert records.validate_record("command_result", result.as_json()) is None
        assert records.is_valid_baseline(result.as_json()) is True
        assert _rc_file(site, "baseline") == "1\n"
        # The deciding segment's own output, not the passing `pwd` before it.
        assert "assert" in _output(site, "baseline")
        assert "test_calc.py" in _output(site, "baseline")
        assert not (site.run_dir / runner.GATE_MARKER).exists()


def test_label_files_hold_the_deciding_segment_s_combined_output_and_exit_code(bundle):
    seal = _seal_and_vet(bundle)
    site = _site(bundle, seal, "description", test_cmd=(
        "echo first-passed",
        "echo to-stdout; echo to-stderr >&2; exit 3",
        "echo never-reached",
    ))

    result = gates.run_baseline(site)

    assert result.rc == 3
    assert result.timed_out is False
    # Nothing printed names a test or a tool: the failure is classified as
    # unknown, pointing at the deciding segment's first line, and a baseline
    # that failed for no test reason proves nothing.
    assert result.failure_kind == "unknown"
    assert result.first_failure.strip() == "to-stdout"
    assert records.is_valid_baseline(result.as_json()) is False
    assert _rc_file(site, "baseline") == "3\n"
    output = _output(site, "baseline")
    assert "to-stdout" in output
    assert "to-stderr" in output
    assert "first-passed" not in output
    assert "never-reached" not in output


def test_a_tool_failure_is_classified_as_one_and_is_no_baseline(bundle):
    seal = _seal_and_vet(bundle)
    site = _site(
        bundle, seal, "description", test_cmd=("echo 'bash: nope: command not found'; exit 127",)
    )

    result = gates.run_baseline(site)

    assert result.rc == 127
    assert result.timed_out is False
    assert result.failure_kind == "tool"
    assert result.first_failure.strip() == "bash: nope: command not found"
    assert records.validate_record("command_result", result.as_json()) is None
    # A baseline that never reached the tests proves nothing about them.
    assert records.is_valid_baseline(result.as_json()) is False
    assert _rc_file(site, "baseline") == "127\n"
    assert "command not found" in _output(site, "baseline")


def test_a_segment_that_outlives_the_bound_reports_a_timeout(bundle):
    seal = _seal_and_vet(bundle)
    site = _site(bundle, seal, "description", test_cmd=("sleep 5",), gate_bound_s=0.5)

    started = time.monotonic()
    result = gates.run_baseline(site)
    elapsed = time.monotonic() - started

    assert result.timed_out is True
    assert result.rc is None
    # The bound fired: the call came back long before the five seconds ran out,
    # and the record says how long the segment was allowed to run, which is no
    # longer than the call itself took.
    assert elapsed < 3.0, elapsed
    assert 0.5 <= result.wall_s <= elapsed
    assert records.validate_record("command_result", result.as_json()) is None
    assert _rc_file(site, "baseline") == "timeout\n"
    assert (site.attempt_dir / "baseline.txt").is_file()
    assert not (site.run_dir / runner.GATE_MARKER).exists()


def test_the_bound_is_one_deadline_across_the_whole_segment_list(bundle):
    seal = _seal_and_vet(bundle)
    # Each segment fits the bound on its own; the list as a whole does not.
    site = _site(bundle, seal, "description", test_cmd=("sleep 0.4",) * 3, gate_bound_s=0.6)

    started = time.monotonic()
    result = gates.run_baseline(site)
    elapsed = time.monotonic() - started

    assert result.timed_out is True
    assert result.rc is None
    assert elapsed < 3.0, elapsed
    assert _rc_file(site, "baseline") == "timeout\n"
    assert not (site.run_dir / runner.GATE_MARKER).exists()


# -- gate ------------------------------------------------------------------


def test_gate_scores_against_the_vetted_oracle_not_the_candidate_s_rewrite(bundle):
    site, _ = _observed(bundle, "description", "mutate-test")
    clone = site.attempt_dir / "clone"
    assert _text(clone / "test_calc.py") not in (ORACLE, WIDENED_ORACLE)
    # Fix the impl in the clone AFTER observe recorded the patch: a gate built
    # off the clone would pass now; one replaying the record runs the broken impl.
    (clone / "calc.py").write_text(FIXED_IMPL, encoding="utf-8")

    result = gates.run_gate(site)

    gate_clone = site.attempt_dir / "gate-clone"
    assert _text(gate_clone / "test_calc.py") == WIDENED_ORACLE
    assert _text(gate_clone / "calc.py") == BROKEN_IMPL
    assert result.rc not in (0, None)
    assert result.timed_out is False
    assert result.failure_kind == "test"
    assert result.first_failure is not None
    assert 0 < result.wall_s
    assert _rc_file(site, "gate") == "1\n"
    assert "assert" in _output(site, "gate")
    assert not (site.run_dir / runner.GATE_MARKER).exists()


def test_gate_passes_a_candidate_that_fixed_the_impl(bundle):
    site, seen = _observed(bundle, "description", "pass")
    assert seen["changed"] == [{"status": "M", "path": "calc.py", "old_path": None}]
    # Only diff.patch remembers the fix now.
    _reset_clone(site)
    assert _text(site.attempt_dir / "clone" / "calc.py") == BROKEN_IMPL

    started = time.monotonic()
    result = gates.run_gate(site)
    elapsed = time.monotonic() - started

    gate_clone = site.attempt_dir / "gate-clone"
    assert _text(gate_clone / "calc.py") == FIXED_IMPL
    assert _text(gate_clone / "test_calc.py") == WIDENED_ORACLE
    assert result.rc == 0
    assert result.timed_out is False
    # A measured duration: the test run's own, within the call that made it.
    assert 0 < result.wall_s <= elapsed
    assert _rc_file(site, "gate") == "0\n"
    assert "passed" in _output(site, "gate")


@pytest.mark.parametrize("entry", ["run_gate", "run_gates"])
def test_gate_in_tdd_scores_a_candidate_that_edited_the_oracle(bundle, entry):
    site, seen = _observed(bundle, "tdd", "mutate-test")
    assert seen["oracle_intact"] is False
    # In tdd the candidate's test hunk is against the committed vetted oracle,
    # not the bare template: a gate that patched the template would refuse
    # it as unappliable instead of scoring the candidate.

    result = getattr(gates, entry)(site)

    record = result["gate"] if entry == "run_gates" else result.as_json()
    gate_clone = site.attempt_dir / "gate-clone"
    assert _text(gate_clone / "test_calc.py") == WIDENED_ORACLE
    assert _text(gate_clone / "calc.py") == BROKEN_IMPL
    assert record["rc"] not in (0, None)
    assert record["timed_out"] is False
    assert record["failure_kind"] == "test"
    assert _rc_file(site, "gate") == "1\n"
    assert "assert" in _output(site, "gate")
    assert not (site.run_dir / runner.GATE_MARKER).exists()
    if entry == "run_gates":
        assert result["own"] is None
        assert result["ablate"] is None


def test_a_noop_candidate_still_runs_the_gate_and_fails_on_its_own_terms(bundle):
    site, _ = _observed(bundle, "description", "noop")
    assert (site.attempt_dir / "diff.patch").stat().st_size == 0

    gate = gates.run_gate(site)
    own = gates.run_own(site)

    gate_clone = site.attempt_dir / "gate-clone"
    assert _text(gate_clone / "calc.py") == BROKEN_IMPL
    assert _text(gate_clone / "test_calc.py") == WIDENED_ORACLE
    assert gate.rc not in (0, None)
    assert gate.failure_kind == "test"
    assert _rc_file(site, "gate") == "1\n"
    assert "assert" in _output(site, "gate")
    assert own.rc not in (0, None)
    assert own.timed_out is False
    assert own.failure_kind == "test"
    assert _rc_file(site, "own") == "1\n"
    assert "assert" in _output(site, "own")


@pytest.mark.parametrize("label, mode, path, template_text", [
    ("gate", "pass", "calc.py", BROKEN_IMPL),
    ("ablate", "vacuous", "test_calc.py", ORACLE),
], ids=["gate-pass", "ablate-vacuous"])
def test_an_emptied_patch_rebuilds_the_template_whatever_the_clone_holds(
    bundle, label, mode, path, template_text
):
    site, _ = _observed(bundle, "description", mode)
    clone_text = _text(site.attempt_dir / "clone" / path)
    assert clone_text != template_text
    # The clone still carries the candidate's edit; the record of it is gone.
    (site.attempt_dir / "diff.patch").write_bytes(b"")

    result = getattr(gates, f"run_{label}")(site)

    assert _text(site.attempt_dir / f"{label}-clone" / path) == template_text
    assert _text(site.attempt_dir / "clone" / path) == clone_text
    assert result.rc not in (0, None)
    assert result.timed_out is False
    assert result.failure_kind == "test"
    assert _rc_file(site, label) == "1\n"
    assert "assert" in _output(site, label)


@pytest.mark.parametrize("writable, stray", [
    (("calc.py",), ["stray.txt"]),
    # stray.txt made writable: no longer a stray, and the ablation, which
    # excludes the site's writable paths, no longer replays it either.
    (("calc.py", "stray.txt"), []),
], ids=["stray", "writable"])
def test_gate_carries_the_extra_file_and_ablate_only_while_it_is_not_writable(
    bundle, writable, stray
):
    site, seen = _observed(bundle, "description", "stray", writable=writable)
    assert seen["stray"] == stray
    stray_bytes = (site.attempt_dir / "clone" / "stray.txt").read_bytes()
    _reset_clone(site)
    assert not (site.attempt_dir / "clone" / "stray.txt").exists()

    gate = gates.run_gate(site)
    ablate = gates.run_ablate(site)

    # `gate` replays everything but the oracle paths: the fix and the extra file.
    gate_clone = site.attempt_dir / "gate-clone"
    assert (gate_clone / "stray.txt").read_bytes() == stray_bytes
    assert _text(gate_clone / "calc.py") == FIXED_IMPL
    assert _text(gate_clone / "test_calc.py") == WIDENED_ORACLE
    assert gate.rc == 0
    # `ablate` replays everything but the writable paths: the stray alone, or
    # nothing at all once the site names that file writable.
    ablate_clone = site.attempt_dir / "ablate-clone"
    if stray:
        assert (ablate_clone / "stray.txt").read_bytes() == stray_bytes
    else:
        assert not (ablate_clone / "stray.txt").exists()
    assert _text(ablate_clone / "calc.py") == BROKEN_IMPL
    assert _text(ablate_clone / "test_calc.py") == ORACLE
    assert ablate.rc not in (0, None)
    assert ablate.failure_kind == "test"


@pytest.mark.parametrize("label, mode", [("gate", "pass"), ("ablate", "vacuous")])
@pytest.mark.parametrize("spoil", ["garbage", "mismatch"])
def test_a_patch_git_refuses_raises_gate_error_and_releases_the_lock(bundle, label, mode, spoil):
    site, _ = _observed(bundle, "description", mode)
    patch = site.attempt_dir / "diff.patch"
    if spoil == "garbage":
        patch.write_text("this is not a patch\n", encoding="utf-8")
    else:
        # Well-formed, and aimed at the path this gate replays (calc.py for
        # `gate`, test_calc.py for `ablate`), but its preimage is not in the tree.
        _tamper_preimage(patch)
        assert _text(patch).startswith("diff --git ")
        assert "\n@@ " in _text(patch)

    with pytest.raises(gates.GateError) as caught:
        getattr(gates, f"run_{label}")(site)

    assert isinstance(caught.value, RuntimeError)
    # A refused patch is not a lock collision: a caller that retries on the
    # latter must not retry this forever.
    assert not isinstance(caught.value, runner.GateConcurrencyError)
    assert label in str(caught.value)
    assert not (site.attempt_dir / f"{label}.txt").exists()
    assert not (site.attempt_dir / f"{label}.rc").exists()
    assert not (site.run_dir / runner.GATE_MARKER).exists()


# -- own -------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["vacuous", "mutate-test"])
def test_own_runs_in_the_dispatch_clone_without_reconstruction(bundle, mode):
    site, _ = _observed(bundle, "description", mode)
    clone = site.attempt_dir / "clone"
    rewritten = _text(clone / "test_calc.py")
    assert rewritten not in (ORACLE, WIDENED_ORACLE)

    result = gates.run_own(site)

    # No tree of its own and nothing put back: the candidate's rewrite is what ran.
    assert not (site.attempt_dir / "own-clone").exists()
    assert _text(clone / "test_calc.py") == rewritten
    assert _text(clone / "calc.py") == BROKEN_IMPL
    assert result.rc == 0
    assert result.timed_out is False
    assert 0 < result.wall_s
    assert _rc_file(site, "own") == "0\n"
    assert "passed" in _output(site, "own")
    assert not (site.run_dir / runner.GATE_MARKER).exists()


# -- ablate ----------------------------------------------------------------


@pytest.mark.parametrize("mode", ["pass", "vacuous", "mutate-test"])
def test_ablate_replays_only_the_candidate_s_test_hunks_onto_the_broken_impl(bundle, mode):
    site, _ = _observed(bundle, "description", mode)
    candidate_test = _text(site.attempt_dir / "clone" / "test_calc.py")
    # Only diff.patch remembers the candidate's edits now.
    _reset_clone(site)

    result = gates.run_ablate(site)

    ablate_clone = site.attempt_dir / "ablate-clone"
    # The impl hunk never lands and no oracle is overlaid: what the candidate
    # did to the tests meets the pre-task implementation, and nothing else.
    assert _text(ablate_clone / "calc.py") == BROKEN_IMPL
    assert _text(ablate_clone / "test_calc.py") == candidate_test
    assert result.timed_out is False
    assert 0 < result.wall_s
    if mode == "pass":
        # The candidate left the tests alone, so the template's own oracle runs
        # against the broken impl: real tests, and they fail without the fix.
        assert candidate_test == ORACLE
        assert result.rc not in (0, None)
        assert result.failure_kind == "test"
        assert _rc_file(site, "ablate") == "1\n"
        assert "assert" in _output(site, "ablate")
    else:
        assert candidate_test != ORACLE
        assert result.rc == 0
        assert _rc_file(site, "ablate") == "0\n"
        assert "passed" in _output(site, "ablate")


# -- run_gates -------------------------------------------------------------


def test_run_gates_in_tdd_shape_runs_only_the_gate(bundle):
    log = bundle.root / "where-gates-ran.txt"
    site, seen = _observed(bundle, "tdd", "pass", test_cmd=(_append_to(log), *TEST_CMD))

    result = gates.run_gates(site)

    assert tuple(result) == records.GATE_KEYS
    assert result["own"] is None
    assert result["ablate"] is None
    assert result["gate"]["rc"] == 0
    assert result["gate"]["timed_out"] is False
    assert 0 < result["gate"]["wall_s"]
    assert records.validate_record("command_result", result["gate"]) is None
    assert records.validate_record("attempt", attempt(gates=result, **seen)) is None
    gate_clone = site.attempt_dir / "gate-clone"
    assert _text(gate_clone / "calc.py") == FIXED_IMPL
    assert _text(gate_clone / "test_calc.py") == WIDENED_ORACLE
    assert _rc_file(site, "gate") == "0\n"
    assert "passed" in _output(site, "gate")
    # One run, in the gate's tree; the gates the shape does not ask for left no trace.
    assert _text(log).splitlines() == [_resolved(gate_clone)]
    assert _wrote_nothing(site, "own")
    assert _wrote_nothing(site, "ablate")


def test_run_gates_in_description_shape_runs_gate_then_own_then_ablate(bundle):
    log = bundle.root / "where-gates-ran.txt"
    site, seen = _observed(bundle, "description", "pass", test_cmd=(_append_to(log), *TEST_CMD))

    result = gates.run_gates(site)

    assert tuple(result) == records.GATE_KEYS
    assert result["gate"]["rc"] == 0
    assert result["own"]["rc"] == 0
    assert result["ablate"]["rc"] not in (0, None)
    assert result["ablate"]["failure_kind"] == "test"
    assert result["ablate"]["first_failure"] is not None
    for label in records.GATE_KEYS:
        assert records.validate_record("command_result", result[label]) is None
        assert result[label]["timed_out"] is False
        assert 0 < result[label]["wall_s"]
        assert (site.attempt_dir / f"{label}.txt").is_file()
        assert (site.attempt_dir / f"{label}.rc").is_file()
    assert records.validate_record("attempt", description_attempt(gates=result, **seen)) is None
    # Each label's file holds that gate's verdict: two greens and one failure.
    assert "passed" in _output(site, "gate")
    assert "passed" in _output(site, "own")
    assert "assert" in _output(site, "ablate")
    assert _rc_file(site, "ablate") == "1\n"
    # One run per gate, in the contract's order, each in its own tree.
    assert _text(log).splitlines() == [
        _resolved(site.attempt_dir / "gate-clone"),
        _resolved(site.attempt_dir / "clone"),
        _resolved(site.attempt_dir / "ablate-clone"),
    ]


# -- gate concurrency ------------------------------------------------------


def test_marker_holds_only_the_running_gate_s_label(bundle):
    seal = _seal_and_vet(bundle)
    marker = bundle.root / "runs" / "r1" / runner.GATE_MARKER
    seen = bundle.root / "runs" / "r1" / "1-cmd1-a1" / "seen.txt"
    copy_marker = f"cp {shlex.quote(str(marker))} {shlex.quote(str(seen))}"
    site = _site(bundle, seal, "description", test_cmd=(copy_marker,))
    assert site.run_dir / runner.GATE_MARKER == marker
    gates.observe(site, _dispatch(site, "pass"), NECESSITY_HOLDS)

    for label in ("baseline", "gate", "own", "ablate"):
        result = getattr(gates, f"run_{label}")(site)

        # `cp` found the marker (or it would have exited non-zero) and the
        # marker named this gate and no other.
        assert result.rc == 0, label
        assert _text(seen).strip() == label
        assert not marker.exists()
        seen.unlink()


@pytest.mark.parametrize("label", ["baseline", "gate", "own", "ablate"])
def test_a_gate_started_under_another_gate_s_lock_raises_and_writes_nothing(bundle, label):
    site, _ = _observed(bundle, "description", "pass")
    marker = site.run_dir / runner.GATE_MARKER

    with runner.gate_lock(site.run_dir, "vet"):
        with pytest.raises(runner.GateConcurrencyError) as caught:
            getattr(gates, f"run_{label}")(site)
        # The outer lock is untouched: still there, still the vetter's.
        assert _text(marker).strip() == "vet"

    assert "vet" in str(caught.value)
    # And the other way round: a lock collision is no unappliable patch.
    assert not isinstance(caught.value, gates.GateError)
    assert _wrote_nothing(site, label)
    assert not marker.exists()

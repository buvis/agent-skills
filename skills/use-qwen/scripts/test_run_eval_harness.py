"""End-to-end tests for eval_harness/attempt.py and the run_eval_harness CLI.

Every round drives the real `run` driver with the fake engine (or a test-local
`cmd:` script) against a copy of a bundle that was sealed and vetted once per
module, so each run pays only for its own attempts and owns its run id (P13).
"""
import dataclasses
import hashlib
import time
from pathlib import Path

import pytest

import run_eval_harness
from eval_harness import attempt, evidence, records, runner, trees
from eval_harness_evidence_helpers import _read_json, _snapshot, _write_json
from eval_harness_fixture_helpers import _dirty, _stopped_growing
from eval_harness_fixtures import WIDENED_ORACLE

# The last seven names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_run_helpers import (
    AGREEABLE_TEST,
    CONFIG_KEYS,
    DESCRIPTION_SITES,
    NO_ENGINE,
    NO_GATES,
    NOT_LAUNCHED,
    OUTCOMES,
    PLAN_FIELDS,
    PYTEST_SEGMENT,
    REFUSALS,
    ROUNDS,
    STAMP,
    _agreeable_repo,
    _assert_attempt_artifacts_match,
    _assert_verify_reports_only_the_template_drift,
    _attempts,
    _copy,
    _cwds,
    _engine,
    _epoch,
    _gate,
    _ids,
    _logged_cwds,
    _marker,
    _new_bundle,
    _paths,
    _record,
    _run_argv,
    _run_direct,
    _spy_engine_probes,
    _stub_dispatch,
    drifted,
    pair,
    rounds,
    scratch,
    shim,
    slow,
    vetted,
)


@pytest.fixture(scope="module", autouse=True)
def module_started():
    """When this module's first test started, for the P13 budget assertion."""
    return time.monotonic()


# -- AttemptPlan -------------------------------------------------------------


def test_attempt_plan_is_frozen_and_carries_exactly_the_contract_fields():
    assert tuple(f.name for f in dataclasses.fields(attempt.AttemptPlan)) == PLAN_FIELDS

    plan = attempt.AttemptPlan(**dict.fromkeys(PLAN_FIELDS))

    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.attempt_no = 2


# -- vet ---------------------------------------------------------------------


def test_cli_vet_readies_the_task_and_records_its_gate_bound_and_shapes(vetted, slow):
    record = _read_json(vetted.task / "vetting.json")
    pretask = _read_json(vetted.task / "pretask.json")

    assert (vetted.task / "ready").exists()
    records.validate_record("vetting", record)
    assert record["ready"] is True
    assert record["gate_bound_s"] == 1800
    assert record["shapes"] == ["description", "tdd"]
    assert record["template_sha"] == pretask["head_sha"]
    assert record["warmup"] == []
    assert records.is_valid_baseline(record["baseline"])
    assert record["canonical"]["rc"] == 0 and record["canonical"]["timed_out"] is False
    assert record["canonical"]["wall_s"] > 0  # measured, not declared
    assert set(record["necessity"]) == {"calc.py"}
    assert record["necessity"]["calc.py"]["holds"] is True
    necessity = record["necessity"]["calc.py"]["result"]
    assert records.is_valid_baseline(necessity) and necessity["first_failure"] is not None
    assert necessity != record["baseline"]  # its own run, not the baseline's result copied
    expected = evidence.inputs_sha256(vetted.root, vetted.task, ("description", "tdd"))
    assert record["inputs_sha256"] == expected
    # the test command ran once per check (baseline, canonical, necessity for calc.py),
    # each in its own scratch clone outside the task dir, none of which survived vet
    cwds = _cwds(vetted.vet_lines)
    assert len(vetted.vet_lines) == 3 and len(set(cwds)) == 3
    for cwd in cwds:
        assert not cwd.startswith(str(vetted.task)) and not Path(cwd).exists(), cwd
    # P4: scratch clones are gone, no gate marker, nothing but seal + vetting + ready.
    assert sorted(p.name for p in vetted.task.iterdir()) == [
        "canonical.patch", "manifest.json", "oracle", "pretask.json", "prompts", "ready",
        "spec.json", "template", "vetting.json",
    ]
    assert not (vetted.root / "runs").exists()
    # and with `--gate-bound 2 --shapes description` given, vetting.json carries those instead
    given = _read_json(slow.task / "vetting.json")
    assert (slow.task / "ready").exists()
    assert (given["gate_bound_s"], given["shapes"], given["ready"]) == (2, ["description"], True)


def test_vet_fails_the_baseline_check_when_the_oracle_already_passes(scratch, capsys):
    bundle = _new_bundle(scratch, "green", {"1-calc": {"raw_test_cmd": ["true"]}})
    task = bundle.root / "tasks" / "1-calc"

    rc = attempt.vet(bundle.root, 1800.0)

    err = capsys.readouterr().err
    assert rc == 1
    assert "1-calc" in err and "baseline" in err
    assert not (task / "ready").exists()
    record = _read_json(task / "vetting.json")
    records.validate_record("vetting", record)
    assert record["ready"] is False
    assert record["baseline"]["rc"] == 0
    assert record["canonical"] is None


def test_vet_fails_the_canonical_check_when_the_patched_tree_does_not_pass(scratch, capsys):
    # the baseline stops at pytest's failure; canonical runs pytest green and then `false`
    bundle = _new_bundle(scratch, "red", {"1-calc": {"raw_test_cmd": [PYTEST_SEGMENT, "false"]}})
    task = bundle.root / "tasks" / "1-calc"

    rc = attempt.vet(bundle.root, 1800.0)

    err = capsys.readouterr().err
    assert rc == 1
    assert "1-calc" in err and "canonical" in err
    assert not (task / "ready").exists()
    record = _read_json(task / "vetting.json")
    records.validate_record("vetting", record)
    assert record["ready"] is False
    assert records.is_valid_baseline(record["baseline"])
    assert (record["canonical"]["rc"], record["canonical"]["timed_out"]) == (1, False)
    assert record["necessity"] == {}  # informational checks do not run after a failed gate


def test_vet_fails_the_warmup_check_and_runs_nothing_after_it(scratch, capsys):
    bundle = _new_bundle(scratch, "cold", {"1-calc": {"warmup": ["exit 3"]}})
    task = bundle.root / "tasks" / "1-calc"

    rc = attempt.vet(bundle.root, 1800.0)

    err = capsys.readouterr().err
    assert rc == 1
    assert "1-calc" in err and "warmup" in err
    assert not (task / "ready").exists()
    record = _read_json(task / "vetting.json")
    records.validate_record("vetting", record)
    assert record["ready"] is False
    assert [result["rc"] for result in record["warmup"]] == [3]
    assert (record["baseline"], record["canonical"], record["necessity"]) == (None, None, {})


def test_vet_runs_each_warmup_segment_once_on_a_scratch_clone(pair):
    plain = _read_json(pair.root / "tasks" / "10-calc" / "vetting.json")
    widened = _read_json(pair.root / "tasks" / "2-calc" / "vetting.json")

    (result,) = plain["warmup"]
    assert (result["rc"], result["timed_out"]) == (0, False)
    assert result["wall_s"] > 0
    assert widened["warmup"] == []
    (cwd,) = _cwds(pair.warmup_lines)
    assert not cwd.startswith(str(pair.root / "tasks" / "10-calc")), cwd
    assert not Path(cwd).exists(), cwd


def test_failed_revetting_removes_the_ready_marker(tmp_path, vetted):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    task = root / "tasks" / "1-calc"
    _write_json(task / "spec.json", dict(_read_json(task / "spec.json"), raw_test_cmd=["true"]))

    rc = attempt.vet(root, 1800.0)

    assert rc == 1
    assert not (task / "ready").exists()
    assert _read_json(task / "vetting.json")["ready"] is False


def test_vet_refuses_an_evidence_dir_that_already_holds_runs(tmp_path, vetted, capsys):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    (root / "runs").mkdir()

    rc = attempt.vet(root, 1800.0)

    assert rc != 0
    assert "runs" in capsys.readouterr().err


def test_vet_judges_the_template_by_the_sealed_oracle_not_by_its_own_tests(scratch):
    bundle = _new_bundle(scratch, "agree", {"1-calc": {}}, build=_agreeable_repo)
    task = bundle.root / "tasks" / "1-calc"

    rc = attempt.vet(bundle.root, 1800.0)

    record = _read_json(task / "vetting.json")
    # the template's own test is green on the broken impl; only the sealed oracle is red
    assert (task / "template" / "test_calc.py").read_text(encoding="utf-8") == AGREEABLE_TEST
    assert (task / "oracle" / "test_calc.py").read_text(encoding="utf-8") == WIDENED_ORACLE
    assert (rc, (task / "ready").exists(), record["ready"]) == (0, True, True)
    # a vet that skipped the overlay would see the template's green test (rc 0) and refuse;
    # the runner reports pytest's FAILURES banner as first_failure, so the line is checked
    # for its test marker, not for the oracle's test name
    assert records.is_valid_baseline(record["baseline"])
    assert runner.classify_failure(record["baseline"]["first_failure"]) == "test"
    assert (record["canonical"]["rc"], record["canonical"]["timed_out"]) == (0, False)
    assert record["necessity"]["calc.py"]["holds"] is True
    necessity = record["necessity"]["calc.py"]["result"]
    assert runner.classify_failure(necessity["first_failure"]) == "test"


# -- run: the CLI round (description, pass + noop) ---------------------------


def test_cli_run_drives_a_two_engine_round_to_complete_txt(rounds, vetted):
    round_ = rounds("r1")
    headers, ids = _marker(round_.run / "complete.txt")
    where = round_.run / "1-cmd1-a1"
    record = _record(round_, "1-cmd1-a1")
    sealed = _read_json(where / "sealed.json")

    assert round_.rc == 0
    assert set(headers) == {"attempts", "finished"}
    assert headers["attempts"] == "2"
    assert STAMP.match(headers["finished"])
    assert ids == ["1-cmd1-a1", "1-cmd2-a1"]
    assert ids == sorted(_attempts(round_))
    assert not (round_.run / "halted.txt").exists()
    vetting = _read_json(vetted.task / "vetting.json")
    assert _read_json(round_.run / "sealed-inputs.json") == {"1-calc": vetting["inputs_sha256"]}
    assert not (round_.run / runner.GATE_MARKER).exists()
    # the attempt's artifacts sit beside the clone, never inside it
    assert (record["task"], record["engine"], record["attempt"]) == (1, "cmd1", 1)
    assert record["shape"] == "description"
    assert record["clone"] == str(where / "clone")
    assert (where / "clone" / ".git").exists()
    prompt = vetted.task / "prompts" / "description.txt"
    assert (where / "prompt.txt").read_bytes() == prompt.read_bytes()
    assert "Using engine 'cmd:pass'" in (where / "wrapper.txt").read_text(encoding="utf-8")
    records.validate_record("sealed", sealed)
    # description leaves the template unchanged, so the sealed state is the pretask state
    pretask = _read_json(vetted.task / "pretask.json")
    assert sealed["head_sha"] == pretask["head_sha"]
    assert sealed["writable"] == pretask["writable"]
    # the own gate runs in clone/ exactly as the engine left it, so it clones nothing
    for label in ("baseline", "gate", "ablate"):
        assert (where / f"{label}-clone").is_dir(), label
    assert not (where / "own-clone").exists()
    assert (where / "baseline.rc").read_text(encoding="utf-8") == "1\n"
    assert (where / "gate.rc").read_text(encoding="utf-8") == "0\n"
    assert (where / "progress.log").read_text(encoding="utf-8").strip()


def test_run_json_records_the_resolved_config_engines_and_tasks(rounds, vetted, shim):
    round_ = rounds("r1")
    run = _read_json(round_.run / "run.json")
    commands = [_engine(shim, "pass"), _engine(shim, "noop")]
    prompt = vetted.task / "prompts" / "description.txt"

    records.validate_record("run", run)
    assert (run["schema_version"], run["run_id"]) == (1, "r1")
    assert STAMP.match(run["started"])
    config = run["config"]
    assert set(config) == CONFIG_KEYS
    assert config["engines"] == commands
    assert config["shape"] == "description"
    assert (config["bound"], config["gate_bound"]) == (30, 1800)
    assert config["alternate"] is False
    assert config["retry_discarded"] == "none"
    for key in ("qwen_provider", "qwen_model", "sonnet_model", "usage_limit_cmd"):
        assert config[key] is None, key
    assert run["engines"] == [
        {"id": "cmd1", "command": commands[0]}, {"id": "cmd2", "command": commands[1]},
    ]
    (task,) = run["tasks"]
    assert set(task) == {"id", "slug", "repo", "kind", "writable", "oracle", "prompt_sha256"}
    assert (task["id"], task["slug"]) == (1, "calc")
    assert task["repo"] == str(vetted.infos["1-calc"]["repo"])
    assert (task["writable"], task["oracle"]) == (["calc.py"], ["test_calc.py"])
    assert task["kind"] == "single-file"  # one sealed writable path
    assert task["prompt_sha256"] == hashlib.sha256(prompt.read_bytes()).hexdigest()
    # versions come from one `engines.record_versions` probe of the engines that run
    assert round_.probes.version_calls == [["cmd1", "cmd2"]]
    assert run["versions"] == round_.probes.versions
    assert set(run["server"]) == set(records.SERVER_KEYS)
    # no qwen among the engines: nothing fetched, only the declared label carried over
    assert round_.probes.server_calls == []
    assert run["server"]["declared_effort"] == config["server_reasoning_effort"]
    null_keys = [key for key in records.SERVER_KEYS if key != "declared_effort"]
    assert [run["server"][key] for key in null_keys] == [None] * 6


def test_pass_yields_pass_and_noop_yields_no_edit(rounds):
    round_ = rounds("r1")
    passed, noop = _record(round_, "1-cmd1-a1"), _record(round_, "1-cmd2-a1")

    assert (passed["outcome"], passed["class"], passed["validity"]) == ("PASS", None, "VALID")
    assert _paths(passed) == ["calc.py"]
    assert (passed["stray"], passed["dropped"], passed["oracle_intact"]) == ([], [], None)
    assert (passed["engine_run"]["launch"], passed["engine_run"]["exit"]) == ("started", 0)
    assert "pass" in passed["engine_run"]["identity"]
    assert passed["engine_run"]["usage_limit"] == "unchecked"  # no checker: never "clear"
    assert (_gate(passed, "gate")["rc"], _gate(passed, "own")["rc"]) == (0, 0)
    assert records.is_valid_baseline(_gate(passed, "ablate"))
    assert (noop["outcome"], noop["class"]) == ("FAIL", "no-edit")
    assert noop["changed"] == []
    assert (round_.run / "1-cmd2-a1" / "diff.patch").stat().st_size == 0
    status = round_.run / "1-cmd2-a1" / "status.txt"
    assert status.read_text(encoding="utf-8").splitlines() == ["FAIL:no-edit"]
    # no-edit is decided by the evidence, yet every required gate still ran on the untouched
    # clone, where the oracle, its own test and the ablation all fail as tests
    for label in ("gate", "own", "ablate"):
        assert records.is_valid_baseline(_gate(noop, label)), label


def test_each_gate_runs_in_its_own_tree_and_the_own_gate_in_the_dispatch_clone(rounds, vetted):
    round_ = rounds("r1")

    # P15's log: one line per site per attempt; the own gate's is the clone as the engine left it
    assert sorted(_logged_cwds(round_, vetted.log)) == sorted(
        str((round_.run / attempt_id / site).resolve())
        for attempt_id in _ids(round_) for site in DESCRIPTION_SITES
    )


# -- run: every completed round against the record contract -----------------


@pytest.mark.parametrize("run_id", list(ROUNDS))
def test_every_record_of_a_completed_round_matches_its_contract(rounds, run_id, capsys):
    round_ = rounds(run_id)
    attempts = _attempts(round_)

    assert round_.rc == 0
    assert sorted(_ids(round_)) == sorted(attempts)
    records.validate_record("run", _read_json(round_.run / "run.json"))
    assert not (round_.run / runner.GATE_MARKER).exists()
    for attempt_id, record in attempts.items():
        # verdict re-derived by classify, stamps, status.txt, one .txt/.rc pair per command
        _assert_attempt_artifacts_match(round_.run / attempt_id, record)
        # without --usage-limit-cmd a launched engine's limit is unchecked, never "clear"
        if run_id != "limit" and record["engine_run"]["launch"] == "started":
            assert record["engine_run"]["usage_limit"] == "unchecked", attempt_id
    for task_dir in (round_.root / "tasks").iterdir():
        records.validate_record("pretask", _read_json(task_dir / "pretask.json"))
        records.validate_record("vetting", _read_json(task_dir / "vetting.json"))
    # verify is clean, except that the `drifted` bundle's templates still carry their drift
    # (a harness never mutates sealed inputs): the two manifest mismatches are all it reports
    _assert_verify_reports_only_the_template_drift(round_, run_id, capsys)


@pytest.mark.parametrize("run_id", list(ROUNDS))
def test_every_stamp_of_a_completed_round_is_a_live_clock_reading(rounds, run_id):
    round_ = rounds(run_id)
    attempts = _attempts(round_)
    headers, ids = _marker(round_.run / "complete.txt")
    # stamps carry whole seconds, so the clock read before the run is floored to match
    window = (int(round_.before), round_.after)

    started = _epoch(_read_json(round_.run / "run.json")["started"])
    finished = _epoch(headers["finished"])
    assert window[0] <= started <= window[1], (started, window)
    assert window[0] <= finished <= window[1], (finished, window)
    previous = window[0]
    for attempt_id in ids:  # execution order: each attempt starts after the last one ended
        record = attempts[attempt_id]
        began, ended = _epoch(record["started"]), _epoch(record["finished"])
        assert previous <= began <= ended <= window[1], (attempt_id, previous, began, ended)
        previous = ended


@pytest.mark.parametrize("run_id", list(ROUNDS))
def test_every_round_probes_versions_once_and_never_the_server_without_qwen(rounds, run_id):
    round_ = rounds(run_id)

    assert round_.probes.version_calls == [round_.engine_ids]
    assert _read_json(round_.run / "run.json")["versions"] == round_.probes.versions
    assert round_.probes.server_calls == []


# -- run: outcomes per mode --------------------------------------------------


def test_tdd_pass_keeps_the_oracle_overlay_out_of_the_candidate_changes(rounds, vetted):
    round_ = rounds("tdd")
    where = round_.run / "1-cmd1-a1"
    record = _record(round_, "1-cmd1-a1")
    sealed = _read_json(where / "sealed.json")
    oracle = vetted.task / "oracle" / "test_calc.py"

    assert (record["outcome"], record["oracle_intact"], record["shape"]) == ("PASS", True, "tdd")
    assert _paths(record) == ["calc.py"]
    assert (record["stray"], record["dropped"]) == ([], [])
    assert "test_calc.py" not in (where / "diff.patch").read_text(encoding="utf-8")
    # the overlay was committed before launch: a new sealed head, the oracle in the tree,
    # and the writable path hashed as the template still holds it
    assert sealed["head_sha"] != _read_json(vetted.task / "pretask.json")["head_sha"]
    assert sealed["oracle"] == {"test_calc.py": hashlib.sha256(oracle.read_bytes()).hexdigest()}
    template_impl = (vetted.task / "template" / "calc.py").read_bytes()
    assert sealed["writable"] == {"calc.py": hashlib.sha256(template_impl).hexdigest()}
    assert (where / "clone" / "test_calc.py").read_bytes() == oracle.read_bytes()
    assert (_gate(record, "own"), _gate(record, "ablate")) == (None, None)


def test_tdd_test_mutation_is_gated_on_the_recopied_oracle(rounds):
    record = _record(rounds("tdd"), "1-cmd2-a1")

    assert (record["outcome"], record["class"]) == ("FAIL", "test-mutation")
    assert record["oracle_intact"] is False
    assert _paths(record) == ["test_calc.py"]
    # the gate saw the vetted oracle again, so the broken impl failed it as a test failure
    assert records.is_valid_baseline(_gate(record, "gate"))


def test_stray_yields_stray_edit_naming_the_stray_path(rounds):
    record = _record(rounds("stray"), "1-cmd1-a1")

    assert (record["outcome"], record["class"]) == ("FAIL", "stray-edit")
    assert record["stray"] == ["stray.txt"]
    assert _paths(record) == ["calc.py", "stray.txt"]
    assert record["dropped"] == []
    # the stray decides the verdict, yet tdd's required gate still ran: the fixed impl is green
    assert (_gate(record, "gate")["rc"], _gate(record, "gate")["timed_out"]) == (0, False)
    assert (_gate(record, "own"), _gate(record, "ablate")) == (None, None)


def test_vacuous_tests_fire_only_once_the_impl_is_not_dropped(rounds):
    round_ = rounds("vacuous")
    fake, fixing = _record(round_, "1-cmd1-a1"), _record(round_, "1-cmd2-a1")

    # P12: the fake engine's `vacuous` leaves calc.py alone, so the drop fires first
    assert (fake["outcome"], fake["class"]) == ("FAIL", "dropped-a-file")
    assert (fake["dropped"], _paths(fake), fake["stray"]) == (["calc.py"], ["test_calc.py"], [])
    # the drop decides the verdict, yet every required gate still measured the fake's tree:
    # the re-copied oracle is red on the broken impl, its own vacuous test green there and
    # on the bare template, so `own` is its own run, not the gate's verdict copied
    assert records.is_valid_baseline(_gate(fake, "gate"))
    assert (_gate(fake, "own")["rc"], _gate(fake, "ablate")["rc"]) == (0, 0)
    # with the fix in place, the vacuous oracle passes on the bare template: ablate rc 0
    assert (fixing["outcome"], fixing["class"]) == ("FAIL", "vacuous-tests")
    assert _paths(fixing) == ["calc.py", "test_calc.py"]
    assert (fixing["dropped"], fixing["stray"]) == ([], [])
    assert (_gate(fixing, "gate")["rc"], _gate(fixing, "ablate")["rc"]) == (0, 0)
    assert fixing["engine_run"]["completion"] == "complete"


def test_run_consumes_tasks_in_numeric_prefix_order(rounds, pair):
    round_ = rounds("pair")
    run = _read_json(round_.run / "run.json")

    assert _ids(round_) == ["2-cmd1-a1", "2-cmd2-a1", "10-cmd1-a1", "10-cmd2-a1"]
    assert [task["id"] for task in run["tasks"]] == [2, 10]
    assert run["tasks"][0]["writable"] == ["calc.py", "notes.md"]
    assert [task["kind"] for task in run["tasks"]] == ["multi-file", "single-file"]
    assert _read_json(round_.run / "sealed-inputs.json") == {
        task_id: _read_json(pair.root / "tasks" / task_id / "vetting.json")["inputs_sha256"]
        for task_id in ("2-calc", "10-calc")
    }


def test_a_drop_is_judged_by_the_writable_set_and_vetted_necessity(rounds, pair):
    round_ = rounds("pair")
    widened, plain = _record(round_, "2-cmd1-a1"), _record(round_, "10-cmd1-a1")
    passed = _record(round_, "2-cmd2-a1")
    necessity = _read_json(pair.root / "tasks" / "2-calc" / "vetting.json")["necessity"]

    assert {path: entry["holds"] for path, entry in necessity.items()} == {
        "calc.py": True, "notes.md": False,
    }
    assert (widened["outcome"], widened["class"]) == ("FAIL", "dropped-a-file")
    assert widened["dropped"] == ["calc.py"]
    assert (_paths(widened), widened["stray"]) == (["notes.md"], [])
    # the default writable set does not name notes.md, so the same edit is a stray
    assert (plain["outcome"], plain["class"]) == ("FAIL", "stray-edit")
    assert plain["stray"] == ["notes.md"]
    # a writable path whose necessity does not hold is no drop when left alone
    assert (passed["outcome"], passed["dropped"]) == ("PASS", [])


def test_only_a_harness_discard_is_retried_once_on_a_fresh_clone(rounds):
    round_ = rounds("retry")
    first, second = _record(round_, "1-cmd1-a1"), _record(round_, "1-cmd1-a2")
    silent = _record(round_, "1-cmd2-a1")

    assert _ids(round_) == ["1-cmd1-a1", "1-cmd1-a2", "1-cmd2-a1"]
    for record in (first, second):
        assert (record["validity"], record["outcome"]) == ("DISCARDED:harness", "DISCARDED")
        assert record["engine_run"]["launch"] == "not-started"
    assert (first["attempt"], second["attempt"]) == (1, 2)
    assert second["clone"] == str(round_.run / "1-cmd1-a2" / "clone")
    # a2 got its own fresh clone: a1's is still in place, a2's stands clean on its own sealed
    # head (the tdd overlay commit made in that clone), with nothing left over from a1
    a1_clone, a2_clone = round_.run / "1-cmd1-a1" / "clone", round_.run / "1-cmd1-a2" / "clone"
    assert (a1_clone / ".git").exists() and (a2_clone / ".git").exists()
    sealed_a2 = _read_json(round_.run / "1-cmd1-a2" / "sealed.json")
    assert trees.head_sha(a2_clone) == sealed_a2["head_sha"]
    assert _dirty(a2_clone) == []
    assert _read_json(round_.run / "run.json")["config"]["retry_discarded"] == "harness-only"
    # a stub that started, edited and exited silently is final, even under harness-only
    assert (silent["validity"], silent["outcome"]) == ("DISCARDED:identity", "DISCARDED")
    assert (silent["engine_run"]["identity"], silent["engine_run"]["exit"]) == (None, 0)
    assert _paths(silent) == ["calc.py"]
    assert not (round_.run / "1-cmd2-a2").exists()


def test_every_attempt_runs_the_baseline_in_its_own_baseline_clone(rounds, vetted):
    round_ = rounds("retry")
    cwds = _logged_cwds(round_, vetted.log)

    assert sorted(c for c in cwds if c.endswith("baseline-clone")) == sorted(
        str((round_.run / attempt_id / "baseline-clone").resolve())
        for attempt_id in _ids(round_)
    )


def test_retry_discarded_none_never_retries_and_exit1_is_final_under_either_policy(rounds):
    round_ = rounds("noretry")
    harness, exit1 = _record(round_, "1-cmd1-a1"), _record(round_, "1-cmd2-a1")

    assert _ids(round_) == ["1-cmd1-a1", "1-cmd2-a1"]
    assert harness["validity"] == "DISCARDED:harness"
    assert (exit1["validity"], exit1["outcome"]) == ("DISCARDED:exit-1", "DISCARDED")
    assert (exit1["engine_run"]["launch"], exit1["engine_run"]["exit"]) == ("started", 1)
    assert _ids(rounds("exit1")) == ["1-cmd1-a1"]
    assert _record(rounds("exit1"), "1-cmd1-a1")["validity"] == "DISCARDED:exit-1"


def test_two_hanging_engines_share_one_bound_and_leave_no_survivors(rounds, scratch):
    round_ = rounds("hang")
    beat = scratch / "beat.txt"
    first, second = _record(round_, "1-cmd1-a1"), _record(round_, "1-cmd2-a1")
    walls = [record["engine_run"]["wall_s"] for record in (first, second)]

    assert round_.rc == 0
    assert _ids(round_) == ["1-cmd1-a1", "1-cmd2-a1"]
    assert _read_json(round_.run / "run.json")["config"]["bound"] == 2
    for record in (first, second):
        assert (record["outcome"], record["validity"]) == ("TIMEOUT", "DISCARDED:timeout")
        assert record["engine_run"]["timed_out"] is True
    assert all(1.5 <= wall <= 6 for wall in walls), walls
    assert abs(walls[0] - walls[1]) <= 2, walls
    assert beat.is_file(), "the heartbeat grandchild never started"
    assert beat.stat().st_size > 0
    assert _stopped_growing(beat)


def test_every_stamp_is_read_from_the_clock_at_its_own_step(rounds):
    round_ = rounds("hang")
    first, second = _record(round_, "1-cmd1-a1"), _record(round_, "1-cmd2-a1")
    run_started = _epoch(_read_json(round_.run / "run.json")["started"])

    # each attempt hangs for its 2 s bound, so no attempt can start and finish on one stamp
    for record in (first, second):
        assert _epoch(record["finished"]) - _epoch(record["started"]) >= 1, record["started"]
    assert _epoch(second["started"]) >= _epoch(first["finished"])
    assert _epoch(second["started"]) > _epoch(first["started"])
    assert _epoch(_marker(round_.run / "complete.txt")[0]["finished"]) - run_started >= 3


def test_a_drifted_template_records_prep_mismatch_and_dispatches_nothing(rounds):
    round_ = rounds("prep")
    attempts = _attempts(round_)

    assert round_.rc == 0
    assert _ids(round_) == ["2-cmd1-a1", "10-cmd1-a1"]
    for attempt_id, record in attempts.items():
        where = round_.run / attempt_id
        # the rewritten writable path and the file the manifest never listed are both named
        assert record["prep"] == {
            "status": "PREP_MISMATCH", "differing_paths": ["calc.py", "extra.txt"],
        }
        assert (record["validity"], record["outcome"]) == ("DISCARDED:prep", "DISCARDED")
        assert record["engine_run"] == NOT_LAUNCHED
        assert record["baseline"] is None
        assert record["gates"] == NO_GATES
        assert [record[k] for k in ("changed", "stray", "dropped", "oracle_intact")] == [None] * 4
        assert not (where / "wrapper.txt").exists()
        assert not (where / "baseline.rc").exists()


def test_alternate_reverses_the_engine_order_on_odd_tasks(rounds, shim):
    round_ = rounds("alt")
    run = _read_json(round_.run / "run.json")

    assert _ids(round_) == ["2-cmd1-a1", "2-cmd2-a1", "10-cmd2-a1", "10-cmd1-a1"]
    assert run["config"]["alternate"] is True
    assert run["engines"] == [
        {"id": "cmd1", "command": _engine(shim, "pass")},
        {"id": "cmd2", "command": _engine(shim, "noop")},
    ]
    # every attempt proved the drifted tree for itself, the second engine included
    assert {record["prep"]["status"] for record in _attempts(round_).values()} == {
        "PREP_MISMATCH"
    }
    assert len(_attempts(round_)) == 4


def test_baseline_and_gate_timeouts_are_suspect(rounds):
    slow_base, slow_gate = rounds("basetimeout"), rounds("gatetimeout")
    base_dir, gate_dir = slow_base.run / "1-cmd1-a1", slow_gate.run / "1-cmd1-a1"
    base, gate = _record(slow_base, "1-cmd1-a1"), _record(slow_gate, "1-cmd1-a1")

    # a baseline past its bound stops the attempt before any engine runs
    assert (base["outcome"], base["validity"]) == ("SUSPECT", "DISCARDED:baseline")
    assert base["baseline"]["timed_out"] is True
    assert (base_dir / "baseline.rc").read_text(encoding="utf-8") == "timeout\n"
    assert base["engine_run"] == NOT_LAUNCHED
    assert base["gates"] == NO_GATES
    assert not (base_dir / "wrapper.txt").exists()
    # a gate past its bound leaves a valid, dispatched attempt without a verdict
    assert (gate["outcome"], gate["validity"]) == ("SUSPECT", "VALID")
    assert records.is_valid_baseline(gate["baseline"])
    assert _gate(gate, "gate")["timed_out"] is True
    assert (gate_dir / "gate.rc").read_text(encoding="utf-8") == "timeout\n"
    assert _paths(gate) == ["calc.py"]


def test_a_usage_limit_checker_reporting_stuck_discards_the_attempt(rounds):
    round_ = rounds("limit")
    where = round_.run / "1-cmd1-a1"
    record = _record(round_, "1-cmd1-a1")
    engine_run = record["engine_run"]

    assert round_.rc == 0
    assert _ids(round_) == ["1-cmd1-a1"]
    assert _read_json(round_.run / "run.json")["config"]["usage_limit_cmd"] == str(round_.stub)
    # the checker was handed this attempt's capture, and its STUCK verdict (exit 0) stands
    argv = round_.stub_argv.read_text(encoding="utf-8").splitlines()
    assert argv[0] == "--log" and Path(argv[1]).resolve() == (where / "out.txt").resolve()
    assert len(argv) == 2
    assert (engine_run["launch"], engine_run["exit"]) == ("started", 0)
    assert "pass" in engine_run["identity"]
    assert engine_run["usage_limit"] == "hit"
    assert (record["validity"], record["outcome"]) == ("DISCARDED:usage-limit", "DISCARDED")
    assert record["class"] is None
    assert _paths(record) == ["calc.py"]  # the edit was observed all the same


def test_a_qwen_run_probes_the_server_for_the_given_provider_and_effort(
    tmp_path, vetted, monkeypatch
):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    run_dir = root / "runs" / "qwen"
    provider = "http://127.0.0.1:9/v1"
    probes = _spy_engine_probes(monkeypatch, "qwen")
    dispatches = _stub_dispatch(monkeypatch)  # nothing listens on port 9: launch nothing

    rc = run_eval_harness.main(_run_argv(
        root, "qwen", ["qwen"], "description", "--qwen-provider", provider, "--qwen-model", "m",
        "--server-reasoning-effort", "medium",
    ))

    run = _read_json(run_dir / "run.json")
    record = _read_json(run_dir / "1-qwen-a1" / "attempt.json")
    assert (rc, _marker(run_dir / "complete.txt")[1], len(dispatches)) == (0, ["1-qwen-a1"], 1)
    records.validate_record("run", run)
    # P6: with qwen among the engines the server block is the probe's answer for exactly
    # this provider and label; versions are still probed once, for the engine that ran
    assert probes.server_calls == [[provider, "medium"]]
    assert run["server"] == probes.server
    assert run["server"]["declared_effort"] == "medium"
    assert (probes.version_calls, run["versions"]) == ([["qwen"]], probes.versions)
    assert run["engines"] == [{"id": "qwen", "command": "qwen"}]
    config = run["config"]
    assert (config["engines"], config["shape"]) == (["qwen"], "description")
    assert (config["qwen_provider"], config["qwen_model"]) == (provider, "m")
    assert (config["server_reasoning_effort"], config["sonnet_model"]) == ("medium", None)
    records.validate_record("attempt", record)
    assert (record["engine"], record["engine_run"]["launch"]) == ("qwen", "started")
    assert record["engine_run"]["usage_limit"] == "unchecked"
    assert (record["outcome"], record["class"]) == ("FAIL", "no-edit")  # the stub edits nothing


# -- run: halts, interruptions and refusals ----------------------------------


def test_orphans_after_the_baseline_halt_the_run(tmp_path, vetted, shim, monkeypatch, capsys):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    run = root / "runs" / "halt"
    # P14: a tree that never empties, and a reap that gives up at once instead of waiting.
    monkeypatch.setattr(runner.ProcessTree, "survivors", lambda self: True)
    monkeypatch.setattr(runner, "reap", lambda tree, **kwargs: False)

    rc = _run_direct(root, "halt", [_engine(shim, "pass"), _engine(shim, "noop")], "description")

    where = run / "1-cmd1-a1"
    record = _read_json(where / "attempt.json")
    halt = (run / "progress.log").read_text(encoding="utf-8").splitlines()[-1].split()
    headers, ids = _marker(run / "halted.txt")
    assert rc == 2
    assert (halt[0], Path(halt[1]).name, halt[2]) == ("HALTED:orphans", "1-cmd1-a1", "baseline")
    assert headers == {
        "reason": "HALTED:orphans", "attempt": "1-cmd1-a1", "command": "baseline", "attempts": "1",
    }
    assert ids == ["1-cmd1-a1"]
    assert not (run / "complete.txt").exists()
    assert not (run / "1-cmd2-a1").exists()
    assert not (where / "wrapper.txt").exists()
    records.validate_record("attempt", record)
    assert record["outcome"] in OUTCOMES
    assert record["baseline"] is None  # the command that raised OrphanError is unobserved
    assert records.classify(record) == (record["outcome"], record["class"])
    assert evidence.verify(root) == 0, capsys.readouterr().out


def test_a_crashed_later_attempt_leaves_neither_marker(tmp_path, vetted, shim, monkeypatch, capsys):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    run = root / "runs" / "cut"
    real_run_attempt = attempt.run_attempt
    seen = []

    def crash_on_the_second(plan):
        seen.append(plan.attempt_dir)
        if len(seen) > 1:
            raise RuntimeError("simulated kill")
        return real_run_attempt(plan)

    monkeypatch.setattr(attempt, "run_attempt", crash_on_the_second)

    with pytest.raises(RuntimeError, match="simulated kill"):
        _run_direct(root, "cut", [_engine(shim, "pass"), _engine(shim, "noop")], "tdd")

    assert [Path(p).name for p in seen] == ["1-cmd1-a1", "1-cmd2-a1"]
    assert (run / "1-cmd1-a1" / "attempt.json").is_file()
    assert not (run / "complete.txt").exists() and not (run / "halted.txt").exists()
    assert attempt.verify(root) == 1
    assert "runs/cut: interrupted" in capsys.readouterr().out
    assert run_eval_harness.main(["verify", str(root)]) == 1


@pytest.mark.parametrize("case", list(REFUSALS))
def test_run_refuses_before_creating_the_run_dir(tmp_path, request, shim, capsys, case):
    bundle_name, prepare, overrides, words = REFUSALS[case]
    root = _copy(request.getfixturevalue(bundle_name).root, tmp_path.resolve() / "bundle")
    prepare(root)
    argv = dict({"engines": [_engine(shim, "pass")], "shape": "description"}, **overrides)

    rc = run_eval_harness.main(
        _run_argv(root, "r", argv.pop("engines"), argv.pop("shape"), **argv)
    )

    err = capsys.readouterr().err
    assert rc == 1
    assert err.strip(), "a refusal owes a diagnostic"
    assert all(word in err for word in words), err
    assert not (root / "runs" / "r").exists()


def test_run_refuses_an_existing_run_directory_and_leaves_it_untouched(tmp_path, rounds, shim):
    root = _copy(rounds("r1").root, tmp_path.resolve() / "bundle")
    before = _snapshot(root / "runs" / "r1")
    engine_cmds = [_engine(shim, "pass"), _engine(shim, "noop")]

    rc = run_eval_harness.main(_run_argv(root, "r1", engine_cmds, "description"))

    assert rc == 1
    assert _snapshot(root / "runs" / "r1") == before


@pytest.mark.parametrize("argv", [
    lambda root: _run_argv(root, "r", [NO_ENGINE], "description", bound="0"),
    lambda root: _run_argv(root, "r", [NO_ENGINE], "description", gate_bound="-1"),
    lambda root: ["vet", str(root), "--gate-bound", "0"],
], ids=["run-bound", "run-gate-bound", "vet-gate-bound"])
def test_parser_refuses_a_non_positive_bound(tmp_path, vetted, argv):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")

    with pytest.raises(SystemExit) as stop:
        run_eval_harness.main(argv(root))

    assert stop.value.code == 2
    assert not (root / "runs").exists()


# -- budget (P13): keep this the last test in the module ---------------------


def test_module_finished_inside_its_runtime_budget(module_started):
    assert time.monotonic() - module_started < 60

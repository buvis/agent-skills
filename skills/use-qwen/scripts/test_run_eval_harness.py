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

from eval_harness import attempt, evidence, records, runner
from eval_harness_evidence_helpers import _read_json, _write_json
from eval_harness_fixtures import WIDENED_ORACLE

# The last seven names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_run_helpers import (
    AGREEABLE_TEST,
    CONFIG_KEYS,
    DESCRIPTION_SITES,
    PLAN_FIELDS,
    PYTEST_SEGMENT,
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
    _expected_versions,
    _gate,
    _ids,
    _logged_cwds,
    _marker,
    _new_bundle,
    _paths,
    _record,
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
    # a no-overlay vet sees the template's green test and refuses; first_failure is the
    # runner's first marked line (pytest's FAILURES banner), never the oracle's test name
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
    assert run["versions"] == _expected_versions(round_.probes.versions, "description")
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
    versions = _read_json(round_.run / "run.json")["versions"]

    assert (round_.probes.version_calls, round_.probes.server_calls) == ([round_.engine_ids], [])
    assert versions == _expected_versions(round_.probes.versions, ROUNDS[run_id][2])


# -- budget (P13): keep this the last test in the module ---------------------


def test_module_finished_inside_its_runtime_budget(module_started):
    assert time.monotonic() - module_started < 60

"""End-to-end tests for eval_harness/attempt.py and the run_eval_harness CLI.

Every round drives the real `run` driver with the fake engine (or a test-local
`cmd:` script) against a copy of a bundle that was sealed and vetted once per
module, so each run pays only for its own attempts and owns its run id (P13).
"""
import dataclasses
import hashlib
import os
import time
from pathlib import Path

import pytest

import run_eval_harness
from eval_harness import attempt, evidence, records, runner
from eval_harness_evidence_helpers import _read_json, _snapshot, _write_json
from eval_harness_fixture_helpers import _stopped_growing

# The last seven names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_run_helpers import (
    CONFIG_KEYS,
    NO_ENGINE,
    NO_GATES,
    NOT_LAUNCHED,
    OUTCOMES,
    PLAN_FIELDS,
    REFUSALS,
    ROUNDS,
    STAMP,
    _attempts,
    _copy,
    _engine,
    _gate,
    _ids,
    _marker,
    _new_bundle,
    _paths,
    _record,
    _run_argv,
    _run_direct,
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
    assert set(record["necessity"]) == {"calc.py"}
    assert record["necessity"]["calc.py"]["holds"] is True
    expected = evidence.inputs_sha256(vetted.root, vetted.task, ("description", "tdd"))
    assert record["inputs_sha256"] == expected
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
    # description leaves the template unchanged, so the sealed head is the pretask head
    assert sealed["head_sha"] == _read_json(vetted.task / "pretask.json")["head_sha"]
    # the own gate runs in clone/ exactly as the engine left it, so it clones nothing
    for label in ("baseline", "gate", "ablate"):
        assert (where / f"{label}-clone").is_dir(), label
    assert not (where / "own-clone").exists()
    assert (where / "baseline.rc").read_text(encoding="utf-8") == "1\n"
    assert (where / "gate.rc").read_text(encoding="utf-8") == "0\n"
    assert (where / "progress.log").read_text(encoding="utf-8").strip()


def test_run_json_records_the_resolved_config_engines_and_tasks(rounds, vetted, shim):
    run = _read_json(rounds("r1").run / "run.json")
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
    assert task["prompt_sha256"] == hashlib.sha256(prompt.read_bytes()).hexdigest()
    assert run["versions"] == {"pi": None, "claude": None}
    assert set(run["server"]) == set(records.SERVER_KEYS)
    # no qwen among the engines: nothing fetched, only the declared label carried over
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
    assert (_gate(passed, "gate")["rc"], _gate(passed, "own")["rc"]) == (0, 0)
    assert records.is_valid_baseline(_gate(passed, "ablate"))
    assert (noop["outcome"], noop["class"]) == ("FAIL", "no-edit")
    assert noop["changed"] == []
    assert (round_.run / "1-cmd2-a1" / "diff.patch").stat().st_size == 0
    status = round_.run / "1-cmd2-a1" / "status.txt"
    assert status.read_text(encoding="utf-8").splitlines() == ["FAIL:no-edit"]


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
        where = round_.run / attempt_id
        records.validate_record("attempt", record)
        assert record["outcome"] in OUTCOMES
        # classify re-derives from the evidence, never from the stored verdict
        assert records.classify(record) == (record["outcome"], record["class"])
        assert record["clone"] == str(where / "clone")
        assert STAMP.match(record["started"]) and STAMP.match(record["finished"])
        expected_status = record["outcome"] if record["class"] is None else (
            f"{record['outcome']}:{record['class']}"
        )
        assert (where / "status.txt").read_text(encoding="utf-8").splitlines() == [expected_status]
        assert (where / "prompt.txt").is_file()
        if (where / "sealed.json").exists():
            records.validate_record("sealed", _read_json(where / "sealed.json"))
        for path in _paths(record) if record["changed"] is not None else []:
            assert path not in ("sealed.json", "prompt.txt") and not path.endswith(".rc"), path
        # every command that ran left its output and rc; one that did not left nothing
        for label, result in [("baseline", record["baseline"]), *record["gates"].items()]:
            if result is None:
                assert not (where / f"{label}.rc").exists(), label
                assert not (where / f"{label}.txt").exists(), label
                continue
            assert (where / f"{label}.txt").is_file(), label
            expected_rc = "timeout\n" if result["timed_out"] else f"{result['rc']}\n"
            assert (where / f"{label}.rc").read_text(encoding="utf-8") == expected_rc, label
    for task_dir in (round_.root / "tasks").iterdir():
        records.validate_record("pretask", _read_json(task_dir / "pretask.json"))
        records.validate_record("vetting", _read_json(task_dir / "vetting.json"))
    assert evidence.verify(round_.root) == 0, capsys.readouterr().out
    assert run_eval_harness.main(["verify", str(round_.root)]) == 0
    assert attempt.verify(round_.root) == 0


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
    # the overlay was committed before launch: a new sealed head, the oracle in the tree
    assert sealed["head_sha"] != _read_json(vetted.task / "pretask.json")["head_sha"]
    assert sealed["oracle"] == {"test_calc.py": hashlib.sha256(oracle.read_bytes()).hexdigest()}
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


def test_vacuous_tests_fire_only_once_the_impl_is_not_dropped(rounds):
    round_ = rounds("vacuous")
    fake, fixing = _record(round_, "1-cmd1-a1"), _record(round_, "1-cmd2-a1")

    # P12: the fake engine's `vacuous` leaves calc.py alone, so the drop fires first
    assert (fake["outcome"], fake["class"]) == ("FAIL", "dropped-a-file")
    assert (fake["dropped"], _paths(fake), fake["stray"]) == (["calc.py"], ["test_calc.py"], [])
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
    assert (round_.run / "1-cmd1-a2" / "clone" / ".git").exists()
    assert _read_json(round_.run / "run.json")["config"]["retry_discarded"] == "harness-only"
    # a stub that started, edited and exited silently is final, even under harness-only
    assert (silent["validity"], silent["outcome"]) == ("DISCARDED:identity", "DISCARDED")
    assert (silent["engine_run"]["identity"], silent["engine_run"]["exit"]) == (None, 0)
    assert _paths(silent) == ["calc.py"]
    assert not (round_.run / "1-cmd2-a2").exists()


def test_every_attempt_runs_the_baseline_in_its_own_baseline_clone(rounds, vetted):
    round_ = rounds("retry")
    prefix = str(round_.run.resolve()) + os.sep
    lines = [
        line for line in vetted.log.read_text(encoding="utf-8").splitlines()
        if line.startswith(prefix)
    ]
    cwds = [line.rsplit(" ", 1)[0] for line in lines]

    assert len(lines) == len(set(lines))
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


def test_a_drifted_template_records_prep_mismatch_and_dispatches_nothing(rounds):
    round_ = rounds("prep")
    attempts = _attempts(round_)

    assert round_.rc == 0
    assert _ids(round_) == ["2-cmd1-a1", "10-cmd1-a1"]
    for attempt_id, record in attempts.items():
        where = round_.run / attempt_id
        assert record["prep"] == {"status": "PREP_MISMATCH", "differing_paths": ["calc.py"]}
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

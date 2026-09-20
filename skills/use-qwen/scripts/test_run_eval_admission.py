"""Run admission tests for eval_harness/attempt.py and the run_eval_harness CLI.

What a run checks before its first attempt: the run id is one path component,
the engine roster is one or two distinct engines, the prompt every engine sees
is the one run-level copy and still is at dispatch, a provider name resolves to
its configured URL or records that it did not, and a tdd run's versions carry
the sealed references. Every case runs against a copy of the bundle vetted once
per module (P13).
"""
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import run_eval_harness
from eval_harness import attempt, engines, gates, records
from eval_harness_evidence_helpers import REFERENCES, _read_json, _write_json

# The last four names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_run_helpers import (
    LAUNCHED_UNEDITED,
    NOT_LAUNCHED,
    _copy,
    _engine,
    _expected_versions,
    _marker,
    _run_argv,
    _run_direct,
    _spy_engine_probes,
    _stub_dispatch,
    pair,
    scratch,
    shim,
    vetted,
)

# Stands in for an id that is absolute, whose value exists only once tmp_path does.
ABSOLUTE = "<absolute>"
# Ids that are not exactly one directory component, by what is wrong with them.
BAD_RUN_IDS = {
    "traversal": "../escaped",
    "absolute": ABSOLUTE,
    "nested": "a/b",
    "backslash": "a\\b",
    "empty": "",
    "dot": ".",
    "dotdot": "..",
    "trailing-slash": "r/",
    "nul": "a\0b",
}
# Rosters a run refuses: engine specs (fake-engine modes or real ids), extra argv, words
# the diagnostic names. Two `cmd:` engines are `cmd1` and `cmd2`: never a repeat.
BAD_ROSTERS = {
    "empty": ([], [], ()),
    "three": (["pass", "noop", "pass"], [], ("two",)),
    "qwen-twice": (["qwen", "qwen"], ["--qwen-provider", "p", "--qwen-model", "m"], ("qwen",)),
    "sonnet-twice": (["sonnet", "sonnet"], ["--sonnet-model", "m"], ("sonnet",)),
}


def _flip_last_byte(original: bytes) -> bytes:
    """`original` with one bit of its last byte flipped: other bytes, the same length."""
    return original[:-1] + bytes([original[-1] ^ 1])


# How the run-level prompt moves between the two attempts: the bytes it gets, and whether
# the sealed task prompt is rewritten with them too (only the recorded digest tells then).
PROMPT_MUTATIONS = {
    "appended": (lambda original: original + b"\nappended between attempts\n", False),
    "same-length": (_flip_last_byte, False),
    "sealed-too": (_flip_last_byte, True),
}


@pytest.fixture(autouse=True)
def no_real_agent_dir(tmp_path, monkeypatch):
    """No case here may read the developer's ~/.pi/agent/models.json."""
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path / "no-agent"))


@pytest.fixture(scope="module")
def completed(scratch, shim, vetted):
    """One completed round per shape, keyed by shape: a two-engine description round and a
    one-engine tdd round, each in its own bundle copy with the version and server probes spied.
    """
    plans = {"description": ["pass", "noop"], "tdd": ["pass"]}
    built = {}
    for shape, modes in plans.items():
        root = _copy(vetted.root, scratch / f"admission-{shape}")
        with pytest.MonkeyPatch.context() as patch:
            probes = _spy_engine_probes(patch, shape)
            rc = _run_direct(root, shape, [_engine(shim, mode) for mode in modes], shape)
        built[shape] = SimpleNamespace(root=root, run=root / "runs" / shape, rc=rc, probes=probes)
    return built


def _run_id(case: str, tmp_path: Path) -> str:
    return str(tmp_path / "abs-run") if BAD_RUN_IDS[case] == ABSOLUTE else BAD_RUN_IDS[case]


def _escape_targets(root: Path, tmp_path: Path) -> list:
    """Where a traversal or absolute id would land: none of these may come to exist."""
    return [root / "escaped", root.parent / "escaped", tmp_path / "abs-run"]


def _roster(shim: Path, specs: list) -> list:
    return [spec if spec in ("qwen", "sonnet") else _engine(shim, spec) for spec in specs]


# -- the run-level prompt file and the pre-dispatch check -------------------


def test_a_run_writes_one_prompt_per_task_and_every_attempt_dispatches_a_copy_of_it(
    completed, vetted
):
    round_ = completed["description"]
    sealed = (vetted.task / "prompts" / "description.txt").read_bytes()
    run_prompt = round_.run / "1-calc.prompt.txt"
    run = _read_json(round_.run / "run.json")

    assert round_.rc == 0
    # copied from the sealed prompt, never re-rendered
    assert run_prompt.read_bytes() == sealed
    for attempt_id in ("1-cmd1-a1", "1-cmd2-a1"):
        assert (round_.run / attempt_id / "prompt.txt").read_bytes() == sealed, attempt_id
    assert run["tasks"][0]["prompt_sha256"] == hashlib.sha256(run_prompt.read_bytes()).hexdigest()


@pytest.mark.parametrize("case", list(PROMPT_MUTATIONS))
def test_a_run_level_prompt_mutated_between_attempts_halts_before_the_next_dispatch(
    tmp_path, vetted, shim, monkeypatch, case
):
    mutate, sealed_too = PROMPT_MUTATIONS[case]
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    run = root / "runs" / "mutated"
    task_prompt = root / "tasks" / "1-calc" / "prompts" / "description.txt"
    sealed = (vetted.task / "prompts" / "description.txt").read_bytes()
    mutated = mutate(sealed)
    dispatches = []

    def dispatch_and_mutate_the_prompt_once(*args, **kwargs):
        dispatches.append((args, kwargs))
        if len(dispatches) == 1:  # between the first engine's dispatch and the second's
            for target in (run / "1-calc.prompt.txt", *([task_prompt] if sealed_too else [])):
                target.write_bytes(mutated)
        return dict(LAUNCHED_UNEDITED, usage=dict(LAUNCHED_UNEDITED["usage"]))

    monkeypatch.setattr(engines, "dispatch", dispatch_and_mutate_the_prompt_once)

    rc = _run_direct(root, "mutated", [_engine(shim, "pass"), _engine(shim, "noop")], "description")

    where = run / "1-cmd2-a1"
    record = _read_json(where / "attempt.json")
    headers, ids = _marker(run / "halted.txt")
    halt = (run / "progress.log").read_text(encoding="utf-8").splitlines()[-1]
    assert rc == 2
    assert len(dispatches) == 1  # the second engine was never dispatched
    assert headers == {
        "reason": "HALTED:prompt", "attempt": "1-cmd2-a1", "command": "engine", "attempts": "2",
    }
    assert ids == ["1-cmd1-a1", "1-cmd2-a1"]
    assert not (run / "complete.txt").exists()
    assert halt.startswith("HALTED:prompt") and "1-cmd2-a1" in halt, halt
    records.validate_record("attempt", record)
    assert record["engine_run"] == NOT_LAUNCHED
    assert record["validity"] == "DISCARDED:harness"
    # the first engine saw the sealed bytes; the second's copy is the mutated file, refused
    assert (run / "1-cmd1-a1" / "prompt.txt").read_bytes() == sealed
    assert (where / "prompt.txt").read_bytes() == mutated


def test_a_sealed_task_prompt_rewritten_after_the_run_started_does_not_stop_the_next_attempt(
    tmp_path, vetted, shim, monkeypatch
):
    # Attempts copy the run-level file, so the sealed task prompt moving under a running
    # round changes nothing the engines see; `verify` is what reports that drift, later.
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    run = root / "runs" / "sealed-moved"
    task_prompt = root / "tasks" / "1-calc" / "prompts" / "description.txt"
    sealed = (vetted.task / "prompts" / "description.txt").read_bytes()
    dispatches = []

    def dispatch_and_rewrite_the_sealed_prompt_once(*args, **kwargs):
        dispatches.append((args, kwargs))
        if len(dispatches) == 1:
            task_prompt.write_bytes(_flip_last_byte(sealed))
        return dict(LAUNCHED_UNEDITED, usage=dict(LAUNCHED_UNEDITED["usage"]))

    monkeypatch.setattr(engines, "dispatch", dispatch_and_rewrite_the_sealed_prompt_once)

    rc = _run_direct(
        root, "sealed-moved", [_engine(shim, "pass"), _engine(shim, "noop")], "description"
    )

    assert rc == 0
    assert len(dispatches) == 2
    assert _marker(run / "complete.txt")[1] == ["1-cmd1-a1", "1-cmd2-a1"]
    assert not (run / "halted.txt").exists()
    # both engines were given the run-level bytes, which never moved
    assert (run / "1-calc.prompt.txt").read_bytes() == sealed
    for attempt_id in ("1-cmd1-a1", "1-cmd2-a1"):
        assert (run / attempt_id / "prompt.txt").read_bytes() == sealed, attempt_id


def test_an_attempt_copy_that_moved_before_its_dispatch_halts_even_the_first_attempt(
    tmp_path, vetted, shim, monkeypatch
):
    # The copy is what is checked, right before dispatch: the run-level file is intact and
    # no earlier attempt exists, yet the bytes about to be dispatched are not the recorded ones.
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    run = root / "runs" / "first"
    sealed = (vetted.task / "prompts" / "description.txt").read_bytes()
    real_run_baseline = gates.run_baseline

    def run_baseline_and_mutate_the_copy(site, *args, **kwargs):
        (Path(site.attempt_dir) / "prompt.txt").write_bytes(_flip_last_byte(sealed))
        return real_run_baseline(site, *args, **kwargs)

    monkeypatch.setattr(gates, "run_baseline", run_baseline_and_mutate_the_copy)
    dispatches = _stub_dispatch(monkeypatch)

    rc = _run_direct(root, "first", [_engine(shim, "pass")], "description")

    where = run / "1-cmd1-a1"
    record = _read_json(where / "attempt.json")
    headers, ids = _marker(run / "halted.txt")
    assert rc == 2
    assert dispatches == []
    assert headers == {
        "reason": "HALTED:prompt", "attempt": "1-cmd1-a1", "command": "engine", "attempts": "1",
    }
    assert ids == ["1-cmd1-a1"]
    assert not (run / "complete.txt").exists()
    records.validate_record("attempt", record)
    assert record["engine_run"] == NOT_LAUNCHED
    assert record["validity"] == "DISCARDED:harness"
    assert (run / "1-calc.prompt.txt").read_bytes() == sealed
    assert (where / "prompt.txt").read_bytes() == _flip_last_byte(sealed)


def test_a_multi_task_run_writes_each_task_its_own_prompt_and_digest(
    tmp_path, pair, shim, monkeypatch
):
    # Two tasks whose sealed prompts differ: each gets its own run-level file, each attempt
    # copies its own task's file, and run.json records one digest per task, not one shared.
    root = _copy(pair.root, tmp_path.resolve() / "bundle")
    run = root / "runs" / "two-tasks"
    sealed = {name: (root / "tasks" / name / "prompts" / "tdd.txt").read_bytes()
              for name in ("2-calc", "10-calc")}
    assert sealed["2-calc"] != sealed["10-calc"]
    _spy_engine_probes(monkeypatch, "two-tasks")
    _stub_dispatch(monkeypatch)

    rc = _run_direct(root, "two-tasks", [_engine(shim, "pass"), _engine(shim, "noop")], "tdd")

    tasks = {task["id"]: task for task in _read_json(run / "run.json")["tasks"]}
    assert rc == 0
    assert sorted(path.name for path in run.glob("*.prompt.txt")) == [
        "10-calc.prompt.txt", "2-calc.prompt.txt",
    ]
    for name, prompt in sealed.items():
        task_id = int(name.split("-", 1)[0])
        assert (run / f"{name}.prompt.txt").read_bytes() == prompt, name
        assert tasks[task_id]["prompt_sha256"] == hashlib.sha256(prompt).hexdigest(), name
        for engine_id in ("cmd1", "cmd2"):
            copied = (run / f"{task_id}-{engine_id}-a1" / "prompt.txt").read_bytes()
            assert copied == prompt, (name, engine_id)


# -- the run id ---------------------------------------------------------------


@pytest.mark.parametrize("case", list(BAD_RUN_IDS))
def test_run_refuses_a_run_id_that_is_not_one_path_component(tmp_path, vetted, shim, capsys, case):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    before = sorted(path.name for path in root.iterdir())

    rc = _run_direct(root, _run_id(case, tmp_path), [_engine(shim, "pass")], "description")

    err = capsys.readouterr().err
    assert rc == 1
    assert "run refused:" in err and "--run-id" in err, err
    assert not (root / "runs").exists()
    assert sorted(path.name for path in root.iterdir()) == before  # `..` names the bundle itself
    assert [target for target in _escape_targets(root, tmp_path) if target.exists()] == []


def test_run_refuses_a_traversal_id_whose_target_already_exists(tmp_path, vetted, shim, capsys):
    # A refusal, not a FileExistsError: the id is judged before anything is created.
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    targets = (root / "escaped", root.parent / "escaped")
    for target in targets:
        target.mkdir()

    rc = _run_direct(root, "../escaped", [_engine(shim, "pass")], "description")

    err = capsys.readouterr().err
    assert rc == 1
    assert "--run-id" in err and "already exists" not in err, err  # the id, not the target
    assert not (root / "runs").exists()
    assert [list(target.iterdir()) for target in targets] == [[], []]  # still empty, untouched


@pytest.mark.parametrize("case", list(BAD_RUN_IDS))
def test_parser_refuses_a_run_id_that_is_not_one_path_component(tmp_path, vetted, shim, case):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")

    with pytest.raises(SystemExit) as stop:
        run_eval_harness.main(
            _run_argv(root, _run_id(case, tmp_path), [_engine(shim, "pass")], "description")
        )

    assert stop.value.code == 2
    assert not (root / "runs").exists()
    assert [target for target in _escape_targets(root, tmp_path) if target.exists()] == []


@pytest.mark.parametrize("case", list(BAD_RUN_IDS))
def test_parser_refuses_a_render_run_id_that_is_not_one_path_component(tmp_path, vetted, case):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")

    with pytest.raises(SystemExit) as stop:
        run_eval_harness.main(["render", str(root), "--run-id", _run_id(case, tmp_path)])

    assert stop.value.code == 2
    assert not (root / "runs").exists()
    assert [target for target in _escape_targets(root, tmp_path) if target.exists()] == []


def test_run_accepts_a_run_id_with_dots_inside_one_component(tmp_path, vetted, shim, monkeypatch):
    # `..` is refused as a whole id, not as a substring: `v1..2` is one directory name.
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    _stub_dispatch(monkeypatch)

    rc = _run_direct(root, "v1..2", [_engine(shim, "pass")], "description")

    assert rc == 0
    assert _marker(root / "runs" / "v1..2" / "complete.txt")[1] == ["1-cmd1-a1"]


# -- the engine roster --------------------------------------------------------


def test_run_refuses_an_empty_roster_given_directly(tmp_path, vetted, capsys):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")

    rc = _run_direct(root, "empty", [], "description")

    err = capsys.readouterr().err
    assert rc == 1
    assert "run refused:" in err, err
    assert not (root / "runs").exists()


@pytest.mark.parametrize("case", list(BAD_ROSTERS))
def test_run_refuses_a_malformed_roster_before_creating_runs(
    tmp_path, vetted, shim, monkeypatch, capsys, case
):
    specs, extra, words = BAD_ROSTERS[case]
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    probes = _spy_engine_probes(monkeypatch, case)
    dispatches = _stub_dispatch(monkeypatch)

    rc = run_eval_harness.main(_run_argv(root, case, _roster(shim, specs), "description", *extra))

    err = capsys.readouterr().err
    assert rc == 1
    assert "run refused:" in err, err
    assert all(word in err for word in words), (words, err)
    assert not (root / "runs").exists()
    # refused before admission: no CLI or server probe ran, nothing was dispatched
    assert (probes.version_calls, probes.server_calls, dispatches) == ([], [], [])


def test_run_admits_the_same_cmd_engine_twice_as_cmd1_and_cmd2(tmp_path, vetted, shim, monkeypatch):
    # `cmd:` engines are named by position, so the identical string twice is not a repeat.
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    _stub_dispatch(monkeypatch)

    rc = _run_direct(root, "twice", [_engine(shim, "pass"), _engine(shim, "pass")], "description")

    assert rc == 0
    assert _marker(root / "runs" / "twice" / "complete.txt")[1] == ["1-cmd1-a1", "1-cmd2-a1"]


# -- the provider URL ---------------------------------------------------------


def test_an_unresolved_provider_name_is_recorded_as_a_diagnostic_and_never_probed(
    tmp_path, vetted, monkeypatch
):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    run_dir = root / "runs" / "unresolved"
    (tmp_path / "agent").mkdir()  # no models.json: the name maps to no URL
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path / "agent"))
    probes = _spy_engine_probes(monkeypatch, "unresolved")
    dispatches = _stub_dispatch(monkeypatch)

    rc = run_eval_harness.main(_run_argv(
        root, "unresolved", ["qwen"], "description", "--qwen-provider", "nowhere",
        "--qwen-model", "m", "--server-reasoning-effort", "medium",
    ))

    run = _read_json(run_dir / "run.json")
    server = run["server"]
    assert (rc, _marker(run_dir / "complete.txt")[1], len(dispatches)) == (0, ["1-qwen-a1"], 1)
    records.validate_record("run", run)
    assert probes.server_calls == []  # nothing to fetch from: the name is not a URL
    assert server["declared_effort"] == "medium"
    assert isinstance(server["metadata_error"], str) and "nowhere" in server["metadata_error"]
    assert [server[key] for key in records.SERVER_KEYS[:5]] == [None] * 5
    assert run["config"]["qwen_provider"] == "nowhere"


# -- the versions map ---------------------------------------------------------


def test_a_tdd_run_records_the_sealed_reference_versions_beside_the_probed_ones(completed):
    tdd, description = completed["tdd"], completed["description"]
    tdd_run = _read_json(tdd.run / "run.json")
    description_versions = _read_json(description.run / "run.json")["versions"]

    assert (tdd.rc, description.rc) == (0, 0)
    records.validate_record("run", tdd_run)
    versions = tdd_run["versions"]
    assert versions["ivan"] == "1"
    assert versions["subagent-dispatch"] == REFERENCES[1]["version"]
    assert versions == _expected_versions(tdd.probes.versions, "tdd")
    assert all(value is None or isinstance(value, str) for value in versions.values())
    # a description prompt carries no references, so their versions do not ride along
    assert {"ivan", "subagent-dispatch"} & set(description_versions) == set()
    assert description_versions == _expected_versions(description.probes.versions, "description")


def test_a_tdd_run_records_the_reference_versions_the_bundle_sealed_not_a_constant(
    tmp_path, vetted, shim, monkeypatch
):
    # The bundle's own dispatch-references.json, re-vetted so the seal covers it, names a
    # version nothing else in this suite spells; that is the one the run must record.
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    references = [
        dict(reference, version="7.3.1") if reference["name"] == "subagent-dispatch"
        else dict(reference) for reference in REFERENCES
    ]
    _write_json(root / "dispatch-references.json", references)
    (root / "tasks" / "1-calc" / "ready").unlink()
    assert attempt.vet(root, 1800.0) == 0
    probes = _spy_engine_probes(monkeypatch, "sealed-versions")

    rc = _run_direct(root, "sealed-versions", [_engine(shim, "pass")], "tdd")

    versions = _read_json(root / "runs" / "sealed-versions" / "run.json")["versions"]
    assert rc == 0
    assert versions == dict(probes.versions, ivan="1", **{"subagent-dispatch": "7.3.1"})

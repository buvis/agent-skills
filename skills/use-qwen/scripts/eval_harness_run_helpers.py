"""Constants, builders, drivers and fixtures shared by test_run_eval_harness.

Every round drives the real `run` driver with the fake engine (or a test-local
`cmd:` script) against a copy of a bundle that was sealed and vetted once per
module, so each run pays only for its own attempts and owns its run id (P13).
"""
import os
import re
import shlex
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import eval_harness_fixtures
import run_eval_harness
from eval_harness import attempt, engines, evidence, records
from eval_harness_evidence_helpers import (
    MUTATIONS,
    REFERENCES,
    _read_json,
    _spec_doc,
    _write_json,
)
from eval_harness_fixture_helpers import ATTEMPT_DIR_ENV, HEARTBEAT_ENV, _neutralise_git_env

# P11: the segments run as `bash -lc`, so name this interpreter, not `python`.
PYTEST_SEGMENT = shlex.quote(sys.executable) + " -m pytest -q -p no:cacheprovider"
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
STAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
OUTCOMES = {"PASS", "FAIL", "TIMEOUT", "SUSPECT", "DISCARDED"}
# No `.py` suffix, so the harness execs it directly and meets FileNotFoundError.
NO_ENGINE = "cmd:/nonexistent/engine"
# Stands in ROUNDS for the usage-limit stub, whose path exists only once `scratch` does.
USAGE_LIMIT_STUB = "<usage-limit-stub>"
PLAN_FIELDS = (
    "task_id", "slug", "spec", "shape", "engine_id", "engine_command", "attempt_no",
    "evidence_dir", "run_dir", "attempt_dir", "template_dir", "template_sha", "prompt_path",
    "writable", "oracle", "pretask", "necessity", "bound_s", "gate_bound_s", "settings",
)
CONFIG_KEYS = {
    "run_id", "engines", "shape", "bound", "gate_bound", "alternate", "retry_discarded",
    "server_reasoning_effort", "qwen_provider", "qwen_model", "sonnet_model", "usage_limit_cmd",
}
# P8: what an attempt stopped before dispatch records as its engine run.
NOT_LAUNCHED = {
    "argv": [], "launch": "not-started", "exit": None, "timed_out": False, "wall_s": None,
    "identity": None, "completion": "unknown", "final_message_bytes": None,
    "usage_limit": "unchecked", "first_edit_s": None, "usage": dict.fromkeys(records.USAGE_KEYS),
}
NO_GATES = {"gate": None, "own": None, "ablate": None}
VACUOUS_ORACLE = (
    "from calc import add\n\n\ndef test_add_returns_the_sum_of_its_arguments():\n    add(2, 3)\n"
)
# A template test that is green on the broken impl (C2): only the sealed oracle is red there.
AGREEABLE_TEST = (
    "from calc import add\n\n\ndef test_add_agrees_with_the_broken_impl():\n"
    "    assert add(2, 3) == -1\n"
)
# What `engines.dispatch` reports for a launched, exit-0, identity-bearing run that edited nothing.
LAUNCHED_UNEDITED = {
    "argv": ["pi", "-p", "spec"], "launch": "started", "exit": 0, "timed_out": False,
    "wall_s": 0.5, "identity": "qwen m", "completion": "complete", "final_message_bytes": 512,
    "usage_limit": "unchecked", "first_edit_s": None, "usage": dict.fromkeys(records.USAGE_KEYS),
}
# Sites the description shape's commands run in: the own gate judges the clone as the engine
# left it, the baseline and the other two gates their own fresh trees.
DESCRIPTION_SITES = ("baseline-clone", "gate-clone", "clone", "ablate-clone")

# Every round, by run id: the bundle to copy, its engines (fake-engine modes, the
# `fix-and-vacuous` script, or a raw `cmd:` string), the shape, extra argv, bounds.
# The `slow` bundle is vetted at gate bound 2, so its rounds run at 2 as well.
ROUNDS = {
    "r1": ("vetted", ["pass", "noop"], "description", [], {}),
    "tdd": ("vetted", ["pass", "mutate-test"], "tdd", [], {}),
    "stray": ("vetted", ["stray"], "tdd", [], {}),
    "vacuous": ("vetted", ["vacuous", "fix-and-vacuous"], "description", [], {}),
    "retry": (
        "vetted", [NO_ENGINE, "silent-edit"], "tdd", ["--retry-discarded", "harness-only"], {}
    ),
    "noretry": ("vetted", [NO_ENGINE, "exit1"], "tdd", [], {}),
    "exit1": ("vetted", ["exit1"], "tdd", ["--retry-discarded", "harness-only"], {}),
    "hang": ("vetted", ["hang", "hang"], "tdd", [], {"bound": "2"}),
    "pair": ("pair", ["drop", "pass"], "tdd", [], {}),
    "prep": ("drifted", ["pass"], "description", [], {}),
    "alt": ("drifted", ["pass", "noop"], "description", ["--alternate"], {}),
    "gatetimeout": ("slow", ["pass"], "description", [], {"gate_bound": "2"}),
    "basetimeout": ("slow", ["pass"], "description", [], {"gate_bound": "2"}),
    "limit": ("vetted", ["pass"], "description", ["--usage-limit-cmd", USAGE_LIMIT_STUB], {}),
}
# Rounds on the `drifted` bundle: both templates were altered on disk after vetting, and a
# harness never mutates sealed inputs, so `verify` keeps reporting exactly that drift.
DRIFTED_ROUNDS = {run_id for run_id, (bundle, *_) in ROUNDS.items() if bundle == "drifted"}


# -- helpers: bundles and scripts -------------------------------------------


def _spec(info: dict, *, segments=(), **over) -> dict:
    """P11's spec: the fixture task, tdd-capable, tested by this interpreter's pytest."""
    doc = dict(_spec_doc(info, tdd=True), raw_test_cmd=[*segments, PYTEST_SEGMENT])
    doc.update(over)
    return doc


def _cwd_log_segment(log: Path) -> str:
    """A segment that appends `<physical cwd> <ns stamp>` to `log` (P15)."""
    script = (
        'import sys, time; open(sys.argv[1], "a").write('
        'sys.argv[2] + " " + str(time.time_ns()) + "\\n")'
    )
    return " ".join(
        [shlex.quote(sys.executable), "-c", shlex.quote(script), shlex.quote(str(log)),
         '"$(pwd -P)"']
    )


def _fixture_repo(root: Path) -> dict:
    return eval_harness_fixtures.build_fixture_repo(root, change_test=True)


def _agreeable_repo(root: Path) -> dict:
    """A fixture repo whose base test agrees with the broken impl (C2).

    Its template is green on its own; only the task commit's widened oracle is red there.
    A vet that skips the oracle overlay sees a green baseline and refuses the task.
    """
    git, identity = eval_harness_fixtures._git, eval_harness_fixtures.IDENTITY
    git(root, *identity, "init")
    commits = (
        (eval_harness_fixtures.BROKEN_IMPL, AGREEABLE_TEST, "base: the test agrees with add()"),
        (eval_harness_fixtures.FIXED_IMPL, eval_harness_fixtures.WIDENED_ORACLE,
         "task: make add() sum its arguments"),
    )
    for impl, test, message in commits:
        (root / eval_harness_fixtures.IMPL_NAME).write_text(impl, encoding="utf-8")
        (root / eval_harness_fixtures.TEST_NAME).write_text(test, encoding="utf-8")
        git(root, "add", eval_harness_fixtures.IMPL_NAME, eval_harness_fixtures.TEST_NAME)
        git(root, *identity, "commit", "-m", message)
    return {"repo": root, "last": git(root, "rev-parse", "HEAD")}


def _new_bundle(scratch: Path, name: str, tasks: dict, build=_fixture_repo) -> SimpleNamespace:
    """An unsealed evidence dir with one fixture repo per task; `tasks` maps id to spec kwargs."""
    root = scratch / name
    (root / "tasks").mkdir(parents=True)
    _write_json(root / "dispatch-references.json", REFERENCES)
    infos = {}
    for task_id, spec_kwargs in tasks.items():
        repo = scratch / f"{name}-{task_id}"
        repo.mkdir()
        infos[task_id] = build(repo)
        (root / "tasks" / task_id).mkdir()
        _write_json(root / "tasks" / task_id / "spec.json", _spec(infos[task_id], **spec_kwargs))
    return SimpleNamespace(root=root, infos=infos)


def _copy(bundle_root: Path, dst: Path) -> Path:
    shutil.copytree(bundle_root, dst, symlinks=True)
    return dst


def _write_shim(directory: Path) -> Path:
    """P10's shim: `dispatch` passes no env, so point the fake engine at the prompt's dir."""
    shim = directory / "shim.py"
    shim.write_text(
        "import os\nimport subprocess\nimport sys\n\n"
        "mode, prompt = sys.argv[1], sys.argv[-1]\n"
        "attempt_dir = os.path.dirname(os.path.abspath(prompt))\n"
        "env = dict(os.environ)\n"
        f"env[{ATTEMPT_DIR_ENV!r}] = attempt_dir\n"
        f"env.setdefault({HEARTBEAT_ENV!r}, os.path.join(attempt_dir, 'beat.txt'))\n"
        "sys.exit(subprocess.call("
        f"[sys.executable, {str(eval_harness_fixtures.FAKE_ENGINE)!r}, mode, prompt], env=env))\n",
        encoding="utf-8",
    )
    return shim


def _write_fixing_vacuous_engine(directory: Path) -> Path:
    """P12's second engine: the fake engine's `pass` (its whole protocol), then a vacuous oracle."""
    script = directory / "fix_and_vacuous.py"
    script.write_text(
        "import os\nimport subprocess\nimport sys\n\n"
        "prompt = sys.argv[-1]\n"
        "env = dict(os.environ)\n"
        f"env[{ATTEMPT_DIR_ENV!r}] = os.path.dirname(os.path.abspath(prompt))\n"
        "rc = subprocess.call("
        f"[sys.executable, {str(eval_harness_fixtures.FAKE_ENGINE)!r}, 'pass', prompt], env=env)\n"
        f"open('test_calc.py', 'w', encoding='utf-8').write({VACUOUS_ORACLE!r})\n"
        "sys.exit(rc)\n",
        encoding="utf-8",
    )
    return script


def _engine(shim: Path, mode: str) -> str:
    return f"cmd:{shim} {mode}"


def _moved_input(name: str) -> tuple:
    """A refusal case that applies one MUTATIONS edit to `1-calc` after vetting."""
    label, edit = MUTATIONS[name]
    return (
        "vetted",
        lambda root: edit(SimpleNamespace(root=root, task=root / "tasks" / "1-calc")),
        {},
        (label, "vet"),
    )


# P3 refusals: bundle to copy, what to do to the copy, argv overrides, words the diagnostic names.
REFUSALS = {
    "no-ready-marker": (
        "vetted", lambda root: (root / "tasks" / "1-calc" / "ready").unlink(), {}, ()
    ),
    "gate-bound-differs": ("vetted", lambda root: None, {"gate_bound": "600"}, ("vet",)),
    "input-moved-since-vetting": _moved_input("edit-spec"),
    "oracle-moved-since-vetting": _moved_input("replace-oracle-file"),
    "prompt-moved-since-vetting": _moved_input("edit-description-prompt"),
    "canonical-moved-since-vetting": _moved_input("edit-canonical-patch"),
    "references-moved-since-vetting": _moved_input("edit-dispatch-references"),
    "manifest-moved-since-vetting": _moved_input("reindent-manifest"),
    # the seal covers every vetted shape: a description run still refuses a moved tdd prompt
    "tdd-prompt-moved-since-vetting": _moved_input("edit-tdd-prompt"),
    "shape-not-vetted": ("slow", lambda root: None, {"shape": "tdd", "gate_bound": "2"}, ("tdd",)),
    "qwen-without-settings": ("vetted", lambda root: None, {"engines": ["qwen"]}, ()),
    "sonnet-without-settings": ("vetted", lambda root: None, {"engines": ["sonnet"]}, ()),
}


# -- helpers: driving and reading runs ---------------------------------------


def _run_argv(root, run_id, engine_cmds, shape, *extra, bound="30", gate_bound="1800") -> list:
    return [
        "run", str(root), "--run-id", run_id, "--engines", ",".join(engine_cmds),
        "--shape", shape, "--bound", bound, "--gate-bound", gate_bound, *extra,
    ]


def _run_direct(root, run_id, engine_cmds, shape) -> int:
    """Call `attempt.run` the way the CLI would, with the P6 config a caller must supply."""
    config = dict.fromkeys(CONFIG_KEYS)
    config.update(run_id=run_id, engines=list(engine_cmds), shape=shape, bound=30.0,
                  gate_bound=1800.0, alternate=False, retry_discarded="none")
    settings = engines.EngineSettings(
        qwen_provider=None, qwen_model=None, sonnet_model=None, usage_limit_cmd=None,
        server_reasoning_effort=None,
    )
    return attempt.run(
        root, run_id, list(engine_cmds), shape, 30.0, 1800.0, alternate=False,
        retry_discarded="none", settings=settings, config=config,
    )


def _record(round_, attempt_id: str) -> dict:
    return _read_json(round_.run / attempt_id / "attempt.json")


def _attempts(round_) -> dict:
    """Every attempt record in the run dir, keyed by attempt id, in name order."""
    found = sorted(round_.run.glob("*/attempt.json"))
    return {path.parent.name: _read_json(path) for path in found}


def _marker(path: Path) -> tuple:
    """A marker file as (headers, ids): `key: value` lines, then one id per line (P1)."""
    headers, ids = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(": ")
        if sep:
            headers[key] = value
        else:
            ids.append(line.strip())
    return headers, ids


def _ids(round_) -> list:
    return _marker(round_.run / "complete.txt")[1]


def _paths(record: dict) -> list:
    return sorted(entry["path"] for entry in record["changed"])


def _gate(record: dict, label: str) -> dict:
    return record["gates"][label]


def _epoch(stamp: str) -> float:
    """A P7 stamp as UTC epoch seconds; a stamp in any other shape raises ValueError."""
    return datetime.strptime(stamp, STAMP_FORMAT).replace(tzinfo=timezone.utc).timestamp()


def _cwds(lines: list) -> list:
    """The cwd of every `<cwd> <ns>` line a `_cwd_log_segment` wrote."""
    return [line.rsplit(" ", 1)[0] for line in lines]


def _logged_cwds(round_, log: Path) -> list:
    """The cwd of every line the round's own test commands appended to `log` (P15)."""
    prefix = str(round_.run.resolve()) + os.sep
    lines = [
        line for line in log.read_text(encoding="utf-8").splitlines() if line.startswith(prefix)
    ]
    assert len(lines) == len(set(lines)), "two runs of the test command share a stamp"
    return _cwds(lines)


def _spy_engine_probes(patch, run_id: str) -> SimpleNamespace:
    """Replace the CLI and server probes with spies whose answers are unique to this run.

    `server_calls` lists the values every `fetch_server_props` call was given, in call
    order; `server` is what the last call returned.
    """
    probes = SimpleNamespace(
        version_calls=[], server_calls=[], versions={"pi": None, "claude": f"spy {run_id}"},
        server=None,
    )

    def spy_versions(engine_ids, settings):
        probes.version_calls.append(list(engine_ids))
        return dict(probes.versions)

    def spy_server(*args, **kwargs):
        given = [*args, *kwargs.values()]
        probes.server_calls.append(given)
        probes.server = dict(
            dict.fromkeys(records.SERVER_KEYS), model_alias=f"spy {run_id}",
            declared_effort=given[-1],
        )
        return dict(probes.server)

    patch.setattr(engines, "record_versions", spy_versions)
    patch.setattr(engines, "fetch_server_props", spy_server)
    return probes


def _stub_dispatch(patch) -> list:
    """Replace `engines.dispatch` with a stub that launches nothing and touches no clone.

    Returns the list its calls land in, as `(args, kwargs)`.
    """
    calls = []

    def dispatch(*args, **kwargs):
        calls.append((args, kwargs))
        return dict(LAUNCHED_UNEDITED, usage=dict(LAUNCHED_UNEDITED["usage"]))

    patch.setattr(engines, "dispatch", dispatch)
    return calls


# -- assertion helpers shared by every completed round --------------------------


def _assert_attempt_artifacts_match(where: Path, record: dict) -> None:
    """One attempt dir against its record: verdict, stamps, status, files per command."""
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


def _assert_verify_reports_only_the_template_drift(round_, run_id: str, capsys) -> None:
    """`verify` (all three entry points) is clean, except on the `drifted` bundle, whose two
    templates were altered on disk after vetting: a harness never mutates sealed inputs, so
    the run leaves that drift in place and the two manifest mismatches are all it reports.
    """
    drifted = ("2-calc", "10-calc") if run_id in DRIFTED_ROUNDS else ()
    capsys.readouterr()
    rc = evidence.verify(round_.root)
    lines = capsys.readouterr().out.splitlines()
    assert rc == (1 if drifted else 0), lines
    assert sorted(line.split(": mismatch ", 1)[0] for line in lines) == sorted(
        f"tasks/{task_id}/manifest.json" for task_id in drifted
    ), lines
    assert all("calc.py" in line.split(": mismatch ", 1)[1] for line in lines), lines
    assert run_eval_harness.main(["verify", str(round_.root)]) == rc
    assert attempt.verify(round_.root) == rc
    for task_id in drifted:
        template = round_.root / "tasks" / task_id / "template"
        assert (template / "extra.txt").is_file(), task_id
        impl = (template / "calc.py").read_text(encoding="utf-8")
        assert impl.endswith("# drifted after vetting\n"), task_id


# -- fixtures ----------------------------------------------------------------


@pytest.fixture(scope="module")
def scratch(tmp_path_factory):
    """One resolved directory for the module, with git kept CI-bare throughout."""
    root = tmp_path_factory.mktemp("harness").resolve()
    with pytest.MonkeyPatch.context() as patch:
        _neutralise_git_env(patch, root)
        yield root


@pytest.fixture(scope="module")
def shim(scratch):
    return _write_shim(scratch)


@pytest.fixture(scope="module")
def vetted(scratch):
    """The one description+tdd bundle, CLI-vetted once (P13); its test command logs cwd (P15)."""
    log = scratch / "baseline-cwds.log"
    bundle = _new_bundle(scratch, "vetted", {"1-calc": {"segments": (_cwd_log_segment(log),)}})
    bundle.log = log
    bundle.task = bundle.root / "tasks" / "1-calc"
    bundle.rc = run_eval_harness.main(["vet", str(bundle.root)])
    assert bundle.rc == 0
    # What vet alone wrote to the log; every later round appends its own lines.
    bundle.vet_lines = log.read_text(encoding="utf-8").splitlines()
    return bundle


@pytest.fixture(scope="module")
def pair(scratch):
    """Two tasks vetted by `attempt.vet` itself: `2-calc` widened to notes.md, `10-calc` plain
    but with one warmup segment that logs the cwd it ran in.
    """
    warmup_log = scratch / "warmup-cwds.log"
    tasks = {
        "2-calc": {"writable": ["calc.py", "notes.md"]},
        "10-calc": {"warmup": [_cwd_log_segment(warmup_log)]},
    }
    bundle = _new_bundle(scratch, "pair", tasks)
    bundle.rc = attempt.vet(bundle.root, 1800.0)
    assert bundle.rc == 0
    bundle.warmup_lines = warmup_log.read_text(encoding="utf-8").splitlines()
    return bundle


@pytest.fixture(scope="module")
def drifted(scratch, pair):
    """A copy of `pair` whose templates drifted after vetting: every clone mismatches (P17).

    `calc.py` is a writable path; `extra.txt` is one the manifest never listed, so only a
    prep that proves the whole tree (not just the writable hashes) reports it.
    """
    root = _copy(pair.root, scratch / "drifted")
    for impl in root.glob("tasks/*/template/calc.py"):
        impl.write_text(impl.read_text(encoding="utf-8") + "# drifted after vetting\n",
                        encoding="utf-8")
        (impl.parent / "extra.txt").write_text("unlisted\n", encoding="utf-8")
    return SimpleNamespace(root=root)


@pytest.fixture(scope="module")
def slow(scratch):
    """A description-only bundle CLI-vetted at gate bound 2 (P17); its test command sleeps 5 s
    in any baseline once the flag exists and in every gate clone. Vetting sees neither, and a
    pytest segment that takes 1.5 s on a loaded box still fits the bound.
    """
    flag = scratch / "slow-baseline.flag"
    segments = (
        f"if [ -e {shlex.quote(str(flag))} ]; then sleep 5; fi",
        'case "$(pwd -P)" in *gate-clone) sleep 5;; esac',
    )
    bundle = _new_bundle(scratch, "slow", {"1-calc": {"segments": segments}})
    bundle.flag = flag
    bundle.task = bundle.root / "tasks" / "1-calc"
    bundle.rc = run_eval_harness.main(
        ["vet", str(bundle.root), "--gate-bound", "2", "--shapes", "description"]
    )
    assert bundle.rc == 0
    return bundle


@pytest.fixture(scope="module")
def rounds(scratch, shim, vetted, pair, drifted, slow):
    """Completed rounds by run id (see ROUNDS), each built on first use in its own bundle copy."""
    bundles = {"vetted": vetted, "pair": pair, "drifted": drifted, "slow": slow}
    fixer = _write_fixing_vacuous_engine(scratch)
    # The usage-limit checker of the `limit` round: exit 0 means STUCK, and it records its argv.
    stub_argv = scratch / "limit-argv.txt"
    stub = eval_harness_fixtures.write_argv_recording_stub(scratch, "limit", stub_argv, exit_code=0)
    built = {}

    def command(spec: str) -> str:
        if spec.startswith("cmd:"):
            return spec
        return f"cmd:{fixer}" if spec == "fix-and-vacuous" else _engine(shim, spec)

    def get(run_id: str) -> SimpleNamespace:
        if run_id in built:
            return built[run_id]
        bundle_name, specs, shape, extra, bounds = ROUNDS[run_id]
        if run_id == "basetimeout":
            get("gatetimeout")  # from here on every baseline of `slow` sleeps past its bound
            slow.flag.touch()
        root = _copy(bundles[bundle_name].root, scratch / f"round-{run_id}")
        extra = [str(stub) if arg == USAGE_LIMIT_STUB else arg for arg in extra]
        argv = _run_argv(root, run_id, [command(spec) for spec in specs], shape, *extra, **bounds)
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv(HEARTBEAT_ENV, str(scratch / "beat.txt"))  # only `hang` writes it
            probes = _spy_engine_probes(patch, run_id)
            before = time.time()
            rc = run_eval_harness.main(argv)
            after = time.time()
        built[run_id] = SimpleNamespace(
            root=root, run=root / "runs" / run_id, rc=rc, before=before, after=after,
            engine_ids=[f"cmd{i}" for i in range(1, len(specs) + 1)], probes=probes,
            stub=stub, stub_argv=stub_argv,
        )
        return built[run_id]

    return get

"""Constants, builders, drivers and fixtures shared by test_run_eval_harness.

Every round drives the real `run` driver with the fake engine (or a test-local
`cmd:` script) against a copy of a bundle that was sealed and vetted once per
module, so each run pays only for its own attempts and owns its run id (P13).
"""
import re
import shlex
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import eval_harness_fixtures
import run_eval_harness
from eval_harness import attempt, engines, records
from eval_harness_evidence_helpers import REFERENCES, _read_json, _spec_doc, _write_json
from eval_harness_fixture_helpers import ATTEMPT_DIR_ENV, HEARTBEAT_ENV, _neutralise_git_env

# P11: the segments run as `bash -lc`, so name this interpreter, not `python`.
PYTEST_SEGMENT = shlex.quote(sys.executable) + " -m pytest -q -p no:cacheprovider"
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
OUTCOMES = {"PASS", "FAIL", "TIMEOUT", "SUSPECT", "DISCARDED"}
# No `.py` suffix, so the harness execs it directly and meets FileNotFoundError.
NO_ENGINE = "cmd:/nonexistent/engine"
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
}


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


def _new_bundle(scratch: Path, name: str, tasks: dict) -> SimpleNamespace:
    """An unsealed evidence dir with one fixture repo per task; `tasks` maps id to spec kwargs."""
    root = scratch / name
    (root / "tasks").mkdir(parents=True)
    _write_json(root / "dispatch-references.json", REFERENCES)
    infos = {}
    for task_id, spec_kwargs in tasks.items():
        repo = scratch / f"{name}-{task_id}"
        repo.mkdir()
        infos[task_id] = eval_harness_fixtures.build_fixture_repo(repo, change_test=True)
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


def _move_spec(root: Path) -> None:
    spec = root / "tasks" / "1-calc" / "spec.json"
    _write_json(spec, dict(_read_json(spec), task_text="make add() multiply"))


# P3 refusals: bundle to copy, what to do to the copy, argv overrides, words the diagnostic names.
REFUSALS = {
    "no-ready-marker": (
        "vetted", lambda root: (root / "tasks" / "1-calc" / "ready").unlink(), {}, ()
    ),
    "gate-bound-differs": ("vetted", lambda root: None, {"gate_bound": "600"}, ("vet",)),
    "input-moved-since-vetting": ("vetted", _move_spec, {}, ("spec", "vet")),
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
    return bundle


@pytest.fixture(scope="module")
def pair(scratch):
    """Two tasks vetted by `attempt.vet` itself: `2-calc` widened to notes.md, `10-calc` plain."""
    tasks = {"2-calc": {"writable": ["calc.py", "notes.md"]}, "10-calc": {}}
    bundle = _new_bundle(scratch, "pair", tasks)
    bundle.rc = attempt.vet(bundle.root, 1800.0)
    assert bundle.rc == 0
    return bundle


@pytest.fixture(scope="module")
def drifted(scratch, pair):
    """A copy of `pair` whose templates drifted after vetting: every clone mismatches (P17)."""
    root = _copy(pair.root, scratch / "drifted")
    for impl in root.glob("tasks/*/template/calc.py"):
        impl.write_text(impl.read_text(encoding="utf-8") + "# drifted after vetting\n",
                        encoding="utf-8")
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
        argv = _run_argv(root, run_id, [command(spec) for spec in specs], shape, *extra, **bounds)
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv(HEARTBEAT_ENV, str(scratch / "beat.txt"))  # only `hang` writes it
            rc = run_eval_harness.main(argv)
        built[run_id] = SimpleNamespace(root=root, run=root / "runs" / run_id, rc=rc)
        return built[run_id]

    return get

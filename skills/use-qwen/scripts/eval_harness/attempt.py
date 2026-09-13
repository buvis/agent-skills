"""The driving half of the qwen evaluation harness: vet, run and verify.

`vet` seals every task under `tasks/` and qualifies it on scratch clones that
are gone when it returns. `run` takes every ready task through every engine,
one frozen AttemptPlan per attempt, and publishes each record before moving
on; a process tree that outlives its command halts the run once the in-flight
record is on disk. Git, subprocesses and hashing all live in sibling modules.
"""
import dataclasses
import itertools
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from eval_harness import engines, evidence, gates, records, runner, trees
from eval_harness import spec as spec_mod
from eval_harness.engines import EngineSettings
from eval_harness.spec import Spec

STAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ORACLE_COMMIT = "tdd: the vetted oracle the candidate works against"


@dataclass(frozen=True)
class AttemptPlan:
    """Everything one attempt needs; `run` is its only constructor."""
    task_id: int
    slug: str
    spec: Spec
    shape: str
    engine_id: str
    engine_command: str
    attempt_no: int
    evidence_dir: Path
    run_dir: Path
    attempt_dir: Path
    template_dir: Path
    template_sha: str
    prompt_path: Path
    writable: tuple[str, ...]
    oracle: tuple[str, ...]
    pretask: dict
    necessity: dict[str, dict]
    bound_s: float
    gate_bound_s: float
    settings: EngineSettings


class RefusalError(RuntimeError):
    """Raised while `runs/<run-id>/` does not exist yet. str() names the remedy."""


class RunHalted(RuntimeError):
    """Raised once the in-flight attempt is recorded, naming the command that leaked a tree."""

    def __init__(self, reason: str, plan: AttemptPlan, command: str):
        super().__init__("%s %s %s" % (reason, plan.attempt_dir, command))
        self.reason, self.plan, self.command = reason, plan, command


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime(STAMP_FORMAT)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, text: str) -> None:
    """Write beside the target, then replace it: a reader sees the old file or the whole new one."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _write_json(path: Path, doc: dict) -> None:
    _write_text(path, json.dumps(doc, indent=2, sort_keys=True) + "\n")


def _write_marker(run_dir: Path, name: str, headers: dict, ids: list[str]) -> None:
    """A run marker (P1): `key: value` header lines, then one attempt id per line."""
    lines = ["%s: %s" % item for item in headers.items()] + ids
    _write_text(run_dir / name, "".join(line + "\n" for line in lines))


def _log(where: Path, line: str) -> None:
    """Append one step to `<where>/progress.log`: the run's, or one attempt's."""
    with (where / "progress.log").open("a", encoding="utf-8") as log:
        log.write(line + "\n")


def _task_dirs(evidence_dir: Path) -> list[Path]:
    """Every task under tasks/, in numeric-prefix order."""
    tasks = [path for path in (evidence_dir / "tasks").iterdir() if path.is_dir()]
    return sorted(tasks, key=lambda path: int(path.name.split("-", 1)[0]))


def _not_launched() -> dict:
    """The engine_run block of an attempt stopped before dispatch (P8)."""
    return {"argv": [], "launch": "not-started", "exit": None, "timed_out": False, "wall_s": None,
            "identity": None, "completion": "unknown", "final_message_bytes": None,
            "usage_limit": "unchecked", "first_edit_s": None,
            "usage": dict.fromkeys(records.USAGE_KEYS)}


def vet(evidence_dir: Path, gate_bound_s: float, shapes=None) -> int:
    """Seal and qualify every task; 0 when each ended ready, else 1 naming the failed check."""
    all_ready = True
    for task_dir in _task_dirs(evidence_dir):
        try:
            seal = evidence.seal_inputs(evidence_dir, task_dir,
                                        shapes or evidence.default_shapes(task_dir))
        except evidence.EvidenceError as exc:
            print("%s: %s" % (task_dir.name, exc), file=sys.stderr)
            return 1
        (task_dir / "ready").unlink(missing_ok=True)
        checks, failed = _vet_checks(task_dir, spec_mod.load_spec(task_dir, "description"), seal,
                                     gate_bound_s)
        record = dict(template_sha=seal.template_sha, gate_bound_s=gate_bound_s, **checks,
                      inputs_sha256=seal.inputs_sha256, shapes=list(seal.shapes),
                      ready=failed is None)
        records.validate_record("vetting", record)
        _write_json(task_dir / "vetting.json", record)
        if failed is None:
            (task_dir / "ready").write_text(_stamp() + "\n", encoding="utf-8")
        else:
            print("%s: the %s check failed; see vetting.json" % (task_dir.name, failed),
                  file=sys.stderr)
            all_ready = False
    return 0 if all_ready else 1


def _vet_checks(task_dir: Path, task_spec: Spec, seal, bound_s: float) -> tuple[dict, str | None]:
    """Warmup, baseline, canonical, then necessity per path; the check that failed, or None."""
    checks = {"warmup": [], "baseline": None, "canonical": None, "necessity": {}}
    with tempfile.TemporaryDirectory() as scratch:
        clones = itertools.count()

        def measure(segments, *, overlay=True, exclude=None) -> dict:
            """The segments on a fresh clone: canonical minus `exclude`, then the oracle, on top."""
            clone = trees.fresh_clone(task_dir / "template", Path(scratch) / str(next(clones)))
            trees.mise_trust(clone)
            if exclude is not None:
                applied = trees.apply_patch(clone, task_dir / "canonical.patch", exclude=exclude)
                if applied.rc != 0:
                    return applied.as_json()
            if overlay:
                trees.overlay_oracle(task_dir, clone, seal.oracle)
            return runner.run_segments(segments, clone, bound_s).as_json()

        for segment in task_spec.warmup:
            checks["warmup"].append(measure([segment], overlay=False))
            if checks["warmup"][-1]["rc"] != 0:
                return checks, "warmup"
        checks["baseline"] = measure(task_spec.raw_test_cmd)
        if not records.is_valid_baseline(checks["baseline"]):
            return checks, "baseline"
        checks["canonical"] = measure(task_spec.raw_test_cmd, exclude=())
        if checks["canonical"]["rc"] != 0:
            return checks, "canonical"
        for path in seal.writable:
            if path not in seal.oracle:
                result = measure(task_spec.raw_test_cmd, exclude=(path,))
                checks["necessity"][path] = {"result": result,
                                             "holds": records.is_valid_baseline(result)}
    return checks, None


def verify(evidence_dir: Path) -> int:
    return evidence.verify(evidence_dir)


def run(evidence_dir: Path, run_id: str, engine_cmds: list[str], shape: str, bound_s: float,
        gate_bound_s: float, *, alternate: bool, retry_discarded: str,
        settings: EngineSettings, config: dict) -> int:
    """Every ready task through every engine: 0 complete, 1 refused before any write, 2 halted."""
    evidence_dir = evidence_dir.resolve()
    run_dir = evidence_dir / "runs" / run_id
    ids = [cmd if cmd in ("qwen", "sonnet") else "cmd%d" % n
           for n, cmd in enumerate(engine_cmds, 1)]
    try:
        if run_dir.exists():
            raise RefusalError("%s already exists; choose a new --run-id" % run_dir)
        admitted = _admit(evidence_dir, shape, gate_bound_s, engine_cmds, settings)
    except (RefusalError, evidence.EvidenceError) as exc:
        print("run refused: %s" % exc, file=sys.stderr)
        return 1
    engine_order = list(zip(ids, engine_cmds))
    plans = _plan_attempts(admitted, engine_order, alternate, dict(
        shape=shape, evidence_dir=evidence_dir, run_dir=run_dir, bound_s=bound_s,
        gate_bound_s=gate_bound_s, settings=settings))
    run_dir.mkdir(parents=True)
    _write_json(run_dir / "sealed-inputs.json", {task.name: found for task, _, found in admitted})
    _write_json(run_dir / "run.json", _run_record(run_id, config, engine_order, plans, settings))
    _log(run_dir, "run %s: %d attempt(s) planned" % (run_id, len(plans)))
    done = []
    try:
        for plan in plans:
            record = run_attempt(plan)
            done.append(plan.attempt_dir.name)
            _log(run_dir, "%s: %s %s" % (done[-1], record["validity"], record["outcome"]))
            if retry_discarded == "harness-only" and record["validity"] == "DISCARDED:harness":
                retry = dataclasses.replace(plan, attempt_no=2, attempt_dir=plan.run_dir / (
                    "%d-%s-a2" % (plan.task_id, plan.engine_id)))
                record = run_attempt(retry)
                done.append(retry.attempt_dir.name)
                _log(run_dir, "%s: %s %s" % (done[-1], record["validity"], record["outcome"]))
    except RunHalted as halt:
        done.append(halt.plan.attempt_dir.name)
        _log(halt.plan.attempt_dir, str(halt))
        _log(run_dir, str(halt))
        _write_marker(run_dir, "halted.txt", {"reason": halt.reason, "attempt": done[-1],
                                              "command": halt.command, "attempts": len(done)}, done)
        return 2
    _write_marker(run_dir, "complete.txt", {"attempts": len(done), "finished": _stamp()}, done)
    return 0


def _admit(evidence_dir: Path, shape: str, gate_bound_s: float, engine_cmds: list[str],
           settings: EngineSettings) -> list[tuple[Path, dict, dict]]:
    """Every task with its vetting record and re-checked seal, or the first refusal (P3)."""
    if "qwen" in engine_cmds and not (settings.qwen_provider and settings.qwen_model):
        raise RefusalError("qwen needs --qwen-provider and --qwen-model")
    if "sonnet" in engine_cmds and not settings.sonnet_model:
        raise RefusalError("sonnet needs --sonnet-model")
    admitted = []
    for task_dir in _task_dirs(evidence_dir):
        if not (task_dir / "ready").exists():
            raise RefusalError("%s: no ready marker; run vet first" % task_dir.name)
        vetting = _read_json(task_dir / "vetting.json")
        if vetting["gate_bound_s"] != gate_bound_s:
            raise RefusalError("%s: --gate-bound %s differs from the vetted %s; re-run vet with "
                               "the new bound" % (task_dir.name, gate_bound_s,
                                                  vetting["gate_bound_s"]))
        if shape not in vetting["shapes"]:
            raise RefusalError("%s: shape %s was not vetted (vetted: %s); re-run vet with "
                               "--shapes %s" % (task_dir.name, shape, ",".join(vetting["shapes"]),
                                                shape))
        admitted.append((task_dir, vetting, evidence.recheck_inputs(evidence_dir, task_dir)))
    return admitted


def _plan_attempts(admitted: list, engine_order: list[tuple[str, str]], alternate: bool,
                   common: dict) -> list[AttemptPlan]:
    """One first attempt per (task, engine); under --alternate odd tasks reverse the engines."""
    plans = []
    for index, (task_dir, vetting, _found) in enumerate(admitted):
        task_spec = spec_mod.load_spec(task_dir, common["shape"])
        pretask = _read_json(task_dir / "pretask.json")
        order = engine_order[::-1] if alternate and index % 2 else engine_order
        for engine_id, command in order:
            plans.append(AttemptPlan(
                task_id=task_spec.task_id, slug=task_spec.slug, spec=task_spec,
                engine_id=engine_id, engine_command=command, attempt_no=1,
                attempt_dir=common["run_dir"] / ("%d-%s-a1" % (task_spec.task_id, engine_id)),
                template_dir=task_dir / "template", template_sha=vetting["template_sha"],
                prompt_path=task_dir / "prompts" / ("%s.txt" % common["shape"]),
                writable=tuple(pretask["writable"]), oracle=tuple(pretask["oracle"]),
                pretask=pretask, necessity=vetting["necessity"], **common))
    return plans


def _run_record(run_id: str, config: dict, engine_order: list[tuple[str, str]],
                plans: list[AttemptPlan], settings: EngineSettings) -> dict:
    """run.json: the resolved config, the engines, the tasks and the two probes (P6, R9)."""
    ids = [engine_id for engine_id, _command in engine_order]
    if "qwen" in ids:
        server = engines.fetch_server_props(settings.qwen_provider,
                                            settings.server_reasoning_effort)
    else:
        server = dict(dict.fromkeys(records.SERVER_KEYS),
                      declared_effort=settings.server_reasoning_effort)
    tasks = [{"id": plan.task_id, "slug": plan.slug, "repo": str(plan.spec.repo),
              "kind": spec_mod.derive_kind(list(plan.writable)), "writable": list(plan.writable),
              "oracle": list(plan.oracle),
              "prompt_sha256": trees.hash_paths(plan.prompt_path.parent,
                                                [plan.prompt_path.name])[plan.prompt_path.name]}
             for plan in {plan.task_id: plan for plan in plans}.values()]
    record = {"schema_version": 1, "run_id": run_id, "started": _stamp(), "config": config,
              "engines": [{"id": i, "command": c} for i, c in engine_order],
              "tasks": tasks, "versions": engines.record_versions(ids, settings),
              "server": server}
    records.validate_record("run", record)
    return record


def run_attempt(plan: AttemptPlan) -> dict:
    """One attempt, steps 1-9; its record is on disk before a halt is raised."""
    plan.attempt_dir.mkdir(parents=True)
    record = dict.fromkeys(records.ATTEMPT_KEYS)
    record.update(task=plan.task_id, engine=plan.engine_id, attempt=plan.attempt_no,
                  shape=plan.shape, clone=str(plan.attempt_dir / "clone"),
                  engine_run=_not_launched(), gates=dict.fromkeys(records.GATE_KEYS),
                  started=_stamp())
    prompt = plan.attempt_dir / "prompt.txt"
    shutil.copyfile(plan.prompt_path, prompt)
    _log(plan.attempt_dir, "started %s; prompt.txt copied from %s" % (record["started"],
                                                                     plan.prompt_path))
    site = gates.GateSite(plan.attempt_dir, plan.run_dir, plan.template_dir.parent, plan.shape,
                          plan.writable, plan.oracle, plan.spec.raw_test_cmd, plan.gate_bound_s)
    try:
        _steps(plan, site, record)
    except RunHalted:
        _write_records(plan, record)
        raise
    return _write_records(plan, record)


def _steps(plan: AttemptPlan, site: gates.GateSite, record: dict) -> None:
    """Steps 2-8 in order; a stop leaves the later fields null for the ladder to read."""
    record["prep"] = _prepare_clone(plan)
    if record["prep"]["status"] != "ok":
        return
    record["baseline"] = _command(plan, "baseline", gates.run_baseline, site).as_json()
    if not records.is_valid_baseline(record["baseline"]):
        return
    record["prep"], sealed = _seal_clone(plan)
    if record["prep"]["status"] != "ok":
        return
    record["engine_run"] = _command(
        plan, "engine", engines.dispatch, plan.engine_id, plan.engine_command,
        plan.attempt_dir / "prompt.txt", plan.attempt_dir / "clone", plan.attempt_dir,
        plan.settings, plan.bound_s)
    record.update(gates.observe(site, sealed, plan.necessity))
    _log(plan.attempt_dir, "observed %d changed path(s), stray %s, dropped %s" % (
        len(record["changed"]), record["stray"], record["dropped"]))
    for name in records.GATE_KEYS:
        if name in records.REQUIRED_GATES[plan.shape]:
            record["gates"][name] = _gate(plan, site, name)


def _command(plan: AttemptPlan, label: str, command, *args):
    """Run one measured command; a tree that outlives it halts the run naming `label` (P14)."""
    _log(plan.attempt_dir, "%s: running" % label)
    try:
        return command(*args)
    except runner.OrphanError as exc:
        raise RunHalted("HALTED:orphans", plan, label) from exc
    except runner.JobAssignmentError as exc:
        raise RunHalted("HALTED:%s" % exc.reason, plan, label) from exc


def _prepare_clone(plan: AttemptPlan) -> dict:
    """Steps 1-2: a fresh, trusted clone proved against pretask.json and manifest.json."""
    clone = trees.fresh_clone(plan.template_dir, plan.attempt_dir / "clone")
    trees.mise_trust(clone)
    manifest = _read_json(plan.template_dir.parent / "manifest.json")
    status, differing = trees.prove_state(clone, plan.pretask, manifest)
    _log(plan.attempt_dir, "clone proved against pretask.json: %s %s" % (status, differing))
    return {"status": status, "differing_paths": differing}


def _seal_clone(plan: AttemptPlan) -> tuple[dict, dict]:
    """Steps 4-5: tdd's oracle committed, sealed.json beside the clone, the tree proved by it."""
    task_dir, clone = plan.template_dir.parent, plan.attempt_dir / "clone"
    expected = _read_json(task_dir / "manifest.json")
    if plan.shape == "tdd":
        trees.overlay_oracle(task_dir, clone, plan.oracle)
        trees.commit_all(clone, ORACLE_COMMIT)
        vetted = trees.build_manifest(task_dir / "oracle")
        expected.update((path, vetted[path]) for path in plan.oracle)
    sealed = {"head_sha": trees.head_sha(clone), "writable": trees.hash_paths(clone, plan.writable),
              "oracle": trees.hash_paths(clone, plan.oracle)}
    records.validate_record("sealed", sealed)
    _write_json(plan.attempt_dir / "sealed.json", sealed)
    status, differing = trees.prove_state(clone, sealed, expected)
    _log(plan.attempt_dir, "clone proved against sealed.json: %s %s" % (status, differing))
    return {"status": status, "differing_paths": differing}, sealed


def _gate(plan: AttemptPlan, site: gates.GateSite, name: str) -> dict | None:
    """One required gate; a patch that does not apply leaves it unmeasured, the rest still run."""
    try:
        return _command(plan, name, getattr(gates, "run_" + name), site).as_json()
    except gates.GateError as exc:
        _log(plan.attempt_dir, "%s: not measured, %s" % (name, exc))
        return None


def _write_records(plan: AttemptPlan, record: dict) -> dict:
    """Step 9: the verdict from the evidence, then attempt.json and status.txt published."""
    record["validity"] = records.derive_validity(record)
    record["outcome"], record["class"] = records.classify(record)
    record["finished"] = _stamp()
    records.validate_record("attempt", record)
    _write_json(plan.attempt_dir / "attempt.json", record)
    status = record["outcome"] if record["class"] is None else "%s:%s" % (record["outcome"],
                                                                          record["class"])
    _write_text(plan.attempt_dir / "status.txt", status + "\n")
    _log(plan.attempt_dir, "finished %s: %s (%s)" % (record["finished"], status,
                                                    record["validity"]))
    return record

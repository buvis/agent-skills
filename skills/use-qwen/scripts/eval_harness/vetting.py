"""The checks a vet runs on a sealed task: warmup, baseline, canonical, necessity.

Every check runs on a fresh clone of the task's template that is gone when the
vet returns, and holds the bundle's one gate marker under its own label while it
runs, so no check overlaps another caller's gate. The warmup list shares one
budget: each segment gets what the earlier ones left of the gate bound. `attempt.vet`
is the entry point; this module never imports it.
"""
import itertools
import tempfile
import time
from pathlib import Path

from eval_harness import records, runner, trees
from eval_harness.spec import Spec


def run_checks(evidence_dir: Path, task_dir: Path, task_spec: Spec, seal,
               bound_s: float) -> tuple[dict, str | None]:
    """Warmup, baseline, canonical, then necessity per path; the check that failed, or None."""
    checks = {"warmup": [], "baseline": None, "canonical": None, "necessity": {}}
    with tempfile.TemporaryDirectory() as scratch:
        clones = itertools.count()

        def measure(label, segments, *, overlay=True, exclude=None, deadline_s=bound_s) -> dict:
            """The segments on a fresh clone, under the gate lock: canonical minus `exclude`,
            then the oracle, on top."""
            with runner.gate_lock(evidence_dir, label):
                clone = trees.fresh_clone(task_dir / "template",
                                          Path(scratch) / str(next(clones)))
                trees.mise_trust(clone)
                if exclude is not None:
                    applied = trees.apply_patch(clone, task_dir / "canonical.patch",
                                                exclude=exclude)
                    if applied.rc != 0:
                        return applied.as_json()
                if overlay:
                    trees.overlay_oracle(task_dir, clone, seal.oracle)
                return runner.run_segments(segments, clone, deadline_s).as_json()

        started = time.monotonic()
        for segment in task_spec.warmup:
            left = bound_s - (time.monotonic() - started)
            checks["warmup"].append(measure("warmup", [segment], overlay=False, deadline_s=left))
            if checks["warmup"][-1]["rc"] != 0:
                return checks, "warmup"
        checks["baseline"] = measure("baseline", task_spec.raw_test_cmd)
        if not records.is_valid_baseline(checks["baseline"]):
            return checks, "baseline"
        checks["canonical"] = measure("canonical", task_spec.raw_test_cmd, exclude=())
        if checks["canonical"]["rc"] != 0:
            return checks, "canonical"
        for path in seal.writable:
            if path not in seal.oracle:
                result = measure("necessity", task_spec.raw_test_cmd, exclude=(path,))
                checks["necessity"][path] = {"result": result,
                                             "holds": records.is_valid_baseline(result)}
    return checks, None

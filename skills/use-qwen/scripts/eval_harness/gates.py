"""The measuring half of one attempt of the qwen evaluation harness.

Before dispatch the baseline runs the vetted oracle in a clone of the sealed
template, so a suite that fails for no test reason is known before any
candidate is blamed. After dispatch the observation reads the candidate's work
out of its clone once, into `diff.patch` and a change list, and touches nothing.
The gates then score that record, never the clone: `gate` replays it minus the
oracle paths onto a fresh template with the vetted oracle on top, `own` runs the
clone as the candidate left it, and `ablate` replays only what is outside the
writable set onto the bare template. Every gate holds the run's one marker for
its whole length and leaves the deciding segment's output and exit code beside
the tree it ran in.
"""
import time
from dataclasses import dataclass
from pathlib import Path

from eval_harness.records import GATE_KEYS, REQUIRED_GATES
from eval_harness.runner import CommandResult, OrphanError, gate_lock, run_bounded
from eval_harness.trees import (
    apply_patch,
    commit_all,
    fresh_clone,
    hash_paths,
    mise_trust,
    overlay_oracle,
    snapshot,
)


class GateError(RuntimeError):
    """Raised when the candidate's diff.patch does not apply. str() names the gate."""


@dataclass(frozen=True)
class GateSite:
    """Where one attempt's gates run and what they are allowed to touch."""
    attempt_dir: Path
    run_dir: Path
    task_dir: Path
    shape: str
    writable: tuple[str, ...]
    oracle: tuple[str, ...]
    test_cmd: tuple[str, ...]
    gate_bound_s: float


def observe(site: GateSite, sealed: dict, necessity: dict) -> dict:
    """Record the candidate's work: the change list, the strays, the drops, the oracle.

    Writes `diff.patch` (zero bytes when nothing changed) and runs no command.
    """
    clone = site.attempt_dir / "clone"
    changed, diff_text = snapshot(clone, sealed["head_sha"])
    (site.attempt_dir / "diff.patch").write_bytes(diff_text.encode("utf-8", "surrogateescape"))
    touched = {record["path"] for record in changed}
    touched |= {record["old_path"] for record in changed if record["old_path"]}
    allowed = set(site.writable) | set(site.oracle)
    dropped = [
        path for path in site.writable
        if path not in touched and necessity.get(path, {}).get("holds") is True
    ]
    oracle_intact = None
    if site.shape == "tdd":
        oracle_intact = hash_paths(clone, site.oracle) == sealed["oracle"]
    return {
        "changed": changed,
        "stray": sorted(touched - allowed),
        "dropped": sorted(dropped),
        "oracle_intact": oracle_intact,
    }


def _clone(site: GateSite, name: str) -> Path:
    """A fresh copy of the sealed template under the attempt, trusted before it runs."""
    clone = fresh_clone(site.task_dir / "template", site.attempt_dir / name)
    mise_trust(clone)
    return clone


def _replay(site: GateSite, label: str, clone: Path, exclude: tuple[str, ...]) -> None:
    """Apply the candidate's patch minus `exclude`; an empty patch is nothing to apply."""
    patch = site.attempt_dir / "diff.patch"
    if patch.stat().st_size == 0:
        return
    result = apply_patch(clone, patch, exclude=exclude)
    if result.rc != 0:
        raise GateError("%s: diff.patch does not apply (rc %s)" % (label, result.rc))


def _run(site: GateSite, label: str, cwd: Path) -> CommandResult:
    """Run the test command in `cwd`, one deadline over the segment list.

    Each segment is one argv element, never read by this process's shell. The
    deciding segment's output lands in `<label>.txt` and its exit code in
    `<label>.rc`, both before the tree is checked for survivors.
    """
    output = site.attempt_dir / (label + ".txt")
    started = time.monotonic()
    result = None
    for segment in site.test_cmd:
        remaining = site.gate_bound_s - (time.monotonic() - started)
        result, tree = run_bounded(["bash", "-lc", segment], cwd, remaining, stdout_path=output)
        rc_text = "timeout\n" if result.timed_out else "%d\n" % result.rc
        (site.attempt_dir / (label + ".rc")).write_text(rc_text, encoding="utf-8")
        if tree.survivors():
            raise OrphanError("%s: the process group still has members" % segment)
        if result.rc != 0:
            return result
    return result


def run_baseline(site: GateSite) -> CommandResult:
    """The vetted oracle against the sealed template, in this attempt's own tree."""
    with gate_lock(site.run_dir, "baseline"):
        clone = _clone(site, "baseline-clone")
        overlay_oracle(site.task_dir, clone, site.oracle)
        return _run(site, "baseline", clone)


def run_gate(site: GateSite) -> CommandResult:
    """The candidate's non-oracle work under the vetted oracle, on a fresh template."""
    with gate_lock(site.run_dir, "gate"):
        clone = _clone(site, "gate-clone")
        if site.shape == "tdd":
            overlay_oracle(site.task_dir, clone, site.oracle)
            commit_all(clone, "tdd: the vetted oracle the candidate works against")
        _replay(site, "gate", clone, site.oracle)
        overlay_oracle(site.task_dir, clone, site.oracle)
        return _run(site, "gate", clone)


def run_own(site: GateSite) -> CommandResult:
    """The candidate's clone as it was left, nothing put back and nothing replayed."""
    with gate_lock(site.run_dir, "own"):
        return _run(site, "own", site.attempt_dir / "clone")


def run_ablate(site: GateSite) -> CommandResult:
    """The candidate's work outside the writable set, on the bare template."""
    with gate_lock(site.run_dir, "ablate"):
        clone = _clone(site, "ablate-clone")
        _replay(site, "ablate", clone, site.writable)
        return _run(site, "ablate", clone)


_GATES = {"gate": run_gate, "own": run_own, "ablate": run_ablate}


def run_gates(site: GateSite) -> dict:
    """Every gate the shape requires, in the contract's order; the rest None."""
    required = REQUIRED_GATES[site.shape]
    return {
        name: _GATES[name](site).as_json() if name in required else None
        for name in GATE_KEYS
    }

"""The evidence bundle of the qwen evaluation harness: sealing inputs, verifying restores.

Sealing writes every input a later run consumes under its task directory and
signs what landed on disk, so nothing moves between vet and run unnoticed.
Verifying reads a bundle back and prints one line per finding: no git, no
subprocess, no network, and it writes nothing, so a restored backup is either
proven intact or told exactly where it is not.
"""
import hashlib
import json
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from eval_harness.evidence_verify import check_artifacts
from eval_harness.prompts import SHAPES, load_dispatch_references, render_prompt
from eval_harness.records import RecordError, validate_record
from eval_harness.spec import Spec, classify_paths, load_spec
from eval_harness.trees import _git_bytes, build_manifest, build_template, contained, hash_paths

TDD_KEYS = ("architecture", "invariants", "read_anchors")

_REFERENCES_FILE = "dispatch-references.json"
_SEALED_DIRS = ("template", "oracle", "prompts")
_TASK_FILES = ("spec.json", "vetting.json", "pretask.json", "manifest.json", "canonical.patch",
               "template")
_MARKERS = ("complete.txt", "halted.txt")
_ATTEMPT_ID_RE = re.compile(r"[0-9]+-(qwen|sonnet|cmd1|cmd2)-a[12]")


class EvidenceError(RuntimeError):
    """Raised when a seal cannot be made or no longer holds. str() names the remedy."""


@dataclass(frozen=True)
class Seal:
    template_sha: str
    writable: tuple[str, ...]
    oracle: tuple[str, ...]
    shapes: tuple[str, ...]
    inputs_sha256: dict[str, str]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")


def _first_difference(found: dict, recorded: dict) -> str | None:
    """The first key, in sorted order, whose value differs or sits on one side only."""
    keys = sorted(set(found) | set(recorded))
    return next((key for key in keys if found.get(key) != recorded.get(key)), None)


# -- sealing ---------------------------------------------------------------


def default_shapes(task_dir: Path) -> tuple[str, ...]:
    """Both shapes when the raw spec carries every tdd key, else description alone.

    Presence is the whole test: whether the values hold up is sealing's job.
    """
    body = json.loads((Path(task_dir) / "spec.json").read_text(encoding="utf-8"))
    return SHAPES if all(key in body for key in TDD_KEYS) else ("description",)


def seal_inputs(evidence_dir: Path, task_dir: Path, shapes: Sequence[str]) -> Seal:
    """Seal every input a run of `task_dir` consumes and sign what is on disk.

    Nothing lands under the task directory until every requested prompt has
    rendered, so a refused shape leaves the task byte-identical.
    """
    evidence_dir, task_dir, shapes = Path(evidence_dir), Path(task_dir), tuple(shapes)
    if not shapes or len(set(shapes)) != len(shapes) or any(s not in SHAPES for s in shapes):
        raise EvidenceError("shapes: %r; pass one or both of %r, each once" % (shapes, SHAPES))
    if (evidence_dir / "runs").exists():
        raise EvidenceError("runs/ already exists in %s: a run consumed the current seal, so "
                            "seal into a fresh evidence directory" % evidence_dir)
    specs = {"description": load_spec(task_dir, "description")}
    if "tdd" in shapes:
        specs["tdd"] = load_spec(task_dir, "tdd")
    spec = specs["description"]
    base = "%s^" % spec.first
    listed = _git_bytes(spec.repo, "diff", "--name-only", "-z", base, spec.last).split(b"\0")
    changed = [path.decode("utf-8", "surrogateescape") for path in listed[:-1]]
    writable, oracle = classify_paths(changed, spec)
    if not writable:
        raise EvidenceError("writable: no non-test path changes between %s and %s; set "
                            "`writable` in spec.json" % (base, spec.last))
    rendered = {shape: render_prompt(specs[shape], shape, writable, oracle,
                                     load_dispatch_references(evidence_dir, shape=shape))
                for shape in shapes}
    template_sha = _write_seal(task_dir, spec, writable, oracle, rendered)
    return Seal(template_sha, tuple(writable), tuple(oracle), tuple(sorted(shapes)),
                inputs_sha256(evidence_dir, task_dir, shapes))


def _show(repo: Path, rev: str, relpath: str) -> bytes:
    """The bytes of `relpath` at `rev`; a path the commit does not hold is refused."""
    try:
        return _git_bytes(repo, "show", "%s:%s" % (rev, relpath))
    except subprocess.CalledProcessError as exc:
        raise EvidenceError("%s: not in the tree at %s; fix `oracle` in spec.json"
                            % (relpath, rev)) from exc


def _write_seal(task_dir: Path, spec: Spec, writable: list[str], oracle: list[str],
                rendered: dict[str, str]) -> str:
    """Replace the sealed set under `task_dir` wholesale; answer the template's sha."""
    for name in _SEALED_DIRS:
        if (task_dir / name).exists():
            shutil.rmtree(task_dir / name)
    template = task_dir / "template"
    template_sha = build_template(spec.repo, spec.first, template)
    pretask = {"head_sha": template_sha, "writable": hash_paths(template, writable),
               "oracle": hash_paths(template, oracle)}
    validate_record("pretask", pretask)
    _write_json(task_dir / "pretask.json", pretask)
    _write_json(task_dir / "manifest.json", build_manifest(template))
    base = "%s^" % spec.first
    (task_dir / "canonical.patch").write_bytes(
        _git_bytes(spec.repo, "diff", "--binary", base, spec.last, "--", *writable))
    (task_dir / "oracle").mkdir()
    for relpath in oracle:
        destination = contained(task_dir / "oracle", relpath)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_show(spec.repo, spec.last, relpath))
    (task_dir / "prompts").mkdir()
    for shape, text in rendered.items():
        (task_dir / "prompts" / ("%s.txt" % shape)).write_bytes(text.encode("utf-8"))
    return template_sha


# -- signing ---------------------------------------------------------------


def _input_files(shapes: Sequence[str]) -> dict[str, str]:
    """The sealed file behind each required label, as a task-relative slash path."""
    files = {"spec": "spec.json", "pretask": "pretask.json", "canonical_patch": "canonical.patch",
             "manifest": "manifest.json"}
    for shape in shapes:
        files["prompt:%s" % shape] = "prompts/%s.txt" % shape
    return files


def _oracle_sha256(oracle: Path) -> str:
    """Sign every file under oracle/ as one `<relpath>\\0<sha256>\\n` line, sorted."""
    entries = sorted(path.relative_to(oracle).as_posix()
                     for path in oracle.rglob("*") if path.is_file())
    lines = "".join("%s\0%s\n" % (relpath, _sha256((oracle / relpath).read_bytes()))
                    for relpath in entries)
    return _sha256(lines.encode("utf-8"))


def inputs_sha256(evidence_dir: Path, task_dir: Path, shapes: Sequence[str]) -> dict[str, str]:
    """Recompute, from disk, the digest of every input a run of `shapes` consumes."""
    evidence_dir, task_dir = Path(evidence_dir), Path(task_dir)
    digests = {}
    for label, relpath in _input_files(shapes).items():
        path = task_dir / relpath
        if not path.is_file():
            raise EvidenceError("%s: %s is missing; re-run vet to re-seal the task"
                                % (label, relpath))
        digests[label] = _sha256(path.read_bytes())
    references = evidence_dir / _REFERENCES_FILE
    digests["dispatch_references"] = (_sha256(references.read_bytes()) if references.is_file()
                                      else "absent")
    digests["oracle"] = _oracle_sha256(task_dir / "oracle")
    return digests


def recheck_inputs(evidence_dir: Path, task_dir: Path) -> dict[str, str]:
    """Prove the vetted seal still matches the disk, or name the first input that moved."""
    task_dir = Path(task_dir)
    try:
        vetting = json.loads((task_dir / "vetting.json").read_bytes())
    except (OSError, ValueError) as exc:
        raise EvidenceError("vetting.json: %s; run vet first" % exc) from exc
    found = inputs_sha256(evidence_dir, task_dir, vetting["shapes"])
    label = _first_difference(found, vetting["inputs_sha256"])
    if label is not None:
        raise EvidenceError("%s: changed since vetting; re-run vet" % label)
    return found


# -- verifying -------------------------------------------------------------


def _note(lines: list[str], path: str, keyword: str, detail: str = "") -> None:
    """Record one finding; the same line from two checks lands once."""
    line = ("%s: %s %s" % (path, keyword, detail)).rstrip()
    if line not in lines:
        lines.append(line)


def _load(lines: list[str], path: Path, where: str, check: Callable[[object], None]):
    """Parse the JSON at `path` and run `check` on it, or report `invalid` and answer None."""
    try:
        doc = json.loads(path.read_bytes())
        check(doc)
    except (OSError, ValueError) as exc:
        _note(lines, where, "invalid", str(exc))
        return None
    return doc


def _require_object(doc: object) -> None:
    if not isinstance(doc, dict):
        raise ValueError("not an object: %r" % doc)


def _check_vetting_record(record: dict) -> None:
    """A vetting record whose `shapes` and `inputs_sha256` a recheck can read."""
    validate_record("vetting", record)
    shapes, digests = record["shapes"], record["inputs_sha256"]
    if not isinstance(shapes, list) or not all(isinstance(shape, str) for shape in shapes):
        raise RecordError("vetting.shapes: %r" % shapes)
    if not isinstance(digests, dict):
        raise RecordError("vetting.inputs_sha256: %r" % digests)


def _check_sealed_doc(doc: object) -> None:
    """An object of task name -> label digests, and nothing else."""
    _require_object(doc)
    if not all(isinstance(entry, dict) for entry in doc.values()):
        raise ValueError("not an object of task -> digests: %r" % doc)


def _note_drift(lines: list[str], where: str, found: dict | None, recorded: dict,
                *words: str) -> None:
    """One `mismatch` line naming the first key, in sorted order, that differs."""
    label = None if found is None else _first_difference(found, recorded)
    if label is not None:
        _note(lines, where, "mismatch", " ".join((*words, label)))


def _recompute(lines: list[str], evidence_dir: Path, task: Path,
               shapes: Sequence[str]) -> dict[str, str] | None:
    """The seal as the disk holds it, or None after reporting every missing input."""
    missing = [relpath for relpath in _input_files(shapes).values()
               if not (task / relpath).is_file()]
    for relpath in missing:
        _note(lines, "tasks/%s/%s" % (task.name, relpath), "missing")
    return None if missing else inputs_sha256(evidence_dir, task, shapes)


def _check_manifest(lines: list[str], task: Path, prefix: str) -> None:
    """The template tree against the manifest that was sealed beside it."""
    where = prefix + "/manifest.json"
    if not (task / "manifest.json").exists() or not (task / "template").is_dir():
        return
    manifest = _load(lines, task / "manifest.json", where, _require_object)
    if manifest is not None:
        _note_drift(lines, where, build_manifest(task / "template"), manifest)


def _check_task(lines: list[str], evidence_dir: Path, task: Path) -> None:
    prefix = "tasks/%s" % task.name
    absent = {name for name in _TASK_FILES if not (task / name).exists()}
    for name in _TASK_FILES:
        if name in absent:
            _note(lines, "%s/%s" % (prefix, name), "missing")
    pretask = vetting = None
    if "pretask.json" not in absent:
        pretask = _load(lines, task / "pretask.json", prefix + "/pretask.json",
                        partial(validate_record, "pretask"))
    if "vetting.json" not in absent:
        vetting = _load(lines, task / "vetting.json", prefix + "/vetting.json",
                        _check_vetting_record)
    if (pretask is not None and vetting is not None
            and vetting["template_sha"] != pretask["head_sha"]):
        _note(lines, prefix + "/vetting.json", "mismatch", "template_sha")
    _check_manifest(lines, task, prefix)
    if vetting is not None:
        found = _recompute(lines, evidence_dir, task, vetting["shapes"])
        _note_drift(lines, prefix + "/vetting.json", found, vetting["inputs_sha256"])


def _check_sealed_inputs(lines: list[str], evidence_dir: Path, run: Path, prefix: str) -> None:
    """Every task the run claims to have consumed, against the seal on disk today."""
    where = prefix + "/sealed-inputs.json"
    if not (run / "sealed-inputs.json").exists():
        _note(lines, where, "missing")
        return
    sealed = _load(lines, run / "sealed-inputs.json", where, _check_sealed_doc)
    if sealed is None:
        return
    for name, recorded in sorted(sealed.items()):
        task = evidence_dir / "tasks" / name
        if not task.is_dir():
            _note(lines, where, "missing", name)
            continue
        shapes = [label[len("prompt:"):] for label in recorded if label.startswith("prompt:")]
        _note_drift(lines, where, _recompute(lines, evidence_dir, task, shapes), recorded, name)


def _read_marker(lines: list[str], path: Path, where: str) -> list[str] | None:
    """The attempt ids a marker lists in file order, or None after reporting a bad marker."""
    ids, headers = [], {}
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue
            if _ATTEMPT_ID_RE.fullmatch(line):
                ids.append(line)
            elif ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip()] = value.strip()
            else:
                raise ValueError("neither an attempt id nor a header: %r" % line)
        if headers.get("attempts") != str(len(ids)):
            raise ValueError("attempts: %r, but %d listed" % (headers.get("attempts"), len(ids)))
    except (OSError, ValueError) as exc:
        _note(lines, where, "invalid", str(exc))
        return None
    return ids


def _check_attempt(lines: list[str], where: Path, prefix: str) -> None:
    """One attempt directory: its record, its agreement with its name, its artifacts."""
    if not (where / "attempt.json").is_file():
        _note(lines, prefix, "missing")
        return
    record = _load(lines, where / "attempt.json", prefix + "/attempt.json",
                   partial(validate_record, "attempt"))
    if record is None:
        return
    number, engine, ordinal = where.name.split("-")
    expected = {"task": int(number), "engine": engine, "attempt": int(ordinal[1:])}
    for field, value in expected.items():
        if record[field] != value:
            _note(lines, prefix + "/attempt.json", "mismatch", field)
            break
    check_artifacts(lines, where, prefix, record, _note)


def _check_attempts(lines: list[str], run: Path, prefix: str) -> None:
    """The run's inventory against its attempt directories, never entering a clone."""
    present = sorted(path.name for path in run.iterdir()
                     if path.is_dir() and _ATTEMPT_ID_RE.fullmatch(path.name))
    marker = next((name for name in _MARKERS if (run / name).is_file()), None)
    if marker is None:
        _note(lines, prefix, "interrupted")
        inventory = None
    else:
        inventory = _read_marker(lines, run / marker, "%s/%s" % (prefix, marker))
    if inventory is None:
        # No inventory to hold the run to: what carries a record is checked, nothing is extra.
        for name in present:
            if (run / name / "attempt.json").is_file():
                _check_attempt(lines, run / name, "%s/%s" % (prefix, name))
        return
    for name in inventory:
        _check_attempt(lines, run / name, "%s/%s" % (prefix, name))
    for name in present:
        if name not in inventory:
            _note(lines, "%s/%s" % (prefix, name), "extra")


def _check_run(lines: list[str], evidence_dir: Path, run: Path) -> None:
    prefix = "runs/%s" % run.name
    if (run / "run.json").exists():
        _load(lines, run / "run.json", prefix + "/run.json", partial(validate_record, "run"))
    else:
        _note(lines, prefix + "/run.json", "missing")
    _check_sealed_inputs(lines, evidence_dir, run, prefix)
    _check_attempts(lines, run, prefix)


def verify(evidence_dir: Path) -> int:
    """Print one `<path>: <keyword>[ <detail>]` line per finding; 0 when clean, else 1.

    Tasks are checked before runs, each in sorted order. A missing or invalid
    file is reported once and the checks that need it are skipped; every other
    check still runs.
    """
    evidence_dir = Path(evidence_dir)
    lines: list[str] = []
    tasks = evidence_dir / "tasks"
    if tasks.is_dir():
        for task in sorted(path for path in tasks.iterdir() if path.is_dir()):
            _check_task(lines, evidence_dir, task)
    else:
        _note(lines, "tasks", "missing")
    runs = evidence_dir / "runs"
    if runs.is_dir():
        for run in sorted(path for path in runs.iterdir() if path.is_dir()):
            _check_run(lines, evidence_dir, run)
    for line in lines:
        print(line)
    return 1 if lines else 0

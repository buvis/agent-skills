"""What a run checks before its first attempt, and again right before each dispatch.

The run id has to be one directory name and the roster one or two distinct
engines before anything is written. Each task's sealed prompt is copied once
into the run dir, and an attempt's copy of it has to hash to the digest
run.json recorded, immediately before its engine is dispatched. /props is
probed at the URL pi's models.json maps the provider name to, and a tdd run's
versions carry the sealed dispatch references. Nothing here imports attempt.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path

from eval_harness import engines, prompts, records

_SEPARATORS = ("/", "\\", os.sep, "\0")


def check_run_id(run_id: str) -> str | None:
    """The refusal for a run id that is not exactly one directory name, else None."""
    lone = run_id not in ("", ".", "..") and not any(mark in run_id for mark in _SEPARATORS)
    if lone and Path(run_id).name == run_id:
        return None
    return "--run-id %r is not one directory name" % run_id


def check_engines(ids: list[str]) -> str | None:
    """The refusal for a roster of mapped engine ids, else None: one or two, no id twice."""
    if not ids:
        return "--engines names no engine"
    if len(ids) > 2:
        return "--engines names %d engines; a run takes at most two" % len(ids)
    repeated = [engine_id for engine_id in ids if ids.count(engine_id) > 1]
    if repeated:
        return "--engines names %s twice" % repeated[0]
    return None


def copy_run_prompts(task_dirs: list[Path], shape: str, run_dir: Path) -> None:
    """One run-level prompt per task: the sealed `prompts/<shape>.txt` bytes, never re-rendered."""
    for task_dir in task_dirs:
        shutil.copyfile(task_dir / "prompts" / ("%s.txt" % shape),
                        run_dir / ("%s.prompt.txt" % task_dir.name))


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prompt_moved(attempt_dir: Path, run_dir: Path, task_id: int) -> bool:
    """True when `<attempt_dir>/prompt.txt` no longer hashes to the digest run.json recorded."""
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    recorded = next(task["prompt_sha256"] for task in run["tasks"] if task["id"] == task_id)
    return hash_file(attempt_dir / "prompt.txt") != recorded


def build_server_block(ids: list[str], settings: engines.EngineSettings) -> dict:
    """run.json's server block: /props at the provider's configured URL, else nulls and why."""
    effort = settings.server_reasoning_effort
    if "qwen" not in ids:
        return dict(dict.fromkeys(records.SERVER_KEYS), declared_effort=effort)
    url = engines.resolve_provider_url(settings.qwen_provider)
    if url is not None:
        return engines.fetch_server_props(url, effort)
    return dict(dict.fromkeys(records.SERVER_KEYS), declared_effort=effort,
                metadata_error="provider %r not found in %s" % (settings.qwen_provider,
                                                                 engines.models_json_path()))


def merge_versions(ids: list[str], settings: engines.EngineSettings, shape: str,
                   evidence_dir: Path) -> dict[str, str | None]:
    """The probed CLI versions, with the sealed references' versions on top for a tdd run."""
    versions = engines.record_versions(ids, settings)
    if shape != "tdd":
        return versions
    references = prompts.load_dispatch_references(evidence_dir, shape="tdd")
    return {**versions, **{reference.name: reference.version for reference in references}}

"""The field domains of the run, pretask, sealed and server records.

The key sets stay in records.py; this module judges the values behind them.
records.py imports it lazily inside validate_record, so the helpers below can
be imported here at load time without closing a cycle.
"""
import re

from eval_harness.records import (
    _ENGINES,
    SERVER_KEYS,
    _check_keys,
    _is_int,
    _is_native_absolute,
    _is_path,
    _is_path_list,
    _is_stamp,
    _require,
)

_ENGINE_KEYS = ("id", "command")
_TASK_KEYS = ("id", "slug", "repo", "kind", "writable", "oracle", "prompt_sha256")
_TASK_KINDS = ("single-file", "multi-file")
_SERVER_TEXT_KEYS = ("model_alias", "build_info", "declared_effort", "metadata_error")

_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _is_nonempty_str(value: object) -> bool:
    return isinstance(value, str) and value != ""


def _check_template(record: dict, where: str) -> None:
    """pretask and sealed: a head and the digest, or absence, of every sealed path."""
    _require(_is_nonempty_str(record["head_sha"]), where + ".head_sha", record["head_sha"])
    for name in ("writable", "oracle"):
        digests = record[name]
        _require(isinstance(digests, dict), where + "." + name, digests)
        for path, digest in digests.items():
            _require(_is_path(path), where + "." + name + " key", path)
            _require(digest == "absent" or _is_digest(digest), where + "." + name, digest)


def _check_server(server: object, where: str) -> None:
    """The probed server block: every field may be null, a run without qwen probes none."""
    _check_keys(server, SERVER_KEYS, where)
    _require(server["n_ctx"] is None or _is_int(server["n_ctx"]), where + ".n_ctx",
             server["n_ctx"])
    for name in _SERVER_TEXT_KEYS:
        _require(server[name] is None or isinstance(server[name], str), where + "." + name,
                 server[name])
    _require(server["sampling"] is None or isinstance(server["sampling"], dict),
             where + ".sampling", server["sampling"])
    flag = server["supports_reasoning_effort"]
    _require(flag is None or isinstance(flag, bool), where + ".supports_reasoning_effort", flag)


def _check_run_task(task: object) -> None:
    _check_keys(task, _TASK_KEYS, "run.tasks[]")
    _require(_is_int(task["id"]), "run.tasks[].id", task["id"])
    _require(_is_nonempty_str(task["slug"]), "run.tasks[].slug", task["slug"])
    _require(_is_native_absolute(task["repo"]), "run.tasks[].repo", task["repo"])
    _require(task["kind"] in _TASK_KINDS, "run.tasks[].kind", task["kind"])
    _require(_is_path_list(task["writable"]), "run.tasks[].writable", task["writable"])
    _require(_is_path_list(task["oracle"]), "run.tasks[].oracle", task["oracle"])
    _require(_is_digest(task["prompt_sha256"]), "run.tasks[].prompt_sha256",
             task["prompt_sha256"])


def _check_run(record: dict) -> None:
    version = record["schema_version"]
    _require(_is_int(version) and version == 1, "run.schema_version", version)
    _require(_is_nonempty_str(record["run_id"]), "run.run_id", record["run_id"])
    _require(_is_stamp(record["started"]), "run.started", record["started"])
    _require(isinstance(record["config"], dict), "run.config", record["config"])
    _require(isinstance(record["engines"], list), "run.engines", record["engines"])
    for engine in record["engines"]:
        _check_keys(engine, _ENGINE_KEYS, "run.engines[]")
        _require(engine["id"] in _ENGINES, "run.engines[].id", engine["id"])
        _require(_is_nonempty_str(engine["command"]), "run.engines[].command", engine["command"])
    _require(isinstance(record["tasks"], list), "run.tasks", record["tasks"])
    for task in record["tasks"]:
        _check_run_task(task)
    versions = record["versions"]
    _require(isinstance(versions, dict)
             and all(v is None or isinstance(v, str) for v in versions.values()),
             "run.versions", versions)
    _check_server(record["server"], "run.server")


CHECKS = {"run": _check_run,
          "pretask": lambda record: _check_template(record, "pretask"),
          "sealed": lambda record: _check_template(record, "sealed"),
          "server": lambda record: _check_server(record, "server")}

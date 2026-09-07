"""The record contract of the qwen evaluation harness.

Pure data: no git, no subprocess, no network, no filesystem. Every record the
harness writes passes through validate_record, and a stored attempt carries
everything derive_validity and classify need to rederive its verdict.
"""
import re

PRETASK_KEYS = ("head_sha", "writable", "oracle")
SEALED_KEYS = ("head_sha", "writable", "oracle")
VETTING_KEYS = ("template_sha", "gate_bound_s", "warmup", "baseline", "necessity",
                "canonical", "inputs_sha256", "shapes", "ready")
COMMAND_RESULT_KEYS = ("rc", "timed_out", "first_failure", "failure_kind", "wall_s")
ENGINE_RUN_KEYS = ("argv", "launch", "exit", "timed_out", "wall_s", "identity", "completion",
                   "final_message_bytes", "usage_limit", "first_edit_s", "usage")
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
              "cost_usd")
GATE_KEYS = ("gate", "own", "ablate")
ATTEMPT_KEYS = ("task", "engine", "attempt", "shape", "clone", "prep", "baseline", "engine_run",
                "validity", "changed", "stray", "oracle_intact", "dropped", "gates", "outcome",
                "class", "started", "finished")
RUN_KEYS = ("schema_version", "run_id", "started", "config", "engines", "tasks", "versions",
            "server")
SERVER_KEYS = ("n_ctx", "model_alias", "build_info", "sampling", "supports_reasoning_effort",
               "declared_effort", "metadata_error")
RECORD_KINDS = ("attempt", "run", "pretask", "sealed", "vetting", "command_result", "engine_run",
                "usage", "server")
REQUIRED_GATES = {"tdd": ("gate",), "description": ("gate", "own", "ablate")}

_KEYS = {"attempt": ATTEMPT_KEYS, "run": RUN_KEYS, "pretask": PRETASK_KEYS, "sealed": SEALED_KEYS,
         "vetting": VETTING_KEYS, "command_result": COMMAND_RESULT_KEYS,
         "engine_run": ENGINE_RUN_KEYS, "usage": USAGE_KEYS, "server": SERVER_KEYS}
_PREP_KEYS = ("status", "differing_paths")
_CHANGED_KEYS = ("status", "path", "old_path")
_NECESSITY_KEYS = ("result", "holds")

_ENGINES = ("qwen", "sonnet", "cmd1", "cmd2")
_SHAPES = ("tdd", "description")
_ATTEMPTS = (1, 2)
_OUTCOMES = ("PASS", "FAIL", "TIMEOUT", "SUSPECT", "DISCARDED")
_FAIL_CLASSES = ("test-mutation", "stray-edit", "no-edit", "dropped-a-file", "vacuous-tests",
                 "logic-error")
_PREP_STATUSES = ("ok", "PREP_MISMATCH")
_FAILURE_KINDS = ("test", "tool", "unknown", None)
_LAUNCHES = ("started", "not-started", "unknown")
_COMPLETIONS = ("complete", "incomplete", "unknown")
_USAGE_LIMITS = ("clear", "hit", "unchecked")
_DISCARD_REASONS = ("prep", "baseline", "harness", "timeout", "usage-limit", "identity",
                    "incomplete")
_EXPECTED_GATE = {"gate": True, "own": True, "ablate": False}

_STAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_STATUS_RE = re.compile(r"[ACDMTUXB]|[RC][0-9]{0,3}")
_PATH_RE = re.compile(r"[^/\\][^\\]*")
_EXIT_RE = re.compile(r"exit--?[0-9]+")


class RecordError(ValueError):
    """Raised when a record's key set or field domain violates the contract."""


def _require(ok: bool, field: str, value: object) -> None:
    if not ok:
        raise RecordError("%s: %r" % (field, value))


def _check_keys(record: object, keys: tuple, where: str) -> None:
    _require(isinstance(record, dict) and set(record) == set(keys), where + " keys", record)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return _is_int(value) or isinstance(value, float)


def _is_seconds(value: object) -> bool:
    return value is None or (_is_number(value) and value >= 0)


def _is_path(value: object) -> bool:
    """A relative, slash-form path: no leading slash, no backslash, not empty."""
    return isinstance(value, str) and bool(_PATH_RE.fullmatch(value))


def _is_path_list(value: object) -> bool:
    return isinstance(value, list) and all(_is_path(p) for p in value) and value == sorted(value)


def _is_stamp(value: object) -> bool:
    return isinstance(value, str) and bool(_STAMP_RE.fullmatch(value))


def _is_jsonable(value: object) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, list):
        return all(_is_jsonable(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _is_jsonable(v) for k, v in value.items())
    return False


def _is_validity(value: object) -> bool:
    if value == "VALID":
        return True
    if not isinstance(value, str) or not value.startswith("DISCARDED:"):
        return False
    reason = value[len("DISCARDED:"):]
    return reason in _DISCARD_REASONS or bool(_EXIT_RE.fullmatch(reason))


def _is_fail_class(outcome: object, fail_class: object) -> bool:
    """A class names a failure mode exactly when the outcome is a failure."""
    if outcome == "FAIL":
        return fail_class in _FAIL_CLASSES
    return fail_class is None


def is_valid_baseline(baseline: dict | None) -> bool:
    """True when a command result is a real, untimed test failure."""
    return (isinstance(baseline, dict)
            and baseline.get("failure_kind") == "test"
            and not baseline.get("timed_out")
            and _is_int(baseline.get("rc"))
            and baseline["rc"] != 0)


def _check_command_result(result: object, where: str) -> None:
    _check_keys(result, COMMAND_RESULT_KEYS, where)
    _require(result["rc"] is None or _is_int(result["rc"]), where + ".rc", result["rc"])
    _require(isinstance(result["timed_out"], bool), where + ".timed_out", result["timed_out"])
    _require(result["first_failure"] is None or isinstance(result["first_failure"], str),
             where + ".first_failure", result["first_failure"])
    _require(result["failure_kind"] in _FAILURE_KINDS, where + ".failure_kind",
             result["failure_kind"])
    _require(_is_seconds(result["wall_s"]), where + ".wall_s", result["wall_s"])


def _check_usage(usage: object) -> None:
    _check_keys(usage, USAGE_KEYS, "usage")
    for key, value in usage.items():
        if key == "cost_usd":
            ok = value is None or (_is_number(value) and value >= 0)
        else:
            ok = value is None or (_is_int(value) and value >= 0)
        _require(ok, "usage." + key, value)


def _check_engine_run(run: object) -> None:
    _check_keys(run, ENGINE_RUN_KEYS, "engine_run")
    _require(isinstance(run["argv"], list) and all(isinstance(a, str) for a in run["argv"]),
             "engine_run.argv", run["argv"])
    _require(run["launch"] in _LAUNCHES, "engine_run.launch", run["launch"])
    _require(run["exit"] is None or _is_int(run["exit"]), "engine_run.exit", run["exit"])
    _require(isinstance(run["timed_out"], bool), "engine_run.timed_out", run["timed_out"])
    _require(_is_seconds(run["wall_s"]), "engine_run.wall_s", run["wall_s"])
    _require(run["identity"] is None or isinstance(run["identity"], str), "engine_run.identity",
             run["identity"])
    _require(run["completion"] in _COMPLETIONS, "engine_run.completion", run["completion"])
    _require(run["final_message_bytes"] is None or _is_int(run["final_message_bytes"]),
             "engine_run.final_message_bytes", run["final_message_bytes"])
    _require(run["usage_limit"] in _USAGE_LIMITS, "engine_run.usage_limit", run["usage_limit"])
    _require(_is_seconds(run["first_edit_s"]), "engine_run.first_edit_s", run["first_edit_s"])
    _check_usage(run["usage"])


def _check_prep(prep: object) -> None:
    _check_keys(prep, _PREP_KEYS, "prep")
    _require(prep["status"] in _PREP_STATUSES, "prep.status", prep["status"])
    _require(_is_path_list(prep["differing_paths"]), "prep.differing_paths",
             prep["differing_paths"])


def _check_gates(gates: object) -> None:
    _check_keys(gates, GATE_KEYS, "gates")
    for name in GATE_KEYS:
        if gates[name] is not None:
            _check_command_result(gates[name], "gates." + name)


def _check_changed(changed: object) -> None:
    if changed is None:
        return
    _require(isinstance(changed, list), "attempt.changed", changed)
    for entry in changed:
        _check_keys(entry, _CHANGED_KEYS, "changed[]")
        status, old_path = entry["status"], entry["old_path"]
        _require(isinstance(status, str) and bool(_STATUS_RE.fullmatch(status)),
                 "changed[].status", status)
        _require(_is_path(entry["path"]), "changed[].path", entry["path"])
        if status[0] in "RC":
            _require(_is_path(old_path), "changed[].old_path", old_path)
        else:
            _require(old_path is None, "changed[].old_path", old_path)


def _check_attempt(record: dict) -> None:
    _require(_is_int(record["task"]), "attempt.task", record["task"])
    _require(record["engine"] in _ENGINES, "attempt.engine", record["engine"])
    _require(_is_int(record["attempt"]) and record["attempt"] in _ATTEMPTS, "attempt.attempt",
             record["attempt"])
    _require(record["shape"] in _SHAPES, "attempt.shape", record["shape"])
    _require(isinstance(record["clone"], str) and record["clone"].startswith("/"),
             "attempt.clone", record["clone"])
    _check_prep(record["prep"])
    if record["baseline"] is not None:
        _check_command_result(record["baseline"], "attempt.baseline")
    _check_engine_run(record["engine_run"])
    _require(_is_validity(record["validity"]), "attempt.validity", record["validity"])
    _check_changed(record["changed"])
    _require(record["stray"] is None or _is_path_list(record["stray"]), "attempt.stray",
             record["stray"])
    _require(record["dropped"] is None or _is_path_list(record["dropped"]), "attempt.dropped",
             record["dropped"])
    intact = record["oracle_intact"]
    _require(intact is None or isinstance(intact, bool), "attempt.oracle_intact", intact)
    _require(record["shape"] != "description" or intact is None, "attempt.oracle_intact", intact)
    _check_gates(record["gates"])
    _require(record["outcome"] in _OUTCOMES, "attempt.outcome", record["outcome"])
    _require(_is_fail_class(record["outcome"], record["class"]), "attempt.class", record["class"])
    _require(_is_stamp(record["started"]), "attempt.started", record["started"])
    _require(_is_stamp(record["finished"]), "attempt.finished", record["finished"])


def _check_vetting(record: dict) -> None:
    if record["baseline"] is not None:
        _check_command_result(record["baseline"], "vetting.baseline")
    _require(isinstance(record["warmup"], list), "vetting.warmup", record["warmup"])
    for result in record["warmup"]:
        _check_command_result(result, "vetting.warmup[]")
    _require(isinstance(record["necessity"], dict), "vetting.necessity", record["necessity"])
    for path, entry in record["necessity"].items():
        _require(_is_path(path), "vetting.necessity key", path)
        _check_keys(entry, _NECESSITY_KEYS, "necessity[]")
        if entry["result"] is not None:
            _check_command_result(entry["result"], "necessity[].result")
        _require(entry["holds"] is is_valid_baseline(entry["result"]), "necessity[].holds",
                 entry["holds"])


_CHECKS = {"attempt": _check_attempt, "vetting": _check_vetting, "engine_run": _check_engine_run,
           "usage": _check_usage,
           "command_result": lambda record: _check_command_result(record, "command_result")}


def validate_record(kind: str, record: dict) -> None:
    """Raise RecordError unless the record is a well-formed record of this kind."""
    _require(kind in RECORD_KINDS, "record kind", kind)
    _check_keys(record, _KEYS[kind], kind)
    for key, value in record.items():
        _require(_is_jsonable(value), "%s.%s" % (kind, key), value)
    check = _CHECKS.get(kind)
    if check:
        check(record)


def _ran_to_completion(run: dict) -> bool:
    return (run["launch"] == "started"
            and run["completion"] == "complete"
            and _is_int(run["final_message_bytes"]) and run["final_message_bytes"] > 0
            and run["exit"] == 0
            and run["usage_limit"] == "clear")


def derive_validity(record: dict) -> str:
    """Walk the rejection ladder over the stored evidence."""
    run = record["engine_run"]
    if record["prep"]["status"] != "ok":
        return "DISCARDED:prep"
    if not is_valid_baseline(record["baseline"]):
        return "DISCARDED:baseline"
    if run["launch"] == "not-started":
        return "DISCARDED:harness"
    if run["timed_out"]:
        return "DISCARDED:timeout"
    if run["usage_limit"] == "hit":
        return "DISCARDED:usage-limit"
    if _is_int(run["exit"]) and run["exit"] != 0:
        return "DISCARDED:exit-%d" % run["exit"]
    if run["identity"] is None:
        return "DISCARDED:identity"
    if _ran_to_completion(run):
        return "VALID"
    return "DISCARDED:incomplete"


def _verdict(result: dict | None) -> bool | None:
    """True when the command passed, False when tests failed, None when unusable."""
    if result is None or result["timed_out"]:
        return None
    if result["rc"] == 0:
        return True
    return False if is_valid_baseline(result) else None


def _judge_evidence(record: dict) -> tuple[str, str | None] | None:
    """The candidate's behaviour, in precedence order. Null evidence is undecidable."""
    if record["shape"] == "tdd" and record["oracle_intact"] is None:
        return ("SUSPECT", None)
    if record["oracle_intact"] is False:
        return ("FAIL", "test-mutation")
    if record["stray"] is None:
        return ("SUSPECT", None)
    if record["stray"]:
        return ("FAIL", "stray-edit")
    if record["changed"] is None:
        return ("SUSPECT", None)
    if not record["changed"]:
        return ("FAIL", "no-edit")
    if record["dropped"] is None:
        return ("SUSPECT", None)
    if record["dropped"]:
        return ("FAIL", "dropped-a-file")
    return None


def _judge_gates(record: dict) -> tuple[str, str | None]:
    gates = record["gates"]
    verdicts = {name: _verdict(gates[name]) for name in REQUIRED_GATES[record["shape"]]}
    if any(verdict is None for verdict in verdicts.values()):
        return ("SUSPECT", None)
    if verdicts.get("ablate") is True:
        return ("FAIL", "vacuous-tests")
    if all(verdicts[name] is _EXPECTED_GATE[name] for name in verdicts):
        return ("PASS", None)
    return ("FAIL", "logic-error")


def classify(record: dict) -> tuple[str, str | None]:
    """Rederive (outcome, class) from the evidence, ignoring the stored verdict."""
    gates = record["gates"]
    if record["engine_run"]["timed_out"]:
        return ("TIMEOUT", None)
    measured = [record["baseline"]] + [gates[name] for name in GATE_KEYS]
    if any(result is not None and result["timed_out"] for result in measured):
        return ("SUSPECT", None)
    if derive_validity(record) != "VALID":
        return ("DISCARDED", None)
    return _judge_evidence(record) or _judge_gates(record)

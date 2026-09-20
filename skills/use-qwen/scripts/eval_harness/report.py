"""Renders evidence.md, report.md and audit-queue.md for a completed run.

Pure filesystem + JSON in, three markdown files out. Every stored attempt
record is rederived through records.derive_validity and records.classify
before it is trusted: a mismatch between the stored and the rederived
outcome, a malformed audit.jsonl line, or a duplicate attempt_dir refuses
the whole render rather than writing anything. Content is built fully in
memory first, so a refused render never touches the three output files.
"""
import json
import math
import shlex
from pathlib import Path

from eval_harness import admission, records, spec

_AUDIT_ROW_KEYS = frozenset({"attempt_dir", "verdict", "claim", "evidence", "review_verdict",
                             "review_findings", "review_effort_s"})
# The record field whose value decided each FAIL class, traced from
# records._judge_evidence/_judge_gates.
_CLASS_FIELD = {
    "test-mutation": "oracle_intact", "stray-edit": "stray", "no-edit": "changed",
    "dropped-a-file": "dropped", "vacuous-tests": "gates.ablate", "logic-error": "gates",
}
# Sibling files inside an attempt directory, alongside attempt.json.
_OUT_FILE = "out.txt"
_WRAPPER_FILE = "wrapper.txt"
_GATE_OUT_FILE = "gate.txt"
_SESSION_LOG_FILE = "session.jsonl"


def _load_entries(run_dir: Path, engine_order: list) -> list:
    entries = []
    for child in sorted(run_dir.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        stem, _, attempt_str = child.name.rpartition("-a")
        task_str, _, engine = stem.partition("-")
        record_path = child / "attempt.json"
        record = None
        if record_path.is_file():
            try:
                record = json.loads(record_path.read_text(encoding="utf-8"))
            except ValueError as exc:
                raise ValueError(
                    "attempt %s: malformed attempt.json: %s" % (child.name, exc)) from exc
            try:
                records.validate_record("attempt", record)
            except records.RecordError as exc:
                raise ValueError("attempt %s: %s" % (child.name, exc)) from exc
            identity = (record["task"], record["engine"], record["attempt"])
            if identity != (int(task_str), engine, int(attempt_str)):
                raise ValueError(
                    "attempt %s: record identity (task=%r, engine=%r, attempt=%r) does not "
                    "match its directory name" % (child.name, *identity))
            derived = records.classify(record)
            stored = (record["outcome"], record["class"])
            if derived != stored:
                raise ValueError(
                    "attempt %s: stored outcome/class %r does not match "
                    "records.classify %r" % (child.name, stored, derived))
        entries.append({
            "id": child.name, "task": int(task_str), "engine": engine,
            "attempt": int(attempt_str), "record": record,
        })
    entries.sort(key=lambda e: (e["task"], engine_order.index(e["engine"]), e["attempt"]))
    return entries


def _reject_json_constant(name: str) -> None:
    """json.loads otherwise accepts the non-JSON tokens NaN, Infinity and -Infinity."""
    raise ValueError("nonstandard JSON constant %s" % name)


def _audit_error(lineno: int, line: str, reason: str) -> ValueError:
    return ValueError("audit.jsonl line %d: %s: %r" % (lineno, reason, line))


def _check_audit_row(lineno: int, line: str, row: dict, valid_id_set: set) -> str:
    """Refuse a row whose keys or values break the contract; returns its attempt_dir."""
    if set(row) != _AUDIT_ROW_KEYS:
        raise _audit_error(lineno, line, "missing/extra key (%s)"
                           % sorted(row.keys() ^ _AUDIT_ROW_KEYS))
    aid = row["attempt_dir"]
    if not isinstance(aid, str):
        raise _audit_error(lineno, line, "non-string attempt_dir")
    if aid not in valid_id_set:
        raise _audit_error(lineno, line, "audits unknown/non-VALID attempt %r" % aid)
    if row["verdict"] not in ("clean", "flagged", "unverifiable"):
        raise _audit_error(lineno, line, "invalid verdict %r" % row["verdict"])
    if row["review_verdict"] not in ("clean", "blocking", "unverifiable"):
        raise _audit_error(lineno, line, "invalid review_verdict %r" % row["review_verdict"])
    claim, evidence = row["claim"], row["evidence"]
    if not (isinstance(claim, str) and isinstance(evidence, str)):
        raise _audit_error(lineno, line, "non-string claim/evidence")
    if row["verdict"] == "flagged" and not (claim and evidence):
        raise _audit_error(lineno, line, "flags without a claim/evidence")
    findings = row["review_findings"]
    if not (isinstance(findings, list) and all(isinstance(f, str) for f in findings)):
        raise _audit_error(lineno, line, "non-string-list review_findings")
    if row["review_verdict"] == "blocking" and not findings:
        raise _audit_error(lineno, line, "blocking with no review_findings")
    effort = row["review_effort_s"]
    numeric = isinstance(effort, (int, float)) and not isinstance(effort, bool)
    # An int is always finite; math.isfinite raises OverflowError on one of 2**1024 or more.
    finite = isinstance(effort, int) or (numeric and math.isfinite(effort))
    if effort is not None and not (numeric and effort >= 0 and finite):
        raise _audit_error(lineno, line, "invalid review_effort_s")
    return aid


def load_audit(run_dir: Path, valid_ids: list) -> dict:
    """audit.jsonl rows keyed by attempt_dir; every row is checked before any is trusted."""
    audit_path = run_dir / "audit.jsonl"
    rows = {}
    if not audit_path.is_file():
        return rows
    valid_id_set = set(valid_ids)
    for lineno, line in enumerate(audit_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, parse_constant=_reject_json_constant)
        except ValueError as exc:
            raise _audit_error(lineno, line, "malformed JSON") from exc
        if not isinstance(row, dict):
            raise _audit_error(lineno, line, "not a JSON object")
        aid = _check_audit_row(lineno, line, row, valid_id_set)
        if aid in rows:
            raise _audit_error(lineno, line, "duplicate attempt_dir %s" % aid)
        rows[aid] = row
    return rows


def _find_task_dir(root: Path, task: dict) -> Path | None:
    tasks_dir = root / "tasks"
    if not tasks_dir.is_dir():
        return None
    for child in sorted(tasks_dir.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        try:
            parsed = spec.parse_task_dir(child)
        except spec.SpecError:
            continue
        if parsed == (task["id"], task["slug"]):
            return child
    return None


def _load_vetting(root: Path, task: dict) -> dict | None:
    task_dir = _find_task_dir(root, task)
    if task_dir is None:
        return None
    path = task_dir / "vetting.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _group_by_task_engine(entries: list) -> dict:
    groups = {}
    for entry in entries:
        groups.setdefault((entry["task"], entry["engine"]), []).append(entry)
    return groups


def _effective(group: list) -> tuple:
    """(outcome, class, attempts) for a task+engine's last numbered attempt."""
    if not group:
        return "NOT_STARTED", None, 0
    last = max(group, key=lambda e: e["attempt"])
    if last["record"] is None:
        return "INCOMPLETE", None, len(group)
    return last["record"]["outcome"], last["record"]["class"], len(group)


def _or(value, fallback: str):
    return fallback if value is None else value


def _path_list(paths) -> str:
    return ", ".join(paths) if paths else "none"


def _read_sibling(attempt_dir: Path, name: str) -> str | None:
    path = attempt_dir / name
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _vetting_lines(vetting: dict, indent: str) -> list:
    baseline, canonical = vetting["baseline"], vetting["canonical"]
    lines = ["%sbaseline rc: %s" % (indent, _or(baseline["rc"], "unavailable") if baseline
                                     else "unavailable")]
    lines.append("%scanonical rc: %s" % (indent, _or(canonical["rc"], "unavailable") if canonical
                                          else "unavailable"))
    for path, necessity in sorted(vetting["necessity"].items()):
        lines.append("%snecessity %s: holds=%s" % (indent, path, necessity["holds"]))
    return lines


def _setup_block(vetting: dict | None) -> list:
    lines = ["## Setup", ""]
    if vetting is None:
        return lines + ["vetting.json: unavailable", ""]
    lines.append("template_sha: %s" % vetting["template_sha"])
    for i, warmup in enumerate(vetting["warmup"], 1):
        lines.append("warmup[%d] rc: %s" % (i, _or(warmup["rc"], "unavailable")))
    lines += _vetting_lines(vetting, "")
    lines.append("")
    return lines


def _incomplete_attempt_block(entry: dict) -> list:
    return [
        "### %s attempt %d" % (entry["engine"], entry["attempt"]), "",
        "Attempt: %s" % entry["id"],
        "Tree: n/a", "Dispatch: n/a", "Engine identity: n/a",
        "Captured output: n/a", "Dispatch exit code: n/a | Dispatch validity: n/a",
        "Baseline exit code: n/a; first failure: n/a",
        "Files changed: n/a | dropped: n/a | stray: n/a",
        "Own/gate/ablation exit codes: n/a / n/a / n/a",
        "Result: INCOMPLETE", "",
    ]


def _attempt_block(entry: dict, run_dir: Path) -> list:
    record = entry["record"]
    if record is None:
        return _incomplete_attempt_block(entry)

    attempt_dir = run_dir / entry["id"]
    engine_run, baseline, gates = record["engine_run"], record["baseline"], record["gates"]
    out_path = attempt_dir / _OUT_FILE
    out_bytes = out_path.stat().st_size if out_path.is_file() else None
    wrapper_path = attempt_dir / _WRAPPER_FILE
    wrapper_bytes = wrapper_path.stat().st_size if wrapper_path.is_file() else None
    changed = [c["path"] for c in record["changed"]] if record["changed"] else []
    result = record["outcome"] if record["class"] is None else "%s:%s" % (
        record["outcome"], record["class"])

    return [
        "### %s attempt %d" % (record["engine"], record["attempt"]), "",
        "Attempt: %s" % entry["id"],
        "Tree: %s" % record["clone"],
        "Dispatch: `%s`" % shlex.join(engine_run["argv"]),
        "Engine identity: `%s`" % _or(engine_run["identity"], "n/a"),
        "Captured output: %s (%s bytes), %s (%s bytes)" % (
            out_path, _or(out_bytes, "unavailable"),
            wrapper_path, _or(wrapper_bytes, "unavailable")),
        "Dispatch exit code: %s | Dispatch validity: %s" % (
            _or(engine_run["exit"], "n/a"), records.derive_validity(record)),
        "Baseline exit code: %s; first failure: `%s`" % (
            _or(baseline["rc"], "n/a") if baseline else "n/a",
            _or(baseline["first_failure"], "n/a") if baseline else "n/a"),
        "Files changed: %s | dropped: %s | stray: %s" % (
            _path_list(changed), _path_list(record["dropped"]), _path_list(record["stray"])),
        "Own/gate/ablation exit codes: %s / %s / %s" % (
            _or(gates["own"]["rc"], "n/a") if gates["own"] else "n/a",
            _or(gates["gate"]["rc"], "n/a") if gates["gate"] else "n/a",
            _or(gates["ablate"]["rc"], "n/a") if gates["ablate"] else "n/a"),
        "Result: %s" % result, "",
        "<details><summary>engine output</summary>", "",
        _or(_read_sibling(attempt_dir, _OUT_FILE), "unavailable"), "",
        "</details>",
        "<details><summary>gate output</summary>", "",
        _or(_read_sibling(attempt_dir, _GATE_OUT_FILE), "unavailable"), "",
        "</details>", "",
    ]


def _evidence_md(run: dict, entries: list, run_dir: Path, vetting_by_task: dict) -> str:
    lines = ["run_id: %s" % run["run_id"], "started: %s" % run["started"]]
    for key, value in sorted(run["config"].items()):
        lines.append("config.%s: %s" % (key, value))
    for key, value in sorted(run["versions"].items()):
        lines.append("version.%s: %s" % (key, _or(value, "unavailable")))
    lines.append("")

    by_task = {}
    for entry in entries:
        by_task.setdefault(entry["task"], []).append(entry)

    for task in run["tasks"]:
        lines.append("## Task %d: %s" % (task["id"], task["slug"]))
        lines.append("")
        lines.append("Repo: %s | Kind: %s" % (task["repo"], task["kind"]))
        lines.append("")
        lines += _setup_block(vetting_by_task.get(task["id"]))
        for entry in by_task.get(task["id"], []):
            lines += _attempt_block(entry, run_dir)
    return "\n".join(lines) + "\n"


def _run_section(run: dict, engine_order: list) -> list:
    lines = ["## Run", "", "run_id: %s" % run["run_id"], "started: %s" % run["started"],
             "tasks: %d" % len(run["tasks"]), "engines: %s" % ", ".join(engine_order), ""]
    lines.append("### Flags")
    for key, value in sorted(run["config"].items()):
        lines.append("%s: %s" % (key, value))
    lines.append("")
    lines.append("### Versions")
    for key, value in sorted(run["versions"].items()):
        lines.append("%s: %s" % (key, _or(value, "unavailable")))
    lines.append("")
    lines.append("### Server")
    server = run["server"]
    for key in records.SERVER_KEYS:
        lines.append("%s: %s" % (key, _or(server[key], "unavailable")))
    lines.append("")
    return lines


def _scores_section(run: dict, engine_order: list, groups: dict) -> list:
    lines = ["## Scores", ""]
    for task in run["tasks"]:
        lines.append("Task %d: %s | kind: %s | repo: %s" %
                      (task["id"], task["slug"], task["kind"], task["repo"]))
        for engine in engine_order:
            outcome, cls, attempts = _effective(groups.get((task["id"], engine), []))
            label = outcome if cls is None else "%s:%s" % (outcome, cls)
            lines.append("  %s: %s (attempts: %d)" % (engine, label, attempts))
        lines.append("")
    return lines


def count(run: dict, engine_order: list, entries: list, groups: dict, valid_ids: list,
          audit_rows: dict) -> dict:
    """Every number the Counts section reports, from the records alone: no I/O, no text.

    `f` is None while any VALID attempt is still unaudited; `f_audited`/`f_total` are its k of n.
    """
    engines = {}
    for engine in engine_order:
        ents = [e for e in entries if e["engine"] == engine]
        recs = [e["record"] for e in ents if e["record"] is not None]
        tallies = {"not_started": not ents, "attempts": len(ents)}
        for label in ("PASS", "FAIL", "TIMEOUT", "SUSPECT", "DISCARDED"):
            tallies[label] = sum(1 for r in recs if r["outcome"] == label)
        for cls in _CLASS_FIELD:
            tallies["FAIL:%s" % cls] = sum(1 for r in recs
                                           if r["outcome"] == "FAIL" and r["class"] == cls)
        tallies["INCOMPLETE"] = len(ents) - len(recs)
        engines[engine] = tallies

    drops = sum(1 for e in entries if e["record"] is not None
               and e["record"]["outcome"] == "FAIL" and e["record"]["class"] == "dropped-a-file")

    scored = 0
    not_started = 0
    for task in run["tasks"]:
        task_scored = True
        for engine in engine_order:
            group = groups.get((task["id"], engine), [])
            if not group:
                not_started += 1
                task_scored = False
                continue
            record = max(group, key=lambda e: e["attempt"])["record"]
            if record is None or record["engine_run"]["launch"] not in ("started", "unknown"):
                task_scored = False
        if task_scored:
            scored += 1

    audited = sum(1 for aid in valid_ids if aid in audit_rows)
    n = len(valid_ids)
    flagged = None
    if audited == n:
        flagged = sum(1 for aid in valid_ids if audit_rows[aid]["verdict"] == "flagged")
    return {"engines": engines, "drops": drops, "scored": scored, "not_started": not_started,
            "f": flagged, "f_audited": audited, "f_total": n}


def _counts_section(run: dict, engine_order: list, entries: list, groups: dict,
                    valid_ids: list, audit_rows: dict) -> list:
    counts = count(run, engine_order, entries, groups, valid_ids, audit_rows)
    lines = ["## Counts", ""]
    for engine, tallies in counts["engines"].items():
        if tallies["not_started"]:
            lines.append("%s: not_started (NOT_STARTED)" % engine)
        else:
            lines.append(engine)
        for label in ("attempts", "PASS", "FAIL"):
            lines.append("  %s: %d" % (label, tallies[label]))
        for cls in _CLASS_FIELD:
            lines.append("  FAIL:%s: %d" % (cls, tallies["FAIL:%s" % cls]))
        for label in ("TIMEOUT", "SUSPECT", "DISCARDED", "INCOMPLETE"):
            lines.append("  %s: %d" % (label, tallies[label]))
        lines.append("")

    lines.append("drops: %d" % counts["drops"])
    lines.append("scored: %d" % counts["scored"])
    lines.append("not_started: %d" % counts["not_started"])
    if counts["f"] is None:
        lines.append("f: pending (%d of %d audited)" % (counts["f_audited"], counts["f_total"]))
        lines.append("Audit incomplete: no decision rule may be applied to these counts.")
    else:
        lines.append("f: %d" % counts["f"])
    lines.append("")
    return lines


def _classification_section(entries: list) -> list:
    lines = ["## Classification", ""]
    for entry in entries:
        record = entry["record"]
        if record is not None and record["outcome"] == "FAIL":
            lines.append("engine: %s | task: %d | class: %s | field: %s" % (
                record["engine"], record["task"], record["class"],
                _CLASS_FIELD.get(record["class"], "class")))
    lines.append("")
    return lines


def _vetting_section(run: dict, vetting_by_task: dict) -> list:
    lines = ["## Vetting", ""]
    for task in run["tasks"]:
        vetting = vetting_by_task.get(task["id"])
        lines.append("Task %d: %s" % (task["id"], task["slug"]))
        if vetting is None:
            lines.append("  vetting.json: unavailable")
            lines.append("")
            continue
        lines += _vetting_lines(vetting, "  ")
        lines.append("")
    return lines


def _measurements_section(entries: list, audit_rows: dict) -> list:
    lines = ["## Measurements", ""]
    for entry in entries:
        lines.append(entry["id"])
        record = entry["record"]
        if record is None:
            lines.append("  wall_s: unavailable")
            lines.append("  first_edit_s: unavailable")
            for key in records.USAGE_KEYS:
                lines.append("  %s: unavailable" % key)
            lines.append("  review_effort_s: unavailable")
            continue
        engine_run = record["engine_run"]
        lines.append("  wall_s: %s" % _or(engine_run["wall_s"], "unavailable"))
        lines.append("  first_edit_s: %s" % _or(engine_run["first_edit_s"], "unavailable"))
        usage = engine_run["usage"]
        for key in records.USAGE_KEYS:
            lines.append("  %s: %s" % (key, _or(usage[key], "unavailable")))
        review_effort = audit_rows.get(entry["id"], {}).get("review_effort_s")
        lines.append("  review_effort_s: %s" % _or(review_effort, "unavailable"))
    lines.append("")
    return lines


def _report_md(run: dict, engine_order: list, entries: list, groups: dict, valid_ids: list,
               audit_rows: dict, vetting_by_task: dict) -> str:
    lines = _run_section(run, engine_order)
    lines += _scores_section(run, engine_order, groups)
    lines += _counts_section(run, engine_order, entries, groups, valid_ids, audit_rows)
    lines += _classification_section(entries)
    lines += _vetting_section(run, vetting_by_task)
    lines += _measurements_section(entries, audit_rows)
    return "\n".join(lines) + "\n"


def _audit_queue_md(run_dir: Path, entries: list, valid_ids: list, audit_rows: dict) -> str:
    by_id = {entry["id"]: entry for entry in entries}
    lines = ["## Audit Queue", ""]
    for aid in valid_ids:
        record = by_id[aid]["record"]
        attempt_dir = run_dir / aid
        out_path = attempt_dir / _OUT_FILE
        session_log_path = attempt_dir / _SESSION_LOG_FILE
        final_bytes = record["engine_run"]["final_message_bytes"]
        gate = record["gates"]["gate"]
        changed = [c["path"] for c in record["changed"]] if record["changed"] else []
        verdict = audit_rows[aid]["verdict"] if aid in audit_rows else "PENDING"

        lines.append("### %s" % aid)
        lines.append("final message: %s (%s bytes)" % (
            out_path if out_path.is_file() else "unavailable",
            _or(final_bytes, "unavailable")))
        lines.append("session log: %s" % (
            session_log_path if session_log_path.is_file() else "none"))
        lines.append("gate exit code: %s" % (_or(gate["rc"], "n/a") if gate else "n/a"))
        lines.append("changed files: %s" % _path_list(changed))
        lines.append("verdict: %s" % verdict)
        lines.append("")
    return "\n".join(lines) + "\n"


def render(root: Path, run_id: str) -> None:
    problem = admission.check_run_id(run_id)
    if problem is not None:
        raise ValueError("run id %r: %s" % (run_id, problem))
    root = Path(root)
    run_dir = root / "runs" / run_id
    run_json_path = run_dir / "run.json"
    if not run_json_path.is_file():
        raise ValueError("run %s: no run.json under %s" % (run_id, run_dir))
    run = json.loads(run_json_path.read_text(encoding="utf-8"))
    engine_order = [engine["id"] for engine in run["engines"]]

    entries = _load_entries(run_dir, engine_order)
    valid_ids = [entry["id"] for entry in entries
                 if entry["record"] is not None
                 and records.derive_validity(entry["record"]) == "VALID"]
    audit_rows = load_audit(run_dir, valid_ids)
    vetting_by_task = {task["id"]: _load_vetting(root, task) for task in run["tasks"]}
    groups = _group_by_task_engine(entries)

    evidence_content = _evidence_md(run, entries, run_dir, vetting_by_task)
    report_content = _report_md(run, engine_order, entries, groups, valid_ids, audit_rows,
                                vetting_by_task)
    audit_queue_content = _audit_queue_md(run_dir, entries, valid_ids, audit_rows)

    (run_dir / "evidence.md").write_text(evidence_content, encoding="utf-8")
    (run_dir / "report.md").write_text(report_content, encoding="utf-8")
    (run_dir / "audit-queue.md").write_text(audit_queue_content, encoding="utf-8")

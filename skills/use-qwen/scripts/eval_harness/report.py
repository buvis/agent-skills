"""Renders evidence.md, report.md and audit-queue.md for a completed run.

Pure filesystem + JSON in, three markdown files out. Every stored attempt
record is rederived through records.derive_validity and records.classify
before it is trusted: a mismatch between the stored and the rederived
outcome, a malformed audit.jsonl line, or a duplicate attempt_dir refuses
the whole render rather than writing anything. Content is built fully in
memory first, so a refused render never touches the three output files.
"""
import json
from pathlib import Path

from eval_harness import records

_TALLY_LABELS = ("PASS", "FAIL", "TIMEOUT", "SUSPECT", "DISCARDED")


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
            record = json.loads(record_path.read_text(encoding="utf-8"))
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


def _load_audit(run_dir: Path) -> dict:
    audit_path = run_dir / "audit.jsonl"
    rows = {}
    if not audit_path.is_file():
        return rows
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("malformed audit.jsonl line: %r" % line) from exc
        aid = row["attempt_dir"]
        if aid in rows:
            raise ValueError("duplicate attempt_dir in audit.jsonl: %s" % aid)
        rows[aid] = row
    return rows


def _evidence_md(run: dict, entries: list) -> str:
    lines = []
    for task in run["tasks"]:
        lines += ["## Setup", "task: %d" % task["id"], "slug: %s" % task["slug"], ""]
    for entry in entries:
        lines.append("### %s" % entry["id"])
        record = entry["record"]
        if record is None:
            lines += ["INCOMPLETE", "outcome: n/a"]
        else:
            lines += [
                "engine: %s" % record["engine"], "attempt: %d" % record["attempt"],
                "outcome: %s" % record["outcome"], "class: %s" % record["class"],
                "validity: %s" % records.derive_validity(record),
            ]
        lines.append("")
    return "\n".join(lines) + "\n"


def _scores_section(entries: list) -> list:
    lines = ["## Scores", ""]
    last_key = None
    for entry in entries:
        key = (entry["task"], entry["engine"])
        if key != last_key:
            lines.append("%d-%s" % key)
            last_key = key
        outcome = entry["record"]["outcome"] if entry["record"] is not None else "INCOMPLETE"
        lines.append("  %s: %s" % (entry["id"], outcome))
    lines.append("")
    return lines


def _counts_section(engine_order: list, entries: list, valid_ids: list, audit_rows: dict) -> list:
    lines = ["## Counts", ""]
    for engine in engine_order:
        ents = [e for e in entries if e["engine"] == engine]
        if not ents:
            lines += ["%s: not_started (NOT_STARTED)" % engine, ""]
            continue
        tallies = dict.fromkeys(_TALLY_LABELS, 0)
        incomplete = 0
        for entry in ents:
            if entry["record"] is None:
                incomplete += 1
            else:
                tallies[entry["record"]["outcome"]] += 1
        lines.append(engine)
        lines.append("  attempts: %d" % len(ents))
        for label in _TALLY_LABELS:
            lines.append("  %s: %d" % (label, tallies[label]))
        lines.append("  INCOMPLETE: %d" % incomplete)
        lines.append("")

    audited = sum(1 for aid in valid_ids if aid in audit_rows)
    n = len(valid_ids)
    if audited == n:
        flagged = sum(1 for aid in valid_ids if audit_rows.get(aid, {}).get("verdict") == "flagged")
        lines.append("f: %d" % flagged)
    else:
        lines.append("f: pending (%d of %d audited)" % (audited, n))
        lines.append("Audit incomplete: no decision rule may be applied to these counts.")
    lines.append("")
    return lines


def _classification_section(entries: list) -> list:
    lines = ["## Classification", ""]
    for entry in entries:
        record = entry["record"]
        if record is not None and record["outcome"] == "FAIL":
            lines.append("%s: %s" % (entry["id"], record["class"]))
    lines.append("")
    return lines


def _report_md(run: dict, engine_order: list, entries: list, valid_ids: list,
               audit_rows: dict) -> str:
    lines = ["## Run", "", "run_id: %s" % run["run_id"], "tasks: %d" % len(run["tasks"]),
             "engines: %s" % ", ".join(engine_order), ""]
    lines += _scores_section(entries)
    lines += _counts_section(engine_order, entries, valid_ids, audit_rows)
    lines += _classification_section(entries)
    lines += ["## Vetting", "", "## Measurements", ""]
    return "\n".join(lines) + "\n"


def _audit_queue_md(valid_ids: list, audit_rows: dict) -> str:
    lines = ["## Audit Queue", ""]
    for aid in valid_ids:
        verdict = audit_rows[aid]["verdict"] if aid in audit_rows else "PENDING"
        lines.append("%s: %s" % (aid, verdict))
    lines.append("")
    return "\n".join(lines) + "\n"


def render(root: Path, run_id: str) -> None:
    run_dir = Path(root) / "runs" / run_id
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    engine_order = [engine["id"] for engine in run["engines"]]

    entries = _load_entries(run_dir, engine_order)
    audit_rows = _load_audit(run_dir)
    valid_ids = [entry["id"] for entry in entries
                 if entry["record"] is not None
                 and records.derive_validity(entry["record"]) == "VALID"]

    evidence_content = _evidence_md(run, entries)
    report_content = _report_md(run, engine_order, entries, valid_ids, audit_rows)
    audit_queue_content = _audit_queue_md(valid_ids, audit_rows)

    (run_dir / "evidence.md").write_text(evidence_content, encoding="utf-8")
    (run_dir / "report.md").write_text(report_content, encoding="utf-8")
    (run_dir / "audit-queue.md").write_text(audit_queue_content, encoding="utf-8")

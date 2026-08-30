"""Persistence for the proposal review queue: durable storage, an undecided
cursor, rejection records keyed by rubric version, and a per-run decision cap.
"""

import argparse
import json
import sys
from pathlib import Path

PER_RUN_CAP = 10
RUBRIC_VERSION = "1"


class QueueError(Exception):
    """Raised for invalid queue operations (unknown entry, bad decision)."""


def _report_dir() -> Path:
    """dev/local/audit-results under the nearest ancestor of the cwd that
    contains a .git entry, falling back to the cwd itself when none do."""
    cwd = Path.cwd()
    root = next((p for p in (cwd, *cwd.parents) if (p / ".git").exists()), cwd)
    return root / "dev" / "local" / "audit-results"


def _resolve_path(path) -> Path:
    return Path(path) if path is not None else _report_dir() / "distil-memory-queue.json"


def _save_queue(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def slice_key(transcript, line_no):
    return f"{transcript}:{line_no}"


def load(path=None):
    p = _resolve_path(path)
    if not p.exists():
        return {"cursor": 0, "entries": []}
    return json.loads(p.read_text())


def _dropped_at(entries, key, rubric_version):
    return any(
        e["id"] == key and e["decision"] == "dropped" and e["rubric_version"] == rubric_version
        for e in entries
    )


def rejected(key, rubric_version, path=None):
    return _dropped_at(load(path=path)["entries"], key, rubric_version)


def save(proposals, path=None):
    p = _resolve_path(path)
    data = load(path=p)
    entries = data["entries"]
    added = 0
    for proposal in proposals:
        key = slice_key(proposal["transcript"], proposal["line_no"])
        blocked = any(
            e["id"] == key and e["decision"] in ("undecided", "kept") for e in entries
        )
        if blocked or _dropped_at(entries, key, RUBRIC_VERSION):
            continue
        entry = dict(proposal)
        entry["id"] = key
        entry["decision"] = "undecided"
        entry["rubric_version"] = RUBRIC_VERSION
        entries.append(entry)
        added += 1
    _save_queue(data, p)
    return added


def next_undecided(path=None):
    data = load(path=path)
    if data.get("session_decided", 0) >= PER_RUN_CAP:
        return None
    for entry in data["entries"]:
        if entry["decision"] == "undecided":
            return entry
    return None


def decide(entry_id, decision, file_text=None, path=None):
    if decision not in ("kept", "dropped"):
        raise QueueError(f"invalid decision: {decision!r}")
    p = _resolve_path(path)
    data = load(path=p)
    entry = next(
        (e for e in data["entries"] if e["id"] == entry_id and e["decision"] == "undecided"),
        None,
    )
    if entry is None:
        raise QueueError(f"no undecided entry with id {entry_id!r}")
    entry["decision"] = decision
    if file_text is not None:
        entry["file_text"] = file_text
    data["cursor"] = data.get("cursor", 0) + 1
    data["session_decided"] = data.get("session_decided", 0) + 1
    _save_queue(data, p)


def cursor(path=None):
    return load(path=path).get("cursor", 0)


def advance(new_cursor=None, path=None):
    p = _resolve_path(path)
    data = load(path=p)
    data["session_decided"] = 0
    if new_cursor is not None:
        data["cursor"] = new_cursor
    _save_queue(data, p)


def _parse_args(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    save_parser = subparsers.add_parser("save")
    save_parser.add_argument("--proposals-dir", required=True)

    subparsers.add_parser("start")
    subparsers.add_parser("next")

    decide_parser = subparsers.add_parser("decide")
    decide_parser.add_argument("id")
    decide_parser.add_argument("state", choices=["kept", "dropped"])
    decide_parser.add_argument("--file", default=None)

    subparsers.add_parser("cursor")

    return parser.parse_args(argv)


def _save_from_proposals_dir(proposals_dir: Path) -> int:
    records = json.loads((proposals_dir / "proposals.json").read_text())
    proposals = [
        {
            "name": record["name"],
            "kind": record["kind"],
            "transcript": record["transcript"],
            "line_no": record["line_no"],
            "evidence_text": record["evidence_text"],
            "file_text": (proposals_dir / record["file"]).read_text(),
            "existing_text": record.get("existing_text"),
        }
        for record in records
    ]
    added = save(proposals)
    print(f"added {added} of {len(proposals)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.command == "save":
        return _save_from_proposals_dir(Path(args.proposals_dir))
    if args.command == "start":
        advance()
        return 0
    if args.command == "next":
        entry = next_undecided()
        if entry is None:
            return 1
        print(json.dumps(entry))
        return 0
    if args.command == "decide":
        file_text = Path(args.file).read_text() if args.file else None
        decide(args.id, args.state, file_text=file_text)
        return 0
    if args.command == "cursor":
        print(cursor())
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

"""Persistence for the proposal review queue: durable storage, an undecided
cursor, rejection records keyed by rubric version, and a per-run decision cap.
"""

import argparse
import json
import sys
from pathlib import Path

import proposal
import write

PER_RUN_CAP = 10  # walkthrough decisions per sitting; unbased guess, tune after first real run (PRD Risks)
RUBRIC_VERSION = "1"  # bump by hand when distil.py's _DISTIL_PROMPT changes meaningfully; re-opens drops made under the old value


class QueueError(ValueError):
    """Raised for invalid queue operations (unknown entry, bad decision)."""


def _report_dir() -> Path:
    """docs/dev/project-management/audit-results under the nearest ancestor of the cwd that
    contains a .git entry, falling back to the cwd itself when none do."""
    cwd = Path.cwd()
    root = next((p for p in (cwd, *cwd.parents) if (p / ".git").exists()), cwd)
    return root / "docs" / "dev" / "project-management" / "audit-results"


def _resolve_path(path) -> Path:
    return Path(path) if path is not None else _report_dir() / "distil-memory-queue.json"


def _save_queue(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def slice_key(transcript, line_no):
    """Build an entry id from a transcript path and line number."""
    return f"{transcript}:{line_no}"


def load(path=None):
    """Load the queue file, or a fresh empty queue if it does not exist yet."""
    p = _resolve_path(path)
    if not p.exists():
        return {"cursor": 0, "entries": []}
    try:
        text = p.read_text()
        data = json.loads(text) if text else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise QueueError(f"cannot read the review queue {p}: {error}") from error
    if not text:
        raise QueueError(f"cannot read the review queue {p}: file is empty")
    if not isinstance(data, dict):
        raise QueueError(f"invalid review queue schema in {p}: expected a JSON object (dict), not a {type(data).__name__}")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise QueueError(f"invalid review queue schema in {p}: entries must be a list")
    if not all(isinstance(entry, dict) for entry in entries):
        raise QueueError(f"invalid review queue schema in {p}: entries must contain only dict entries")
    return data


def _dropped_at(entries, key, rubric_version):
    return any(
        e["id"] == key and e["decision"] == "dropped" and e["rubric_version"] == rubric_version
        for e in entries
    )


def rejected(key, rubric_version, path=None):
    """Return True if key was dropped under this exact rubric_version.

    A drop recorded under a different rubric_version does not count: bumping
    the rubric re-opens previously dropped entries.
    """
    return _dropped_at(load(path=path)["entries"], key, rubric_version)


def save(proposals, path=None):
    """Append new proposals to the queue as undecided entries, skipping ones
    already present.

    A proposal is skipped when its key already has an "undecided" or "kept"
    entry (unconditional, regardless of rubric_version), or when it was
    "dropped" under the *current* RUBRIC_VERSION specifically - a drop
    recorded under an older rubric_version does not block re-adding it.
    Returns the count of proposals actually added.
    """
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
    """Return the next undecided entry, or None if the session's per-run cap
    (PER_RUN_CAP, refilled by advance()) has been reached, or none remain.
    """
    data = load(path=path)
    if data.get("session_decided", 0) >= PER_RUN_CAP:
        return None
    return next(
        (entry for entry in data["entries"] if entry["decision"] == "undecided"),
        None,
    )


def _find(entries, entry_id, decision):
    return next((e for e in entries if e["id"] == entry_id and e["decision"] == decision), None)


def decide(entry_id, state, file_text=None, path=None, data=None, *, name=None):
    """Record a "kept"/"dropped" decision for an undecided entry.

    Increments both the lifetime cursor and the per-sitting session_decided
    counter; the latter is what next_undecided() checks against PER_RUN_CAP
    and what advance() resets to re-arm the next sitting.

    Deciding an already-kept entry "kept" again with a file_text and/or name
    is a recovery edit: it replaces those fields and moves neither counter.

    Pass `data` to decide against a queue the caller has already read, so the
    read and the decision cannot report different failures for one command.
    """
    if state not in ("kept", "dropped"):
        raise QueueError(f"invalid decision: {state!r}")
    p = _resolve_path(path)
    if data is None:
        data = load(path=p)
    entry = _find(data["entries"], entry_id, "undecided")
    if entry is not None:
        entry["decision"] = state
        data["cursor"] = data.get("cursor", 0) + 1
        data["session_decided"] = data.get("session_decided", 0) + 1
    elif state == "kept" and (file_text is not None or name is not None):
        entry = _find(data["entries"], entry_id, "kept")
    if entry is None:
        raise QueueError(f"no undecided entry with id {entry_id!r}")
    if file_text is not None:
        entry["file_text"] = file_text
    if name is not None:
        entry["name"] = name
    _save_queue(data, p)


def cursor(path=None):
    """Return the lifetime count of decisions made across all sittings."""
    return load(path=path).get("cursor", 0)


def advance(new_cursor=None, path=None):
    """Reset the per-sitting session_decided counter to 0, unconditionally,
    re-arming exactly PER_RUN_CAP more decisions for the next sitting.

    There is no "already lifted" special case: this reset is identical every
    time advance() is called, however many times it has run before.
    Optionally also overwrites the lifetime cursor with new_cursor.
    """
    p = _resolve_path(path)
    data = load(path=p)
    data["session_decided"] = 0
    if new_cursor is not None:
        data["cursor"] = new_cursor
    _save_queue(data, p)


_ENVELOPE_FAULTS = (KeyError, TypeError, AttributeError, proposal.ProposalError)


def unpublished(store, path=None) -> list[str]:
    """Ids, in queue order, of the kept entries that own a target in the store
    at `store` and that write.published() does not confirm there.

    Only the last kept entry for a target owns it. An entry whose envelope
    cannot be read is listed. Store and index read failures propagate.
    """
    data = load(path=path)
    store = Path(store)
    if (store / "MEMORY.md").exists():
        write._readable_bytes(store / "MEMORY.md")
    own_store = store.resolve()
    owners = {}
    for entry in data["entries"]:
        if entry["decision"] != "kept":
            continue
        if (Path(entry["transcript"]).parent / "memory").resolve() != own_store:
            continue
        try:
            target = write._target_stem(entry)[0]
        except _ENVELOPE_FAULTS:
            target = ("unreadable envelope", entry["id"])
        owners.pop(target, None)
        owners[target] = entry
    ids = []
    for entry in owners.values():
        try:
            if write.published(entry, store):
                continue
        except _ENVELOPE_FAULTS:
            pass
        ids.append(entry["id"])
    return ids


def _parse_args(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    save_parser = subparsers.add_parser("save")
    save_parser.add_argument("--proposals-dir", required=True)
    save_parser.add_argument("--queue", default=None)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--queue", default=None)

    next_parser = subparsers.add_parser("next")
    next_parser.add_argument("--queue", default=None)

    decide_parser = subparsers.add_parser("decide")
    decide_parser.add_argument("id")
    decide_parser.add_argument("state", choices=["kept", "dropped"])
    decide_parser.add_argument("--file", default=None)
    decide_parser.add_argument("--name", default=None)
    decide_parser.add_argument("--queue", default=None)

    unpublished_parser = subparsers.add_parser("unpublished")
    unpublished_parser.add_argument("--store", required=True)
    unpublished_parser.add_argument("--queue", default=None)

    cursor_parser = subparsers.add_parser("cursor")
    cursor_parser.add_argument("--queue", default=None)

    return parser.parse_args(argv)


def _save_from_proposals_dir(proposals_dir: Path, path=None) -> int:
    if path is None:
        path = proposals_dir.parent / "distil-memory-queue.json"
    # `source` always names the file whose read is next, so the handler below
    # blames the one that actually failed rather than the last one seen.
    source = proposals_dir / "proposals.json"
    try:
        records = json.loads(source.read_text())
        proposals = []
        for record in records:
            source = proposals_dir / record["file"]
            proposals.append(
                {
                    "name": record["name"],
                    "kind": record["kind"],
                    "transcript": record["transcript"],
                    "line_no": record["line_no"],
                    "evidence_text": record["evidence_text"],
                    "file_text": source.read_text(),
                    "existing_text": record.get("existing_text"),
                    "dedup_error": record.get("dedup_error"),
                }
            )
    except (OSError, json.JSONDecodeError) as error:
        print(f"cannot read the proposals {source}: {error}", file=sys.stderr)
        return 1
    added = save(proposals, path=path)
    print(f"added {added} of {len(proposals)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        if args.command == "save":
            return _save_from_proposals_dir(Path(args.proposals_dir), path=args.queue)
        elif args.command == "start":
            advance(path=args.queue)
            return 0
        elif args.command == "next":
            entry = next_undecided(path=args.queue)
            if entry is None:
                return 1
            print(json.dumps(entry))
            return 0
        elif args.command == "decide":
            file_text = None
            if args.file:
                try:
                    file_text = Path(args.file).read_text()
                except (OSError, json.JSONDecodeError) as exc:
                    print(f"cannot read the note file {args.file}: {exc}", file=sys.stderr)
                    return 1
            # Read once, outside the refusal handler below, so an unreadable
            # queue leaves through the exit 2 handler instead.
            data = load(path=args.queue)
            try:
                decide(args.id, args.state, file_text=file_text, path=args.queue, data=data, name=args.name)
            except QueueError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            return 0
        elif args.command == "unpublished":
            try:
                ids = unpublished(args.store, path=args.queue)
            except (write.WriteError, OSError) as exc:
                print(f"cannot check the store {args.store}: {exc}", file=sys.stderr)
                return 1
            for entry_id in ids:
                print(entry_id)
            return 1 if ids else 0
        elif args.command == "cursor":
            print(cursor(path=args.queue))
            return 0
    except QueueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

"""Writing an approved proposal into the memory store: the memory file itself
and the MEMORY.md pointer line that indexes it.
"""

import argparse
import json
import sys
from pathlib import Path

import dedup
import proposal


class WriteError(ValueError):
    """Raised when a memory file cannot be written."""


def _target_stem(entry: dict) -> tuple[str, bool]:
    """The filename stem `entry` targets, and whether it is a new one.

    An update targets the name carried by its `kind`, not `entry["name"]` or
    the file text's own frontmatter name field - either of those may differ
    from the memory actually being replaced.
    """
    name = proposal.updated_name(entry["kind"])
    if name is not None:
        return proposal.sanitise_name(name), False
    return proposal.sanitise_name(entry["name"]), True


def _atomic_write(path: Path, data: str | bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        if isinstance(data, bytes):
            tmp.write_bytes(data)
        else:
            tmp.write_text(data)
        tmp.replace(path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def _readable_bytes(path: Path) -> bytes:
    """The bytes `path` holds now, refused as a WriteError when unreadable.

    Bytes rather than text: read_text translates line endings, so a memory
    written with CRLF would come back punctuated differently. Decoding is
    only the check that the store can read the file at all, strictly as
    UTF-8 so that legal non-ASCII passes through untouched. The refusal
    names the file, because that is what the caller has to repair.
    """
    try:
        raw = path.read_bytes()
        raw.decode()
    except (OSError, UnicodeDecodeError) as exc:
        raise WriteError(f"{path}: {exc}") from exc
    return raw


def write_memory(entry: dict, store_path: Path) -> Path:
    """Write `entry["file_text"]` to its target file inside `store_path`.

    The file text's frontmatter must parse. A new entry must not already have
    a file at its target; an update must. Raises WriteError otherwise, or when
    the write itself fails (for example because `store_path` does not exist).
    """
    try:
        proposal.parse_frontmatter(entry["file_text"])
    except proposal.ProposalError as exc:
        raise WriteError(str(exc)) from exc
    stem, is_new = _target_stem(entry)
    target = store_path / f"{stem}.md"
    exists = target.exists()
    if is_new and exists:
        raise WriteError(f"{target} already exists")
    if not is_new and not exists:
        raise WriteError(f"{target} does not exist")
    try:
        _atomic_write(target, entry["file_text"])
    except OSError as exc:
        raise WriteError(str(exc)) from exc
    return target


def _title(stem: str) -> str:
    return stem.replace("-", " ").capitalize()


def _pointer_line(stem: str, description: str) -> str:
    return f"- [{_title(stem)}]({stem}.md) — {description}"


def append_pointer(store_path: Path, entry: dict) -> str | None:
    """Upsert `entry`'s pointer line in `store_path`'s MEMORY.md.

    A new entry's line is always appended. An update's line replaces the
    existing entry for its target stem in place, or is appended when no line
    for that stem exists yet - unless the description is unchanged from
    `entry["existing_text"]`, in which case nothing is written and None is
    returned.
    """
    stem, is_new = _target_stem(entry)
    description = proposal.parse_frontmatter(entry["file_text"])["description"]

    if not is_new:
        old_description = proposal.parse_frontmatter(entry["existing_text"])["description"]
        if old_description == description:
            return None

    line = _pointer_line(stem, description)
    index_path = store_path / "MEMORY.md"
    lines = _readable_bytes(index_path).decode().splitlines() if index_path.exists() else []

    if not is_new:
        for i, existing_line in enumerate(lines):
            if stem in dedup.parse_index(existing_line):
                lines[i] = line
                _atomic_write(index_path, "\n".join(lines) + "\n")
                return line

    lines.append(line)
    _atomic_write(index_path, "\n".join(lines) + "\n")
    return line


def _rollback(target: Path, previous: bytes | None) -> None:
    """Put `target` back the way this run found it.

    `previous` is the bytes the target held before this run wrote it, or None
    when this run created it. A rollback that cannot happen is reported rather
    than swallowed: the store is left holding a memory nothing points to.
    """
    try:
        if previous is None:
            target.unlink()
        else:
            _atomic_write(target, previous)
    except OSError as exc:
        print(f"rollback failed: {exc}", file=sys.stderr)


def _parse_args(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("--store", required=True)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.command == "write":
        entry = json.loads(sys.stdin.read())
        store_path = Path(args.store)
        try:
            # naming the target reads the entry envelope, so a malformed one
            # fails here: report it and return 1 like every other fault
            stem, _ = _target_stem(entry)
            target = store_path / f"{stem}.md"
            # read fresh, every run: the entry's own copy of the previous text
            # may be stale, and only the bytes on disk are what a rollback owes
            # back. A target this run cannot read is one to refuse, not to
            # overwrite: nothing has been written yet, so the store keeps
            # every byte it came in with.
            # is_file answers False for a target that is merely absent, but a
            # store this process cannot search makes it raise instead: refuse
            # on that too, naming the file the probe could not answer for
            try:
                exists = target.is_file()
            except OSError as exc:
                raise WriteError(f"{target}: {exc}") from exc
            previous = _readable_bytes(target) if exists else None
            written = write_memory(entry, store_path)
        except (WriteError, KeyError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        try:
            line = append_pointer(store_path, entry)
        except (OSError, WriteError, proposal.ProposalError, KeyError) as exc:
            # the pointer line is built from frontmatter, so this step fails on
            # the entry as well as on the disk: file text carrying no
            # description, an update whose existing_text will not parse, or an
            # index this process cannot read (a WriteError naming it). The
            # memory file is already on disk by then, so the store has to go
            # back to the state this run found it in. MEMORY.md needs no
            # restoring: _atomic_write only ever moves a complete file into
            # place, so a failed index write leaves the index holding its
            # previous bytes, and an entry fault never reaches the index at all.
            print(str(exc), file=sys.stderr)
            _rollback(written, previous)
            return 1
        print(written)
        print(line if line is not None else "MEMORY.md: unchanged")
        return 0


if __name__ == "__main__":
    sys.exit(main())

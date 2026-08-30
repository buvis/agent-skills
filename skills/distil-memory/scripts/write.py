"""Writing an approved proposal into the memory store: the memory file itself
and the MEMORY.md pointer line that indexes it.
"""

from pathlib import Path

import dedup
import proposal


class WriteError(ValueError):
    """Raised when a memory file or its index pointer cannot be written."""


def _target_stem(entry: dict) -> tuple[str, bool]:
    """The filename stem `entry` targets, and whether it is a new one.

    An update targets the name carried by its `kind`, not `entry["name"]` or
    the file text's own frontmatter name field - either of those may differ
    from the memory actually being replaced.
    """
    name = proposal.updated_name(entry["kind"])
    if name is not None:
        return name, False
    return proposal.sanitise_name(entry["name"]), True


def write_memory(entry: dict, store_path) -> Path:
    """Write `entry["file_text"]` to its target file inside `store_path`.

    A new entry must not already have a file at its target; an update must.
    Raises WriteError otherwise, or when the write itself fails (for example
    because `store_path` does not exist).
    """
    store_path = Path(store_path)
    stem, is_new = _target_stem(entry)
    target = store_path / f"{stem}.md"
    exists = target.exists()
    if is_new and exists:
        raise WriteError(f"{target} already exists")
    if not is_new and not exists:
        raise WriteError(f"{target} does not exist")
    try:
        target.write_text(entry["file_text"])
    except OSError as exc:
        raise WriteError(str(exc)) from exc
    return target


def _title(stem: str) -> str:
    replaced = stem.replace("-", " ")
    return replaced[0].upper() + replaced[1:] if replaced else replaced


def _pointer_line(stem: str, description: str) -> str:
    return f"- [{_title(stem)}]({stem}.md) — {description}"


def append_pointer(store_path, entry: dict) -> str | None:
    """Upsert `entry`'s pointer line in `store_path`'s MEMORY.md.

    A new entry's line is always appended. An update's line replaces the
    existing entry for its target stem in place, or is appended when no line
    for that stem exists yet - unless the description is unchanged from
    `entry["existing_text"]`, in which case nothing is written and None is
    returned.
    """
    store_path = Path(store_path)
    stem, is_new = _target_stem(entry)
    description = proposal.parse_frontmatter(entry["file_text"])["description"]

    if not is_new:
        old_description = proposal.parse_frontmatter(entry["existing_text"])["description"]
        if old_description == description:
            return None

    line = _pointer_line(stem, description)
    index_path = store_path / "MEMORY.md"
    lines = index_path.read_text().splitlines() if index_path.exists() else []

    if not is_new:
        for i, existing_line in enumerate(lines):
            if stem in dedup.parse_index(existing_line):
                lines[i] = line
                index_path.write_text("\n".join(lines) + "\n")
                return line

    lines.append(line)
    index_path.write_text("\n".join(lines) + "\n")
    return line

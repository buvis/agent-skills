"""The index side of deduplication: read the memory plane's index, parse its
bullet links, and shortlist the existing memories a proposal may duplicate.

`shortlist()` scores each index entry against the proposal's name and
description with the Jaccard ratio of their content words, so a long entry that
merely mentions the query's words ranks below a short one that is about them.
"""

import re
from pathlib import Path

import proposal

SHORTLIST_LIMIT = 5

Candidate = tuple[str, str]

_ENTRY = re.compile(r"^- \[([^\]]+)\]\(([\w.-]+)\.md\)\s*—\s*(.*)$")


def read_index(memory_dir: Path) -> str:
    """The index text of `memory_dir`, or "" when it holds no index."""
    index = memory_dir / "MEMORY.md"
    if not index.exists():
        return ""
    return index.read_text()


def parse_index(index_text: str) -> dict[str, str]:
    """Each bullet link's memory name mapped to its title and hook."""
    entries = {}
    for line in index_text.splitlines():
        match = _ENTRY.match(line)
        if match:
            title, name, hook = match.groups()
            entries[name] = f"{title} {hook}"
    return entries


def shortlist(
    index_text: str, proposed: proposal.Proposal, limit: int = SHORTLIST_LIMIT
) -> list[str]:
    """The `limit` index names closest to `proposed`, best score first."""
    frontmatter = proposal.parse_frontmatter(proposed.file_text)
    query = set(proposal._tokens(f"{frontmatter['name']} {frontmatter['description']}"))

    scored = []
    for name, text in parse_index(index_text).items():
        entry = set(proposal._tokens(f"{name} {text}"))
        shared = len(query & entry)
        if shared:
            scored.append((-shared / len(query | entry), name))

    return [name for _, name in sorted(scored)[:limit]]

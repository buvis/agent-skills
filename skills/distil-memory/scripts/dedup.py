"""Deduplication: read the memory plane's index, parse its bullet links,
shortlist the existing memories a proposal may duplicate, read those memories,
and type the proposal against them.

`shortlist()` scores each index entry against the proposal's name and
description with the Jaccard ratio of their content words, so a long entry that
merely mentions the query's words ranks below a short one that is about them.
`classify()` then asks the strong-tier judge once about the whole shortlist,
which is why only that handful of memories is ever read.
"""

import re
from collections.abc import Callable
from pathlib import Path

import funnel
from proposal import NEW, Proposal, _tokens, parse_frontmatter, update_kind

SHORTLIST_LIMIT = 5

Candidate = tuple[str, str]

_ENTRY = re.compile(r"^- \[([^\]]+)\]\(([\w.-]+)\.md\)\s*—\s*(.*)$")

_PROMPT = """A distiller proposes this new memory:

{proposal}

These memories already exist:

{candidates}
If the proposal restates or refines one of them, answer with that memory's \
name and nothing else. If it records something none of them holds, answer \
with the single word new.
"""


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
    index_text: str, proposal: Proposal, limit: int = SHORTLIST_LIMIT
) -> list[str]:
    """The `limit` index names closest to `proposal`, best score first."""
    frontmatter = parse_frontmatter(proposal.file_text)
    query = set(_tokens(f"{frontmatter['name']} {frontmatter['description']}"))

    scored = []
    for name, text in parse_index(index_text).items():
        entry = set(_tokens(f"{name} {text}"))
        shared = len(query & entry)
        if shared:
            scored.append((-shared / len(query | entry), name))

    return [name for _, name in sorted(scored)[:limit]]


def read_candidates(
    memory_dir: Path, names: list[str]
) -> tuple[list[Candidate], list[str]]:
    """The full text of each named memory, and the names of the memories that
    exist but could not be read. A name the plane no longer holds is a stale
    index entry, so it is skipped rather than reported."""
    candidates = []
    unread_names = []
    for name in names:
        try:
            candidates.append((name, (memory_dir / f"{name}.md").read_text()))
        except FileNotFoundError:
            continue
        except OSError:
            unread_names.append(name)

    return candidates, unread_names


def classify(
    proposal: Proposal,
    candidates: list[Candidate],
    judge: Callable[[str, str], str] = funnel.judge,
) -> str:
    """`proposal`'s kind: `update <name>` when it restates one of `candidates`,
    `new` otherwise. A name a candidate already holds is a settled collision,
    so only an open question about a non-empty shortlist costs a model call."""
    names = [name for name, _ in candidates]
    proposed_name = parse_frontmatter(proposal.file_text)["name"]
    if proposed_name in names:
        return update_kind(proposed_name)
    if not candidates:
        return NEW

    existing = "\n".join(f"## {name}\n\n{text}\n" for name, text in candidates)
    prompt = _PROMPT.format(proposal=proposal.file_text, candidates=existing)
    answer = judge(prompt, "strong").strip()

    return update_kind(answer) if answer in names else NEW

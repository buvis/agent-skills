"""Filter transcript entries down to genuine assistant-authored prose.

Exclusions applied by assistant_only:
1. entry.get("type") != "assistant" - not an assistant turn at all.
2. entry.get("isMeta") truthy - matches parser.py's user-side guard.
3. _is_compaction_entry(entry) - a harness-generated compaction summary,
   not the model's original authored text for that turn.
4. A content block without a "text" key (tool_use, thinking,
   redacted_thinking) - excluded per-block, not per-entry: a kept entry
   can still drop some of its blocks.
5. A "text" block that is empty or whitespace-only -
   `_assistant_text_blocks` already excludes it, nothing to slice.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator
import json
import re


def _is_compaction_entry(entry: dict) -> bool:
    if entry.get("isCompactSummary") is True:
        return True
    sub = entry.get("subtype", "")
    if isinstance(sub, str) and "compact" in sub:
        return True
    att = entry.get("attachment")
    if isinstance(att, dict) and "compact" in str(att.get("type", "")):
        return True
    return False


def _iter_entries(path: Path) -> Iterator[tuple[int, dict]]:
    """Yield (line_no, entry) for each parseable JSON line. Skips blank
    lines and invalid JSON exactly like parser.py's parse_session loop
    (shape reused, not imported - this is a 6-line generator, not worth a
    cross-module dependency for)."""
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield line_no, json.loads(raw)
            except ValueError:
                continue


def _assistant_text_blocks(entry: dict) -> list[str]:
    """Every content block's "text" field on an assistant-role entry.
    Blocks without a "text" key (tool_use, thinking, redacted_thinking) are
    structurally excluded for free - they don't have the key this reads."""
    if entry.get("type") != "assistant":
        return []
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return [content] if content.strip() else []
    if not isinstance(content, list):
        return []
    return [
        b["text"] for b in content
        if isinstance(b, dict) and isinstance(b.get("text"), str) and b["text"].strip()
    ]


def assistant_only(entries: Iterable[tuple[int, dict]]) -> list[tuple[int, str]]:
    """Filter (line_no, entry) pairs to genuine assistant-authored prose.

    Enumerated exclusions (each gets its own test in test_funnel.py):
    1. entry.get("type") != "assistant" - not an assistant turn at all.
    2. entry.get("isMeta") truthy - matches parser.py's user-side guard.
    3. _is_compaction_entry(entry) - a harness-generated compaction summary,
       not the model's original authored text for that turn.
    4. A content block without a "text" key (tool_use, thinking,
       redacted_thinking) - excluded per-block, not per-entry: a kept entry
       can still drop some of its blocks.
    5. A "text" block that is empty or whitespace-only -
       `_assistant_text_blocks` already excludes it, nothing to slice.

    Returns one (line_no, text) pair per surviving text block.
    """
    out: list[tuple[int, str]] = []
    for line_no, entry in entries:
        if entry.get("isMeta") or _is_compaction_entry(entry):
            continue
        for text in _assistant_text_blocks(entry):
            out.append((line_no, text))
    return out


@dataclass(frozen=True)
class Slice:
    text: str
    transcript: Path
    line_no: int
    marker: str  # the literal substring _MARKER_RE matched


# One named pattern, case-insensitive. Vocabulary drawn verbatim from the
# source discovery doc's measured examples (MEASURED, Verified:, proven
# live, confirmed, reproduced live). Extend this one place, not the callers.
_MARKER_RE = re.compile(r"\b(measured|verified|confirmed|reproduced|proven)\b", re.IGNORECASE)


def _raw_marker_hits(entries: list[tuple[int, dict]]) -> int:
    """Count _MARKER_RE hits across every assistant-role text block, BEFORE
    assistant_only's isMeta/compaction exclusion (so this includes hits
    inside compaction summaries and isMeta entries). Non-text blocks
    (tool_use, thinking) are still structurally excluded for free, same as
    assistant_only - only the isMeta/compaction entry-level exclusion is
    skipped here. This is the yield report's "slices matched" stage."""
    count = 0
    for _line_no, entry in entries:
        for text in _assistant_text_blocks(entry):
            count += len(_MARKER_RE.findall(text))
    return count


def scan(transcripts: list[Path]) -> tuple[int, list[Slice]]:
    """The one authoritative pass: reads each transcript's entries exactly
    once and returns (matched_count, kept_slices) together, so "matched"
    and "kept" can never drift out of sync by being computed from two
    different reads. `slice_on_markers` (below) is a thin wrapper over this
    for the PRD's named export; `main()` calls `scan()` directly to get
    both yield-report numbers from a single pass per transcript."""
    matched = 0
    kept: list[Slice] = []
    for path in transcripts:
        entries = list(_iter_entries(path))
        matched += _raw_marker_hits(entries)
        for line_no, text in assistant_only(entries):
            m = _MARKER_RE.search(text)
            if m:
                kept.append(Slice(text=text, transcript=path, line_no=line_no, marker=m.group(0)))
    return matched, kept


def slice_on_markers(transcripts: list[Path]) -> list[Slice]:
    """Marker-match assistant-role text per transcript, post assistant_only
    filtering. Thin wrapper: `return scan(transcripts)[1]`. This is the
    PRD-named export other modules should call when only the kept slices
    (not the matched count) are needed; `main()` itself calls `scan()`
    directly to avoid re-reading every transcript a second time.
    """
    return scan(transcripts)[1]

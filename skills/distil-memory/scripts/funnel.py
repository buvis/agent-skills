"""Filter transcript entries down to genuine assistant-authored prose.

Exclusions applied by assistant_only:
1. entry.get("type") != "assistant" - not an assistant turn at all.
2. entry.get("isMeta") truthy - matches parser.py's user-side guard.
   Defensive only on the assistant side: measured against the real
   transcript corpus (2,712 transcripts, 201,379 assistant-role entries),
   0 assistant-role entries carried a truthy isMeta (vs. 1,406 non-assistant
   entries that did). Kept as a guard against a schema that could change,
   not because it has ever fired here.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Iterator
import argparse
import json
import re
import subprocess
import sys

import corpus


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

    Enumerated exclusions: see the module docstring at the top of this file.

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
            if _MARKER_RE.search(text):
                count += 1
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
        for line_no, entry in _iter_entries(path):
            matched += _raw_marker_hits([(line_no, entry)])
            for _line_no, text in assistant_only([(line_no, entry)]):
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


_MODEL_FOR_TIER = {"cheap": "haiku", "strong": "sonnet"}


def judge(prompt: str, tier: str) -> str:
    """Invoke the `claude` CLI non-interactively with the model resolved
    from `tier` and return its raw stdout. Raises RuntimeError(stderr) on
    a non-zero exit."""
    proc = subprocess.run(
        ["claude", "--print", "--model", _MODEL_FOR_TIER[tier], prompt],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return proc.stdout


_TRANSIENT = "transient"
_DURABLE = "durable"

_TRIAGE_PROMPT = (
    "Classify this snippet as exactly one word, '{transient}' or '{durable}'. "
    "'{transient}' means it verifies something already known or already "
    "working (a test pass, a build succeeding, a repeated confirmation). "
    "'{durable}' means it establishes a new fact worth remembering. "
    "Answer with exactly one of those two words, nothing else.\n\n{text}"
)


def triage(
    slices: list[Slice], judge: Callable[[str, str], str] = judge
) -> tuple[list[Slice], int]:
    """Cheap-tier pass: ask `judge` to classify each slice as transient or
    durable, discarding transient ones. Fail-open - any response other than
    an exact (case/whitespace-insensitive) match on "transient" keeps the
    slice. Returns (survivors, discard_count)."""
    survivors: list[Slice] = []
    discard_count = 0
    for slice_ in slices:
        prompt = _TRIAGE_PROMPT.format(transient=_TRANSIENT, durable=_DURABLE, text=slice_.text)
        response = judge(prompt, "cheap")
        if response.strip().lower() == _TRANSIENT:
            discard_count += 1
        else:
            survivors.append(slice_)
    return survivors, discard_count


def render_yield(counts: dict[str, int | str | None]) -> str:
    """Pure string formatting of the pipeline's yield report: no subprocess
    calls, no file I/O. `counts` carries transcripts_read, slices_matched,
    slices_kept, survivors (survivors is None for a --dry-run, rendered as
    "n/a") and claude_checkup_version (the resolved parser version, per the
    PRD's Phase 2 acceptance criteria)."""
    survivors = counts["survivors"]
    survivors_text = "n/a" if survivors is None else str(survivors)
    lines = [
        f"transcripts_read: {counts['transcripts_read']}",
        f"slices_matched: {counts['slices_matched']}",
        f"slices_kept: {counts['slices_kept']}",
        f"survivors: {survivors_text}",
        f"claude_checkup_version: {counts['claude_checkup_version']}",
        "",
        "How to proceed: this report was also written to "
        "dev/local/audit-results/. Review the survivors and promote "
        "durable facts into memory.",
    ]
    return "\n".join(lines) + "\n"


def _run_triage(kept_slices: list[Slice]) -> tuple[int | None, str | None]:
    """Cheap-tier triage with the model-call failure path folded in.

    Returns (survivors_count, error_message). On any failure reaching the
    `claude` CLI the count is None - rendered "n/a", the same as a dry run,
    because no survivor count exists - and the message is the failure text.
    The report still gets printed either way: a run must never go silent.
    """
    try:
        survivors, _discard_count = triage(kept_slices)
        return len(survivors), None
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)


def _report_dir() -> Path:
    """dev/local/audit-results under the nearest ancestor of the cwd that
    contains a .git entry, falling back to the cwd itself when none do.
    Computed at call time (not a module constant) so it reflects the
    caller's cwd rather than the cwd at import time."""
    cwd = Path.cwd()
    root = next((p for p in (cwd, *cwd.parents) if (p / ".git").exists()), cwd)
    return root / "dev" / "local" / "audit-results"


def _write_report(report: str, report_dir: Path) -> Path:
    """Write `report` under report_dir with a UTC-stamped filename and
    return the path written. Raises OSError if the directory cannot be
    created or the file cannot be written."""
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = report_dir / f"distil-memory-{timestamp}.md"
    out_path.write_text(report)
    return out_path


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--project", default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: select transcripts, scan and (unless --dry-run)
    triage them, then print and write the yield report.

    Returns 0 on success.
    """
    args = _parse_args(argv)

    try:
        module, resolved_version = corpus.resolve_parser()
        transcripts = corpus.select_transcripts(
            days=args.days, all=args.all, project=args.project, resolved=(module, resolved_version)
        )
    except corpus.StaleParserError as exc:
        print(exc, file=sys.stderr)
        return 1

    matched_count, kept_slices = scan(transcripts)

    if args.dry_run:
        survivors_count, triage_error = None, None
    else:
        survivors_count, triage_error = _run_triage(kept_slices)

    counts = {
        "transcripts_read": len(transcripts),
        "slices_matched": matched_count,
        "slices_kept": len(kept_slices),
        "survivors": survivors_count,
        "claude_checkup_version": resolved_version,
    }
    report = render_yield(counts)
    print(report, end="")

    if triage_error is not None:
        print(triage_error, file=sys.stderr)

    report_dir = _report_dir()
    try:
        print(_write_report(report, report_dir))
    except OSError as exc:
        print(f"failed to write report to {report_dir}: {exc}", file=sys.stderr)
        return 1

    return 1 if triage_error is not None else 0


if __name__ == "__main__":
    sys.exit(main())

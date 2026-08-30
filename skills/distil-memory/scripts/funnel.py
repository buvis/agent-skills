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

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Iterator
import argparse
import json
import re
import subprocess
import sys

import corpus
import proposal


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


def _matches_and_slices_for_entry(line_no: int, entry: dict, path: Path) -> tuple[int, list[Slice]]:
    """Per-entry equivalent of `_raw_marker_hits`/`assistant_only` for one
    (line_no, entry) pair, without wrapping it in a singleton list for
    either. Preserves `_raw_marker_hits`' broader match count (every
    assistant text block, including isMeta/compaction ones) alongside
    `assistant_only`'s narrower one (kept slices)."""
    matched = 0
    kept: list[Slice] = []
    is_excluded_entry = entry.get("isMeta") or _is_compaction_entry(entry)
    for text in _assistant_text_blocks(entry):
        m = _MARKER_RE.search(text)
        if m:
            matched += 1
            if not is_excluded_entry:
                kept.append(Slice(text=text, transcript=path, line_no=line_no, marker=m.group(0)))
    return matched, kept


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
            entry_matched, entry_kept = _matches_and_slices_for_entry(line_no, entry, path)
            matched += entry_matched
            kept.extend(entry_kept)
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


def render_yield(counts: dict[str, object], proposals_dir: Path | None = None) -> str:
    """Pure string formatting of the pipeline's yield report: no subprocess
    calls, no file I/O, and no mutation of `counts`. `counts` carries
    transcripts_read, slices_matched, slices_kept, survivors (survivors is
    None for a --dry-run, rendered as "n/a") and claude_checkup_version (the
    resolved parser version, per the PRD's Phase 2 acceptance criteria).

    The distil stage's five counts are optional, so a caller from before
    that stage still renders. Missing or None means the stage did not run
    and shows as "n/a"; a stage that ran and yielded nothing reports 0.
    `new_vs_update` is a (new, update) pair of ints, joined with a slash
    here - presentation belongs to the renderer.

    `proposals_dir` is the directory this run published, handed in rather
    than looked up: the audit directory holds every run's proposals, so
    hunting it for a name would point the reader at somebody else's. None
    means this run published none, and then the closing paragraph names no
    proposals directory at all.
    """
    def text(key: str) -> str:
        value = counts.get(key)
        return "n/a" if value is None else str(value)

    pair = counts.get("new_vs_update")
    lines = [
        f"transcripts_read: {counts['transcripts_read']}",
        f"slices_matched: {counts['slices_matched']}",
        f"slices_kept: {counts['slices_kept']}",
        f"survivors: {text('survivors')}",
        f"proposals: {text('proposals')}",
        f"discards: {text('discards')}",
        f"new_vs_update: {'n/a' if pair is None else f'{pair[0]}/{pair[1]}'}",
        f"skipped_by_limit: {text('skipped_by_limit')}",
        f"dedup_errors: {text('dedup_errors')}",
        f"claude_checkup_version: {counts['claude_checkup_version']}",
        "",
        "How to proceed: this report was also written to "
        "dev/local/audit-results/. Review the survivors and promote "
        "durable facts into memory."
        + (f" This run's proposals are in {proposals_dir}." if proposals_dir is not None else ""),
    ]
    return "\n".join(lines) + "\n"


def _run_triage(kept_slices: list[Slice]) -> tuple[list[Slice], int | None, str | None]:
    """Cheap-tier triage with the model-call failure path folded in.

    Returns (survivors, survivors_count, error_message), where the count is
    always len(survivors) from the one triage pass, so the number reported
    can never disagree with the slices handed back. On any failure reaching
    the `claude` CLI there are no survivors and the count is None - rendered
    "n/a", the same as a dry run, because no survivor count exists - and the
    message is the failure text. The report still gets printed either way: a
    run must never go silent.
    """
    try:
        survivors, _discard_count = triage(kept_slices)
        return survivors, len(survivors), None
    except subprocess.TimeoutExpired as exc:
        return [], None, f"claude timed out after {exc.timeout}s"
    except (RuntimeError, OSError) as exc:
        return [], None, str(exc)


def _report_dir() -> Path:
    """dev/local/audit-results under the nearest ancestor of the cwd that
    contains a .git entry, falling back to the cwd itself when none do.
    Computed at call time (not a module constant) so it reflects the
    caller's cwd rather than the cwd at import time."""
    cwd = Path.cwd()
    root = next((p for p in (cwd, *cwd.parents) if (p / ".git").exists()), cwd)
    return root / "dev" / "local" / "audit-results"


def _write_report(report: str, report_dir: Path, timestamp: str) -> Path:
    """Write `report` under report_dir named with the caller's `timestamp`
    and return the path written. The stamp comes from the caller so every
    artefact of one run carries the same one. Raises OSError if the
    directory cannot be created or the file cannot be written."""
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / f"distil-memory-{timestamp}.md"
    out_path.write_text(report)
    return out_path


@dataclass(frozen=True)
class _PublishedDiscard:
    """A discard in the shape `proposal.write_proposals` reads it in.

    `distil.Discard` carries the slice it came from, the publisher wants the
    transcript and line number themselves.
    """

    transcript: Path
    line_no: int
    reason: str


def _read_plane(memory_dir: Path, dedup, distil) -> tuple[str, list[str], bool, str | None]:
    """One memory plane read once: its index text, the anchors it offers, and
    whether the index names anything at all.

    The read happens before the directory's first proposal exists, so an index
    that will not open cannot be reported on the proposal it broke. Its message
    is returned instead, for every proposal the directory goes on to produce.
    """
    try:
        index_text = dedup.read_index(memory_dir)
    except OSError as exc:
        return "", [], False, f"the memory index could not be read: {exc}"
    examples = distil.load_examples(memory_dir, index_text)
    return index_text, examples, bool(dedup.parse_index(index_text)), None


def _type_proposal(
    candidate: proposal.Proposal,
    memory_dir: Path,
    index_text: str,
    pending_error: str | None,
    dedup,
) -> proposal.Proposal:
    """`candidate` typed against the memories its own plane already holds.

    Every dedup failure keeps the proposal and leaves it new: a distilled
    memory must not be lost to the step that was only meant to label it. A
    missing CLI is not one of those failures - it ends the whole stage.
    """
    if pending_error is not None:
        return replace(candidate, dedup_error=pending_error)

    names = dedup.shortlist(index_text, candidate)
    candidates, unread_names = dedup.read_candidates(memory_dir, names)
    if unread_names:
        return replace(candidate, dedup_error=f"could not read {', '.join(unread_names)}")

    try:
        kind = dedup.classify(candidate, candidates)
    except FileNotFoundError:
        raise
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        return replace(candidate, dedup_error=f"the typing call failed: {exc}")
    existing_text = dict(candidates).get(proposal.updated_name(kind))
    return replace(candidate, kind=kind, existing_text=existing_text)


def _run_distil(
    survivors: list[Slice],
) -> tuple[list[proposal.Proposal], list[_PublishedDiscard], str | None]:
    """Distil `survivors` (already capped by the caller) into proposals, each
    typed against the memory plane beside its own transcript.

    Returns (proposals, discards, stage_error). A missing `claude` binary fails
    the same way for every call still to come, so it ends the stage with what
    was already produced rather than burning the cap repeating itself.
    """
    # `dedup` and `distil` import `funnel` at module level, so importing either
    # at the top of this file would close that cycle.
    import dedup
    import distil

    proposals: list[proposal.Proposal] = []
    discards: list[_PublishedDiscard] = []
    planes: dict[Path, tuple[str, list[str], bool, str | None]] = {}
    for slice_ in survivors:
        memory_dir = slice_.transcript.parent / "memory"
        if memory_dir not in planes:
            planes[memory_dir] = _read_plane(memory_dir, dedup, distil)
        index_text, examples, has_names, pending_error = planes[memory_dir]
        try:
            result = distil.distil(slice_, examples, has_names)
            if isinstance(result, distil.Discard):
                turned_down = result.slice_
                discards.append(
                    _PublishedDiscard(turned_down.transcript, turned_down.line_no, result.reason)
                )
                continue
            proposals.append(_type_proposal(result, memory_dir, index_text, pending_error, dedup))
        except FileNotFoundError as exc:
            return proposals, discards, f"the distil stage stopped, no claude CLI: {exc}"
    return proposals, discards, None


def _distil_and_publish(
    survivors: list[Slice], limit: int, out_dir: Path
) -> tuple[dict[str, object], str | None, str | None]:
    """Run the distil stage over the first `limit` survivors (0 means no cap)
    and publish what it produced to `out_dir`.

    The cap is applied once here so the survivors distilled and the ones
    counted as skipped can never be measured against two different rules.

    Returns (counts, stage_error, publish_error). Publication is attempted
    before the report is written, so a report on disk can never name a
    proposals directory that is not there.
    """
    capped = survivors[: limit or None]
    proposals, discards, stage_error = _run_distil(capped)
    new_count = sum(1 for record in proposals if proposal.updated_name(record.kind) is None)
    counts: dict[str, object] = {
        "proposals": len(proposals),
        "discards": len(discards),
        "new_vs_update": (new_count, len(proposals) - new_count),
        "skipped_by_limit": len(survivors) - len(capped),
        "dedup_errors": sum(1 for record in proposals if record.dedup_error is not None),
    }
    try:
        proposal.write_proposals(proposals, discards, out_dir)
    except OSError as exc:
        return counts, stage_error, f"failed to publish the proposals to {out_dir}: {exc}"
    return counts, stage_error, None


def _non_negative_int(value: str) -> int:
    """argparse type for --distil-limit. A negative cap would slice
    survivors from the end instead of capping them, so refuse it here."""
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError(f"must not be negative, got {number}")
    return number


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--project", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--distil", action="store_true")
    parser.add_argument("--distil-limit", type=_non_negative_int, default=25)
    return parser.parse_args(argv)


def _report_outcome(
    counts: dict[str, object],
    report_dir: Path,
    timestamp: str,
    errors: tuple[str | None, str | None, str | None],
    proposals_dir: Path | None,
) -> int:
    """Print the yield report, then every stage error, then write the report to
    `report_dir` and print where it landed.

    `errors` is (triage_error, distil_error, publish_error). Returns main's exit
    code: a failed publication ends the run before the report is written, and a
    triage or distil error is non-zero even though the report was written.
    """
    triage_error, distil_error, publish_error = errors
    report = render_yield(counts, proposals_dir)
    print(report, end="")

    for message in errors:
        if message is not None:
            print(message, file=sys.stderr)

    if publish_error is not None:
        return 1

    try:
        print(_write_report(report, report_dir, timestamp))
    except OSError as exc:
        print(f"failed to write report to {report_dir}: {exc}", file=sys.stderr)
        return 1

    return 1 if triage_error is not None or distil_error is not None else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: select transcripts, scan and (unless --dry-run)
    triage them, distil the survivors behind --distil, then print and write
    the yield report.

    Returns 0 on success. Returns non-zero on a stale or absent parser
    (`StaleParserError`), a triage model-call failure, a distil stage the
    missing CLI ended, a failed publication, or a report-write failure.
    """
    args = _parse_args(argv)
    if args.dry_run and args.distil:
        print("--distil is ignored with --dry-run: a dry run makes no model calls", file=sys.stderr)

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
        survivors, survivors_count, triage_error = [], None, None
    else:
        survivors, survivors_count, triage_error = _run_triage(kept_slices)

    counts: dict[str, object] = {
        "transcripts_read": len(transcripts),
        "slices_matched": matched_count,
        "slices_kept": len(kept_slices),
        "survivors": survivors_count,
        "claude_checkup_version": resolved_version,
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = _report_dir()
    distil_error = publish_error = None
    published_dir = None
    # A triage that failed handed the stage no input, so the stage never ran and
    # its counts stay "n/a". An empty survivor list from a triage that ANSWERED
    # is a stage that ran and found nothing, which still publishes and reports 0.
    if args.distil and not args.dry_run and triage_error is None:
        out_dir = report_dir / f"distil-memory-{timestamp}-proposals"
        distil_counts, distil_error, publish_error = _distil_and_publish(
            survivors, args.distil_limit, out_dir
        )
        counts.update(distil_counts)
        published_dir = out_dir if publish_error is None else None

    return _report_outcome(
        counts, report_dir, timestamp, (triage_error, distil_error, publish_error), published_dir
    )


if __name__ == "__main__":
    sys.exit(main())

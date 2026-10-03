# Design: Distil Memory Candidates: Extraction and Funnel (PRD 00007)

## Architecture fit

New skill `skills/distil-memory/` (this repo's standard shape per `AGENTS.md`:
a directory under `skills/` holding `SKILL.md` plus `scripts/`). No existing
module owns transcript access or funnel logic, so this is greenfield within
the repo, but it deliberately does not vendor `claude-checkup`'s parser: it
resolves and dynamically imports the plugin cache's `parser.py` at runtime
(the version-glob idiom named in the PRD), matching the CLI-script invocation
convention already used by `skills/brief-portfolio` (`collect.py`) and
`skills/purge-devlocal` (`purge_devlocal.py`): a `scripts/*.py` module that is
both an importable library (for PRD 00008's `judge` reuse) and its own
argparse CLI entry point, invoked directly by `SKILL.md`.

`corpus.py` sits below `funnel.py` per the PRD's Dependency Graph (Foundation
-> Core -> Integration). Neither module talks to any other skill in this
repo; `corpus.py`'s only external dependency is the `claude-checkup` plugin
cache, resolved by path glob, never a pinned version.

## Module placement

New files only, matching the PRD's Structural Decomposition exactly:

- `skills/distil-memory/SKILL.md` (new)
- `skills/distil-memory/scripts/corpus.py` (new)
- `skills/distil-memory/scripts/funnel.py` (new)
- `skills/distil-memory/scripts/test_corpus.py` (new)
- `skills/distil-memory/scripts/test_funnel.py` (new)

No edits to any existing file.

## Interfaces & contracts

### `corpus.py`

```python
from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

# The one named constant the PRD's Risk "the plugin cache root moves" points
# at. Migrating claude-checkup to the agent-plugins standard is one edit here.
_CACHE_ROOT = Path.home() / ".claude" / "plugins" / "cache" / "buvis-plugins" / "claude-checkup"
_PROJECTS_ROOT = Path.home() / ".claude" / "projects"
_MIN_VERSION = "0.2.2"
_REQUIRED_PARSER_SYMBOLS = ("parse_session", "SessionData")


class StaleParserError(RuntimeError):
    """Raised by assert_contract() on a below-minimum or contract-broken parser."""


def _version_key(name: str) -> tuple[int, ...]:
    """`"0.2.2"` -> `(0, 2, 2)`. Non-numeric segments sort below every real
    version. Copied from `hooks/strunk-ruling-inject.py:_version_key` (that
    file lives under `~/.claude/hooks/`, outside this repo's import graph, so
    the ~4-line idiom is duplicated rather than imported)."""
    return tuple(int(part) if part.isdigit() else -1 for part in name.split("."))


def resolve_parser(cache_root: Path = _CACHE_ROOT) -> tuple[ModuleType, str]:
    """Import the highest installed claude-checkup version's parser.py.

    Returns (module, version_string). Raises StaleParserError if the cache
    root is missing/empty or the winning version has no parser.py at
    `skills/audit-sessions/scripts/parser.py`.
    """
    try:
        versions = [d for d in cache_root.iterdir() if d.is_dir()]
    except OSError:
        versions = []
    if not versions:
        raise StaleParserError(f"no claude-checkup versions found under {cache_root}")
    winner = max(versions, key=lambda d: _version_key(d.name))
    parser_path = winner / "skills" / "audit-sessions" / "scripts" / "parser.py"
    if not parser_path.is_file():
        raise StaleParserError(f"claude-checkup {winner.name} has no parser.py at {parser_path}")
    spec = importlib.util.spec_from_file_location("claude_checkup_parser", parser_path)
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(module)
    return module, winner.name


def assert_contract(
    version: str, parser_module: ModuleType, minimum: str = _MIN_VERSION
) -> None:
    """Raise StaleParserError naming the resolved version and the minimum
    when `version < minimum`, or naming any of _REQUIRED_PARSER_SYMBOLS
    missing from `parser_module`. Message states the over-count consequence
    (claude-checkup d10ecb1's promptSource=="sdk" fix), not "parse failed"."""
    if _version_key(version) < _version_key(minimum):
        raise StaleParserError(
            f"claude-checkup {version} is older than the required {minimum} "
            f"(the release carrying d10ecb1's promptSource=='sdk' fix) - "
            f"the resolved parser over-counts user prompts by roughly 41%. "
            f"Install claude-checkup {minimum} or newer."
        )
    missing = [s for s in _REQUIRED_PARSER_SYMBOLS if not hasattr(parser_module, s)]
    if missing:
        raise StaleParserError(
            f"claude-checkup {version}'s parser.py is missing {missing} - "
            "it no longer matches this skill's contract."
        )


def select_transcripts(
    days: int = 30, all: bool = False, project: str | None = None
) -> list[Path]:
    """Return transcript paths under ~/.claude/projects/, resolving and
    contract-checking the parser first (raises StaleParserError on failure -
    propagates uncaught, per the PRD: "stop and report rather than lowering
    the minimum").

    - `all=True` skips the date filter entirely (returns every transcript in
      the selected project directories).
    - `days` (ignored when `all=True`) keeps transcripts whose
      `SessionData.latest` (parsed via the resolved parser) falls within the
      last `days` days of `datetime.now(timezone.utc)`. A transcript that
      fails to parse (`parse_session` returns None) or whose `latest` is
      None (a transcript predating timestamped entries) is KEPT, not
      dropped - matches parser.py's own documented negative-check choice
      (see module docstring reference below): silently dropping the
      un-timestamped case is exactly the failure mode this skill exists to
      avoid repeating.
    - `project`, when given, keeps only `~/.claude/projects/*` directories
      whose name ends with `-{project}` (a plain suffix match on the
      already-encoded directory name - see "Alternatives considered" for why
      this skill does not attempt to re-derive or decode the encoding).
      Zero matching directories is not an error: it returns an empty list,
      and the yield report's "transcripts read: 0" is the loud signal.

    Returns a sorted list for deterministic test assertions.
    """
```

### `funnel.py`

```python
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator


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

# Entry-level exclusions mirroring parser.py's _is_compaction, duplicated
# rather than imported: parser.py's helper is prefixed `_` (private, not
# part of the contract assert_contract() checks) and this skill's own
# assistant-side filter is explicitly the PRD's "no equivalent exists yet"
# gap, not a reuse of the user-side one.
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
    5. A "text" block that is empty or whitespace-only - nothing to slice.

    Returns one (line_no, text) pair per surviving text block.
    """
    out: list[tuple[int, str]] = []
    for line_no, entry in entries:
        if entry.get("isMeta") or _is_compaction_entry(entry):
            continue
        for text in _assistant_text_blocks(entry):
            out.append((line_no, text))
    return out


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


_MODEL_FOR_TIER = {"cheap": "haiku", "strong": "sonnet"}


def judge(prompt: str, tier: str) -> str:
    """The one model seam. tier in {"cheap", "strong"}; this PRD's own code
    only ever calls tier="cheap" (Haiku triage) - "strong" exists so PRD
    00008's distiller imports this same function rather than reinventing
    it. Default implementation shells out to the headless `claude` CLI the
    way skills/use-sonnet documents it (that plugin skill is not imported
    by filesystem path, per AGENTS.md "Never point at a plugin skill by
    filesystem path" - the invocation shape is reproduced directly):

        subprocess.run(["claude", "--print", "--model", model, prompt],
                        stdin=subprocess.DEVNULL, capture_output=True,
                        text=True, timeout=120)

    Raises RuntimeError(stderr) on nonzero exit. Callers (tests, and PRD
    00008) inject a stub via triage(slices, judge=<stub>) / a direct
    monkeypatch of funnel.judge - no test ever spends.
    """


_TRANSIENT = "transient"
_DURABLE = "durable"
_TRIAGE_PROMPT = (
    "Classify this snippet as exactly one word, {transient!r} or {durable!r}. "
    "{transient!r} means it verifies something already known or already "
    "working (a test pass, a build succeeding, a repeated confirmation). "
    "{durable!r} means it establishes a new fact worth remembering. "
    "Answer with exactly one of those two words, nothing else.\n\n{text}"
)


def triage(
    slices: list[Slice], judge: Callable[[str, str], str] = judge
) -> tuple[list[Slice], int]:
    """Cheap-tier pass. Survivors are slices whose judge() response,
    lowercased and stripped, is not exactly _TRANSIENT; an unparseable or
    unexpected response is treated as _DURABLE (fail open - never silently
    discard on a garbled response, matching parser.py's own documented
    negative-check precedent for the one predates-both-fields entry).
    Returns (survivors, discard_count).
    """


def render_yield(counts: dict[str, int | None]) -> str:
    """Pure string formatting (no subprocess calls, no file I/O - mirrors
    skills/sweep-fix/scripts/sweep.py:render_report's contract). `counts`
    keys, always all four, always printed even when 0:

        transcripts_read: int
        slices_matched: int
        slices_kept: int
        survivors: int | None   # None on a --dry-run (triage never ran)

    A run that finds nothing still prints every line, each ending "0" - the
    retired pipeline's silence is exactly what this excludes. Ends with a
    literal "How to proceed:" line naming dev/local/audit-results/ as where
    the report was also written, per this repo's skill-report convention
    (skills/brief-portfolio's brush-report.md; the discovery doc's own
    "Conventions" section)."""
```

### `SKILL.md` invocation contract

```bash
python3 ~/.agents/skills/distil-memory/scripts/funnel.py \
  [--days N] [--all] [--project NAME] [--dry-run]
```

`funnel.py` carries `main(argv=None)` / `if __name__ == "__main__":` (not a
listed "Export" - it is the CLI entry, not a symbol PRD 00008 imports).
`main()`:

1. Calls `corpus.select_transcripts(days=args.days, all=args.all, project=args.project)`.
   A `StaleParserError` propagates to a non-zero exit with the raised
   message printed - "stop and report rather than lowering the minimum."
2. Calls `matched, kept_slices = funnel.scan(transcripts)` - the single
   authoritative pass that yields both `slices_matched` (`matched`) and
   `slices_kept` (`len(kept_slices)`) from one read per transcript.
3. `--dry-run`: skip `triage()` entirely (zero model calls of any tier -
   "price a sweep before paying for it" reads as zero spend, not "only the
   expensive tier is zero"); `survivors = None`.
   Otherwise: `survivors_list, discarded = triage(kept_slices)`;
   `survivors = len(survivors_list)`.
4. `render_yield(counts)`, print it, and write it to
   `dev/local/audit-results/distil-memory-<UTC timestamp>.md`.

## Data flow

```
select_transcripts(days, all, project)
    -> corpus.resolve_parser()          # version-glob import, once
    -> corpus.assert_contract()         # loud failure or continue
    -> [Path, ...]                      # transcript files in scope
        -> _iter_entries(path)          # per transcript: (line_no, entry)
            -> assistant_only(entries)  # structural filter -> (line_no, text)
            -> _MARKER_RE.search(text)  # regex, no model
                -> Slice(...)           # kept slices, with provenance
    -> triage(slices, judge)            # Haiku tier, skipped on --dry-run
        -> judge(prompt, tier="cheap")  # subprocess -> claude --print
    -> render_yield(counts)             # pure formatting
    -> print + dev/local/audit-results/ # never silent, even at 0
```

PRD 00008's distiller imports only `judge` from `funnel.py` (cross-skill
import, see Alternatives) and calls it with `tier="strong"`; it consumes
`Slice` objects (or their `.text`/`.transcript`/`.line_no` fields) that this
PRD's funnel already produced - no data flows back into this PRD's modules.

## Reuse inventory

- `~/.claude/plugins/cache/buvis-plugins/claude-checkup/{0.2.1,0.2.2}/skills/audit-sessions/scripts/parser.py`
  - `parse_session(path) -> SessionData | None` and `SessionData.earliest`/`.latest`
    reused (via dynamic import, not copied) for `select_transcripts`'s
    date-window filter.
  - `_is_real_user_prompt` / `_SYNTHETIC_USER_PREFIXES` are the "solved
    upstream" user-side filter the PRD explicitly says this PRD does not
    need to touch or re-verify.
- `~/.claude/hooks/strunk-ruling-inject.py:210-227` (`_version_key`,
  `resolve_strunk_skills_dir`) - the version-glob-and-max idiom, duplicated
  (not imported - the file lives outside this repo, under `~/.claude/hooks/`)
  into `corpus.py`'s `_version_key`/`resolve_parser`.
- `skills/sweep-fix/scripts/sweep.py:485` (`render_report`) - shape reused
  (pure formatting function, ends with a literal "How to proceed:" block,
  no I/O inside the render function itself) for `render_yield`. Not
  imported: different domain (grep hits vs funnel counts), and it is
  sweep-fix's private module-scoped function.
- `skills/brief-portfolio/scripts/collect.py` and
  `skills/purge-devlocal/scripts/purge_devlocal.py` - both establish the
  convention this design follows: a `scripts/*.py` module is simultaneously
  an importable library and its own argparse CLI, invoked directly by
  `SKILL.md` with `python3 ~/.agents/skills/<name>/scripts/<file>.py`.
  `dev/local/audit-results/` as the report-write target: same two files
  (`brush-report.md`) plus the discovery doc's own "Conventions" section.
- Nothing found for a reusable "assistant-authored text only" filter:
  greps tried `assistant_only`, `assistant.*text`, `role.*assistant`,
  `thinking.*block` across `skills/**/*.py` and
  `~/.claude/plugins/cache/buvis-plugins/claude-checkup/0.2.2/skills/audit-sessions/scripts/*.py`
  (the latter has none - confirmed by reading the whole file, it only
  extracts user prompts and tool calls). This PRD's own `assistant_only` is
  the first implementation, matching the PRD's stated gap.
- Nothing found for `--project` name-to-encoded-directory resolution
  anywhere in this repo or `~/.claude/hooks/`: greps tried `project_path`,
  `encode.*project`, `-Users-.*-`. The one prior attempt at this encoding
  (the retired instincts pipeline, per `rules/memory.md`) got it wrong by
  only replacing `/`; see Alternatives for why this design deliberately
  does not attempt to re-derive it either.

## Alternatives considered

1. **Chosen: suffix-match `--project` against the already-encoded directory
   name** (`d.name.endswith(f"-{project}")`), no attempt to decode or
   re-derive the encoding. Smallest-diff option. Drawback: two differently
   organized repos ending in the same trailing segment (e.g. a hypothetical
   `not-agent-skills`) would both match `--project agent-skills`; accepted
   as a named, documented edge case for a solo-maintainer single-project
   pilot tool, not a multi-tenant selector.
2. **Re-derive the canonical path encoding** (replace `/` and `.` with `-`,
   matching the harness's own encoder) and glob for the exact match. More
   "correct" in principle, but this is the exact bug class that killed the
   retired instinct pipeline (`rules/memory.md`: "encoded the repo path by
   replacing `/` alone while the harness also replaces `.`... every repo
   under `github.com/` landed in a phantom sibling directory") - observed
   directly in this session's own catchup (`-Users-bob-git-src-github-com-buvis-claude-autopilot`
   vs `-Users-bob-git-src-github.com-buvis-claude-autopilot` for what should
   be the same repo). Rejected: the encoding is not reliably invertible or
   re-derivable from outside the harness, and getting it wrong silently
   drops a project's transcripts rather than failing loudly.
3. **Largest: have corpus.py accept an explicit absolute project directory
   path instead of a short name**, sidestepping the encoding question
   entirely. Rejected as worse ergonomics for the stated target user ("the
   solo maintainer, running an on-demand sweep") for a benefit (exactness)
   the suffix match already gets close enough to, given option 2 is
   unsafe. Revisit only if option 1's collision risk is ever hit for real.

## Risks & edge cases

- **Likely next change 1 (PRD 00008, the distiller)**: imports `judge` from
  this PRD's `funnel.py` via a sibling-scripts `sys.path.insert`, e.g.:
  ```python
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "distil-memory" / "scripts"))
  from funnel import judge
  ```
  This design boxes that in: `judge`'s signature (`prompt: str, tier: str`)
  and the two tier names (`"cheap"`, `"strong"`) must not change without
  updating 00008. Nothing else in `funnel.py` is a promised cross-PRD
  contract.
- **Likely next change 2 (PRD 00009, the walkthrough)**: consumes
  `triage()`'s survivor `Slice` list as input to the persisted proposal
  queue. `Slice` is frozen and its four fields
  (`text`/`transcript`/`line_no`/`marker`) are the contract; adding fields
  later is safe, renaming or removing one is not.
- **Likely next change 3**: `_MARKER_RE`'s vocabulary is a single named
  constant specifically so that tuning it (after a real `--dry-run` shows
  poor recall/precision) is a one-line edit, per the PRD's own "marker
  abundance is not candidate precision" risk.
- **`parser.py` changing shape underneath this skill**: `assert_contract`
  checks `hasattr(module, "parse_session")` and `hasattr(module,
  "SessionData")` specifically because those are the only two symbols this
  design calls; a rename of anything else in `parser.py` (e.g. `ToolCall`)
  would not be caught and is out of scope.
- **A transcript file mutates or grows between `select_transcripts` and the
  later marker-slicing pass** (a session still in progress when the sweep
  runs): not mitigated - the PRD's target user is an on-demand maintainer
  sweep, not a live-tailing tool, and re-running captures the tail on the
  next pass.
- **`_iter_entries` reading a very large single transcript line-by-line**
  is already bounded by the OS file buffer per line; no whole-file read.
  The corpus-size risk the PRD names is bounded upstream by
  `select_transcripts`'s day window and `--project`, not by anything in
  the per-line reader.

## Test strategy outline

Matches the PRD's own Test Strategy section one-for-one, plus the design's
own additions:

- `test_corpus.py`: `resolve_parser` against a fixture cache dir holding
  `0.2.1` and `0.2.2` subdirectories (resolves `0.2.2`); `assert_contract`
  raising `StaleParserError` on a version below `0.2.2` (message names both
  versions) and on a stub module missing `parse_session`/`SessionData`;
  `select_transcripts` against a fixture `~/.claude/projects/`-shaped tree:
  window filtering, `--project` suffix match, `--all` returning everything,
  and the "keep on missing/unparseable timestamp" negative-check case.
- `test_funnel.py`: `assistant_only` gets one test per enumerated exclusion
  (5 listed above, so 5 tests minimum); `slice_on_markers` on a fixture
  transcript with two markers returns two `Slice`s with correct
  `line_no`/`transcript`; `scan`'s matched-vs-kept distinction tested by
  planting a marker inside a compaction-summary entry (counted in
  `matched`, excluded from `kept`), plus a direct assertion that
  `slice_on_markers(transcripts) == scan(transcripts)[1]` so the wrapper
  can never drift from the authoritative pass; `triage` with a stub
  `judge` for both the transient-discard and unexpected-response-keeps
  cases (fail open); `judge`'s default path is never reached in any test -
  proven by a test that monkeypatches `subprocess.run` to raise and
  asserts it is never called when a stub `judge` is passed to `triage`;
  `render_yield` printing every stage including all-zero, and rendering
  `survivors=None` (dry-run) distinctly from `survivors=0` (a real run
  that triaged everything away). `main()` itself is covered by the PRD's
  two Critical-Scenario happy paths run end to end against 2-3 fixture
  transcripts under a temp `~/.claude/projects/`-shaped tree: (1) a normal
  run asserts the printed report and the written
  `dev/local/audit-results/distil-memory-*.md` file both match
  `render_yield`'s output for the counts independently computed by calling
  `scan()`/`triage()` directly, and (2) a `--dry-run` invocation asserts
  `survivors: n/a` in the report AND monkeypatches `subprocess.run` to
  raise, proving zero model calls of any tier reach it end to end (not
  just within `triage()` in isolation).
- Fixture transcripts are hand-written minimal JSONL (2-4 lines each), not
  sampled from the real corpus (which is out of repo and may contain
  private content per this repo's public-repo constraint).

## Review log

dispatch 1 (claude): cardinal-sin 0, blocker 2, non-blocker 4, question 2

- Fixed (blocker): matched-vs-kept counting named a helper (`main()`'s
  "local helper") that was never signed. Introduced `scan(transcripts) ->
  tuple[int, list[Slice]]` as the one authoritative pass; `slice_on_markers`
  is now a thin wrapper (`scan(transcripts)[1]`) and `main()` calls `scan()`
  directly.
- Fixed (blocker): no test exercised `main()`, where the matched/kept
  aggregation and `--dry-run` wiring actually live. Added `main()` coverage
  to `test_funnel.py`'s outline: both PRD Critical-Scenario happy paths run
  end to end against fixture transcripts, including the report file write
  and a full-stack proof that `--dry-run` reaches zero `subprocess.run`
  calls.
- Non-blocker (recorded, not fixed): `assistant_only`'s structural filter
  only excludes harness-generated artifacts; a genuine assistant text block
  that quotes/paraphrases injected content (e.g. a rule file) passes every
  exclusion and would still be sliced. Accepted as a residual risk matching
  the PRD's own Risk section - PRD 00008's distiller and dedup-against-memory
  step is where content-provenance, not structural filtering, belongs.
- Non-blocker (recorded, not fixed): `--dry-run` skips `triage()` entirely
  rather than running the cheap tier only, so it never estimates
  `survivors`. Considered stricter than the PRD's literal "no strong-model
  call" wording requires. Left as designed: "price a sweep before paying
  for it" is read as zero spend of any kind on a dry run, and the
  implementor can revisit if the yield report proves less useful without a
  survivor estimate.
- Non-blocker (recorded, not fixed): the PRD 00008 cross-skill
  `sys.path.insert` import snippet hardcodes a `parents[2]` depth with no
  existence assertion. Left as a note for PRD 00008's own design to harden
  when it's actually written.
- Non-blocker (recorded, not fixed): `triage()` has no hard cap on total
  `judge()` calls for a real `--all` sweep across the full corpus. Bounded
  today only by the day-window/`--project` filters and the advisory
  `--dry-run`; an explicit `--max-slices` flag is a reasonable future
  addition, not required for this slice.
- Question (recorded): `assert_contract`'s signature carries `parser_module`
  and `minimum` beyond the PRD's shorthand `assert_contract(version)`.
  Read as the PRD's shorthand omitting detail already justified by the
  Feature's own text ("also asserts the imported parser exposes what this
  skill calls"), not a real conflict.
- Question (recorded): unverified whether Claude Code ever sets
  `isMeta: true` on an assistant-role entry (parser.py's precedent for the
  check is user-role only). Left as an implementation-time check: if it
  never fires in practice, the module docstring should note the exclusion
  as defensive-only rather than empirically observed.

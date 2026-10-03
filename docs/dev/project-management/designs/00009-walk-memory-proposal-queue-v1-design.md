# Design: Distil Memory Candidates — Queue, Cursor and Walkthrough

PRD: `dev/local/prds/wip/00009-walk-memory-proposal-queue-v1.md` (slice 3/3)

## Architecture fit

The work lands entirely inside `skills/distil-memory/`, the skill PRDs 00007
and 00008 built as a five-stage pipeline (select → scan → triage → distil →
report). Slices 1 and 2 stop at typed, evidenced proposals published to
`dev/local/audit-results/distil-memory-<stamp>-proposals/`
(`proposals.json` + `discards.json` + one `<name>.md` per proposal, all
written atomically by `proposal.write_proposals`). This slice adds two new,
decoupled modules that consume that output — a persistence layer (`queue.py`)
and a memory-plane writer (`write.py`) — plus a walkthrough procedure appended
to `SKILL.md`. Nothing here touches `funnel.py`, `distil.py`, or `dedup.py`;
the pipeline's fifth stage (report) is unchanged.

Two repo-level constraints from prior slices still apply and shape this one:

- `funnel.judge(prompt, tier)` remains the only route to a model in this
  skill. This slice makes **zero** model calls of its own — `write_memory`
  writes `entry["file_text"]` verbatim (or the operator's edited replacement,
  itself produced by a chat-driven re-emit through the *existing* `strong`
  tier, per the PRD's "Re-emit on edit" feature — the re-emission is the
  walkthrough's job in `SKILL.md` prose, not a new code path in `queue.py` or
  `write.py`). Neither new module imports `funnel.judge`.
- The repo is public. No personal paths in code, tests, docstrings, or sample
  output — this design's examples below use `~/.claude/projects/<hash>/...`
  exactly as `funnel.py`'s own docstrings already do.

## Module placement

| Path | New/Edit | Contents |
|---|---|---|
| `skills/distil-memory/scripts/queue.py` | **new** | `PER_RUN_CAP`, `RUBRIC_VERSION`, `QueueError`, `slice_key`, `load`, `save`, `next_undecided`, `decide`, `cursor`, `advance`, `rejected`, `main` (CLI) |
| `skills/distil-memory/scripts/write.py` | **new** | `WriteError`, `write_memory`, `append_pointer`, `main` (CLI) |
| `skills/distil-memory/scripts/test_queue.py` | **new** | Phase 0 tests |
| `skills/distil-memory/scripts/test_write.py` | **new** | Phase 1 tests |
| `skills/distil-memory/SKILL.md` | **edit** | the walkthrough stage: one-at-a-time keep/edit/drop, re-emit-on-edit, the run report, the how-to-proceed block |

**Divergence from the PRD's Structural Decomposition, stated deliberately.**
The PRD's `queue.py`/`write.py` "Exports" lists name plain Python functions
only. A live walkthrough is chat-driven across many turns with no persistent
Python process holding state between them, so the agent must shell out
between turns to read/mutate the queue and to write memory files. Both new
modules therefore also carry a thin `argparse` CLI (`main(argv)` +
`if __name__ == "__main__": sys.exit(main())`), the same shape `funnel.py`
already uses (`_parse_args`/`main`) and `proposal.py` deliberately doesn't
need. The **pure functions are the tested contract** (Phase 0/1 exit criteria
run against them directly, matching the PRD's own Phase 2 acceptance text,
"Calling `decide()` directly with a scripted sequence"); the CLI is a thin,
untested-beyond-smoke wrapper `SKILL.md`'s prose invokes. See Interfaces below
for both surfaces.

## Interfaces & contracts

### `queue.py`

**Constants:**

```python
PER_RUN_CAP = 10       # walkthrough decisions per sitting; unbased guess, tune after first real run (PRD Risks)
RUBRIC_VERSION = "1"   # bump by hand when distil.py's _DISTIL_PROMPT changes meaningfully; re-opens drops made under the old value
```

**Storage.** One JSON file at `<funnel.py._report_dir()>/distil-memory-queue.json`
— literally the same `dev/local/audit-results/` directory the pipeline's
reports and proposals already land in, not a sibling. This is a deliberate
correction from an earlier draft that used a new `dev/local/distil-memory/`
top-level directory: this repo's `dev/local/` is swept by the `purge-devlocal`
GC (`~/.claude/skills/purge-devlocal/scripts/purge_devlocal.py`), whose
`KNOWN_DIRS` is a closed, cross-repo-enforced vocabulary
(`prds`/`designs`/`reviews`/`plans`/`tmp`/`autopilot`/`meta` plus the flagged
set `discovery`/`specs`/`notes`/`walkthroughs`/`audit-results`/`spikes`) — any
other top-level name ages out as `stale-foreign` after 7 idle days
(`purge_devlocal.py:233`, `--tmp-age-days` default). `audit-results` is
already in that flagged (never-trashed) set, and this queue must survive idle
gaps far longer than 7 days (draining 2,371 transcripts across many sittings
is the PRD's own stated scenario), so it has to live inside a name the GC
already recognizes rather than inventing a new one (`rules/working-documents.md`:
"Don't invent new top-level dirs"). No new directory is created; the file is
just one more name inside the directory `_run_distil`'s output already uses.

**On-disk shape:**

```json
{
  "cursor": 0,
  "session_decided": 0,
  "entries": [
    {
      "id": "<transcript>:<line_no>",
      "transcript": "<str path, exactly proposals.json's transcript field>",
      "line_no": 42,
      "name": "kebab-case-name",
      "kind": "new",
      "file_text": "<complete memory file: frontmatter + body>",
      "evidence_text": "<the slice text>",
      "existing_text": null,
      "decision": "undecided",
      "rubric_version": "1"
    }
  ]
}
```

`cursor` is a lifetime counter (total decisions ever made, only ever
incremented, useful for the run report). `session_decided` is a SEPARATE,
smaller counter — how many decisions have landed since the last sitting
started — and is what actually gates `next_undecided()` below; it is not
derived from `cursor` or from scanning `entries`.

`kind` is `"new"` or `f"update {existing-name}"`, exactly `proposal.NEW` /
`proposal.update_kind(name)`'s output — this slice imports those two symbols
from `proposal.py` rather than re-deriving the string shape. `id` is always
`slice_key(transcript, line_no)`; see below.

**Functions (the tested contract):**

```python
def slice_key(transcript: str, line_no: int) -> str:
    """`f"{transcript}:{line_no}"` — the stable identity of a proposal's
    source slice, shared by queue entry ids and the rejection record."""

def load(path: Path | None = None) -> dict:
    """The queue as a dict (`{"cursor": int, "entries": [...]}`,
    `{"cursor": 0, "entries": []}` when the file doesn't exist yet). `path`
    defaults to the resolved storage path above; every other function takes
    the same optional `path` param for the same default, so tests inject a
    `tmp_path` file without monkeypatching cwd."""

def save(proposals: list[dict], path: Path | None = None) -> int:
    """Enqueue `proposals` (each a dict with `name`, `kind`, `transcript`,
    `line_no`, `evidence_text`, `file_text`, `existing_text`) as new
    `"undecided"` entries stamped with the current `RUBRIC_VERSION`, and
    return how many were actually added.

    A candidate is silently skipped (not added, not an error) when its
    `slice_key` already names an entry in the queue (any decision state —
    never double-queue one slice) OR when `rejected(slice_key(...),
    RUBRIC_VERSION)` is true (a drop still stands under the current rubric).
    Persists atomically: write `queue.json.tmp` in the same directory, then
    `Path.replace` onto `queue.json` (the pattern `brief-portfolio/scripts/
    collect.py:write_snapshot` already uses in this repo)."""

def next_undecided(path: Path | None = None) -> dict | None:
    """The first entry (queue order) whose `decision` is `"undecided"`, or
    `None` — either because none remain, or because `session_decided` has
    already reached `PER_RUN_CAP` this sitting. This is the enforcement
    point: it is a hard code gate on the cap, not a convention the
    walkthrough is trusted to follow, and it is exactly what makes the PRD's
    acceptance text ("a queue of 25 proposals yields 10 in one run")
    verifiable by `test_queue.py` alone, without a chat loop. A genuinely
    undecided proposal is never skipped or lost by this gate — it is only
    ever deferred to the next sitting (see `advance()`)."""

def decide(entry_id: str, state: str, file_text: str | None = None, path: Path | None = None) -> None:
    """Set `entry_id`'s `decision` to `state` (`"kept"` or `"dropped"` only —
    `"undecided"` is refused, `QueueError`). When `file_text` is given
    (the edit-then-keep case), it replaces the entry's stored `file_text`
    in the same write. Increments both `cursor` and `session_decided` by 1
    (increments, not a recompute from `entries` — see `advance()` for why
    that distinction matters), in the same write. Raises `QueueError` if
    `entry_id` is not in the queue, or already holds a terminal decision
    (a slice can be decided once)."""

def cursor(path: Path | None = None) -> int:
    """The persisted lifetime cursor: the total number of decisions ever
    made. Monotonic — `decide()` is the only thing that increments it, and
    `advance()` never touches it."""

def advance(new_cursor: int | None = None, path: Path | None = None) -> None:
    """Start a new sitting: reset `session_decided` to 0, unlocking the next
    `PER_RUN_CAP` calls to `next_undecided()`. This is the walkthrough's
    normal call at the start of every session (`SKILL.md` step 0 below) and
    is what "a second run advances past them" means in the PRD text — after
    it, `next_undecided()` resumes from the first still-undecided entry in
    queue order, whichever ones those are (nothing about which specific
    entries were decided last sitting matters, so an entry `save()` appends
    mid-sitting is never hidden behind a stale boundary the way an
    index-based window would hide it — see "Alternatives considered").
    `new_cursor`, when given, ALSO force-sets the lifetime `cursor` field —
    a separate recovery/testing escape hatch (forcing a specific value in a
    fixture) that ordinary operation never needs, since `decide()` already
    keeps `cursor()` current on its own via plain increments. The two
    effects are independent: a bare `advance()` call touches only
    `session_decided`, never `cursor`."""

def rejected(key: str, rubric_version: str, path: Path | None = None) -> bool:
    """True when some entry has `id == key`, `decision == "dropped"`, and
    `rubric_version == rubric_version` (the *current* one, if the caller is
    `save()` — but the parameter makes this independently testable and
    lets a caller check against an arbitrary version)."""
```

`QueueError(ValueError)` — mirrors `proposal.ProposalError`'s shape (message
names the field/rule that failed).

**CLI (thin, `SKILL.md`'s walkthrough drives this, not the tests):**

```
python3 queue.py save --proposals-dir <dir>     # reads <dir>/proposals.json + each named <dir>/<file>, calls save(); prints "added N of M"
python3 queue.py start                          # calls advance() with no cursor arg — begin a sitting, unlock the next PER_RUN_CAP decisions
python3 queue.py next                           # prints the next-undecided entry as one JSON line, or prints nothing and exits 1 when none
python3 queue.py decide <id> kept|dropped [--file PATH]   # --file's contents become the edit replacement; calls decide()
python3 queue.py cursor                          # prints the lifetime cursor int
```

### `write.py`

```python
class WriteError(ValueError):
    """A write that must not happen. Message names why."""

def write_memory(entry: dict, store_path: Path) -> Path:
    """Write `entry["file_text"]` into `store_path`, named after the target
    stem, and return the path written.

    Stem: for `entry["kind"] == "new"`, `proposal.sanitise_name(entry["name"])`
    (imported from `proposal.py`, not re-derived). For an `"update <name>"`
    kind, `proposal.sanitise_name(proposal.updated_name(entry["kind"]))` —
    the file replaced is the one the update TARGETS, regardless of what the
    (possibly re-emitted) `file_text`'s own `name:` field now says.

    Preconditions, checked at call time, both raising `WriteError` (never
    creating a directory, never silently overwriting):
    - `store_path` must already exist (the PRD's Premise: "if the resolved
      store does not exist, stop and report rather than creating a
      directory").
    - the target file's existence must match the kind: `"new"` requires
      ABSENCE (refuses to clobber an unrelated existing memory that happens
      to share a stem); `"update ..."` requires PRESENCE (refuses to
      "update" a file that isn't there)."""

def append_pointer(store_path: Path, entry: dict) -> str | None:
    """Upsert one `MEMORY.md` bullet line for the file `write_memory` just
    wrote, matching `dedup._ENTRY`'s read-side format byte-for-byte
    (`- [Title](stem.md) — description`, real em-dash U+2014, since
    `dedup.parse_index` is what reads it back on the next distil run this
    memory plane participates in — this slice does not import that private
    regex, it duplicates the minimal shape needed to locate/replace one line).

    Title: `stem.replace("-", " ").capitalize()` — a mechanical, deliberately
    lossy approximation, NOT a faithful reconstruction of hand-written
    titles: checked against this repo's own two-line `MEMORY.md`, it
    reproduces `session-pins-plugin-version` -> "Session pins plugin
    version" correctly but gets `prd-phase-2-needs-a-human` -> "Prd phase 2
    needs a human" wrong (loses the `PRD` acronym's casing; real hand-written
    titles Title-Case every word and preserve acronyms). This is accepted,
    not fixed here: `distil.py`'s prompt only asks the model for a kebab-case
    `name`, never a separate display title, so no true title exists anywhere
    in the proposal/queue schema to recover — inventing one would mean
    changing `distil.py`'s prompt and schema, out of this slice's scope (see
    Risks & edge cases). Description: the new `file_text`'s frontmatter
    `description` field,
    verbatim (no model call to write a curated hook — the PRD's own
    architecture invariant is one route to a model, already spent by the
    distil stage that produced this text).

    For a `"new"` kind: always appends a new line, creating `MEMORY.md` if
    absent (creating the FILE is fine; only creating the `memory/` DIRECTORY
    itself is forbidden, and `write_memory`'s precondition already required
    it to exist). Returns the line written.

    For an `"update <name>"` kind: compares the new description against
    `proposal.parse_frontmatter(entry["existing_text"])["description"]`.
    Identical -> no file write, returns `None` ("leaves MEMORY.md unchanged
    when the description did not change"). Different -> replaces the
    existing bullet line for that stem in place and returns the new line;
    if no existing line is found for that stem (shouldn't happen for a
    genuine update, but self-healing beats a crash), appends instead."""
```

**CLI:**

```
python3 write.py write --store PATH < entry.json     # entry JSON on stdin (the same shape `queue.py next` prints); calls write_memory then append_pointer; prints the memory file path, then the MEMORY.md line or "MEMORY.md: unchanged"
```

Deliberately reads the entry from stdin rather than looking it up by id in
the queue itself: `write.py` stays ignorant of `queue.py`'s storage (matches
the PRD's Dependency Graph, "write.py depends on queue.py" only insofar as
the walkthrough passes queue-shaped JSON between them — no Python import
from `write.py` to `queue.py`), and Phase 1's exit criterion tests it
"against a temporary store" with hand-built fixtures, no queue file involved
at all.

### `SKILL.md` walkthrough stage (prose, not a module)

One iteration, repeated by the agent narrating it in chat, capped at
`queue.PER_RUN_CAP` (10) decisions per sitting — enforced by `next_undecided`
itself (see Interfaces above), not by the agent counting turns:

0. `python3 queue.py start` once, at the top of the sitting.
1. `python3 queue.py next`. Empty/exit 1 -> nothing left (either drained, or
   this sitting's cap is spent — the report in step 7 tells them apart by
   comparing `cursor()` to the queue's total entry count), stop and report.
2. Show the proposal: its evidence (`transcript`, `line_no`, `evidence_text`),
   and for an update, `existing_text` beside the proposed `file_text`. Ask
   keep / edit / drop — one at a time, no bulk affordance (`rules/
   communication.md`).
3. **Drop** -> `python3 queue.py decide <id> dropped`.
4. **Keep** (no edit) -> `python3 queue.py decide <id> kept`, then
   `python3 write.py write --store <derived path> < entry.json` (the entry
   JSON step 1 already printed).
5. **Edit** -> re-emit the *whole* file at the `strong` tier (reusing
   `funnel.judge`, the skill's one model-call route — this is the only new
   model call site slice 3 introduces, and it lives in `SKILL.md` prose plus
   whatever glue script Phase 2 needs, not in `queue.py`/`write.py`), validate
   the result with `proposal.validate_distil_output` before it ever reaches
   the queue (a failing re-emit is reported and the proposal STAYS
   undecided — "a re-emitted file failing the frontmatter contract -> not
   written, and the proposal stays undecided"), then
   `python3 queue.py decide <id> kept --file <edited-file-path>` followed by
   the same `write.py write` call as step 4 (which now reads the replaced
   `file_text`).
6. `store_path` (steps 4/5) is always `Path(entry["transcript"]).parent /
   "memory"` — the exact derivation `funnel.py`'s own
   `memory_dir = slice_.transcript.parent / "memory"` already uses. Computed
   by whoever drives the loop (the walkthrough prose / a small glue script),
   never inside `queue.py` or `write.py` — matches `write_memory`'s
   explicit `store_path` parameter, which exists precisely so Phase 1 can
   test against a fixture store instead of a hardcoded real one.
7. After the sitting ends (cap reached, or `next` returned empty): report
   counts of kept/edited/dropped, `queue.cursor()`, and the paths written,
   into `dev/local/audit-results/` (matching the pipeline's existing report
   convention) with the verbatim how-to-proceed block.

## Data flow

```
dev/local/audit-results/distil-memory-<stamp>-proposals/
  proposals.json  ──┐
  <name>.md ×N     ─┴─► queue.py save() ──► dev/local/audit-results/distil-memory-queue.json
                                                   │
                                    (chat loop, capped at PER_RUN_CAP)
                                                   │
                                     queue.py next_undecided()
                                                   │
                                    keep/edit/drop decision (chat)
                                                   │
                                     queue.py decide(id, state[, file_text])
                                                   │
                                    (kept only) write.py write_memory()
                                                   │           │
                                                   ▼           ▼
                              ~/.claude/projects/<hash>/memory/<name>.md
                              ~/.claude/projects/<hash>/memory/MEMORY.md (upsert)
```

`discards.json` (slice 2's pre-distil discards) is never read by this slice —
those slices were never proposals, so `queue.py` has nothing to do with them.

## Reuse inventory

- `proposal.sanitise_name`, `proposal.parse_frontmatter`, `proposal.NEW`,
  `proposal.update_kind`, `proposal.updated_name`,
  `proposal.validate_distil_output` (`skills/distil-memory/scripts/
  proposal.py`) — stem derivation, frontmatter parsing, and the update-kind
  string contract are reused verbatim rather than re-derived; the re-emit
  validation gate is the exact function slice 2 already uses.
- `dedup._ENTRY`'s bullet-line SHAPE (`- [title](name.md) — hook`, real
  em-dash) — read-side contract `write.py.append_pointer` must produce
  byte-compatible output for (`skills/distil-memory/scripts/dedup.py:23`,
  confirmed against `test_dedup.py`'s and `test_dedup_classify.py`'s own
  comments: "The separator in a real MEMORY.md bullet line is an em-dash
  (U+2014)"). Not imported (private symbol) — the shape is duplicated
  minimally in `write.py`.
- `funnel.py._report_dir()`'s "nearest `.git` ancestor of cwd" resolution —
  duplicated (not imported, it's a private function), and its RETURN VALUE
  is the exact directory `queue.py` writes `distil-memory-queue.json` into —
  not a new directory, the queue is a fourth kind of file in the same
  already-GC-recognized `dev/local/audit-results/` the reports and
  proposals already share.
- `funnel.py`'s `memory_dir = slice_.transcript.parent / "memory"`
  derivation — reused verbatim as the `store_path` computation the
  walkthrough performs before calling `write.py`.
- `brief-portfolio/scripts/collect.py:write_snapshot`'s tmp-file +
  `Path.replace` atomic-write idiom — reused for `queue.py`'s single-file
  persistence (simpler than `proposal.write_proposals`'s directory-staging
  dance, which exists because THAT writes many files atomically as one unit;
  `queue.json` is one file).
- `funnel.py`'s `argparse` CLI shape (`_parse_args` + `main(argv)` +
  `if __name__ == "__main__"`) — reused for both new modules' CLI surfaces.
- Greps tried before concluding no queue/cursor/pointer helper already
  exists in this repo: `rg "cursor"`, `rg "class.*Queue"`, `rg "def save\("`,
  `rg "next_undecided|undecided"`, `rg "append_pointer|MEMORY.md.*write"`,
  `rg "os.replace|tempfile|NamedTemporaryFile"` (found the two atomic-write
  idioms above, nothing queue-shaped), `rg "rubric"` (three prose mentions
  in `test_distil.py`, no `RUBRIC_VERSION`-shaped constant anywhere — this
  slice introduces the first one).

## Alternatives considered

1. **Windowed cursor** (`next_undecided()` bounded to
   `entries[cursor : cursor + PER_RUN_CAP]`, `advance()` required to unlock
   the next window) — rejected. A window keyed on raw list INDEX breaks the
   moment a later `save()` call appends new proposals while the cursor sits
   past their eventual index: those new entries would land BEHIND the
   window boundary and `next_undecided()` would never see them again without
   a manual `advance()` backward, which is exactly the silent-skip bug this
   feature exists to prevent.
2. **Cap enforced only by the walkthrough's own loop counter, queue.py
   stays a passive counter** — an earlier draft of this design. Rejected on
   design review: `test_queue.py` (Phase 0's own exit criterion) cannot then
   verify the PRD's literal acceptance text ("a queue of 25 proposals yields
   10 in one run") without simulating a whole chat loop's discipline inside
   the test — the guarantee would live in `SKILL.md` prose the agent is
   trusted to follow, not in code. **Chosen instead: a `session_decided`
   counter, separate from the lifetime `cursor`, that `next_undecided()`
   itself checks.** It keeps the safety property option 1 was rejected for
   protecting (an entry is only ever deferred to the next sitting, never
   permanently hidden, since the gate is a COUNT, not an INDEX into
   `entries`) while making the cap a real, `test_queue.py`-verifiable
   invariant instead of a convention.
3. **Smallest-diff version: no `write.py`, extend `proposal.py` instead** —
   rejected because `proposal.py`'s docstring already scopes it to "the
   record and the generic memory-file contract"; adding filesystem writes to
   it would blur a module slice 2's review already settled, and Phase 1's
   exit criteria name `test_write.py` as its own file.
4. **Chosen: two new decoupled modules, CLI-wrapped pure functions** — the
   PRD's own module list, sized to let Phase 0 test `queue.py` with zero
   filesystem coupling to slice 2's real output shape (fixtures build
   proposal dicts directly) and Phase 1 test `write.py` against a bare
   temporary store with no queue involved at all. The extra size over
   option 2 buys that isolation, which is what makes both phases'
   `uv run --with pytest pytest scripts/test_*.py` exit criteria
   independently meaningful.

## Risks & edge cases

- **The per-run cap of 10 is an unbased guess** (PRD's own stated risk) —
  `PER_RUN_CAP` is a single named constant in `queue.py`, so tuning it later
  is a one-line change with no ripple.
- **Likely next changes**: (a) the rejection record currently re-opens ALL
  drops on any rubric bump, repo-wide — a future slice might want per-memory
  or per-project rubric versions; `rubric_version` is already a per-entry
  field, not a global one, so that extension doesn't require a schema
  migration, only a different value passed to `save()`. (b) A future
  `--project NAME`-scoped walkthrough (mirroring `funnel.py`'s existing
  flag) would filter `next_undecided()` by `entry["transcript"]` — not
  built now (PRD doesn't ask for it), but the entry schema already carries
  the field it would filter on.
- **This design boxes in**: `entries` as a flat, ever-growing JSON list with
  no compaction. A store with thousands of accumulated decided entries would
  make `load()`/`save()` O(n) on every call. Out of scope per the PRD's own
  Memory bloat risk section ("revisit if a store passes ~100 entries") —
  that risk is about target `MEMORY.md` files, not this tool's own queue,
  but the same "revisit at scale, not now" judgment applies here too.
- **Concurrent invocation**: two simultaneous walkthroughs (or a walkthrough
  racing a `save()` from a fresh funnel run) could lose a write under the
  read-modify-write pattern every function above uses. Out of scope — this
  is a solo-maintainer, one-terminal-at-a-time tool (PRD's Target Users),
  and no PRD acceptance criterion exercises concurrency.
- **A malformed `--file` edit path** (Phase 2 walkthrough step 5): handled
  by `proposal.validate_distil_output` raising before `decide()` is ever
  called — the entry is untouched and stays undecided, matching the PRD's
  stated error case exactly.
- **`MEMORY.md` pointer titles are mechanically derived and lossy**:
  `stem.replace("-", " ").capitalize()` loses acronym casing (`prd` stays
  lowercase instead of `PRD`) and any other proper-noun capitalization a
  hand-written title would carry — see `append_pointer`'s docstring above.
  Accepted as-is; fixing it for real means teaching `distil.py`'s prompt to
  emit a separate display title, which is a `distil.py`/`proposal.py` schema
  change outside this slice's module list.

## Test strategy outline

- `test_queue.py` (Phase 0, `uv run --with pytest pytest scripts/
  test_queue.py`): `save()` dedup by `slice_key` and by `rejected()`;
  `next_undecided()`/`decide()` round-trip across a simulated reload (two of
  five decided, reload, third returned, no duplicates); the cap scenario
  exactly as the PRD's own acceptance text states it — `save()` 25
  proposals, loop `next_undecided()`+`decide()` until `next_undecided()`
  returns `None` (this happens at exactly 10, confirmed by asserting
  `cursor() == 10` at that point with 15 entries still `"undecided"` in the
  queue — the gate firing with real work left is the behavior under test,
  not a test-side loop counter), call `advance()` (no cursor arg), assert
  `next_undecided()` now returns an 11th entry, and continue this "second
  run" to completion, asserting no id is ever returned twice across the
  whole sequence and `cursor() == 25` at the end; `rejected()` true under
  the recording rubric version, false after a version bump; `advance(n)`
  force-sets `cursor()` to `n` without touching `session_decided`; `advance()`
  with no argument resets `session_decided` without touching `cursor()`;
  `QueueError` on an unknown id, on `state="undecided"`, and on deciding an
  already-decided id twice.
- `test_write.py` (Phase 1, against `tmp_path` stores only — no real
  `~/.claude/projects/`): `write_memory` for `"new"` and for
  `"update <name>"` (writes to the target's existing stem, not the possibly
  different re-emitted name); `WriteError` on a missing store, on a `"new"`
  stem collision, and on an `"update"` target that doesn't exist;
  `append_pointer` appends for new, upserts in place for a changed update
  description, returns `None` and leaves the file byte-identical for an
  unchanged one, and produces a line `dedup.parse_index` can read back
  (round-trip assertion against the real `dedup._ENTRY` shape — not just
  eyeballed).
- Phase 2 exit criterion (PRD-specified, run headless): seed a queue of five
  proposals via `save()`, drive a scripted `decide()` sequence (three kept —
  one plain, one via the edit path with a stub re-emit — two dropped)
  against a `dev/local/tmp/` store, assert at least one memory file plus its
  pointer line, assert a dropped proposal's `slice_key` is `rejected()` on a
  simulated second `save()` over overlapping input, and assert the
  interrupted-and-resumed sequence (stop after two of five, reload, third
  undecided entry returned) — exactly the PRD's three named edge cases,
  exercised without a human answering keep/edit/drop live.

## Review log

**Dispatch 1 (claude).** 3 blockers, all fixed: (1) the queue's storage path
was a new, unrecognized `dev/local/` top-level directory that this repo's
`purge-devlocal` GC would trash after 7 idle days — moved into the existing,
GC-flagged `dev/local/audit-results/` directory instead. (2) the per-run cap
of 10 was enforced only by `SKILL.md` prose, not verifiable by
`test_queue.py` — redesigned around a `session_decided` counter that
`next_undecided()` itself checks, a real code gate. (3) the `append_pointer`
title-derivation claim ("verified against every existing MEMORY.md line")
was false — checked against a second real line and found wrong (loses
acronym casing); corrected to an honest "accepted, lossy" description.

Non-blocker ("`advance()`'s effect is silently clobbered by the next
`decide()`") was resolved as a side effect of fix (2): `decide()` now
increments `cursor`/`session_decided` rather than recomputing them, so an
explicit `advance(n)` value persists until the next decision, not just until
the next write.

Question recorded, not fixed (real but low-priority for a solo-maintainer
tool): `RUBRIC_VERSION` is a manual, unenforced convention — nothing ties a
change to `distil.py`'s `_DISTIL_PROMPT` to a required bump.

dispatch 1 (claude): cardinal-sin 0, blocker 3, non-blocker 1, question 1

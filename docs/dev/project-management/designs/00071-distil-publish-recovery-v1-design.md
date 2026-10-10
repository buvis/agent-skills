# Design: 00071 distil-memory publish recovery

## Architecture fit

All changes land in the `skills/distil-memory/` walkthrough stage (stage 6):
`scripts/write.py` (publish a kept entry: memory file + `MEMORY.md` pointer),
`scripts/docket.py` (the durable review queue and its CLI), `scripts/dedup.py`
(index parsing, read-only consumer here), and `SKILL.md` steps 5-7, which a
driver model follows verbatim. The capsule's seam rule holds: no model call is
added; `funnel.judge` stays the only model route. PRDs 00015-00017 are
foundations, not work: `load()`'s exit-2 contract for an unreadable queue,
`main`'s single queue read in `decide`, and `write.main`'s guarded
write-then-pointer transaction with `_rollback` all stay exactly as they are.

## Module placement

Edits only, no new production files:

- `skills/distil-memory/scripts/write.py` - `write_memory` (identical-content
  short-circuit), `append_pointer` (idempotent upsert for both kinds), new
  `published()`, new private `_pointer_state()`, `main` (catch
  `AttributeError`).
- `skills/distil-memory/scripts/dedup.py` - new public `parse_index_line()`.
- `skills/distil-memory/scripts/docket.py` - `decide` (keyword `name`,
  kept-to-kept recovery edit), new `unpublished()`, CLI: `decide --name`, new
  `unpublished` subcommand.
- `skills/distil-memory/SKILL.md` - steps 5, 6 and 7 rewritten.
- Tests (edits/additions): `scripts/test_write.py`, `scripts/test_write_cli.py`,
  `scripts/test_docket.py`, `scripts/test_docket_cli.py`,
  `scripts/test_walkthrough_integration.py`.

## Interfaces & contracts

### dedup.py

```python
def parse_index_line(line: str) -> tuple[str, str, str] | None:
    """(title, name, hook) of one index bullet line, or None when the line is
    not a bullet link. Uses the module's existing _ENTRY pattern."""
```

`parse_index` is left unchanged.

### write.py

```python
def _hook(description) -> str:
    """The canonical single-line pointer hook for a frontmatter description:
    " ".join(str(description).split())."""
```

A YAML block or folded scalar, or a description with leading/trailing
whitespace, is valid frontmatter but cannot survive `dedup._ENTRY`'s
`\s*—\s*(.*)$` parse unchanged. Every pointer is therefore built from, and
compared against, `_hook(description)`; `_pointer_line(stem, description)`
becomes `f"- [{_title(stem)}]({stem}.md) — {_hook(description)}"`. For a
single-line description with no edge whitespace (every existing test fixture)
`_hook` is the identity, so existing pointer-text assertions are unchanged.

```python
def _pointer_state(lines: list[str], stem: str, description: str) -> tuple[int | None, bool]:
    """Index of the first line whose parsed name equals `stem` (None when no
    line names it), and whether that line's hook equals _hook(description)."""
```

```python
def write_memory(entry: dict, store_path: Path) -> Path:
```
Behavior change, in this order after the frontmatter parse and `_target_stem`:
- `target.exists()` and its current text (`target.read_text()`, the same
  text-mode round trip `_atomic_write` used to write it) equals
  `entry["file_text"]` -> return `target` with no write, for a new entry and
  an update alike. A read failure (`OSError`, `UnicodeDecodeError`) raises
  `WriteError(f"{target}: {exc}")`.
- otherwise unchanged: new + exists -> `WriteError(f"{target} already exists")`;
  update + absent -> `WriteError(f"{target} does not exist")`; else
  `_atomic_write`.

```python
def append_pointer(store_path: Path, entry: dict) -> str | None:
```
New semantics, identical for new entries and updates except for the one
envelope check in step 1:
1. `stem, is_new = _target_stem(entry)`;
   `description = proposal.parse_frontmatter(entry["file_text"])["description"]`;
   for an update (`not is_new`), `proposal.parse_frontmatter(entry["existing_text"])`
   is still called and its result discarded: an update whose `existing_text`
   will not parse stays a malformed entry that raises `ProposalError` before
   the index is touched (`main` rolls the target back, as
   `test_write_crash_safety.py::test_main_write_restores_the_update_targets_original_bytes_and_reports_the_reason_when_the_entrys_existing_text_will_not_parse`
   pins). Its description is no longer compared - the old
   unchanged-description short-circuit is removed.
2. `lines` = the index split into lines via `_readable_bytes(...).decode()`
   when `MEMORY.md` exists, else `[]` (unchanged read).
3. `idx, current = _pointer_state(lines, stem, description)`.
4. `current` -> return `None`, nothing written.
5. `line = _pointer_line(stem, description)`; `idx is not None` ->
   `lines[idx] = line` (stale pointer replaced in place, title normalised);
   else `lines.append(line)`.
6. `_atomic_write(index_path, "\n".join(lines) + "\n")`; return `line`.

```python
def published(entry: dict, store_path: Path) -> bool:
    """True when the entry's target file holds exactly entry["file_text"] and
    MEMORY.md holds a current pointer for its target stem."""
```
- Target and description come from `_target_stem(entry)` and
  `proposal.parse_frontmatter(entry["file_text"])`, the writer's own rules.
- Target absent, or text differs -> `False`. Index absent, or
  `_pointer_state(...)[1]` false -> `False`.
- An unreadable target or index raises `WriteError` naming the file (target
  via the same read as `write_memory`, index via `_readable_bytes`).
- An entry envelope fault (`KeyError`, `TypeError`, `AttributeError`,
  `proposal.ProposalError`) propagates to the caller unchanged.

`main`, `write` command: the snapshot block's handler at `write.py:178`
becomes `except (WriteError, KeyError, AttributeError) as exc:` - a `"kind":
null` entry exits 1, reason on stderr, store and index untouched. Nothing else
in `main` changes; the guarded pointer block, `_rollback` and its diagnostics
are preserved byte for byte.

### docket.py

```python
def decide(entry_id, state, file_text=None, path=None, data=None, *, name=None):
```
- `state not in ("kept", "dropped")` -> `QueueError` (unchanged).
- Look up the entry with `id == entry_id` and `decision == "undecided"`.
  Found -> initial decision (unchanged): set `decision`, apply
  `file_text`/`name` when not None, increment `cursor` and `session_decided`
  by 1 each, `_save_queue` once.
- Not found -> recovery edit only when ALL hold: `state == "kept"`, an entry
  with that id has `decision == "kept"`, and at least one of `file_text`,
  `name` is not None. Then apply `file_text` and/or `name` to that entry,
  leave `cursor` and `session_decided` unchanged, `_save_queue` once.
- Anything else -> `QueueError(f"no undecided entry with id {entry_id!r}")`
  (same message as today; covers kept->dropped, dropped->anything, and a bare
  `decide <id> kept` on a kept entry).
- All field changes happen in memory before the single `_save_queue`, so a
  refusal or an earlier failure leaves the queue file untouched.

```python
def unpublished(store, path=None) -> list[str]:
    """Ids, in queue order, of the kept entries that own a target in the store
    at `store` and that write.published() does not confirm there."""
```
- `data = load(path=path)` (an unreadable queue raises `QueueError`).
- Index first: when `Path(store) / "MEMORY.md"` exists, read it once with
  `write._readable_bytes` before any entry is checked, so an unreadable or
  non-UTF-8 index raises `WriteError` (CLI: exit 1, diagnostic, empty stdout)
  even when every target is missing - a missing target can never hide a
  corrupt index behind a printed id list.
- Candidates: entries with `decision == "kept"` whose own store,
  `Path(entry["transcript"]).parent / "memory"` (the SKILL.md step 5 rule,
  now in code), resolves (`Path.resolve()`) to `Path(store).resolve()`.
  Entries of other stores are ignored, never listed: one distil run spans
  several projects (`corpus.py` walks every project dir unless `--project`),
  so one queue can feed several stores.
- Ownership: among the candidates, group by target stem
  (`write._target_stem(entry)[0]`); only the LAST kept entry of each group in
  queue order owns that target and is checked. Earlier kept entries for the
  same stem are superseded (a later update, or a later rename onto that
  stem) and are never listed, so a re-publish can never revert a newer
  memory and two entries can never alternate.
- For each owner: `write.published(entry, Path(store))`; `False`, or an
  envelope fault (`KeyError`, `TypeError`, `AttributeError`,
  `proposal.ProposalError`, raised by `_target_stem` or `published`) -> id
  listed. A candidate whose envelope faults before a stem can be derived is
  its own group and is listed.
- `write.WriteError` / `OSError` from a store or index read propagate (no
  partial result).
- `docket.py` gains `import write` (write does not import docket; no cycle).

CLI:
- `decide` gains `--name` (default None), passed as `name=args.name`. The
  existing order is kept: `--file` read first (exit 1 on failure), then one
  `load`, then `decide(..., data=data, name=args.name)`; `QueueError` from
  `decide` -> exit 1, from `load` -> exit 2.
- New subcommand `unpublished --store <path> [--queue <path>]`:
  - compute `ids = unpublished(args.store, path=args.queue)` fully before any
    output;
  - `QueueError` -> outer handler, exit 2 (unchanged);
  - `write.WriteError` or `OSError` -> stderr
    `cannot check the store <store>: <error>`, no stdout, exit 1;
  - `ids` non-empty -> each id on its own stdout line, exit 1;
  - empty -> no output, exit 0.

### SKILL.md

- Step 5: keep -> `decide kept` -> `write.py write`. A failed write is
  re-run with the same `entry.json` after fixing the cause; a re-run is safe
  (identical memory text and a current pointer are no-ops). "already exists"
  now means a DIFFERENT memory already holds that name: rename through step 6
  with a new `name` in the re-emitted frontmatter, then
  `docket.py decide "<id>" kept --name "<new-name>" --file "<edited-file-path>" --queue "<queue-path>"`
  (accepted on an already-kept entry), set `name` and `file_text` in
  `entry.json` to the same values, and re-run `write.py write`.
- Step 6: snippet becomes
  `index_has_names = bool(dedup.parse_index(dedup.read_index(Path("<store-path>"))))`;
  the edit-path `decide` works for an undecided entry and, for a recovery
  edit, for an already-kept one.
- Step 7: before the sitting report, for each distinct `<store-path>` among
  the queue's kept entries (each derived with the step 5 expression), run
  `python3 ~/.agents/skills/distil-memory/scripts/docket.py unpublished --store "<store-path>" --queue "<queue-path>"`.
  Exit 0 -> nothing unpublished in that store. Exit 1 with ids on stdout ->
  show the user each listed entry (id, target name, and why: file missing,
  text differs, or pointer missing) and ask, per entry, whether to publish it
  now; a memory the user deleted or hand-edited on purpose is declined, not
  restored. For each confirmed id, rebuild `entry.json` from that queue entry
  (snippet:
  `json.dumps(next(e for e in json.loads(Path("<queue-path>").read_text())["entries"] if e["id"] == "<id>" and e["decision"] == "kept"))`;
  the `decision` filter matters because `save` re-adds an id dropped under
  an older rubric, so a dropped and a kept entry can share one id), and show
  the user that same kept entry. Run `write.py write --store "<store-path>"`, and record its result. Attempt
  every confirmed id once per pass, then re-run `unpublished`; stop when it
  exits 0, or when a pass publishes nothing new (the confirmed ids it lists
  are the same set as the previous pass). List every id still printed, with
  its write's stderr, in the report. Exit 1 with empty stdout -> the store
  check failed (stderr names it); report it. Exit 2 -> queue unreadable;
  report it and write no sitting report.

## Data flow

Keep: driver -> `decide kept` (queue: undecided->kept, counters +1) ->
`write.main` -> snapshot target (`previous`) -> `write_memory` (no-op when the
target already holds the text) -> `append_pointer` (no-op when a current
pointer exists; else replace stale line or append) -> success; pointer fault
-> `_rollback(written, previous)` (restores bytes for a pre-existing identical
target, unlinks a target this run created).

Recovery: `unpublished` reads the queue once, keeps the kept entries whose
derived store is `--store`, reduces them to one owner per target stem (the
last in queue order), then reads each owner's target file and `MEMORY.md`
through `write.published`, returning ids. The driver asks the user per id,
rebuilds each confirmed entry from the queue and re-runs `write.main`. Each
target has exactly one owner, and a successful write makes that owner
published, so a confirmed id leaves the list after one successful pass; the
no-progress stop ends the loop when a write keeps failing. Rename: `decide kept --name --file` on the
kept entry rewrites `name` + `file_text` in one `_save_queue`;
`_target_stem` then derives the new stem from `entry["name"]` (new entries) or
keeps the `kind`-encoded stem (updates).

## Reuse inventory

- `write._target_stem(entry)` - target stem + new/update flag; reused by
  `published`, unchanged.
- `write._readable_bytes(path)` - UTF-8-checked index read raising
  `WriteError`; reused for the index read in `published`.
- `write._atomic_write(path, data)` - the only writer; unchanged.
- `write._pointer_line(stem, description)` - pointer text; now routes the
  description through `_hook` (identity for single-line descriptions).
- `dedup._ENTRY` regex (`dedup.py:23`) - the one index-line grammar; exposed
  through the new `parse_index_line` rather than a second regex.
- `docket.load`, `docket._save_queue`, `docket._resolve_path` - queue read,
  atomic save, default path; reused by `unpublished` and the recovery edit.
- `proposal.parse_frontmatter`, `proposal.updated_name` - description and
  update target; reused.
- Greps tried for an existing "is published" / idempotent check:
  `rg -n "published|idempot|already holds|same text" skills/distil-memory/scripts`
  - nothing found beyond `proposal.write_proposals`'s staging publication
  (a different concept: publishing the proposals directory, not a memory).

## Alternatives considered

1. **Smallest diff: SKILL.md-only recovery** (re-run write after deleting the
   orphaned file by hand; read the queue JSON to find kept entries). Rejected:
   defects 1, 2 and 5 are code facts (`_target_stem` ignores re-emitted
   frontmatter, `decide` is terminal, `next` skips kept entries); prose
   cannot make a refused command succeed.
2. **A persisted `published: true` flag on queue entries**, set by
   `write.main`. Rejected: `write.py` would have to know the queue path, and a
   flag can lie after a crash between the memory write and the flag write -
   exactly the window defect 5 describes. Checking the store itself is the
   source of truth.
3. **Chosen: idempotent writer + store-derived `unpublished` + kept-entry
   recovery edit.** Larger than (1) by two small functions and one CLI verb;
   the extra size buys convergence (re-running is always safe) and a check
   that cannot drift from what is on disk.

## Risks & edge cases

- **Tests pinning old behavior (mandated rewrites).**
  `test_write.py::test_append_pointer_new_always_appends_even_when_a_line_for_the_same_stem_already_exists`
  pins a duplicate pointer for a new entry; the PRD's "upsert a missing/stale
  pointer once" reverses it. Rewrite it, renamed
  `test_append_pointer_new_replaces_a_stale_line_for_the_same_stem_in_place`,
  asserting one line for the stem carrying the new description. Every other
  existing write/docket test keeps passing unchanged: the update-with-
  unchanged-description tests (`test_write.py:252`, `:374`,
  `test_write_cli.py:60`) all seed a current pointer line, which the new rule
  also answers with `None`; `test_docket_cli.py:228` (bare `decide kept` twice
  -> exit 1) stays refused because a recovery edit needs `--file` or
  `--name`; `test_write_crash_safety.py:584` (unparseable `existing_text` ->
  exit 1, target restored) stays green because `append_pointer` still parses
  an update's `existing_text` as an envelope check. Re-audited by `rg -n
  existing_text` over `test_write_crash_safety.py`, `test_write_refusals.py`
  and `test_write_cli.py`: :584 is the only test that depends on that parse
  failing; the rest pass a parseable `existing_text`. These suites are also
  PRD 00076's rebinding target; this PRD adds tests beside them and rewrites
  only the one named test.
- **Deliberately removed or hand-edited memories.** A kept entry whose memory
  the user later deleted or edited by hand is listed by `unpublished` (its
  target no longer matches). Step 7 asks before re-publishing, so the user
  declines it; the entry stays listed in later sittings' checks until a
  later decision supersedes it. Accepted: listing is informational, nothing
  is written without a per-entry yes, matching the skill's "no automatic
  write" rule.
- **Hand-titled index lines.** "Current" compares the hook only, so an index
  line whose title differs from `_title(stem)` is not rewritten when its
  description already matches; only a stale or missing pointer is touched.
- **Multi-store queues.** One distil run can span several projects
  (`corpus.py` walks every project dir unless `--project`;
  `test_funnel_distil_dedup.py::test_main_types_each_projects_proposal_against_that_projects_own_memory_plane`),
  so one queue can feed several stores. `unpublished` derives each entry's
  store from its transcript and treats `--store` as a filter, and step 7 runs
  it once per distinct store, so an entry is only ever checked and re-written
  against its own store.
- **Windows line endings.** Identity is decided by `read_text()` against
  `file_text`, the inverse of the `write_text` that wrote it, so CRLF
  translation on Windows does not make an identical file look different.
- **Likely next changes:** PRD 00076 rebinds the crash-safety and refusal
  tests (same files); PRD 00077 widens `docket.py`'s read guards and guards
  `_save_queue` in `save`/`decide`/`start`. Neither is boxed in: `unpublished`
  adds no new read guard pattern, and the recovery edit uses the same single
  `_save_queue`.

## Test strategy outline

- `test_write.py`: the PRD's
  `test_write_memory_returns_the_target_when_it_already_holds_the_same_text`,
  `test_write_memory_still_refuses_a_different_existing_file`; idempotent
  pointer for a new entry (second call returns None, index bytes unchanged);
  missing pointer for an unchanged-description update is appended; the
  rewritten stale-line test above; a block-scalar (multi-line) description
  and one with leading whitespace each publish once and then read as
  current (second `append_pointer` returns None, `published` True); `published` true/false cases (missing file,
  different text, missing pointer, stale pointer, unreadable index raises).
- `test_write_cli.py`: the PRD's
  `test_main_write_reports_a_pointer_failure_to_stderr_and_returns_one_without_a_traceback`
  (patch `write.append_pointer` to raise `OSError`); null `kind` -> exit 1,
  stderr non-empty, no traceback, store and index bytes unchanged (red first
  against old code); writing the same new entry twice through `main` leaves
  memory and index bytes identical.
- `test_docket.py` / `test_docket_cli.py`: the PRD's
  `test_decide_kept_again_with_name_and_file_replaces_both`,
  `test_decide_kept_to_dropped_is_still_refused`,
  `test_unpublished_lists_kept_entries_whose_file_is_missing_and_exits_one`;
  plus superseded entries (two kept updates for one stem: only the later is
  checked, the earlier never listed), entries of another store ignored, a
  kept `new` entry superseded by a later update not listed,
  stale update content, missing pointer, explicit `--queue`, unreadable
  queue -> exit 2, unreadable index -> exit 1 with empty stdout (including
  when every listed target is also missing), recovery edit
  leaves `cursor` and `session_decided` unchanged. Existing
  `test_docket_exit_codes.py` tests stay green unchanged.
- `test_walkthrough_integration.py`: collision-rename scenario (two kept
  entries claiming one name; second write refused; `decide kept --name --file`
  then write succeeds) and pointer-retry scenario (pointer write fails, rolled
  back, re-run succeeds, `unpublished` returns `[]`).
- `validate_skill.py skills/distil-memory/` passes after the SKILL.md rewrite.

## Review log

Dispatch 1 (claude) blockers, fixed in the doc: (1) `unpublished` re-listed
superseded kept entries for one target and the step-7 loop could alternate
and revert newer memories - now one owner per target stem, user confirmation
per id, and a no-progress stop; (2) "one queue maps to one store" was false -
`unpublished` now derives each entry's store and filters by `--store`, step 7
runs per store; (3) removing the `existing_text` parse broke
`test_write_crash_safety.py:584` - the parse stays as an envelope check.

Dispatch 1 non-blockers (recorded, not fixed):
- `_pointer_state` matches only the first line for a stem; indexes written by
  the old always-append rule can hold duplicate lines for one stem (first
  stale + second current leaves two current lines; first current + second
  stale leaves the stale one). `dedup.parse_index` keeps the last
  occurrence, so the two can disagree. Suggested: treat "current" as exactly
  one matching line with the current hook, else rewrite the first match and
  drop the rest in the same write; add a duplicate-seeded test.
- Hook equality is not normalised: a description with leading whitespace or a
  newline (YAML block scalar) never equals the parsed hook, so
  `append_pointer` rewrites every run and `published` stays False.
  Suggested: normalise with `" ".join(description.split())` in both the
  pointer line and the comparison, or refuse a multi-line description.
- The step-7 rebuild snippet can pick a dropped entry sharing the id (a drop
  under an older rubric re-added as kept); add `and e["decision"] == "kept"`.
- `import write` in `docket.py` pulls yaml and the funnel import chain into
  every queue verb; import it lazily inside `unpublished()`.
- When `write_memory` short-circuits, a later pointer fault still rewrites the
  identical target in `_rollback` and can print a spurious "rollback failed";
  have `write_memory` report whether it wrote, or accept it.

Dispatch 1 questions (recorded):
- Step 7: does one failed write stop the remaining ids? (The fixed text now
  says every confirmed id is attempted once per pass.)
- A name-only recovery edit can leave `entry["name"]` and the frontmatter
  `name` inconsistent; require `file_text` with `name`, or check the two
  agree before saving.

dispatch 1 (claude): cardinal-sin 0, blocker 3, non-blocker 5, question 2

Dispatch 2 (codex) blockers, fixed in the doc: (1) a valid multi-line or
edge-whitespace description could never read as published - pointers are now
built from and compared against the canonical `_hook(description)`; (2) the
step-7 rebuild snippet could publish a dropped entry sharing the id - it now
filters `decision == "kept"`; (3) a missing target let `unpublished` print ids
without reading a corrupt index - the index is now read once up front.
(Items 1 and 2 were dispatch-1 non-blockers; codex showed they break the
PRD's idempotence and "no automatic write" contracts, so they were promoted.)

Dispatch 2 non-blockers (recorded, not fixed):
- Duplicate pointer lines: `_pointer_state` uses the first match,
  `dedup.parse_index` keeps the last; repair duplicates during upsert and
  cover both orderings (same as dispatch 1's first non-blocker).
- The CRLF claim is too broad: a `file_text` that already contains `\r\n`
  (LF frontmatter, CRLF body) fails the `read_text()` identity after a
  text-mode write, so a re-run reports a collision. Suggested: normalise line
  endings before queueing or compare a normalised form; add mixed-ending
  identity tests. (`file_text` reaches the queue through `read_text()` in
  `docket.py:218`/`:250`, which already normalises, so this needs a
  hand-built entry.)
- Windows encoding: `_atomic_write` uses locale-default `write_text` while
  `_readable_bytes` requires UTF-8; a cp1252 process writes an em dash the
  next check rejects. CI sets `PYTHONUTF8=1`. Suggested: explicit UTF-8 for
  store reads and writes.
- `unpublished`'s store routing reads `entry["transcript"]` before the
  envelope-fault handling; a missing/null transcript escapes as an uncaught
  exception. Suggested: treat it as an envelope fault (listed) or a
  queue-schema error, with no partial stdout.
- Pointer failure after a short-circuited `write_memory` still runs
  `_rollback` on an untouched target (same as dispatch 1's last
  non-blocker).

dispatch 2 (codex): cardinal-sin 0, blocker 3, non-blocker 5, question 0

Dispatch 3 (codex verification) confirmed no open cardinal sins or blockers.
Non-blockers (recorded, not fixed):
- An invalid `--store` (a regular file) with no matching owners makes
  `unpublished` return `[]` and exit 0; validate an existing store path as an
  accessible directory first, test a regular-file store.
- Duplicate pointer lines, first-match vs last-match (repeat of dispatches 1
  and 2).
- Missing/null `transcript` escapes `unpublished`'s routing as an uncaught
  exception; raise `QueueError` naming the entry, keep stdout empty (repeat).
- CRLF identity for a hand-built entry with CRLF already in `file_text`
  (repeat).
- Locale-default encoding in `_atomic_write` vs UTF-8 in `_readable_bytes`
  (repeat).
- Rollback rewrites an untouched identical target after a pointer failure
  (repeat).
Question (recorded): step 7 does not say how declined entries are reported
(they have no write stderr) or whether confirmations persist between passes;
suggested: confirm once per recovery check, stop when no confirmed pending
entry disappears, report declined entries separately from failed writes.

dispatch 3 (codex): cardinal-sin 0, blocker 0, non-blocker 6, question 1

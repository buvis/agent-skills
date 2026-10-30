# Design: Large skipped directories may resurface on every Glean scan

## Architecture fit

Glean's deterministic half (`skills/glean/scripts/glean.py`) is a single
flat script: `load_ledgers` validates and merges `BUILTIN` + local + public
ledger entries, `describe(rel)` characterizes one untracked candidate (file,
symlink, or directory), and `cmd_scan` walks every untracked path, looks up
a matching ledger entry, and buckets the path into `candidates` (never
decided), `resurfaced` (a prior volatile decision that no longer covers the
current content/age), or counts it `settled` (quietly covered). This PRD's
work lands entirely inside that existing shape: `describe` gains a fallback
fingerprint for the one case it does not characterize today (a directory
above `MAX_DIR_FILES`), and `cmd_scan`'s "did this change" comparison in the
volatile branch gains a second comparison path that reads that fallback
field when the primary `sha256` field is absent. No new module, no new
ledger file, no new CLI command.

## Module placement

All changes are edits to existing files; no new files.

- `skills/glean/scripts/glean.py` — `describe()` gains the large-directory
  fallback fingerprint; `load_ledgers()`'s volatile-entry validation accepts
  the fallback field as an alternative to `sha256`; `cmd_scan()`'s volatile
  comparison reads whichever field the candidate actually produced.
- `skills/glean/scripts/test_glean.py` — Phase 0 reproduction test (new,
  isolated-home, real `cmd_scan` call, >200-file directory, asserts the
  pre-fix resurfacing) plus, if confirmed, the Phase 1 regression suite for
  the fingerprint (stays quiet, resurfaces on a count/mtime change, resurfaces
  on expiry, both volatile verdicts, legacy ledger entries with only
  `sha256`, existing small-directory hash behavior unchanged).
- `skills/glean/SKILL.md` — the ledger schema section (lines 35-57) gains one
  sentence naming the new optional field and when it appears, only if Phase 1
  runs.

## Interfaces & contracts

**`describe(rel: str) -> dict`** (`skills/glean/scripts/glean.py:135`) — the
`kind == "dir"` branch (lines 144-160) changes shape only for the
over-cap case. Today:

```python
if p.is_dir():
    files = [f for f in sorted(p.rglob("*")) if f.is_file() and not f.is_symlink()]
    c.update(kind="dir", files=len(files), soft_hits=0)
    for f in files[:MAX_DIR_FILES]:
        ...
    if len(files) > MAX_DIR_FILES:
        c["hints"].append(f"prescreen capped at {MAX_DIR_FILES} files")
    elif sum(f.stat().st_size for f in files) <= MAX_FILE:
        c["sha256"] = hashlib.sha256(...).hexdigest()
    return c
```

New shape — add one `else` to the existing `if len(files) > MAX_DIR_FILES`
branch so the over-cap path gains a fingerprint instead of nothing:

```python
if len(files) > MAX_DIR_FILES:
    c["hints"].append(f"prescreen capped at {MAX_DIR_FILES} files")
    c["count_mtime"] = f"{len(files)}:{int(max(f.stat().st_mtime for f in files))}"
elif sum(f.stat().st_size for f in files) <= MAX_FILE:
    c["sha256"] = hashlib.sha256(...).hexdigest()
```

- `count_mtime` is a string `"<file count>:<latest mtime, whole seconds,
  int>"`. String (not two separate int fields) because it slots into the
  existing single-field volatile-entry shape (`{..., "sha256": "<hex>"}` or
  `{..., "count_mtime": "<count>:<epoch>"}`) with no schema branching beyond
  "which field is present."
- `files` here is the *uncapped* list already computed on the line above
  (`sorted(p.rglob("*"))`, before the `files[:MAX_DIR_FILES]` prescreen
  slice) — the fingerprint must see every file, including ones past the
  prescreen cap, or a change outside the first 200 files is invisible to it.
  `st_mtime` is a cheap `stat()` call already paid for implicitly by
  `rglob`'s directory walk; no extra filesystem pass.
- A directory at or under `MAX_DIR_FILES` is unaffected: it still gets
  `sha256` exactly as today. `count_mtime` and `sha256` are mutually
  exclusive on one `describe()` result — never both, never neither (every
  dir branch falls into exactly one of the two `if`/`elif` arms, or neither
  when `sum(size) > MAX_FILE`, which is pre-existing undescribed behavior
  this PRD does not touch).

**`load_ledgers(local_path: Path) -> tuple[dict, list[dict]]`**
(`skills/glean/scripts/glean.py:61`) — the per-entry validation at line
79-80:

```python
if v in VOLATILE and not e.get("sha256"):
    sys.exit(f"glean: volatile entry {e.get('path')} needs sha256")
```

becomes:

```python
if v in VOLATILE and not (e.get("sha256") or e.get("count_mtime")):
    sys.exit(f"glean: volatile entry {e.get('path')} needs sha256 or count_mtime")
```

Every existing ledger entry (all carry `sha256` today) still validates
unchanged; only a newly-written large-directory entry needs the new field.

**`cmd_scan(cfg: dict, entries: list[dict]) -> dict`**
(`skills/glean/scripts/glean.py:185`) — the volatile-entry comparison at
line 205:

```python
changed = c.get("sha256") != entry["sha256"]
```

becomes:

```python
changed = (
    c.get("count_mtime", c.get("sha256")) != entry.get("count_mtime", entry.get("sha256"))
)
```

This is the one line that fixes the false-resurfacing: today `c.get("sha256")`
is `None` for an over-cap directory against a real `entry["sha256"]` string,
so `changed` is unconditionally `True` and the directory resurfaces every
scan regardless of actual change. After this edit, when `c` carries
`count_mtime` (over-cap) it is compared against the entry's `count_mtime` (or,
for a legacy entry that only has `sha256` from before this directory crossed
the cap, against that `sha256` — which will differ, correctly resurfacing
once so the operator re-decides with a fingerprint the entry can actually
carry going forward). When `c` carries `sha256` (at-or-under cap, the
unchanged path today) behavior is identical to today's line.

No other call site reads `entry["sha256"]` with the subscript form that
would now need a guard — line 80's membership check above is the only other
reader, already fixed.

## Data flow

1. `cmd_scan` lists untracked paths via `git ls-files -o`.
2. For each path, it finds the matching ledger `entry` (if any) and calls
   `describe(rel)` to characterize the current on-disk state.
3. For a directory over `MAX_DIR_FILES`: `describe` now stamps
   `count_mtime` instead of leaving the dict fingerprint-less; for a smaller
   directory or a file, the existing `sha256` path is unchanged.
4. `cmd_scan`'s volatile branch picks whichever fingerprint field `c`
   produced and compares it to the entry's own fingerprint. Equal + not
   stale → `settled` (quiet). Different, or stale by the existing 180-day
   rule → `resurfaced`, carrying the existing `previous` block whose
   `reason` field already distinguishes `"content changed"` from
   `"decision older than 180 days"` — no change to that branch.
5. Nothing downstream of `cmd_scan`'s return dict changes shape: the JSON
   output schema gains one possible field (`count_mtime`) inside a
   `candidates`/`resurfaced` entry, additive only.

## Reuse inventory

- `skills/glean/scripts/glean.py:106` `sha256(p: Path) -> str` — the existing
  per-file hash helper; untouched, still used for small directories and
  files. No new hashing helper is introduced.
- `skills/glean/scripts/glean.py:156-159` the existing directory-hash
  construction (`"".join(f"{f.relative_to(p)}\0{sha256(f)}\n" ...)`) is the
  pattern this design mirrors for shape (one string fingerprint stored under
  one dict key), not reused directly — it needs per-file content, which is
  exactly the cost the over-cap branch exists to avoid paying.
- `skills/glean/scripts/glean.py:144-146` the `files` list (uncapped
  `rglob` walk) is reused as-is; no second filesystem walk is added.
- nothing found for an existing mtime/fingerprint helper elsewhere in the
  repo; greps tried: `rg -n "st_mtime|strftime|isoformat" skills/*/scripts/*.py`
  (no hits outside test files), `rg -n "fingerprint" skills/` (only this
  PRD's own comment at `glean.py:156` and `SKILL.md:56`), `rg -n
  "count_mtime|latest_mtime|file_count" skills/glean` (no hits — confirms
  nothing to reuse and nothing to collide with).

## Alternatives considered

1. **Chosen: count + latest-mtime string fingerprint, computed from the
   already-walked uncapped `files` list.** Smallest diff: one new field on
   one existing dict, one new comparison branch, no new ledger file, no new
   CLic flag, no second directory walk. Weaker than a content hash (two
   different large trees can coincidentally share a file count and a
   max-mtime second, though in practice a directory large enough to hit this
   path changing without touching its newest-mtime file is rare), which the
   PRD's own Risks section accepts explicitly.
2. **Hash a bounded sample (e.g. the `MAX_DIR_FILES` already prescreened,
   sorted by mtime) instead of count+mtime.** Rejected: a sampled hash still
   needs `sha256()` calls the whole point of `MAX_DIR_FILES` is to avoid
   paying for a 10,000-file directory, and a sample can miss a changed file
   outside the sample just as easily as the mtime fingerprint can miss one
   that preserves both metadata values — no accuracy win for the extra cost.
3. **Smallest-diff alternative: skip the fingerprint; instead have `describe`
   set `c["sha256"] = entry["sha256"]` (copy the prior verdict's hash forward)
   whenever the directory is over the cap, i.e. make an over-cap directory
   permanently unable to resurface on content change.** Rejected outright:
   this is exactly the "fabricate a content hash solely to force the
   suspected mismatch" the PRD forbids, and it would silently defeat
   resurfacing forever for any directory that grows past 200 files — the
   180-day expiry would become the only way such a directory is ever
   re-reviewed. The chosen design keeps resurfacing live (on both metadata
   change and expiry), it only makes repeated *unchanged* scans quiet.

## Risks & edge cases

- **Known weakness (PRD-accepted):** a directory that changes without
  changing its file count or its newest mtime (e.g. editing the content of
  a file that is not the most-recently-modified one, without adding or
  removing any file) will not resurface. This is strictly a known risk of
  using metadata instead of content; it is the reason Phase 1 is
  conditional on Phase 0 actually reproducing the complained-of behavior
  first, rather than speculative.
- **Legacy entries:** an existing ledger `skip`/`machine` entry for a
  directory that was small when decided (so it only carries `sha256`) and
  has since grown past `MAX_DIR_FILES`: the new comparison line reads
  `c.get("count_mtime", c.get("sha256"))` against
  `entry.get("count_mtime", entry.get("sha256"))` — `c` now has
  `count_mtime` (no `sha256`) while `entry` has only `sha256`, so they
  compare unequal and the directory resurfaces once. **After this fix
  ships**, that one resurfacing self-heals: the operator's next decision
  writes a `count_mtime` entry (now computable) and it goes quiet from
  there. No migration script needed. This self-healing is exactly what
  pre-fix code cannot do — pre-fix, `describe()` never computes anything
  for an over-cap directory to re-decide with, so the same resurfacing
  repeats on every scan forever; that permanence, not the one expected
  resurfacing at the moment of growth, is the defect Phase 0 confirms.
- **Likely next changes after this PRD:** (1) raising or making configurable
  `MAX_DIR_FILES`/`MAX_FILE` — the two cap constants this design reads but
  does not change; a future PRD should not need to touch the fingerprint
  logic to adjust them. (2) extending the same count/mtime fallback to the
  file-size cap (`MAX_FILE`) path, which today also silently omits `sha256`
  for an oversized single file with no fingerprint at all — out of scope
  here (the PRD names only directories), but the same `changed = c.get(...)
  != entry.get(...)` line already generalizes to that case for free if a
  later PRD adds `count_mtime`-equivalent data to that branch too. (3) a
  future ledger-format migration (PRD 00112's validation territory) should
  treat `count_mtime` as a first-class optional volatile field alongside
  `sha256`, not a special case.
- This design does not touch `BUILTIN`, `STABLE`, `VOLATILE`, the 180-day
  `RESURFACE_AFTER` constant, `secret_gaps`, `cmd_check_staged`, or any CLI
  flag — confirmed by the Interfaces section above naming every touched line.

## Test strategy outline

Carries the PRD's own Test Strategy verbatim (unverified status, not run end
to end) plus the concrete shape Phase 0/1 give it:

- **Phase 0 (mandatory, runs regardless of outcome):** `load_ledgers`
  rejects any volatile (`skip`/`machine`) entry with no `sha256`
  (`glean.py:79-80`), and `describe()` never produces a `sha256` for a
  directory already over `MAX_DIR_FILES` (`glean.py:153-154`) — so there is
  no reachable path where an operator decides a directory *while it is
  already over the cap*: the ledger entry that decision would need could
  never pass validation, and `SKILL.md:55` already assumes the operator
  copies a real `sha256` from a `describe()` result. The only reachable
  pre-fix repro is the **grow-past-the-cap** sequence: decide the directory
  while it is small (≤200 files, real `sha256` recorded, passes
  `load_ledgers` validation), then add files until it crosses
  `MAX_DIR_FILES`. The one resurfacing that follows immediately is
  *expected* (the recorded decision no longer matches the grown directory)
  and is not by itself evidence of the suspected defect — the defect is
  that under current code **no scan after that point can ever settle
  again**, because `describe()` never computes a `sha256` for an over-cap
  directory, so the operator has no value to re-decide with and
  `c.get("sha256")` stays `None` forever after. The test proves *that*: use
  the existing `home` fixture pattern in `test_glean.py` to create the
  directory with ≤200 files, run real `cmd_scan` once, write a `skip` entry
  with the `sha256` that run reported, add files until the directory
  exceeds 200, then run `cmd_scan` **twice more** with no further content
  change in between. The first of those two is expected to resurface (the
  decision changed under it); the second is the actual test: with nothing
  having changed between the first and second re-scan, a `sha256`-based
  comparison can never go quiet again (there is no `sha256` to write back),
  so it resurfaces identically a second time. Asserting that second,
  otherwise-pointless re-scan still resurfaces is what confirms the
  defect — a single resurfacing right after growth proves nothing, since
  that one is correct behavior either way. If the second re-scan instead
  settles, the defect is unconfirmed and Phase 1 is skipped. Phase 0
  deliberately never writes a new ledger decision between its two
  post-growth scans — under pre-fix code `describe()` gives the operator
  no fingerprint to write one with for an over-cap directory, which is
  exactly the absence the test is proving. Phase 1, by contrast, DOES
  record a new decision mid-sequence (next bullet) because the fix gives
  `describe()` something to record.
- **Phase 1 (conditional on Phase 0 confirming), if it runs:**
  - repeated unchanged scans of an over-cap directory stay `settled` — the
    regression pin for the fixed defect, run as: grow the directory past
    the cap (as in Phase 0), let it resurface once with its new
    `count_mtime` fingerprint attached to the `resurfaced` entry, record a
    fresh `skip`/`machine` ledger decision using that reported
    `count_mtime` value, then assert the next scan (content still
    unchanged) is `settled`, not `resurfaced` — the step Phase 0
    intentionally cannot perform pre-fix.
  - a file added to (or removed from) the over-cap directory, or its newest
    file's mtime changing, resurfaces it (`count_mtime` fingerprint moved).
  - the existing 180-day expiry still resurfaces an over-cap directory
    whose `count_mtime` is unchanged (expiry check is independent of which
    fingerprint field is in play).
  - both `skip` and `machine` volatile verdicts exercise the new branch
    (not just one).
  - a legacy ledger entry (only `sha256`, directory since grown past the
    cap) resurfaces once per the edge case above, without a `KeyError` or
    `TypeError` from the new `.get(...)` comparisons.
  - existing small-directory and file `sha256` behavior is unchanged
    (`test_skip_stays_quiet_while_content_unchanged`,
    `test_skip_resurfaces_when_content_changes`,
    `test_skip_resurfaces_after_180_days` keep passing with no edits).
  - `load_ledgers` accepts a volatile entry carrying only `count_mtime` (no
    `sha256`) and still rejects one carrying neither.

## Review log

- non-blocker (dispatch 1, claude): the claim that the new `st_mtime` pass
  for an over-cap directory is "already paid for" by the existing `rglob`
  walk is imprecise — no second *walk* is added, but a stat-equivalent pass
  over the full uncapped `files` list is new work for that branch (today's
  code only stats `files[:MAX_DIR_FILES]` via `prescreen`, or sums sizes
  only in the at-or-under-cap `elif`). Accepted as written; the design's
  point (no second `rglob`) stands, the cost phrasing was imprecise, not
  wrong about what matters (this stays O(uncapped file count) `stat()`
  calls either way, same order as the existing `rglob`).
- question (dispatch 1, claude): resolved in the Test strategy section
  above — the only reachable pre-fix repro is "decided small, grew large
  later," not "decided while already over cap."
- dispatch 1 (claude): cardinal-sin 0, blocker 1, non-blocker 1, question 1
- dispatch 2 (codex): cardinal-sin 0, blocker 1, non-blocker 0, question 0 weak
- dispatch 3 (codex): cardinal-sin 0, blocker 1, non-blocker 0, question 0


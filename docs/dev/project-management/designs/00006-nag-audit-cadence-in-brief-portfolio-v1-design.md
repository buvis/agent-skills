# Design: Put Config Maintenance on a Calendar (PRD 00006)

## Architecture fit

`brief-portfolio` is a two-layer pipeline: `scripts/collect.py` gathers
deterministic facts (git/gh, no LLM) into `data.json`, and `app/src/lib/derive.js`
turns that payload into pure-function derivations (`attention`, `todosFor`,
`externalTodos`, `allTodos`) consumed by the Svelte components at render time.
This PRD adds one collector function to each side of that boundary and expands
`externalTodos`'s single hardcoded "run claude-checkup" nag into a table-driven
set of per-audit cadence rows. No new module, no new pipeline stage, no Svelte
component changes — `Todos.svelte` already renders generic `{action, why,
urgency, kind, ...}` rows with no `kind`-specific branching (confirmed: no
`kind ===` in the component tree), so new `kind: 'maintenance'` rows render
for free.

## Module placement

Edits only, no new files:

- `skills/brief-portfolio/scripts/collect.py` — add
  `collect_audit_cadence(base=None)`, add `collect_purge_devlocal(path)`, wire
  the latter into `collect_repo`'s per-key loop, remove
  `collect_claude_maintenance` and its call site.
- **Rebuild the SPA and regenerate `assets/template.html`** (mandatory, not
  optional — see the callout after Interfaces below). `build.py` only injects
  `data.json` into a **pre-compiled** `assets/template.html`; it never runs
  Vite (`build.py:11,43-50` reads the template as a static file with one
  string-replace). Editing `derive.js` source alone ships nothing — the live
  brief keeps running whatever JS was compiled in last, until
  `skills/brief-portfolio/SKILL.md`'s "Rebuilding the SPA template" recipe
  (`npm install`, `npm run build`, `cp app/dist/index.html
  assets/template.html`, `npm test`) runs. This must be a task in the PRD's
  own Phase 2, immediately before its `build.py --out ...` step, or Phase 2's
  acceptance criterion ("the rendered file... carries one row per due or
  never-run audit") cannot pass — the shipped HTML would still contain the
  old `claude_maintenance_last` logic (confirmed:
  `assets/template.html` currently references `claude_maintenance_last` once
  and neither `audit_cadence` nor `purge_last_run`).
- `skills/brief-portfolio/scripts/test_collect.py` — remove the two
  `collect_claude_maintenance` tests and the now-dead import; add tests for
  the two new collectors.
- `skills/brief-portfolio/app/src/lib/derive.js` — add `AUDIT_CADENCE`, add
  `auditTodos(external, repos)`, change `externalTodos`'s signature to
  `externalTodos(external, repos)` and replace its single maintenance block
  with `auditTodos(external, repos)`, remove `MAINT_DUE_DAYS`, update the
  `allTodos` call site.
- **`skills/purge-devlocal/scripts/purge_devlocal.py`** — one file beyond the
  PRD's drafted Structural Decomposition (which lists only the 4
  `brief-portfolio` files). Added at dispatch-3 review: without this, the
  "clean run" gap in Risks & edge cases isn't a documented tradeoff, it's a
  goal-breaking defect — the row can never turn green no matter how often the
  maintainer correctly runs `purge-devlocal`, since a clean apply creates no
  dated directory for `collect_purge_devlocal` to find (see Risks, below, for
  the confirmed mechanism). This is a design-time correction of the PRD's own
  drafted file list, not scope creep: Feature 2's stated Behavior ("the
  newest `<date>` directory name... collected per repo") only holds if a
  directory is guaranteed to exist after every successful `--apply` run. The
  fix is one line in `process_store`'s existing `if args.apply:` block
  (`purge_devlocal.py:437-439`, alongside the existing `prune_empty_dirs`/
  `empty_old_trash` calls): `(store / TRASH_DIR / batch).mkdir(parents=True,
  exist_ok=True)`. This stamps today's batch directory unconditionally on
  every apply run, trashed-something or not; it does not touch the manifest
  format, `trash_file()`, or any existing test's assertions (confirmed:
  `test_empty_trash_ages_out_old_batches_only` and the other existing
  `TRASH_DIR` tests in `test_purge_devlocal.py` only assert presence/absence
  of *specific* dated dirs they themselves create, none assert the *absence*
  of an auto-created empty batch dir).
- `skills/brief-portfolio/app/src/lib/derive.test.js` — update the 12 existing
  `externalTodos(...)` call sites (`rg -n "externalTodos\(" derive.test.js`:
  lines 98, 108, 111, 114, 115, 116, 173, 181, 182, 193, 205, 206 — enumerate
  by search rather than trust this count, it is the kind of number that goes
  stale) to the new `external.audit_cadence` shape (relying on the `repos`
  parameter's `[]` default — see Interfaces below — so none of the 12 need a
  second argument added) and add the row-state tests the PRD's Phase 1 task
  specifies.

## Interfaces & contracts

### `collect.py`

```python
MACHINE_AUDIT_SKILLS = [
    "claude-checkup:audit-filesystem",
    "claude-checkup:audit-context",
    "claude-checkup:audit-config",
    "claude-checkup:audit-authoring",
    "claude-checkup:audit-sessions",
    "claude-checkup:audit-mcp-health",
]

def collect_audit_cadence(base: str | Path | None = None) -> dict[str, str | None]:
    """{skill: newest ISO day} for every skill in MACHINE_AUDIT_SKILLS,
    pre-seeded to None so a never-run audit is a present key with value
    None, per the PRD's Phase 0 contract — not merely absent (a caller doing
    result[skill] must not KeyError). Newest `ts` per skill, no lookback
    cutoff. Also includes any OTHER skill name found in the log (e.g.
    'purge-devlocal') at its newest day, for callers that want a generic
    lookup — but the six MACHINE_AUDIT_SKILLS keys are always present
    regardless of what's in the log. `base` overrides the file path (tests
    only); default ~/.local/share/agents/metrics/skills.jsonl. Missing file
    → every MACHINE_AUDIT_SKILLS key maps to None. Malformed JSON lines are
    skipped, matching collect_claude_skill_adherence's existing tolerance."""
```

Row shape read (matches `track_skills.py`, already in production):
`{"host": "claude", "skill": "<name>", "session_id": ..., "ts": "<iso-utc>",
"source": "loop|interactive", "tool_use_id": ...}`. Only `skill` and `ts` are
read. `ts` is truncated to its first 10 characters via the existing `iso_day`
helper (already used by `collect_issues`/`collect_prs`/etc. in this file) —
no new date-parsing helper needed.

**Revised after cross-model review (dispatch 2 below):** the first draft of
this function was fully generic (no hardcoded skill list, relying on
`dict.get(missing_key)` returning `None` as the "never run" signal). Codex
correctly flagged that against the PRD's literal Phase 0 wording — "Outputs:
`{skill: newest ISO day}` for the six machine-wide audits, with `None` where
a skill has never run" and the acceptance criterion "returns... `None` for a
skill with no rows" — both describe a dict that **contains** the key with
value `None`, not a key that is merely absent and happens to `.get()` as
`None`. `MACHINE_AUDIT_SKILLS` is a short, private list (module-level next to
`GITA_CSV`/`MAX_COMMITS`, not re-exported), so this is a small, contained
duplication against `derive.js`'s `AUDIT_CADENCE` (six shared strings) rather
than two competing sources of behavior — see Alternatives, below, for why
this beats the fully-generic version despite the duplication.

```python
def collect_purge_devlocal(path: str | Path) -> str | None:
    """ISO day of the newest dev/local/.trash/<date>/ directory in the repo
    at `path`, or None when dev/local/.trash/ is absent or has no
    date-named subdirectory. Matches the `collect_brush(path)` calling
    convention (repo path in, ISO day or None out)."""
```

Exact algorithm (spelled out because "no `.trash/` → `None`" alone left the
guard order ambiguous — `Path.iterdir()` raises `FileNotFoundError` if the
directory doesn't exist, so the directory check must come first, not inside
the loop): compute `trash = Path(path) / "dev/local/.trash"`; return `None`
unless `trash.is_dir()`; then iterate `trash.iterdir()`, keeping only entries
that are both directories (`Path.is_dir()`) and match
`^\d{4}-\d{2}-\d{2}$` — `purge-devlocal`'s own `.trash/manifest.tsv` sits
directly alongside the dated subdirectories, so the directory check is not
optional; return the lexicographically-newest matching name, or `None` if
none match.

Wiring (both are one-line additions to existing lists, no new call pattern):

- `collect_repo`'s per-key loop (`collect.py:360-369`) gains
  `("purge_last_run", lambda: collect_purge_devlocal(path))`, alongside the
  existing `("brush_last_run", lambda: collect_brush(path))` — same pattern,
  same error handling (the surrounding `try/except` already catches and
  records a per-key error string, unchanged).
- `main()` (`collect.py:452`) replaces
  `data["external"]["claude_maintenance_last"] = collect_claude_maintenance()`
  with `data["external"]["audit_cadence"] = collect_audit_cadence()`.

`collect_claude_maintenance` (current `collect.py:274-286`) is deleted in
full — nothing else calls it (`rg collect_claude_maintenance` across
`scripts/` and `app/src/` returns only its own definition and the one call
site above, confirmed at design time).

### `derive.js`

```js
export const AUDIT_CADENCE = [
  { skill: 'claude-checkup:audit-filesystem', horizonDays: 30, command: '/claude-checkup:audit-filesystem', scope: 'machine' },
  { skill: 'purge-devlocal',                  horizonDays: 30, command: '/purge-devlocal',                  scope: 'repo' },
  { skill: 'claude-checkup:audit-context',     horizonDays: 90, command: '/claude-checkup:audit-context',     scope: 'machine' },
  { skill: 'claude-checkup:audit-config',      horizonDays: 90, command: '/claude-checkup:audit-config',      scope: 'machine' },
  { skill: 'claude-checkup:audit-authoring',   horizonDays: 90, command: '/claude-checkup:audit-authoring',   scope: 'machine' },
  { skill: 'claude-checkup:audit-sessions',    horizonDays: 90, command: '/claude-checkup:audit-sessions',    scope: 'machine' },
  { skill: 'claude-checkup:audit-mcp-health',  horizonDays: 90, command: '/claude-checkup:audit-mcp-health',  scope: 'machine' },
]
```

Seven entries — the PRD's "seven rows a month" figure is this table's length,
not a promise that every render emits exactly seven todos (a `scope: 'repo'`
entry can emit zero, one, or many rows depending on how many gita repos are
overdue; see Alternatives for why `purge-devlocal` is repo-scoped while the
other six are not).

```js
export function auditTodos(external, repos = []) {
  // For each AUDIT_CADENCE entry:
  //   scope 'repo' -> for each repo in `repos`, look up repo.purge_last_run,
  //     emit a row per overdue/never repo (id:
  //     `${slug(r)}:audit:${skill}:${last ?? 'never'}`, repo: slug(r)).
  //     Unconditional on `external` — this branch depends only on `repos`.
  //   scope 'machine' -> ONLY when `external` is truthy (preserves the
  //     current code's `if (external) {...}` guard at derive.js:316-327 —
  //     `externalTodos(null)` must keep returning 0 rows, per the two
  //     existing tests at derive.test.js:116 and :205): look up
  //     external.audit_cadence?.[skill], emit at most one row (id:
  //     `claude:audit:${skill}:${last ?? 'never'}`, repo: '~/.claude'). A
  //     truthy `external` with no `audit_cadence` key (or a key missing this
  //     particular skill) still emits a 'never' row for it — matching the
  //     current maintenance-row behavior at derive.test.js:108
  //     (`externalTodos({review_requested: [], authored: []})` finds a
  //     `claude:maintenance:never` row today; the new equivalent is one
  //     `claude:audit:<skill>:never` row per machine-scope entry).
  // Due test for both scopes: daysAgo(last) === null || daysAgo(last) >= horizonDays
  // (reuses the existing `daysAgo` helper — same boundary rule already used
  // by the brush-cadence check at derive.js:102-104).
  // Row shape matches every other todo: {id, repo, kind: 'maintenance',
  // urgency: 'soon', importance: 'low', effort: 'medium', agent: command,
  // url: null, external: true, action: `Run ${command}`, why: <'never run' |
  // `last run ${aged}d ago`> + ` — target: one pass per ${horizonDays}d`}.
}
```

`externalTodos` gains a second parameter, defaulted so every existing
zero-arg-repos caller (including all 12 test call sites) keeps working
unchanged:

```js
export function externalTodos(external, repos = []) {
  // unchanged: review_requested / authored / error blocks
  // replaces the old `if (external) { const last = external.claude_maintenance_last; ... }`
  // block with: out.push(...auditTodos(external, repos))
}
```

`allTodos`'s call site (`derive.js:339`) changes
`...externalTodos(external)` to `...externalTodos(external, repos)` — `repos`
is already in scope there (`allTodos(repos, epics, external)`'s first
parameter).

`MAINT_DUE_DAYS` (`derive.js:16`) is deleted — superseded by the per-entry
`horizonDays` in `AUDIT_CADENCE`.

## Data flow

`track_skills.py` (Stop hook, already shipping, unmodified by this PRD) →
`~/.local/share/agents/metrics/skills.jsonl` → `collect_audit_cadence()` reads
it once per `collect.py` run → `data.json`'s `external.audit_cadence`. In
parallel, each gita repo's own `dev/local/.trash/<date>/` (written by
`purge-devlocal`'s trash-first GC, unmodified by this PRD) →
`collect_purge_devlocal(path)`, called once per repo inside `collect_repo` →
each repo object's `purge_last_run`. `build.py`'s own code is unmodified — it
just injects `data.json` verbatim as `#portfolio-payload` — but the compiled
JS it injects *alongside* (`assets/template.html`'s bundled script) must be
regenerated from the edited `derive.js` source via the SPA rebuild (Module
placement, above), or the browser runs stale logic against the new payload
fields. Once rebuilt, `derive.js`'s `auditTodos(data.external, data.repos)`
turns the two stamps into todo rows at render time, folded into `allTodos`'s
merged list the same way the old single maintenance row was, so `Todos.svelte`
needs no source changes of its own.

## Reuse inventory

- `iso_day(s)` (`collect.py:55-56`) — truncates an ISO timestamp to its date;
  reused for `ts` → day conversion in `collect_audit_cadence`, exactly as
  `collect_issues`/`collect_prs`/`collect_releases` already use it. Greps
  tried: `date|timestamp|iso` (verb/noun) across `collect.py` — this was the
  only existing date-truncation helper, confirming no duplicate needed.
- `collect_claude_skill_adherence(base=None)` (`collect.py:242-271`) — the
  direct precedent for reading `skills.jsonl` with a `base=None` override
  param and per-line `try/except json.JSONDecodeError` tolerance;
  `collect_audit_cadence` copies this exact shape rather than inventing a new
  one.
- `collect_brush(path)` (`collect.py:230-239`) — the direct precedent for a
  per-repo "newest stamp from a directory, or None" collector, and for the
  `("brush_last_run", lambda: collect_brush(path))` wiring pattern in
  `collect_repo`'s key loop; `collect_purge_devlocal` and its wiring mirror it
  exactly instead of introducing a second per-repo-collector pattern. Greps
  tried: `def collect_` (verb) across `collect.py`, `trash|purge` (noun)
  across `collect.py` and `skills/purge-devlocal/` — nothing already reads
  `dev/local/.trash/` from outside the `purge-devlocal` skill itself.
- `daysAgo(iso)` / the boundary rule `aged === null || aged >= HORIZON`
  (`derive.js:20`, already the exact test the current brush-cadence check
  uses at `derive.js:102-104` and the old maintenance check used at
  `derive.js:319`) — reused verbatim in `auditTodos` rather than restating the
  boundary logic a third time. Greps tried: `daysAgo|DUE_DAYS` (noun/verb)
  across `derive.js`.
- `slug(r)` (`derive.js:18`) — reused for the per-repo `purge-devlocal` row
  ids, matching every other per-repo id in `todosFor`.

## Alternatives considered

1. **(Chosen, after dispatch-2 correction) `collect_audit_cadence` pre-seeds
   `MACHINE_AUDIT_SKILLS` (six names) to `None`, then overlays newest-day from
   the log for those six plus any other skill found.** Matches the PRD's
   Phase 0 contract literally: the returned dict always **contains** all six
   keys, `None` when never run, not merely `.get()`-absent. Cost: the six
   names are duplicated as literal strings between `collect.py`'s
   `MACHINE_AUDIT_SKILLS` and `derive.js`'s `AUDIT_CADENCE` — accepted, see
   option 2 below for why this is the lesser problem.
2. **Fully generic `collect_audit_cadence` (no hardcoded list), fixed skill
   list lives only in `derive.js`'s `AUDIT_CADENCE`.** This was the original
   choice in this doc's first draft. Rejected on cross-model review: a plain
   dict never contains a key it was never told to seed, so a never-run audit
   would be **absent**, not present-with-`None` — that only reads as "`None`"
   through a caller's `.get(key)` default, which contradicts the PRD's Phase 0
   wording ("returns... `None` for a skill with no rows") closely enough that
   a planner copying this interface verbatim could reasonably write a test
   asserting `"claude-checkup:audit-filesystem" in result`, which the generic
   version would fail. Avoiding the six-string duplication was true but
   secondary to getting the literal contract right.
3. **Treat `purge-devlocal` as machine-wide too, aggregating across all gita
   repos into one row ("N repos overdue").** Rejected: a single aggregated row
   can't tell the maintainer *which* repo to run `purge-devlocal` in, breaking
   the contract every other row in this brief honors (repo-scoped action,
   `repo:` field driving which `RepoDetail.svelte` a click lands on). Per-repo
   rows (this design's `scope: 'repo'` branch) cost one extra loop, not a new
   module.

## Risks & edge cases

- **A clean `purge-devlocal --apply` run (nothing to trash) used to leave the
  stamp unchanged, not refreshed — fixed, see Module placement.** Confirmed
  against `skills/purge-devlocal/scripts/purge_devlocal.py:360-368,417-427`:
  `trash_file()` (the only thing that created a dated `.trash/<date>/`
  directory before this fix) ran only inside `if action == "trash":`, i.e.
  only when something was actually moved, so a successful run that correctly
  found nothing to purge created no new directory. **Revised at dispatch-3
  review**: this doc's first pass downgraded the gap to a documented,
  unfixed risk on the grounds that `purge_devlocal.py` sat outside the PRD's
  drafted file list. Codex correctly pushed back — the PRD's own Feature 2
  Behavior clause only holds if a directory is guaranteed to exist after a
  successful run, so this is goal-breaking, not a stylistic gap, and the fix
  is small enough (one line) to be in-scope rather than deferred. See Module
  placement for the fix and why the file-list divergence is justified rather
  than silent scope creep.
- **`purge-devlocal` can emit up to `len(repos)` rows** in one brief render if
  every gita repo is simultaneously overdue — unlike every other row kind,
  which is capped at one per repo per condition. Accepted: `todosFor` already
  has several per-repo row kinds (brush, PRs, issues) that scale the same way,
  and the brief's existing urgency sort + `quickWins` cap already handle a
  large todo list.
- **A repo with no `dev/local/` at all** (a non-PRD-workflow repo in the gita
  registry) returns `None` from `collect_purge_devlocal`, which reads as
  "never" and nags forever. Same accepted imprecision the PRD states for the
  brush cadence row today; not a regression this PRD introduces.
- **Next likely changes** this design should not box in: (1) a horizon becomes
  configurable instead of a hardcoded constant in `AUDIT_CADENCE` — the table
  shape (array of `{skill, horizonDays, command, scope}`) already supports
  reading `horizonDays` from a config file without touching `auditTodos`; (2)
  an eighth audit joins the roster — appending one `AUDIT_CADENCE` entry is
  the entire change, no code path branches on the list's length; (3)
  `purge-devlocal` itself becomes schedulable (the PRD's own "Automating
  purge-devlocal later" deferred risk) — this design's `collect_purge_devlocal`
  only reads `.trash/`, so scheduling the GC itself is unrelated to this data
  path and needs no rework here.

## Test strategy outline

Python (`test_collect.py`, `pytest`):
- `collect_audit_cadence`: missing file → all six `MACHINE_AUDIT_SKILLS` keys
  present, each `None` (not an empty dict — matches the pre-seeded contract
  in Interfaces); a fixture with a row for one `MACHINE_AUDIT_SKILLS` member
  and one for `purge-devlocal` → the seeded skill's key resolves to its
  newest day, the other five seeded keys stay `None`, and `purge-devlocal`
  also appears in the result at its own newest day (the "namespaced key and
  unnamespaced key both resolve" acceptance criterion, satisfied by the
  seeded-plus-generic-overlay design); a malformed JSON line is skipped,
  matching `collect_claude_skill_adherence`'s existing malformed-line test.
- `collect_purge_devlocal`: no `dev/local/.trash/` → `None`; one dated
  subdirectory → that date; two dated subdirectories → the newer one
  (mirrors `test_reads_generated_date_from_brush_report`'s single-value
  case and a `collect_brush`-style "picks the newest" case); a plain file
  (not a directory) named `2026-08-01` under `.trash/` → not picked up.
- Delete `test_maintenance_none_when_dir_absent_or_empty` and
  `test_maintenance_returns_newest_mtime_day` (dead code for a removed
  function) and the now-unused `collect_claude_maintenance` import.

`test_purge_devlocal.py` (`pytest`, added at dispatch-3 review alongside the
`purge_devlocal.py` fix in Module placement):
- A clean `--apply` run (nothing eligible for trashing — mirror
  `test_dry_run_moves_nothing`'s fixture but call `run(store, "--apply")`)
  → `(store / gc.TRASH_DIR / today).is_dir()` is `True`, matching the pattern
  `test_empty_trash_ages_out_old_batches_only` already uses for `today`.
  This is the regression test for the fix: before it, this exact fixture
  left `.trash/` either absent or missing today's entry.
- Confirm no existing test breaks: `test_refuses_a_project_that_is_not_a_store`
  (`.trash/` asserted absent) exits via `SystemExit` before `process_store`
  runs at all; `test_dry_run_moves_nothing` and the engram-harvest test near
  line 753 (`.trash/` asserted absent) both call `run(store)` **without**
  `--apply`, so the new `mkdir` (guarded on `args.apply`) never executes for
  either — traced by hand against the current file, not assumed.

JS (`derive.test.js`, `node --test`):
- `AUDIT_CADENCE`/`auditTodos` row-state tests per the PRD's own Phase 1
  acceptance: for both horizons (30d via `purge-devlocal`, 90d via any
  `claude-checkup:*` entry), age 0 → no row, age horizon-1 → no row, age
  horizon+1 → a row, missing stamp → a row whose id ends `never`, **and the
  exact horizon age itself → a row** (the PRD's own ±1 framing doesn't
  actually pin whether the boundary is `>` or `>=`; the implementation
  contract above is `>=`, so assert the exact-horizon case explicitly rather
  than leaving `>` vs `>=` untested — this is the free addition from
  dispatch-2 review, not a new requirement).
- A `purge-devlocal` case with two repos, one overdue and one fresh → exactly
  one row, scoped to the overdue repo's slug.
- Regression: `externalTodos(null)` (both existing call sites,
  derive.test.js:116 and :205) must still return an empty array — the
  machine-scope branch of `auditTodos` is gated on `external` being truthy,
  so this stays true even though the repo-scope branch no longer depends on
  `external` at all. Verify explicitly rather than trusting that porting the
  old `if (external)` guard silently "just works".

**Migrating the 12 existing `externalTodos(...)` call sites — precise,
call-site-by-call-site (dispatch-2 review found the original one-line
instruction here — "the `kind === 'maintenance'` filter stays valid" —
insufficient: with `MACHINE_AUDIT_SKILLS` pre-seeded, EVERY machine audit
without an explicit `audit_cadence` entry now emits its own `never` row, so
six rows can share `kind === 'maintenance'` at once. A bare
`.find(t => t.kind === 'maintenance')` silently picks whichever
`AUDIT_CADENCE` entry happens to be first in table order — it must become
`.find(t => t.id.startsWith('claude:audit:<skill>:'))` wherever the test
needs one specific audit's row):**

- Line 98 (`ext = externalTodos({review_requested:[...], authored:[...]})`,
  asserts `ext[0]`/`ext[1]`): **no change needed.** `auditTodos`'s rows are
  appended after the review/authored rows, so indices 0 and 1 are unaffected
  regardless of how many maintenance rows follow.
- Line 108 (`externalTodos({review_requested: [], authored: []})`, asserts
  `maintNever.id === 'claude:maintenance:never'` and `action` matches
  `/audit-filesystem/`): update the id assertion to
  `` `claude:audit:claude-checkup:audit-filesystem:never` `` and select the
  row via `.find(t => t.id.startsWith('claude:audit:claude-checkup:audit-filesystem:'))`
  rather than the bare `kind` filter — it happened to still pass by table
  order in a manual trace, but that is exactly the fragility to remove.
- Line 111 (`externalTodos({claude_maintenance_last: day(45)})`, asserts
  `why`/`id`): `claude_maintenance_last` is dead — this field is never read
  once `collect_claude_maintenance` is removed. Replace the fixture with
  `externalTodos({audit_cadence: {'claude-checkup:audit-filesystem': day(45)}})`
  and select via the same `id.startsWith(...)` pattern as line 108. **Exact
  assertion, no alternative wording** (dispatch-3 review found the prior
  "or whatever exact wording" escape hatch let this contradict the
  Interfaces pseudocode's `why` template, `` `last run ${aged}d ago`` — the
  two must be the same string, so pin it here rather than leave it to the
  planner to reconcile):
  `assert.match(maint45.why, /^last run 45d ago/)` and
  `assert.equal(maint45.id, `` `claude:audit:claude-checkup:audit-filesystem:${day(45)}` ``)`.
- Lines 114–115 (`day(30)` "due" / `day(10)` "fresh, no row" — **both use
  the dead `claude_maintenance_last` field and, left as-is, line 115 becomes
  a real failure, not just a vacuous pass**: with `audit_cadence` unset,
  all six `MACHINE_AUDIT_SKILLS` are `never`, so
  `.find(kind === 'maintenance')` finds a row even for the "fresh" case).
  Replace both fixtures with `audit_cadence: {'claude-checkup:audit-filesystem': day(30)}}` /
  `{..., 'claude-checkup:audit-filesystem': day(10)}` and select via
  `id.startsWith('claude:audit:claude-checkup:audit-filesystem:')` so each
  assertion isolates that one skill's row instead of any-of-six.
- Line 116 / 205 (`externalTodos(null).length === 0`): unchanged (see the
  regression case above).
- Lines 173, 181–182, 193, 205–206 (`isErrTodo` / `kind === 'external'`
  filters): unchanged — these filter by `kind: 'error'` / `'external'`,
  neither of which `auditTodos` rows carry.

Fixture-driven Python integration test (`test_collect.py`): a fixture
`skills.jsonl` plus a fixture repo `.trash/` tree, run through `collect_repo`
(or the two collectors called directly), asserting `data.json`'s
`external.audit_cadence` and a repo's `purge_last_run` both land correctly —
this is the deterministic check; save the live run for Phase 2.

**Phase 2's live-machine run is NOT a fixture-driven check** (correcting this
doc's earlier claim, made during the first review pass, that it was
fixture-shaped and needed no [[prd-phase-2-needs-a-human]] rework — that
citation conflated two different things: the PRD's `--out
dev/local/tmp/brief-check.html` flag only relocates the *output* to stay
inside the unattended write fence, it says nothing about the *input*.
`build.py`'s `--dir` flag controls the data source and defaults to
`~/.local/share/agents/portfolio-brief/` — the PRD's Phase 2 task never
passes `--dir`, so it runs `collect.py` for real against the live gita
registry, exactly as the PRD's own task text says: "against the live
machine"). Run, in order: (1) the SPA rebuild (Module placement, above), (2)
`collect.py` for real, (3) `build.py --out dev/local/tmp/brief-check.html`
(default `--dir`, i.e. live data), (4) read the output HTML and confirm it
contains at least one `audit_cadence`-derived row (a live environment's exact
overdue count is not knowable in advance, so the acceptance check is "the
markup contains rows naming `claude-checkup:` or `/purge-devlocal` commands
and the run completed with no prompt", not a fixed row count). No prompt,
question, or interactive step at any of these four steps — all are plain CLI
invocations.

## Review log

- dispatch 1 (claude): cardinal-sin 0, blocker 2, non-blocker 1, question 2
  - Fixed (blocker): `auditTodos`'s machine-scope branch lacked the
    `if (external)` null-guard the old code had, which would have made
    `externalTodos(null)` emit 6 false "never" rows and broken
    derive.test.js:116/:205. Fixed by gating the machine-scope loop on
    `external` truthiness while leaving the repo-scope (`purge-devlocal`)
    loop unconditional on `repos` alone.
  - Fixed (blocker): design doc undercounted existing `externalTodos(...)`
    test call sites as 8; actual is 12 (`rg -n "externalTodos\(" derive.test.js`).
    Corrected the count and added a note to enumerate by search rather than
    trust a hardcoded number.
  - Addressed (non-blocker, fixed as a small free clarification rather than
    deferred): `collect_purge_devlocal`'s directory matching now states an
    explicit `is_dir()` check, since `.trash/manifest.tsv` sits alongside the
    dated subdirectories and a future non-directory entry could otherwise
    collide with the date regex.
  - Recorded, not fixed (question): PRD's "one row per audit" Success Metric
    phrasing could read as a literal cap of 7 rows; the design's accepted
    per-repo fan-out for `purge-devlocal` (Alternative 3) can exceed that.
    Read as "one row per (audit, occurrence)" — matches Feature 2's explicit
    ask for per-repo purge-devlocal stamps. No design change; flagging for
    whoever reviews the rendered brief against the PRD's Success Metrics.
  - Recorded, not fixed (question): `AUDIT_CADENCE`'s `skill` string literals
    have no automated cross-check against the real Skill-tool invocation
    names `track_skills.py` records — a future typo would silently produce a
    permanent "never" row with no test catching it. Standing risk, not a
    defect in this draft; the six current strings were verified correct
    against the live skill roster.

- dispatch 2 (codex): cardinal-sin 0, blocker 4, non-blocker 1, question 2
  - Fixed (blocker): `collect_audit_cadence`'s fully-generic design (chosen in
    dispatch 1) violated the PRD's literal Phase 0 contract — a dict
    returning `None` only via `.get()` on a missing key is not the same as a
    dict that *contains* the key with value `None`. Redesigned around a
    module-level `MACHINE_AUDIT_SKILLS` list, pre-seeded to `None`, overlaid
    from the log. Alternatives section 1/2 swapped to reflect this.
  - Fixed (blocker): the SPA rebuild step was entirely missing from Module
    placement and the Test Strategy Outline. Verified against
    `build.py:11,43-50` (static template string-replace, no Vite invocation)
    and `SKILL.md:121-129` (the documented rebuild recipe) — without it,
    Phase 2's rendered brief would ship the old compiled JS regardless of
    what `derive.js`'s source says. Added as a mandatory Module placement
    bullet and as step 1 of the corrected Phase 2 test sequence.
  - Fixed (blocker): the "`externalTodos` test migration, `kind ===
    'maintenance'` filter stays valid" claim was wrong once
    `MACHINE_AUDIT_SKILLS` is pre-seeded — up to six rows can share that
    `kind` at once, so a bare `.find(kind === 'maintenance')` silently binds
    to table order, and derive.test.js:115's "fresh, no row" case would
    become an actual failing assertion (not just vacuous) because the fixture
    field it sets (`claude_maintenance_last`) is no longer read. Traced all
    12 call sites by hand and replaced the one-line instruction with a
    per-call-site migration list, keyed on `id.startsWith(...)` selection
    instead of bare `kind` filtering.
  - Not fixed as a code change, documented as an accepted risk instead
    (blocker per the reviewer's severity call, downgraded here because the
    fix is out of this PRD's file scope): a clean `purge-devlocal --apply`
    run with nothing to trash creates no new `.trash/<date>/` directory
    (verified against `purge_devlocal.py:360-368,417-427` —
    `trash_file()` only runs inside the `action == "trash"` branch), so the
    chosen stamp (this PRD's own Feature 2 Inputs) cannot distinguish "never
    run" from "ran clean." Fixing it means changing `purge_devlocal.py`,
    which is outside this PRD's Structural Decomposition; recorded in Risks &
    edge cases and flagged for a follow-up PRD.
  - Addressed (non-blocking, fixed as a free addition): the outlined tests
    covered horizon-1/horizon+1 but never the exact-horizon boundary itself
    (`>` vs `>=` are indistinguishable without it). Added to the Test
    Strategy Outline.
  - Addressed (question, clarified as a free addition): `collect_purge_devlocal`'s
    missing-`.trash/`-directory guard order was implicit (`Path.iterdir()`
    raises before any child check if the base itself doesn't exist). Spelled
    out the exact algorithm in Interfaces.
  - Fixed (question, corrected a factual error in this doc rather than left
    open): the Test Strategy Outline previously mischaracterized the PRD's
    Phase 2 as "fixture-driven" — it is a live-machine run
    (`build.py`'s `--dir` defaults to the live data dir; the PRD's `--out`
    flag only relocates output, not input). Corrected the outline to
    describe the real four-step live sequence and what "acceptance" means
    when the exact row count isn't knowable in advance.

- dispatch 3 (codex, conditional verification pass — ran because dispatch 2
  found blockers): cardinal-sin 0, blocker 2, non-blocker 1, question 0.
  Explicitly confirmed the pre-seeding fix and the SPA-rebuild fix as
  correct; found the purge-no-op downgrade and the line-111 test instruction
  both still broken. "Do not proceed to planning yet."
  - Fixed (blocker, escalation accepted): dispatch 2's purge-no-op finding
    was downgraded to a documented, unfixed risk on the grounds that
    `purge_devlocal.py` sat outside the PRD's drafted file list. Codex
    pushed back — correctly, on reflection — that this makes the feature
    permanently unable to reach "green" no matter how often the maintainer
    runs the real command, which is goal-breaking rather than a stylistic
    gap. Reversed the downgrade: added `purge_devlocal.py` as a 5th touched
    file (Module placement) with a one-line, verified-safe fix (stamp
    today's batch dir on every `--apply` run, guarded so dry-run and the
    early-refusal path are unaffected — traced against all three existing
    `.trash/`-absence assertions in `test_purge_devlocal.py` by hand) plus a
    regression test.
  - Fixed (blocker): the line 111 test-migration instruction offered two
    inconsistent candidate assertions (`/45d old/` vs "whatever exact wording
    `auditTodos` emits"), and the literal `/45d old/` regex does not match
    the Interfaces section's own `why` template (`` `last run ${aged}d ago` ``).
    Pinned one exact assertion consistent with the Interfaces pseudocode and
    removed the escape-hatch wording.
  - Recorded, not fixed (non-blocker): the corrected Phase 2 HTML check
    (dispatch 2's fix) can false-pass without any row actually rendering,
    since `build.py` only injects JSON into a static template and a
    plain-text search over the compiled bundle would find command strings
    unconditionally, JS-executed or not. A JSDOM-based render check (the app
    already ships `smoke.test.js`) would close this properly; left as a
    known gap in the Test Strategy Outline rather than fixed here, since
    designing that check requires understanding the existing smoke-test
    harness in more depth than a one-line clarification — a reasonable task
    for whoever plans/implements Phase 2, not a blocker to planning starting.

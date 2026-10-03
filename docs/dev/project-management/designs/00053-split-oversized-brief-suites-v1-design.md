# Design: Split the two oversized brief-portfolio test suites

## Architecture fit

Pure test-suite reorganization inside `skills/brief-portfolio/{app,scripts}/`; no
production code changes. The repo already tests each skill with `uv run pytest`
(collecting every `test_*.py` under `skills/*/scripts/`) plus, for
brief-portfolio specifically, an explicit `node --test` file list in
`app/package.json` (Node's test runner does not auto-discover files the way
pytest does). Both suites already follow a "shared harness/helpers module +
several focused test files" shape — `smoke.harness.js` + `smoke.test.js` +
`smoke.a11y.test.js` on the JS side is the existing precedent this PRD extends
rather than invents.

## Module placement

**New files:**
- `skills/brief-portfolio/app/smoke.harness.test.js` — harness self-tests
  (the 3 tests that exercise `waitFor` itself, now that `waitFor` is a harness
  export rather than a private helper).
- `skills/brief-portfolio/app/smoke.brief.test.js` — Brief tab.
- `skills/brief-portfolio/app/smoke.repos.test.js` — PRDs tab + Repos tab /
  RepoDetail panel.
- `skills/brief-portfolio/app/smoke.work.test.js` — Work tab (including the
  one test that also drills into RepoDetail).
- `skills/brief-portfolio/app/smoke.todos.test.js` — Todo tab, copy mechanics.
- `skills/brief-portfolio/app/smoke.todos.status.test.js` — Todo tab, per-group
  status/disabled-state and announcement-ordering edge cases (split out of the
  Todos bucket solely because one file can't hold all 11 Todos tests under the
  400-line cap — see Alternatives).
- `skills/brief-portfolio/scripts/collect_test_helpers.py` — shared stubs.
- `skills/brief-portfolio/scripts/test_collect_repo.py` — `collect_repo` /
  `stub_from_path`.
- `skills/brief-portfolio/scripts/test_collect_local.py` — the local-filesystem
  readers: `collect_brush`, `collect_claude_skill_adherence`,
  `collect_audit_cadence`, `collect_purge_devlocal`.
- `skills/brief-portfolio/scripts/test_collect_history.py` — `should_rotate` /
  `ROTATE_MIN_AGE`, `main()`'s snapshot-rotation and offline-mode behavior,
  `history_counts`.
- `skills/brief-portfolio/scripts/test_collect_pipeline.py` — `main()`'s
  registry-driving orchestration and its resilience to corrupt/unreadable
  `data.json`/registry state (renamed from the PRD's suggested
  `test_collect_ci.py` — see Alternatives, no `collect_ci()` coverage exists
  in this suite to justify that name).

**Edited files:**
- `skills/brief-portfolio/app/smoke.harness.js` — add `waitFor` as a named
  export.
- `skills/brief-portfolio/app/package.json` — `test` script names the 6 new
  JS files plus the untouched `smoke.a11y.test.js` and
  `src/lib/derive.test.js`, in place of `smoke.test.js`.
- Any of `dev/local/prds/backlog/00054-*.md`..`00069-*.md` that names
  `test_collect.py` or `smoke.test.js` in a task acceptance line gets that
  reference rewritten to the successor file below (Phase 1 Core task, not
  this design).

**Deleted files:**
- `skills/brief-portfolio/app/smoke.test.js`
- `skills/brief-portfolio/scripts/test_collect.py`

**Untouched:** `smoke.a11y.test.js`, `smoke.harness.js`'s existing exports
(`TEMPLATE`, `PAYLOAD`, `render`), `test_build_page.py`, `collect.py` itself.

## Interfaces & contracts

### `smoke.harness.js` (extended)

Add, alongside the existing `TEMPLATE`/`PAYLOAD`/`render` exports, moved
verbatim from `smoke.test.js` lines 13-27:

```js
export async function waitFor(predicate, { flush, timeout = 3000, interval = 25 } = {}) {
  // body unchanged
}
```

### JS test-name membership (exact, by current `smoke.test.js` line number)

- **`smoke.harness.test.js`** — imports `{ waitFor }` from `./smoke.harness.js`:
  - `waitFor resolves once the predicate turns true` (29)
  - `waitFor awaits the supplied flush between predicate checks` (36)
  - `waitFor throws an Error naming the timeout once the deadline passes` (61)
- **`smoke.brief.test.js`** — imports `{ PAYLOAD, render }`:
  - `mounts with zero errors on the default Brief tab` (103)
  - `Brief tab names repos it could not collect this run` (276)
  - `Brief tab trend sparkline plots only complete history runs, not incomplete ones` (439)
  - `Brief tab trend sparkline skips a run where a repo failed to collect` (459)
  - `done.js survives a blocked localStorage: loadDone returns empty, saveDone no-ops, isStorageBlocked flips true` (560)
  - `loadDone() returns an empty Set when the stored value is corrupt JSON` (586)
  - `saveDone() alone flips isStorageBlocked when only setItem throws` (607)
  - `render(payload, { url: null }) omits the jsdom url option, so localStorage throws on the default opaque origin` (632)
  - `render(payload) still mounts on a real origin, so localStorage works by default` (637)
  - `Brief tab shows no persistence notice when localStorage works` (642)
  - `Brief tab still renders with a persistence notice when localStorage is blocked` (647)
- **`smoke.repos.test.js`** — imports `{ PAYLOAD, render }`; keeps a local
  (non-exported) `backlogListItems(container, selector, text)` copied
  verbatim from lines 79-87 — it is used only by these three tests, so it
  does not need to become a harness export:
  - `PRDs tab renders both duplicate backlog entries instead of crashing` (108)
  - `RepoDetail panel renders both duplicate backlog entries instead of crashing` (120)
  - `RepoDetail panel renders both grouped epics that share a title, not once` (164)
- **`smoke.work.test.js`** — imports `{ PAYLOAD, render }`:
  - `Work tab and RepoDetail panel render both instances of a duplicated issue label, not once` (136) — stays whole; it is one test that happens to touch both Work and RepoDetail, not two tests to split.
  - `Work tab shows the external PR lookup error instead of an empty section` (191)
  - `Work tab has no "Waiting on you elsewhere" section when there is no external data` (202)
  - `Work tab shows "No CI runs." on the CI wall when no repo has CI data` (209)
  - `Work tab names a never-fetched-CI repo below the wall, alongside the wall's own empty state` (219)
  - `Work tab does not name a repo with \`ci: []\` as not collected this run` (233)
  - `Work tab shows the not-collected-this-run line even when the CI wall has rows from another repo` (247)
- **`smoke.todos.test.js`** — imports `{ PAYLOAD, render, waitFor }`. Does
  **not** need `stubClipboard` — none of its 6 tests call it (295/315/334/480
  rely on jsdom's default missing clipboard support; 358/412 stub
  `clipboard.writeText`/`execCommand` inline). Only `smoke.todos.status.test.js`
  below needs the local copy:
  - `Todos tab shows a failed-copy state when neither clipboard.writeText nor execCommand works` (295)
  - `Failed copy leaves no leftover <textarea> in the document` (315)
  - `Failed copy is announced in an aria-live region, not just the button label` (334)
  - `Todos tab reports success and copies the open todos when the execCommand fallback works` (358)
  - `Todos tab reports failure when the execCommand fallback returns false` (412)
  - `aria-live region clears once the failed-copy button label has reverted` (480) — this is the one call site of `waitFor` outside the harness self-tests (line 501).
- **`smoke.todos.status.test.js`** — imports `{ PAYLOAD, render }`; keeps the
  sole copy of `stubClipboard(doc)` (verbatim from lines 94-101) — its 5 tests
  are every remaining call site (528, 684, 725, 755, 828):
  - `Todos tab shows a "nothing" status on a per-group copy when the group's only open item is checked done` (513)
  - `Todos tab disables the "copy open as markdown" button and touches nothing when there are no open todos` (669)
  - `Todos tab disables the per-group button too, once the whole-list openCount reaches 0` (702)
  - `A declined copy is announced truthfully even right after a successful copy` (742)
  - `A newer status announcement survives an older one's 1500ms expiry, and still clears once its own window elapses` (807)

### `package.json` `test` script

```
"test": "node --test src/lib/derive.test.js smoke.harness.test.js smoke.brief.test.js smoke.repos.test.js smoke.work.test.js smoke.todos.test.js smoke.todos.status.test.js smoke.a11y.test.js"
```

### `collect_test_helpers.py` (new; every function moved verbatim, same signature)

```python
def write_report(tmp_path: Path, body: str) -> None
def make_registry(tmp_path: Path, names) -> list
def write_registry_csv(tmp_path: Path, paths) -> Path
def make_fake_run(skip_cwds)
def run_collector(tmp_path, monkeypatch, resolvable_names, skip_names)
def write_data_json_fixture(path: Path, generated_at: str, marker: str) -> str
def make_trash_dir(tmp_path: Path, *, dirs=(), files=()) -> Path
def make_git_repo(path: Path, commits: int) -> None
```

Every new `test_collect_*.py` module does
`from collect_test_helpers import <only the names it actually calls>` (plus
its own `from collect import <...>` subset) rather than `import *`, so an
unused-import lint has nothing to flag.

### Python test-name membership (exact, by current `test_collect.py` line number)

- **`test_collect_repo.py`** (8 tests, ~180 lines with helpers/imports):
  `test_stub_from_path_builds_owner_name_org_and_reason_from_path` (214),
  `test_collect_repo_returns_skip_stub_when_remote_unresolvable` (225),
  `test_collect_repo_records_fetch_timeout_without_raising` (242),
  `test_collect_repo_returns_skip_stub_when_remote_get_url_times_out` (579),
  `test_collect_repo_returns_skip_stub_when_git_binary_missing` (592),
  `test_collect_repo_records_meta_os_error_without_raising` (605),
  `test_collect_repo_records_meta_timeout_without_raising` (622),
  `test_collect_repo_purge_last_run_key_equals_collect_purge_devlocal_result` (834).
- **`test_collect_local.py`** (20 tests, ~240 lines): the 3 `collect_brush`
  tests (34, 43, 47), the 4 `collect_claude_skill_adherence`/
  `MACHINE_AUDIT_SKILLS` tests (52, 56, 83, 92), the 6 `collect_audit_cadence`
  tests (103, 108, 133, 145, 170, 190), the 7 `collect_purge_devlocal` tests
  (794, 798, 803, 808, 813, 818, 829).
- **`test_collect_history.py`** (17 tests, ~250 lines): the 4 `should_rotate`/
  `ROTATE_MIN_AGE` tests (353, 359, 367, 375), the 3 snapshot-rotation `main()`
  tests (393, 419, 437), the 4 offline-mode tests (465, 484, 503, 520), the 2
  `--no-git-fetch` flag tests (537, 559), the 4 `history_counts` tests (922,
  932, 937, 948).
- **`test_collect_pipeline.py`** (18 tests, ~320 lines): the 5 registry-driving
  `main()` tests (310, 318, 325, 332, 342), `test_main_includes_skipped_repos_in_known_set_for_external_classification`
  (639), the 7 corrupt/unreadable-`data.json` recovery tests (658, 671, 684,
  700, 724, 740, 761), the 2 `audit_cadence`-in-`main()` tests (853, 866, 897 —
  three tests), `test_missing_registry_file_exits_with_the_documented_message`
  (966, `@pytest.mark.xfail(strict=True, raises=FileNotFoundError, ...)`) and
  `test_a_capped_commit_list_still_carries_the_true_commit_count` (995,
  `@pytest.mark.xfail(strict=True, raises=KeyError, ...)`) — both xfail
  decorators, and the shared "Found by an agoge run on 2026-09-05..." comment
  above them (lines 954-957), move verbatim with these two tests.

## Data flow

No runtime data flow changes — this is test-file reorganization only. The
only "data flow" of note is import wiring: each new file imports from its
shared module (`smoke.harness.js` / `collect_test_helpers.py` +
`collect.py`), never from a sibling `smoke.*.test.js` / `test_collect_*.py`,
so the new files have no cross-dependencies on each other (confirmed by the
membership lists above — no helper is called from two different new files
except through the shared modules).

## Reuse inventory

- `skills/brief-portfolio/app/smoke.harness.js` + `smoke.a11y.test.js` is the
  existing "shared harness + several focused test files" pattern; this PRD
  extends it with more sibling files rather than inventing a new shape.
- `skills/distil-memory/scripts/docket_test_helpers.py` and
  `distil_test_helpers.py` are this repo's existing precedent for a
  `<module>_test_helpers.py` shared-stub file, which `collect_test_helpers.py`
  follows by name and shape.
- `skills/use-qwen/scripts/test_eval_tree_{patches,proofs,links}.py` is this
  repo's existing precedent for splitting one oversized suite into several
  concern-named files (rather than N roughly-equal-size chunks), which is the
  same principle applied here to `test_collect_*.py`.
- Commit `df71f88` (2026-09-20, this same PRD's own motivating batch) already
  did exactly this kind of split for `test_run_eval_harness.py` at 821 lines
  ("split ... into a companion outcomes-per-mode module to stay under the
  800-line cap") — same repo, same week, same pattern.
- Greps tried before concluding nothing more specific exists: `split.*test`,
  `test.*split` (case-insensitive) across `skills/` — only the precedents
  above and unrelated hits (an HTML template literally containing the string
  "split", a `derive.test.js`); `rg -n "backlogListItems|stubClipboard"` to
  confirm exact helper scope before deciding what moves to the harness vs.
  stays local (see Interfaces & contracts).

## Alternatives considered

1. **Smallest-diff: keep exactly the PRD's literal file list** (3 JS files —
   `smoke.brief.test.js`, `smoke.work.test.js`, `smoke.todos.test.js` — plus 4
   Python files literally named `test_collect_repo.py`,
   `test_collect_ci.py`, `test_collect_history.py`, `test_collect_local.py`,
   with no `smoke.harness.test.js`/`smoke.repos.test.js`/
   `smoke.todos.status.test.js` split). Rejected: not viable, not just
   smaller. Folding the PRDs+Repos tests into whichever file and the harness
   self-tests into `smoke.brief.test.js` still leaves `smoke.todos.test.js`
   at ~470 lines (11 tests, several 30-65 lines each) — over the Must-have
   400-line cap on its own. And there is no `collect_ci()` coverage in this
   suite at all (checked: the only "ci" hit in the whole file is one error
   string inside an unrelated `history_counts` test), so `test_collect_ci.py`
   would be an empty or misleading file. This is exactly the case the PRD's
   own "design step may regroup where a boundary does not fit" clause covers.
2. **Chosen: concern-named files, further split only where the cap forces it**
   (this design). One extra JS file (`smoke.harness.test.js` for the 3
   `waitFor` self-tests, since `waitFor` itself is moving out of `smoke.test.js`
   and needs its tests to go somewhere sensible) and one forced split
   (`smoke.todos.status.test.js`) beyond the PRD's literal 3; on the Python
   side, the same file count as requested but `test_collect_ci.py` renamed to
   `test_collect_pipeline.py` to match actual content. Costs 3 more files than
   option 1's literal reading, buys: every file under the line cap, and every
   file name tells a future contributor (including the 16 dependent backlog
   PRDs) where a new test for that surface belongs.
3. **Split purely by original line position** (e.g. `test_collect.py` lines
   1-500 → part 1, 501-1014 → part 2; same for JS). Smaller design effort, but
   produces meaningless names (`test_collect_part1.py`) that give the 16
   dependent PRDs and any future contributor no signal about where a new test
   belongs, and splits closely-related tests (e.g. the two
   `collect_purge_devlocal`/`collect_repo` cross-check tests) across an
   arbitrary boundary. Rejected — the PRD's own naming intent (collector
   groups / tabs) is worth the extra grouping effort.

## Risks & edge cases

- **Byte-identical bodies are the hard constraint.** Every move must be a pure
  cut-paste — no reformatting, no import reordering inside a test body. The
  Phase 0 inventory task (hashes before the split) is what catches an
  accidental edit; this design doesn't re-derive that mechanism.
- **The two Python xfail markers must travel with their tests, not get
  stranded.** Both `@pytest.mark.xfail(...)` decorators (and the shared
  explanatory comment above them) land in `test_collect_pipeline.py` per the
  membership list above — verify with `rg -n "xfail" skills/brief-portfolio/scripts/test_collect_pipeline.py` printing exactly 2 hits after the split.
- **`stubClipboard` is local to `smoke.todos.status.test.js` only** — all 5
  real call sites (528, 684, 725, 755, 828) land in that file's 5 tests, so
  `smoke.todos.test.js` needs no copy of it at all.
- **Likely next changes** (from the PRD's own text — PRDs 00054-00069 add
  tests to both suites): (1) most of those PRDs add tests to exactly one of
  these new files (e.g. 00056 "ci-failure-fakes-no-ci" likely adds a
  `test_collect_pipeline.py` or `test_collect_local.py` test, not
  `test_collect_repo.py`) — the concern-based names are what let a task author
  pick the right file without re-reading this design doc; (2) if any one file
  grows back toward 400 lines from new tests, the fix is the same
  concern-based further split this design already used for Todos, not a
  wholesale re-split; (3) a genuine `collect_ci()` unit-test file could be
  added later under the name `test_collect_ci.py` — freed up by this design's
  rename of the pipeline bucket, so no future collision.

## Test strategy outline

- Baseline: `dev/local/tmp/00053-inventory-before.txt` (Phase 0 task) records
  test-name multiset + body hashes + xfail reason/marker metadata for both
  languages before any file is touched.
- After each split step: `npm --prefix skills/brief-portfolio/app test` and
  `uv run pytest skills/brief-portfolio/scripts -q` both report 0 failing,
  same xfail set (2, both strict, same `raises=`/`reason=`).
- Structural checks: `wc -l` on every new file ≤400;
  `rg -n "smoke.test.js" skills/brief-portfolio/app/package.json` prints
  nothing; a post-split inventory (test names + body hashes) diffs equal to
  the Phase 0 baseline as a multiset, in both languages.
- Cross-reference check: for each of PRDs 00054-00069 that names
  `test_collect.py` or `smoke.test.js` in a task acceptance line, confirm the
  rewritten reference names a file that actually contains the test/line range
  it used to point at (using the membership lists above).

## Review log

- question: cross-reference rewrite scoped to "task acceptance line" is
  narrower than the PRD's "task text" must-have — most of PRDs 00054-00069
  name `test_collect.py`/`smoke.test.js` only in a `### Module:` header and a
  `- X: Depends on [...]` bullet, not inside an acceptance-criteria checkbox;
  unresolved whether those header/dependency lines also need rewriting.
  Deferred to the Phase 1 Core task that performs the rewrite.
- non-blocker: `backlogListItems` is actually called by only 2 of the 3 tests
  assigned to `smoke.repos.test.js` (108, 120; not 164, which queries the DOM
  directly) — the doc's "used only by these three tests" overstates the call
  count. Placement is unaffected (both real call sites still land in that
  file).
- non-blocker: `smoke.a11y.test.js:71` has a comment naming `smoke.test.js`
  by name ("same fixup the Todos-tab tests in smoke.test.js use") that will
  be stale once `smoke.test.js` is deleted; that file is listed Untouched and
  outside this split's must-haves.
- non-blocker: the Python membership list's `test_collect_pipeline.py` entry
  says "the 2 `audit_cadence`-in-`main()` tests (853, 866, 897 — three
  tests)" — the count "2" should read "3" (three line numbers, three tests,
  and the file's stated 18-test total already assumes 3).
- non-blocker: the shared xfail-explanation comment is cited as "lines
  954-957"; the actual comment body is 954-956 (957 is a blank line before
  the next blank and the decorator at 959).
- non-blocker: the Reuse inventory cites commit `df71f88` as "2026-09-20";
  its actual author/committer date is 2026-09-14.

dispatch 1 (claude): cardinal-sin 0, blocker 1, non-blocker 4, question 1

- non-blocker: 3 of the 8 helpers placed in `collect_test_helpers.py`
  (`write_report`, `make_trash_dir`, `make_git_repo`) each have call sites in
  exactly one destination file, unlike the JS side where a single-file helper
  was correctly kept local (`backlogListItems`, `stubClipboard`) — an
  unexplained scope-classification inconsistency between the two languages,
  though moving all 8 together still satisfies the Must-have ("shared
  helpers live in ... `collect_test_helpers.py`") and breaks nothing.
- non-blocker: the Reuse inventory cites the `use-qwen` split precedent as 3
  files (`test_eval_tree_{patches,proofs,links}.py`); the actual split
  produced 5 (also `containment`, `state`).
- question: `smoke.test.js`'s 8-line file header (the jsdom rationale and the
  `each_key_duplicate` regression note that motivates several of the moved
  tests) has no stated destination in the design — not a Must-have violation
  (comments aren't tests), but an implementor could miss it. Left for the
  Phase 1 Core task to place (most naturally atop `smoke.harness.js`, next to
  the tests it motivates, or split — unresolved).

dispatch 2 (claude-fallback): codex unavailable (usage limit, exit 1) —
cardinal-sin 0, blocker 0, non-blocker 2, question 1

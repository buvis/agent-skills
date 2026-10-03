---
default_model: opus
model_tier_rationale: equivalence obligation - a behaviour-preserving split of two suites must keep every test byte-identical, and the file grouping is a design call
design: run
consensus_engine: shadow
---

# Split the two oversized brief-portfolio test suites before more tests land in them

## Problem

`skills/brief-portfolio/app/smoke.test.js` is 896 lines and
`skills/brief-portfolio/scripts/test_collect.py` is 1,014, both past the 800-line
ceiling in `rules/coding-style.md`, and every lane PRD grows them: smoke.test.js
went 785 (PRD 00026) to 835 (00028) to 849 (00033) in one batch, and the
reviewers of all three PRDs refused to split inside a feature diff (surgical
changes) and asked for a PRD of its own. Sixteen PRDs from the 2026-09-05 agoge
walkthrough (00054 to 00069) add tests to both files, so this PRD drains first.
Source: batch 202609040601 deferred items 2, 4 and 6 (LOW, consensus 2/3 twice);
decision 2026-09-05: one split PRD for both files, drained before the
brief-portfolio agoge PRDs.

```
smoke.test.js: 785 lines after PRD 00026, 835 after 00028, 849 after 00033.
test_collect.py: 911 lines before PRD 00028, 951 after.
```

## Solution

Split each suite by the surface it exercises, moving tests verbatim.
JavaScript: `smoke.harness.js` already holds `render()` and `PAYLOAD`, and
`smoke.a11y.test.js` already exists (`smoke.browser.test.js`, Playwright and
outside the `test` script, is not part of this split); move `waitFor` into the harness and split
the rest of `smoke.test.js` into one file per tab (`smoke.brief.test.js`,
`smoke.work.test.js`, `smoke.todos.test.js`, and whatever the design step adds
for the remaining tabs and the harness self-tests). The `test` script in
`app/package.json` names its files explicitly
(`node --test src/lib/derive.test.js smoke.test.js smoke.a11y.test.js`), so
every new file is added there and the deleted one removed. Python: one module
per collector group (`test_collect_repo.py`, `test_collect_ci.py`,
`test_collect_history.py`, `test_collect_local.py`) plus `collect_test_helpers.py` for the
shared stubs (`make_fake_run`, `write_registry_csv` and friends). The design
step may regroup where a boundary does not fit; the name-set and line-cap
criteria below hold whatever the grouping. No test is renamed, dropped, merged or reworded. Test bodies and markers
stay unchanged; imports and shared-helper wiring may change. Keep ordinary
helper functions ordinary, rather than converting them into injected fixtures.

## Requirements

### Must have

- Every test name present before the split is present after it, exactly once,
  under the same directory.
- Every strict xfail keeps its marker and reason.
- No resulting test file exceeds 400 lines; shared helpers live in
  `smoke.harness.js` and `collect_test_helpers.py`.
- `npm --prefix skills/brief-portfolio/app test` and
  `uv run pytest skills/brief-portfolio/scripts -q` report 0 failing before and
  after, with the same xfail set.
- Any backlog PRD in the 00054 to 00069 range whose task names
  `test_collect.py` or `smoke.test.js` is updated to name the file its test now
  belongs in.

### Nice to have

- Test order inside each new file follows the original file, so concatenating
  the new files diffs against the old one as moves only.

## Implementation

### Module: smoke.harness.js and smoke.*.test.js

- **Location**: `skills/brief-portfolio/app/`
- **Responsibility**: Hold the jsdom smoke tests split by tab, sharing the
  existing render harness plus `waitFor`.
- **Exports**: `render()`, `waitFor()`, `PAYLOAD`; `node --test` cases

### Module: collect_test_helpers.py and test_collect_*.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Hold the collector tests split by collector group,
  sharing the ordinary gh/git helper functions.
- **Exports**: shared helper functions; pytest cases

### Dependencies

- smoke.harness.js: No dependencies (foundation)
- smoke.*.test.js: Depends on [smoke.harness.js]
- collect_test_helpers.py: No dependencies (foundation)
- test_collect_*.py: Depends on [collect_test_helpers.py]

Re-check current file sizes and helper locations before moving them; preserve
already-completed splits and update the inventory instead of recreating obsolete files.

## Tasks

### Phase 0: Foundation

- [ ] Record the execution-time pre-split inventory - Acceptance: save separate Python and JavaScript inventories to `dev/local/tmp/00053-inventory-before.txt`: extracted test names and their multiplicities (without filename/line prefixes), test-body hashes and marker/reason metadata. Include the named suites and existing a11y cases and exclude `smoke.browser.test.js`; capture passing baseline commands and xfails from the current committed baseline (the Windows CI job already exists; held PRD 00044 is not a prerequisite).
- [ ] Move `waitFor` into `smoke.harness.js` and import it from `smoke.test.js` - Acceptance: `npm --prefix skills/brief-portfolio/app test` reports 0 failing and the same test names as the inventory.
- [ ] Move the ordinary shared stubs from `test_collect.py` into `collect_test_helpers.py`, updating imports - Acceptance: test bodies/names/markers remain unchanged; `uv run pytest skills/brief-portfolio/scripts -q` exits 0 with the same inventoried tests and xfails.

### Phase 1: Core

- [ ] Split `smoke.test.js` by tab into the per-tab files, add them to the `test` script in `app/package.json`, and delete the original (depends on: Phase 0) - Acceptance: the extracted test-name multiset from the new smoke files equals the JavaScript inventory, with unchanged body hashes, `wc -l` of each file is at most 400, `rg -n "smoke.test.js" skills/brief-portfolio/app/package.json` prints nothing, and `npm --prefix skills/brief-portfolio/app test` reports 0 failing.
- [ ] Split `test_collect.py` by collector group into the four modules and delete the original (depends on: Phase 0) - Acceptance: the extracted test-name multiset from the new collector modules equals the Python inventory, with unchanged body hashes and marker metadata, `wc -l` of each file is at most 400, `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing with the same xfails, and each task-location reference in backlog PRDs 00054–00069 points to the appropriate successor. Exclude this PRD's migration text and historical Problem evidence from that check.

## Success Criteria

- The test-name inventories before and after are equal as multisets, in both
  languages, and every xfail marker survives.
- Every test file produced by this split has at most 400 lines; unrelated existing suites are outside this criterion.
- Both suite commands report 0 failing.
- PRDs 00054 to 00069 name the split files, not the deleted ones.
- Source: batch 202609040601, walked in
  `dev/local/audit-results/agoge-2026-09-05.md`.

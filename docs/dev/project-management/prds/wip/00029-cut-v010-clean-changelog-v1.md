---
default_model: opus
rework_cap: 5
design: skip
---

# Cut v0.1.0 and make the changelog match the format it claims

## Overview

### Problem Statement
`CHANGELOG.md:5-6` claims Keep a Changelog and Semantic Versioning, and no
artifact carries either. The file holds two `### Added`, two `### Changed` and
two `### Fixed` sections, so the fixes under the second one are invisible to a
reader who stopped at the first, hundreds of lines higher. A Fixed-type bullet
sits under `### Added`, seven bullets carry `**ci**`, `**tests**` and `**docs**`
scopes that `rules/changelog.md` excludes, the workflow comment plus its
matching changelog bullet both miscount the skills shipping a bash suite, and
commit af1b704 deleted the brief-portfolio skill with no `### Removed` entry.
Meanwhile `git tag -l` prints nothing while `pyproject.toml:7` and
`src/agent_skills_braid/__init__.py:3` pin `0.1.0`, a string the changelog never
mentions, so an installed build maps to no section, no tag, no compare range.
Source: agoge run
`docs/dev/project-management/audit-results/agoge-2026-08-31.md`, findings 22
(MEDIUM, release lane), 23 (MEDIUM, release lane) and 38 (LOW, release lane);
decision 2026-09-02: cut a real v0.1.0 with the cleanup inside it, absorbing PRD
00042's shell-suite count fix.

```
rg -n "^#{2,3} " CHANGELOG.md -> 8:## [Unreleased], 10:### Added,
91:### Changed, 104:### Fixed, 370:### Added, 576:### Removed,
591:### Changed, 603:### Fixed.
git tag -l prints nothing. rg -c "^- \*\*" CHANGELOG.md -> 176.
rg -n "^- \*\*(ci|tests|docs)\*\*" CHANGELOG.md -> 75, 501, 552, 564, 569,
571, 634. ls skills/*/scripts/test_*.sh returns five files across four
skills (use-qwen ships two), against "Five skills" in ci.yml:122 and
CHANGELOG.md:571.
```

Re-verified on master 2026-10-17 (the 2026-09-02 numbers had drifted: 70
bullets became 176 and `### Added` is doubled too). The file moves under every
batch, so every count below is arithmetic over the numbers each task measures
at execution, never a pinned total. The report's "dangling `[Unreleased]:`
link reference" does not exist: the file holds no link definitions, so none
are added here.

### Target Users
Anyone reading the changelog to learn what shipped, anyone reading the workflow
to judge test coverage, and any future consumer of a versioned install.

### Success Metrics
- `rg -n "^#{2,3} " CHANGELOG.md` returns six lines: an empty `## [Unreleased]`
  (where `rules/changelog.md` files the next entries), `## [0.1.0] - <date>`,
  plus one each of `### Added`, `### Changed`, `### Removed`, `### Fixed`.
- `rg -c "^- \*\*" CHANGELOG.md` prints N0 - E + 15: N0 the bullet count
  measured before Phase 0 (176 on 2026-10-17), E the excluded-scope bullets
  deleted (7 on 2026-10-17), plus 14 backfilled skill entries and the
  brief-portfolio Removed entry (184 on today's numbers).
- `git tag -l v0.1.0` prints `v0.1.0`, matching the `0.1.0` already pinned in
  `pyproject.toml:7` and `src/agent_skills_braid/__init__.py:3`.
- `python3 scripts/check_changelog_skills.py` exits 0 with an empty
  `GRANDFATHERED` list.

## Functional Decomposition

### Capability: Changelog format repair
One section per type, every bullet under the type its commit belongs to.

#### Feature: Duplicate section merge
- **Description**: one `### Added`, one `### Changed` and one `### Fixed`, not two of each.
- **Inputs**: the `###` headings `rg -n "^#{2,3} " CHANGELOG.md` prints (10, 91, 104, 370, 576, 591, 603 on 2026-10-17).
- **Outputs**: four type sections in Keep a Changelog order.
- **Behavior**: append the later duplicate's bullets to the earlier section,
  text unchanged, then delete the emptied heading.

#### Feature: Excluded-scope bullet drop
- **Description**: remove bullets whose commit type never earns an entry.
- **Inputs**: every bullet matching `^- \*\*(ci|tests|docs)\*\*` (seven on 2026-10-17: 75, 501, 552, 564, 569, 571, 634).
- **Outputs**: N0 - E bullets remain.
- **Behavior**: delete each bullet with its continuation lines; `rules/changelog.md`
  exempts those commit types, so they are dropped, not refiled. The `**ci**`
  bullet at 571-572 is the one carrying "Five skills" (finding 38); the one at
  75 names the deleted brief-portfolio suite.

#### Feature: Work bullet refile
- **Description**: the one Fixed-type bullet parked under `### Added`.
- **Inputs**: the `**work**` bullet at `CHANGELOG.md:560-563`, under the second `### Added`.
- **Outputs**: the same bullet, text unchanged, under `### Fixed`.
- **Behavior**: it reads "the qwen helper paths in the documentation copy
  resolve again", which is a fix.

### Capability: Changelog completeness
The changelog names everything this repo ships and counts it correctly.

#### Feature: Shell-suite count fix
- **Description**: the workflow comment states the true number.
- **Inputs**: `.github/workflows/ci.yml:122`, today `# Five skills ship bash
  suites their helper scripts are the subject of.`
- **Outputs**: the same comment reading "Four skills ship five bash suites".
- **Behavior**: five files across four skills - `use-codex`, `use-gemini`,
  `use-sonnet`, and `use-qwen`'s two.

#### Feature: Grandfathered skill backfill
- **Description**: one entry per skill the changelog has never named.
- **Inputs**: `GRANDFATHERED` in `scripts/check_changelog_skills.py` (PRD
  00020), holding 14 names.
- **Outputs**: 14 new `### Added` bullets, then an empty list.
- **Behavior**: write `- **<name>**: ...` from that skill's `SKILL.md`
  description, then empty the list so the check covers all 50 directories.

#### Feature: Removed-skill entry
- **Description**: the changelog records that brief-portfolio is gone.
- **Inputs**: commit af1b704, which deleted `skills/brief-portfolio/` with no changelog line; the 31 historical lines that still name it.
- **Outputs**: one `### Removed` bullet; the historical bullets stay as written.
- **Behavior**: `rules/changelog.md` files a removal under Removed; history is not rewritten.

### Capability: Release cut
The accumulated log becomes a version the artifacts agree with.

#### Feature: Version 0.1.0 cut
- **Description**: `[Unreleased]` becomes a dated release beneath a fresh, empty `[Unreleased]`, tagged locally.
- **Inputs**: the `## [Unreleased]` heading at `CHANGELOG.md:8`, and the commit
  carrying the finished file.
- **Outputs**: `## [Unreleased]` (empty) above `## [0.1.0] - <YYYY-MM-DD>`, and a local `v0.1.0` tag.
- **Behavior**: rename in place, keeping the four type sections beneath it,
  insert an empty `## [Unreleased]` heading above it (the `rules/changelog.md`
  mandate files every later feat/fix entry there, and nine later PRDs in this
  batch do), then `git tag v0.1.0`. `pyproject.toml` and `__init__.py` stay at
  `0.1.0` and become true. Pushing the tag is a human follow-up, not a task.

## Structural Decomposition

### Repository Structure

```
CHANGELOG.md                   # Maps to: Duplicate section merge, Excluded-scope
                               #   bullet drop, Work bullet refile,
                               #   Grandfathered skill backfill, Version 0.1.0 cut
.github/workflows/ci.yml       # Maps to: Shell-suite count fix
scripts/check_changelog_skills.py  # Maps to: Grandfathered skill backfill
```

### Module: changelog
- **Maps to capability**: Changelog format repair, Changelog completeness,
  Release cut
- **Responsibility**: be the record of what this repo ships, in the format it
  claims and under the version it shipped as
- **Exports**:
  - `## [Unreleased]` - empty, where the next feat/fix entries land
  - `## [0.1.0] - <date>` - the released section
  - `### Added`, `### Changed`, `### Removed`, `### Fixed` - one each

### Module: ci
- **Maps to capability**: Changelog completeness
- **Responsibility**: describe the shell job with a count that matches the tree
- **Exports**:
  - the `shell` job comment - "Four skills ship five bash suites"

### Module: check_changelog_skills
- **Maps to capability**: Changelog completeness
- **Responsibility**: hold the shrinking list of skills exempt from the check
- **Exports**:
  - `GRANDFATHERED` - empty once the backfill lands

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **changelog**: the merged, refiled, trimmed body every later phase edits

### Core Layer (Phase 1)
- **ci**: Depends on [changelog]
- **check_changelog_skills**: Depends on [changelog]

### Integration Layer (Phase 2)
- **changelog (release cut)**: Depends on [ci, check_changelog_skills]

## Implementation Phases

### Phase 0: Foundation
**Goal**: one section per type, every bullet filed under the type it belongs to.

**Tasks**:
- [ ] Merge every doubled type section into its first occurrence (`### Added`,
  `### Changed` and `### Fixed` are each doubled today), keeping every bullet
  byte-identical and ordering the sections Added, Changed, Removed, Fixed
  (Premise: `rg -n "^#{2,3} " CHANGELOG.md` prints `## [Unreleased]` once and
  at least one `###` type heading twice; on 2026-10-17 it printed 8, 10, 91,
  104, 370, 576, 591, 603. Re-run first, record N0 = `rg -c "^- \*\*"
  CHANGELOG.md` (176 on 2026-10-17) in the task notes, and skip with a report
  if no heading is doubled) (no deps) - Acceptance: `rg -c "^### Added"`,
  `rg -c "^### Changed"`, `rg -c "^### Removed"` and `rg -c "^### Fixed"` each
  print 1 against `CHANGELOG.md`; `rg -c "^- \*\*" CHANGELOG.md` still prints N0.
- [ ] Delete every bullet whose scope prefix is `**ci**`, `**tests**` or
  `**docs**`, each with its continuation lines (Premise:
  `rg -n "^- \*\*(ci|tests|docs)\*\*" CHANGELOG.md` returns at least one line;
  seven on 2026-10-17, at 75, 501, 552, 564, 569, 571 and 634 before the
  merge; re-run after the merge, record its count E, and delete only what it
  returns) (depends on: the merge task above) -
  Acceptance: `rg -c "^- \*\*(ci|tests|docs)\*\*" CHANGELOG.md` exits 1 with no
  match; `rg -c "172 tests" CHANGELOG.md` exits 1 with no match;
  `rg -c "^- \*\*" CHANGELOG.md` prints N0 - E.
- [ ] Move the `**work**` bullet from `### Added` to the end of `### Fixed`
  (Premise: `rg -n "\*\*work\*\*" CHANGELOG.md` returns one line, the bullet
  beginning "the qwen helper paths in the documentation copy resolve again",
  sitting below an `### Added` heading (560 on 2026-10-17, under the second
  one); re-run and skip if it already sits under `### Fixed`) (depends on: the
  merge task above) - Acceptance:
  `rg -n "\*\*work\*\*" CHANGELOG.md` matches one line whose number is greater
  than the line of the sole `### Fixed` heading; `rg -c "^- \*\*" CHANGELOG.md`
  prints N0 - E.

**Exit Criteria**: `rg -n "^#{2,3} " CHANGELOG.md` returns five lines
(`## [Unreleased]` plus one each of Added, Changed, Removed, Fixed) and
`rg -c "^- \*\*" CHANGELOG.md` prints N0 - E.

### Phase 1: Core
**Goal**: the changelog names every skill and the workflow states a true count.

**Tasks**:
- [ ] Rewrite the `shell` job comment at `.github/workflows/ci.yml:122-124` (today; find it by its text) from
  `# Five skills ship bash suites their helper scripts are the subject of.` to
  `# Four skills ship five bash suites their helper scripts are the subject of.`
  (Premise: `ls skills/*/scripts/test_*.sh` returns five paths across four skill
  directories; re-run and write the counted numbers if they differ) (depends on:
  Phase 0) - Acceptance: `rg -n "Four skills ship five bash suites"
  .github/workflows/ci.yml` matches one line; `rg -c "Five skills"
  .github/workflows/ci.yml` exits 1 with no match; `python3 -c "import yaml,sys;
  yaml.safe_load(open('.github/workflows/ci.yml'))"` exits 0.
- [ ] Add one `### Added` bullet per name in `GRANDFATHERED`, shaped
  `- **<name>**: <what the skill does>`, taken from that skill's `SKILL.md`
  description (Premise: `scripts/check_changelog_skills.py` exists and its
  `GRANDFATHERED` holds the 14 names PRD 00020 shipped; re-read it at execution,
  use the list it actually holds, and if the file is absent skip this task and
  report the failed premise) (depends on: Phase 0) - Acceptance:
  `rg -c "^- \*\*" CHANGELOG.md` prints N0 - E + 14; `rg -c -- "\*\*catchup-ecc\*\*"
  CHANGELOG.md` prints 1, and the same command prints 1 for each of
  `check-python-compat`, `digest-github-repo`, `e2e-testing`,
  `frontend-patterns`, `manage-agents-md`, `python-patterns`, `research`,
  `resolve-git-conflicts`, `review-deps-prs`, `review-with-doubt`,
  `rust-testing`, `sync-plan-issue` and `watch-ci`.
- [ ] Empty `GRANDFATHERED` in `scripts/check_changelog_skills.py` (Premise: the
  backfill task above completed; skip and report if it did not) (depends on: the
  backfill task above) - Acceptance: `python3 -c "import sys;
  sys.path.insert(0,'scripts'); import check_changelog_skills as c;
  print(len(c.GRANDFATHERED))"` prints 0; `python3
  scripts/check_changelog_skills.py` exits 0 and prints nothing.
- [ ] Add the Removed entry for brief-portfolio under the sole `### Removed`
  heading: `- **brief-portfolio**: the skill and its app are gone (af1b704);
  the entries above that name it stay as written` (Premise:
  `ls skills/brief-portfolio` fails and `rg -n "^- \*\*brief-portfolio\*\*"
  CHANGELOG.md` prints no line below the `### Removed` heading; skip and report
  if one exists) (depends on: Phase 0) - Acceptance:
  `rg -n "^- \*\*brief-portfolio\*\*" CHANGELOG.md` matches one line whose
  number is greater than the sole `### Removed` heading's and smaller than the
  sole `### Fixed` heading's; `rg -c "^- \*\*" CHANGELOG.md` prints N0 - E + 15.

**Exit Criteria**: the workflow parses and states the true count,
`rg -c "^- \*\*" CHANGELOG.md` prints N0 - E + 15, and the changelog check
passes with an empty list.

### Phase 2: Integration
**Goal**: the log becomes a released 0.1.0 the artifacts agree with.

**Tasks**:
- [ ] Rename the `## [Unreleased]` heading to `## [0.1.0] - <the commit date as
  YYYY-MM-DD>` and insert a new empty `## [Unreleased]` heading, followed by one
  blank line, directly above it (Premise: `rg -n "Unreleased" CHANGELOG.md`
  returns exactly one line, the heading, and the file holds no `[Unreleased]:`
  link definition; re-run and stop if a second occurrence appeared) (depends
  on: Phase 1) - Acceptance: `rg -n "^## \[0\.1\.0\] - [0-9]{4}-[0-9]{2}-[0-9]{2}$"
  CHANGELOG.md` matches one line; `rg -n "^## \[Unreleased\]$" CHANGELOG.md`
  matches one line with a smaller number; `rg -c "^## " CHANGELOG.md` prints 2;
  no `###` heading or bullet sits between the two `## ` headings.
- [ ] Create the tag locally with `git tag v0.1.0` on the commit carrying the
  finished changelog (Premise: `git tag -l` prints nothing today; re-run and skip
  if `v0.1.0` already exists) (depends on: the heading task above) - Acceptance:
  `git tag -l v0.1.0` prints `v0.1.0`; `git tag -l` prints exactly one line;
  `rg -n '^version = "0.1.0"' pyproject.toml` still matches line 7.

**Exit Criteria**: the released section (beneath an empty `[Unreleased]`), the
tag, `pyproject.toml:7` and `src/agent_skills_braid/__init__.py:3` all read
`0.1.0`.

## Test Strategy

### Critical Scenarios
- **Happy path**: run every acceptance command above on the finished tree →
  Expected: six headings, N0 - E + 15 bullets, `v0.1.0` tagged, the changelog
  check green with an empty grandfather list.
- **Edge case**: a bullet silently dropped while merging the duplicates →
  Expected: the arithmetic catches it - N0 measured before the merge (176 on
  2026-10-17), minus E excluded-scope bullets (7), plus 15 backfilled, is
  N0 - E + 15 (184); any other count fails the phase.
- **Error case**: `scripts/check_changelog_skills.py` absent because PRD 00020
  has not landed → Expected: the backfill and list-emptying tasks report a
  failed premise and are skipped, the count stays N0 - E + 1, every other task
  completes.

## Risks

- **A large diff in a file people read by scrolling**: a bullet could vanish
  unnoticed. Mitigation: the bullet count is checked after every phase, not only
  at the end.
- **Deleting the excluded-scope entries**: the `**ci**`, `**tests**` and `**docs**`
  bullets record work that happened. Mitigation: accepted 2026-09-02 because
  `rules/changelog.md` excludes those commit types; the workflow and test files
  remain the record and git history keeps the text.
- **The backfill depends on another PRD**: 00020 owns the list. Mitigation: the
  premise clause skips and reports rather than guessing a list.
- **Human follow-up**: `git push origin v0.1.0` is one command a human runs
  after merge. Nothing above pushes or depends on the push.

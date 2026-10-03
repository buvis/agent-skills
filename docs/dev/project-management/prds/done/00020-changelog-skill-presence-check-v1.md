---
default_model: sonnet
rework_cap: 5
design: skip
---

# Check that every skill is named in the changelog

## Problem

`sweep-fix` shipped as a complete, runnable skill - 56 commits, listed by
Copilot, linked into both projections by braid - while `CHANGELOG.md` never
mentioned it, and nothing in the repo noticed. The changelog is the only record
of what this repo ships, so an unnamed skill is an invisible skill. The entry
was added at the walkthrough (`CHANGELOG.md:85`); this PRD carries the
prevention half. Source: agoge run
`dev/local/audit-results/agoge-2026-08-31.md`, finding 10 (HIGH, release lane);
decision 2026-09-02: ship the check with a grandfather list of the 14 skills the
changelog has never named, which PRD 00029 backfills and empties.

```
rg -n "sweep" CHANGELOG.md returns two hits, both unrelated prose at lines 165
and 217 (control: rg -c "distil-memory" CHANGELOG.md -> 24). git merge-base
--is-ancestor f8e91be 350a03c confirms CHANGELOG.md existed before
skills/sweep-fix/SKILL.md was added on 2026-08-29. 56 commits touch it.
```

## Solution

A stdlib-only Python script lists every directory under `skills/`, reads
`CHANGELOG.md` once, and reports each directory name that appears nowhere in the
file. Grandfathered names are skipped, so the check is green on today's tree and
red the moment a new skill lands with no entry. A pytest beside the script drives
it against a temporary skills tree; two `lint` steps in ci.yml run both.

## Requirements

### Must have

- Match each of the 47 directory names under `skills/` as a literal substring of
  `CHANGELOG.md`, skipping the names in `GRANDFATHERED`.
- Exit 0 and print nothing when nothing is missing; exit 1 with one
  `<name>: not named in CHANGELOG.md` line per miss on stderr.
- A test beside the script pins the failing arm against a temporary skills tree.
- `.github/workflows/ci.yml` runs script and test, and still parses as YAML.

### Nice to have

- A stricter match than "the name appears somewhere". The `**<name>**` scope
  prefix would need 29 grandfathered names today, not 14, because 15 skills are
  named only inside `**skills**`-scoped bullets, so it waits for 00029.

## Implementation

### Module: check_changelog_skills
- **Location**: `scripts/`
- **Responsibility**: report skill directories the changelog does not name
- **Exports**: `find_missing()`, `main()`, `GRANDFATHERED`

### Module: test_check_changelog_skills
- **Location**: `scripts/`
- **Responsibility**: pin both arms of the check against a temporary tree
- **Exports**: `test_reports_a_skill_dir_absent_from_the_changelog()`,
  `test_passes_when_every_skill_dir_is_named()`, `test_grandfathered_name_is_skipped()`

### Module: ci
- **Location**: `.github/workflows/`
- **Responsibility**: run the check and its test on every push and pull request
- **Exports**: the `lint` steps `Check every skill has a changelog entry` and
  `Test the changelog check`

### Dependencies
- check_changelog_skills: No dependencies (foundation)
- test_check_changelog_skills: Depends on [check_changelog_skills]
- ci: Depends on [check_changelog_skills, test_check_changelog_skills]

## Tasks

### Phase 0: Foundation

- [ ] Add `scripts/check_changelog_skills.py`, stdlib only, exposing
  `find_missing(skills_dir, changelog_path)` returning the sorted directory names
  under `skills_dir` that are neither substrings of the changelog text nor in
  `GRANDFATHERED`, `main(argv=None)` resolving `skills/` and `CHANGELOG.md` from
  the repo root, and `GRANDFATHERED` holding the 14 verified names and no
  others - Acceptance: `python3 scripts/check_changelog_skills.py` run from the repo
  root exits 0 and prints nothing on stdout or stderr; `python3 -c "import sys;
  sys.path.insert(0,'scripts'); import check_changelog_skills as c;
  print(sorted(c.GRANDFATHERED))"` prints exactly `['catchup-ecc',
  'check-python-compat', 'digest-github-repo', 'e2e-testing',
  'frontend-patterns', 'manage-agents-md', 'python-patterns', 'research',
  'resolve-git-conflicts', 'review-deps-prs', 'review-with-doubt',
  'rust-testing', 'sync-plan-issue', 'watch-ci']`.
- [ ] Add `scripts/test_check_changelog_skills.py`, building a temporary skills
  tree holding `zz-unlisted/SKILL.md` and a changelog naming no skill -
  Acceptance: `uv run pytest scripts/test_check_changelog_skills.py -q` exits 0,
  and `test_reports_a_skill_dir_absent_from_the_changelog` asserts
  `find_missing()` returns `['zz-unlisted']`.

### Phase 1: Core

- [ ] Add two steps to the `lint` job in `.github/workflows/ci.yml`, `Check every skill has a changelog entry`
  running `python3 scripts/check_changelog_skills.py` and `Test the changelog
  check` running `uv run pytest scripts/test_check_changelog_skills.py -q`
  (depends on: Phase 0) - Acceptance: `uv run python3 -c "import yaml,sys;
  yaml.safe_load(open('.github/workflows/ci.yml'))"` exits 0; `rg -n "python3
  scripts/check_changelog_skills.py" .github/workflows/ci.yml` matches one line;
  `rg -n "uv run pytest scripts/test_check_changelog_skills.py"
  .github/workflows/ci.yml` matches one line.

## Success Criteria

- `python3 scripts/check_changelog_skills.py` exits 0 against the execution-time
  inventory, retaining the pinned grandfather list. The 47/14/33 inventory
  was the review snapshot, not a fixed skill-count requirement.
- A new skill directory with no changelog mention makes `find_missing()` return
  its name, pinned by `uv run pytest scripts/test_check_changelog_skills.py -q`
  passing `test_reports_a_skill_dir_absent_from_the_changelog`.
- `.github/workflows/ci.yml` parses and `rg` finds both step commands in it.
- Human follow-up: the first GitHub Actions run after merge is where the steps'
  runner behaviour is observed. Nothing above depends on it.

Deferred follow-up, outside these success criteria: PRD 00029 is in `hold/`;
when resumed it backfills the grandfathered names and empties `GRANDFATHERED`.
This PRD completes with its fourteen-name list intact, without waiting for that work.

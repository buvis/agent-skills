# Sweep a Fix Across the Portfolio

Source: `~/.claude/dev/local/discovery/00151-sweep-fixes-across-repos.md`
(elicitation complete 2026-08-27, review 2026-08-28).

## Overview

### Problem Statement

`rules/development-workflow.md` § Bug Fix Discipline asks "Is this mistake
somewhere else also?" after every fix. Nothing enforces it, so the answer is
whatever the session has energy for. The same bug shapes then recur in sibling
repos and each one pays full price to rediscover them. Two shapes already
repeated across the portfolio: path-resolution assumptions (buvis pathspecs
resolving against cwd, the gemini symlink blindness on `dev/local`) and
string-match false positives (the codex exit-4 "quota" grep matching codex's own
command args).

### Target Users

The solo maintainer of the 26-repo buvis portfolio, immediately after landing a
`fix:` commit in one repo.

### Success Metrics

- A sweep against a fixture bug planted in three repos reports three hits with
  `file:line`.
- `git status --porcelain` in every repo other than the current one is
  byte-identical before and after a sweep.
- The report names every on-disk repo missing from the gita registry and states
  the count.
- A structural sweep's report carries an ast-grep rule block that runs unedited
  via `ast-grep scan --rule {file}`.

## Functional Decomposition

### Capability: Pattern derivation

Turn one fix commit into a machine-runnable hunt for the same mistake.

#### Feature: Derive the anti-pattern from a fix commit

- **Description**: Read a fix commit's diff and derive the pattern the sweep will
  hunt for.
- **Inputs**: A sha or a range, default `HEAD`; the current repo.
- **Outputs**: One derivation record: `kind` (`astgrep` or `rg`), the pattern
  text, and the reason that kind was chosen.
- **Behavior**: A bug with a code shape derives an ast-grep rule; a textual bug
  (config, docs, a bad literal) derives an `rg` pattern. The report states the
  kind and the reason, so a bad choice is visible rather than inferred. Exactly
  one kind per sweep.

#### Feature: Resolve the search tools the way this machine needs

- **Description**: Locate `rg` and `ast-grep` without assuming PATH.
- **Inputs**: None.
- **Outputs**: Two resolved executables, or a loud failure naming the one that
  could not be found.
- **Behavior**: `rg` is a bash function re-execing the claude binary, not a
  binary, so it is resolved the way `hooks/cartographer-echo.py` does
  (`_resolve_rg()` plus `executable=`). `ast-grep` is resolved with
  `mise which ast-grep`. Before any empty result is reported as "no hits", the
  same pattern shape is re-run with a control term known to be present in the
  fix commit's own diff; an empty control result aborts the sweep as unverified.

### Capability: Portfolio sweep

Run the derived pattern everywhere, without touching anything.

#### Feature: Enumerate the portfolio

- **Description**: Decide which repos a sweep covers.
- **Inputs**: `~/.config/gita/repos.csv`; the current working repo; the on-disk
  layout `~/git/src/github.com/*/*`.
- **Outputs**: A repo list, plus a gap list of on-disk repos absent from the
  registry.
- **Behavior**: Registry rows plus the current repo, registered or not. Repos
  found on disk but missing from the registry are reported as gap lines, never
  swept silently and never written into the CSV. The `~/.buvis` bare repo (work
  tree `$HOME`) is a named special case: its file set comes from
  `git --git-dir=~/.buvis --work-tree=~ ls-files -z`, converted to absolute
  paths, because the registry cannot express it and every pathspec there resolves
  against cwd. Registry parsing reuses the one-line `csv.reader` / `row[0]` read
  already in `brief-portfolio/scripts/collect.py:429`; no new registry reader.

#### Feature: Scan every repo read-only

- **Description**: Run the derived pattern across the repo list.
- **Inputs**: The derivation record and the repo list.
- **Outputs**: Per-repo hit rows carrying `file:line`, plus a suppressed count
  where a repo was capped.
- **Behavior**: No writes of any kind outside the current repo, and no git
  command that writes anywhere. Per-repo hits are capped at 20; when a repo is
  capped the report states the suppressed count, never truncates silently. Other
  worktrees may be edited live by the user during a sweep, so the scan reads and
  never locks.

### Capability: Reporting and local repair

Turn hits into something a human can act on.

#### Feature: Write the sweep report

- **Description**: Emit one report per sweep.
- **Inputs**: Derivation record, repo list, hit rows, gap list.
- **Outputs**: `dev/local/audit-results/sweep-{slug}-{date}.md` in the current
  repo.
- **Behavior**: Per-repo hit rows with `file:line`, the derived pattern and why
  that kind was chosen, the registry gap lines, any suppressed counts, the
  languages an ast-grep rule could not cover, and the verbatim how-to-proceed
  block at the end.

#### Feature: Carry installable guard text

- **Description**: Give a structural sweep a paste-ready guard.
- **Inputs**: The derived ast-grep rule.
- **Outputs**: A rule block inside the report, in loupe's rule-pack shape
  (`claude-loupe/rules/ast-grep/{lang}/rules.yml`).
- **Behavior**: The report carries the text; the sweep never installs it into
  loupe's pack.

#### Feature: Apply fixes in the current repo only

- **Description**: Let the operator close the hits they are standing on.
- **Inputs**: The hit rows for the current repo.
- **Outputs**: Edits in the current repo, on approval.
- **Behavior**: Fixes land only in the repo the sweep was invoked from, only
  after approval. Hits in every other repo stay report rows.

## Structural Decomposition

### Repository Structure

```
skills/
└── sweep-fix/               # Maps to: all three capabilities
    ├── SKILL.md             # Maps to: Reporting and local repair (the workflow)
    └── scripts/
        ├── sweep.py         # Maps to: Pattern derivation, Portfolio sweep
        └── test_sweep.py    # Tests for sweep.py
```

### Module: sweep-fix skill body

- **Maps to capability**: Reporting and local repair
- **Responsibility**: The invocation contract - derive, sweep, report, then walk
  the current repo's hits for approval. Verb-led name, request-only.
- **Exports**:
  - `SKILL.md` frontmatter with a trigger-led description under 250 chars
  - The how-to-proceed block appended verbatim to every report

### Module: sweep.py

- **Maps to capability**: Pattern derivation, Portfolio sweep
- **Responsibility**: Everything deterministic - tool resolution, repo
  enumeration, scanning, hit collection, report rendering.
- **Exports**:
  - `resolve_rg()`, `resolve_ast_grep()` - executables, or a loud failure
  - `enumerate_repos(registry_path, cwd)` - `(repos, gaps)`
  - `scan(pattern, repos, cap=20)` - hit rows plus suppressed counts
  - `render_report(derivation, hits, gaps)` - report markdown

## Dependency Graph

### Foundation Layer (Phase 0)

No dependencies - built first.

- **sweep.py resolvers and enumeration**: provides working `rg` / `ast-grep`
  handles and the repo list every later stage runs against.

### Core Layer (Phase 1)

- **sweep.py scan and report**: Depends on [sweep.py resolvers and enumeration]

### Integration Layer (Phase 2)

- **sweep-fix skill body**: Depends on [sweep.py scan and report]

## Implementation Phases

### Phase 0: Foundation

**Goal**: The sweep can find its tools and its repos on this machine.

**Tasks**:

- [ ] Add `resolve_rg()` and `resolve_ast_grep()` to `scripts/sweep.py` (no deps)
  - Acceptance: `test_sweep.py` asserts `resolve_rg()` returns a path that runs
    and that a `subprocess.run(["rg", ...])` style call is never used;
    `resolve_ast_grep()` returns the `mise which ast-grep` path.
- [ ] Add `enumerate_repos()` reading `~/.config/gita/repos.csv` plus the current
  repo, and the `~/.buvis` `ls-files -z` special case (no deps)
  - Acceptance: given a fixture CSV and a fixture on-disk tree, the function
    returns the registry repos plus cwd, and a gap list naming the on-disk repos
    absent from the CSV.

**Exit Criteria**: `enumerate_repos()` run against the real machine names every
on-disk repo absent from the registry and reports how many there were.

### Phase 1: Core

**Goal**: A pattern derived from one commit produces honest hit rows and a
report.

**Tasks**:

- [ ] Implement `scan()` with the per-repo cap of 20 and suppressed counts
  (depends on: Phase 0)
  - Acceptance: a fixture repo with 25 planted matches yields 20 rows and a
    suppressed count of 5; every row carries `file:line`.
- [ ] Add the control-term self-check that rejects an unverified empty sweep
  (depends on: Phase 0)
  - Acceptance: a deliberately broken pattern shape (Rust-regex `\|` alternation)
    over a corpus known to contain the control term aborts with an "unverified"
    error instead of reporting zero hits.
- [ ] Implement `render_report()` including the ast-grep rule block, the gap
  lines, the uncovered-language line and the verbatim how-to-proceed block
  (depends on: Phase 0)
  - Acceptance: the rendered report's rule block, extracted to a file, runs
    unedited via `ast-grep scan --rule {file}`.

**Exit Criteria**: `python scripts/sweep.py` against a fixture bug planted in
three repos writes a report with three `file:line` rows.

### Phase 2: Integration

**Goal**: The skill is invocable and provably read-only outside the current repo.

**Tasks**:

- [ ] Write `skills/sweep-fix/SKILL.md`: trigger-led description, the derive /
  sweep / report / walk workflow, the read-only rule, and a `## Dependencies`
  section naming `brief-portfolio/scripts/collect.py` (registry read shape),
  `hooks/cartographer-echo.py` (`rg` resolution) and loupe's rule-pack path
  (depends on: Phase 1)
  - Acceptance: the create-skill validator passes on the new skill.
- [ ] Add the read-only regression test (depends on: Phase 1)
  - Acceptance: a sweep across three fixture repos leaves
    `git status --porcelain` byte-identical in the two non-current repos.

**Exit Criteria**: `/sweep-fix HEAD` in a repo with a planted bug produces the
report, and only the current repo is ever modified.

## Test Strategy

### Critical Scenarios

- **Happy path**: a structural fix commit → an ast-grep rule is derived, three
  repos report hits with `file:line`, and the report's rule block runs unedited.
- **Happy path**: a textual fix commit → an `rg` pattern is derived and the
  report states why the textual path was chosen.
- **Edge case**: a repo with 25 matches under a cap of 20 → 20 rows plus an
  explicit suppressed count of 5, never a silent truncation.
- **Edge case**: an on-disk repo absent from the registry → one gap line in the
  report, no sweep of it, no write to the CSV.
- **Error case**: `rg` invoked as a plain binary name → the test fails, pinning
  the `_resolve_rg()` + `executable=` requirement.
- **Error case**: a pattern that matches nothing while its control term is
  present → the sweep aborts as unverified rather than reporting zero hits.

## Risks

- **Over-general patterns spam findings**: report-first, never auto-fix outside
  the current repo, and every report states hit counts plus any suppressed count.
- **The rg-as-function trap silently returns nothing**: it killed
  cartographer-echo's gate for months. Mitigated by resolving `rg` the way echo
  does and by the control-term self-check, which is a must-have task, not a
  nicety.
- **ast-grep grammar gaps make structural sweeps quietly partial**: the report
  names the languages the rule could not cover.
- **Sweeping live worktrees the user is editing**: read-only by construction,
  with the byte-identical `git status` test pinning it.
- **Registry rot**: gaps are reported, never repaired, so one loose CSV edit
  cannot silently widen a sweep.

---
default_model: sonnet
rework_cap: 5
design: skip
---

# Run the node suites in CI and document the install they need

## Overview

### Problem Statement
Both app skills document a `npm --prefix ... test` command with no install step
in front of it. `.gitignore:8` ignores `node_modules/`, so on a fresh clone that
command dies with `ERR_MODULE_NOT_FOUND: Cannot find package 'jsdom'`, an error
naming a missing package rather than a missing install, and the install line it
needs sits two sections lower under a heading that says "maintenance only".
Worse, `.github/workflows/ci.yml` has `test`, `shell` and `lint` jobs and no
node job, so neither smoke suite runs in CI and every UI regression test here
gates nothing. Source: agoge run
`dev/local/audit-results/agoge-2026-08-31.md`, finding 12 (MEDIUM, journey
lane); decision 2026-09-02: take both halves and drop the old sequencing
clause - the node job runs whatever suites exist when it lands.

```
Running the documented command verbatim gives
Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'jsdom', tests 18, pass 17,
fail 1. .gitignore:8 is node_modules/, so this is the state of every fresh
checkout. For brief-portfolio the shape is identical but the suite passes here
because node_modules happens to exist - that half is inferred, not observed.
```

### Target Users
Anyone following either skill's docs on a clone that has never installed, and
every future UI fix in these two apps that wants a gate outside a laptop.

### Success Metrics
- `npm --prefix ~/.agents/skills/<skill>/app install` is the first command in
  both `## Tests` fenced blocks.
- `.github/workflows/ci.yml` parses and carries a `node` job with four
  `npm --prefix skills/` lines.
- Both suites exit 0 from the repo root with zero failing tests, using each
  package's complete current test script. Portfolio has 44 tests at review;
  debrief has 47 before the additional regression in PRD 00021.

## Functional Decomposition

### Capability: Runnable test instructions
The documented Tests commands succeed on a checkout that has never installed.

#### Feature: Brief-portfolio install line
- **Description**: the Tests block installs before it tests.
- **Inputs**: `skills/brief-portfolio/SKILL.md`, fence at lines 125-128.
- **Outputs**: a three-command block, install first.
- **Behavior**: prepend `npm --prefix ~/.agents/skills/brief-portfolio/app
  install`, matching the installed-skill path style the block already uses.

#### Feature: Debrief-meeting install line
- **Description**: the same fix in the sibling skill.
- **Inputs**: `skills/debrief-meeting/SKILL.md`, fence at lines 149-152.
- **Outputs**: a three-command block, install first.
- **Behavior**: prepend `npm --prefix ~/.agents/skills/debrief-meeting/app
  install`.

### Capability: Node suites in CI
Both smoke suites run on every push and pull request, not only on a laptop.

#### Feature: Node job
- **Description**: a fourth job beside `test`, `shell` and `lint`.
- **Inputs**: `.github/workflows/ci.yml`.
- **Outputs**: a `node` job on `ubuntu-latest`.
- **Behavior**: same shape as the existing jobs, `actions/checkout@v7` then
  `actions/setup-node@v6` at node 24.

#### Feature: App suite steps
- **Description**: install and run each app's suite from the repo root.
- **Inputs**: the two `app/` directories, each with a committed
  `package-lock.json` (verified present in both, so `npm ci` is valid).
- **Outputs**: a red job when either suite fails.
- **Behavior**: `npm --prefix skills/<app>/app ci` then `... test` for both
  apps; invoke each package's current `test` script without listing or
  filtering test files. Portfolio also includes `smoke.a11y.test.js`.

## Structural Decomposition

### Repository Structure

```
.github/
└── workflows/
    └── ci.yml           # Maps to: Node job, App suite steps
skills/
├── brief-portfolio/
│   └── SKILL.md         # Maps to: Brief-portfolio install line
└── debrief-meeting/
    └── SKILL.md         # Maps to: Debrief-meeting install line
```

### Module: brief-portfolio-skill-doc
- **Maps to capability**: Runnable test instructions
- **Responsibility**: tell a reader what to run, in an order that works
- **Exports**:
  - `## Tests` block - the three commands a fresh clone runs

### Module: debrief-meeting-skill-doc
- **Maps to capability**: Runnable test instructions
- **Responsibility**: the same contract for the sibling skill
- **Exports**:
  - `## Tests` block - the three commands a fresh clone runs

### Module: ci
- **Maps to capability**: Node suites in CI
- **Responsibility**: run both node suites on every push and pull request
- **Exports**:
  - `node` job - checkout, setup-node, four `npm --prefix skills/` steps

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **brief-portfolio-skill-doc**: the documented install for the first app
- **debrief-meeting-skill-doc**: the documented install for the second app

### Core Layer (Phase 1)
- **ci**: Depends on [brief-portfolio-skill-doc, debrief-meeting-skill-doc]

### Integration Layer (Phase 2)
- none

## Implementation Phases

### Phase 0: Foundation
**Goal**: both documented Tests blocks work on a clone that never installed.

**Tasks**:
- [ ] Prepend `npm --prefix ~/.agents/skills/brief-portfolio/app install` to the
  `## Tests` fenced block in `skills/brief-portfolio/SKILL.md` (Premise: the
  fence at lines 125-128 holds exactly two commands, the `test_collect.py`
  pytest call then `npm --prefix ~/.agents/skills/brief-portfolio/app test`;
  re-read and skip if an install line is already first) (no deps) - Acceptance:
  `rg -c "brief-portfolio/app install" skills/brief-portfolio/SKILL.md` prints 2
  (the new Tests line plus the pre-existing rebuild line), and the first command
  line inside the `## Tests` fence is that install.
- [ ] Prepend `npm --prefix ~/.agents/skills/debrief-meeting/app install` to the
  `## Tests` fenced block in `skills/debrief-meeting/SKILL.md` (Premise: the
  fence at lines 149-152 holds exactly two commands, the `test_parse.py` and
  `test_debrief_build.py` pytest call then `npm --prefix
  ~/.agents/skills/debrief-meeting/app test`; re-read and skip if an install
  line is already first) (no deps) - Acceptance: `rg -c
  "debrief-meeting/app install" skills/debrief-meeting/SKILL.md` prints 2, and
  the first command line inside the `## Tests` fence is that install.

**Exit Criteria**: `rg -n "app install" skills/brief-portfolio/SKILL.md
skills/debrief-meeting/SKILL.md` returns four lines, two per file.

### Phase 1: Core
**Goal**: both smoke suites run in CI on every push and pull request.

**Tasks**:
- [ ] Add a `node` job to `.github/workflows/ci.yml` on `ubuntu-latest` with
  `actions/checkout@v7` and `actions/setup-node@v6` at node 24 (depends on:
  Phase 0) - Acceptance: `uv run python3 -c "import yaml,sys;
  yaml.safe_load(open('.github/workflows/ci.yml'))"` exits 0; `rg -n "^  node:"
  .github/workflows/ci.yml` matches one line; `rg -n "actions/setup-node@"
  .github/workflows/ci.yml` matches one line.
- [ ] Add four steps to that job: `npm --prefix skills/brief-portfolio/app ci`,
  `npm --prefix skills/brief-portfolio/app test`, `npm --prefix
  skills/debrief-meeting/app ci`, `npm --prefix skills/debrief-meeting/app test`
  (depends on: Phase 0) - Acceptance: `rg -c "npm --prefix skills/"
  .github/workflows/ci.yml` prints 4; `npm --prefix skills/brief-portfolio/app
  test` and `npm --prefix skills/debrief-meeting/app test` from the repo root
  both exit 0 with zero failures. Do not freeze the number of passing tests
  or the reporter's summary formatting; earlier PRDs can add tests.

**Exit Criteria**: the workflow parses, `rg` finds the `node` job and all four
`npm --prefix skills/` invocations, and both suites exit 0 locally.

### Phase 2: Integration
**Goal**: No additional capability; Phase 1 integrates both suites into CI.

**Tasks**: No additional tasks.

**Exit Criteria**: Both complete package test scripts run through the new job.

## Test Strategy

### Critical Scenarios
- **Happy path**: `npm --prefix skills/<app>/app ci` then `... test` from the
  repo root, both apps → Expected: exit 0 and zero failures on both, regardless of reporter format.
- **Edge case**: a checkout with `node_modules/` deleted, following the Tests
  block top to bottom → Expected: the install line creates `node_modules/` and
  the test line passes instead of raising `ERR_MODULE_NOT_FOUND`.
- **Error case**: a `package.json` change absent from `package-lock.json` →
  Expected: `npm ci` exits non-zero and the job stops before `npm test`, rather
  than silently resolving a different tree the way `npm install` would.

## Risks

- **A second toolchain in CI**: node joins uv. Mitigation: pin the setup action
  the way `astral-sh/setup-uv@v10.0.1` is pinned and let renovate move it.
- **The job could go red on defects it did not cause** (findings 11 and 16-19
  are open UI bugs in these apps). Mitigation: both suites pass locally today,
  so the job is green on the tree it lands on, and no PRD sequences behind it.
- **Two path styles for one command**: the SKILL.md blocks address the installed
  skill (`~/.agents/skills/...`), the workflow the checkout (`skills/...`).
  Mitigation: keep both forms, never copy one into the other's place.
- **Human follow-up**: read the first GitHub Actions run after merge and open a
  separate PRD for anything that only appears on a hosted runner. Nothing here
  is gated on that run.

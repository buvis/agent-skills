# Put Config Maintenance on a Calendar

Source: `~/.claude/dev/local/discovery/00155-schedule-maintenance-cadence.md`
(decisions resolved 2026-08-28).

## Overview

### Problem Statement

The maintenance tooling already exists and nothing invokes it on a schedule. The
audits run when someone remembers, which means they run after the drift has
already cost something - one hand-run cleanup reclaimed ~46 MB of stale plugin
versions and archived nine legacy project dirs, work nothing would have
scheduled. The gap is a cadence, not a capability. The brief already carries a
single coarse maintenance nag whose stamp is the newest mtime under
`~/.claude/dev/local/audit-results/`, which is a proxy: three of the seven audits
write no report at all, so the row can read green while they have never run.

### Target Users

The solo maintainer, once a month, reading the portfolio brief.

### Success Metrics

- A unit test on row state at ages 0, horizon-1 and horizon+1 days, and with no
  run recorded, passes for both horizons.
- The rendered brief shows one row per audit, each naming the command to run.
- No prompt, question or interactive step is added to the brief run.

## Functional Decomposition

### Capability: Cadence stamps

#### Feature: Read each audit's last run from the skill metrics log

- **Description**: Find when each maintenance skill last ran.
- **Inputs**: `~/.local/share/agents/metrics/skills.jsonl`, one `{skill, ts}` row
  per invocation written by `track_skills.py`.
- **Outputs**: `{skill: newest ISO day}` for the six machine-wide audits, with
  `None` where a skill has never run.
- **Behavior**: Newest `ts` per skill, with no lookback cutoff - unlike the
  existing 30-day adherence summary, a never-run skill must stay visible. Plugin
  skills are namespaced (`claude-checkup:audit-filesystem`); `purge-devlocal` is
  not. Accepted imprecision: a run that was invoked but abandoned still counts,
  and the log records no repo. Replaces the `audit-results` newest-mtime proxy,
  which three of the audits never write to.

#### Feature: Read purge-devlocal's last run per repo

- **Description**: Stamp the one audit that is per-repo, not machine-wide.
- **Inputs**: Each repo's `dev/local/.trash/<date>/` directories - the GC's own
  trash-first artifact.
- **Outputs**: One ISO day per repo, or `None`.
- **Behavior**: The newest `<date>` directory name, read the way `collect_brush`
  reads the brush stamp, and collected per repo alongside it. `skills.jsonl`
  cannot answer this one, because it records no repo.

### Capability: Drift-rate rows

#### Feature: Emit one nag row per audit at its own horizon

- **Description**: Turn stamps into rows that go red on their own clock.
- **Inputs**: The stamps above.
- **Outputs**: One todo row per audit, carrying the audit's command name.
- **Behavior**: 30-day horizon for `audit-filesystem` and `purge-devlocal` - disk
  and `dev/local` drift in weeks. 90-day horizon for `audit-context`,
  `audit-config`, `audit-authoring`, `audit-sessions` and `audit-mcp-health`. A
  row is red when the last run is older than its horizon, and reads "never" with
  no run recorded. Both horizons are stated guesses with no measurement behind
  them; one set too long hides drift while the row looks green. Rejected:
  monthly for all seven (seven red rows a month becomes wallpaper), quarterly for
  all (the fastest-drifting item gets the slowest response), and a rotating
  single row (an individual audit would come round barely twice a year).

#### Feature: Name the command, run nothing

- **Description**: Keep the brief a report.
- **Inputs**: The row's audit.
- **Outputs**: The command text in the row's action line.
- **Behavior**: The row names the command; it does not run it and is not
  clickable-to-run. A nag is a reminder, not a run, so drift still accrues between
  the row turning red and the audit being performed - accepted, because a
  scheduled unattended run that hits a question stalls, the `WARDEN_UNATTENDED`
  failure class. Rejected outright: a cloud routine via the `schedule` skill
  (cloud agents cannot read `~/.claude` on this machine, so `audit-filesystem`
  and `audit-context` would audit an environment that lacks the thing they
  audit), and a local launchd job (new infrastructure to own, and it stalls on a
  question).

## Structural Decomposition

### Repository Structure

```
skills/brief-portfolio/
├── scripts/
│   ├── collect.py            # Maps to: Cadence stamps
│   └── test_collect.py       # Tests for the collectors
└── app/src/lib/
    ├── derive.js             # Maps to: Drift-rate rows
    └── derive.test.js        # Tests for the row states
```

### Module: collect.py cadence collectors

- **Maps to capability**: Cadence stamps
- **Responsibility**: Produce the last-run stamps, machine-wide and per repo.
  Replaces `collect_claude_maintenance`, whose newest-mtime proxy this supersedes.
- **Exports**:
  - `collect_audit_cadence(base=None)` - `{skill: ISO day | None}` for the six
    machine-wide audits
  - `collect_purge_devlocal(path)` - ISO day of the newest
    `dev/local/.trash/<date>/` in one repo, or `None`
  - `external.audit_cadence` and the per-repo `purge_last_run` payload keys

### Module: derive.js audit rows

- **Maps to capability**: Drift-rate rows
- **Responsibility**: Turn stamps into red-or-silent rows with per-audit
  horizons. Replaces the single `maintenance` todo emitted by `externalTodos`.
- **Exports**:
  - `AUDIT_CADENCE` - the audit-to-horizon table (30d / 90d)
  - `auditTodos(external, repos)` - one row per due or never-run audit,
    consumed by `externalTodos`

## Dependency Graph

### Foundation Layer (Phase 0)

No dependencies - built first.

- **collect.py cadence collectors**: nothing can render a row before a stamp
  exists.

### Core Layer (Phase 1)

- **derive.js audit rows**: Depends on [collect.py cadence collectors]

### Integration Layer (Phase 2)

- **rendered brief**: Depends on [derive.js audit rows, collect.py cadence
  collectors]

## Implementation Phases

### Phase 0: Foundation

**Goal**: Every audit has an honest last-run stamp.

**Tasks**:

- [ ] Add `collect_audit_cadence()` to `scripts/collect.py`, reading the newest
  `ts` per skill from `skills.jsonl` with no lookback cutoff (no deps)
  - Acceptance: given a fixture log, it returns the newest day per skill and
    `None` for a skill with no rows; a namespaced key
    (`claude-checkup:audit-filesystem`) and an unnamespaced one
    (`purge-devlocal`) both resolve.
- [ ] Add `collect_purge_devlocal(path)` and wire it into `collect_repo`
  alongside `brush_last_run` (no deps)
  - Acceptance: a fixture repo with `dev/local/.trash/2026-08-01/` and
    `dev/local/.trash/2026-08-20/` yields `2026-08-20`; a repo with no `.trash/`
    yields `None`.
- [ ] Remove `collect_claude_maintenance` and its `claude_maintenance_last`
  payload key (no deps)
  - Premise: `collect.py` still defines `collect_claude_maintenance` (the
    newest-mtime proxy over `~/.claude/dev/local/audit-results/`) and still sets
    `data["external"]["claude_maintenance_last"]`. Re-check at execution; if
    either is already gone, skip that half and report it rather than
    re-introducing the key.
  - Acceptance: `rg claude_maintenance_last` over `scripts/` and `app/src/`
    returns nothing, and `test_collect.py` has no test referring to it.

**Exit Criteria**: `uv run --with pytest pytest scripts/test_collect.py` passes
with zero failures and the payload carries `audit_cadence`.

### Phase 1: Core

**Goal**: Rows go red on the right clock.

**Tasks**:

- [ ] Add the `AUDIT_CADENCE` table and `auditTodos()` to `app/src/lib/derive.js`,
  and call it from `externalTodos()` in place of the single `maintenance` row
  (depends on: Phase 0)
  - Premise: `externalTodos()` still emits exactly one `kind: 'maintenance'` todo
    gated on `MAINT_DUE_DAYS`. Re-check at execution; if the shape has changed,
    adapt to what is there and report the difference.
  - Acceptance: seven rows are defined - `audit-filesystem` and `purge-devlocal`
    at 30 days, `audit-context`, `audit-config`, `audit-authoring`,
    `audit-sessions` and `audit-mcp-health` at 90 days - and each row's action
    names its command.
- [ ] Add the row-state tests to `app/src/lib/derive.test.js` (depends on:
  Phase 0)
  - Acceptance: for both horizons, age 0 emits no row, age horizon-1 emits no
    row, age horizon+1 emits a red row, and a missing stamp emits a row whose id
    ends `never`.

**Exit Criteria**: `node --test app/src/lib/derive.test.js` passes with zero
failures.

### Phase 2: Integration

**Goal**: The brief shows the rows and asks nothing.

**Tasks**:

- [ ] Run `collect.py` plus `build.py --out dev/local/tmp/brief-check.html`
  against the live machine and check the rendered brief (depends on: Phase 1)
  - The explicit `--out` keeps the render inside the unattended write fence,
    which allows only the repo, `dev/local`, `$TMPDIR` and `/tmp`; `build.py`
    defaults to `~/.local/share/agents/portfolio-brief/`, which it denies.
  - Acceptance: the rendered file at `dev/local/tmp/brief-check.html` carries one
    row per due or never-run audit, each naming its command, and the run
    completes with no prompt or question added.

**Exit Criteria**: The monthly brief carries per-audit cadence rows instead of
one coarse maintenance row.

## Test Strategy

### Critical Scenarios

- **Happy path**: `audit-context` last run 100 days ago → a red row naming
  `/claude-checkup:audit-context`.
- **Happy path**: `audit-filesystem` last run 10 days ago → no row.
- **Edge case**: exactly at the horizon → the boundary is pinned by the
  horizon-1 / horizon+1 tests, so a later refactor cannot flip it silently.
- **Edge case**: a skill with no rows in `skills.jsonl` → a "never" row, not a
  green one; this is the case the old mtime proxy hid.
- **Error case**: `skills.jsonl` missing or unreadable → collectors return `None`
  and the brief renders "never" rows rather than crashing.
- **Error case**: a malformed JSON line in the log → skipped, the rest still
  parsed, matching the existing adherence collector's behavior.

## Risks

- **Both horizons are guesses**: no measurement stands behind 30 or 90 days, and
  one set too long hides drift behind a green row. Mitigation: they are two
  constants in one table, tuned after the first months of real rows.
- **Row wallpaper**: seven rows going red together would be ignored. Mitigation
  is the split cadence itself - only the two fast-drifting audits can fire
  monthly.
- **A nag is not a run**: drift still accrues between red and done. Accepted; the
  alternatives that actually execute either cannot read `~/.claude` (cloud
  routines) or stall on a question (a local job).
- **The stamp counts abandoned invocations**: `skills.jsonl` records the
  invocation, not the completion, so a started-and-abandoned audit resets the
  clock. Accepted, and stated in the row's why-line.
- **Automating `purge-devlocal` later**: deferred, not dismissed. It would trash
  while a loop may be mid-flight; its own idle horizons handle that and must not
  be shortened.

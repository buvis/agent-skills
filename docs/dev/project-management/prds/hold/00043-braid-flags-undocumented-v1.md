---
default_model: opus
rework_cap: 5
---

# Four braid flags exist with neither help text nor README coverage

Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 39
(LOW, release lane, verified). Decision 2026-09-02: accepted — add `help=`
strings and a README flag table.

## Overview

### Problem Statement

`braid --help` lists `--policy`, `--agents-root`, `--claude-root`,
`--config-root` and `--no-claude` with a blank description column, and the
README names none of the first four. `--policy` is fully functional and
reachable only by reading the source. The root-overriding flags — the ones
that make braid safe to run against scratch directories — are the least
discoverable of all, while the three env vars the README does document work
exactly as written.

### Target Users

Anyone driving braid beyond the default sync — especially against scratch
roots.

### Success Metrics

- All five `add_argument` calls carry `help=` text.
- The README's braid section has a one-line-per-flag table covering them.

## Functional Decomposition

`help=` strings on the five arguments; a small flag table in the README
beside the env-var documentation.

## Structural Decomposition

- `src/agent_skills_braid/cli.py` (~415-419)
- `README.md` (~134-136)

## Implementation Phases

### Phase 0: The docs

Both surfaces in one commit.

## Test Strategy

Evidence from the report, verbatim:

```
The help output shows the five flags with no help= text. --policy is fully
functional and reachable only by reading the source: running with
--policy /…/mypolicy.txt gave 21 ignored against 20 ignored without it.
```

Check: `braid --help` shows a description for every flag.

## Risks

Creates the same two-places-to-update situation that produced the gap —
accepted; generating the table in CI was declined as machinery for a five-row
table.

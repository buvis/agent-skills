---
default_model: sonnet
rework_cap: 5
catchup: force
design: skip
---

# The review queue lands wherever the shell happens to be

## Problem

`docket.py` exposes no queue-path flag. `_resolve_path()` (`skills/distil-memory/scripts/docket.py:26-27`)
falls back to `_report_dir()` (lines 18-23), which walks up from `Path.cwd()` to the nearest `.git` and returns
`<that root>/dev/local/audit-results/distil-memory-queue.json`, or the cwd itself when no ancestor has a
`.git`. `_parse_args` (lines 156-173) gives `save` a `--proposals-dir` and nothing else, and every `main()`
branch calls in with the default path (lines 191, 202, 205, 213, 219), so the queue follows the shell rather
than the proposals it describes. Run the walkthrough from the wrong directory and it reports "drained" while
undecided proposals sit in another repo's queue; worse, a second queue re-offers a decided proposal, the write
fails "already exists", and `SKILL.md:204-207` then tells the operator to rename through the edit path, which
would put a second copy of the same memory in the plane under a different name. Source: agoge run
`dev/local/audit-results/agoge-2026-08-31.md`, finding 6 (HIGH, integration lane); decision 2026-09-02: add
`--queue PATH` to every subcommand and default `save`'s queue off `--proposals-dir`.

```
Running save --proposals-dir <repoA>/proposals from repo B wrote the queue
into repo B while repo A's queue kept its own 2 entries. Cursors then
disagreed: cursor from A: 1 | cursor from B: 0, and repo B's next re-offered
a proposal already written to disk from repo A. The subsequent write failed:
exit 1 | .../store/memory/scratch-fact-one.md already exists.
```

## Solution

Give every subcommand a `--queue PATH` argument and pass it to `load`/`save`/`next_undecided`/`decide`/
`cursor`/`advance`, which all already take `path=`. With `--queue` absent, `save` derives the queue from
`--proposals-dir` instead of the cwd, so the queue follows the proposals it describes; the other subcommands
keep the cwd walk as their only fallback. `SKILL.md` then passes `--queue` in every command example, the way it
already has the driver derive `<store-path>` itself (`SKILL.md:187`).

## Requirements

### Must have

- `save`, `start`, `next`, `decide` and `cursor` each accept `--queue PATH` and operate on exactly that file,
  whatever the cwd is.
- With no `--queue`, `save` uses `Path(args.proposals_dir).parent / "distil-memory-queue.json"`, and the other four subcommands keep the `_report_dir()` cwd walk unchanged.
- `SKILL.md` passes `--queue "<queue-path>"` in all seven `docket.py` examples (lines 144, 154, 160, 176, 183,
  237, 251) and says how the driver derives `<queue-path>` from `<proposals-dir>`.

### Nice to have

- none

## Implementation

### Module: docket
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: queue persistence and the CLI the walkthrough drives
- **Exports**: `_parse_args()`, `_resolve_path()`, `_save_from_proposals_dir()`, `main()`

### Module: test_docket
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: the queue's regression suite, including its CLI wiring
- **Exports**: the `main()` CLI tests at `test_docket.py:402-727`

### Module: SKILL
- **Location**: `skills/distil-memory/`
- **Responsibility**: the approval walkthrough the driver follows
- **Exports**: the `save` preamble (line 144) and steps 1, 2, 4, 5, 6, 7

### Dependencies
- PRD 00015: must finish first; preserve its corrupt-queue exit codes and walkthrough handling.
- docket: No dependencies (foundation)
- test_docket: Depends on [docket]
- SKILL: Depends on [docket]

## Tasks

### Phase 0: Foundation

- [ ] Add `--queue PATH` to all five subparsers and thread it into every `main()` branch - Acceptance: `uv run
  pytest skills/distil-memory/scripts/test_docket.py -q` passes with new tests that chdir into `tmp_path`, pass
  `--queue <tmp_path>/elsewhere/q.json` to `save`, `start`, `next`, `decide` and `cursor`, and assert every
  entry and the cursor land in that file while `<tmp_path>/dev/local/audit-results/` is never created.
- [ ] Default `save`'s queue off `--proposals-dir` - Acceptance: a new test in
  `skills/distil-memory/scripts/test_docket.py` chdirs into `tmp_path/repo_b`, runs `docket.main(["save",
  "--proposals-dir", str(tmp_path / "repo_a" / "proposals")])`, then asserts `(tmp_path / "repo_a" /
  "distil-memory-queue.json").exists()` is True and that no `distil-memory-queue.json` exists anywhere under
  `tmp_path/repo_b`.
- [ ] Repoint every existing `save` CLI test that reads the old cwd-derived queue (depends on: the new
  save default). Premise: existing save tests call `docket.load()` without the path written by the
  command; re-read each test before editing and skip only assertions already using the correct path.
  Seven call sites existed at review time; that count is historical, not an execution guard.
  Acceptance: inventory affected tests by name, record each assertion's before/after queue path, and
  `uv run pytest skills/distil-memory/scripts -q` passes with every affected assertion reading the
  command's derived or explicitly requested queue. New save tests and PRD 00015's exit-code coverage
  remain intact; an increased call count never skips this migration.
- [ ] Pass `--queue` in every `SKILL.md` command example - Acceptance: `rg -c "docket.py.*--queue"
  skills/distil-memory/SKILL.md` prints `7`, and `rg -n "queue-path" skills/distil-memory/SKILL.md` shows the
  sentence deriving it from `<proposals-dir>`.

### Phase 1: Core

No additional work; the Phase 0 tasks deliver the complete queue-path capability.

## Success Criteria

- `uv run pytest skills/distil-memory/scripts -q` reports no failures.
- A `save --proposals-dir <repoA>/proposals` run from any cwd writes exactly one queue file, derived from repo
  A, and creates nothing under the cwd's repo.
- `rg -n "docket.py" skills/distil-memory/SKILL.md` shows no invocation without a `--queue` argument.
- Human follow-up, not a task, and outside this repo's write scope: sweep the portfolio for stray
  `distil-memory-queue.json` files the old cwd resolution scattered into other repos and fold any undecided
  entries back by hand. This fix does not migrate them.

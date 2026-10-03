# Backlog review supplement - agent-skills - 2026-09-05 (PRDs 00053 to 00074)

Verdict for this subset: GO for 00053 to 00069 and 00071 to 00074 (21 READY);
00070 HOLD (loop self-harm, parked beside 00035).

Scope: the 22 PRDs emitted after `backlog-review-2026-09-05.md` was written
at 10:01 (that report covers 00016 to 00052 and is owned by another session,
still waiting on B07; nothing in it was touched here). 00053 to 00069 come
from the agoge-2026-09-05 walkthrough, 00070 to 00074 from the walk of batch
202608290848's deferred file. The reviewer is also the author, so lenses B,
C, F, G and H are a self-check; the drain's own design and review phases
remain the independent gate.

## Map

| # | PRD | template | lines | subsystems | depends on | verdict |
|---|---|---|---:|---|---|---|
| 00053 | split oversized brief suites | minimal | 110 | brief-portfolio tests (js, py) | none; drains before 00054-00069 by number | READY |
| 00054 | non-JSON metadata kills collect | minimal | 90 | collect.py | none | READY |
| 00055 | bad metrics ts aborts run | minimal | 96 | collect.py | none | READY |
| 00056 | CI failure fakes no CI | minimal | 91 | collect.py | done 00026 (page side) | READY |
| 00057 | data.json world-readable | minimal | 84 | collect.py | none | READY |
| 00058 | page links accept javascript: | minimal | 96 | derive.js, 4 components | none | READY |
| 00059 | build dies on torn inputs | minimal | 93 | build.py | none | READY |
| 00060 | torn history fuses next row | minimal | 78 | collect.py | none | READY |
| 00061 | meta failure fakes hygiene nags | minimal | 84 | collect.py | none | READY |
| 00062 | commit cap hides true count | minimal | 97 | collect.py, Brief, RepoDetail | done 00028 | READY |
| 00063 | missing registry tracebacks | minimal | 78 | collect.py | none | READY |
| 00064 | braid follows symlinked skill | minimal | 82 | braid cli.py | none | READY |
| 00065 | build reads whole history | minimal | 79 | build.py | 00059 (lower) | READY |
| 00066 | clipboard markdown unescaped | minimal | 79 | Todos.svelte | 00058 (lower) | READY |
| 00067 | remote URL passes query/dotdot | minimal | 83 | collect.py | none | READY |
| 00068 | redundant branch resolve | minimal | 78 | collect.py | none | READY |
| 00069 | announcement window injectable | minimal | 95 | Todos.svelte, harness, smoke test | 00053 (lower, file move) | READY |
| 00070 | purge trash-first guarantee | minimal | 91 | purge_devlocal.py | loop self-harm | HOLD |
| 00071 | distil publish recovery | minimal | 135 | write.py, docket.py, SKILL.md | wip 00015's docket changes (read at catchup) | READY |
| 00072 | distil judge no persistence | minimal | 88 | funnel.py | none | READY |
| 00073 | sweep loud failures | minimal | 122 | sweep.py | none | READY |
| 00074 | distil tests bind intent | minimal | 86 | 3 test files | 00071 (lower) | READY |

## Findings

### Blocking

- [00070] B/E: edits `purge_devlocal.py`, which the installed autopilot
  invokes at batch drain (B15 in the primary report) -> fails as: loop
  self-harm. Applied: moved to `hold/` next to 00035; both drain together in
  a dedicated batch or attended, as B15 prescribes for 00035.

### Non-blocking

- [00053] A: an acceptance `rg` used shell globs the citation checker split
  into two dangling targets. Applied: `-g` globs on the directory.
- [00061] A: the citation checker flagged `dev/local/audit-results/brush-report.md`,
  a fixture the test creates. Applied: `link-ok:` token on the line.
- [00069] B/E: an acceptance `rg` named `smoke.test.js`, which 00053 deletes
  first. Applied: the check runs over the app directory.
- [00059, 00073] A: `{path}` and `{exc}` inside backticked f-strings trip a
  naive stub scan; they are code, not placeholders. Left as is.
- [00071] E: lands after wip 00015, which is changing `docket.py` live.
  `catchup: run` (default) re-grounds it; no edit needed unless 00015's
  exit-code split moves `load()`'s error shape, which 00071 does not touch.

### Questions

- none. Every contract value in these PRDs was pinned at emission from code
  read the same day (line numbers cited in each Problem section).

## Reshapes

- 00070 -> `hold/` (applied). No merges: 00054 to 00068 each own one
  collector defect with its own regression test, and the drain rebases them
  sequentially onto the same `collect.py`; merging would recreate the
  multi-defect PRDs the rework-cap history argues against.

## Gaps

- Held 00018 owns the Brief and Work-tab collection-failure UI; no backlog
  PRD depends on it.
- 00053 must actually drain before 00054: ascending selection guarantees it,
  and 00054 to 00069 name "the PRD 00053 successor" for the moved test files.

## End state after this batch

The brief-portfolio collector survives a flaky GitHub morning, a torn
history file, a bad metrics row and a hostile epics.json; the page tells
the truth about capped commit lists and failed CI fetches; braid ignores
planted symlinks; the two oversized suites are split before they grow again;
distil-memory's publication is recoverable and its judge calls stop feeding
the corpus they scan; sweep-fix fails loud. Left explicit: 00070 and 00035
(purge helper) wait for a dedicated batch; 00018 and the other opus PRDs wait
in hold on the operator's cost decision.

## Frontmatter tuning

All 22 parse as valid (checked by script). 00053, 00071 and 00073 carry
`design: run` with `opus` (equivalence or invented-contract escalators);
the rest `sonnet` with `design: skip` and a one-line rationale each.

## Gate honesty and verification

- Lenses A and D (headings, frontmatter, stubs, acceptance clauses, cited
  path existence, citation resolution via `check_links.py --root . --json`,
  higher-number dependency scan) ran by script over all 22; output kept in
  this session's scratchpad. Lenses B, C, E, F, G, H ran inline by the
  author-reviewer; no subagent was dispatched, so this is a self-check, not
  an independent grounding pass.
- Primary report untouched; its 17 PRDs were not re-reviewed.
- The drain (PRD 00015, phase review) advanced HEAD during this work
  (`f4824a9`, `4120994`, `5ef8be1`); nothing here edited its files, state or
  wip PRD.

## Decisions applied

- 00053, 00061, 00069: acceptance-text edits above.
- 00070: `mv` to `hold/`; reason recorded here and in
  `deferred-walk-202608290848-2026-09-05.md`.
- Decisions were the reviewer's own, on the operator's delegation
  ("involve me only for decisions you cannot make").

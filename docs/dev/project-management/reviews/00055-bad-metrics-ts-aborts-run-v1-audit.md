# Decision Audit Log: 00055-bad-metrics-ts-aborts-run-v1

PRD: `00055-bad-metrics-ts-aborts-run-v1.md`
Started: 2026-09-21T05:40:34Z
Completed: 2026-09-21T05:40:34Z
Autonomous: 7  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-21T05:40:34Z

**Decision**: F1 [2/4] 🟠 No CHANGELOG.md entry for the three fix(brief-portfolio) commits (rules/changelog.md blocking rule); shadow engine confirmed it twice

**Choice**: auto-fix -> [D1] task 3 (CHANGELOG entry under [Unreleased] > Fixed, docs-only, own commit)

**Rationale**: Cycle 1 decision gate: additive-only docs change and a standing rule mandates it; not a settled deferral, not a blocker. Cycle 1 does not converge on this 🟠; 1 < rework_cap 2 so rework runs.

### [autonomous] 2026-09-21T05:40:34Z

**Decision**: F2 [1/4] 🟡 _parse_ts("0001-01-01T00:00:00+01:00") raises OverflowError from astimezone outside the except, so one filterable row costs the whole metric (collect.py:275); shadow correctness dimension reproduced it

**Choice**: auto-fix -> [D1] task 4 (widen except to (ValueError, OverflowError), move astimezone inside the try, tests-first with the boundary row in both reader tests)

**Rationale**: Cycle 1 decision gate: medium with a clear two-line mechanical fix; PRD says the helper catches parse/type failures internally, so this is in scope.

### [autonomous] 2026-09-21T05:40:34Z

**Decision**: F3 [1/4] 🟡 Naive rejection and UTC normalization unpinned: every valid fixture is +00:00 and the naive fixtures lose anyway (test_collect_local.py:91); shadow tests dimension found the same and failed R1 on it

**Choice**: auto-fix -> [D1] task 4 (add an offset row crossing UTC midnight, a newer naive cadence row, and an in-window naive adherence row; keep test names)

**Rationale**: Cycle 1 decision gate: medium, 1/4 consensus, additive tests only. Bob R1 fail and shadow R1 fail both point here; the added rows make the mutants fail.

### [autonomous] 2026-09-21T05:40:34Z

**Decision**: F4 [1/4] 🟡 Redundant negative assertions (test_collect_local.py:246-247) and a comment paraphrasing the assertions (test_collect_pipeline.py:292-294) in the new regression tests; shadow quality dimension flagged the dead asserts too

**Choice**: auto-fix -> [D1] task 4 (delete the two inequalities and the three-line comment, no coverage change)

**Rationale**: Cycle 1 decision gate: medium, clear mechanical fix, de-slop lens; folded into task 4 because it touches the same two test files.

### [autonomous] 2026-09-21T05:40:34Z

**Decision**: F5 [1/4] ⚪ Cannot statically verify: tests, skill validation, and braid checks pass at the reviewed HEAD (Bob, VERIFY bucket)

**Choice**: routed to verification: `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio`, `braid --check` (dev/local/reviews/00055-bad-metrics-ts-aborts-run-v1-checks-1.json, 3 entries); no task created

**Rationale**: Cycle 1 decision gate: Low finding matching this cycle queue entries on issue text; its checks run in the rework work pass step 7 (PRD 00164). All three already ran green at 893e2df in the work phase.

### [autonomous] 2026-09-21T05:40:34Z

**Decision**: F1 [1/4] ⚪ Carried forward from checks-1.json: queued check `braid --check` -> exit 127 (cycle-1 F5 verification item)

**Choice**: discarded (ledger: discarded, verified reason); no task

**Rationale**: Cycle 2 decision gate: exit 127 is `command not found` — `braid` is not on the headless PATH (re-confirmed this session). The same check by absolute path, /Users/bob/.agents/bin/braid --check, exited 0 at HEAD 5552bd1 in the work phase and again in this session (0 drift). Environment artifact, not a repo defect; the other two queued checks exited 0.

### [autonomous] 2026-09-21T05:40:34Z

**Decision**: F2 [1/4] 🟡 mech-check replay: test_a_raising_skill_adherence_reader_costs_one_metric_not_the_run passes against the cycle-1 base 893e2df (test_collect_pipeline.py)

**Choice**: discarded (ledger: discarded, verified reason); no task, no sweep

**Rationale**: Cycle 2 decision gate: the only change to this test in the reviewed diff is the removal of a three-line paraphrasing comment (cycle-1 F4); no assertion changed, so passing at the cycle-1 base is expected. Its behavior was pinned in cycle 1 (failed against a563e06a in the cycle-1 replay). Shadow engine R2 note and all four reviewers read it the same way.

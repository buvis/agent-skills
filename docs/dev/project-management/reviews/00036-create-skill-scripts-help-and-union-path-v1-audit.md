# Decision Audit Log: 00036-create-skill-scripts-help-and-union-path-v1

PRD: `00036-create-skill-scripts-help-and-union-path-v1.md`
Started: 2026-09-07T01:08:58Z
Completed: 2026-09-07T01:08:58Z
Autonomous: 6  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-07T01:08:58Z

**Decision**: Missing CHANGELOG.md [Unreleased] > Fixed entry for the two user-visible fix(create-skill) commits

**Choice**: auto-fix

**Rationale**: Additive only (adds two changelog bullets, no signature/type/schema change) and mandated by the repo standing changelog rule, so no judgment call remains. Queued as rework task 5 in cycle 1.

### [autonomous] 2026-09-07T01:08:58Z

**Decision**: test_validate_skill.py: duplicate --help tests, PRD-required -h alias untested, argparse required-argument diagnostic unpinned, stale module docstring

**Choice**: auto-fix

**Rationale**: Clear mechanical fix plus additive test coverage; the PRD-named export test_help_flag_prints_usage_and_exits_zero and its two pinned asserts are preserved. Queued as rework task 6 in cycle 1.

### [autonomous] 2026-09-07T01:08:58Z

**Decision**: test_init_skill.py: two overlapping scaffolder tests assert the same printed-output contract, one with a function-local import that shadows the module-level name

**Choice**: auto-fix

**Rationale**: Clear mechanical fix; the PRD-named export test_printed_validate_step_names_the_union_path and its two pinned asserts are preserved and absorb the extra assertions. Queued as rework task 7 in cycle 1.

### [autonomous] 2026-09-07T01:08:58Z

**Decision**: BOB VERIFY: Cannot statically verify the PRD success-criterion commands (uv run pytest, validate_skill.py skills/create-skill, braid --check, --help, skills/survey/, skills/sweep-fix/)

**Choice**: discarded

**Rationale**: Sandbox artifact, not a defect: Bob runs static-only and cannot execute. Not queued (command shape: six commands on one line). Every named command ran green at this HEAD - last-verification.json records uv run pytest, validate_skill.py skills/create-skill and braid --check all exit 0 at a1b972ab (1100 passed, 0 failed), and Alice and Blake each independently executed --help, the no-argument case, skills/survey/ and skills/sweep-fix/ with the expected exits. Recorded in the settled-decisions ledger.

### [autonomous] 2026-09-07T01:08:58Z

**Decision**: mech-check: 1 touched test passes against the pre-change code: test_printed_validate_step_names_the_union_path

**Choice**: discarded

**Rationale**: Measurement artifact of an INCREMENTAL cycle: the replay base a1b972ab is cycle 1 HEAD, where init_skill.py union-path fix already landed, so a test-only refactor passes there by construction. Cycle 1 replay against the true pre-PRD base 35d6a6c reported 2 run / 2 failed / 0 passed, proving the tests pin the change. Recorded in the settled-decisions ledger.

### [autonomous] 2026-09-07T01:08:58Z

**Decision**: mech-check: 3 touched tests pass against the pre-change code: test_help_flag_prints_usage_and_exits_zero, test_short_help_flag_exits_zero_with_usage_line, test_missing_skill_path_argument_exits_two

**Choice**: discarded

**Rationale**: Same incremental-base artifact: a1b972ab already carries the argparse rewrite. Two of the three tests are cycle-1 findings closed on purpose (the -h alias and the skill_path stderr assert) - coverage backfill pinning behavior argparse already provided, which passes against its own base by definition. Recorded in the settled-decisions ledger.

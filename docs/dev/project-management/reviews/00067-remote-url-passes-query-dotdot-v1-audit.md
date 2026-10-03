# Decision Audit Log: 00067-remote-url-passes-query-dotdot-v1

PRD: `00067-remote-url-passes-query-dotdot-v1.md`
Started: 2026-09-26T19:06:28Z
Completed: 2026-09-26T19:06:28Z
Autonomous: 4  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-26T19:06:28Z

**Decision**: Both new tests define a bespoke inline fake_run closure that reimplements the shape make_fake_run already has, instead of extending make_fake_run with an optional remote-URL argument as the task description instructed (test_collect_repo.py:320, Alice, 1/4)

**Choice**: discarded with a verified reason - ledgered (supersedes an initial auto-fix classification made before the code was read)

**Rationale**: The prescribed fix would break the test it targets. make_fake_run raises RuntimeError(gh: not authenticated) on a gh call, and collect_repo catches RuntimeError at collect.py:433 and returns a skip stub, so a gh call made through that helper is swallowed rather than surfaced. The test asserts no gh call happened, which needs an uncaught AssertionError AND a call log; make_fake_run has neither, and it derives its remote from Path(cwd).name so it cannot return a hostile URL at all. Reusing it would require adding a call log plus an error-mode switch to a helper shared by four test modules, to serve one caller - more complexity, not less. The two closures are also not duplicates of each other: 4 lines asserting on repo_slug directly versus 7 lines asserting collect_repo made no gh call, with different error modes. A per-test fake_run closure is this module established convention, used by _run_answering_gh and three other existing tests, so the diff matches surrounding style as rules/coding-style.md requires. Alice herself marked the row a simplification rather than a defect and confirmed the acceptance criteria are met either way.

### [autonomous] 2026-09-26T19:06:28Z

**Decision**: Four accepted-URL parameter cases of test_remote_re_accepts_github_slugs_and_rejects_query_and_dotdot pass against the pre-change code and cannot fail-first (test_collect_repo.py:303, Bob + mech-check, 1/4; also Bob R2: fail)

**Choice**: discarded with a verified reason - ledgered

**Rationale**: Those four cases are regression guards the PRD explicitly mandates: the Must-have list requires git@github.com:demo/repo.git, https://github.com/demo/repo, https://github.com/demo/repo.git/ and https://github.com/demo/my.repo-2 to still parse to their owner and name. A guard for deliberately preserved behavior passes against base by design; that is not behavior left unpinned. The change itself IS pinned fail-first: the computed replay reports 5 of 9 touched tests failing against base, which are the four rejected shapes plus test_an_unparseable_remote_is_skipped_before_any_gh_call. Acting on this row would mean deleting coverage the PRD requires. Bob raised it himself as KNOWN/out-of-scope with the same justification, so his R2 fail is dispositioned rather than carried.

### [autonomous] 2026-09-26T19:06:28Z

**Decision**: The CHANGELOG entry says the capture groups admit only word characters, dots and hyphens, but the shipped class is ASCII-only [A-Za-z0-9_.-]; in Python str patterns word characters is Unicode-aware (CHANGELOG.md:77, Bob, 1/4)

**Choice**: auto-fix - swept into the [D1] Tail sweep task

**Rationale**: Low severity, any consensus, and the claim checks out: the entry was written while the regex still used [\w.-] and was not updated when commit a46a690 tightened it to the exact ASCII class per the per-task review. A user-visible CHANGELOG line that describes a wider character set than the code admits is a factual error in a released artifact, and the fix is one phrase.

### [autonomous] 2026-09-26T19:06:28Z

**Decision**: Cannot statically verify: run uv run pytest skills/brief-portfolio/scripts -q to confirm the suite reports zero failures and every existing remote-parsing test passes (N/A, Bob, 1/4)

**Choice**: discarded with a verified reason - ledgered

**Rationale**: The named check ran and passed four independent times at this exact HEAD a46a690: Alice reported 115 passed 0 failed, Blake reported 115 passed 0 failed, Carl ran the same command plus the full suite, validate_skill and braid --check, and the work phase recorded verification in dev/local/autopilot/last-verification.json at this sha with 3484 passed, 0 failed, 6 skipped and exit 0 on all three commands. This is codex read-only sandbox limitation reported as instructed by its persona, not an open question, so no check was queued and no task created.

# Decision Audit Log: 00053-split-oversized-brief-suites-v1

PRD: `00053-split-oversized-brief-suites-v1.md`
Started: 2026-09-21T03:05:56Z
Completed: 2026-09-21T03:05:56Z
Autonomous: 9  |  Deferred: 2  |  Doubts: 0

### [autonomous] 2026-09-21T03:05:56Z

**Decision**: PRD 00053 design: split smoke.test.js into 6 concern-named files (harness/brief/repos/work/todos/todos.status) and test_collect.py into 4 (repo/local/history/pipeline, renamed from ci - no collect_ci coverage exists) plus shared helper modules

**Choice**: auto-fix

**Rationale**: review dispatch 1 (claude) found and fixed 1 blocker (mis-scoped stubClipboard claim); dispatch 2 (codex outage, claude-fallback) found 0 cardinal-sin/blocker; 6 non-blockers + 2 questions logged unresolved in the design doc Review log (helper-move scope inconsistency, a reuse-precedent file-count citation, file-header comment destination, cross-reference rewrite scope for PRD Module/Depends-on lines vs acceptance lines)

### [autonomous] 2026-09-21T03:05:56Z

**Decision**: F1 collect_test_helpers.py docstring is copy-pasted from skills/distil-memory/scripts/docket_test_helpers.py and cites a funnel family / funnel_test_helpers.py that do not exist in brief-portfolio (collect_test_helpers.py:6)

**Choice**: auto-fix

**Rationale**: cycle 1: Medium, clear mechanical docstring fix, 1/4 consensus (also raised by the shadow workflow's quality lane); swept into the [D1] Tail sweep task

### [autonomous] 2026-09-21T03:05:56Z

**Decision**: F2+F3 the suite-wide jsdom header from smoke.test.js survives only atop smoke.repos.test.js; its first paragraph describes every smoke.*.test.js and belongs on smoke.harness.js, and the each_key_duplicate note motivates tests in smoke.brief.test.js and smoke.work.test.js too

**Choice**: auto-fix

**Rationale**: cycle 1: Low, comments outside test bodies (the byte-identical constraint binds bodies only); Alice and Bob raised the two halves; swept into the [D1] Tail sweep task

### [autonomous] 2026-09-21T03:05:56Z

**Decision**: F4 test_collect_pipeline.py module docstring omits the two strict agoge xfails it hosts, one of which (test_a_capped_commit_list_still_carries_the_true_commit_count) exercises collect_repo, not main()

**Choice**: auto-fix

**Rationale**: cycle 1: Low, one-clause docstring addition; the shadow workflow's MEDIUM quality note names the same docstring and the same smallest fix; swept into the [D1] Tail sweep task

### [autonomous] 2026-09-21T03:05:56Z

**Decision**: F8 Cannot statically verify: the recorded pytest line omits the xfailed count, so the must-have 'same xfail set' has no recorded evidence

**Choice**: routed to verification

**Rationale**: cycle 1: queued `uv run pytest skills/brief-portfolio/scripts -q` in 00053-split-oversized-brief-suites-v1-checks-1.json (source bob); runs in the sweep's work-phase step 7; Alice and Blake already observed 64 passed / 4 xfailed at HEAD 2fd6389, matching the baseline

### [autonomous] 2026-09-21T03:05:56Z

**Decision**: F7 Cannot statically verify: post-split body hashes equal the baseline (no after-inventory artifact recorded)

**Choice**: discard

**Rationale**: cycle 1: verified this cycle by Alice and Blake, who each re-ran dev/local/tmp/00053-verify-after.py (63/63 Python names equal, 0 hash mismatches) and 00053-verify-task4.mjs (43/43 JS, MULTISET MATCH); the shadow rubric lane confirmed 35 JS callbacks + 63 Python bodies hash-identical to base 94c7aa5

### [autonomous] 2026-09-21T03:05:56Z

**Decision**: F9 write_report and make_git_repo have one consuming module each yet sit in the shared collect_test_helpers.py while the JS side kept single-file helpers local

**Choice**: discard

**Rationale**: cycle 1: settled at design time - task 3's contract names all 8 helpers and the design Review log recorded this scope inconsistency as a non-blocker; Bob himself filed it KNOWN; moving them back contradicts the reviewed contract for no behavioral gain

### [autonomous] 2026-09-21T03:05:56Z

**Decision**: F10 node --test now runs the real-time sleep/timeout tests alongside five other jsdom-mounting files instead of one; recorded run was green

**Choice**: discard

**Rationale**: cycle 1: no defect observed - four independent green npm test runs at HEAD this cycle (work phase, Alice, Blake, Carl); node --test already ran three files in parallel before the split; PRD 00069 removes the real-time sleeps; the five-run VERIFY is not a single queueable command

### [autonomous] 2026-09-21T03:05:56Z

**Decision**: F11 three moved JS test callbacks exceed 50 lines (smoke.todos.status.test.js:204 ~90, :139 ~64, smoke.todos.test.js:68 ~53)

**Choice**: discard

**Rationale**: cycle 1: pre-existing and moved byte-identically as the PRD mandates (no reformatting, no rewording); the 90-line one is the exact test PRD 00069 shortens; Bob filed it KNOWN

### [deferred] 2026-09-21T03:05:56Z

**Decision**: F5 stale cross-reference '(comparable to the existing 1.6s real-wait test above)' at smoke.todos.status.test.js:211 now points at a test that lives in smoke.todos.test.js

**Choice**: defer

**Rationale**: cycle 1: the comment sits inside a test body the PRD requires byte-identical (inventoried hash); PRD 00069 rewrites that exact test and should reword the comment then; also raised by three shadow-workflow lanes

### [deferred] 2026-09-21T03:05:56Z

**Decision**: F6 smoke.a11y.test.js:71 comment 'same fixup the Todos-tab tests in smoke.test.js use' names the file this PRD deleted; the fixup now lives in smoke.todos.test.js

**Choice**: defer

**Rationale**: cycle 1: the line sits inside an inventoried a11y test body and the design lists smoke.a11y.test.js Untouched, so editing it here breaks this PRD's own equivalence check; a one-line follow-up commit after 00053 closes, or PRD 00058/00066 which touch the app, should reword it to smoke.todos.test.js; also raised by three shadow-workflow lanes

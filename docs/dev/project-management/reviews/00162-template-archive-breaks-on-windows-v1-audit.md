# Decision Audit Log: 00162-template-archive-breaks-on-windows-v1

PRD: `00162-template-archive-breaks-on-windows-v1.md`
Started: 2026-11-08T22:17:12Z
Completed: 2026-11-08T22:17:12Z
Autonomous: 13  |  Deferred: 10  |  Doubts: 0

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: Design approach for 00162 Windows archive fixes (git update-index --chmod for executable bits, two-pass typed symlinks via _land chain resolution, onexc read-only-aware rmtree retry, test-only extended-prefix helper)

**Choice**: auto-approved after 2 blockers fixed across 3 review dispatches

**Rationale**: chain-landing computation contradiction and on-disk-separator-form contradiction both fixed before dispatch 3 verified clean; codex unavailable both mandatory dispatches (sandbox denied file reads), Claude fallback used

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: Cleanup failure replaces the original build exception. **FIX**: preserve the original as the raised exception, with cleanup failure chained.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: Unbounded path argv exceeds the Windows process limit. **FIX**: send NUL-delimited paths through stdin, preserving one call per mode group.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: New cleanup tests accept either exception order and broad exception classes. **FIX with R1**: assert original-error identity and separately assert the cleanup cause. Absorbs mechanical flags at lines 408 and 433.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: Link test module grew to 933 lines. **FIX**: extract the new typing tests with shared fixtures retained.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: Twin cleanup test does not enforce the PRD's exception order. **DISCARD duplicate of R3**, not a separate unresolved HIGH.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: Locale-decoded tracked names can mismatch archive Unicode names and silently skip chmod. **FIX**: use byte output with explicit UTF-8/surrogateescape decoding; CP1252 probe reproduced the lost bit.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: Manual extraction calls getmembers again despite an existing members list. **FIX adjacent to rework**; downgraded from MEDIUM because getmembers is cached and this is redundancy, not a runtime defect.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: Host-native link text containing backslashes is rejected by containment readers. **FIX** the host-read/archive-input boundary with regression coverage; preserve hostile archive-input refusal.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: R5 twin cleanup test (HIGH, single voice) and opus tier for D1 rework

**Choice**: R5 classified fix inside the R3 task instead of discard; D1 tasks at opus; repair contracts from review 01 copied into task bodies

**Rationale**: cycle 1: a HIGH is never single-voiced away; R1/R19 sit on the security-containment path that floored every original task at opus

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: `_set_index_modes` hand-rolls a third `subprocess.run(["git","-C",...])` spelling instead of giving `_git_bytes` an `input=` parameter, only because the `_serve_archive` fake takes no keywords. **FIX** (sweep): add `input=` to `_git_bytes`, widen the fakes to `**kwargs`, call it from `_set_index_modes`. Behavior-preserving.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: The read side uses `_HOST_SEP` but the write side in `_lay_links_typed` and `_copytree_links_typed` uses `os.sep`; two names for one concept and nothing says the simulation depends on that. **FIX** (sweep): extend the `_HOST_SEP` comment to say it governs reading only and the write side keeps `os.sep`.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-11-08T22:17:12Z

**Decision**: Native Windows behavior of host-link fixtures, literal-backslash case and clone round trip is inferred, not run (review 02 R4)

**Choice**: routed to verification

**Rationale**: Cycle 2: hosted windows job on the exact combined candidate, uv run pytest skills/use-qwen/scripts/test_eval_tree_archive*.py test_eval_tree_links*.py test_eval_tree_host_links.py test_eval_tree_state.py -W error::DeprecationWarning; macOS pytest cannot close it

### [deferred] 2026-11-08T22:17:12Z

**Decision**: Cleanup does not repair POSIX read-only parent directories. **DEFER hardening**: normal extraction/git staging does not create such directories; clarify any broader task prose when repairing R1.

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-11-08T22:17:12Z

**Decision**: Cleanup retries every rmtree error with chmod, including unrelated failures. **DEFER hardening**; R1 must preserve the original exception for these failures too.

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-11-08T22:17:12Z

**Decision**: Two cleanup-test names are awkward. **DEFER cosmetic naming**; improve while changing those tests if useful.

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-11-08T22:17:12Z

**Decision**: Internal helper names/signatures differ across PRD, design and code. **DEFER documentation reconciliation**; exported signatures are unchanged and the implementation decision is recorded.

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-11-08T22:17:12Z

**Decision**: Ignored archive members are excluded from the chmod groups. **DEFER inherited seal-contract gap**: git add -A already omitted such members before this lane; preserve the guard against chmod on untracked paths until that contract is resolved.

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-11-08T22:17:12Z

**Decision**: Prefix helper is imported inside a test to avoid a circular import. **DEFER test organization**; no incorrect result demonstrated.

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-11-08T22:17:12Z

**Decision**: Existing staging test hedges with reached-is-None-or-reached; older exception alternatives also remain. **DEFER inherited test hardening**: line 266 predates this lane. This retains the first mechanical tautology flag.

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-11-08T22:17:12Z

**Decision**: Generic rmtree callback assumes a single-argument callable and may mishandle open/scandir errors. **DEFER with R8**: unreadable directories are outside normal staging construction.

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-11-08T22:17:12Z

**Decision**: Links retain archive order instead of target-first order. **DEFER specification reconciliation**: explicit type from full-chain landing supplies the required Windows type without depending on creation order.

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-11-08T22:17:12Z

**Decision**: The two never-lifts cleanup tests assert only `isinstance(cleanup, PermissionError)`, so an unrelated `PermissionError` would pass. Task 10's contract asked for the exact type and the injected object or message. **DEFER (verified, single-voice)**: confirmed at lines 435 and 464; the injector raises `PermissionError(errno.EACCES, "read-only file refused deletion", path)`, so `type(cleanup) is PermissionError` plus `cleanup.strerror` would close it. The PRD rule (keep the original as the raised error) is met and pinned by identity. The installed gate refuses a single-voice task, so this is carried to batch end as a test-strength follow-up. Alice's "exact `PermissionError` context" claim is refuted by the code.

**Choice**: deferred

**Rationale**: deferred by review-close

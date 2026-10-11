# Decision Audit Log: 00073-sweep-loud-failures-v1

PRD: `00073-sweep-loud-failures-v1.md`
Started: 2026-10-11T09:32:30Z
Completed: 2026-10-11T09:32:30Z
Autonomous: 11  |  Deferred: 2  |  Doubts: 0

### [autonomous] 2026-10-11T09:32:30Z

**Decision**: 00073 design approach

**Choice**: hoist resolver in main, verify_control raises, _git_root walk-up, registry guard, _yaml_quote = json.dumps(ensure_ascii=False) + isprintable escape, default report suffix loop

**Rationale**: deviates from PRD ensure_ascii=True because astral chars would not round-trip; 10 non-blockers + 3 questions left in the design Review log; codex dispatch 2 fell back to Claude (codex sandbox failure)

### [autonomous] 2026-10-11T09:32:30Z

**Decision**: `enumerate_repos` uses `Path(cwd).absolute()`, which does not normalise `..`. For `--cwd ../repo/sub`, `_git_root` walks the textual parents (`/x/y/../repo`, `/x/y/..`, `/x/y`, ...), not the real ancestors. It can return a non-normalised root like `/x/y/../repo` that never equals the registry row `/x/repo`. The repo is then scanned twice and may show as a registry gap, which is the bug this task fixes, and it can also pick up a `.git` from a lexical parent that is not a real ancestor. Replace with `Path(os.path.abspath(cwd))`, which normalises `..` without following symlinks, and add a `..` cwd test.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-11T09:32:30Z

**Decision**: The shapes block flags `assert escaping_out in message or str(target) in message` as an either-or hedge. It is pre-existing (blame 2026-08-29), not introduced by this diff, but the file is touched here. Pin one outcome.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-11T09:32:30Z

**Decision**: `resolve_ast_grep` can still raise something other than `RuntimeError` (sweep.py:69-74). `subprocess.run(["mise", "which", ...], timeout=30)` can raise `TimeoutExpired`, and an OSError is possible too. Neither is caught by main's `except RuntimeError` (sweep.py:566), so this setup failure ends in a traceback instead of a one-line exit 1. Narrow, but the PRD's goal is that every setup failure takes the diagnostic path.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-11T09:32:30Z

**Decision**: Mechanical check flags an existing either-or assertion in `test_render_report_how_to_proceed_states_fixes_apply_only_in_invoking_repo`. Assert the required invoking-repo restriction directly.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-11T09:32:30Z

**Decision**: The awkward-scalar and broad-corpus tests duplicate the same rendering, parsing, and four assertions. Combine their parameter sets into one round-trip test, retaining descriptive case IDs and all values.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-11T09:32:30Z

**Decision**: `skills/sweep-fix/SKILL.md` step 2 describes `main()` but does not say that an unusable scan tool, registry or control repo now exits 1 with one stderr line and no report. The caller now has a new failure mode to handle. Add one sentence.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-11T09:32:30Z

**Decision**: `registry.open()` on an unreadable file raises `PermissionError`, which is not a `RuntimeError`, so it escapes `main` as a traceback. A registry that is a directory reads as "registry not found". The PRD only requires the missing case, so this is a gap in the same bug class (setup faults that surface as tracebacks), not a defect in the delivered scope. Consider catching `OSError` at the open and re-raising it as `RuntimeError`.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-11T09:32:30Z

**Decision**: The registry guard is only `is_file()` (sweep.py:152). An unreadable registry (PermissionError) or a non-UTF-8 registry (UnicodeDecodeError) still gives a raw traceback at `registry.open()` (sweep.py:155). The PRD only required the missing-file case.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-11T09:32:30Z

**Decision**: R3/R12/R13/R14/R15: _yaml_quote deviation, seventh test file, replay rows (tests passing at base)

**Choice**: no action; settled in ledger

**Rationale**: cycle 1: each is deliberate and documented (design deviation for astral round-trip; size-driven test split; guards and refactor-equivalence pins that pass at base by design)

### [autonomous] 2026-10-11T09:32:30Z

**Decision**: Tail sweep: R1, R2, R4, R5, R6, R7, R8, R9

**Choice**: swept as 4 tasks (5-8) at sonnet

**Rationale**: cycle 1 converged (0 C/H, constraint gate exit 0); actionable medium/low tail is fixed, not dropped

### [deferred] 2026-10-11T09:32:30Z

**Decision**: The default-report collision check is check-then-act. `exists()` runs in `_resolve_report_path` (sweep.py:524) and the later `write_text` (sweep.py:579) overwrites unconditionally. Two concurrent same-reason sweeps could still clobber each other. This is not the sequential case the PRD requires.

**Rationale**: deferred by review-close

### [deferred] 2026-10-11T09:32:30Z

**Decision**: When a sweep runs from a subdirectory, the repo scan covers the whole repo, but the default report path is still built under the resolved `--cwd` subdirectory, not the git root (sweep.py:557-558). The PRD does not specify this, so it is flagged, not failed. cwd walk-up also uses `.absolute()` while main passes the unresolved `args.cwd`, so a symlinked cwd (for example /tmp versus /private/tmp) may not dedupe against a registered real path.

**Rationale**: deferred by review-close

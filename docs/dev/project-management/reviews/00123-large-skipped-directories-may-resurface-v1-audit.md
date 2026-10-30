# Decision Audit Log: 00123-large-skipped-directories-may-resurface-v1

PRD: `00123-large-skipped-directories-may-resurface-v1.md`
Started: 2026-10-29T23:21:08Z
Completed: 2026-10-29T23:21:08Z
Autonomous: 6  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-10-29T23:21:08Z

**Decision**: Design-solution for PRD 00123: describe() never produces a sha256 fingerprint for directories over MAX_DIR_FILES, so a skip/machine ledger decision on such a directory always compares None vs. its recorded sha256 and resurfaces forever once the directory crosses the cap.

**Choice**: Chose a count+latest-mtime fallback fingerprint (count_mtime) computed from the already-walked uncapped files list, stored on the candidate dict and accepted by load_ledgers as an alternative to sha256 on volatile entries; cmd_scan compares whichever field is present. Rejected copying the prior sha256 forward (fabricates a match) and rejected hashing a bounded sample (still pays the cost MAX_DIR_FILES exists to avoid). 3 reviewer dispatches (claude, codex weak, codex); all blockers fixed, one non-blocker accepted as written, one question resolved in the doc.

**Rationale**: Smallest-diff fix that keeps resurfacing live on real metadata change and on the existing 180-day expiry, matches the PRD mandate not to fabricate a content hash, and needs no ledger-format migration.

### [autonomous] 2026-10-29T23:21:08Z

**Decision**: Phase 0 test is 54 lines (mechanical facts: line 383), over the 50-line limit. Most of that is a 20-line docstring that now describes pre-fix behavior. Cut the docstring to a short statement of the flow and outcome, or move the re-record step into a helper.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-29T23:21:08Z

**Decision**: SKILL.md still documents only `sha256` in two places. The schema line is `{path, verdict, decided, sha256?, note?}` and the verdict table says skip "Comes back when sha256 changes". The PRD requires documented volatile-entry requirements to be updated alongside validation. Add `count_mtime?` to the schema line and "or count_mtime" to the skip/machine rows.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-29T23:21:08Z

**Decision**: The new `f.stat()` over every file in an over-cap directory is unguarded. A file that vanishes between `rglob` and `stat` raises FileNotFoundError out of `describe`, while `prescreen` catches OSError. The small-directory `elif` branch already has the same pre-existing exposure, so this is consistent with the current code. Consider guarding both.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-29T23:21:08Z

**Decision**: Cycle 1 converged with no CRITICAL/HIGH; 12 consolidated findings, all medium/low

**Choice**: converged and swept 3 multi-voice medium/low findings (R1, R2, R3) into tail-sweep tasks 3, 4, 5; ledgered the six single-voice rows and the three non-defect rows

**Rationale**: Phase 5 convergence test is no unresolved CRITICAL/HIGH; the doubt-roster constraint gate exited 0. Medium/Low never block convergence, so the tail sweep is the path. review-close enforces the single-voice exclusion deterministically (it refused R4 with tail_sweep_single_voice), so every [1/3] row was ledgered instead of swept.

### [autonomous] 2026-10-29T23:21:08Z

**Decision**: Carl (gemini) produced no review this cycle

**Choice**: recorded Carl unavailable after one retry; continued with Alice, Blake and Bob (graceful degradation)

**Rationale**: gemini-run exit 1 on both dispatches, backend copilot, stderr 'You have exceeded your monthly quota'. Exit 1 is a one-off runtime failure, not the exit-4 permanent-configuration case, so Carl was NOT latched into batch.unavailable_reviewers and a later batch will try him again.

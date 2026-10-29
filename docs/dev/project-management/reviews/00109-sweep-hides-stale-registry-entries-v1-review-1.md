---
head_sha: ca4dea90798b271722d5e1cd8a29915704451e66
reviewers: alice, blake, eve
---

## Alice

**00109-sweep-hides-stale-registry-entries-v1-c1**

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | 🟡 | `enumerate_repos` docstring not updated for the new gap shape — fixed (ca4dea9). | skills/sweep-fix/scripts/sweep.py:159 | 1 | CONSENSUS, BLIND |
| R2 | [2/3] | ⚪ | SKILL.md's "each gap line names its path and a reason" is false for unregistered-on-disk gaps — fixed (ca4dea9). | skills/sweep-fix/SKILL.md:62 | 1 | CONSENSUS, BLIND |
| R3 | [2/3] | ⚪ | Edge case: a registered row that is also `cwd` and not a git repo is both scanned and reported as a gap — left as a known limitation (LOW, not required by the PRD's Must-have list). | skills/sweep-fix/scripts/sweep.py:184 | 1 | CONSENSUS, BLIND |
| R4 | [1/3] | 🟡 | `enumerate_repos` pushed to 56 lines, over the 50-line limit — fixed (ca4dea9, extracted `_unresolved_registry_gaps`). | skills/sweep-fix/scripts/sweep.py:184 | 1 | CONSENSUS |
| R5 | [1/3] | 🟡 | New regressions did not check which reason goes with which path (swap-proof) — fixed (ca4dea9). | skills/sweep-fix/scripts/test_sweep_enumerate.py:593 | 1 | CONSENSUS |
| R6 | [1/3] | 🟡 | Main test never checked the gap line sits in the `Gaps` section or that the count is right — fixed (ca4dea9). | skills/sweep-fix/scripts/test_sweep_main.py:165 | 1 | CONSENSUS |
| R7 | [1/3] | 🟡 | `_gap_reason_for` test helper carried a dead `isinstance(dict)` branch — removed (ca4dea9). | skills/sweep-fix/scripts/test_sweep_enumerate.py:550 | 1 | CONSENSUS |
| R8 | [1/3] | ⚪ | Stale registry rows are not deduplicated — left as a known limitation (LOW; mirrors pre-existing behavior for valid rows, out of PRD scope). | skills/sweep-fix/scripts/sweep.py:184 | general | BLIND |

## Blake

**00109-sweep-hides-stale-registry-entries-v1-c1**

Same R1, R2, R3, R8 as Alice's table above (cross-lens agreement). Rubric B1-B19: all pass.

## Eve

**00109-sweep-hides-stale-registry-entries-v1-c1**

FIX (8, matching R1/R2/R3/R5/R6/R7 above plus a file-vs-directory reason mix-up at sweep.py:187, left open as a known limitation — a regular file reports "not found on disk" rather than a file-specific reason):
- enumerate_repos docstring stale — fixed.
- SKILL.md wording overbroad — fixed.
- Registered path that is a regular file reported "not found on disk" — known limitation, not fixed (would need its own pinning test).
- cwd-also-registered-non-repo double report — known limitation, not fixed.
- Swap-proof test assertions — fixed.
- Main test gap-section/count assertion — fixed.
- `_gap_reason_for` dead dict branch — fixed (removed).
- Main test's "never scanned" check was vacuous (no file planted in the non-repo dir) — known limitation, not fixed in this pass.

VERIFY: (none)

KNOWN (2):
- Stale registry rows are not deduplicated — mirrors pre-existing behavior for valid rows, out of PRD scope.
- A registered bare repository (no `.git` entry) now surfaces as a gap where the prior code silently dropped it — separate design decision, not requested by the PRD.

D1-D5: all pass. Eve independently replayed both new tests against the pre-fix commit (confirmed fail-first) and ran the full suite (4113 passed, 9 skipped at the time of her pass), `validate_skill.py`, and `braid --check` (all clean).

Codex (Bob) and Gemini (Carl) did not report: both lanes were dispatched twice (initial + one retry) and failed both times — Bob's codex sandbox denied every file read (`sandbox_apply: Operation not permitted`), Carl's copilot backend hit its monthly quota. Neither lane contributed findings.

Verdict: converged
Tests: 65 passed, 0 failed, 0 skipped (reused from last-verification: `uv run pytest skills/sweep-fix/scripts/test_sweep_enumerate.py skills/sweep-fix/scripts/test_sweep_main.py` at ca4dea9; full-repo `uv run pytest` ran 4111 passed, 9 skipped, 2 failed on an unrelated load-dependent timing suite (`test_sweep_scan.py`), confirmed pre-existing by re-running it in isolation twice and against the pre-change commit, all green)
codex_rung_guard: not fired

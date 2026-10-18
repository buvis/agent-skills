---
head_sha: 10fb3a916582a7282ed57a10d614ae410b09d70f
reviewers: alice, blake, eve, carl
---

## Alice

**00087-ground-prd-root-and-relative-exclusion-v1-c1**
| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/4] | 🟡 | `main()` exceeds the 50-line limit (53 lines; the 3 inserted root-check lines account for the overage). Behavior-preserving fix: extract the path-collection/readability loop into `collect_prd_files()`. | skills/create-prd/scripts/ground_prd.py:337 | 1 | CONSENSUS, GEMINI |
| R2 | [2/4] | ⚪ | test_ground_prd.py is 997 lines, over the 800-line limit (pre-existing: was ~954 before this diff). | skills/create-prd/scripts/test_ground_prd.py:653 | general | CONSENSUS, GEMINI |
| R3 | [1/4] | ⚪ | `_rg_hit`/`known_packages` lru_cache keyed on raw `root` Path is cwd-dependent; latent test-isolation risk, not a production defect. | skills/create-prd/scripts/ground_prd.py:137 | 2 | CONSENSUS |

Verified the diff matches the PRD's prescribed code line-for-line; ran a fail-first replay of the pre-change code confirming all 4 PRD-named tests fail there. Full `uv run pytest`: 3946 passed, 9 skipped. R1–R11 pass, R12/R13 fail (size limits).

## Blake

**00087-ground-prd-root-and-relative-exclusion-v1-c1**
No blocking findings; implementation matches spec exactly (commits aae1e6c, b6fdefb).
| Ref | Severity | Issue | File |
|-----|----------|-------|------|
| R4 | ⚪ | lru_cache keyed on root Path risks a stale hit across relative-root tests | skills/create-prd/scripts/test_ground_prd.py:832 |
| R5 | ⚪ | Cargo.lock-unreadable test's chmod 000 is a no-op under root-run CI; accepted by design (PRD forbids `os.geteuid`) | skills/create-prd/scripts/test_ground_prd.py:666 |

All 19 blind rubric rules (B1–B19) pass.

## Eve

**00087-ground-prd-root-and-relative-exclusion-v1-c1**
Confirmed fail-first replay (4 failed pre-change, 64 passed) and full suite green (3946 passed, 9 skipped).

FIX:
- CHANGELOG entry for the `fix` commit — reviewed and declined: the card's frontmatter explicitly sets `changelog: none` (internal dev-tooling fix, not user-facing); trusting the card's own classification.
- Hold stubs 00089/00090 re-minted the same two defects this PRD fixes — applied: deleted both stubs and added ledger keys bac71612d738 and 6b0e4ec95f8f to the PRD Source line (commit 10fb3a9).
- `test_cli_exits_two_when_cargo_lock_is_unreadable` only asserts the generic `ground_prd:` prefix, not that the OSError path specifically fired — deferred, out of this card's scope.

KNOWN: capsys/traceback assertion limitation, root-CI chmod no-op, pre-existing lru_cache design — all accepted with justification.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

**00087-ground-prd-root-and-relative-exclusion-v1-c1**
Reported successfully, consistent with Alice: `main()` 53 lines (R1 duplicate) and test file 997 lines (R2 duplicate). R12/R13 fail, all else pass.

Verdict: converged
Tests: 3946 passed, 0 failed, 9 skipped (fast-track batch suite)
codex_rung_guard: not fired

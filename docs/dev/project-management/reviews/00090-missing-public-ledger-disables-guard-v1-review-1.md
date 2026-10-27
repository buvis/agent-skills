---
head_sha: 1fd407b68f5dfad70e64c103e28e303e036ca2a5
reviewers: alice, blake, eve
---

## Alice

**00090-missing-public-ledger-disables-guard-v1-c1**
| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | 🟡 | The unmerged branch `agoge/authored-tests-2026-10-26` has a second strict-xfail glean test (non-ASCII path) that calls `run_cli(home, ledger)` with two arguments. The new `run_cli` needs a `command` argument. A later merge of that branch must update the call, or that test fails with a TypeError, which strict xfail still counts as an expected failure. That would hide the regression. The finding-1 xfail test on that branch was correctly turned into a normal regression test here | skills/glean/scripts/test_glean.py:214 | general | CONSENSUS, BLIND |
| R2 | [2/3] | ⚪ | `public_path.exists()` accepts a directory. A `public_ledger` that points at a directory then reaches `read_text`, which raises IsADirectoryError with a traceback. `is_file()` would close this edge, and its error message would still name the path | skills/glean/scripts/glean.py:72 | 1 | CONSENSUS, BLIND |
| R3 | [1/3] | 🟡 | Dead hedge assertion. `assert not (r.returncode == 0 and json.loads(r.stdout or "{}").get("ok"))` is always true once line 257 has asserted `r.returncode != 0`, so it can never fail. Delete it, or replace it with a direct check that stdout is empty or reports no `"ok": true` | skills/glean/scripts/test_glean.py:261 | 1 | CONSENSUS |
| R4 | [1/3] | ⚪ | The near-miss test runs the same code path as the missing-ledger test: a configured path that does not exist. Having `public.json` present nearby changes nothing in `load_ledgers`. It adds no coverage. Merge it into the missing-ledger test or drop it | skills/glean/scripts/test_glean.py:264 | 1 | CONSENSUS |
| R5 | [1/3] | ⚪ | The missing-local-ledger control test checks only the path in stderr. The PRD says the first-run guidance must stay. Also assert "First run" or "no config", so a later change to `load_ledgers` cannot drop the guidance without a test failing | skills/glean/scripts/test_glean.py:292 | 1 | CONSENSUS |

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: pass

## Blake

**00090-missing-public-ledger-disables-guard-v1-c1**
Verdict: the fix is correct and the spec is met. No Critical or High issues.

| Ref | Severity | Issue | File | Task |
|-----|----------|-------|------|------|
| R6 | ⚪ | The check is "exists, then read", so it has a race. If the file is deleted between `exists()` at glean.py:72 and the read, `load_json` still catches `FileNotFoundError` (glean.py:55), returns `{}`, and the ledger fails open as empty. The tight fix is a `required` flag on `load_json` that exits on `FileNotFoundError`, with no separate `exists()` call. | skills/glean/scripts/glean.py:72 | general |
| R7 | ⚪ | A missing local ledger gives "no config in <path>. First run: ..." (glean.py:66), not "does not exist". It names the path and exits non-zero, so it is acceptable, but the wording does not say the file is missing. | skills/glean/scripts/glean.py:66 | general |

Also flagged (duplicates of Alice's R1 and R2 above, merged by consensus scoring): the unmerged-branch xfail collision risk, and `exists()` accepting a directory.

B1-B13: pass. B14: fail (exists-then-read TOCTOU race at glean.py:72). B15-B19: pass.

## Eve

**00090-missing-public-ledger-disables-guard-v1-c1**
FIX:
- Card said "if present, convert that test to a normal regression"; the branch test is present locally but was not converted, so merging agoge/authored-tests-2026-10-26 later lands a strict xfail that now XPASSes and fails the suite — skills/glean/scripts/test_glean.py:251 — replace `test_check_staged_refuses_harmless_file_when_public_ledger_is_missing` with the branch's `test_check_staged_refuses_when_public_ledger_is_missing` body (xfail marker dropped, keep the stderr/no-traceback asserts), so the merge collides on the same test instead of adding a second copy.
- Dead assertion: `assert not (r.returncode == 0 and ...)` is tautologically true after `assert r.returncode != 0` four lines above — skills/glean/scripts/test_glean.py:261 — delete lines 260-261.
- Redundant test: the "near miss" case exercises the identical code path as the missing case (code has no prefix/fuzzy logic; `exists()` is the only check) and the `public.json` it writes is never read — skills/glean/scripts/test_glean.py:264-274 — delete it (or parametrize the missing test over the two paths if the typo wording matters).
- Speculative parameter: `write_ledger_with_public(..., entries=None)` has no caller passing `entries`; it also duplicates `write_ledger` at line 46 — skills/glean/scripts/test_glean.py:221 — drop the `entries` parameter (write `"entries": []`), or add an optional `public_ledger` kwarg to the existing `write_ledger` and delete the new helper.
- `exists()` lets a directory through to `read_text()`, giving a traceback instead of the path-specific diagnostic the card requires — skills/glean/scripts/glean.py:72 — change `public_path.exists()` to `public_path.is_file()` and widen the message to "is not a file".

VERIFY:
- (none)

KNOWN:
- An existing but unreadable ledger (PermissionError) still tracebacks for both local and public ledgers — pre-existing `load_json` behavior; the card scopes "missing", not "unreadable".
- `"public_ledger": ""` is treated as omitted (`cfg.get` falsy) rather than as a bad path — pre-existing branch condition untouched by this diff; the card's "omitted setting" case means key absent.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

Codex (Bob) and gemini (Carl) both reported nothing: codex's sandbox blocked its own Fact-Forcing Gate hook on every read (`sandbox_apply: Operation not permitted`) on both the initial run and the one retry; gemini's copilot backend (`gemini-3.8-flash`) reported monthly quota exceeded on both the initial run and the one retry. Both lanes are recorded as failed in the ledger (`fast-track:bob`, `fast-track:carl`).

Verdict: converged
Tests: 3963 passed, 9 skipped, 0 failed (fast-track batch suite)
codex_rung_guard: not fired

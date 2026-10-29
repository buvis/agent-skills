---
head_sha: 381f4540b95ac0fbf1d7d3423c656ca80620b9a5
reviewers: alice, blake, eve, bob, carl
---

## Alice

**00107-meeting-tools-crash-malformed-input-v1-c1**

[ALICE] 🟡 The transcript check only tests that the `turns` key exists and never checks the value's type. `{"turns": null}` exits 0 and writes a broken debrief.html; `{"turns":"abc"}` plus a correction crashes with a TypeError traceback. The same unchecked consumption hits `warnings` and `corrections` when they are strings. | File: skills/debrief-meeting/scripts/build.py:126 | Task: 1
[ALICE] ⚪ `read_source` catches only `BadZipFile` and `KeyError`; a damaged deflate stream raises `zlib.error`, other compression methods raise `NotImplementedError`. Outside the reported cases, same "corrupt DOCX" class. | File: skills/debrief-meeting/scripts/parse.py:52 | Task: 1
[ALICE] 🟠 RESOLVED: correction entries were checked only for being dicts; `from`/`to` values were not type-checked, crashing with uncaught TypeErrors. Victor-confirmed, fixed in rework commit 381f454, resolution verified by Eve's delta review via fail-first replay against the pre-rework code. | File: skills/debrief-meeting/scripts/build.py:132 | Task: 1
[ALICE] 🟡 The task requires a file-specific diagnostic for every malformed input. Only the truncated-transcript test asserts the file name is in the message; the others never check the path. | File: skills/debrief-meeting/scripts/test_debrief_build.py | Task: 1

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: fail
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: pass

## Blake

**00107-meeting-tools-crash-malformed-input-v1-c1**

[BLAKE] 🟡 Correction entries are checked only for being dicts; the "from" and "to" types from the SKILL.md schema are not checked, so a non-string "from" or "to" still crashes with a traceback. | File: skills/debrief-meeting/scripts/build.py | Task: 00107-c1 — RESOLVED by rework commit 381f454.
[BLAKE] 🟡 The transcript shape check only tests that the 'turns' key exists; turns as a non-list, or corrections/warnings as non-lists, still crash with a traceback. | File: skills/debrief-meeting/scripts/build.py | Task: 00107-c1
[BLAKE] ⚪ Non-UTF-8 transcript.json or extract.json raises an uncaught UnicodeDecodeError, because only JSONDecodeError is caught. | File: skills/debrief-meeting/scripts/build.py | Task: 00107-c1
[BLAKE] ⚪ The parse.py DOCX handler catches only BadZipFile and KeyError; RuntimeError, NotImplementedError, zlib.error and OSError would still give a traceback. | File: skills/debrief-meeting/scripts/parse.py | Task: 00107-c1
[BLAKE] ⚪ The build malformed-input tests call main() in-process and assert only that excinfo.value.code is truthy, not that the CLI exits 1; the "Traceback" not-in-message check cannot fail in-process. | File: skills/debrief-meeting/scripts/test_debrief_build.py | Task: 00107-c1
[BLAKE] ⚪ A non-dict transcript root (for example a JSON list) gets the misleading message "is missing a 'turns' key". | File: skills/debrief-meeting/scripts/build.py | Task: 00107-c1

B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: fail
B11: pass
B12: pass
B13: pass
B14: pass
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass

## Eve

**00107-meeting-tools-crash-malformed-input-v1-c1** (round 1, full diff 111ba9a..832d2a9)

FIX:
- Correction entries with wrong field types still traceback (`from: 123`, `to: 5`) — RESOLVED by rework commit 381f454.
- Falsy non-list `corrections` (`""`, `false`, `0`) silently coerced to "no corrections" — still open, see delta R-series below.
- Non-object transcript root reports a misleading "is missing a 'turns' key" message — still open.
- Five of six new build.py tests do not assert the file name in the diagnostic — still open.
- Vacuous assertions in the new tests (`"Traceback" not in message`, bare `excinfo.value.code`) — still open.

VERIFY:
- (none)

KNOWN:
- `transcript["turns"]` shape unvalidated beyond key presence — out of scope (card enumerates transcript.json cases only, machine-written not model-generated).
- parse.py's docx handler catches only BadZipFile/KeyError, not zlib.error — out of scope (card names the two archive cases explicitly).

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

**00107-meeting-tools-crash-malformed-input-v1-c1** (delta, rework diff 832d2a9..381f454)

Confirmed resolved: correction entries with non-string `from`/`to` now exit 1 with the existing diagnostic; fail-first replay against the pre-rework code (832d2a9) reproduces both original TypeErrors with the new regression tests.

FIX:
- transcript.json consumer fields (`turns`, `warnings`, `corrections`) remain unguarded beyond key presence; reproduced tracebacks for non-list/non-string-typed values and a silent broken-payload write for `null`/non-list `turns` with no corrections present — skills/debrief-meeting/scripts/build.py:126-127,147 — out of scope for this cycle's rework (narrow fix for the confirmed HIGH only); carried forward as a residual MEDIUM.
- `{"from":"old"}` / `{"to":"x"}` (key absent) silently vanish with no "matched nothing" warning, inconsistent with `{"from":"old","to":null}` which now exits 1 — skills/debrief-meeting/scripts/build.py:134-135 — residual LOW-MEDIUM.
- A wrong-type `turn` selector (e.g. `"turn":"0"`) is accepted and silently warns "matched nothing" instead of being rejected — skills/debrief-meeting/scripts/build.py:132-137 — residual LOW.
- The two new rework tests never assert the diagnostic names `extract.json` — skills/debrief-meeting/scripts/test_debrief_build.py:384-387,412-415 — residual LOW.
- Test names use review-cycle jargon ("confirmed") instead of naming the rule under test — skills/debrief-meeting/scripts/test_debrief_build.py:362,390 — residual LOW slop.
- The two new tests are a near-verbatim copy differing only in the `corrections` literal — skills/debrief-meeting/scripts/test_debrief_build.py:362-415 — residual LOW slop.

VERIFY:
- (none)

KNOWN:
- Full-suite flake in skills/sweep-fix/scripts/test_sweep_scan.py under load (unrelated to this diff; isolated rerun green).
- Stale docstring in test_debrief_build.py:1 naming a nonexistent test_build.py (pre-existing, outside this diff).

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Bob

Both dispatches (initial and the one retry) failed with a sandboxed read-only tool denial (`sandbox_apply: Operation not permitted`) before any file could be read; no evidence was produced. [BOB] ⚪ Review incomplete: sandbox denied file reads on both attempts | File: N/A | Task: general

R1: fail
R2: fail
R3: fail
R4: fail
R6: fail
R7: fail
R8: fail
R9: fail
R10: fail
R11: fail
R12: fail
R13: fail

## Carl

Dispatch failed: the `copilot` backend (gemini-3.8-flash) returned "You have exceeded your monthly quota" before producing any output. [CARL] ⚪ Review incomplete: backend quota exceeded | File: N/A | Task: general

Note: 11 non-blocking MEDIUM/LOW findings remain recorded above (Alice R1/R2/R4, Blake's blind findings, Eve's 6 residual delta findings); the confirmed HIGH on correction-entry types was fixed in the rework and verified resolved by the delta review. The batch suite ran 4106 passed, 9 skipped, 0 failed at 381f4540b95ac0fbf1d7d3423c656ca80620b9a5 (one unrelated flaky timing test in skills/sweep-fix re-ran green in isolation).

Verdict: converged
Tests: 4106 passed, 9 skipped, 0 failed
codex_rung_guard: not fired

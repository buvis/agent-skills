---
prd: dev/local/prds/wip/00034-timeout-leaks-prompt-to-disk-v1.md
review: 1
date: 2026-09-06
head_sha: b542182469dc3ef410c8896fda986bfa1e1cb068
codex_thread_id: 01a0791b-8c46-7a72-913f-1b9ad84f4d9d
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00034-timeout-leaks-prompt-to-disk-v1

Diff range: `19cbdf76f4eef0216328d69b25ac0fb808b014da..b542182469dc3ef410c8896fda986bfa1e1cb068`

codex_rung_guard: not fired

pack: failed (`engram pack` exited 1 — "not inside a registered repo; register it in
/Users/bob/.config/gita/repos.csv"). Prompts carried the `(no pack available this cycle)` sentinel for
`{PACK_FILE}` and `{PACK_FINDINGS}`. Deterministic configuration failure, so no retry was spent. The review is
degraded on retrieval context only, not invalid.

Scope note: this is cycle 1, a **full** first-pass review. `gather-context.sh` defaults its range to
`master..HEAD`, which is empty in this repo (work lands on `master`), so the range was passed explicitly as
`state.work_start_sha..HEAD`. That makes the context file label itself "incremental review"; the label is an
artifact of the flag, not the review's nature. Every reviewer prompt carried a correction saying so.

## Review Summary

Reviewed: 2 completed tasks
PRDs checked: 00034-timeout-leaks-prompt-to-disk-v1.md

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind lens — PRD only, no diff)
- Bob: ✅ Available (codex, doubt + de-slop lens; exit 0, no fallback needed)
- Carl: ✅ Available (gemini via `copilot`, model `gemini-3.8-flash`)

Consensus engine: `legacy` (single Alice subagent). Doubt reviewer: `codex`. Eve not activated — the codex
doubt-roster guard did not fire (0 codex-implemented tasks; both attempts recorded `implementor: "claude"`).

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟡 | [FIX] The direct timeout unit at lines 385–398 duplicates the end-to-end regression at lines 43–63; remove it and its synthetic prompt because the E2E test already exercises the real proposal/shortlist prompt and fails against the base revision | skills/distil-memory/scripts/test_funnel_distil_dedup.py:385 | 2 | BOB |
| [1/4] | 🟡 | [FIX] The RuntimeError and OSError tests repeat identical setup and assertions; replace them with one parametrized test over both exception types | skills/distil-memory/scripts/test_funnel_distil_dedup.py:400 | 2 | BOB |
| [1/4] | ⚪ | CHANGELOG.md `[Unreleased]/Fixed` has no entry for this typing-timeout fix, though the repo's own changelog-check CI only verifies the skill name appears somewhere in the file (it does, for unrelated entries), so this is a process gap, not a spec violation | CHANGELOG.md | general | BLAKE |
| [1/4] | ⚪ | [KNOWN] RuntimeError still persists raw `claude` stderr in `dedup_error`, leaving an unexamined disclosure boundary; changing it is out of scope because the PRD explicitly requires this branch to remain unchanged | skills/distil-memory/scripts/funnel.py:362 | 1 | BOB |
| [1/4] | ⚪ | [VERIFY] Cannot statically verify the mandated checks; run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`, and `braid --check`, requiring zero failures | N/A | general | BOB |

No 🔴 Critical and no 🟠 High findings. Carry-forward from a prior cycle: none (cycle 1).

### Verification-check queue

**No queue file written this cycle.** Bob's `[VERIFY]` item is the only VERIFY-shaped finding, and it is not
queued for two independent reasons:

- **Command shape** — it names three commands, and a queue entry must be one command with no chaining.
- **Already answered** — those exact three commands are the ones `dev/local/autopilot/last-verification.json`
  records as run at this same HEAD (`b542182`), each `exit: 0`. There is nothing left for a runner to resolve.

Eve did not run this cycle, and `agents/bob.md` defines no FIX/VERIFY/KNOWN buckets of its own, so `source:
"bob"` is reserved and no entry could be sourced from him regardless.

## Mechanical checks (computed)

- **Function line counts** — every function touched by the diff is well inside the 50-line limit; the largest
  in either file is the pre-existing `funnel.main` at 47 lines. Both files are far under 800 lines.
- **Tautological test shapes** — 15 test functions checked in 1 test file. **None found.**
- **Fail-first replay** — the scripted replay was **inconclusive and was re-run by hand**. It reported "1 test
  file(s) could not be collected at base" under `uv run --no-project --with pytest`; that collection failure
  was `ModuleNotFoundError: No module named 'yaml'`, a missing project dependency, not a failing test. Treating
  it as "fails at base" would have been a false pass on the one piece of evidence a bug fix most needs. Redone
  with the project's own runner (`uv run pytest` from a base worktree at `19cbdf7`, HEAD's test file overlaid):

  | Test | Against base `19cbdf7` | Reading |
  |------|------------------------|---------|
  | `test_no_dedup_error_ever_embeds_the_typing_prompt` | **FAILS** | Pins the change. Base produced `the typing call failed: Command '['claude', '--print', '--model', 'sonnet', 'A distiller proposes this new memory:\n\n---\nname: cheap-tier-is-haiku\n…'` — the leak the PRD describes, memory body text included, reproduced end-to-end through `funnel.main`. |
  | `test_type_proposal_reports_a_fixed_message_when_the_typing_call_times_out` | **FAILS** | Pins the change. Base carried the full 500-char argv prompt. |
  | `test_type_proposal_reports_the_runtime_error_message_unchanged` | passes | By design — pins PRD Must-have #2, that `RuntimeError` stays unchanged. |
  | `test_type_proposal_reports_the_os_error_message_unchanged` | passes | By design — same, for `OSError`. |

  4 touched tests ran; 2 failed against base (they pin the change), 2 passed against base (they pin
  explicitly-unchanged behavior the PRD requires to stay unchanged).

## Alice

Implementation-aware consensus lens. Ran the suite herself rather than trusting the replay block:
`test_funnel_distil_dedup.py` 15 passed; `skills/distil-memory/scripts` 623 passed, no regressions. Reproduced
all three PRD acceptance `rg` checks and the `known boundary` docstring match. Confirmed
`subprocess.TimeoutExpired` is not a subclass of `RuntimeError`/`OSError` (checked `__mro__`), so the clause
split is sound regardless of order, and the `FileNotFoundError` re-raise still correctly precedes the catch-all.
Confirmed the real call site passes `timeout=120` as an int (`funnel.py:183`), so `exc.timeout` renders `120s`
exactly. Confirmed `_type_proposal`'s signature and its one call site (`funnel.py:399`) are unchanged, all new
imports are used, and there is no dead code, TODO, debug marker or secret.

On scope: the three `test_type_proposal_reports_*` tests go beyond Task 2's literal single-test wording, but
pin PRD Must-have #2 with exact-string precision no pre-existing test provided — "legitimate coverage of a
stated requirement, not scope creep."

[ALICE] ✅ No issues found

```
R1: pass    R2: pass    R3: pass    R4: pass
R6: pass    R7: pass    R8: pass    R9: pass
R10: pass   R11: pass   R12: pass   R13: pass
```

## Blake

Blind lens — prompt carried the PRD and the blind rubric only: no diff, no changed-file list, no review
history. He located the code himself and judged it against the spec alone. Verdict: "exactly the minimal fix
required, nothing extra", with all success criteria verified independently (623 passed, exact fixed-string
format, `RuntimeError`/`OSError` path unchanged, the required regression test present with the specified
assertions, the `known boundary` docstring note present).

One ⚪ Low finding, outside the PRD's own rubric scope:

[BLAKE] ⚪ CHANGELOG.md `[Unreleased]/Fixed` has no entry for this typing-timeout fix, though the repo's own changelog-check CI only verifies the skill name appears somewhere in the file (it does, for unrelated entries), so this is a process gap, not a spec violation | File: CHANGELOG.md | Task: general

```
B1: pass    B2: pass    B3: pass    B4: pass    B5: pass
B6: pass    B7: pass    B8: pass    B9: pass    B10: pass
B11: pass   B12: pass   B13: pass   B14: pass   B15: pass
B16: pass   B17: pass   B18: pass   B19: pass
```

## Bob

Doubt + de-slop lens (codex, static-only sandbox; exit 0, no Claude fallback needed).

[BOB] 🟡 [FIX] The direct timeout unit at lines 385–398 duplicates the end-to-end regression at lines 43–63; remove it and its synthetic prompt because the E2E test already exercises the real proposal/shortlist prompt and fails against the base revision | File: skills/distil-memory/scripts/test_funnel_distil_dedup.py:385 | Task: 2
[BOB] 🟡 [FIX] The RuntimeError and OSError tests repeat identical setup and assertions; replace them with one parametrized test over both exception types | File: skills/distil-memory/scripts/test_funnel_distil_dedup.py:400 | Task: 2
[BOB] ⚪ [KNOWN] RuntimeError still persists raw `claude` stderr in `dedup_error`, leaving an unexamined disclosure boundary; changing it is out of scope because the PRD explicitly requires this branch to remain unchanged | File: skills/distil-memory/scripts/funnel.py:362 | Task: 1
[BOB] ⚪ [VERIFY] Cannot statically verify the mandated checks; run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`, and `braid --check`, requiring zero failures | File: N/A | Task: general

```
R1: pass    R2: pass    R3: pass    R4: pass
R6: pass    R7: pass    R8: pass    R9: pass
R10: pass   R11: pass   R12: pass   R13: pass
```

Doubt-rubric verdicts:

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Gemini via `copilot`, model `gemini-3.8-flash`. Ran the scoped suite, the skill validator, `braid --check`, and
all four PRD acceptance `rg` checks; found no frontend surface in the diff and reviewed as a generalist, as his
persona directs.

[CARL] ✅ No issues found

```
R1: pass    R2: pass    R3: pass    R4: pass
R6: pass    R7: pass    R8: pass    R9: pass
R10: pass   R11: pass   R12: pass   R13: pass
```

## Decision gate

No unresolved 🔴 Critical or 🟠 High finding. Medium and Low never block convergence, so **this cycle
converges**; the actionable Medium/Low tail is swept, not dropped.

| # | Severity | Disposition | Reason |
|---|----------|-------------|--------|
| 1 | 🟡 | **Settled deferral** (ledger) | Not duplicate coverage. The E2E pins the message through `funnel.main` with the real prompt; the direct unit pins the same contract at `_type_proposal`'s own boundary with a 500-char synthetic argv the E2E cannot produce — the exact leak vector the PRD describes. It is also the timeout member of a trio whose other two members pin PRD Must-have #2 and cannot be removed. Both were hand-verified to fail against base. Alice reviewed the same code and judged it legitimate. Test kept. |
| 2 | 🟡 | **Auto-fix** → tail sweep | Medium with a clear mechanical fix. Two 9-line tests differ only in the exception type; one `parametrize` removes the duplicated setup without losing the rule each name states. |
| 3 | ⚪ | **Auto-fix** → tail sweep | Rule-mandated, not discretionary: `rules/changelog.md` is a BLOCKING rule requiring every `fix` commit with a user-visible change to update `CHANGELOG.md` in the same commit. Confirmed `361d9c9` is `fix(distil-memory)` and touched only `funnel.py`. |
| 4 | ⚪ | **Settled deferral** (ledger) | Bob filed it KNOWN himself. PRD Must-have #2 requires this branch unchanged and Must-have #4 requires the docstring to record it as an unexamined boundary, which it does. Out of scope by specification. |
| 5 | ⚪ | **Resolved by recorded verification** | Not queued (three commands; a queue entry is one command). The same three commands are recorded in `last-verification.json` at this exact HEAD, each `exit: 0`. |

Settled decisions ledger: `dev/local/reviews/00034-timeout-leaks-prompt-to-disk-v1-ledger.json` (2 entries).

Verdict: 5 findings
Tests: 1094 passed, 0 failed, 5 skipped (reused from last-verification.json at b542182469dc3ef410c8896fda986bfa1e1cb068)

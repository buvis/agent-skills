---
prd: docs/dev/project-management/prds/wip/00088-document-the-eval-harness-contract-v1.md
review: 1
date: 2026-10-18
head_sha: f3eca457c95e9b4f7d42c0b5ddd04d809673746e
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 0064bcd2
  carl: e6ac818b
---

# Review: 00088-document-the-eval-harness-contract-v1

Diff range: `0399860a004512973e2e19ed41cdc88c30572492..f3eca457c95e9b4f7d42c0b5ddd04d809673746e`

codex_rung_guard: not fired

pack: failed (engram pack exit 1: not inside a registered repo; run `gita add <repo>`) — review degraded, not invalid; no findings-precedent section this cycle.

## Review Summary

All four lenses ran: Alice (consensus), Blake (blind, PRD-only), Bob (doubt rubric D1-D5 + de-slop) and Carl (Gemini). 17 consolidated findings, **no CRITICAL and no HIGH**. The cycle converges; the actionable Medium/Low tail is swept, not dropped.

### Agent Status

- **alice**: available — ran on the legacy single-subagent consensus engine.
- **blake**: available — blind lens, PRD-only prompt.
- **bob**: available **via the Claude fallback**. Codex produced an off-target review on its first run (it reviewed `skills/debrief-meeting/app/smoke.test.js`, a file absent from this diff) and its retry returned a lack-of-input refusal: codex's read-only shell could not read the staged inputs because `cat` is blocked by the aegis `prefer_tools` hook in this environment. A Claude subagent then ran Bob's exact assembled doubt prompt (with Read substituted for `cat`), so the doubt lens did not drop. Both codex dispatch rows are closed as errors.
- **carl**: available **after one retry**. His first run read the correct staged inputs and then also reviewed `skills/debrief-meeting`, off-target; the retry was on-target.

Two reviewers going off-target onto the same unrelated skill on their first dispatch is an infrastructure signal, not a content one — recorded here and deferred as an operational finding, since the staged inputs were verified correct (`rg` found zero `debrief` matches and 36 `use-qwen` matches in the context file).

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🟡 | Subparsers-action lookup is duplicated inside the file: `_subparser` (skills/use-qwen/scripts/test_runbook_matches_harness.py:28) and `test_runbook_names_every_harness_subcommand` (skills/use-qwen/scripts/test_runbook_matches_harness.py:37) each re-run `next(action for action in parser._actions if action.choices is not None)`, and the two flag tests share an identical 5-line body. Simpler, behavior-preserving: add `_subparsers_action()` returning that action, call it from `_subparser` and from the subcommand test, and factor the flag loop into `_long_flags(subparser)` that yields every `--` option except `--help`; each test then reads `for flag in _long_flags(_subparser("vet")): assert flag in section, flag`. | skills/use-qwen/scripts/test_runbook_matches_harness.py | 1 | ALICE, BOB, BLAKE |
| R18 | [2/4] | 🟡 | Flag drift test uses bare substring matching, so two run flags are masked by longer ones: `--shape` is a substring of the documented `--shapes` and `--bound` of `--gate-bound`. Delete `--bound SECONDS` or `--shape {description,tdd}` from § 7 and the test still passes, defeating the stated goal that the contract "cannot drift silently". The PRD prescribed this assertion literally, so it is a spec defect faithfully implemented; a word-boundary check (`rg`-style `--shape\b`) would close it | skills/use-qwen/scripts/test_runbook_matches_harness.py:50 | 1 | BLAKE, BOB |
| R2 | [2/4] | ⚪ | `_subparser(name: str) -> "object"` uses a quoted, meaningless return annotation; `argparse.ArgumentParser` is the actual type of a `choices` value and `argparse` is already importable here | skills/use-qwen/scripts/test_runbook_matches_harness.py:26 | 1 | ALICE, BOB |
| R3 | [1/4] | 🟡 | § 7 says "`inputs_sha256` maps every sealed input ... to its digest", but `template/` - named one line above as part of the sealed set - is not a key of `inputs_sha256` (keys are `spec`, `pretask`, `canonical_patch`, `manifest`, `prompt:<shape>`, `dispatch_references`, `oracle`; `eval_harness/evidence.py:162`, `:180`), and `spec.json`, which is a key, is absent from the sealed-set sentence. An operator reading the next sentence ("Before any dispatch it refuses a task whose sealed inputs no longer match `inputs_sha256`") will believe an edited `template/` tree is caught pre-dispatch; `recheck_inputs` does not catch it (template drift is only caught later, per attempt, at `eval_harness/trees.py:213`). Wording came verbatim from the PRD | skills/use-qwen/references/eval-runbook.md:113 | 2 | BLAKE |
| R4 | [1/4] | 🟡 | Drift test is one-directional: nothing fails when § 7 names a subcommand or flag the CLI has removed, so the runbook can rot in the stale direction while staying green. Not required by the PRD, which is the gap | skills/use-qwen/scripts/test_runbook_matches_harness.py:34 | general | BLAKE |
| R5 | [1/4] | 🟡 | Function cmd_scan exceeds 50-line limit (54 lines) | skills/glean/scripts/glean.py:191 | general | CARL |
| R6 | [1/4] | 🟡 | Unrequested formatting changes to glean scripts included in diff | skills/glean/scripts/glean.py:1 | general | CARL |
| R7 | [1/4] | ⚪ | `run_eval_harness.py`'s own module docstring still says "vet, verify and run" and omits `render`, the same drift this PRD fixes in the runbook; pre-existing and outside the diff, so surfaced rather than changed | skills/use-qwen/scripts/run_eval_harness.py:2 | general | ALICE |
| R8 | [1/4] | ⚪ | The review diff carries unrelated, uncommitted reformatting of `skills/glean/scripts/glean.py` and `test_glean.py` (whitespace/trailing-comma reflow, `re.I` -> `re.IGNORECASE`, behavior-preserving). Mtime 12:16 vs 21:24 for this PRD's new test shows it predates this build session, so it is swept-in working-tree noise, not scope creep by task 1/2; keep it out of this PRD's commits | skills/glean/scripts/glean.py | general | ALICE |
| R9 | [1/4] | ⚪ | § 7 documents `run`'s three exit codes and `verify`'s two but not `vet`'s (0 when every task ends ready, 1 naming the failed check, `eval_harness/attempt.py:109`), and does not say that a failed check leaves `vetting.json` written with `ready: false` and no `ready` marker - the text reads as if the marker is always written | skills/use-qwen/references/eval-runbook.md:111 | 2 | BLAKE |
| R10 | [1/4] | ⚪ | `run` catches refusals only around `_admit`; `_plan_attempts` runs outside that `try` and calls `spec.load_spec`, so a `SpecError` there surfaces as a traceback rather than the "each refusal names the remedy" contract § 7 now advertises. Pre-existing harness code the PRD forbade touching; the new doc is what raises the expectation | skills/use-qwen/scripts/eval_harness/attempt.py:167 | 2 | BLAKE |
| R11 | [1/4] | ⚪ | Private helper `_subparser` exists beyond the PRD's declared new symbols (`_section_seven` plus the four tests). Harmless and needed by two tests, but it is undeclared surface | skills/use-qwen/scripts/test_runbook_matches_harness.py:26 | 1 | BLAKE |
| R12 | [1/4] | ⚪ | The commit range also rewrote `docs/dev/project-management/meta/assumptions.md`, replacing the previous PRD's recorded assumptions wholesale (13 lines removed). Outside the PRD's three-file implementation set; looks like autopilot keeper rotation rather than deliberate work, and the prior record is only recoverable from git | docs/dev/project-management/meta/assumptions.md:1 | general | BLAKE |
| R13 | [1/4] | ⚪ | The test-only commit `3f24b2f` is red on its own (the runbook edit lands in `99846b5`), so the history contains one non-green commit. The PRD explicitly permitted either ordering; noted only because a bisect across that commit fails for a documentation reason | N/A | 1 | BLAKE |
| R14 | [1/4] | ⚪ | `_section_seven` anchors on the exact heading `## 7. Harness rounds`; renumbering or renaming the section raises a bare `StopIteration` instead of naming the missing anchor | skills/use-qwen/scripts/test_runbook_matches_harness.py | 1 | BOB |
| R15 | [1/4] | ⚪ | PRD must-have "SKILL.md names verify beside vet, run, render" has no test; the SKILL.md harness line can drift silently on the next subcommand | skills/use-qwen/SKILL.md | 2 | BOB |
| R16 | [1/4] | ⚪ | Cannot statically verify: `uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen` passes and the full suite's PASS/FAIL/SKIP counts (test gate reported exit 0 with counts unavailable) | N/A | 2 | BOB |
| R17 | [1/4] | ⚪ | The reviewed diff carries unrelated working-tree reformatting of `skills/glean/scripts/glean.py` and `test_glean.py` plus a rewritten `meta/assumptions.md`, none of it PRD 00088 work | N/A | general | BOB |

**Consolidation note.** `consolidate_findings.py` folded Blake's and Bob's substring-matching finding onto Alice's deduplication finding, because both cite the same file and the merge keeps the first-seen wording. Those are two distinct defects, so the substring-matching finding is restored verbatim above as **R18** rather than being lost inside R1's text (PRD 00095: the finding that survives must not be the one nobody wrote down). Every other row is the script's output unchanged.

## Alice

Five findings (one 🟡, four ⚪), all listed above. Her own verification this cycle: `uv run pytest -q` → 3950 passed, 9 skipped, 0 failed (424 s); `uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen` → `[OK] Skill is valid!`; the runbook § 7 text is a verbatim match to the PRD contract; all four subcommands, every `vet`/`run` long flag and all nine `VETTING_KEYS` appear in § 7; `Three commands` is gone; hold stubs 00081/00082 are absent from `prds/hold/`.

R1: pass / R2: pass / R3: pass / R4: pass / R6: pass / R7: pass / R8: pass / R9: pass / R10: pass / R11: pass / R12: pass / R13: pass

## Blake

Eight findings (three 🟡, five ⚪), all listed above. Blind lens: he located the code from the PRD alone and verified every factual claim § 7 makes against the harness source, finding one documentation inaccuracy (R3). His own verification: `uv run pytest skills/use-qwen/scripts/test_runbook_matches_harness.py -q` → 4 passed; `uv run pytest -q` → 3950 passed, 9 skipped (431.99 s); validator OK; `rg -c "Three commands"` → exit 1; red-before proved by inspecting `git show 3f24b2f:...eval-runbook.md` (zero matches for `verify `, `--shapes`, `--alternate`, `` `inputs_sha256` ``). No security surface: no secrets, auth, network, new dependency or write path.

B1-B19: pass (all nineteen).

## Bob

Doubt lens + de-slop, run through the Claude fallback after codex failed twice (see Agent Status). Eight findings (two 🟡, six ⚪), all listed above, plus a positive-verification record so the next cycle need not redo it: `VETTING_KEYS` is exactly the nine keys § 7 lists in the same order; all four subcommands and all 14 `vet`/`run` option strings appear in § 7; `--gate-bound` default 1800, `--retry-discarded` default `none`, the `--usage-limit-cmd` argv shape, `--alternate` odd-task reversal, run exit codes 0/1/2 with `halted.txt`, `verify`'s line format and 0/1 exits, the wholesale sealed-set replacement and the default-shape rule all hold against code; § 7 is bounded by `## Scope of approval`, so `_section_seven` slices the intended text.

FIX bucket: the four items restored as R1, R1b, R2 and R14. VERIFY bucket: the validator and suite counts, queued as a verification check (see below). KNOWN bucket: no test pins SKILL.md's `verify` mention (outside the PRD's verbatim test contract); section-wide rather than per-subcommand flag checks (the PRD specifies the assertion literally); the unrelated glean and assumptions.md edits.

D1: pass / D2: pass / D3: pass / D4: pass / D5: pass

R1: pass / R2: pass / R3: pass / R4: pass / R6: pass / R7: pass / R8: pass / R9: pass / R10: pass / R11: pass / R12: pass / R13: pass

## Carl

Two 🟡 findings after one retry, both about the uncommitted `skills/glean` working-tree drift swept into the review diff rather than about this PRD's work (R5, R6). His R12 fail is factually correct and corroborated by the computed mechanical-facts block (`cmd_scan` — line 191, 54 lines), but the function is pre-existing drift outside PRD 00088's three-file scope, so it is recorded as a settled deferral rather than swept. Backend: copilot. His own verification: the new test file passes, `rg -c "Three commands"` exits 1, the use-qwen validator is OK, and the full `uv run pytest` suite ran green.

R1: pass / R2: pass / R3: pass / R4: pass / R6: pass / R7: pass / R8: pass / R9: pass / R10: pass / R11: pass / R12: fail (glean drift, out of scope) / R13: pass

## Mechanical checks

- **Tautological test shapes**: 23 test functions checked across 2 test files, zero `[MECH]` lines.
- **Fail-first replay**: 4 touched tests ran against base `0399860a0045`, 4 failed, 0 passed — the drift test genuinely pins the documentation edit.
- **Mechanical facts** (computed from `ast`): used to adjudicate Carl's R12; no finding contradicted a computed value, so nothing was discarded on that ground.

Verdict: 18 findings
Tests: 3950 passed, 0 failed, 9 skipped (suite run this cycle)

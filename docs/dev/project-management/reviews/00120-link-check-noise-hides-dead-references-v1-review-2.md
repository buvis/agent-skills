---
prd: docs/dev/project-management/prds/wip/00120-link-check-noise-hides-dead-references-v1.md
review: 2
date: 2026-10-29
head_sha: 7a863d6d445ee1c12fee5bae96e947f9e5aa2fe3
codex_thread_id: 01a188e5-b4ef-7ee0-bcb4-e1c8e6025536
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: b4f25007
  carl: 402995f6
---

# Review: 00120-link-check-noise-hides-dead-references-v1

Diff range: `43984f8c6750e994706580a553023b1af5e2c309..7a863d6d445ee1c12fee5bae96e947f9e5aa2fe3` (incremental — cycle 1 reviewed the full work range)

codex_rung_guard: not fired

## Review Summary

Reviewed: 5 completed tasks
PRDs checked: 00120-link-check-noise-hides-dead-references-v1.md
Consensus engine: legacy
Context pack: ok
Settled-decisions ledger: 6 entries fed to Alice and Bob; `--ledger-dismiss BLAKE` active

### Agent Status

- Alice: ✅ Available (consensus lens, Claude subagent)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (doubt lens + de-slop, codex, inlined prompt 142 KB, resumed cycle-1 thread)
- Carl: ⚠️ Unavailable: gemini-run exit 1, backend=copilot model=gemini-3.8-flash, "You have exceeded your monthly quota". One-off runtime failure (not exit 4), so no batch latch and no retry against an exhausted monthly quota — same cause as cycle 1.

Mechanical test checks: the tautological-shape block was clean (24 test functions checked). The fail-first replay raised 1 `[MECH]` finding, absorbed into R3 below (same test file and test), so it added no separate row: `mech-check` is appended to R3's finders.

### Test-gate provenance (fail loud)

`review-stage` ran the full suite this cycle at HEAD and reported `counts unavailable`: this repo has no `dev/bin/release-checks`, so the gate command `uv run pytest` emits no `PASS n FAIL n SKIP n EXIT n` line for `cli/verification.SUMMARY_RE` to parse. The run itself is green — `docs/dev/tmp/gate-00120c2.log:207` records `4192 passed, 9 skipped, 236 warnings in 417.15s` with exit 0. The `Tests:` line below carries those counts read from that log rather than a second seven-minute run that would parse identically. `last-verification.json` was therefore not written this cycle.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | 🟡 | The new inventory tree in the PRD adds 10 fresh `~/.claude/dev/local/ provenance` findings, one per line, with the finding target `~/.claude/dev/local/`. This is the same noise class as R2, moved from the design doc into the PRD: the PRD cited in the tree comments no longer resolves under the checker. A fresh `run()` reports them at lines 61-70. Add `link-ok:` to those lines, or reword the comments to "provenance in dev/local" without the `~/.claude/...` path. | docs/dev/project-management/prds/wip/00120-link-check-noise-hides-dead-references-v1.md:61 | 4 | ALICE, BLAKE |
| R2 | [2/3] | 🟡 | The fence closer is still any line starting with three backticks, at `check_links.py:96`. A language-tagged opener such as a fenced `python` block inside an open fence flips state and closes it, and a 4-backtick fence with inner 3-backtick lines mis-pairs. That can suppress a malformed or unclosed evidence block without reporting the error. The earlier discard reason ("the rework covers it") does not hold, because the closer is unchanged. Low severity, since real evidence blocks are plain. Fix by requiring the closer to be a bare fence at least as long as the opener, and add a malformed-closer test. | skills/review-prd-backlog/scripts/check_links.py:96 | 3 | ALICE, BOB |
| R3 | [1/3] | 🟡 | `test_evidence_fence_without_a_following_fence_is_not_armed` still passes against the pre-change code, which was the R8/R11 ask. The added assertion `"[[suppressed-package]] (no memory)" not in [f[2] for f in findings]` is redundant: the exact-equality assertion just above already allows only lines 2 and 3. The extra closed-evidence block is also suppressed identically by the old code (heading, then fence, then close). Replace the fixture with a case the old code cannot pass. For example, put a closed ordinary fence containing the marker ahead of the evidence block, as the sibling test already does, or drop the redundant assert. | skills/review-prd-backlog/scripts/test_check_links.py:277 | 5 | ALICE, mech-check |
| R4 | [1/3] | 🟡 | The backtick exemption drops every `[[name]]` from memory-link checking, whether or not it is a literal example. A genuine memory link written in a code span is now undetectable, which cuts against "genuine memory links remain detectable". The rule is pinned by tests but not documented in the module docstring or in SKILL.md step 1. | skills/review-prd-backlog/scripts/check_links.py:140 | 1 | BLAKE |
| R5 | [1/3] | 🟡 | The evidence-fence skip is keyed to a hard-coded template phrase, "Carry the observed evidence verbatim". About 40 PRDs carry it, including backlog PRDs that SKILL.md:46 blocks on. Any genuine dead path or PRD citation inside the fence after that heading is silently skipped. This hides real rot. The skip is not documented in the docstring or SKILL.md. The unclosed-fence handling and the armed-state fix are sound. | skills/review-prd-backlog/scripts/check_links.py:107 | 1 | BLAKE |
| R6 | [1/3] | 🟡 | Tracking ordinary fences introduces spurious evidence errors: an unclosed ordinary code block now reaches the unconditional EOF error branch without any evidence heading. Require `fence_is_evidence` before reporting this error; add a regression confirming ordinary unclosed blocks remain scanned without evidence errors. | skills/review-prd-backlog/scripts/check_links.py:109 | 3 | BOB |
| R7 | [1/3] | 🟡 | The new inventory comments repeat the known-missing `~/.claude/dev/local/` path without waivers. Ordinary fenced blocks remain scanned, so these comments introduce fresh dangling-path findings while repairing documentation noise. Replace the repeated path comments with "historical provenance"; retain every enumerated repair filename. | docs/dev/project-management/prds/wip/00120-link-check-noise-hides-dead-references-v1.md:61 | 4 | BOB |
| R8 | [1/3] | ⚪ | Scope creep. The spec asks only for double-bracket examples and diagnostic-prefix quotes. The change also widens the `PRD_RE` lookbehind from `\d` to `\w` (UUID fragments) and adds a new scan-error type for unclosed fences. The lookbehind change also stops detecting citations glued to a word character, such as `x00099-foo`. | skills/review-prd-backlog/scripts/check_links.py:26 | 1 | BLAKE |
| R9 | [1/3] | ⚪ | The checker still reports 196 findings, and a few false-positive classes are untouched. Examples are range tokens such as `00039-00043` (`meta/project-capsule.md:1140`) and truncated `{slug}`/`<run-id>` paths (`designs/00073-sweep-loud-failures-v1-design.md:175`). This is not a spec violation, because the spec says the count is not a target. | skills/review-prd-backlog/scripts/check_links.py:25 | general | BLAKE |
| R10 | [1/3] | ⚪ | The PRD repairs waive the whole line with `link-ok:` and insert it mid-prose, for example "Source: link-ok: `~/.claude/dev/local/...`". This keeps the citations and fabricates nothing. But it also waives any other citation on those lines, and it leaves awkward text. The 00118 lifecycle-path fix (`prds/done/`) is a proper repair. | docs/dev/project-management/prds/done/00002-add-sweep-fix-skill-v1.md:3 | 2 | BLAKE |

### Auto-dismissed (ledger)

- [BLAKE] ⚪ The remaining genuine rot in `prds/backlog/00050-qwen-ivan-capability-eval-v1.md` is correctly left in place, as the spec requires. It is still reported, and `meta/project-capsule.md:565,594` still correctly flags the retired 00057 PRD. | File: docs/dev/project-management/prds/backlog/00050-qwen-ivan-capability-eval-v1.md:6 — Requirements ambiguity, decision already taken in the design doc: 00050's citations are forward references to artifacts 00049 will produce, and 00049 still sits in prds/backlog. Repairing them now would point at files that do not exist yet; removing them would delete the eligibility link between the two PRDs. Deferred to batch end for a human call on whether the design's forward-reference reading overrides the PRD's literal Phase 1 wording.

## Alice

Consensus lens, implementation-aware. Three findings (R1, R2, R3 above).

Verification she ran: `test_check_links.py` gives 24 passed; a fresh `run()` over the repo returns 196 findings and `scan_errors == []`, so the cycle-1 unclosed-fence scan error (R1/R6/R7 of cycle 1) is gone. She replayed HEAD's tests against the cycle-1 `check_links.py` in a scratch worktree: the three new fence-state tests fail there (marker-in-closed-ordinary-fence, marker-in-code-fence, repeated-marker-leak), so they pin the fix, while the strengthened `test_evidence_fence_without_a_following_fence_is_not_armed` still passes there.

Her read of the prior cycle: R1, R6, R7 resolved (trigger anchored with `startswith`, markers recognised only outside open fences, evidence state tracked per fence); R2 resolved for the design doc (0 findings now) but the same noise class reappeared in the PRD (R1 here); R3 resolved (Repository Structure lists the 11 `done/` files and shows 00120 under `wip/`); R8/R11 not resolved (R3 here); R10's cycle-1 discard reason no longer holds, because the rework did not touch the closer (R2 here).

She reports briefly staging the old script in the index by mistake and resetting it; `git status` is back to the two pre-existing metrics-file modifications.

```
R1: pass
R2: fail
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
```

## Blake

Blind lens, PRD-only prompt. Seven findings; one was auto-dismissed against the ledger (above), six reached the table (R1, R4, R5, R8, R9, R10).

What he verified: `test_check_links.py` passes (24 passed) and `validate_skill.py` on review-prd-backlog is valid. He did not rerun the full suite or `braid --check`.

```
B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: fail
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass
```

### Doubt buckets (Bob)

```
FIX:
- Tracking ordinary fences introduces spurious evidence errors on an unclosed ordinary block (check_links.py:109)
- The malformed-closer path is unchanged, so the cycle-1 discard reason no longer holds (check_links.py:96)
- The new inventory comments repeat the known-missing ~/.claude/dev/local/ path without waivers (00120 PRD:61)
VERIFY:
- (none)
KNOWN:
- (none)
```

No VERIFY item, so no verification-check queue file was written for cycle 2.

## Bob

Doubt lens plus de-slop, codex, static-only sandbox, inlined prompt (142 KB: context plus full diff verbatim), resumed cycle-1 thread `01a188e5`. Three findings (R2, R6, R7 above).

```
R1: fail
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: pass
```

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Carl: unavailable (gemini-run exit 1, backend=copilot model=gemini-3.8-flash, monthly quota exceeded). Graceful degradation: the other three lenses carried the cycle, as in cycle 1.

Verdict: 10 findings
Tests: 4192 passed, 0 failed, 9 skipped (suite run this cycle)

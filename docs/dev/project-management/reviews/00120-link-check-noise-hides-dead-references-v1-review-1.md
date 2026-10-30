---
prd: docs/dev/project-management/prds/wip/00120-link-check-noise-hides-dead-references-v1.md
review: 1
date: 2026-10-29
head_sha: 43984f8c6750e994706580a553023b1af5e2c309
codex_thread_id: 01a188e5-b4ef-7ee0-bcb4-e1c8e6025536
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: 7601725c
  carl: 33e7184d
---

# Review: 00120-link-check-noise-hides-dead-references-v1

Diff range: `1abb9fa7d36b10925c9e9f67744ee22ee0c6c042..43984f8c6750e994706580a553023b1af5e2c309`

codex_rung_guard: not fired

## Review Summary

Reviewed: 2 completed tasks
PRDs checked: 00120-link-check-noise-hides-dead-references-v1.md
Consensus engine: legacy
Context pack: ok

### Agent Status

- Alice: ✅ Available (consensus lens, Claude subagent)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (doubt lens + de-slop, codex, inlined prompt)
- Carl: ⚠️ Unavailable: gemini-run exit 1, backend=copilot model=gemini-3.8-flash, "You have exceeded your monthly quota". One-off runtime failure (not exit 4), so no batch latch and no retry against an exhausted quota.

Mechanical test checks: 1 `[MECH]` finding absorbed (fail-first replay). Tautological-shape block was clean.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | 🟠 | The "Carry the observed evidence verbatim" trigger is a bare substring match (`"..." in stripped`), so any prose or code line that merely quotes the phrase arms the next fence anywhere in the file. The shipped design doc does this: the python snippet at design line 134 contains the phrase, so the snippet's own closing fence at line 147 is read as an opening evidence fence. A fresh run of `check_links.py --root . --json` now reports a new scan error, `designs/00120-link-check-noise-hides-dead-references-v1-design.md: evidence fence opened at line 147 never closed`. The baseline was `scan_errors: []`, and Task 2's verify step says to confirm no new scan_errors appeared. If a later ordinary fence had closed, it would have been silently skipped instead. Fix: anchor the trigger, for example `stripped.startswith("Carry the observed evidence verbatim")`. | skills/review-prd-backlog/scripts/check_links.py:111 | 1 | ALICE, BLAKE |
| R2 | [2/3] | 🟡 | The design doc added in this diff adds 11 new findings to the corpus, the same noise class this PRD removes. They are the example tokens `00042-`, `99999-` (line 166), `00057-` and `[[package]]` (line 218), `17278-` (line 359), `99999-` (line 383), `/Users/you/` (line 196), `/Users/bob/.codex/session` (line 198), `~/.claude/dev/local/` (lines 29 and 261) and the stale `prds/backlog/00118-...` path (line 289). The count drops from the design-time 244 to 197 only because of the checker fix. Add `link-ok:` to those lines (or reword the examples) so the new document adds no findings. | docs/dev/project-management/designs/00120-link-check-noise-hides-dead-references-v1-design.md:166 | 2 | ALICE, BLAKE |
| R3 | [1/3] | 🟠 | Phase 1 inventory requirement not met: the PRD's Repository Structure still lists only 00050 and 00120. The PRD required each repair target's exact path to be added there and forbade editing unlisted files. Commit a29d2e2 edited 11 prds/done files (00002, 00003, 00004, 00006, 00007, 00008, 00009, 00015, 00017, 00030, 00118) that no spec section lists. The inventory lives only in the design doc. The same PRD section also still shows 00120 under prds/backlog/ although the file now sits in prds/wip/. | docs/dev/project-management/prds/wip/00120-link-check-noise-hides-dead-references-v1.md:55 | 2 | BLAKE |
| R4 | [1/3] | 🟠 | Most "repairs" are `link-ok:` waivers on genuinely missing `~/.claude/dev/local/...` citations, not repairs or removals. The spec says to repair with verified replacement targets or remove obsolete citations. Waiver is an existing mechanism, but it hides the dead target and exempts the whole line from every other check. It also leaves tool markers in prose. The PRD does not name this as an accepted outcome | docs/dev/project-management/prds/done/00006-nag-audit-cadence-in-brief-portfolio-v1.md:3 | 2 | BLAKE |
| R5 | [1/3] | 🟠 | The one PRD the spec names as the reported genuine dead-link example was deliberately left unrepaired. 00050 still yields 5 findings: prds/done/00049-..., audit-results/qwen-ivan-calibration/protocol.md (lines 6, 113, 208), and a truncated `qwen-ivan-` token (line 156). The design overrides the accepted evidence and calls them a forward-reference eligibility gate. That is plausible, since 00049 is still in prds/backlog and not in done. But Phase 1 acceptance says every classified broken reference in the enumerated files is repaired or removed. The override is defensible but contradicts the spec's wording, and nothing in the PRD records that decision | docs/dev/project-management/prds/backlog/00050-qwen-ivan-capability-eval-v1.md:6 | 2 | BLAKE |
| R6 | [1/3] | 🟠 | Evidence markers inside ordinary code fences arm suppression. The new design document reproduces the helper's marker string inside a Python fence; its closing delimiter becomes an evidence opener, producing a spurious unclosed-fence error. Track ordinary fences and recognize headings only outside them; add this regression. | skills/review-prd-backlog/scripts/check_links.py:89 | 1 | BOB |
| R7 | [1/3] | 🟠 | A repeated marker inside an evidence fence leaves `armed_at` set after closing it, so the next ordinary fenced block is silently excluded, hiding genuine broken references. Handle markers according to fence state and clear pending state when closing; test repeated markers followed by an ordinary block containing missing references. | skills/review-prd-backlog/scripts/check_links.py:89 | 1 | BOB |
| R8 | [1/3] | 🟡 | `test_evidence_fence_without_a_following_fence_is_not_armed` passes against the pre-change code (the fail-first replay confirms this), so it does not pin the change. It is a negative guard and could fail against a wrong implementation, for example one that skips until a blank line. Strengthen it with a case the old code cannot pass. | skills/review-prd-backlog/scripts/test_check_links.py:1261 | 1 | ALICE, mech-check |
| R9 | [1/3] | 🟡 | The backtick skip for `[[x]]` is purely syntactic. Any memory link wrapped in single backticks is never checked, so a genuinely dangling `[[ghost]]` in inline code is silently hidden. The Risks section names this exact hazard. The design assumes real links are always bare, and the tests encode that assumption | skills/review-prd-backlog/scripts/check_links.py:130 | 1 | BLAKE |
| R10 | [1/3] | 🟡 | `startswith` on a triple-backtick prefix accepts an opening delimiter such as a language-tagged fence as a closing fence, suppressing findings from an actually unclosed evidence block without reporting its error. Validate closing delimiter length and trailing whitespace against the opener; add malformed-closer coverage. | skills/review-prd-backlog/scripts/check_links.py:92 | 1 | BOB |
| R11 | [1/3] | 🟡 | The mechanical replay shows `test_evidence_fence_without_a_following_fence_is_not_armed` passes against the old implementation. Retain its preservation assertions and add a separate closed evidence block in the same scan, asserting suppression there so the test also pins the new behavior. Same defect as R8, raised independently. | skills/review-prd-backlog/scripts/test_check_links.py:266 | 1 | BOB, mech-check |
| R12 | [1/3] | ⚪ | `armed_at` survives any number of intervening lines until the next fence line. The design says a range is trusted only "before the next armed trigger", but the code does not enforce this: a re-arm just overwrites `armed_at`. This is acceptable per the design's accepted-edge note, but the comment or docstring should state that arming is unbounded. | skills/review-prd-backlog/scripts/check_links.py:107 | 1 | ALICE |
| R13 | [1/3] | ⚪ | Residual placeholder noise remains. `PATH_RE` stops at an angle or brace character, so the truncated token no longer matches `PLACEHOLDER`. This yields false positives like `.../audit-results/qwen-ivan-` (from a `<run-id>` placeholder) and `.../audit-results/sweep-` (from a `{slug}` placeholder). The reported classes are fixed, but the checker's noise is not fully removed | skills/review-prd-backlog/scripts/check_links.py:25 | 1 | BLAKE |

## Alice

Consensus lens, implementation-aware. Four findings (R1, R2, R8, R12 above).

Verification she ran: `uv run pytest skills/review-prd-backlog/scripts/test_check_links.py` gave 21 passed; the twelve `link-ok:` waivers and the single 00118 path fix match the task inventory; 00050 untouched and still 5 findings; corpus total now 197 findings plus the one new scan error she reports in R1.

```
R1: pass
R2: pass
R3: pass
R4: fail
R6: pass
R7: pass
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: pass
```

## Blake

Blind lens, PRD-only prompt. Eight findings; R3 below folds his two PRD-section findings (missing repair inventory, stale lifecycle location) into one row.

What he verified: `PRD_RE` now excludes a word character before the five digits, stopping UUID fragments; the self-quote skip covers the quoted diagnostic; the backtick-wrapped memory-link skip covers the literal examples; an unclosed evidence fence is reported as a scan error, so the checker does not fail open; positive controls and fixture-tree regressions exist for genuine path, PRD and memory references; the error contract, citing-line context and `--json` shape are unchanged; no directory-wide exclusions were added. `test_check_links.py` passes (21 passed) and `validate_skill.py` on review-prd-backlog passes. He did not run `braid --check` or the full suite, and did not confirm the new regressions fail against the prior code.

```
B1: fail
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass
```

### Doubt buckets (Bob)

```
FIX:
- Evidence markers inside ordinary code fences arm suppression (check_links.py:89)
- A repeated marker inside an evidence fence leaves armed_at set after closing (check_links.py:89)
- Triple-backtick prefix match accepts a language-tagged opener as a closing fence (check_links.py:92)
- The fail-first replay shows the no-following-fence test passes against the old code (test_check_links.py:266)
VERIFY:
- (none)
KNOWN:
- (none)
```

No VERIFY item, so no verification-check queue file was written for cycle 1.

## Bob

Doubt lens plus de-slop, codex, static-only sandbox, inlined prompt (158 KB: context plus full diff verbatim). Four findings (R6, R7, R10, R11 above).

```
R1: fail
R2: fail
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

Carl: unavailable (gemini-run exit 1, backend=copilot model=gemini-3.8-flash, monthly quota exceeded). Graceful degradation: the other three lenses carried the cycle.

Verdict: 13 findings
Tests: 4189 passed, 0 failed, 9 skipped (suite run this cycle)

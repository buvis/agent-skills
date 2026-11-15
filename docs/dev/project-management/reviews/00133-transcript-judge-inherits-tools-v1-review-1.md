---
prd: docs/dev/project-management/prds/done/00133-transcript-judge-inherits-tools-v1.md
review: 1
date: 2026-11-15
head_sha: ef83b22d01eef24abb8f3a731221d82f39733886
reviewers: alice,blake,bob,carl,eve
agents:
  alice: available
  blake: available
  bob: available
  carl: available
  eve: available
---

# Review: 00133-transcript-judge-inherits-tools-v1

Diff range: `7a61c5b..ef83b22`, path-scoped to `funnel.py`,
`test_funnel_triage.py`, `test_funnel_main.py` and `funnel_test_helpers.py`
under `skills/distil-memory/scripts/`. Later PRDs changed the same files; their
hunks are in the diff.

codex_rung_guard: fired (1 codex-implemented task(s))

Standalone completion review, run by a session that did not build this PRD.
The build stopped on a red suite on 2026-11-10 (a test helper outside the
card's allowlist); commit a9dd871 fixed the helper and the suite is green.
No loop state was read or written. Consolidation was model-side, not by
`consolidate_findings.py`. No engram pack (the worktree is not registered).
The fail-first replay was skipped by the staging tool; Eve replayed it by
hand: with the argv restriction removed 6 tests fail, with the raw snippet
restored 8 fail.

## Roster

| Lens | Backend / model | Result |
|---|---|---|
| Alice, consensus | native Claude subagent | R12 fail, rest pass |
| Blake, blind PRD-only | native Claude subagent | B1-B19 pass |
| Bob, doubt | Codex CLI, inlined prompt (model not printed by the runner) | R12 fail, D1-D5 pass |
| Carl | Copilot CLI, `gemini-3.8-flash` | R12 fail, rest pass |
| Eve, non-Codex doubt | native Claude subagent, Fable | D1-D5 pass |

## Alice

Seven findings (4 medium, 3 low): strong-tier prompts lack the untrusted-data
framing, no changelog entry, `main` 52 lines, a 72-line test and a 52-line
fixture, three cosmetic notes. R1-R11 pass, R12 fail, R13 pass.

## Blake

No spec violation in the judge or triage path. Two notes: `distil.py` and
`dedup.py` share the tool-less `judge()` but not the framing (outside the
spec); tests show argv, not a real CLI (the PRD states that limit).
B1-B19 pass.

## Bob

One finding: the 72-line damaged-transcript test.

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
R12: fail
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Three size findings: `main` 52 lines, the 72-line test, `make_corpus` 52 lines.
R12 fail, rest pass.

## Eve

Five FIX, two VERIFY, one KNOWN. The production change is correct against the
PRD; two regressions did not pin what they claimed.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Consolidated findings

| Ref | Voices | Severity | Issue | File | Disposition |
|---|---|---|---|---|---|
| F1 | Eve | MEDIUM | The argv checks were membership tests: `--tools "" Bash --strict-mcp-config` plus a permission flag passed all 869 tests. | skills/distil-memory/scripts/test_funnel_triage.py:34 | Fixed: exact argv equality in both tests. |
| F2 | Eve | MEDIUM | The framing sentence was pinned by two keywords; a sentence telling the judge to obey the data passed. | skills/distil-memory/scripts/test_funnel_triage.py:130 | Fixed: exact prompt equality. |
| F3 | Alice, Eve | MEDIUM | No changelog entry for the judge restriction. | CHANGELOG.md | Fixed. |
| F4 | Alice, Bob, Carl | MEDIUM | `main` 52 lines, a 72-line test, a 52-line fixture (R12). | skills/distil-memory/scripts/funnel.py:578 | Deferred: these lines come from PRDs 00098, 00143 and 00144, not from this PRD's commits; size only, no behaviour. |
| F5 | Alice, Blake, Eve | MEDIUM | The strong-tier distil and dedup prompts embed the raw snippet with no data framing, so a hostile snippet can steer proposed memory text. | skills/distil-memory/scripts/distil.py:43 | Deferred: the PRD limits framing to the triage classifier; the call is tool-less now and a human reviews each proposal. Needs its own PRD. |
| F6 | Eve | LOW | The ASCII form of the data line was not pinned. | skills/distil-memory/scripts/test_funnel_triage.py:195 | Fixed: `data.isascii()`. |
| F7 | Eve, Alice | LOW | Two test cases for states that cannot occur; one parametrize value adds no coverage; a repeated `rsplit` helper; SKILL.md does not state the tool-less invariant. | skills/distil-memory/scripts/test_funnel_triage.py:48 | Deferred: cosmetic. |
| V1 | Eve | VERIFY | Nobody has confirmed on a live CLI that the two flags leave the judge with zero tools and zero MCP servers (plugin-registered servers included). | skills/distil-memory/scripts/funnel.py:189 | Not run: agent shells lack the token. Operator check: `printf 'hi' \| claude --print --no-session-persistence --model haiku --tools "" --strict-mcp-config --output-format stream-json --verbose`, then read `tools` and `mcp_servers` in the first `init` event. |
| V2 | Eve | VERIFY | The JSON framing may draw a quoted reply; a quoted word counts as unclassified. | skills/distil-memory/scripts/funnel.py:230 | Not run, same reason. |

Verdict: 9 findings

Tests: 4906 passed, 0 failed, 12 skipped (suite run this cycle, after the fixes above)

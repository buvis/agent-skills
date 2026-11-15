---
prd: docs/dev/project-management/prds/done/00134-empty-sweep-lacks-verification-marker-v1.md
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

# Review: 00134-empty-sweep-lacks-verification-marker-v1

Diff range: `d7299cf..ef83b22`, path-scoped to `skills/sweep-fix/SKILL.md`,
`sweep.py`, `test_sweep_main.py` and `test_sweep_verify_control.py`. Later
PRDs changed the same files; their hunks are in the diff.

codex_rung_guard: fired (1 codex-implemented task(s))

Standalone completion review, run by a session that did not build this PRD.
The build stopped on a red suite on 2026-11-10 because of the same unrelated
distil-memory failure as PRD 00133; the suite is green now. No loop state was
read or written. Consolidation was model-side, not by
`consolidate_findings.py`. No engram pack. The fail-first replay was skipped
by the staging tool; Eve replayed it by hand (with `return False` reverted,
three main-level tests fail).

## Roster

| Lens | Backend / model | Result |
|---|---|---|
| Alice, consensus | native Claude subagent | R12 and R13 fail, rest pass |
| Blake, blind PRD-only | native Claude subagent | B1-B19 pass |
| Bob, doubt | Codex CLI, inlined prompt (model not printed by the runner) | R12 and R13 fail, D1-D5 pass |
| Carl | Copilot CLI, `gemini-3.8-flash` | R1, R12, R13 fail |
| Eve, non-Codex doubt | native Claude subagent, Fable | D1-D5 pass |

Carl's headless run was denied the staged context and diff files. It read the
PRD and the code from the main checkout instead, an older revision of the same
files. Its three findings match other voices and are counted with them.

## Alice

Six findings: `sweep.py` over 800 lines, `main` 52 lines, the tri-state
outcome, no direct unit test of the new `False` return, marker placement, and
a note on unrelated hunks. R12 and R13 fail, rest pass.

## Blake

The must-haves hold: marker line, exit 1, report kept, setup and deadline
paths intact, SKILL.md updated. Four notes: the missing unit test, the
tri-state contract, the marker appended outside `render_report`, the PRD's
evidence command not carried verbatim. B1-B19 pass.

## Bob

Two FIX (`main` length, a one-case parametrize), one KNOWN (older size
overruns).

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
R13: fail
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

`main` 52 lines, `sweep.py` over 800 lines, the missing unit test.

## Eve

Eight FIX, four KNOWN. The code meets the PRD's must-haves. One KNOWN is an
operator decision (K1).

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Consolidated findings

| Ref | Voices | Severity | Issue | File | Disposition |
|---|---|---|---|---|---|
| F1 | Alice, Blake, Carl, Eve | MEDIUM | No unit test asserted `verify_control`'s `False` return; with it reverted every test in the file passed. | skills/sweep-fix/scripts/test_sweep_verify_control.py:27 | Fixed: both-absent test added, dropped assertion restored. |
| F2 | Eve | MEDIUM | No changelog entry for the changed exit status. | CHANGELOG.md | Fixed. |
| F3 | Eve | MEDIUM | SKILL.md told the operator to pick a control that verifies the pattern, which the documented invocation cannot do. | skills/sweep-fix/SKILL.md:59 | Fixed: the text now says a zero-hit sweep never exits 0 with the current repo as control, and names what would. |
| F4 | Alice, Bob, Carl | MEDIUM | `main` was 52 lines. | skills/sweep-fix/scripts/sweep.py:774 | Fixed: 50 lines, same behaviour. |
| F5 | Alice, Carl, Bob, Eve | MEDIUM | `sweep.py` is over the 800-line cap. | skills/sweep-fix/scripts/sweep.py:1 | Deferred: the overrun predates this PRD; clearing it needs a module split. |
| F6 | Alice, Blake, Eve | LOW | `verify_control` returns `None` or `False`, both falsy; the caller needs `is False`. | skills/sweep-fix/scripts/sweep.py:600 | Deferred: behaviour is correct; a comment now marks the call site. |
| F7 | Alice, Blake, Eve | LOW | The marker is appended in `main` after `render_report`, as the last line. | skills/sweep-fix/scripts/sweep.py:816 | Deferred. |
| F8 | Eve | LOW | The inconclusive exit prints nothing on stderr, and the report does not name the control term. | skills/sweep-fix/scripts/sweep.py:817 | Deferred. |
| F9 | Eve, Bob, Blake | LOW | The main regression sits in the setup-failure test module; one-case parametrize; test slop; the PRD's evidence command is not carried verbatim. | skills/sweep-fix/scripts/test_sweep_main_setup_errors.py:119 | Deferred. |
| K1 | Eve | HIGH, operator decision | With the documented invocation (control repo = current repo) a zero-hit sweep can no longer exit 0 at all: term absent gives Unverified, term present gives the broken-pattern abort. A verifiable clean result needs a control redesign. | skills/sweep-fix/SKILL.md:51 | Open: outside this PRD (option A was accepted as written and is met). Needs a new PRD. |
| K2 | Eve | MEDIUM | A rerun flips the diagnosis: the saved report quotes the pattern, and the control-term search does not skip `audit-results`. | skills/sweep-fix/scripts/sweep.py:550 | Open: pre-existing, follow-up. |
| K3 | Eve | LOW | rg `$` never matches before CR, so `$`-anchored patterns miss CRLF files. | skills/sweep-fix/scripts/sweep.py | Open: pre-existing scan behaviour. |

Verdict: 12 findings

Tests: 4906 passed, 0 failed, 12 skipped (suite run this cycle, after the fixes above)

---
head_sha: a3dfcc75ec011ada9dae1a6707d1897fd4bdde32
reviewers: alice, blake, eve, bob
---

## Alice

**00096-brush-hides-pull-request-failures-v1-c1**
| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🟠 | Shape check rejects only dicts. Any non-list JSON from `gh` gets returned as `open_prs` with no warning (e.g. `null`, a bare string/number). CONFIRMED by Victor, resolved in rework. | skills/brush/scripts/collect_facts.py:227 | 1 | CONSENSUS, BLIND, CODEX |
| R2 | [2/4] | ⚪ | Probe-level failure tests use `pytest.raises(Exception)`, too broad. | skills/brush/scripts/test_brush_scripts.py:871 | 1 | CONSENSUS, BLIND |
| R3 | [1/4] | 🟡 | Missing `gh` now raises `RuntimeError` instead of returning `None`, a wording deviation from the PRD. | skills/brush/scripts/collect_facts.py:211 | 1 | CONSENSUS |
| R4 | [1/4] | 🟡 | SKILL.md and the new hygiene-rules.md guard disagree on how an unknown `open_prs` is handled. | skills/brush/SKILL.md:33 | 1 | CONSENSUS |
| R5 | [1/4] | 🟡 | Guard text does not say to read `warnings` before choosing cleanup actions, nor cover malformed values. | skills/brush/references/hygiene-rules.md:81 | 1 | CONSENSUS |
| R7 | [1/4] | ⚪ | Redundant/dead assert in two tests. | skills/brush/scripts/test_brush_scripts.py:967 | 1 | CONSENSUS |
| R-delta-1 | n/a | 🟡 | Missing CHANGELOG entry for the two `fix` commits. | CHANGELOG.md | 1 | DELTA |
| R-delta-2 | n/a | ⚪ | hygiene-rules.md does not say to read `warnings` before choosing cleanup actions. | skills/brush/references/hygiene-rules.md:81 | 1 | DELTA |
| R-delta-3 | n/a | ⚪ | Non-list-reply warning message is untruncated unlike the sibling rc!=0 branch. | skills/brush/scripts/collect_facts.py:228 | 1 | DELTA |

## Blake

**00096-brush-hides-pull-request-failures-v1-c1**
[BLAKE] 🟡 The reply-shape check rejects only a dict. A JSON `null` reply returns `None` with no `open_prs` warning: a silent unknown. Fix: require `isinstance(data, list)`. CONFIRMED, resolved in rework. | File: skills/brush/scripts/collect_facts.py:227 | Task: general
[BLAKE] 🟡 `gh pr list --limit 100` can cut the list short with no signal. | File: skills/brush/scripts/collect_facts.py:215 | Task: general
[BLAKE] ⚪ List items are never checked, e.g. each a dict with `headRefName`. | File: skills/brush/scripts/collect_facts.py:229 | Task: general
[BLAKE] ⚪ An `OSError` from `subprocess.run` is not caught in `gather_prs`, and `main`'s except does not list `OSError`. | File: skills/brush/scripts/collect_facts.py:341 | Task: general
[BLAKE] ⚪ `gather_prs` failure tests use `pytest.raises(Exception)`, too broad. | File: skills/brush/scripts/test_brush_scripts.py:871 | Task: general
[BLAKE] ⚪ The AUTO row for `git branch -D` requires "gh shows merged PR", unreachable from the facts collected. | File: skills/brush/references/hygiene-rules.md:24 | Task: general

## Eve

**00096-brush-hides-pull-request-failures-v1-c1**
FIX:
- Shape validation only rejects dicts; `null`/scalar replies pass through with no warning. CONFIRMED, resolved in rework. — skills/brush/scripts/collect_facts.py:227
- SKILL.md and the new hygiene-rules.md guard disagree on unknown `open_prs` handling. — skills/brush/SKILL.md:33-34
- Guard wording does not say which branches it covers. — skills/brush/references/hygiene-rules.md:81-83
- `gather_prs` raises `ValueError` for malformed JSON but `RuntimeError` for every other failure; tests hide the split with `pytest.raises(Exception)`. — skills/brush/scripts/collect_facts.py:226, test_brush_scripts.py:871,882,890,899,908
- Redundant test and dead assert. — test_brush_scripts.py:1004-1022, :962

VERIFY: (none)

KNOWN:
- Repos without a GitHub remote now yield `open_prs: null` + warning, so every branch delete there is blocked, a design question for a follow-up PRD.
- hygiene-rules.md:24 AUTO precondition "gh shows merged PR" cannot be satisfied from facts (pre-existing).
- test_brush_scripts.py exceeds the 800-line file cap (pre-existing overflow).

Delta (rework range c604d5f..HEAD): prior finding RESOLVED (verified: new shape check rejects any non-list, two new regression tests pin it, narrow run 17 passed/92 deselected, no regression). Raised 3 new findings on the rework diff:
- Missing CHANGELOG entry for the two `fix` commits.
- hygiene-rules.md doesn't say to read `warnings` before choosing cleanup actions.
- Non-list-reply warning message untruncated unlike the sibling rc!=0 branch.

## Bob

**00096-brush-hides-pull-request-failures-v1-c1**
(codex CLI failed twice under the Seatbelt sandbox — substituted with a general-purpose Read-tool reviewer, no retry spent)
[BOB] ⚪ test_brush_scripts.py is 1037 lines, over the 800-line file cap. | File: skills/brush/scripts/test_brush_scripts.py | Task: general
[BOB] ⚪ gather_prs only guards against a dict error payload (at the time of review, before rework fixed it). | File: skills/brush/scripts/collect_facts.py:46 | Task: general
[BOB] ✅ No other issues found

Verdict: 3 findings
Tests: 109 passed, 0 failed, 0 skipped (fast-track batch suite)
codex_rung_guard: not fired

---
prd: docs/dev/project-management/prds/wip/00080-recognize-pipeline-frontmatter-keys-and-the-lane-path-rule-v1.md
review: 1
date: 2026-10-16
head_sha: 7302ca72b1a9326a32933eacdf33a0527e146fb5
codex_thread_id: 01a14648-2daa-7c22-af9c-ea21a5154316
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 8f6d455d
  carl: efb8195d
---

# Review: 00080-recognize-pipeline-frontmatter-keys-and-the-lane-path-rule-v1

Diff range: `bde94d7872861cf65a1e3d11028bd377398dba18..7302ca72b1a9326a32933eacdf33a0527e146fb5`

codex_rung_guard: not fired

pack: failed (engram pack exit 1: not inside a registered repo; run `gita add <worktree>`)

Mechanical checks: 0 `[MECH]` findings (4 test functions checked in 1 test file; replay: 4 touched tests ran, 4 failed against base, 0 passed, so every new test pins the change).

## Review Summary

Reviewed: 4 completed tasks
PRDs checked: 00080-recognize-pipeline-frontmatter-keys-and-the-lane-path-rule-v1

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (first run unusable: the codex sandbox denied every read with `sandbox_apply: Operation not permitted` and returned all-fail R verdicts; first dispatch row 7360cb93 closed `format-invalid`; re-dispatched as the inlined retry, row 8f6d455d, `after one retry (inlined)`)
- Carl: ✅ Available (`backend=copilot model=gemini-3.8-flash`)

## Consolidated Findings

3 findings, all ⚪ Low, all from Blake. No 🔴, 🟠 or 🟡.

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [1/4] | ⚪ | The only deviation is the Nice-to-have frontmatter-tuning suggestion (`lane: solo` / `lane: fast-track`) in the review-prd-backlog lens B bullet. It is optional in the spec, so I count it as in scope, not creep. | skills/review-prd-backlog/SKILL.md:85 | general | BLAKE |
| R2 | [1/4] | ⚪ | `validate_skill.py skills/review-prd-backlog` exits 0 with a warning: the description is 251 characters and only the first 250 are shown. The diff does not touch the description, so the warning predates this change and does not block anything. | skills/review-prd-backlog/SKILL.md | general | BLAKE |
| R3 | [1/4] | ⚪ | The branch carries autopilot housekeeping files (`deferred/202610162125-deferred.json`, two `dispatch-metrics.jsonl` files) and the PRD file move. These are pipeline state, not skill changes, and the spec does not mention them. | docs/dev/project-management/autopilot/deferred/202610162125-deferred.json | general | BLAKE |

## Alice

Consensus lens, implementation-aware. No issues found.

```
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
```

## Blake

Blind lens, PRD-only. 3 ⚪ observations (rows R1-R3), no spec violation. Compared every SKILL.md and CHANGELOG string line by line against the PRD's verbatim text; ran the new prose test plus `test_check_links.py` (16 passed) and `validate_skill.py` on both skills (OK; review-prd-backlog with the pre-existing 251-char description warning).

```
B1: pass
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

## Bob

Doubt lens + de-slop (codex), `after one retry (inlined)`. No issues found. FIX: (none). VERIFY: (none). KNOWN: (none).

```
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
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

UI/design specialist, generalist here (no frontend in the diff). `backend=copilot model=gemini-3.8-flash`. No issues found. Ran the new prose test (4 passed) and `validate_skill.py` on both skills.

```
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
```

Test note: the one failure is `tests/test_conftest_fixtures.py::test_armed_directory_refuses_a_childs_stat`, outside this diff and failing at the base commit too (recorded at build time).

Verdict: 3 findings
Tests: 3804 passed, 1 failed, 6 skipped (suite run this cycle)

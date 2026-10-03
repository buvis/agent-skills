---
prd: dev/local/prds/wip/00022-node-ci-and-install-docs-v1.md
review: 1
date: 2026-09-06
head_sha: 927e70003ace82fdd0b03c1050ad42b8cf0c3d6f
codex_thread_id: 01a0786d-e345-7411-a685-ab20332508c6
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00022-node-ci-and-install-docs-v1

Diff range: `f8c7bfcb4d064ac3852279b6c3076e40ea212667..927e70003ace82fdd0b03c1050ad42b8cf0c3d6f`

codex_rung_guard: not fired

pack: failed (`engram pack` exit 1 — "not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv"). `{PACK_FILE}` and `{PACK_FINDINGS}` were substituted with `(no pack available this cycle)` in every prompt that takes them. The review is degraded on retrieval context, not invalid.

## Review Summary

Reviewed: 4 completed tasks
PRDs checked: 00022-node-ci-and-install-docs-v1

Scope note: this is a **full** cycle-1 review over the PRD's whole work range. `gather-context.sh` was invoked with `--since <work_start_sha>` rather than bare, because this repo commits straight to `master`, so the script's default branch-base diff (`git diff master` evaluated from `master`) produced an empty diff and an empty changed-file list. The `--since` form yielded the correct 80-line diff across 4 files.

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind lens — PRD only)
- Bob: ✅ Available (codex, doubt + de-slop lens; thread `01a0786d-e345-7411-a685-ab20332508c6`)
- Carl: ✅ Available (gemini-run: `backend=copilot model=gemini-3.8-flash`, exit 0, non-empty output)

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟡 | FIX — The fresh-clone promise is still false for the brief-portfolio Tests block: `test:browser` runs without an executable Chromium-install step; the trailing `npx playwright install chromium` is only a comment, and the lockfile shows Playwright has no install script. Insert `npm --prefix ~/.agents/skills/brief-portfolio/app exec -- playwright install chromium` before `test:browser`. | skills/brief-portfolio/SKILL.md:137 | 1 | BOB |
| [1/4] | ⚪ | Cannot statically verify: VERIFY — run the node job's four npm commands on a clean Node 24 Ubuntu checkout and confirm every command exits 0; runtime execution was prohibited. | .github/workflows/ci.yml:118 | 4 | BOB |

No 🔴 Critical and no 🟠 High findings. Both rows are Bob's alone at 1/4 consensus; the other three lenses returned clean.

### Mechanical blocks

- **Mechanical facts**: all four changed files skipped (non-python). No countable claim to contradict.
- **Tautological test shapes**: 0 test functions in 0 test files — nothing to absorb.
- **Fail-first replay**: `replay: skipped (the diff touches no test function)` — nothing to absorb.

No `[MECH]` lines were produced, so no finding was added or amended from these blocks.

### Carry-forward

Cycle 1: no previous-cycle check queue exists. Nothing carried forward.

### Verification-check queue

**Not written this cycle.** Eve did not run (the codex doubt-roster guard did not fire, and `doubt_reviewer` resolved to `codex`), so no lens emitted FIX/VERIFY/KNOWN buckets — Bob's persona defines none, and `source: "bob"` is reserved. Bob's inline `VERIFY —` item is recorded above as an ordinary finding. It would not have been queued in any case: **not queued: command shape** — "run the four npm commands on a clean Node 24 Ubuntu checkout" names an environment, not one runnable local command line.

## Alice

`[ALICE] ✅ No issues found`

All acceptance criteria verified: YAML parses, `rg -n "^  node:"` and `rg -n "actions/setup-node@"` each match one line, `rg -c "npm --prefix skills/"` prints 4, `rg -c "... install"` prints 2 in each SKILL.md with the install line first in the `## Tests` fence. Both `npm --prefix skills/brief-portfolio/app test` and `npm --prefix skills/debrief-meeting/app test` run from the repo root: 44/44 and 48/48 pass, both exit 0. `scripts/check_changelog_skills.py` exits 0 against the new CHANGELOG entries. Git log for the range confirms all 4 commits match the task descriptions exactly. The CI job mirrors the existing `test`/`shell`/`lint` job shape, and `actions/setup-node@v6` pinning matches the tag-pin style already used for `actions/checkout@v7` / `astral-sh/setup-uv@v10.0.1`. No scope creep, no dead code, no TODOs/placeholders, no secrets.

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

`[BLAKE] ✅ No issues found`

Blind lens — spec only, found the code himself. Checked every task's stated acceptance command literally and all match. Both apps have committed `package-lock.json`, so the `npm ci` steps are valid. The two path styles (SKILL.md `~/.agents/skills/...` versus the workflow's checkout-relative `skills/...`) are kept distinct as the PRD's risk section required. Git history shows surgical diffs scoped exactly to the files the PRD names, with matching CHANGELOG entries and no unrelated changes.

Blake notes that B3, B9-B14, B16 and B17 are vacuously satisfied: a docs+CI PRD has no auth, secrets, database, migration, rate-limiting or API surface, and the PRD defines no Phase 2 tasks and no Phase 3. He passes them because the PRD specifies no such behavior and none was introduced.

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

Doubt + de-slop lens (codex, static-only sandbox). Two findings, both carried into the table above.

```
[BOB] 🟡 FIX — The fresh-clone promise is still false for the brief-portfolio Tests block: `test:browser` runs without an executable Chromium-install step; the trailing `npx playwright install chromium` is only a comment, and the lockfile shows Playwright has no install script. Insert `npm --prefix ~/.agents/skills/brief-portfolio/app exec -- playwright install chromium` before `test:browser`. | File: skills/brief-portfolio/SKILL.md:137 | Task: 1
[BOB] ⚪ Cannot statically verify: VERIFY — run the node job's four npm commands on a clean Node 24 Ubuntu checkout and confirm every command exits 0; runtime execution was prohibited. | File: .github/workflows/ci.yml:118 | Task: 4
```

```
R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
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

Bob's `R9: fail` ("Implementation matches PRD feature behavior exactly") rests entirely on his Medium finding above. The decision gate discarded that finding as out of PRD scope after verifying it against the files (see Decision gate below), so R9 fails on a premise the gate did not accept. His verdict lines are recorded verbatim and unmodified.

## Carl

`[CARL] ✅ No issues found`

Frontend & design specialist lens, run as a generalist here (no UI surface in the diff). Carl executed the suites himself: `uv run pytest`, both skill validators, `git diff --check`, both npm test suites, the YAML parse, `scripts/check_changelog_skills.py`, and `python3 bin/braid.py --check`. He notes that adding the `node` job means both frontend app suites (including the accessibility and smoke suites) now gate CI, and that documenting `npm install` in both SKILL.md files prevents module-resolution failures on fresh checkouts.

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

## Decision gate (cycle 1)

Convergence test: **no unresolved CRITICAL or HIGH finding**. Zero of either were raised, so the cycle converges. Medium and Low never block convergence; they are swept, not dropped. Both rows were verified and then discarded with a reason, so the sweep's selection is empty.

**Finding 1 (🟡 Medium, 1/4) — discarded, out of PRD scope.** Verified directly against the files rather than accepted or dismissed on assertion:

- `skills/brief-portfolio/app/package.json` defines `test` and `test:browser` as **separate scripts** — `test` is `node --test src/lib/derive.test.js smoke.test.js smoke.a11y.test.js` (no browser), `test:browser` is `playwright test`.
- The PRD's contract command is `npm --prefix ... test`, whose failure mode was `ERR_MODULE_NOT_FOUND: Cannot find package 'jsdom'` — a node **module** install, fixed by the added line.
- CI runs only `test`: the four `npm --prefix skills/` lines at `ci.yml:120-129` contain no `test:browser`.
- The `test:browser` line already documents its own remedy inline, on the same line, as a one-time step: `# real chromium on a file:// page; once: npx playwright install chromium`.
- Bob's proposed fix would make every run of the Tests block attempt a ~150 MB chromium download, which is worse for the reader than the existing "once" note.

**Finding 2 (⚪ Low, 1/4) — discarded, not a defect.** This is the sandbox-limitation line `agents/bob.md` mandates whenever a criterion needs runtime verification. The other three lenses each ran both suites at this HEAD (44/44 and 48/48, exit 0), as did the work phase's recorded verification at the same sha. The residual part — behavior on a hosted Node 24 Ubuntu runner — cannot be checked by any local command, and the PRD's own Risks section assigns it to human follow-up: "read the first GitHub Actions run after merge and open a separate PRD for anything that only appears on a hosted runner. Nothing here is gated on that run."

Both discards are recorded in `dev/local/reviews/00022-node-ci-and-install-docs-v1-ledger.json` so they are not re-argued in a later cycle.

**Tail sweep: skipped** — zero actionable Medium/Low findings remain after the two discards.

### Acceptance criteria re-verified by the gate

Run directly at `927e700`, not taken on a reviewer's word:

| Check | Result |
|-------|--------|
| `rg -c "brief-portfolio/app install" skills/brief-portfolio/SKILL.md` | `2` ✓ |
| `rg -c "debrief-meeting/app install" skills/debrief-meeting/SKILL.md` | `2` ✓ |
| install line first inside both `## Tests` fences | ✓ (both read directly) |
| `uv run python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"` | `YAML OK`, exit 0 ✓ |
| `rg -n "^  node:" .github/workflows/ci.yml` | one line (110) ✓ |
| `rg -n "actions/setup-node@" .github/workflows/ci.yml` | one line (115) ✓ |
| `rg -n "npm --prefix skills/" .github/workflows/ci.yml` | four lines (120, 123, 126, 129) ✓ |
| node job shape | `ubuntu-latest`, `actions/checkout@v7`, `actions/setup-node@v6`, `node-version: 24` ✓ |

All three PRD success metrics are met.

## Follow-up Tasks Created

✅ None. No follow-up tasks needed: no CRITICAL/HIGH findings, and both Medium/Low rows were discarded with verified reasons.

Verdict: 2 findings
Tests: 1165 passed, 0 failed, 5 skipped (reused from last-verification.json at 927e70003ace82fdd0b03c1050ad42b8cf0c3d6f)

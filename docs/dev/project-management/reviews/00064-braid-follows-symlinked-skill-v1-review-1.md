---
prd: dev/local/prds/wip/00064-braid-follows-symlinked-skill-v1.md
review: 1
date: 2026-09-26
head_sha: ae7b6fdea9a8b307ebbd72724ebd67ecd3fb4247
codex_thread_id: 01a0de28-c90d-7a43-b58a-a2febf25879c
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00064-braid-follows-symlinked-skill-v1

Diff range: `0d675fc3758768086799b7291e20e46585d4a0e2..ae7b6fdea9a8b307ebbd72724ebd67ecd3fb4247`

codex_rung_guard: not fired

pack: unavailable (`engram pack` exited 1: "not inside a registered repo; register it in
~/.config/gita/repos.csv"). Every prompt that takes `{PACK_FILE}` / `{PACK_FINDINGS}` received the
sentinel `(no pack available this cycle)`. The failure is deterministic (a registration gap, not a
transient error), so the one permitted retry was skipped as pointless and recorded instead.
Degraded, not invalid — the pack is additive retrieval context.

diff-base note: `gather-context.sh`'s branch-base detection resolved to `master`, and this repo
commits straight to `master`, so its default `git diff master` would have been **empty**. The script
was run with `--since 0d675fc3758768086799b7291e20e46585d4a0e2` to pin `state.work_start_sha`, which
is the range the skill mandates under autopilot. Despite the script labelling that mode
"incremental", this is a **full cycle-1 review** of the PRD's whole work range; the context file's
scope line was corrected to say so, and no reviewer was given the incremental-review instruction.

## Review Summary

Reviewed: 1 completed task (task 1, 3 commits: `b1b546a`, `4ae54d5`, `ae7b6fd`)
PRDs checked: 00064-braid-follows-symlinked-skill-v1

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind lens — PRD-only)
- Bob: ✅ Available (codex, doubt lens D1-D5 + de-slop, first run, no retry needed)
- Carl: ✅ Available (gemini via `copilot` backend, model `gemini-3.8-flash`, UI/generalist lens)

Eve did not run: the codex doubt-roster guard did not fire (task 1's only attempt records
`implementor: "claude"`), and `state.doubt_reviewer` is `codex`, so the fifth lens was not activated.

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟡 | Symlink guard lands after the pre-existing `is_dir()` check, not before it as the PRD contract states verbatim ("continue past any candidate for which candidate.is_symlink() is true, before the is_dir() check"; acceptance criterion says "at the top of the per-candidate loop") — no functional difference since `is_dir()` already returns true through a symlink-to-directory (per the PRD's own Problem section), so ordering doesn't change any outcome; confirmed by the passing test and a manual --dry-run repro | src/agent_skills_braid/cli.py:134 | 1 | ALICE, BOB |
| [1/4] | ⚪ | Cannot statically verify: `uv run pytest tests -q` reports zero failures | N/A | 1 | BOB |
| [1/4] | ⚪ | Cannot statically verify: the dry-run reproduction emits no `WOULD LINK` line for the symlinked skill | N/A | 1 | BOB |

No 🔴 Critical, no 🟠 High. One 🟡 Medium and two ⚪ Low; none blocks convergence.

The consolidator merged Alice's ⚪ and Bob's 🟡 into the single row above — its own log line records why:
`row 1 merged citations that matched only after suffix stripping: src/agent_skills_braid/cli.py:134 ~
src/agent_skills_braid/cli.py:135`. Two reviewers describing one defect at one file is real 2/4
agreement, and the merged row keeps the higher severity (🟡). **Blake independently traced the same
ordering point and declined to raise it**, having confirmed functional equivalence across all three
symlink cases; his silence is a third opinion on severity, not a fourth vote for the finding.

Mechanical test checks contributed no findings: the tautological-shapes scan flagged nothing across
15 test functions, and the fail-first replay is clean (1 touched test ran, 1 failed against base,
0 passed — the regression test does pin this change). No `[MECH]` line existed to absorb.

No previous-cycle check queue to carry forward (this is cycle 1).

## Alice

`[ALICE] ⚪ Symlink guard lands after the pre-existing is_dir() check, not before it as the PRD contract states verbatim | File: src/agent_skills_braid/cli.py:134 | Task: 1`

Consensus lens. Read the diff and `src/agent_skills_braid/cli.py:124-149` plus
`tests/test_braid.py:1-40,300-337`, and confirmed the guard is the exact literal the PRD contract
names, that `discover_inventory`'s signature is unchanged, and that its single caller (`run()`,
`src/agent_skills_braid/cli.py:338`) is unaffected. Ran `uv run pytest tests/test_braid.py -q`
(12 passed, 3 xfailed, 0 failing) and re-ran the target test alone to confirm it passes with no
marker. Read the test hunk directly: the xfail decorator and its orphaned comment are fully removed
with correct PEP-8 spacing, and the assertion is tightened from `"evil" not in inventory` to
`inventory == {"kept": kept.resolve()}`, which pins the exact surviving inventory rather than only
the excluded entry's absence. **Built a scratch reproduction outside the repo** (a real `kept` dir
plus an `evil` symlink to an external directory carrying a matching `SKILL.md`) and ran
`braid --dry-run` against a throwaway `$HOME`: `kept` is listed, `evil` appears nowhere. Cited the
mechanical-facts block for the size claims: `discover_inventory` 26 lines, `cli.py` 513 lines,
`test_braid.py` 353 lines — all inside the 50/800-line limits; the two functions over 50 lines
(`_sync_links` 58, `main` 55) are pre-existing and untouched. She judged her own finding a literal
wording mismatch with zero behavioural consequence and therefore did **not** fail R9.

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

## Blake

`[BLAKE] ✅ No issues found`

Blind lens: given the PRD alone, Blake located `discover_inventory`
(`src/agent_skills_braid/cli.py:124`) and the named test (`tests/test_braid.py:324`) himself, and
confirmed the final state matches the spec. He verified the target test carries no `@pytest.mark.xfail`
decorator, and correctly identified the two neighbouring xfailed tests (`tests/test_braid.py:281`,
`:303`) plus a third (`:308`) as unrelated pre-existing markers left untouched. Ran
`uv run pytest tests/test_braid.py -v` (target test PASSED, 12 passed, 3 xfailed) and
`uv run pytest tests -q` (155 passed, 3 xfailed, 0 failed). **Executed the PRD's reproduction live**
in a scratch tree at `/private/tmp/blake-repro-00064`: 76 real `WOULD LINK` lines for the repo's own
skills and zero lines mentioning `evil` or `outside`, exit 0, nothing written.

His hostile-audit scope checks are worth keeping: (1) `discover_inventory` has exactly one call site,
shared by `--dry-run`, `--check` and sync, so the fix covers all three modes as the PRD requires;
(2) `rg` found no second definition or plugin-twin copy left unpatched; (3) the final state carries no
containment/resolved-path check, matching the PRD's explicit "Bounded" rationale — the `ae7b6fd`
commit removed one the implementor had added; (4) he traced the check order across all three symlink
cases (to a dir, to a non-dir, broken) and confirmed the two checks are functionally equivalent in
either order. No new dependencies, flags, or parameters.

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

## Bob

`[BOB] 🟡 discover_inventory dereferences each symlink via is_dir() before applying the symlink guard, contrary to the PRD's required ordering | File: src/agent_skills_braid/cli.py:135 | Task: 1`
`[BOB] ⚪ Cannot statically verify: uv run pytest tests -q reports zero failures | File: N/A | Task: 1`
`[BOB] ⚪ Cannot statically verify: the dry-run reproduction emits no WOULD LINK line for the symlinked skill | File: N/A | Task: 1`

Doubt + de-slop lens, codex, first run (no retry). He is the only reviewer to fail a rubric rule
(R9), on the ordering mismatch.

```
FIX:
- The symlink guard follows the dereferencing `is_dir()` call — src/agent_skills_braid/cli.py:135 — move `if candidate.is_symlink(): continue` above the existing name/`is_dir()` condition

VERIFY:
- Full test suite result — run `uv run pytest tests -q`
- Required CLI reproduction — create the specified external-target symlink, run `uv run braid --dry-run --source srcA`, and confirm stdout has no `WOULD LINK` entry for `evil`

KNOWN:
- (none)
```

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

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

**Bob's VERIFY bucket, and why he has one.** His assembled prompt carried the doubt-lens sections of
`agents/eve.md` — the two lenses, the FIX/VERIFY/KNOWN categorisation, and the D1-D5 verdicts — so
the buckets above are his own output, not an invention of this consolidation. The categorisation
section travels with the rubric deliberately: D1 and D5 grade the buckets, so without them both rules
would be unevaluable and therefore automatic failures.

- **Queued:** `uv run pytest tests -q` is one runnable project verification command, so it was written
  to `dev/local/reviews/00064-braid-follows-symlinked-skill-v1-checks-1.json` with `source: "bob"`.
- **not queued: command shape** — the CLI-reproduction item needs scratch-tree setup plus a stdout
  assertion, which is not the single-runnable-command shape the queue accepts. It stays an ordinary
  finding and is classified at the decision gate. Recording the refusal here rather than dropping it
  silently.

Both of Bob's ⚪ items are sandbox limits rather than defects, and **both were already answered by
live evidence from three other lanes in this same cycle**: Alice, Blake and Carl each ran the suite,
and Alice and Blake each executed the dry-run reproduction independently in separate scratch trees,
both reporting no `WOULD LINK` line for the symlink.

## Carl

`[CARL] ✅ No issues found`

Backend: gemini via the `copilot` CLI, model `gemini-3.8-flash`. No frontend surface in this diff, so
Carl reviewed as a generalist. He read the context and diff, ran the full suite
(`uv run pytest`), ran `uv run pytest tests/test_braid.py -q`, searched for remaining `xfail` markers
in `tests/test_braid.py`, read `tests/test_braid.py:250-310` and `src/agent_skills_braid/cli.py:120-155`,
ran the target test alone with `-v`, inspected `git show ae7b6fd`, and checked `git status` for a clean
tree. He raised nothing.

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

## Follow-up Tasks Created

None at this step. The one actionable finding (the guard's position relative to the `is_dir()` check)
is swept by the decision gate's single `[D1] Tail sweep` task rather than duplicated here — see the
decision gate's record. Bob's queued check is routed to verification and correctly creates no task;
his unqueued reproduction item is a verification request rather than a fixable defect.

Verdict: 3 findings
Tests: 3474 passed, 0 failed, 6 skipped (reused from last-verification.json at ae7b6fdea9a8b307ebbd72724ebd67ecd3fb4247)

The reused record is the work phase's own mandatory suite run at this exact HEAD
(`ae7b6fdea9a8b307ebbd72724ebd67ecd3fb4247`, one command `uv run pytest`, exit 0), so no suite was
re-run for this review. Three reviewers nonetheless ran pytest themselves this cycle and none reported
a failure: Alice `tests/test_braid.py` (12 passed, 3 xfailed), Blake `tests` (155 passed, 3 xfailed,
0 failed), Carl the full suite.

## Post-sweep addendum (same cycle, after convergence)

The converged cycle's Tail sweep fixed the one actionable Medium finding. It ran on the **micro lane**
(`references/rework-mode.md`): one non-CRITICAL finding in one file, tree clean at claim time, so the
orchestrator made the edit with the Edit tool and no Tess/Ivan/Devon dispatched. Two commits:

- `c8e3230` `refactor(braid): move the symlink guard above the is_dir() check (task 2)` — the two-line
  move, 2 insertions / 2 deletions, net 0 lines in 1 file (well under the lane's 30-line ceiling).
- `7353bcf` `docs(braid): add the CHANGELOG entry for the symlinked-skill skip` — see below.

`discover_inventory`'s loop now reads `if candidate.is_symlink(): continue` first, matching the PRD's
wording in both its Solution section and the task acceptance criterion. Behaviour is unchanged, as all
three reviewers predicted: the braid test file reports the identical **12 passed, 3 xfailed** before and
after, and `braid --check` reports `0 linked, 76 current, 20 ignored, 0 removed, 0 backed up, 0 drift` —
the same 76 current as the pre-sweep run, which is direct evidence no real skill left the inventory.

**A CHANGELOG gap the four lenses missed, fixed under a standing rule.** No reviewer raised it, but the
PRD's own `fix(braid)` commits (`4ae54d5`, `ae7b6fd`) never touched `CHANGELOG.md`, and this repo's
`rules/changelog.md` makes an entry BLOCKING for any commit with a user-visible change — which this PRD
squarely is (a symlinked entry under a source's `skills/` is no longer inventoried, and the drop is
silent). The entry was added under `[Unreleased]` / `### Fixed` as its own `docs(braid)` commit rather
than folded into the refactor, matching this repo's own precedent (`0bb5d9a`). Recording it here because
it is scope this cycle added on its own initiative, not something the findings asked for.

Gates on the sweep task: `style_gate: clean`, `split_hygiene: skipped:no-tests`,
`self_deslop: skipped:trivial`, `red_check: n/a:micro-lane`, `reflow` not flagged.
Pat (per-task reviewer, Sonnet lane) reviewed `ae7b6fd..7353bcf` and returned `NO FINDINGS` plus
`CLOSURE | resolved` for the swept finding.

**Queued check ran and passed:** `verify_check: uv run pytest tests -q -> exit 0` (155 passed,
3 xfailed), written back to `00064-braid-follows-symlinked-skill-v1-checks-1.json` as
`"result": {"exit": 0}`. No verify-escape, and no sweep-escape (Pat raised nothing).

Full suite at the settled HEAD `7353bcf`: **3474 passed, 0 failed, 6 skipped, 4 xfailed** in 291s.
The `Verdict:`/`Tests:` lines above are deliberately left as they were — they describe the revision the
four lenses actually reviewed (`ae7b6fd`). This addendum records the later state without rewriting that
history.

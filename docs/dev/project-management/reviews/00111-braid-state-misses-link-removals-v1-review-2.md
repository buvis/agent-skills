---
prd: docs/dev/project-management/prds/wip/00111-braid-state-misses-link-removals-v1.md
review: 2
date: 2026-10-29
head_sha: 388ce5be5191c83068feffb1d717d197a4fcd8ae
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: ba89afb5
  carl: ee053fe3
---

# Review: 00111-braid-state-misses-link-removals-v1

Diff range: `1bb1d6b73c861cbe849987af410c00ab7e7525e2..388ce5be5191c83068feffb1d717d197a4fcd8ae`

codex_rung_guard: not fired

pack: ok

## Review Summary

Incremental review of cycle 1's rework (commit e0aef44, the `[D1]` fix for
cycle-1 R1). 2 completed tasks.
PRDs checked: 00111-braid-state-misses-link-removals-v1.md

### Agent Status

- Alice: ✅ Available (consensus lens, legacy engine)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (doubt lens, codex; resumed thread 01a1872b; D1-D5 emitted).
  `--emit-thread-id` wrote an empty sidecar this cycle, so no `codex_thread_id`
  is stamped above and cycle 3 (if any) would start a fresh codex session.
- Carl: ⚠️ Unavailable: gemini-run backend=copilot model=gemini-3.8-flash exited
  1, "You have exceeded your monthly quota". Retried once per retry policy, same
  failure. Exit 1, not exit 4, so no batch latch was recorded.
- Eve: ⏸️ Disabled: resolved doubt reviewer is `codex` and no task was
  implemented by codex, so the codex doubt-roster guard did not fire.

Mechanical checks: the tautological-shape scan found no `[MECH]` lines across 16
test functions in 1 file. The fail-first replay again collected 0 touched tests
(the test file could not be collected against base `1bb1d6b7`), so it produced
no evidence either way.

Test-gate note (fail loud): `uv run pytest` ran once this cycle at HEAD on a
clean tree and exited 0, but the autopilot gate parser expects a
`PASS n FAIL n SKIP n EXIT n` line that this project's suite does not print, so
it reported `counts unavailable` and wrote no `last-verification.json`. The
counts in the `Tests:` line below were read from the pytest summary at line 200
of `docs/dev/tmp/gate-00111-c2.log` (`4134 passed, 9 skipped` in 422.65s), not
parsed by the gate. The first `review-stage` call of this session also passed
the wrong gate command (`dev/bin/release-checks`, which this repo does not
have, exit 127); it was re-staged with `uv run pytest`.

Consolidation note (fail loud): `consolidate_findings.py` merged several
same-file citations after suffix stripping, which folded the "empty first run
writes no state file" finding (raised independently by Alice, Bob and Blake)
into R1. That finding is a separate defect, so it is restored below as **R13**
with its true 3/3 consensus rather than left inside R1's row.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/3] | 🔴 | Per-removal persist over-claims: `on_removal(managed)` hands `persist` a snapshot that already excludes every stale entry the loop has not yet processed, so a completed removal persists state that drops the ownership record of a link still on disk - including the hand-changed path the next iteration refuses. Reproduced (union stage): skills aa/bb/cc, sources aa+bb deleted, union `bb` replaced by a real directory -> `REMOVE .../skills/aa`, then `refusing to clean changed managed path: .../skills/bb`, and `.braid-state.json` union is `['cc']` (bb's record gone); the NEXT sync completes with no refusal at all, and `_report_orphan_links` skips non-symlinks (cli.py:455), so the hand-changed directory is silently unmanaged forever. Same in the Claude stage: `hosts.claude` becomes `['cc']` and the second run no longer refuses. Breaks the must-haves "without discarding unaffected ownership records" and "Preserve refusal for changed managed paths", and is a regression vs cycle 1, where the refused path kept its record. Fix: track `pending = {n: t for n, t in previous.items() if n not in desired}`, pop each name as it is handled, and call `on_removal({**pending, **managed})` | src/agent_skills_braid/_run_stages.py:258 | 2 | ALICE, BLAKE, BOB |
| R2 | [2/3] | 🟠 | The CI `lint` job is red at HEAD: `uv run ruff check` fails with I001 (this cycle's expanded import block is unsorted - `_present` before `_points_to`) and UP035 (`Callable` imported from `typing`; cli.py:12 uses `collections.abc`), and `uv run ruff format --check` fails on cli.py (missing blank line after the local import, and the 12-argument `run_kiro_stage` call). Control: the pre-PRD cli.py from `6091e02` passes both checks, so this is new with this PRD. Both commands are gates in .github/workflows/ci.yml:154 | src/agent_skills_braid/_run_stages.py:12 | general | ALICE, BLAKE |
| R13 | [3/3] | 🟡 | Empty first-run initialization writes no state file at all: with an empty inventory and `project_claude=False, project_kiro=False`, every candidate equals the loaded empty state, so `persist` skips and `.braid-state.json` is never created, where the pre-change code always wrote it in SYNC mode. Breaks the must-have "Preserve real state-only changes, first-run initialization, and host/Kiro state". Cycle-1 R8, still unfixed and with no ledger disposition. Track whether the state file existed and force its initial write in sync mode. | src/agent_skills_braid/_run_stages.py:39 | 1 | ALICE, BOB, BLAKE |
| R3 | [2/3] | 🟡 | Cycle-1 finding R9 is still unfixed and has no ledger disposition: `run_claude_stage` and `run_kiro_stage` annotate `hosts: dict[str, str]`, but the parameter holds link maps and is passed into `State`, whose field is `dict[str, dict[str, str]]` (cli.py:82). Change both annotations | src/agent_skills_braid/_run_stages.py:83 | general | ALICE, BOB |
| R4 | [1/3] | 🟡 | Dead optionality: `on_removal: Callable[[dict[str, str]], None] \| None = None` plus the `if on_removal is not None` guard exists for no caller - all three stages pass it. Make the keyword required and call it unconditionally | src/agent_skills_braid/_run_stages.py:154 | 2 | ALICE |
| R5 | [1/3] | 🟡 | The intra-stage regression uses only two stale names with the refused one last, so it cannot observe a discarded unaffected record; it also never asserts that `bb` stays recorded. | tests/test_braid_check.py:268 | Phase 0 | BLAKE |
| R6 | [1/3] | ⚪ | `_link_desired` and `_remove_stale_links` take `managed` as a caller-owned dict they mutate in place. Having `_link_desired` return it and `_remove_stale_links` take it read-only keeps both functions under the line limit and matches the repo's immutability preference | src/agent_skills_braid/_run_stages.py:197 | 2 | ALICE |
| R7 | [1/3] | ⚪ | The new same-stage regression asserts only that `bb` survives on disk, not that it keeps its ownership record - which is exactly why finding R1 shipped green. Add `assert "bb" in state["union"]` (and the host-stage twin) with the fix | tests/test_braid_check.py:286 | 2 | ALICE |
| R8 | [1/3] | ⚪ | The autopilot state commits in this range swept in unrelated working-tree files: 5dffe76 added docs/dev/project-management/plans/skill-migration-bundle-plan.md and PRDs 00135-00137, and 2329597 committed this PRD file as zero bytes (its 119 lines are still uncommitted). A tracked empty PRD is in backlog | docs/dev/project-management/prds/backlog/00138-brush-reinterprets-absolute-paths-v1.md | general | ALICE |
| R9 | [1/3] | ⚪ | `hosts` is annotated `dict[str, str]` in both host stage helpers but holds `dict[str, dict[str, str]]`; no type checker runs, so the wrong annotation just misleads. | src/agent_skills_braid/_run_stages.py:83 | Phase 0 | BLAKE |
| R10 | [1/3] | ⚪ | The Claude stage's intermediate and final persists write `kiro=previous_state.kiro` even when `select_kiro` chose a new registration; the Kiro stage corrects it, so only a failure landing between the two loses the enrollment (same as before this PRD). | src/agent_skills_braid/_run_stages.py:104 | Phase 0 | BLAKE |
| R11 | [1/3] | ⚪ | Pre-existing: `_remove_owned_link`'s `unlink`/`rmdir` and `_backup`'s `shutil.move`/`mkdir` are unguarded, so an OSError there escapes `entrypoint()`'s BraidError handler as a raw traceback, now inside the persistence path. | src/agent_skills_braid/cli.py:432 | general | BLAKE |
| R12 | [1/3] | ⚪ | A semantically equal but unnormalized state file (duplicate Kiro agent names, odd key order) is now never rewritten, so it keeps its unnormalized content indefinitely. | src/agent_skills_braid/_run_stages.py:39 | Phase 0 | BLAKE |

### Auto-dismissed (ledger)

- [BLAKE] 🟡 "No state-write attempt for unchanged content" is never asserted. The test infers it from `chmod 0o500` and skips on Windows, so it is vacuous under root and cannot distinguish "no write attempted" from "write succeeded". The PRD asked for portable permission fixtures. | File: tests/test_braid_check.py:292 — single-voice
- [BLAKE] 🟡 `src/agent_skills_braid/_run_stages.py` is outside the PRD's declared implementation surface, and `cli.py` no longer exports `_sync_links` as the Module section requires. The new module also binds `_write_state` at import time, so `monkeypatch.setattr(cli, "_write_state", ...)` silently misses `persist`. | File: src/agent_skills_braid/_run_stages.py:14 — single-voice
- [BLAKE] ⚪ Kiro links and enrollment now persist before `sync_kiro_agent` can refuse, so a refused agent edit leaves enrollment recorded. Beyond the spec; next run re-detects the unconfigured agent. | File: src/agent_skills_braid/_run_stages.py:137 — single-voice; the reviewer judged it benign because the next run re-detects the unconfigured agent

## Alice

Consensus lens, implementation-aware, legacy engine. Two 🟠 (one consolidated to
🔴 at 3/3 consensus), three 🟡, three ⚪. Verified cycle-1 R1 as half-fixed: the
completed removal is now persisted and pinned by a non-tautological test, but
the fix introduced the R1 regression above. Cycle-1 R8 and R9 confirmed still
unfixed and undispositioned. Narrow run at HEAD:
`uv run pytest tests/test_braid.py tests/test_braid_check.py` → 62 passed.
Mechanical limits hold: longest function 42 lines (`_sync_links`); cli.py 708
lines, `_run_stages.py` 258.

R1: fail
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

## Blake

Blind lens, PRD-only. One 🔴, two 🟠, three 🟡, six ⚪. Located the code himself
and reproduced the R1 regression with aa/bb/cc in a temporary root, measuring
both consequences: a permanently unowned orphan link, and a refusal that stops
being reported after the record is dropped (`--check` then reports 0 drift). He
also ran the CI lint gate and found it red. He confirmed the unchanged-sync
no-write behaviour by spying `_write_state` through both module bindings, and
confirmed `--check` / `--dry-run` stay read-only. He did not re-run the full
suite (the gate's counts were supplied to him).

B1: fail
B2: pass
B3: fail
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
B14: fail
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Doubt lens (codex, resumed thread), rubric D1-D5 plus de-slop. One 🟠
(consolidated to 🔴), two 🟡 — all three agreeing with Alice and Blake. FIX
bucket: the removal-checkpoint record loss, prior R8, prior R9. VERIFY bucket:
none. KNOWN bucket: none.

R1: fail
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

## Carl

Not run. gemini-run backend=copilot model=gemini-3.8-flash exited 1 twice with
"You have exceeded your monthly quota". No `ui` lens this cycle.

Verdict: 13 findings
Tests: 4134 passed, 0 failed, 9 skipped (suite run this cycle)

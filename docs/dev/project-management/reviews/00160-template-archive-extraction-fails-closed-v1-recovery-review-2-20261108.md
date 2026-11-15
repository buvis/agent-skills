---
prd: docs/dev/project-management/prds/hold/00160-template-archive-extraction-fails-closed-v1.md
review: standalone-recovery-2-20261108
date: 2026-11-08
head_sha: 1a01b3a94c2696d75ea025bb24c5f56e0122868f
reviewers: alice,blake,bob,carl,eve
agents:
  alice: available
  blake: available
  bob: available
  carl: available
  eve: available
---

# Standalone recovery review 2: PRD 00160

Diff range: `1384ddc..1a01b3a` (last reviewed source baseline `39b97f3`;
`1384ddc` adds only the first recovery report).

codex_rung_guard: not fired

## Outcome

**PASS.** The two LOW documentation corrections requested by the first
recovery review (its R5 `_safe_mode` docstring, R6 superseding note in the
assumptions ledger) are correct. `git diff 39b97f3 1a01b3a -- skills tests`
touches only the `_safe_mode` docstring; no executable code or test changed.
No CRITICAL, HIGH or MEDIUM finding. The archive branch repair is ready for
supported recovery of held 00160; the remaining Stage 2 lanes may resume.

This is a standalone branch-repair review under installed autopilot 0.10.0
`recovery.md` `cap_regression`, explicitly targeting held 00160 with no task
context. It is not an original review cycle. The original two-cycle cap,
reports, store, held PRD, 29 deferred rows and ledger keys are unchanged.
No default entry, PRD 00133 selection, phase transition, push or publication ran.

## Roster and actual backends

| Lens | Backend / model | Verdict |
|---|---|---|
| Alice, consensus | native Claude subagent, `claude-sonnet-5-5` | PASS, 2 LOW |
| Blake, blind PRD-only | native Claude subagent, `claude-sonnet-5-5`; told not to read reviews, designs, ledger or log | PASS, 4 LOW |
| Bob, doubt/de-slop | Codex CLI `gpt-6-astra`, read-only, inlined prompt | PASS, no findings |
| Bob persona, extra doubt voice | native Claude subagent, `claude-opus-5-5` (persona did not reach Codex) | PASS, 2 LOW |
| Carl, consensus | Copilot CLI `gemini-3.8-flash` | PASS, 1 LOW |
| Carl persona, extra voice | native Claude subagent, `claude-opus-5-5` (persona did not reach Gemini) | PASS, 1 LOW |
| Eve, Anthropic doubt safeguard | native Claude subagent, `claude-fable-5-1` | PASS, 1 FIX/1 VERIFY/5 KNOWN, all LOW or pre-existing |

The first Codex attempt with repository access failed before inference
(`sandbox-exec: sandbox_apply: Operation not permitted`, nested Seatbelt). The
documented inlined retry ran without tools and verified the backend in its
session header. Codex and Gemini both ran, so this roster has independent
provider voices, unlike the first recovery review. Eve preserved the extra
Anthropic voice required after Codex implementation.

## Verification

- Full gate at `1a01b3a`, `UV_PYTHON=3.13.18` adapter, rootdir the repair
  worktree: `PASS 4598 FAIL 0 SKIP 9 EXIT 0`, 535.90 s. Log in main checkout:
  `docs/dev/tmp/closeout-cap-docs-review-20261108-gate.log`.
- Eve, isolated environments with `-W error::DeprecationWarning`: full
  `skills/use-qwen` on 3.13, 2622 passed, 1 skipped; six focused archive/tree
  files on 3.10 and 3.12, 429 passed each. Mutations, all killed: reinstated
  directory chmod, `callable` -> `hasattr`, dropped root/implicit-parent
  directory classification, `_seal_template` catching nothing.
- Blake, focused files: 265 passed on 3.10 and 3.12, 429 on 3.13.
- Environment incident: Blake's Python 3.10 `uv run` rebuilt the shared
  worktree `.venv` while a 3.13 run was in flight. The single resulting
  failure (`test_only_one_of_several_processes_racing_for_the_gate_takes_it`,
  `ModuleNotFoundError: _pytest` in a 3.10 spawn child) does not reproduce in
  isolated runs or in the gate above. Not a code defect.

## Consolidated findings

| Ref | Voices | Severity | Issue | File | Disposition |
|---|---|---|---|---|---|
| N1 | Bob-Opus, Carl-Gemini | LOW | Test comment says directory modes are "stripped"; they are now ignored. | skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py:96 | Defer: outside this delta, wording only, no behavior. |
| N2 | Bob-Opus, Eve | LOW | `UNSAFE_DIRECTORY_BITS` assertion fails under umask 002 on both seams. | skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py:45 | Defer: pre-existing environment dependence, CI and macOS use 022. Follow-up: pin umask in a fixture. |
| N3 | Blake | LOW | `hash_paths` link tests never read the sentinel through the link before asserting refusal (Phase 2 A11 wording). | skills/use-qwen/scripts/test_eval_tree_links.py:614 | Defer: new durable follow-up, outside this delta, refusal itself is asserted. |
| N4 | Eve | LOW | 72-way seal-failure cross product; mode dimension is orthogonal. | skills/use-qwen/scripts/test_eval_tree_archive_staging.py:324 | Defer: test cost only, 23.5 s. |
| N5 | Eve | LOW | Stale `hasattr` wording in a test helper docstring. | skills/use-qwen/scripts/test_eval_tree_links.py:358 | Defer: cosmetic, pre-existing. |
| N6 | Alice, Carl-Opus | LOW | "by the extractor" does not name both seams. | skills/use-qwen/scripts/eval_harness/trees.py:301 | Reject: claim verified true on both seams. |
| K1 | Alice, Blake, Eve | known | File exec-bit parity with `data_filter`. | skills/use-qwen/scripts/eval_harness/trees.py:349 | Existing first-recovery R1 / original cycle-2 R7. |
| K2 | Blake, Eve | known | ReadError/ExtractError not translated. | skills/use-qwen/scripts/eval_harness/trees.py:415 | Existing first-recovery R16 / original cycle-2 R14. |
| K3 | Blake | known | Existing empty `dest` refused (stricter than spec). | skills/use-qwen/scripts/eval_harness/trees.py:394 | Existing ledger auto-dismissal. |
| K4 | Eve | verify | Windows `target_is_directory` only observable on hosted Windows. | skills/use-qwen/scripts/test_eval_tree_archive_safety_ancestor_parity.py | Existing first-recovery R9: exact-SHA hosted Windows gate. |
| K5 | Eve | known | On 3.10 both seams take the manual path. | skills/use-qwen/scripts/test_eval_tree_archive_safety.py:88 | Pre-existing seam design; real parity runs on 3.12/3.13. |

No new finding is HIGH or above, and none is a regression of `1a01b3a`.
N1-N5 are not repaired here: each sits outside the reviewed delta, and a
repair would need another fresh review boundary for wording or test cost
alone. They join the recovery follow-ups; no deferred row or ledger key was
rewritten.

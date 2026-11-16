---
prd: docs/dev/project-management/prds/done/00178-clean-sweep-cannot-be-verified-v1.md
review: 1
date: 2026-11-16
head_sha: 30d2bf9b697418555ccd22ef236c9f8a07313283
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
---

# Review: 00178-clean-sweep-cannot-be-verified-v1

Diff range: `d7bf96a..30d2bf9b697418555ccd22ef236c9f8a07313283`

codex_rung_guard: not fired

Standalone completion review in a fresh session; no active autopilot task state. Each PRD received independent consensus, blind PRD-only, and doubt plus de-slop reviews. Reviewers resumed only their own contexts for follow-up checks. Blake received no diff, fix summary, or other reviewer output.

## Backends and isolation

- Alice: native Claude CLI, `claude-sonnet-5`, explicit high effort; session `2e9111ea-0cdd-485a-890c-e5076382ee0e`.
- Blake: native Claude CLI, `claude-sonnet-5`, explicit high effort; session `7c701c25-f37f-4fbf-a5a2-931b9902c2d0`.
- Bob: isolated native Codex agent `bob_00178`, GPT-6 family. The host does not expose its exact deployment identifier. The Codex CLI refused nested dispatch; the native agent route preserved isolation without overriding that refusal.

The model identity limitation is recorded rather than inferred from a local default. Claude model selection was verified from session records. The optional engram pack was unavailable because this worktree is not registered; review continued without it.

## Findings and dispositions

- **Fixed, Bob:** Windows backslash traversal, drive-qualified paths, rooted paths, and UNC paths could evade the POSIX-only guard. Export now rejects anchors and parent components using `PureWindowsPath` before writing. Six Windows cases failed before the fix; all seven path cases pass afterward.
- **Fixed, Bob:** configured temporary roots could place the export inside a swept repo. Resolved containment is checked against every scan scope before any blob is written. Tests cover the control repo, another repo, and a bare-repo dictionary scope; cleanup and refusal are asserted.
- **Fixed, Alice:** the bare-scope containment branch initially lacked a dedicated regression. The final parameterized test exercises real bare-scope enumeration through `BUVIS_BARE`. All 17 control-revision tests pass. Replaying that case against the original production source fails because it returns success instead of refusing.
- **Dismissed, Blake:** multiple changelog bullets are not a defect. The PRD requires an entry and its acceptance check explicitly accepts a positive occurrence count; it does not forbid separate entries for separate fixes.
- **Dismissed, Blake:** the added path and temporary-location checks enforce existing safety requirements rather than add a new feature.

The optional `label` parameter avoids exposing a deleted temporary path in errors. Checking the revision only for zero-hit sweeps preserves the verification contract. Merge commits use their first parent; renames export the removed path; added files, symlinks and submodules have no searchable regular-file pre-image. The deadline is shared with export and verification; context-manager cleanup also covers `SystemExit`.

Existing function-size overruns in `enumerate_repos` and `main`, plus the repository's exclusion of `skills/` from ruff, remain documented debt.

## Verification

The final full suite passes on the reviewed source and tests. Both changed skills pass `validate_skill.py`. The renderer import check prints `sweep deadline expired`; its six functions are verbatim and `sweep.py` is 775 lines. The canonical-source `braid --check --source <canonical-repo>` reports zero drift. Bare `braid --check` initially reported no configured sources; no machine configuration was changed.

## Alice

[ALICE] 🟡 `test_preimage_refuses_a_temporary_root_inside_a_swept_repo` only parametrizes plain-Path repos ("control", "other"); the new containment check's dict/bare-scan-scope branch (`_repo_cwd_and_targets` returning `repo["cwd"]` for a `{"cwd":..., "files":[...]}` entry) has no dedicated regression test, even though the fix is described as covering "any swept repo, including bare scan scopes" | File: skills/sweep-fix/scripts/test_sweep_control_rev.py:237 | Task: general

Everything else checked out: `sweep_preimage.py`'s path-safety check now uses `PureWindowsPath` and rejects both `..`-traversal styles, drive-absolute/drive-relative paths, and UNC paths (`test_sweep_preimage_paths.py:11-40`, which would have let `..\escape.py`-style and `C:\...`-style paths through the old `PurePosixPath`-only check). The new containment guard in `sweep.py:700-707` runs before `_export_preimage` so no file is ever written when the temp root collides with a swept repo, and the `with tempfile.TemporaryDirectory(...)` block still cleans up on that `RuntimeError` exit path, matching `test_sweep_control_rev.py:251-254`. `sweep.py` is 775 lines, still under the 800-line cap, and `_verify_zero_hit_sweep` stays at 30 lines.

R1: fail
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

Alice's last 00178 coverage finding is resolved by the added bare-scope regression and passing focused/full gates; its original verdict is retained as reviewer evidence rather than rewritten.

## Blake

All acceptance checks confirmed by code inspection. Final re-review complete.

## Report

[BLAKE] ⚪ (pre-existing, now compounded) `CHANGELOG.md` must-have states "gains one `### Fixed` line under `[Unreleased]`," but the sweep-fix work in scope now carries three separate `### Fixed` lines (control-rev verification, saved-report exclusion, and a newly added path-escape/temp-dir-inside-repo hardening line) instead of one | File: CHANGELOG.md:20 | Task: general
[BLAKE] ⚪ New code beyond the PRD's declared "New symbols" list: `sweep.py`'s `_verify_zero_hit_sweep` gained a runtime check rejecting a temp pre-image directory nested inside any swept repo, and `sweep_preimage.py` switched its unsafe-path check from `PurePosixPath`/`".." only` to `PureWindowsPath`/`anchor-or-".."`, with a new test file `test_sweep_preimage_paths.py` and a new test `test_preimage_refuses_a_temporary_root_inside_a_swept_repo`. Both directly reinforce existing must-haves ("outside every swept repo", safe read-only export) rather than adding an unrelated feature, so this reads as legitimate hardening, not harmful scope creep — flagged for visibility only | File: skills/sweep-fix/scripts/sweep_preimage.py:79 | Task: general
[BLAKE] ✅ All other must-haves verified by re-reading the current code: `--control-rev` wiring, pre-image export via read-only git commands only, cleanup on every exit path (now including the new inside-swept-repo case), the "unusable rev" one-line `sweep unverified:` contract, the saved-report exclusion applied unconditionally in `_search_control_term`, the unchanged no-flag path, `sweep.py` at 776 lines (still under the 800 cap), and SKILL.md documenting `--control-rev` with no "never exits 0" sentence.

Verification performed this pass: re-read `sweep.py`, `sweep_preimage.py`, `test_sweep_control_rev.py`, `test_sweep_verify_control.py`, `test_sweep_preimage_paths.py`, `CHANGELOG.md`, `SKILL.md`, and the filed PRD at `docs/dev/project-management/prds/done/00178-clean-sweep-cannot-be-verified-v1.md` to confirm the spec text was unchanged. No commands or tests were run this pass, per instructions; correctness of the new path-safety and temp-dir-location logic was traced by hand against the new parametrized test cases.

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

Second-pass static review confirms both containment fixes, caller integration, deadline behavior, and cleanup. `_verify_control_by` has two callers; `_preimage_blobs` separates Git parsing and keeps the export below the function cap. Neither abstraction warranted removal. Bob's requested runtime checks were completed by the orchestrator. No in-scope FIX remains.

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

Bob's runtime VERIFY items are discharged by the verification above. His R12 failure records the explicitly accepted pre-existing function-size debt.

Verdict: converged
Tests: 4934 passed, 0 failed, 12 skipped

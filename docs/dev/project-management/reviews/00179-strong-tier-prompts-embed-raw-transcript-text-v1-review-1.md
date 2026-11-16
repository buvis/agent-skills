---
prd: docs/dev/project-management/prds/done/00179-strong-tier-prompts-embed-raw-transcript-text-v1.md
review: 1
date: 2026-11-16
head_sha: 30d2bf9b697418555ccd22ef236c9f8a07313283
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
---

# Review: 00179-strong-tier-prompts-embed-raw-transcript-text-v1

Diff range: `d7bf96a..30d2bf9b697418555ccd22ef236c9f8a07313283`

codex_rung_guard: not fired

Standalone completion review in a fresh session; no active autopilot task state. Each PRD received independent consensus, blind PRD-only, and doubt plus de-slop reviews. Reviewers resumed only their own contexts for follow-up checks. Blake received no diff, fix summary, or other reviewer output.

## Backends and isolation

- Alice: native Claude CLI, `claude-sonnet-5`, explicit high effort; session `240131ac-e6a0-4a64-b9f5-9470b3b92f60`.
- Blake: native Claude CLI, `claude-sonnet-5`, explicit high effort; session `fe938e29-24e6-4000-abd3-0acf784f419d`.
- Bob: isolated native Codex agent `bob_00179`, GPT-6 family. The host does not expose its exact deployment identifier. The Codex CLI refused nested dispatch; the native agent route preserved isolation without overriding that refusal.

The model identity limitation is recorded rather than inferred from a local default. Claude model selection was verified from session records. The optional engram pack was unavailable because this worktree is not registered; review continued without it.

## Findings and dispositions

- **Fixed, Bob:** the hostile-snippet test lacked the explicitly required whole-prompt equality assertion. It now compares the complete expected string as well as checking the final data line.
- **Fixed, Bob:** the Phase 0 test inventory and acceptance command still named the old location of the dedup test. Both now name `test_dedup_prompt.py`.
- **Resolved, Alice:** initial diff artifacts became stale when review fixes landed. Follow-up reviewers read the current files; the final review is tied to the committed `head_sha`, not the old snapshot.
- **Dismissed, Bob:** existing instruction assertions are preservation tests and may pass against the original implementation. Their assertions were not weakened. The three new framing tests all fail whole-prompt equality against the original production sources.

Both production format calls use default `json.dumps`, producing one ASCII data line with escaped quotes, line breaks, and non-ASCII characters. Prompt text matches the PRD exactly. Reply parsing, tiers, timeouts, discard handling and anchors are unchanged.

The quality of distilled memories under the JSON framing remains unmeasured, as explicitly allowed by the PRD. No claim of prompt-injection immunity or live judge-quality validation is made.

## Verification

The final full suite passes on the reviewed source and tests. Both changed skills pass `validate_skill.py`. The renderer import check prints `sweep deadline expired`; its six functions are verbatim and `sweep.py` is 775 lines. The canonical-source `braid --check --source <canonical-repo>` reports zero drift. Bare `braid --check` initially reported no configured sources; no machine configuration was changed.

## Alice

[ALICE] ✅ No issues found — re-reading the current working tree confirms both fix sets: `skills/sweep-fix/scripts/sweep_preimage.py:79-81` now checks `PureWindowsPath(rel).anchor` and `".." in parts`, covering both `/` and `\` traversal plus drive/UNC anchors, with `skills/sweep-fix/scripts/test_sweep_preimage_paths.py` exercising all seven unsafe forms against the real `_export_preimage`; `skills/sweep-fix/scripts/sweep.py:700-707` refuses a pre-image temp dir that resolves inside any entry in `repos` (plain repo paths and bare `{"cwd": ...}` scan-scope dicts alike, via the existing `_repo_cwd_and_targets` helper), tested in `test_sweep_control_rev.py:237-254` for both the control repo and another swept repo. On the 00179 side, `test_distil.py:393-407`'s hostile-snippet test now asserts whole-prompt equality (`prompt == expected`) in addition to the data-line checks, and PRD 00179's Phase 0 task (lines 93, 96) and CHANGELOG.md:20 correctly name `test_dedup_prompt.py` and the new "escape temporary directories" fix respectively.

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

Unchanged and correct. Everything I found in the first pass still holds in the current tree. No new defects introduced, and I found no pre-existing debt relevant to this PRD's scope either.

[BLAKE] ✅ No issues found

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

The first static pass found the two test/documentation gaps above. The second pass confirms both fixes and corrects R2 to pass: preservation assertions are not tautological merely because they preserve existing behavior. The shared test helper has two callers; independent expected prompt literals intentionally pin the external contract. No additional simplification or in-scope FIX remains.

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

Bob's runtime VERIFY items are discharged by the verification above. No residual limitation beyond the PRD's stated quality-measurement limit remains.

Verdict: converged
Tests: 4934 passed, 0 failed, 12 skipped

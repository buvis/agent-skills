---
prd: docs/dev/project-management/prds/wip/00089-purge-devtmp-moves-a-nested-repo-as-one-unit-v1.md
review: 1
date: 2026-10-25
head_sha: e2d0f855f07e06c8834a6645d9edf6564bf237ee
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
dispatch_rows:
  alice: 7857d05f
  blake: a7deba18
  bob: 71036fc6
---

# Review: 00089-purge-devtmp-moves-a-nested-repo-as-one-unit-v1

Diff range: `87e8be8d6b2952502ff588cf62551979c302a7c9..e2d0f855f07e06c8834a6645d9edf6564bf237ee`

codex_rung_guard: not fired
provider_review_guard: satisfied
autocodex_alice_anthropic_receipt: /Users/bob/git/src/github.com/buvis/agent-skills/docs/dev/tmp/alice-output-00089-c1-resumed-20261025.txt.receipt.json
autocodex_blake_anthropic_receipt: /Users/bob/git/src/github.com/buvis/agent-skills/docs/dev/tmp/blake-output-00089-c1-resumed-20261025.txt.receipt.json
autocodex_bob_anthropic_receipt: /Users/bob/git/src/github.com/buvis/agent-skills/docs/dev/tmp/bob-output-00089-c1-resumed-20261025.txt.receipt.json

The model-provider guard supersedes the legacy Codex/Eve guard. Eve did not run.
All three independent Anthropic reviewers used fresh external sessions through the host helper, requested Opus/xhigh; raw metadata identifies claude-opus-5-5. Receipts preserve each actual session and source output. Carl was omitted: this change has no UI surface. The prior failed authentication attempt remains preserved.

Implementation files are unchanged since the original cycle-1 staging. The staged three-test replay failed all three against the base; no tautological-test findings were produced. No prior-cycle verification queue exists.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/3] | 🟡 | The `autocodex-sessions/` ignore entry is outside the PRD's scope but went into the `fix(purge-devtmp)` commit. It is defensible, since it keeps raw transcripts out of a public repo, but it belongs in a separate chore commit | .gitignore:8 | 1 | ALICE, BLAKE, BOB |
| R2 | [3/3] | 🟡 | Nothing tests the new unit guard in `prune_empty_dirs`. I swapped the pre-change prune back in and all 15 tests in `test_purge_devtmp.py` still pass. The guard matters: on a `git init` fixture that is classed fresh and kept in apply mode, the old prune deletes the empty `.git/refs` and `.git/objects` dirs, and `git rev-parse` then exits 128 with "not a git repository". Add an apply-mode test with a fresh unit that holds empty `.git/refs/heads` and `.git/objects/pack`, and assert they survive | skills/purge-devtmp/scripts/purge_devtmp.py:154 | 1 | ALICE, BLAKE, BOB |
| R3 | [2/3] | 🟡 | `walk_store` nests 5 levels deep (for, elif, for, for, try), over the 4-level limit. Move the inner walk and its fallback into `newest_file_mtime(directory: Path) -> float`. The branch then becomes `yield Path(base).relative_to(store), newest_file_mtime(Path(base))`, `dirs[:] = []`, `continue` | skills/purge-devtmp/scripts/purge_devtmp.py:85 | 1 | ALICE, BOB |
| R4 | [2/3] | 🟡 | Two walkers now repeat the same pruning rules: the `".git" in dirs or ".git" in files` check and the root `.trash` prune appear in both `walk_store` and `prune_empty_dirs`. A shared `is_repo_unit(dirs, files)` check would keep them from drifting apart | skills/purge-devtmp/scripts/purge_devtmp.py:151 | 1 | ALICE, BOB |
| R5 | [2/3] | ⚪ | A `.git` at the store root is never treated as a unit, because the `base == store` branch runs first. The walk then enters `store/.git`, yields its `hooks/*` files, and hits the same `.git/hooks` mkdir denial. `prune_empty_dirs` also removes empty dirs inside it. This is unlikely, but it is the same crash class | skills/purge-devtmp/scripts/purge_devtmp.py:81 | 1 | ALICE, BLAKE |
| R6 | [1/3] | 🟡 | The PRD's root cause was the uncaught exception in process_store, and it is still there. trash_file has no guard, so any other move failure (for example a rename refused for another reason) still leaves the store half moved and stops every later store. That puts the "no purge traceback" success signal at risk | skills/purge-devtmp/scripts/purge_devtmp.py:195 | general | BLAKE |
| R7 | [1/3] | 🟡 | Possible follow-on bug: trash batches can now hold `.git/hooks`. If the Seatbelt also refuses to unlink under `.git/hooks`, and `empty_old_trash` does not handle the error, the purge dies again once that batch is 30 days old. | skills/purge-devtmp/scripts/purge_devtmp.py:165 | 1 | BOB |
| R8 | [1/3] | ⚪ | The prune change also fixes a user-visible bug: kept repo fixtures no longer lose their empty `.git` subdirs. Neither the CHANGELOG entry nor SKILL.md mentions it | CHANGELOG.md:12 | 1 | ALICE |
| R9 | [2/3] | ⚪ | The live check now reads only the unit's own path. A file with a live PRD number inside a stale fixture moves to the trash (I reproduced this), but SKILL.md still says "Files carrying the number of a PRD ... are kept". The 30-day trash makes it recoverable; the gap is in the PRD and the docs | skills/purge-devtmp/SKILL.md:32 | general | BLAKE, BOB |
| R10 | [1/3] | ⚪ | The fake sandbox in the test patches only pathlib.Path.mkdir, so a move that fell back to os.makedirs or copytree would still pass. This matches the spec's wording, but it is a weak guard against that kind of regression | skills/purge-devtmp/scripts/test_purge_devtmp.py:105 | 1 | BLAKE |
| R11 | [1/3] | ⚪ | `max(mtimes, default=Path(base).stat().st_mtime)` runs `stat` for every unit, even when files were found, and nothing catches its error. If another session deletes the unit during the inner walk, `FileNotFoundError` stops the whole store run. That is the failure this PRD set out to remove. | skills/purge-devtmp/scripts/purge_devtmp.py:93 | 1 | BOB |
| R12 | [2/3] | ⚪ | Nothing tests the PRD's empty-unit rule (use the directory's own mtime when the unit holds no regular file). All three new tests put files in the unit, so changing `default=` to `0` would pass. The apply-mode test above can use a unit with only empty `.git` subdirs to cover this too | skills/purge-devtmp/scripts/purge_devtmp.py:93 | 1 | ALICE, BOB |

The fresh full-suite gate initially failed only in convert-to-icon/iconutil under the command sandbox (3926 passed, 27 failures including setup errors, 9 skipped). The approved retry passed all 3953 tests; the gate wrote its own verification record. Skill validation and braid check also passed.

## Consolidation corrections and decisions

The script completed, but its approximate semantic merge combined distinct issues. Model-side corrections restore the separate empty-unit fallback test, attribute prune coverage to all three reviewers, attribute duplicated predicates to Alice/Bob, and count the member-name behavior from Blake/Bob. Every original report follows verbatim.

- R1: discarded: the ignore rule prevents private raw host transcripts from entering this public repository; workflow reports and model audits remain tracked. Rewriting committed history adds no product benefit.
- R2: actionable shared finding; tail sweep
- R3: actionable shared finding; tail sweep
- R4: actionable shared finding; tail sweep
- R5: settled-deferral: this PRD covers repositories nested below the tmp store. Moving the store itself into its own trash is invalid; a root-repository refusal policy needs separate scope.
- R6: single-voice Medium/Low; discarded under the review decision policy
- R7: single-voice Medium/Low; discarded under the review decision policy
- R8: single-voice Medium/Low; discarded under the review decision policy
- R9: actionable shared finding; tail sweep
- R10: single-voice Medium/Low; discarded under the review decision policy
- R11: single-voice Medium/Low; discarded under the review decision policy
- R12: actionable shared finding; tail sweep

Bob’s proposed expiry verification is not queued: it is a multi-step manual sandbox experiment, not one runnable project verification command. Its single-voice speculative finding is discarded. Member-name semantics match the explicit PRD directory-path rule; R9 requests prose clarification only.

## Alice

Provider: Anthropic. Requested model: opus. Actual model: claude-opus-5-5. Effort: xhigh. Session: 9047f9e0-3196-417c-b9cc-de9f924e59d3.

[ALICE] 🟡 Nothing tests the new unit guard in `prune_empty_dirs`. I swapped the pre-change prune back in and all 15 tests in `test_purge_devtmp.py` still pass. The guard matters: on a `git init` fixture that is classed fresh and kept in apply mode, the old prune deletes the empty `.git/refs` and `.git/objects` dirs, and `git rev-parse` then exits 128 with "not a git repository". Add an apply-mode test with a fresh unit that holds empty `.git/refs/heads` and `.git/objects/pack`, and assert they survive | File: skills/purge-devtmp/scripts/purge_devtmp.py:154 | Task: 1
[ALICE] ⚪ Nothing tests the PRD's empty-unit rule (use the directory's own mtime when the unit holds no regular file). All three new tests put files in the unit, so changing `default=` to `0` would pass. The apply-mode test above can use a unit with only empty `.git` subdirs to cover this too | File: skills/purge-devtmp/scripts/purge_devtmp.py:93 | Task: 1
[ALICE] 🟡 `walk_store` nests 5 levels deep (for, elif, for, for, try), over the 4-level limit. Move the inner walk and its fallback into `newest_file_mtime(directory: Path) -> float`. The branch then becomes `yield Path(base).relative_to(store), newest_file_mtime(Path(base))`, `dirs[:] = []`, `continue` | File: skills/purge-devtmp/scripts/purge_devtmp.py:85 | Task: 1
[ALICE] ⚪ Two walkers now repeat the same pruning rules: the `".git" in dirs or ".git" in files` check and the root `.trash` prune appear in both `walk_store` and `prune_empty_dirs`. A shared `is_repo_unit(dirs, files)` check would keep them from drifting apart | File: skills/purge-devtmp/scripts/purge_devtmp.py:151 | Task: 1
[ALICE] ⚪ A `.git` at the store root is never treated as a unit, because the `base == store` branch runs first. The walk then enters `store/.git`, yields its `hooks/*` files, and hits the same `.git/hooks` mkdir denial. `prune_empty_dirs` also removes empty dirs inside it. This is unlikely, but it is the same crash class | File: skills/purge-devtmp/scripts/purge_devtmp.py:81 | Task: 1
[ALICE] ⚪ The prune change also fixes a user-visible bug: kept repo fixtures no longer lose their empty `.git` subdirs. Neither the CHANGELOG entry nor SKILL.md mentions it | File: CHANGELOG.md:12 | Task: 1
[ALICE] ⚪ The `autocodex-sessions/` ignore entry is outside the PRD's scope but went into the `fix(purge-devtmp)` commit. It is defensible, since it keeps raw transcripts out of a public repo, but it belongs in a separate chore commit | File: .gitignore:8 | Task: 1

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

## Blake

Provider: Anthropic. Requested model: opus. Actual model: claude-opus-5-5. Effort: xhigh. Session: b01b0c6c-46d8-40d9-b052-73987fc2606e.

The fix does what the spec asks: a directory holding `.git` now moves to the trash as one unit, and all acceptance checks pass. I found two pieces of scope creep (one rubric fail), plus four smaller gaps.

**Checks I ran**
- The purge test module passes (15 tests). I had to point uv at a cache under `docs/dev/tmp/uv-cache` because the default uv cache lock is denied in this sandbox.
- I ran the three new tests against the old code from `3f8b65d`. All three fail as the PRD predicts: the first raises the simulated `PermissionError`, the fresh test gets 1 stale item where it expects 0, and the live test counts 2 live items where it expects 1.
- `validate_skill.py skills/purge-devtmp` passes. The SKILL.md sentence appears once, and the CHANGELOG line appears once under `[Unreleased]` / Fixed.
- I probed two edge cases with a scratch script:
  - A stale fixture holding `00123-notes.md` (with PRD 00123 live) comes back as one stale unit, so that file gets trashed.
  - A store whose root holds `.git/hooks/pre-commit` still yields that file one by one.

**Findings**
```
[BLAKE] 🟡 prune_empty_dirs was rewritten even though the PRD names only walk_store: it now stops at .git directories and skips .trash only at the store root (before, a .trash anywhere in the path was skipped). No test covers either change and the CHANGELOG does not mention them. The skip does protect kept fixtures from losing empty .git/refs dirs, but it is unplanned and untested | File: skills/purge-devtmp/scripts/purge_devtmp.py:147 | Task: general
[BLAKE] 🟡 The fix commit also adds an unrelated .gitignore line for docs/dev/project-management/autopilot/autocodex-sessions/. It has nothing to do with PRD 00089, and it ignores part of a tree that the working-documents rule says must stay tracked | File: .gitignore:8 | Task: general
[BLAKE] 🟡 The PRD's root cause was the uncaught exception in process_store, and it is still there. trash_file has no guard, so any other move failure (for example a rename refused for another reason) still leaves the store half moved and stops every later store. That puts the "no purge traceback" success signal at risk | File: skills/purge-devtmp/scripts/purge_devtmp.py:195 | Task: general
[BLAKE] ⚪ The live check now reads only the unit's own path. A file with a live PRD number inside a stale fixture moves to the trash (I reproduced this), but SKILL.md still says "Files carrying the number of a PRD ... are kept". The 30-day trash makes it recoverable; the gap is in the PRD and the docs | File: skills/purge-devtmp/SKILL.md:32 | Task: general
[BLAKE] ⚪ A store root that is itself a repo is not treated as a unit (the elif skips the root), so the walk still yields .git/hooks/* files and trash_file hits the same sandbox denial. I reproduced this with walk_store; it is a rare case | File: skills/purge-devtmp/scripts/purge_devtmp.py:83 | Task: 2
[BLAKE] ⚪ The fake sandbox in the test patches only pathlib.Path.mkdir, so a move that fell back to os.makedirs or copytree would still pass. This matches the spec's wording, but it is a weak guard against that kind of regression | File: skills/purge-devtmp/scripts/test_purge_devtmp.py:105 | Task: 1
```

B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: fail
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

My probes left two scratch items: `docs/dev/tmp/uv-cache` (gitignored) and a `mkdtemp` directory under `$TMPDIR`. I didn't remove them because `rm` needs warden approval.

## Bob

Provider: Anthropic. Requested model: opus. Actual model: claude-opus-5-5. Effort: xhigh. Session: 5540837e-ab9b-484e-be4a-cc8b495d3dd9.

[BOB] 🟡 The new rule in `prune_empty_dirs` that skips repository units has no committed test, and neither has the fallback that gives a unit with no files its directory's own mtime. Only the build report's one-off check covers them. A regression would let the purge delete empty `.git/refs/*` folders inside a fixture it decided to keep, and break that repo. | File: skills/purge-devtmp/scripts/purge_devtmp.py:154 | Task: 1
[BOB] 🟡 `walk_store` nests five levels deep (outer walk, elif, inner walk, file loop, try/if). The coding style allows four. | File: skills/purge-devtmp/scripts/purge_devtmp.py:87 | Task: 1
[BOB] ⚪ `max(mtimes, default=Path(base).stat().st_mtime)` runs `stat` for every unit, even when files were found, and nothing catches its error. If another session deletes the unit during the inner walk, `FileNotFoundError` stops the whole store run. That is the failure this PRD set out to remove. | File: skills/purge-devtmp/scripts/purge_devtmp.py:93 | Task: 1
[BOB] ⚪ The repository-unit test `".git" in dirs or ".git" in files` appears twice. If the two copies drift apart, the prune can delete folders inside a fixture that the walk kept. | File: skills/purge-devtmp/scripts/purge_devtmp.py:83 | Task: 1
[BOB] 🟡 Possible follow-on bug: trash batches can now hold `.git/hooks`. If the Seatbelt also refuses to unlink under `.git/hooks`, and `empty_old_trash` does not handle the error, the purge dies again once that batch is 30 days old. | File: skills/purge-devtmp/scripts/purge_devtmp.py:165 | Task: 1
[BOB] ⚪ Inside a unit, a PRD number in a member file's name no longer keeps that file. Only the unit's directory path counts. | File: skills/purge-devtmp/scripts/purge_devtmp.py:93 | Task: 1
[BOB] ⚪ The `.gitignore` entry for `autocodex-sessions/` and the autopilot ledger and report files are outside the PRD's scope. | File: .gitignore:8 | Task: general

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

FIX:
- `prune_empty_dirs` unit preservation and the no-file mtime fallback have no tests — skills/purge-devtmp/scripts/purge_devtmp.py:154 — Add two tests to skills/purge-devtmp/scripts/test_purge_devtmp.py:
  - A fresh `fixture/.git/HEAD` plus an empty `fixture/.git/refs/tags/`. Run `process_store` with `apply=True`. Assert `fixture/.git/refs/tags` is still a directory.
  - A fixture that holds only an empty `fixture/.git/`. Run with `apply=True`. Assert `counts["fresh"] == 1` and that `fixture/.git` still exists.
  - Both tests fail against the old bottom-up prune.
- `walk_store` nests five levels — skills/purge-devtmp/scripts/purge_devtmp.py:87 — Move the inner walk and the fallback into `newest_file_mtime(directory: Path) -> float`. The unit branch then reads `yield Path(base).relative_to(store), newest_file_mtime(Path(base))`.
- The fallback `stat` runs on every unit and is unguarded — skills/purge-devtmp/scripts/purge_devtmp.py:93 — Stat the directory only when `mtimes` is empty. Wrap that call in `try/except OSError` and skip the unit, the same way a vanished file is skipped.
- The unit test is written twice — skills/purge-devtmp/scripts/purge_devtmp.py:83 — Define it once (for example `holds_repo(dirs, files)`). Call it from `walk_store` and from `prune_empty_dirs` at skills/purge-devtmp/scripts/purge_devtmp.py:154.

VERIFY:
- Trash expiry may fail on `.git/hooks` under the Seatbelt — check in two steps:
  1. Run `rg -n "rmtree|onexc|onerror|ignore_errors|except" skills/purge-devtmp/scripts/purge_devtmp.py`. Confirm that `empty_old_trash` catches `OSError` for each batch, and that `process_store` cannot die there before it moves the store.
  2. Outside the sandbox, seed `docs/dev/tmp/.trash/2026-09-01/fx/.git/hooks/pre-commit` in a scratch repo. Inside a `~/bin/run-agent` session, run `python3 skills/purge-devtmp/scripts/purge_devtmp.py --repo <scratch> --apply`. Expect exit 0 and no traceback.

KNOWN:
- Member file names inside a unit no longer count for the live-PRD rule — the PRD says to use only the directory's path ("a PRD number anywhere in the directory's path"), and trashed units can be restored for 30 days.
- The `.gitignore` and autopilot bookkeeping changes are outside the PRD — the coordinator committed them as loop housekeeping, and ignoring raw session transcripts keeps machine-specific paths out of a public repo, so they should stay.

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

Verdict: 12 findings
Tests: 3953 passed, 0 failed, 9 skipped (suite run this cycle; approved sandbox retry at e2d0f855f07e06c8834a6645d9edf6564bf237ee)

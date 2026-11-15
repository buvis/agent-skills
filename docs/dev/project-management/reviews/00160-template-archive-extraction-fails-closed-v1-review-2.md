---
prd: docs/dev/project-management/prds/wip/00160-template-archive-extraction-fails-closed-v1.md
review: 2
date: 2026-11-06
head_sha: bd014b9a787cbb4dd2db167aa8838843e7819d1b
reviewers: alice,blake,bob,carl
codex_thread_id: 01a1ae64-2fa0-7f83-a211-8a6c20d805f3
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 13c70528
  carl: ba01738a
---

# Review: 00160-template-archive-extraction-fails-closed-v1

Diff range: `a8347f3c691d64e3eec1d2d124e3fa92953629bd..bd014b9a787cbb4dd2db167aa8838843e7819d1b`

codex_rung_guard: not fired

## Review Summary

Reviewed: 10 completed tasks (cycle-1 rework: tasks 8, 9, 10)
PRDs checked: 00160-template-archive-extraction-fails-closed-v1

Cycle 2, incremental review scoped to the cycle-1 rework. Lane `full` (classified
`full`, `security_path`). Every required lens ran.

### Agent Status

- Alice (consensus, native Claude subagent, `autopilot:alice`, `claude-sonnet-5-5` at high effort): available
- Blake (blind PRD-only, native Claude subagent, `autopilot:blake`, `claude-sonnet-5-5` at high effort): available
- Bob (doubt + de-slop, codex CLI via `codex-run.sh`, `gpt-6-astra` at medium reasoning effort): available
- Carl (UI/design generalist, `gemini-run.sh` backend `copilot`, model `gemini-3.8-flash`): available

Model-family diversity this cycle: Anthropic (Alice, Blake), OpenAI (Bob),
Google (Carl). Three families, no `auto` selection and no silent downgrade.

Backend/model notes, as actually selected:

- Bob ran on the codex CLI with the inlined prompt shape
  (`retry-policy.md` § Inlined prompt), exit 0. His `--emit-thread-id` sidecar
  `docs/dev/tmp/bob-thread-00160-c2.txt` is non-empty this cycle, so
  `codex_thread_id` is stamped above and cycle 3, if any, resumes his session.
  Cycle 1's sidecar was empty, so this cycle ran him fresh with no
  `--resume-thread`.
- Carl's dispatch passed `-m gemini-3.8-flash` from the start, because the
  runner's default copilot model is known to fail eligibility on this host. The
  helper's stderr recorded `gemini-run: backend=copilot model=gemini-3.8-flash`,
  exit 0. No exit-4 latch; Carl stays active for this batch.
- `consensus_engine` resolved to `legacy`, so Alice's leg is the single Task
  subagent and no `review-fanout` workflow ran. No `consensus_run_id`.
- `doubt_reviewer` resolved to `codex`. No task carries
  `attempts[].implementor == "codex"` (nine are `claude`, one `orchestrator`),
  so the Codex doubt-roster guard did not fire and Eve was not activated.

### Degradations, stated loudly

- **Context pack unavailable.** `engram pack` exited 1
  (`not inside a registered repo; run gita add <this worktree>`), as in cycle 1.
  Every prompt carried the `(no pack available this cycle)` sentinel for
  `{PACK_FILE}` and `{PACK_FINDINGS}`. This review is degraded by the missing
  findings precedent, not invalid. An agent cannot run `gita add`; a human must
  register the worktree to restore it.
- **Test-gate counts read from the gate log, not from `autopilot verify`.**
  `review-stage` ran the full suite this cycle at this HEAD and reported
  `Tests: counts unavailable (suite run this cycle, exit 0, no PASS/FAIL/SKIP/EXIT
  summary line)`. That is the documented `cli/verification.SUMMARY_RE` mismatch
  for this repo's pytest summary format, not a failing suite. Step 6's fallback
  names `autopilot verify`, which fails the same way here (and could not certify
  HEAD anyway, the tree carrying telemetry appends), so the counts below were
  read from that same `run_gate` invocation's log,
  `docs/dev/tmp/gate-00160-c2.log:197`. The suite exited 0. Recorded as a
  deviation from the literal step rather than hidden.
- **Consolidation corrected by hand.** `consolidate_findings.py` exited 0 but
  one ledger dismissal was wrong and one pair of rows was left unmerged. Three
  corrections were applied and are itemised under "Consolidation corrections".
  The findings table is the corrected one.
- **`prompt_bytes` understated for Bob's dispatch row.** `review-stage` measured
  the staged 24909-byte render; the inlined prompt actually sent to codex is
  279155 bytes. Row `13c70528` therefore under-reports its prompt size.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🟠 | Cycle-1 R4 is only partly resolved, and the rework lost an error-translation guarantee it used to hold. The manual path still applies the archive's directory mode (deferred `os.chmod` in the second loop of `_extract_without_filter`), but `filter="data"` sets a directory's mode to `None`, so `tarfile.makedir` creates it at `0o777 & ~umask` and never chmods it. Measured divergences on accepted archives: directory `0o500` extracts `0o755` on the filter seam and `0o500` on the manual seam. A directory member at mode `0o000` or `0o200` holding a child seals on the filter seam, while on the manual seam the seal's `git commit` fails and leaks a raw `subprocess.CalledProcessError`, and the unreadable directory defeats `shutil.rmtree(staging, ignore_errors=True)` so `dest.staging-<hex>` stays behind. PRD A9's output contract is "a sealed template at `dest`, or a `TreeError`", and its cleanup rule is "on any failure, remove only the staging directory this call created"; both are broken, and the docstring claim that the `filter="data"` policy applies is false for directories. Cycle 1 asked for "skip or force 0o700 on directories, and wrap the seal failure"; neither was done. The fix matching `data_filter` is to not chmod directories on the manual path, plus wrapping the seal. No test covers a directory mode other than `0o500` | skills/use-qwen/scripts/eval_harness/trees.py:353 | 9 | ALICE, BLAKE, BOB |
| R2 | [3/4] | 🟡 | `build_template` is 53 lines, over the project's 50-line function limit, per the cycle's computed mechanical-facts block. The cycle-1 rework grew it from 45 lines with `created_ancestor`, the nested `mkdir` try and the extra cleanup branch, so this cycle's own rework is what crossed the limit. Extract the staging-and-seal sequence, or the cleanup, into a helper | skills/use-qwen/scripts/eval_harness/trees.py:370 | 9 | ALICE, BOB, CARL |
| R3 | [2/4] | 🟠 | The cycle-1 R3 regression does not pin the ancestor rule. `ANCESTOR_CROSSING_THROUGH_A_SAFE_LINK` holds both `pkg/a.txt` and `alias/a.txt`, which `_refuse_colliding_landings` already refuses as a duplicate landing, and the computed fail-first replay confirms the test passes against the pre-change code. With `_ancestor_crossing` stubbed out, this test and every other R3 case still pass; only the four `case-alias-directory-link*` cases fail. The cycle-1 reproducer (`pkg/`, `alias -> pkg`, `alias/file.txt` with no colliding member) is accepted under the stub and is untested. Add that shape to the refusal matrix on both seams | skills/use-qwen/scripts/test_eval_tree_archive_safety_ancestor_parity.py:75 | 9 | ALICE, BOB, mech-check |
| R4 | [2/4] | 🟠 | `test_build_template_falls_back_to_manual_extraction_when_data_filter_is_present_but_not_callable` cannot fail, so cycle-1 R2's "no test pins it" is still true even though the code is fixed. The computed fail-first replay names this test as passing against the pre-change `hasattr` code, because `extractall(filter="data")` resolves the named filter through tarfile's internal `_NAMED_FILTERS` and ignores the patched module attribute. `assumptions.md` records this as an unavoidable gap on this runtime; it is avoidable. Spy on `tarfile.TarFile.extractall` and assert it receives no `filter` kwarg when `data_filter` is non-callable, or spy on `_extract_without_filter` and require its invocation. Also correct the comment claiming `hasattr` necessarily crashes | skills/use-qwen/scripts/test_eval_tree_archive_safety_ancestor_parity.py:50 | 9 | ALICE, BOB, mech-check |
| R5 | [1/4] | 🟠 | Cycle-1 R5 remains incomplete: `_symlink_targets_a_directory` recognises only explicit directory members, so a link whose target is the extraction root or an implicitly-created parent is typed as a file link. Measured: `l -> .` is accepted by validation, extracts, and is created with `target_is_directory=False` even though `.` is a directory; so is `l -> pkg` when the archive carries `pkg/f.txt` but no `pkg` directory member. The first shape is an ordinary committed symlink that `git archive` emits, so this is reachable from real input rather than crafted-only. On Windows it produces a file symlink where the PRD's Phase 2 requires a directory symlink. Include the extraction root and implied parent directories in the classification, and pin both shapes with the existing call spy | skills/use-qwen/scripts/eval_harness/trees.py:304 | 9 | BOB |
| R6 | [1/4] | 🟡 | Behavior-preserving simplification: `_symlink_targets_a_directory` rebuilds `links` and `directories` from every member on each symlink, so the cost is symlinks times members. `_land` also rebuilds `keyed` (a `_fold` of every key) on every call and every recursive hop, even when `fold=False`, where it is an identity dict. Build the maps once per `_extract_without_filter` call and once per `_land` call and pass them down. Measured at 21,000 members with 1,000 links: about 4 s for validation alone, growing quadratically | skills/use-qwen/scripts/eval_harness/trees.py:304 | 9 | ALICE |
| R7 | [1/4] | 🟡 | `_extract_without_filter` does not clear group and other execute bits when the owner lacks execute, so it diverges from `filter="data"`, which does. Measured on accepted archives: file mode `0o077` extracts `0o644` on the filter seam and `0o655` on the manual seam; `0o070` gives `0o640` against `0o650`. Note the spec tension: PRD A7's own wording ("strips setuid, setgid, sticky and group/other write bits, and keeps owner read/write and the executable bit") is exactly what the code does, while the parity requirement ("write an accepted archive identically whether or not `tarfile.data_filter` exists") demands `data_filter`'s stricter rule. One of the two has to give; the code currently follows A7's letter | skills/use-qwen/scripts/eval_harness/trees.py:344 | Phase 1 (A7) | BLAKE |
| R8 | [1/4] | 🟡 | `_extract_without_filter` writes with `open(path, "wb")` and `os.symlink` and never uses `O_NOFOLLOW` or `lstat`, so containment rests entirely on the pre-validation passes being complete. That is sound only if validation has no gap, and R9 below is one | skills/use-qwen/scripts/eval_harness/trees.py:339 | Phase 1 | BLAKE |
| R9 | [1/4] | 🟡 | The case rule folds only whole normalized member names. The `landings` and `files` sets in `_refuse_colliding_landings` hold the raw spelling `_land` returns, and the ancestor-file loop compares `ancestor in files` raw, so folding the `_land` calls alone did not make the rule judge for a name-merging host. Measured: file `pkg` plus `Pkg/x` is ACCEPTED by validation in both member orders. On this case-insensitive host both seams then fail at extraction (surfaced as `TreeError`), but on a case-sensitive host the archive seals and the template is broken on macOS and Windows. PRD A5 requires a file/directory swap refused independent of member order. The minimal fix consistent with `_fold`'s existing use is to fold the set elements and the ancestor probe, keeping raw spellings in the refusal messages. This is also the rework design's own stated intent for this function, which the implementation did not reach | skills/use-qwen/scripts/eval_harness/trees.py:271 | Phase 1 (A5) | BLAKE |
| R10 | [1/4] | 🟡 | `_lay_links` passes `target_is_directory` but does not convert the target's separators to native form, which the PRD's Phase 2 asks for; the target text is written as given. The Q4/Q5 raw-versus-native probe is therefore not implemented in the fixture | skills/use-qwen/scripts/test_eval_tree_links.py:145 | Phase 2 | BLAKE |
| R11 | [1/4] | ⚪ | `_topmost_missing_ancestor(dest.parent)` runs outside the outer `try`, so an `OSError` from `Path.exists()` on an unreadable ancestor would escape untranslated. Pre-existing residual already recorded by Pat's task-9 review. Coordinator note: on CPython 3.x `Path.exists()` catches `OSError` and returns `False`, so this is not reachable on the supported runtimes | skills/use-qwen/scripts/eval_harness/trees.py:360 | 9 | ALICE |
| R12 | [1/4] | ⚪ | Symbols beyond the PRD's "New symbols" list: `_fold` with NFC normalization, `_symlink_targets_a_directory` and `_topmost_missing_ancestor`. The NFC normalization refusal is behavior the PRD does not ask for, though the cycle-1 rework design adopted it deliberately to close a reproduced escape | skills/use-qwen/scripts/eval_harness/trees.py:83 | general | BLAKE |
| R13 | [1/4] | ⚪ | On cleanup, `created_ancestor` is removed with `rmtree(ignore_errors=True)`. It is computed before `staging.mkdir`, so another process that created content there in between would lose it. Low-probability race, outside the harness's single-writer model | skills/use-qwen/scripts/eval_harness/trees.py:419 | general | BLAKE |
| R14 | [1/4] | ⚪ | Staging creation (a write) happens before archive validation. Harmless, since it stays in the staging directory beside `dest`, but it differs from "decide from tar metadata alone, before any write". Corrupt-tar errors (`tarfile.ReadError`, `ExtractError`) are still not translated to `TreeError` | skills/use-qwen/scripts/eval_harness/trees.py:392 | general | BLAKE |
| R15 | [1/4] | ⚪ | The mechanical replay reports passing pre-change staging tests and safe-link controls. These are expected: task 10 strengthens assertions without changing production behavior, and the acceptance controls are supposed to pass against both revisions. No additional production fix follows from those two replay lines, beyond R3 and R4 above, which the same lines also name | skills/use-qwen/scripts/test_eval_tree_archive_staging.py:232 | general | BOB, mech-check |

### Consolidation corrections

`consolidate_findings.py` exited 0 and emitted 16 rows plus two ledger
dismissals. Three corrections were applied. Recorded so the correction is
visible rather than silent.

1. **A wrong ledger dismissal, now restored and merged.** `--ledger-dismiss
   BLAKE` auto-dismissed Blake's directory-mode finding against the cycle-1
   ledger entry for R8, whose recorded reason was: *"single-voice. Also
   substantially covered: the R4 fix row carries 'wrap the seal failure', so the
   seal-path translation lands with that rework task anyway."* **That settled
   reason no longer holds, and the dismissal is therefore wrong.** The R4 fix row
   did not wrap the seal failure (verified: `build_template` still calls `_git`
   three times outside any translating `try`), so the premise the cycle-1 discard
   rested on is falsified by this cycle's own diff. The ledger rule is that a
   settled call may be re-raised when the settled reason is shown not to hold;
   that condition is met here on measured evidence. Blake's finding is restored
   and merged with Alice's and Bob's identical finding as R1, which takes it from
   `[2/4]` to `[3/4]`.
2. **A missed merge, now merged.** The unpinned callable-check test arrived twice
   at the same file and line (Alice `ancestor_parity.py:50` at 🟠, Bob the same
   line at 🟡) as two separate rows, so one defect read as two single voices. It
   is R4 above at two of four, at the higher of the two severities, with
   `mech-check` appended because the computed fail-first replay names that exact
   test.
3. **Mechanical lines absorbed onto existing rows, not added as new ones.** Both
   `[MECH]` fail-first replay lines name tests that existing rows already cover:
   `test_build_template_falls_back_to_manual_extraction_when_data_filter_is_present_but_not_callable`
   onto R4, `test_build_template_refuses_a_member_named_under_a_symlink_that_resolves_safely`
   onto R3, and the staging and safe-link control tests onto R15. `mech-check`
   was appended as a finder to those three rows and no new row was created.

The second ledger dismissal was correct and stands: Blake's "empty `dest`
refused too" finding matches a cycle-1 discard whose reason (the PRD marks the
non-empty rule a guess, fail-closed is safer on a security path) still holds.

### Auto-dismissed (ledger)

- [BLAKE] 🟡 The PRD says a non-empty existing `dest` raises `TreeError` and gives no behavior for an empty one. The code refuses any existing path, including an empty directory. This is arguably stricter than the spec's "guess". The new `lexists` check also runs before staging, so the TOCTOU window is only partly covered by the rename. | File: skills/use-qwen/scripts/eval_harness/trees.py:382 — single-voice. The PRD marks the non-empty rule "(guess)" and the stricter rule is documented in the docstring and pinned by tests. Fail-closed is the safer direction for a security PRD; the reviewer himself calls it deliberate.

Blake's directory-mode finding was also auto-dismissed by the script and is
**not** accepted as dismissed; see correction 1 above. It is R1 in the table.

### Coordinator verification

Six reviewer claims were reproduced against the code at `bd014b9` before being
ranked, and two reviewer claims were corrected as a result. The probes ran as
isolated scripts outside the repository under `python -I`, against crafted
`TarInfo` members and throwaway destinations.

- **Cycle-1 R1 (the CRITICAL) is resolved.** Alice ran all 14 new
  `ANCESTOR_ESCAPES` cases on both seams and confirmed that stubbing
  `_ancestor_crossing` fails the four `case-alias-directory-link*` cases, so the
  crossed-slot logic is pinned for them. No reviewer found a surviving
  out-of-`dest` write, and none raised a new CRITICAL.
- **R1 confirmed as a regression, with the mechanism identified.** Running the
  same crafted archive (directory `d` at mode `0o000` holding `d/f`) through the
  manual seam of both revisions: base `a8347f3` raised
  `TreeError("d/f: [Errno 13] Permission denied")`; head `bd014b9` raises a raw
  `subprocess.CalledProcessError` from the seal's `git commit`. The deferred
  directory chmod is what moved the failure past the translating extraction
  block. The staging directory survives on **both** revisions, so that half of
  the finding is pre-existing, not new. Two reviewer details corrected: the
  failing command is `git commit`, not `git add`, and Blake's unconfirmed
  staging leak is confirmed (staging left behind, holding `d`).
- **The directory-mode divergence is crafted-archive only.** Both
  git-archive-shaped cases are parity-clean (dir `0o755` + file `0o644`, and dir
  `0o775` + file `0o664`, both extract identically on the two seams), because
  `_safe_mode` happens to agree with `0o777 & ~umask` at umask `0022`. Divergence
  needs a mode `git archive` does not emit. That bounds R1's reachability without
  excusing it: crafted archives are this PRD's stated threat model, and the
  agreement is umask-dependent rather than designed.
- **Cycle-1 R4's two quoted reproductions are closed.** A directory at `0o500`
  holding a child now seals on the manual seam, and a file at `0o000` extracts
  `0o600` on both seams. The finding's stated remedy was not implemented, which
  is why R1 re-raises it rather than the ledger settling it.
- **R5 confirmed and widened.** `_symlink_targets_a_directory` returns `False`
  for `l -> .` and for a link to an implicitly-created parent, and `True` for an
  explicit directory member and for a forward chain `a -> b -> pkg`; the control
  (link to a regular file) is correctly `False`. End to end, `l -> .` is accepted
  by validation, extracts, and is created with `target_is_directory=False`. The
  reachable-from-`git archive` character of that shape is coordinator evidence
  for Bob's finding, not a second reviewer voice.
- **R9 confirmed.** File `pkg` plus `Pkg/x` is accepted by validation in both
  member orders. On this host both seams then fail at extraction with a
  `TreeError` (filter seam: `[Errno 20] Not a directory`; manual seam:
  `[Errno 17] File exists`), so the defect surfaces as host-dependent acceptance
  rather than an escape.
- **R7 confirmed, and a spec tension named.** File `0o077` and `0o070` diverge
  between the seams as Blake reports. The implementation matches PRD A7's literal
  mode wording while contradicting the PRD's parity sentence, so this is a spec
  conflict to resolve rather than a simple code defect.
- **R2 confirmed against the computed block.** `build_template` is 45 lines at
  `a8347f3` and 53 at `bd014b9` (`ast`, both revisions), so the rework crossed the
  50-line limit. `_extract_without_filter` grew 26 → 42 lines and stays under it.
  No finding contradicts the mechanical-facts block, so nothing was discarded
  under that rule.

Repository gates run directly, rather than taken from a reviewer's report:

- `~/.agents/bin/braid --check`: `0 linked, 131 current, 20 ignored, 0 removed, 0 backed up, 0 configured, 0 drift`.
- `validate_skill.py skills/use-qwen`: `[OK] Skill is valid!`.
- Carl's own `braid --check` attempt failed with `command not found`; `braid` is
  not on the agent shell's PATH, which is an environment fact, not a repo defect.

## Alice

Consensus lens, implementation-aware, incremental scope. Six findings: three
high, two medium, one low. She verified each cycle-1 row individually, ran 14
probe cases plus a mutation run of the safety and parity files, and did not
re-run the full suite. No repo files were modified.

Her findings are R1, R4, R3, R2, R6 and R11 above.

Per-rule verdicts:

R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: fail
R11: pass
R12: fail
R13: pass

## Blake

Blind lens, PRD-only prompt: no diff, no file list, no review history, no design
doc, and no settled-decisions ledger. He located the implementation himself, ran
the three tree test files on the local Python (265 passed under
`-W error::DeprecationWarning`), and did not re-run the full suite.

Nine findings: one high, five medium, three low. They are R1, R7, R8, R9, R10,
R12, R13, R14 above, plus the one ledger-dismissed row listed earlier. He also
recorded what matches the spec: the ancestor rule, the runtime `data_filter`
detection with a manual member-by-member fallback, staged-sealed-renamed
extraction, and `contained`-based read containment all present.

Per-rule verdicts:

B1: fail
B2: pass
B3: pass
B4: pass
B5: fail
B6: fail
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: fail
B15: fail
B16: fail
B17: pass
B18: pass
B19: pass

## Bob

Doubt and de-slop lens, codex CLI, static-only sandbox, on the inlined prompt.
Five FIX items (two high, three medium), an empty VERIFY bucket, and one low
KNOWN item. They are R1, R5, R4, R3, R2 and R15 above. His VERIFY bucket being
empty is why no verification-check queue was written for this cycle.

Buckets as emitted:

- FIX: the unresolved directory-mode parity (R1); the incomplete
  `target_is_directory` classification (R5); the unpinned callable-filter
  regression (R4); the safe-ancestor refusal test satisfied by the existing
  landing-collision guard (R3); `build_template` over the 50-line limit (R2).
- VERIFY: (none).
- KNOWN: the mechanical replay's passing pre-change staging tests and safe-link
  controls, judged expected (R15).

Per-rule verdicts:

R1: fail
R2: fail
R3: pass
R4: fail
R6: pass
R7: pass
R8: pass
R9: fail
R10: pass
R11: pass
R12: fail
R13: pass

Doubt-rubric verdicts:

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Frontend and design specialist, generalist here; this diff has no UI surface, so
he reviewed it as a generalist. Backend `copilot`, model `gemini-3.8-flash`,
exit 0. He ran the `skills/use-qwen` tests, computed function lengths at both
revisions with `ast`, ran `ruff` over the touched files, and probed
`_ancestor_crossing` on the PRD's worked example.

One finding, medium: R2 above.

His `ruff check` run surfaced pre-existing `UP031` percent-format advisories
across `trees.py` and the known `F401` `bare_ci` fixture-import false positive.
Neither is raised as a finding: the percent-format style is the module's
existing convention and out of this diff's scope, and deleting the `bare_ci`
import would break fixture resolution.

Per-rule verdicts:

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

## Rubric disagreements worth naming

- R1 (tests cover every new behaviour): Alice, Bob fail; Carl pass; Blake's B1
  fail agrees. The fails are the better reading: R3 and R4 show that two of the
  three code fixes this cycle shipped have no test that can fail without them,
  and the computed replay independently names both tests.
- R2 (no obvious bugs): Alice and Bob fail, Carl pass. The fails are the better
  reading, on R1's measured raw `CalledProcessError`.
- R9 (implementation matches PRD feature behaviour exactly): Alice, Bob fail;
  Carl pass. R7 and R9 are each a named divergence from PRD text, so the fails
  hold.
- R10 (error handling): Alice fail, Bob and Carl pass. Alice's fail rests on R1's
  untranslated seal error, which is a real break of A9's output contract.
- R12 (code is maintainable): Bob, Carl, Alice all fail on the 53-line
  `build_template`; unanimous and computed, so it stands.

Verdict: 15 findings
Tests: 4532 passed, 0 failed, 9 skipped (suite run this cycle)

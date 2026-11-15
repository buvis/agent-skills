---
prd: docs/dev/project-management/prds/wip/00160-template-archive-extraction-fails-closed-v1.md
review: 1
date: 2026-11-05
head_sha: a8347f3c691d64e3eec1d2d124e3fa92953629bd
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 083774c0
  carl: f3aa72af
---

# Review: 00160-template-archive-extraction-fails-closed-v1

Diff range: `3c0c9dbb46b05bda8a01470e75d7e4e088684736..a8347f3c691d64e3eec1d2d124e3fa92953629bd`

codex_rung_guard: not fired

## Review Summary

Reviewed: 7 completed tasks
PRDs checked: 00160-template-archive-extraction-fails-closed-v1

Cycle 1, full review. Lane `full` (classified `full`, `security_path`). Every
required lens ran.

### Agent Status

- Alice (consensus, native Claude subagent, `autopilot:alice`, `claude-sonnet-5-5` at high effort): available
- Blake (blind PRD-only, native Claude subagent, `autopilot:blake`, `claude-sonnet-5-5` at high effort): available
- Bob (doubt + de-slop, codex CLI via `codex-run.sh`, `gpt-6-astra` at medium reasoning effort): available
- Carl (UI/design generalist, `gemini-run.sh` backend `copilot`, model `gemini-3.8-flash`): available

Model-family diversity this cycle: Anthropic (Alice, Blake), OpenAI (Bob),
Google (Carl). Three families, no `auto` selection and no silent downgrade.

**Correction.** An earlier revision of this file recorded Alice and Blake as
`opus/high`. That was wrong: it restated the pack's effort preamble instead of
the model actually dispatched. Their transcripts' `requestedModel` and
`message.model` are both `claude-sonnet-5-5`, at high effort. Bob's model was
read from his own run header (`model: gpt-6-astra`, `reasoning effort: medium`)
and was not recorded in the first revision at all. No finding, severity or
verdict changed with this correction; only the model evidence did.

Backend/model notes, as actually selected:

- Bob ran on the codex CLI (`gpt-6-astra`, provider openai, sandbox read-only,
  reasoning effort medium), exit 0, with the inlined prompt shape
  (`retry-policy.md` § Inlined prompt). The `--emit-thread-id` sidecar
  `docs/dev/tmp/bob-thread-00160-c1.txt` was written empty, so no
  `codex_thread_id` is stamped and cycle 2 runs Bob fresh.
- Carl's dispatch passed `-m gemini-3.8-flash` from the start. The helper's
  stderr recorded `gemini-run: backend=copilot model=gemini-3.8-flash`, exit 0.
  The runner's default copilot model is known to fail eligibility on this host,
  so the model was pinned rather than probed; no exit-4 latch was recorded and
  Carl stays active for this batch.
- `consensus_engine` resolved to `legacy`, so Alice's leg is the single Task
  subagent and no `review-fanout` workflow ran. No `consensus_run_id`.
- `doubt_reviewer` resolved to `codex`. No task carries
  `attempts[].implementor == "codex"` (all seven are `claude`), so the Codex
  doubt-roster guard did not fire and Eve was not activated.

### Degradations, stated loudly

- **Context pack unavailable.** `engram pack` exited 1
  (`not inside a registered repo; run gita add <this worktree>`). Every prompt
  carried the `(no pack available this cycle)` sentinel for `{PACK_FILE}` and
  `{PACK_FINDINGS}`. This review is degraded by the missing findings precedent,
  not invalid. An agent cannot run `gita add`; a human must register the
  worktree to restore it.
- **Test gate repaired before staging.** The first `review-stage` run produced
  `Tests: counts unavailable`, because this worktree's `.venv` console scripts
  carried a stale interpreter shebang pointing at the worktree's former
  location (`.../agent-skills-closeout/archive/.venv/bin/python`), left behind
  by an earlier `git worktree move`. `uv sync` alone did not repair it; the
  virtualenv was recreated pinned to Python 3.13. The suite was then run and
  recorded. The stale virtualenv is parked at
  `/tmp/agent-skills-closeout-archive-stale-venv-20261105`.
- **Consolidation corrected by hand.** `consolidate_findings.py` exited 0 but
  mis-merged on line-suffix stripping. Three corrections were applied and are
  itemised under "Consolidation corrections" below. The findings table is the
  corrected one.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [1/4] | 🔴 | Case-folding ancestor alias lets an accepted archive write outside `dest`. `A -> .` plus a member named `a/../outside/secret.txt` passes validation: the duplicate/case rule folds whole normalized names, so it never notices that `a` aliases the symlink `A` on a case-insensitive host. On the manual (no-filter) path `dest.joinpath(member.name)` then mkdirs through `dest/a`, which case-folds onto `dest/A -> .`, so `..` climbs out of `dest` and the payload lands beside it. Reproduced: the file appeared at `<box>/outside/secret.txt`, outside the tree root. The filter path keeps it inside (`tree/outside/secret.txt`), so this is also a parity break. Breaks the PRD's first success metric on the manual path. Validate case-equivalent components for ancestor and symlink lookups before extraction, and pin the regression on both seams | skills/use-qwen/scripts/eval_harness/trees.py:213 | 3 | BOB |
| R2 | [4/4] | 🟠 | Filter detection uses `hasattr(tarfile, "data_filter")`, but PRD A8 names `callable(getattr(tarfile, "data_filter", None))` explicitly. A `data_filter` attribute that exists but is not callable (for example `None`) takes the filtered branch and fails instead of falling back to the manual path. The test seam only hides the attribute, so the callable form is never exercised and no test pins it | skills/use-qwen/scripts/eval_harness/trees.py:308 | 4 | ALICE, BLAKE, BOB, CARL |
| R3 | [3/4] | 🟠 | The ancestor rule is narrower than the PRD text, which says to refuse any member whose path has an archive symlink as a proper ancestor, judged on normalized names. `_ancestor_crossing` compares `_land(prefix)` (which resolves `alias` to `pkg`) against symlink own-locations (`alias`), so a member directly beneath a safe symlink is accepted. Reproduced twice: `pkg/` + `alias -> pkg` + `alias/file.txt` is ACCEPTED, and `pkg/` + `alias -> pkg` + `alias/escape -> ../../outside` (no victim member) is ACCEPTED on the manual path, which seals an escaping symlink `pkg/escape -> ../../outside` into the template, while `filter="data"` refuses the same archive with `LinkOutsideDestinationError`. The four-member A1 case from the PRD is correctly refused in both member orders. Also test each raw prefix's own name, not only its landing, against `symlink_landings`, and give the manual path the link-target containment check `filter="data"` applies | skills/use-qwen/scripts/eval_harness/trees.py:169 | 3 | ALICE, BOB, CARL |
| R4 | [2/4] | 🟠 | Filtered and unfiltered extraction are not equivalent, against the PRD's "write an accepted archive identically whether or not `tarfile.data_filter` exists". The manual path calls `chmod(_safe_mode(mode))` on directories and files; `data_filter` ignores directory modes and forces owner read/write on regular files. Measured: a dir member at mode 0o500 holding a child is accepted on the filter seam and raises `TreeError("d/f: Permission denied")` on the manual seam; a file member at mode 0o000 seals on the filter seam (extracted 0o600) and on the manual seam leaks a raw `subprocess.CalledProcessError` from `git add` rather than a `TreeError`. Unreachable from `git archive` (which emits 0644/0755 only), but crafted archives are this PRD's stated threat model. Force owner read/write on files, skip or force 0o700 on directories, and wrap the seal failure | skills/use-qwen/scripts/eval_harness/trees.py:253 | 4 | ALICE, BLAKE |
| R5 | [1/4] | 🟠 | Manual extraction creates every symlink with `os.symlink(member.linkname, path)` and no `target_is_directory`, so on Windows a directory link, and a forward directory-link chain, loses the semantics the PRD requires. Determine the target's directory-ness from the validated archive graph and pass `target_is_directory` when creating the link | skills/use-qwen/scripts/eval_harness/trees.py:279 | 4 | BOB |
| R6 | [2/4] | 🟡 | `staging.mkdir(parents=True)` can create missing parent directories of `dest`, and the failure cleanup removes only the staging directory, so those created parents stay behind despite the docstring's promise that a failure leaves nothing. The `mkdir` also sits outside the `try`, so an `OSError` from it escapes as itself rather than as a `TreeError` | skills/use-qwen/scripts/eval_harness/trees.py:301 | 5 | ALICE, BLAKE |
| R7 | [3/4] | 🟡 | `test_build_template_injected_extraction_failure_leaves_no_dest_and_siblings_untouched` hedges with `or`: `reached is None or reached` is satisfied by the `None` case, so the two name-too-long parameters assert nothing. This is also the computed tautological-shape line. Separate the ENOSPC case from the filesystem-name failures and assert the exact member reached, keeping explicit coverage of both mechanisms | skills/use-qwen/scripts/test_eval_tree_archive_staging.py:266 | 5 | ALICE, BOB, CARL, mech-check |
| R8 | [1/4] | 🟡 | Failures after extraction raise raw errors instead of `TreeError`: `subprocess.CalledProcessError` from git init, add or commit, and `tarfile.ReadError` from a corrupt archive, both escape unwrapped. The PRD only mandates translating FilterError and `OSError` during extraction, so this is a gap in the documented guarantee rather than in the letter of A10. Cleanup uses `ignore_errors=True`, so a read-only directory produced by the manual path can leave the staging directory behind | skills/use-qwen/scripts/eval_harness/trees.py:315 | 6 | BLAKE |
| R9 | [1/4] | 🟡 | `contained` rebuilds the links map with a full `os.walk` of `root` on every call. `hash_paths` calls it once per path and `prove_state` calls `hash_paths` on every proof, so the cost is paths times tree size; a clone holding `node_modules` or build output is the bad case. `Path.resolve` was O(depth). Build the links map once per `hash_paths` or `overlay_oracle` call and pass it into the landing step, preserving behaviour | skills/use-qwen/scripts/eval_harness/trees.py:421 | 6 | ALICE |
| R10 | [1/4] | 🟡 | `except trees.TreeError: assert list(dest.glob("*")) == []` accepts a refusal as a pass, and `dest` is always empty or absent after a refusal, so a build that raised `TreeError` for every archive would still pass the refusal branch. The success branch does bite: with `_safe_mode` replaced by the identity function the no-filter parameters fail. Tighten the refusal branch by requiring success for the setuid and foreign-owner cases, which are git-archive-valid input, or by asserting the refusal reason | skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py:132 | 4 | ALICE |
| R11 | [1/4] | 🟡 | `build_template` raises `TreeError` when `dest` exists in any form, including an empty directory. The PRD says to refuse when `dest` already exists and is non-empty, and marks that rule a guess. The docstring documents the stricter behaviour, so this is a deliberate, documented deviation rather than a silent one | skills/use-qwen/scripts/eval_harness/trees.py:296 | 6 | BLAKE |
| R12 | [1/4] | 🟡 | `_lay_links` determines directory-ness from targets already present on disk, so a forward chain such as `a -> b`, `b -> pkg` types `a` incorrectly on Windows. Resolve the directory type through the supplied links map before creating each fixture link | skills/use-qwen/scripts/test_eval_tree_links.py:145 | 6 | BOB |
| R13 | [1/4] | 🟡 | The final rename can replace an empty directory created after the initial existence check on POSIX, so the docstring's create-only guarantee is stronger than the code. Raised by the doubt lens in its KNOWN bucket as a concurrency limitation outside the PRD's single-writer scope | skills/use-qwen/scripts/eval_harness/trees.py:323 | 5 | BOB |
| R14 | [1/4] | ⚪ | The seal-failure test accepts either `type(error)` or `TreeError`, so it cannot tell whether failures are translated. Pin one outcome per injected step, or document that the seal deliberately does not translate | skills/use-qwen/scripts/test_eval_tree_archive_staging.py:325 | 5 | ALICE |
| R15 | [1/4] | ⚪ | `if os.path.isabs(member.name): raise TreeError(... is absolute)` is unreachable: `_archive_name_escapes` on the line above already refuses a leading `/` and every Windows-absolute spelling. Dead code, droppable. The `isabs` inside `_land` is likewise redundant but the design asked for it | skills/use-qwen/scripts/eval_harness/trees.py:206 | 3 | ALICE |
| R16 | [1/4] | ⚪ | The case-collision check uses `str.lower()`, not `casefold()` or Unicode normalization, so names differing only by NFC/NFD form, or by a case-fold such as `ß`, still collide on macOS and Windows and are accepted | skills/use-qwen/scripts/eval_harness/trees.py:214 | 3 | ALICE |
| R17 | [1/4] | ⚪ | `_archive_name_escapes` tests `":" in component[1:]`, so a component that begins with a colon, such as `:stream`, is not refused. An edge of the NTFS stream-like rule | skills/use-qwen/scripts/eval_harness/trees.py:145 | 3 | BLAKE |
| R18 | [1/4] | ⚪ | The PRD's repository structure names three test files; the implementation adds two more, `test_eval_tree_archive_staging.py` and `test_eval_tree_archive_safety_modes.py`. A harmless split, raised for the record only | N/A | general | BLAKE |
| R19 | [1/4] | 🟡 | Computed fail-first replay: 54 touched tests in this file pass against the pre-change code at `3c0c9dbb46b0`, beginning `test_build_template_refuses_a_member_named_absolute_in_any_domain` and `test_build_template_refuses_a_link_whose_target_is_absolute_in_any_domain` | skills/use-qwen/scripts/test_eval_tree_archive_safety.py | general | mech-check |
| R20 | [1/4] | 🟡 | Computed fail-first replay: 27 touched tests in this file pass against the pre-change code, beginning `test_build_template_never_applies_setuid_setgid_or_a_foreign_owner_from_the_archive` | skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py | general | mech-check |
| R21 | [1/4] | 🟡 | Computed fail-first replay: 4 touched tests in this file pass against the pre-change code, beginning `test_build_template_still_seals_an_absent_dest_beside_siblings_sharing_its_prefix` | skills/use-qwen/scripts/test_eval_tree_archive_staging.py | general | mech-check |
| R22 | [1/4] | 🟡 | Computed fail-first replay: 2 touched tests in this file pass against the pre-change code, namely `test_build_template_refuses_every_absolute_target_shape_as_a_tree_error` | skills/use-qwen/scripts/test_eval_tree_state.py | general | mech-check |

### Consolidation corrections

`consolidate_findings.py` exited 0 and emitted 20 rows, then warned four times
that it had merged citations "only after suffix stripping". Three of those
merges were wrong, and all three are corrected above. Recorded so the
correction is visible rather than silent.

1. **A wrong merge, now split.** It folded Alice's staging-parent finding at
   `trees.py:301` together with Blake's untranslated-post-extraction-failure
   finding at `trees.py:315`. Those are different defects. They are R6 and R8
   above.
2. **A missed merge, now merged.** The ancestor-rule finding arrived three
   times with three citations (Alice `:169`, Carl `:165`, Bob `:168`). The
   script merged Alice with Carl and left Bob's as a separate row, so one
   defect read as a two-of-four consensus plus a single voice. It is R3 above,
   at three of four.
3. **A missed merge, now merged.** The hedged either-or assertion in the
   injected-failure test arrived three times (Alice, Bob, Carl) on the same
   file and line, as three rows. It is R7 above, at three of four, with
   `mech-check` appended as a fourth finder because the computed
   tautological-shapes block names the same test.

The four fail-first replay lines were absorbed as R19-R22, per the rule that
every `[MECH]` line becomes a finding. None matched an existing row's test.

### Coordinator verification

Three reviewer claims were reproduced against the code at `a8347f3` before
being ranked, and one was escalated as a result. The probes ran as isolated
scripts outside the repository, each under `python -I`, against crafted
`TarInfo` members and a throwaway destination with an outside sentinel.

- **R1 escalated from high to critical.** Bob reported it as permitting outside writes.
  It does, on this host: the filesystem under `TMPDIR` is case-insensitive
  (verified directly), the archive is accepted by
  `_refuse_duplicate_or_crossing_members`, and the manual extraction wrote
  `secret.txt` outside the destination tree. The PRD's first success metric is
  "No accepted archive can create, modify, or chmod any path outside `dest`, on
  either filter path", so a demonstrated out-of-`dest` write on an accepted
  archive is critical, not high. Severity raised on evidence; the finding and
  its finder are Bob's.
- **R3 confirmed and widened.** Both the safe-ancestor case Alice, Bob and Carl
  describe and a second shape nobody raised were reproduced: with
  `alias -> pkg` plus `alias/escape -> ../../outside` and no victim member, the
  validator accepts, `filter="data"` then refuses with
  `LinkOutsideDestinationError`, and the manual path completes and seals an
  escaping symlink into the template. The widened description is attributed to
  the same three reviewers; the extra shape is coordinator evidence for their
  finding, not a new reviewer voice.
- **The PRD's own A1 case is correctly refused.** All four members, in both
  member orders, raise `TreeError("pkg/escape/secret.txt is beneath an archive
  symlink")`. The 00158 finding this PRD was promoted to fix is closed.
- **Coverage hole behind R1 and R3.** Every parametrisation in
  `ANCESTOR_ESCAPES` carries a victim member that trips the landing-based rule.
  None covers an escaping link under a safe alias with no victim, and none
  covers a case-folding ancestor alias. That is why a passing suite coexists
  with these two findings.

Python-version metric, run directly rather than taken from the build record:

- Python 3.10, focused five-file set, `-W error::DeprecationWarning`: 326 passed.
- Python 3.12, same set: 326 passed. The first 3.12 attempt aborted with 50
  fixture setup errors from `git init` failing to spawn; the same set passed
  in isolation and passed again on re-run, so that was environment flake, not a
  code failure. Reported rather than hidden.
- Python 3.13: covered by the full-suite gate below.

## Alice

Consensus lens, implementation-aware. Ten findings: six medium and four low, no
critical or high of her own, though her ancestor-rule and mode-parity findings
are ranked high
above on consensus with Blake, Bob and Carl. She probed `build_template`
directly and ran one mutation check (`_safe_mode` as the identity function) on a
copy outside the repository. She did not run the full suite.

Her findings are R3, R4, R2, R9, R7, R10, R14, R15, R6 and R16 above.

Per-rule verdicts:

R1: pass
R2: fail
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

Blind lens, PRD-only prompt: no diff, no file list, no review history, no design
doc. He was given the project root and this cycle's `## Test gate` block, and
was told not to read `docs/dev/tmp/`, `reviews/` or `designs/`, so that he
located the implementation himself. He ran the focused tests on the local
Python (326 passed under `-W error::DeprecationWarning`) and did not run 3.10,
3.12 or 3.13 separately.

Seven findings: two high, three medium, two low. They are R2, R4, R11, R6, R8, R17 and
R18 above.

He also recorded what does match the spec: archive-domain name and target
classification independent of the host `os.path.isabs`; the ancestor,
duplicate, case-collision, landing-collision and type-refusal rules all
present; no bare `extractall` and no `fully_trusted`; staged-sealed-renamed
extraction removing only its own staging directory; `hash_paths` and
`contained` both routed through the `_land` walk; `_lay_links` passing
`target_is_directory`; and the chown spy tests present.

Per-rule verdicts:

B1: fail
B2: pass
B3: pass
B4: pass
B5: fail
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Doubt and de-slop lens, codex CLI, static-only sandbox, on the inlined prompt.
Six FIX items (three high, three medium), an empty VERIFY bucket, and one medium KNOWN
item. They are R1, R3, R5, R2, R12, R7 and R13 above. His VERIFY bucket being
empty is why no verification-check queue was written for this cycle.

Buckets as emitted:

- FIX: the case-folding ancestor alias (R1); the safe-symlink ancestor
  acceptance (R3); untyped Windows symlinks on the manual path (R5); `hasattr`
  instead of the callable check (R2); `_lay_links` forward-chain typing (R12);
  the hedged failure-injection assertion (R7).
- VERIFY: (none).
- KNOWN: the rename-over-empty-directory race (R13), justified as outside the
  PRD's single-writer scope.

Per-rule verdicts:

R1: fail
R2: fail
R3: pass
R4: fail
R6: pass
R7: fail
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
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
exit 0. He probed `_ancestor_crossing` and `_refuse_duplicate_or_crossing_members`
directly and ran the focused tests.

Three findings, one high and two medium: R3, R7 and R2 above.

Per-rule verdicts:

R1: fail
R2: fail
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

## Rubric disagreements worth naming

- R1 (tests cover every new behaviour): Alice pass, Bob and Carl fail. The
  coverage hole behind R1 and R3 above is concrete, so the fails are the better
  reading.
- R4 (changed components integrate with existing callers): Bob fail, Alice and
  Carl pass. Bob's fail rests on his Windows symlink-typing finding (R5), which
  is a real gap on a platform this suite only simulates.
- R7 (user input validated and sanitized): Bob fail, the rest pass. Bob's fail
  rests on R1, the demonstrated out-of-`dest` write, which makes it the better
  reading.
- R9 (implementation matches PRD feature behaviour exactly): all four fail. R2,
  R3 and R11 are each a named divergence from PRD text.

Verdict: 22 findings
Tests: 4495 passed, 0 failed, 9 skipped (suite run this cycle)

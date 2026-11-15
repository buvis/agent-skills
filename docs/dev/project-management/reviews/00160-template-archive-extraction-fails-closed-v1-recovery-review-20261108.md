---
prd: docs/dev/project-management/prds/hold/00160-template-archive-extraction-fails-closed-v1.md
review: standalone-recovery-20261108
date: 2026-11-08
head_sha: 39b97f32ac47fcfa61fe70f55c6e3348ada9a796
reviewers: alice,blake,bob,eve
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
  eve: available
---

# Standalone recovery review: PRD 00160

Diff range: `373be1f1f280efa8f0690b3ad0d15454bc65e468..39b97f32ac47fcfa61fe70f55c6e3348ada9a796`

codex_rung_guard: not fired

## Outcome and boundary

The four blocking cap regressions (original cycle-2 R1, R3, R4, R5) and
function-length finding R2 are resolved. Two supported LOW documentation
corrections remain (recovery R5/R6 below). No new HIGH/CRITICAL cap regression
was found. Existing deferrals, the accepted .git exclusion, and a newly recorded
drive-relative follow-up remain visible. The next action is a narrow repair
session, followed by a fresh review of its resulting SHA.

This is a standalone branch-repair review under installed autopilot 0.10.0
`recovery.md`'s `cap_regression` route, explicitly targeting held PRD 00160
with `[]` tasks. It is NOT original review cycle 3. Eve's raw heading uses
that label incorrectly; it is reviewer prose, not a state transition. The
original two-cycle cap, reports, store, held PRD, 29 deferred rows, and ledger
keys remain unchanged. No tasks were created or marked completed. No default
entry, selection of 00133, `review-close`, phase transition, push, or publication ran.

The standalone task-telemetry predicate cannot fire because no task attempts
exist. The guard line records that fact. Codex implemented the repair, so the
implementation-diversity requirement was independently enforced by explicitly
adding Eve, Anthropic Fable 5. No task count was invented.

## Execution and limitations

- Alice: separate native Claude `claude-sonnet-5-5`, explicit high effort;
  implementation-aware consensus, generated persona and context/design inputs.
- Blake: separate native Claude `claude-sonnet-5-5`, explicit high effort;
  generated PRD-only blind prompt plus test-gate facts. No diff, design,
  changed-file list, ledger, prior findings, or peer outputs supplied.
- Bob: installed Codex helper refused nested dispatch, exit 3, before inference.
  The prescribed Claude fallback used a separate `claude-sonnet-5-5` session,
  high effort, and the exact inlined doubt/de-slop prompt. All consensus and
  D1-D5 verdicts were present.
- Carl: installed Gemini helper refused nested dispatch, exit 3, before any
  backend ran. This was a guard refusal, not permanent model unavailability.
  No unchanged retry or guard bypass was attempted; Carl is not counted.
- Eve: separate native Claude `claude-fable-5`, explicit high effort;
  PRD-only doubt/de-slop inputs, D1-D5 verdicts, independent mutation checks.

Model identities were verified in stream init/assistant events and terminal
`modelUsage`. All four native terminal results succeeded. The roster is
degraded: no Codex or Gemini inference ran, so this review has no independent
provider voice. The prescribed Bob fallback preserved his lens; Eve preserved
the additional Anthropic voice required after Codex implementation.

No native Claude Task tool is exposed on this host. The equivalent native CLI
adapter pinned `Read,Bash`, retained hooks, used `dontAsk` permissions and
read/test allow rules, and granted neither Edit/Write nor permission bypass.
Bob's inlined prompt prohibited tool use and his fallback used none. The
installed Sonnet helper lacks an explicit effort flag, so the adapter supplied
the model, effort, tool and logging flags directly. CLI refusal records were
closed as errors in separate recovery telemetry, never in the original store.

`review-stage` ran in standalone mode with explicit held PRD, design, roster,
base, settled ledger, prior review, canonical gate and per-file replay. No
staging errors occurred. Engram failed because the worktree is not
gita-registered; applicable prompts used the documented no-pack sentinel.

Bob's generated prompt was preserved before the required inline assembly.
The shared staged context contains the design; a separate PRD-only copy removes
only the Design Doc block through the next mechanical-facts heading for Bob's
doubt input. Original context and generated prompt remain intact. Alice retained
the design; Blake and Eve never received it. Outputs were saved only after all
reviewers terminated. Reviewer outputs were not rewritten to improve verdicts.

## Verification

Canonical full gate at the reviewed SHA:

`UV_PYTHON=3.13.18 bash <main-checkout>/docs/dev/tmp/closeout-stage-2-20261105-run/pytest-gate.sh`

Result: `PASS 4598 FAIL 0 SKIP 9 EXIT 0`, 501.53 seconds. The installed verifier
wrote the canonical HEAD record. The 53 warnings concern prior red/replay temp
trees. No POSIX assertion was removed and no platform skip was added.

Alice ran both touched test modules: 114 passed with DeprecationWarnings as
errors. Eve ran six archive/tree modules on Python 3.13.18 (429 passed), and
the touched modules on 3.10.22 and 3.12.16 (114 each). She restored the venv to
Python 3.13 afterward.

Independent replay reproduced three restrictive-directory failures at base
and two passing controls. A `hasattr` mutant fails the fallback-path test.
Disabling `_ancestor_crossing` fails both refusal seams while safe-link controls
pass. This confirms the repair session's recorded Python 3.10 evidence and
three expected mutation failures. The temporary detached replay worktree was
removed. Old pytest garbage directories remain after a chmod permission denial;
no denial was bypassed and no broad cleanup is required to complete this review.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Found By |
|-----|-----------|----------|-------|------|----------|
| R1 | [4/4] | 🟡 | Original cycle-2 R7: manual/filter executable-bit parity remains a PRD A7 wording conflict. | skills/use-qwen/scripts/eval_harness/trees.py:347 | Alice, Blake, Bob, Eve |
| R2 | [3/4] | 🟡 | Original cycle-2 R6: per-link map rebuild remains; implied-parent traversal increases its cost. | skills/use-qwen/scripts/eval_harness/trees.py:309 | Alice, Bob, Eve |
| R3 | [2/4] | 🟡 | Original cycle-2 R9: raw-spelling collision sets accept pkg plus Pkg/x. | skills/use-qwen/scripts/eval_harness/trees.py:293 | Alice, Eve |
| R4 | [2/4] | 🟡 | Original cycle-2 R10: native-separator fixture probe remains unimplemented. | skills/use-qwen/scripts/test_eval_tree_links.py:145 | Alice, Eve |
| R5 | [2/4] | ⚪ | The current _safe_mode docstring still claims application to directories. | skills/use-qwen/scripts/eval_harness/trees.py:299 | Alice, Bob |
| R6 | [2/4] | ⚪ | The historical Ivan assumptions bullet needs an explicit superseded note after directory chmod removal. | docs/dev/project-management/meta/assumptions.md:87 | Alice, Bob |
| R7 | [1/4] | 🟠 | Explicitly hashing a symlink below .git can read outside bytes; the design recorded this excluded input surface. fresh_clone copies the link itself. | skills/use-qwen/scripts/eval_harness/trees.py:520 | Blake |
| R8 | [1/4] | 🟡 | contained does not reject drive-relative names; writable/oracle validation does not fully exclude C:x. | skills/use-qwen/scripts/eval_harness/trees.py:517 | Blake |
| R9 | [1/4] | 🟡 | Windows-native directory-link behavior and Q4/Q5 still require the planned hosted CI run. | skills/use-qwen/scripts/test_eval_tree_links.py:141 | Eve |
| R10 | [1/4] | 🟡 | Original cycle-2 R8: manual extraction relies on pre-validation rather than O_NOFOLLOW/lstat. | skills/use-qwen/scripts/eval_harness/trees.py:339 | Eve |
| R11 | [1/4] | 🟡 | Mechanical replay reports two function names with passing base cases: callable-filter and restricted-directory parity tests. | skills/use-qwen/scripts/test_eval_tree_archive_safety_ancestor_parity.py:50 | mech-check, Eve |
| R12 | [1/4] | ⚪ | Cleanup-warning claim: pytest reported an old garbage staging directory; no current HEAD staging leak was demonstrated. | skills/use-qwen/scripts/eval_harness/trees.py:423 | Blake |
| R13 | [1/4] | ⚪ | The seal helper no longer repeats the pretask.json rationale for the stable date. | skills/use-qwen/scripts/eval_harness/trees.py:368 | Bob |
| R14 | [1/4] | ⚪ | Original cycle-2 R12: helper symbols exceed the PRD inventory; _seal_template extends it. | skills/use-qwen/scripts/eval_harness/trees.py:368 | Eve |
| R15 | [1/4] | ⚪ | Original cycle-2 R13: concurrent writes in a newly created ancestor are outside the single-writer model. | skills/use-qwen/scripts/eval_harness/trees.py:423 | Eve |
| R16 | [1/4] | ⚪ | Original cycle-2 R14: staging mkdir precedes validation and corrupt-tar ReadError remains untranslated. | skills/use-qwen/scripts/eval_harness/trees.py:403 | Eve |

## Adjudication

The installed consolidator ran successfully. Model-side consolidation then
merged its two split duplicates (file-mode parity and assumptions), added Eve's
bucket findings/voices and Bob's explicit KNOWN/VERIFY support, and absorbed
the mechanical row. The script does not parse Eve's bucket format. Its raw
table is preserved in the execution transcript; raw reviewer files remain
unaltered. The 16 rows include known, deferred and disproved findings, not 16
new repair tasks.

- **R5: supported LOW correction.** Describe regular-file mode stripping in
  `_safe_mode`'s docstring. Directory handling and the newer extraction
  docstring are already correct.
- **R6: supported LOW correction.** Keep the historical statement in
  `assumptions.md:87`; append a superseded note stating recovery R1 removed
  deferred directory chmod. Directories now use mkdir defaults and umask,
  matching data_filter. Alice's line-23 citation identifies the ledger heading;
  Bob's line 87 identifies the actual bullet. Preserve history.
- **R1/R2/R3/R4/R10/R14/R15/R16: retain existing dispositions.** These are
  original deferrals, not newly solved findings. R2 adds work per symlink but
  demonstrates no new correctness failure or violated performance criterion;
  the performance deferral remains open. `_seal_template` is required by the
  repair's R1/R2, not speculative indirection. No deferred row is closed here.
- **R7: accepted excluded surface, not factually impossible.** The original
  design's Review log at line 495 explicitly records that `_walk` excludes
  .git links and excludes them as legitimate hash inputs. Coordinator
  reproduction confirms the outside hash. `fresh_clone` uses
  `copytree(..., symlinks=True)`, copying the link rather than target bytes;
  the outside sentinel remains unchanged. Retain the known limitation without
  treating it as a new branch-repair regression.
- **R8: new durable follow-up outside this repair.** `_is_repo_relative`
  rejects drive names only for read anchors. Writable/oracle lists use
  `_text_tuple`, and `_write_seal` hashes before record validation. This cannot
  be dismissed as universally prevalidated. `_slash_sorted` normalizes normal
  caller backslashes, so that part of the example does not demonstrate a
  normal-call escape. Investigate and pin drive-relative handling on Windows
  separately. No original deferred key was repurposed and no native Windows
  execution is claimed.
- **R9: external verification pending.** Keep the planned exact-SHA approval
  and hosted Windows dispatch gates. This standalone review creates no
  verification queue and dispatches no CI workflow.
- **R11: discharge with evidence.** The base already contains callable
  detection; the stronger observation test correctly passes there and fails
  the `hasattr` mutant. Directory mode 0o755 is a valid passing control;
  0o000/0o200/0o500 fail at base. The replay parser drops parameter IDs. Parent
  and Eve independently verified this. The mechanical row is retained visibly.
- **R12: reject the claimed new leak.** Blake's warning names an old
  `pytest-of-.../garbage-.../template.staging-*` tree. Current seal-failure
  tests assert exact sibling-name equality after every injected failure and
  pass across the matrix. No HEAD staging leak was reproduced. Hypothetical
  cleanup failure is not evidence that this repair regressed.
- **R13: optional wording, not required repair.** The helper documents a
  stable date and applies the same SEAL_DATE to both Git timestamps. Its
  caller, deterministic-seal coverage and behavior are unchanged.

### Auto-dismissed (ledger)

- Blake's existing-empty-destination narrowing: the existing ledger accepts
  the documented fail-closed behavior for the PRD's explicitly guessed rule.
- Blake's repeated whole-tree hashing cost: the existing ledger treats this
  as separate performance work and preserves the shared containment walk.

## Triage: stub 00171 / key 6c34669148b8

Decision: close as an already-fixed cycle-1 critical, not a newly accepted
escape. The cycle-2 report explicitly closes the case-folding ancestor escape
with both-seam and mutation evidence. Recovery does not weaken that logic;
the fresh full/archive runs retain the regressions, and Eve independently
proved the ancestor refusal remains discriminating. This is distinct from
the excluded .git read surface and new drive-relative follow-up.

This report records the triage decision while retaining stub 00171 in hold
and preserving its history/key for the review boundary. No renumbering,
ledger rewriting, original-store mutation, or completed-task claim occurred.
All 29 historical rows remain intact; unrelated deferrals retain their status.

## Alice

Raw return: `docs/dev/tmp/alice-output-recovery-20261108.txt`.
Confirmed original R1-R5 resolved; reported recovery R1-R6. The implementation
aware PRD verdict remains fail because original deferred gaps remain.

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

## Blake

Raw return: `docs/dev/tmp/blake-output-recovery-20261108.txt`.
Blind findings are retained as recovery R1/R7/R8/R12 and ledger dismissals.
His .git probe was independently reproduced and scoped, not denied.

B1: fail
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
B14: fail
B15: pass
B16: fail
B17: pass
B18: pass
B19: pass

## Bob

Raw return: `docs/dev/tmp/bob-output-recovery-20261108.txt`.
Claude fallback confirmed original R1-R5 resolved, no new HIGH/CRITICAL.
FIX: performance rebuild, stale assumptions, optional rationale comment.
VERIFY: `_safe_mode` docstring wording, confirmed by coordinator inspection.
KNOWN: unchanged executable-bit parity/spec tension. Dispositions above
adjudicate the buckets rather than silently accepting every proposed fix.

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

## Eve

Raw return: `docs/dev/tmp/eve-output-recovery-20261108.txt`.
Confirmed original R1-R5 empirically; no new-diff regression. FIX bucket:
original cycle-2 R7/R9/R10. VERIFY: hosted Windows check. KNOWN: original
R6/R8/R12/R13/R14 and discharged mechanical replay. These retain their
existing deferrals and external gates; they do not restart the capped review.
The raw heading's “cycle 3” is explicitly corrected by this report.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Evidence and preservation

Repair-worktree-relative artifacts:

- `docs/dev/tmp/*-prompt-recovery-20261108.md`: dispatch prompts;
  `bob-staged-prompt-recovery-20261108.md` and
  `bob-prd-only-context-recovery-20261108.md`: preserved derivation.
- `docs/dev/tmp/*-native-recovery-20261108.jsonl` and `.stderr`: native model,
  permission, tool-call and terminal-result evidence.
- `docs/dev/tmp/*-output-recovery-20261108.txt`: unedited final returns.
- `docs/dev/tmp/gate-recovery-20261108.log`: canonical full gate.
- `docs/dev/tmp/recovery-ledger-20261108/`: isolated CLI telemetry; Bob
  `a29ff8b8` and Carl `9abf5819` closed with exit-3 refusal evidence.
- `docs/dev/tmp/recovery-preservation-20261108.json`: 48 original report/store
  hashes, all unchanged after review. All 29 deferrals remain intact.

No source or assumptions repair was made in this review session. Findings
were reported, not written as tasks. Correct the two supported documentation
statements in a separate repair session, then review the new SHA freshly.

The installed report shape gate passed with both codex-guard checks enabled;
the staged diff whitespace check passed. Live `braid --check` reports the same
nine unrelated link mismatches for copy-rich-text, create-note, and
explain-bim-system across three hosts. No live links changed. No skill changed,
so no changed-skill validator applies to this report-only commit.

Verdict: 16 findings
Tests: 4598 passed, 0 failed, 9 skipped (suite run this cycle)

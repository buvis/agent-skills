# Unpublished-change review — 2026-10-30

## Outcome and scope

The interrupted PRD 00133 state was committed first (`18d7085`). Master then
had 310 commits ahead of remote master. Of these, 147 have published equivalents
through migration PR #17. The earlier filter-branch pass stripped signatures
and changed their IDs, making Git report misleading divergence.

The user chose to preserve the 147 published commits and regroup only the
163 local commits. Master now descends from the original signed `6091e02`
and contains 12 signed component commits. Candidate `6c82516` has exactly the
same tree as `18d7085`; a separate hygiene commit updates this review and the
capsule. No runtime changes were made during grooming. Nothing was pushed.

Review covered the net production changes since `origin/master` across 12
skills, braid, and CI/documentation, plus relevant regression tests and held
findings. The original range changed 235 files, mostly work-management records.
Historical telemetry and every test line were not independently re-reviewed.
This is a Git/content review, not a replacement for an autopilot review gate.

## Findings

### HIGH — archive compatibility path still permits an escape

`skills/use-qwen/scripts/eval_harness/trees.py:183` extracts without a filter
when `tarfile.data_filter` is unavailable. Its preflight misses a symlink stored
under another symlink: `pkg/`, `alias -> pkg`, `alias/escape -> ../../outside`,
followed by `pkg/escape/secret.txt`.

A disposable crafted-archive probe against `build_template` confirmed:

| Path | Outcome | Sentinel outside destination |
|---|---|---|
| With data filter | `LinkOutsideDestinationError` | unchanged |
| Without data filter | accepted | overwritten |

All probe files were inside one temporary directory. Git archive output was
stubbed; this confirms the crafted-archive boundary, not an exploit against
an ordinary Git-generated archive. This remains owned by held PRDs 00156 and
00158. Do not describe PRD 00131 as complete containment hardening or treat
the green suite as closure. Repairing that security contract is outside this
tree-preserving history regroup; retain the finding before publishing/releasing.

### Known gaps — compatibility coverage and Windows verification

Held PRDs 00155–00157 retain missing rejection cases, unsafe compatibility
metadata handling, and the omitted-filter warning. The local full suite passed
with two extraction deprecation warnings, not warning-free.

Remote master run 40584704851 failed 60 Windows Qwen harness clone-path/hash
tests. The current migration run 41030058506 passed Linux 3.10/3.13, lint,
Node, and shell; Windows was in progress when recorded. A macOS pass does not
prove the Windows baseline repaired.

### Resolved — ancestry and stale recovery guidance

Restored the exact original 147 published commits as ancestors, preserving
their signatures. Compared the regrouped tree byte-for-byte against the
checkpoint before moving master. The private migration plan is absent from
every local branch's history. The old pending-purge project memory is corrected
so a later session does not repeat the history rewrite.

### Metadata follow-up

PR #17 still names follow-up PRD 00150 in its body. The branch contains 00159.
This does not affect executable behavior; update the description with the next
authorized PR metadata edit. The branch itself remains unchanged at `9249695`.

## Grouped local commits

Each component commit contains both implementation and its accompanying tests.
The reverted PRD 00111 implementation has no net change to carry from the
published base; its custody resolution remains in the work records.

| Commit | Subject |
|---|---|
| `2396578` | fix(audit-qwen): report discovery fallback and create output parents |
| `53524cb` | fix(distil-memory): warn when queue reads target missing files |
| `05e711d` | fix(glean): fingerprint large directories and tolerate vanished files |
| `0d03721` | fix(purge-devtmp): preserve repository context for linked stores |
| `62874a2` | fix(review-deps-prs): paginate repository enumeration with GET |
| `b037a0d` | feat(cli): provide help for survey and design review scripts |
| `08dc1aa` | fix(review-prd-backlog): distinguish evidence and examples from references |
| `ee0f3d6` | test(sweep-fix): account for measured search startup time |
| `147d146` | fix(use-qwen): validate archive members and use available data filters |
| `d535891` | fix(braid): report unreadable state encoding without a traceback |
| `306d72f` | docs: refresh release notes and portable invocation guidance |
| `6c82516` | chore(autopilot): consolidate run records and preserve held work |

The final hygiene commit follows these 12 groups. The resulting ahead count
is 160: 147 published commits + 12 local groups + 1 hygiene record.

## Branch review

| Branch | Tip at review | Decision and evidence |
|---|---|---|
| `master` | `6c82516` before report commit | Keep; grouped and verified |
| `feat/skill-migration-bundle` | `9249695` | Keep local/remote; open PR #17, eight migration commits |
| `agoge/authored-tests-2026-10-26` | `ea71a0a` | Keep; one unmatched commit, 259 lines of tests across eight files |
| `custody/00111-braid-state-misses-link-removals-v1` | `2921bc0` | Keep; deliberately preserved implementation for held PRD 00111 |
| `fast-track/00098-damaged-transcript-aborts-memory-scan-v1-c1` | `9dd5b84` | Keep; three unmatched commits, held PRD 00098 |
| `fast-track/00100-link-check-scans-outside-root-v1-c1` | `8ab8c15` | Keep; three unmatched commits, held PRD 00100 |
| `fast-track/00112-glean-crashes-invalid-ledger-structure-v1-c1` | `7d8bea0` | Keep; three unmatched commits, held PRD 00112 |
| `origin/renovate/node-26.x` | `78596db` | Keep; open PR #16 |
| `origin/renovate/astral-sh-setup-uv-10.x` | `34a0622` | Keep; open PR #15 |

Patch-equivalence checks were used alongside ancestry; signature/history
rewrites make ahead counts alone unsuitable for deciding branch disposal.
No remote or local branch was safe to delete under the retained-work policy.

## Verification and recovery

- Before-groom source: `18d708511dc67218d9414402265ca508f9997094`.
- Published base: `6091e02c41e823f3bd061434edf8bd389ffea8d0`.
- Tree-identical grouped tip: `6c82516c4a5fd24d393c700f4ec72de0d230812d`.
- Local full suite from this recovery session: 4258 passed, 9 skipped.
  No production/test content changed afterward; the tree comparison supports
  reusing that result rather than rerunning an identical seven-minute suite.
- Ruff passed; all 12 affected skills validated; braid reported zero drift.
- Original refs, full bundle, state snapshot, group map, probe and logs remain
  under `.git/recovery-20261030/`. Those private backups must stay local.
- Ignored autopilot `work_start_sha` follows the final grooming tip, keeping
  these housekeeping changes out of PRD 00133's resumed review diff.

# PRD 00089 tail sweep

Cycle 1 entered through the existing converged-review handoff. Tasks 2 and 3
are complete. No completion-review cycle was reopened, and cycle remains 1.

## Changes and checks

- `6f78731`: task 2 regression tests for fresh units' empty Git directories
  and empty units' directory timestamps, including mixed fresh/stale units.
- `a47fdd3`: task 2 extracts `newest_file_mtime` and shares `is_repo_unit`.
- `c64b3ee`: task 3 clarifies relative-path linkage and member-only PRD numbers.
- Focused module: 19 passed, exit 0. Default uv cache was inaccessible;
  a temporary cache or the existing virtualenv ran the same module.
- Regression tests were green before this behavior-preserving refactor.
  Isolated broken copies prove their signal: removing the pruning guard fails
  3 tests; replacing the directory timestamp fallback with zero fails 2 tests.
  The working tree was never mutated for these checks.
- Task 2: style_gate: clean, split_hygiene: clean.
- Task 3: style_gate: clean, split_hygiene: skipped:no-tests.
- Self-deslop: skipped:trivial for both tasks, per the source size gate.
- Skill validator passes; `bin/braid --check` reports zero drift.
- Full suite through `autopilot verify`: 3957 passed, 0 failed, 9 skipped,
  236 warnings, exit 0, 323.40 seconds. The gate recorded a clean result at
  `c64b3eeca39977f3156c266e50e50e4f5ea28bda`. The command used the existing
  `00089-review-gate.py` summary adapter, Python 3.12 selection, and an approved
  command scope required by macOS icon tests. Raw log:
  `docs/dev/tmp/00089-tail-sweep-full-suite.log`.
- No queued verification checks exist for this cycle.
- All three native workers reported `ASSUMPTIONS: none`. The existing assumptions
  ledger concerns an earlier PRD's runbook/harness work; it supplied no assumptions
  for this sweep and was preserved.
- No extra worktree or executed plan file was created.

## Independent task review

Pat ran through the real use-sonnet wrapper with no tools, explicit high effort,
fresh session IDs, and existing guards. Both outputs passed `parse_review.py`.

Task 2 session `0b710ee9-f46d-45ab-8f51-3905fc3634b8`, dispatch `4f9ae9cf`:
all four findings resolved. The reviewer verified the empty-directory test,
extracted timestamp walk, shared predicate, and distinct empty-unit timestamps.
One Low suggests dropping the second parametrized fresh fixture. Discarded:
the mandated test-author rubric explicitly requires distinct fixture values,
and the case verifies distinct content and age values at negligible runtime.

Task 3 session `a06699a6-b1c1-48fb-bf47-1b1b1889739d`, dispatch `44d13234`:
the member-path documentation finding resolved. One Low suggests defining
repository units before first use. Not retried under the source Low-only rule:
the definition follows in the same paragraph, and another polish loop would
exceed the converged sweep's scope. The micro lane retained Pat even though
the general documentation-only lane permits skipping him.

Raw task-review outputs: `docs/dev/tmp/review-task-2.md` and
`docs/dev/tmp/review-task-3.md`. These per-task reviews do not replace the
three-lens provider review or its receipts.

## Implementation provenance

Source row 7 selected native Sonnet: Qwen eligibility and Codex-interception
metadata were absent. Host mapping used OpenAI `gpt-6.1-sol`, medium effort,
for all three workers. An independent Anthropic route was available, so no
unsupported-provider fallback was needed. Task 3 qualified for the source
micro lane: one Low finding, one clean file, net two lines. The coordinator
made that documentation edit; its observed model is also `gpt-6.1-sol`.

Raw session metadata and turn-context records were copied, unchanged, into
the ignored `autocodex-sessions/` directory. These records, rather than the
launcher name, establish the actual model. Each row below cites line 10 of
`docs/dev/project-management/autopilot/autocodex-sessions/<file>`; hashes cover
line bytes excluding the newline.

| Role | File | Effort | SHA-256 |
|---|---|---|---|
| Task 2 Tess, dispatch d6f53c00 | 01a17276-79b7-70a1-9cd8-198e33e8ed2d.jsonl | medium | 9f3c85c294ce892b4c28fc59939a0780afeeae32810d6601a3cede55f7fe8239 |
| Task 2 Tess correction, dispatch 10db4988 | 01a17277-d653-7543-b2c2-9a4a81accce8.jsonl | medium | e53e4169ad3aa5eba2b932ff519b9a65c9d4d6de1736b13a7fa907418644d3d0 |
| Task 2 Ivan, dispatch 33fda591 | 01a17278-82e1-7811-975b-a70e3dba6bd6.jsonl | medium | b637ee51bcefb7283ee0630d17745163aa1b377674e66b8513f4999c3dc8592f |
| Task 3 coordinator implementation | rollout-2026-10-25T10-47-50-01a17275-925c-7190-9bc7-6514742b69cf.jsonl | low | fd2753d1c7daf6a7be5880b7cc9811663cf799e1a42536dd7c3baab6a32cc061 |

The first three session metadata records name their exact `/root/` agent paths
and parent session. These correlate with task 2 dispatch prompts and ledger IDs.
The coordinator session performed only task 3's prose implementation; guardian
and read-only reviewer models are excluded from implementation attribution.
State attempt records retain actual model, provider, launcher, and session IDs.

## Host-contract blocker

The original reviewed implementation audit and receipts remain unchanged.
The source `phase-review.md` Tail sweep step 4 requires finalizing without
another review cycle. The host contract additionally requires unchanged
implementation provenance at convergence. Actual tail-sweep attempts necessarily
change that provenance. The installed host's `adapter.review_gap`, called on
an in-memory prospective `phase: done` state, returns exactly:

`implementation changed since the converged review`

No state transition to done was attempted, no model history was relabeled,
and no receipt or reviewed snapshot was rewritten to hide this mismatch.
An operator must authorize a fresh full provider review or adapt the host's
tail-sweep policy. Any review must occur in a fresh session because this session
implemented the sweep. Keep cycle 1 and the original reviewed snapshot until
the operator selects the recovery path.

The state CLI persisted `phase: paused`, `next_phase: paused`, and
`pause_reason.site: host_tail_sweep_provenance`. Task count is 3/3 completed.
Schema validation and task-count consistency checks passed. The source review
shape/constraint gate also passed against the preserved cycle-1 review.

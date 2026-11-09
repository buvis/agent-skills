# PRD 00133 build

Outcome: stopped at card gate 2 (`uv run pytest`). No completion review ran.
The fast-track red-gate policy requires `fast_track_blocked` parking; it does
not authorize another implementation pass or allowlist expansion in this run.

## Changes

- `c49d87c`: separate regression tests, observed red before implementation:
  12 failed, 43 passed, exit 1.
- `ac18d34`: preserve an actual empty `--tools` argv element, add
  `--strict-mcp-config`, and encode triage snippets as JSON string data beneath
  an explicit untrusted-data instruction. No unrestricted retry was added.
- Targeted gate: 55 passed, exit 0. stdin, model tier, timeout, session and
  existing classification/error behavior remain covered.

Installed `claude --help` verified both restriction flags. No live judge or
user transcript corpus was used.

## Full-suite failure

The shared `FakeClaudeCli` in
`skills/distil-memory/scripts/funnel_test_helpers.py:172` still determines
triage verdicts with `prompt.endswith(self.transient_texts)`. JSON string
encoding changes the suffix, so the fake incorrectly answers durable for
transient fixtures. The full-suite distil integration test detects this.

This helper is outside the card's fixed three-file allowlist. A future recovery
must include the helper in the authorized card scope, update only its cheap-tier
framing decoder while retaining strong-tier routing and integration assertions,
then rerun the entire gate sequence. This is diagnosis, not an implemented fix.

Failing test:
`test_funnel_distil.py::test_main_with_distil_reports_zero_rather_than_n_a_when_a_triage_that_answers_keeps_nobody`
at line 275. Expected `survivors: 0`; the fake produced `survivors: 2`.

## Gate results

| Command | Result |
|---|---|
| `uv run pytest skills/distil-memory/scripts/test_funnel_triage.py skills/distil-memory/scripts/test_funnel_main.py` | 55 passed; exit 0 |
| `uv run pytest` | 4,392 passed, 1 failed, 12 skipped; exit 1; 345.96 seconds |
| `uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory` | Valid; exit 0 |
| `uv run braid --check` | 164 current, zero drift; exit 0 |
| `git diff --check` | exit 0 |

The validator and final braid check are unaffected diagnostic checks after the
red suite; they do not clear the stop. The full suite was run once.

Exit: stopped: gate 2. No branch was created; no surviving review finding
triggered the separate branch/reset exit rule.

batch suite: 4392 passed, 1 failed, 12 skipped, exit 1

## Reviews and provenance

Alice, Blake and Bob were not dispatched over a red gate. The host's fresh
work/review session boundary supersedes the source's in-session fast-track
roster. No finding was verified, no review passed, and no convergence is claimed.
No Carl lane was requested. The implementation model audit and worker-result
records are retained beside this report.

## Scope and cleanup

Implementation touched exactly the card's three files. Commits remain local.
No worktree, temporary branch, or executed plan was created. Temporary prompt
inputs belong to this held PRD and remain available for recovery.

Concurrent closeout reports, the closeout plan, agoge profile and host metrics
are foreign work. The handoff records only this run's owned store paths using
the source `record_store` function with a scoped git callback, preserving those
concurrent files unstaged. This adapts the broad store pathspec without changing
the installed plugin or the workflow state writer.

## Dispatch counts

```text
fast-track:ivan 1
fast-track:tess 3
```

Counts include the older lost Tess dispatch and this run's no-edit input-budget
abort plus its successful retry. See the model audit for session correlation
and the retained late-resume telemetry correction.

Canonical stall succeeded and the wip-to-hold move was verified. State schema
and reset task counts pass. Item duration starts at this session’s first dispatch;
the older dispatch is outside the recorder’s 24-hour admission window.

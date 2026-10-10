---
default_model: sonnet
model_tier_rationale: exact argv change given, the existing argv test is updated in place
design: skip
---

# distil-memory's judge calls write transcripts into the corpus the next run scans

## Problem

`judge()` in `skills/distil-memory/scripts/funnel.py` (line 178) runs
`claude --print --model <tier> <prompt>` with the repo root as cwd, so every
triage and distil call persists a session transcript under
`~/.claude/projects/<this repo>/`, exactly where `select_transcripts` reads.
The task-11 live run measured 153 selectable transcripts before and 474 after
(322 new `.jsonl` against 321 model calls): that run was unaffected, but every
later run reads its predecessor's judge chatter as corpus. The same call
passes the slice text as a positional argument, so a very long assistant
block hits `ARG_MAX`; there is no injection risk (list-form argv, no shell).
Source: batch 202608290848 deferred items on PRDs 00007 and 00008
(self-ingestion: HIGH, out-of-scope, runtime-confirmed; ARG_MAX: LOW, 1/4);
decided 2026-09-05: one PRD, both inside `judge()`.

```
task-11 end-to-end run: 153 selectable transcripts before, 474 after; 322 new
.jsonl against 321 model calls.
```

## Solution

`judge()` runs `["claude", "--print", "--no-session-persistence", "--model",
_MODEL_FOR_TIER[tier]]` with the prompt supplied on stdin (`input=prompt`;
`stdin=subprocess.DEVNULL` goes away). `--no-session-persistence` is
documented for `--print` ("sessions will not be saved to disk") in
`claude --help` on this machine, checked 2026-09-05.
`test_judge_invokes_claude_cli_with_model_resolved_from_tier`
(`test_funnel_triage.py` lines 15-35) pins today's argv and kwargs and is
updated to the new shape. Migrate FakeClaudeCli in funnel_test_helpers.py
(reads `cmd[-1]` and `cmd[3]`) and the positional argv assumptions in
test_funnel_main.py (lines 102, 218 - 00034's `[*cmd[:-1], sentinel]` -
281 and 558 at 2026-10-10; re-locate by `rg -n "cmd\[" ` at execution): read the prompt
from input and locate the model flag by name, preserving their behavioral
assertions. Keep the 120-second judge bound and 00034's separate typing-timeout
regression. A real child process proves the prompt arrives intact at one
megabyte on Windows and POSIX: the test writes `fake_claude.py` under
`tmp_path` and monkeypatches `funnel.subprocess.run` with a wrapper that
replaces argv[0] (`"claude"`) with `[sys.executable, str(fake_claude)]` and
calls the real `subprocess.run` with every other argument unchanged. No
production change: `judge()` keeps the bare `"claude"`, and PATH resolution
of the real binary stays out of this test's scope.

## Requirements

### Must have

- `judge()` passes `--no-session-persistence` and sends the prompt on stdin.
- A one-megabyte prompt reaches the CLI intact (asserted with a fake
  `claude` script that records its stdin length and argv).
- The other `judge` tests (`returns raw stdout`, `raises RuntimeError with
  stderr`) pass unchanged.

### Nice to have

- none

## Implementation

### Module: funnel.py

- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: Call the CLI without leaving a transcript behind.
- **Exports**: `judge(prompt, tier)`, unchanged signature

### Module: test_funnel_triage.py, test_funnel_main.py and funnel_test_helpers.py

- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: Pin the argv and the stdin prompt.
- **Exports**: pytest cases

### Dependencies

- funnel.py: No dependencies (foundation)
- judge and main test fixtures: Depends on [funnel.py; preserve PRD 00034]

## Tasks

### Phase 0: Foundation

- [ ] Change the argv and stdin in `judge()` - Acceptance: `test_judge_invokes_claude_cli_with_model_resolved_from_tier` is updated to expect `["claude", "--print", "--no-session-persistence", "--model", expected_model]` with kwargs `{"input": "prompt text", "capture_output": True, "text": True, "timeout": 120}` and no `stdin` key; a new test `test_judge_sends_a_one_megabyte_prompt_on_stdin_intact` writes a `fake_claude.py` under `tmp_path` that records its stdin length and argv to a file, monkeypatches `funnel.subprocess.run` with a wrapper that swaps argv[0] for `[sys.executable, str(fake_claude)]` and delegates to the real `subprocess.run` (no shell, no executable bit, no platform skip), calls `judge("x" * 1_000_000, "cheap")`, and asserts the recorded length is 1000000 and `--no-session-persistence` is in the argv; shared FakeClaudeCli and main-test argv consumers are migrated, and their behavioral assertions plus 00034's timeout diagnostic pass; `uv run pytest skills/distil-memory/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- Both tests pass; the other judge tests pass unchanged.
- The fake CLI records the no-persistence flag and exact stdin bytes without
  requiring credentials or model calls. The historical live measurement is
  context, not a mandatory rerun; the installed CLI's documented print-mode
  flag supplies the no-persistence contract.

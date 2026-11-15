---
catchup: skip
design: skip
default_model: sonnet
model_tier_rationale: one-flag transcription with its exact text given; the new shell test fails on the old script
eligibility: test "$(git rev-parse --git-dir)" != "$(git rev-parse --git-common-dir)"
---

# qwen-run.sh dispatches pi without extensions

## Problem

On 2026-09-06 two qwen dispatches failed after a healthy preflight, and the failure was read as "pi sent the
request to `localhost:8080` instead of the resolved llamacpp8002 provider". The original 00078 was written to
find and fix that routing.

It does not reproduce. On 2026-10-17, with the llamacpp8002 provider serving `unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL`
on port 8002 and nothing listening on 8080, a real `qwen-run.sh --approved-only -R -j` dispatch ran on provider
llamacpp8002 and finished with stopReason "stop" and an agent_end event.

What that run did show is the likely source of the misreading. The pi install carries the
`huggingface/pi-llama` extension, which hardcodes `http://localhost:8080/v1` (overridable only through its
LLAMA_BASE_URL environment variable) and prints `[llama-cpp] failed to reach http://localhost:8080/v1/models: fetch failed` on
every pi start while 8080 is down, successful dispatches included. The 2026-09-06 report quotes that same
`localhost:8080` wording, while `models.json` names `127.0.0.1`. A dispatch never needs the extension: the
`--provider`/`--model` pair `qwen-run.sh` passes resolves from `~/.pi/agent/models.json`, which pi core reads.
Verified the same day: `pi --no-extensions --provider llamacpp8002 --model unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL
--mode text --tools read --no-session -p "..."` answered `OK` with no `[llama-cpp]` line.

So every dispatch output carries a false "endpoint unreachable" line that has already sent one diagnosis the
wrong way.

## Solution

`qwen-run.sh` adds `--no-extensions` to the pi arguments every dispatch mode shares
(`skills/use-qwen/scripts/qwen-run.sh:469`). Interactive pi outside the wrapper keeps its extensions. The
preflight is unchanged: it never starts pi. PRD 00049 (lower number, same guard) rewrites that line's
dispatch options first and keeps the one `ARGS=(--provider ...)` array; this PRD appends to whatever
it holds.

Run it in a lane worktree only, like 00049, which edits the same script. `~/.agents/skills/use-qwen` links
to the main checkout, so autopilot dispatches qwen through the main checkout's `qwen-run.sh`. The
`eligibility:` check passes only in a linked worktree, so a drain on the main checkout skips this PRD.

## Requirements

### Must have

- Every pi command `qwen-run.sh` runs carries `--no-extensions`.
- `test_qwen_run.sh` has a test that fails when a dispatch omits `--no-extensions`.
- `CHANGELOG.md` gains a `**use-qwen**` entry under `[Unreleased]` / `### Fixed`.

### Nice to have

- None.

## Implementation

```text
skills/use-qwen/scripts/
├── qwen-run.sh        # shared pi ARGS gain --no-extensions
└── test_qwen_run.sh   # new argv test
CHANGELOG.md           # Fixed entry
```

### Module: qwen-run.sh
- **Location**: `skills/use-qwen/scripts/qwen-run.sh`
- **Responsibility**: provider resolution, the preflight, and the pi dispatch
- **Exports**: the dispatch modes and `--preflight`

### Module: test_qwen_run.sh
- **Location**: `skills/use-qwen/scripts/test_qwen_run.sh`
- **Responsibility**: shell tests driven through a stub `pi` that records its argv
- **Exports**: none

### Module: changelog
- **Location**: `CHANGELOG.md`
- **Responsibility**: user-visible change record
- **Exports**: none

### Dependencies
- test_qwen_run.sh: Depends on [qwen-run.sh]
- changelog: Depends on [qwen-run.sh]

## Tasks

### Phase 0: Foundation
- [ ] Pass `--no-extensions` to every pi dispatch. Premise, re-checked at execution (a failed premise means skip
  and report, never force): `rg -c '^ARGS=\(--provider ' skills/use-qwen/scripts/qwen-run.sh` prints 1
  (line 469 today, reading `ARGS=(--provider "$PROVIDER" --model "$MODEL" --mode "$OUTPUT_MODE")`; PRD
  00049 may have changed the elements after `--model "$MODEL"`), and `rg -n "no-extensions"
  skills/use-qwen/scripts/qwen-run.sh` prints nothing.
  In `skills/use-qwen/scripts/test_qwen_run.sh`, directly after the T3 block and before the line
  `# ══ T4: healthy dispatch reaches pi; child stdin is guarded`, insert:

  ```bash
  # ══ T3b: dispatch runs pi without extensions ═════════════════════════════════
  # The pi-llama extension prints a localhost:8080 "failed to reach" warning on
  # every start; a dispatch never needs it (providers come from models.json).
  run_qwen t3b -f "$PROMPT_FILE_T"
  if [ "$RC" -eq 0 ] && grep -qx -- "--no-extensions" "$WORK/t3b.argv"; then
      PASS "dispatch passes --no-extensions to pi"
  else
      FAIL "dispatch passes --no-extensions to pi" "rc=$RC; argv: $(tr '\n' ' ' < "$WORK/t3b.argv" 2>/dev/null || echo MISSING); output: $OUT"
  fi
  ```

  Run `bash skills/use-qwen/scripts/test_qwen_run.sh` and watch exactly this test fail. Then in
  `skills/use-qwen/scripts/qwen-run.sh` append `--no-extensions` as the last element of that
  `ARGS=(...)` array (on today's text:
  `ARGS=(--provider "$PROVIDER" --model "$MODEL" --mode "$OUTPUT_MODE" --no-extensions)`), and put this comment
  line directly above it:
  `# --no-extensions: providers resolve from models.json; extensions only add startup noise (pi-llama's localhost:8080 probe).`
  Acceptance: `bash skills/use-qwen/scripts/test_qwen_run.sh` ends with `0 failed`.

### Phase 1: Core
- [ ] Record the fix (depends on: Phase 0). Under `## [Unreleased]` / `### Fixed` in `CHANGELOG.md`, add:
  `- **use-qwen**: \`qwen-run.sh\` dispatches pi with \`--no-extensions\`, so the pi-llama extension's \`[llama-cpp] failed to reach http://localhost:8080\` warning no longer appears in dispatch output, where it read as a failed request on runs that succeeded.`
  Acceptance: `rg -n "no-extensions" CHANGELOG.md` matches one line, and that line sits under `## [Unreleased]`
  between its `### Fixed` heading and the next `## [` heading (PRD 00029 cuts `## [0.1.0]` beneath an empty
  `[Unreleased]` earlier in the batch; if `[Unreleased]` has no `### Fixed` yet, add the heading).

## Success Criteria

- `dispatch passes --no-extensions to pi` passes in `test_qwen_run.sh` and failed before the script change.
- The full `uv run pytest` gate and `bash skills/use-qwen/scripts/test_qwen_run.sh` pass at the end of the last
  phase.

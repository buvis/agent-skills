---
default_model: sonnet
model_tier_rationale: one shell script, a reproduction step first, then the probe and the pin specified by observed behaviour; tests through a fake pi
rework_cap: 3
catchup: skip
design: skip
---

# The qwen preflight passes while every real dispatch is refused

## Problem

`skills/use-qwen/scripts/qwen-run.sh` resolves a provider from `~/.pi/agent/models.json` (`llamacpp8002`,
`http://127.0.0.1:8002/v1`), probes it with a real 1-token completion over curl (`preflight: healthy`), and then
dispatches `pi --provider llamacpp8002 --model <id> ...` (line 469). On 2026-09-06 the request pi sent underneath
went to `localhost:8080`, the `llamacpp` provider, where nothing was listening, so both qwen dispatches on
claude-autopilot PRD 00178 task 3 aborted `endpoint_unreachable` after a healthy preflight, and the loop latched
`state.qwen_preflight = endpoint_unreachable` for batch 202609061630 to route qwen-eligible tasks to Sonnet.
The model id is registered under `llamacpp8002` only, so this is pi choosing a provider by its own rule, not an
id clash. The preflight cannot see it because it probes the server directly, never the path pi takes. Source:
claude-autopilot deferred ledger `202609061630`, PRD 00178 `infra-bug` row; decided 2026-09-06 in the
config-audit closure walkthrough (`~/.claude/dev/local/audit-results/2026-09-05.md`).

## Solution

Find out what decides pi's base URL for a `--provider`/`--model` run (the flag, the model's provider list, or a
default in `~/.pi/agent/settings.json`), then make the two paths one: the preflight's final gate is a 1-token
completion sent through `pi` with exactly the dispatch arguments, so a provider mismatch fails the preflight
as `endpoint_unreachable` with the URL pi used; and the dispatch pins pi to the resolved provider by the
mechanism the investigation found (a flag, an environment variable, or a temporary models file holding only
that provider), so pi cannot wander to another port. The curl probe stays as the cheap first check.

## Requirements

### Must have

- A Phase 0 note in the PRD's commit body names what decided the base URL on this host, reproduced with pi's
  verbose or debug output against `llamacpp8002` live and `llamacpp` down.
- `qwen-run.sh --preflight` ends with a completion sent through `pi` using the same `--provider`, `--model`
  and mode arguments the dispatch uses; a request that reaches any base URL other than the resolved
  provider's fails the preflight with `endpoint_unreachable` and prints both URLs.
- The dispatch uses the pinning mechanism found in Phase 0 so pi's request goes to the resolved provider.
- `preflight: healthy` output keeps its shape (`provider '<p>', model '<m>'`), so the loop's parser is unchanged.
- The skill's `SKILL.md` preflight section states that the probe runs through pi, and `CHANGELOG.md` gains a
  `**use-qwen**` entry under Fixed.

### Nice to have

- none

## Implementation

### Module: qwen-run.sh
- **Location**: `skills/use-qwen/scripts/`
- **Responsibility**: provider resolution, the preflight ladder, and the pi dispatch
- **Exports**: `--preflight`, the prompt-mode dispatch

### Module: test_qwen_run.sh
- **Location**: `skills/use-qwen/scripts/`
- **Responsibility**: the script's bats or shell tests, driven through a fake `pi` on PATH that records the
  base URL it would call
- **Exports**: the cases named below

### Module: SKILL.md
- **Location**: `skills/use-qwen/`
- **Responsibility**: the preflight contract the loop and the operator read
- **Exports**: the preflight section

### Dependencies
- `pi` (mise) and `~/.pi/agent/models.json` as installed; no new dependency.
- test_qwen_run.sh: Depends on [qwen-run.sh]
- SKILL.md: Depends on [qwen-run.sh]

## Tasks

### Phase 0: Reproduce

- [ ] Reproduce the wrong-port dispatch and name its cause - Acceptance: with `llamacpp8002` live and nothing
  on 8080, a prompt-mode run under pi's verbose flag shows the request URL; the commit body states which
  setting picked it and which flag, variable or file pins it; no code change in this task.

### Phase 1: One path

- [ ] Route the preflight's final gate through `pi` and pin the dispatch (depends on: Phase 0) - Acceptance:
  `test_preflight_fails_when_pi_targets_another_provider` (fake pi that reports a base URL differing from the
  resolved one; `--preflight` exits 1 and stderr names both URLs) and
  `test_dispatch_pins_pi_to_the_resolved_provider` (fake pi records the pin the dispatch passed and the run
  exits 0) pass in `test_qwen_run.sh`; `test_preflight_healthy_output_keeps_its_shape` asserts the unchanged
  `preflight: healthy (provider '...', model '...')` line; each red against the old script first.

### Phase 2: Docs

- [ ] State the through-pi probe in `SKILL.md` and add the CHANGELOG entry (depends on: Phase 1) - Acceptance:
  `rg -n "through pi" skills/use-qwen/SKILL.md` matches in the preflight section; `rg -n "use-qwen"
  CHANGELOG.md` matches under `[Unreleased]`; `uv run python3 skills/create-skill/scripts/validate_skill.py
  skills/use-qwen/` reports the skill valid.

## Success Criteria

- A healthy `--preflight` is followed by a dispatch that reaches the same base URL, on this host with
  `llamacpp8002` live; a deliberately wrong pin fails the preflight, never the dispatch.
- `bash skills/use-qwen/scripts/test_qwen_run.sh` reports 0 failing.
- The next claude-autopilot batch on this host records no `endpoint_unreachable` after a healthy preflight in
  `dev/local/autopilot/ledger/attempts.jsonl` (post-release signal, checked by the operator).

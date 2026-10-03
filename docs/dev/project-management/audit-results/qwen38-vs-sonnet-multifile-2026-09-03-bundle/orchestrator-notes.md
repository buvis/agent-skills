# Orchestrator notes for the audit and report tasks (PRD 00010, batch 202609012242)

Written by the build orchestrator after the six eval tasks ran (2026-09-02 12:55 to 2026-09-03 ~15:30). These are facts the per-dispatch evidence blocks do not carry on their own. Read them before auditing or scoring; they are also in the `-bundle/` copy.

## What a "transcript" is here

- `runs/<n>-<engine>-a<k>.out.txt` is the engine's FINAL MESSAGE only, for both engines: `pi` in print mode and `claude --print` both emit nothing until the end. A qwen `out.txt` that holds only the 74-byte `[llama-cpp] failed to reach http://localhost:8080/v1/models: fetch failed` line means pi produced no final message (timeout, kill, or an ended run); that probe line appears in EVERY qwen run, passing ones included, and is not an error of the run.
- For qwen the FULL transcript exists: pi persisted every session as JSONL, copied here as `runs/<n>-qwen-a<k>.session.jsonl` (one entry per line; `type: message` entries carry `role` assistant/toolResult with `toolCall` blocks and their results, timestamps, and `usage` counters; a `type: compaction` entry means pi compacted the context). Audit qwen claims against these: they show every real tool call, so "narrated tool use without a real tool call" is checkable directly. Task 1 attempt 1 has no session file (pi rejected the argv before starting).
- For Sonnet only the final message exists; the C7 `unverifiable` rule applies as designed.

## Attempt histories and effective results (C4: effective = first VALID attempt)

| task | engine | attempts | effective | notes |
|---|---|---|---|---|
| 1 repoint-bim-doc-callers (impl+caller, 8 files) | qwen | a1 DISCARDED:exit-1 (harness: pi rejected the `- [ ]` prompt as an option, fixed df551fc), a2 VALID | a2 PASS | |
| 1 | sonnet | a1, a2 DISCARDED:exit-1 (harness: `claude --print` rejected the argv, fixed 13d68a8; both ruled harness faults, not engine attempts), a3 VALID | a3 PASS | |
| 2 route-tui-create-note (impl+test, 4 files) | qwen | a1 DISCARDED:harness-interrupted (agent killed, engine killed with it), a2 DISCARDED:timeout (40-min bound), a3 DISCARDED:timeout (40-min bound), a4 VALID under the 60-min bound | a4 PASS | pi logs of a2/a3 show the suite green at 36.9 / 38.6 min and self-verification when the cap fired; the user raised the bound to 60 min on 2026-09-03 for all remaining dispatches and ordered a4 |
| 2 | sonnet | a1 VALID (40-min bound) | a1 PASS | |
| 3 repoint-zettel-save (impl+test, 2 files) | qwen | a1 VALID | a1 PASS | |
| 3 | sonnet | a1 VALID | a1 PASS | |
| 4 record-raw-source-sha (impl+test, 2 files) | qwen | a1 VALID | a1 FAIL (gate exit 1: 3 canonical tests fail, the fix records only the raw-source-sha dedup identity and drops the filed-PDF identity; own 15 passed; ablation real) | baseline ran inside the dispatch tree, then the pretask test file was restored from the template and the tree verified clean before the engine ran (self-reported) |
| 4 | sonnet | a1 VALID | a1 PASS | |
| 5 surface-reindex-skip-warnings (impl+test, 11 files, 3 gate-invisible) | qwen | a1 VALID | a1 FAIL:dropped (zero edits; pi log: 61 read-only tool calls, ~125K-token context, `compaction`, run ended exit 0 after 53.4 min) | |
| 5 | sonnet | a1 VALID | a1 PASS (11/11 files incl. the 3 gate-invisible ones; gate 44 passed) | |
| 6 cap-frontmatter-size (impl+test, 2 files) | qwen | a1 VALID | a1 PASS | first agent stopped before any engine ran (ran `git reset --hard`); baseline reused, dispatch on a fresh clone |
| 6 | sonnet | a1 VALID | a1 PASS (own 96, gate 97, ablation compile error) | |

Transcript count: 18 `runs/*.out.txt` files (task 1: qwen a1, a2, sonnet a1, a2, a3; task 2: qwen a1-a4, sonnet a1; tasks 3-6: one per engine). Nine qwen session logs (`runs/<n>-qwen-a<k>.session.jsonl`; task 1 qwen a1 has none).

## Rules added during the build (all recorded in `state.autonomous_decisions` and the design doc)

- Harness-fault DISCARDs (engine never started: CLI rejected argv, helper died before exec, agent killed by the session harness) do not consume the C4 one-retry budget; they are recorded in the block as such.
- Engine bound: `timeout -k 60 2400` (40 min) for task 1 both engines, task 2 qwen a1-a3 and Sonnet a1; `timeout -k 60 3600` (60 min) from task 2 qwen a4 onward (user decision 2026-09-03; reasoning effort unchanged).
- Slot 5 `necessity`: `ffi/mod.rs`, `ddb.udl`, `ddb-cli/src/commands/crud.rs` are Required but gate-invisible (scored by `dropped`/`stray` only); `app_contract/mod.rs` is Ancillary (R2).
- Every clone is `mise trust`ed; RESET/RECON are fresh clones, never `git reset --hard`/`git clean`.
- Sonnet helper for all dispatches after task 1 a2: the repo copy `~/.agents/skills/use-sonnet/scripts/sonnet-run.sh` (stdin routing for hyphen-prefixed prompts); the autopilot plugin cache copy still passes the prompt as argv (tracked as claude-autopilot PRD 00171).

## Incidents that touched evidence files

- `runs/1-qwen-a1.out.txt` was overwritten at 13:40:58 on 2026-09-02 by a concurrent headless autopilot session (the operator's `autoclaude` loop ran turns on this same task until paused at 14:13); the 1193-byte original survives in `runs/1-qwen-a1.wrapper.txt` and in the evidence block.
- Task 6: `6-cap-frontmatter-size-qwen-a1.contaminated-baseline` is the tree the first agent ran the baseline in; it is not an attempt tree.

## For the report's C8/C9

- Attempts under the 40-min bound that timed out (task 2 qwen a2, a3) are DISCARDED, not FAIL; the effective qwen result on task 2 is a4 (VALID, PASS). If the report author wants to show the cost of the bound, pi's logs give exact timings.
- Task 4 qwen: both Required files present in `status.txt` with real diffs; C8 step 1 (b) no-op test is moot (large diffs), step 2 no stray; class 3 `unrelated-logic-error` unless the first gate error is against a pinned symbol (it is an assertion, not a name error).
- Task 5 qwen: C8 step 1 (a) all 11 Required files untouched -> `dropped-a-file` for every file.
- `drops` counts qwen `dropped-a-file` results over tasks with a VALID qwen effective attempt: task 5 qualifies.

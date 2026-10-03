# Qwen3.8 as a Sonnet stand-in: retrospective (2026-09-05)

Source material: PRD 00010 (`dev/local/prds/hold/`), the 2026-09-03 comparative
report and its evidence bundle (`dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03*`),
the pi session logs inside that bundle, review cycle 1 (tasks 14-17 in
`dev/local/autopilot/state.json`, `contract-card.md`), the live `audit-qwen`
report card (run today), the autopilot routing sources in `claude-autopilot`
(`work_routing.py`, `model-ladder.md`, `qwen-integration.md`, `classify_tier.py`),
and the server launch helper `start_qwen` in `~/.config/bash/plugins/development.plugin.bash`.

## 1. Where it stands

| Measure | Qwen3.8 (Q6_K_XL, 128K ctx) | Sonnet | Source |
|---|---|---|---|
| Single-file eval, 2026-08-31 | 6/6, 0 false claims | 6/6 | approved-models.txt, eval report |
| Multi-file eval, 2026-09-03 | 4/6 | 6/6 | comparative report (review cycle 1: "not decision-grade") |
| Real autopilot dispatches, all repos | 4/4 gate pass | n/a | audit-qwen card |
| Share of qwen-eligible tasks actually dispatched to qwen | 4/40 = 10% | n/a | audit-qwen card |

PRD 00010 state: build finished through task 13 (report written, SKILL.md and
qwen-integration.md carry the `single-file-only` scope text). Review cycle 1
returned 15 findings, four of them 4/4-consensus criticals about evidence
integrity, and queued rework tasks 14-17. The PRD sits in `hold/`; the report's
walkthrough minutes were never written. The routing side is already a queued
PRD in `claude-autopilot`: `00174-align-qwen-routing-with-single-file-trust-v1.md`
(narrow `qwen_eligible` to one file, recheck the write set at dispatch, treat an
exit-0 empty diff as a capability failure, guard Tess-owned tests).

## 2. Why it is not there yet

### 2.1 The binding constraint is wall-clock, not correctness

Qwen wall time per effective attempt, read from the pi session logs:

| Task | Files | Lang | Qwen time | Turns | Result |
|---|---|---|---|---|---|
| 1 repoint-bim-doc-callers | 8 | Python | 8m52s | 15 | PASS |
| 2 route-tui-create-note | 4 | Python | 27m (a4); a2 and a3 hit the 40-min bound | 30 | PASS |
| 3 repoint-zettel-save | 2 | Python | 3m32s | 10 | PASS |
| 4 record-raw-source-sha | 2 | Python | 50m | 46 | FAIL (logic) |
| 5 surface-reindex-skip-warnings | 11 | Rust | 53m | 41 | FAIL (no edit) |
| 6 cap-frontmatter-size | 2 | Rust | 40m | 18 | PASS |

Median 34 minutes. Sonnet finished every task inside the original 40-minute
bound (only its final messages were captured, so no exact figures).

Where the minutes go: thinking. On task 5 the thinking blocks grew from a few
hundred characters per turn to 17.9K and 16.6K characters; those two turns each
took about 6.5 minutes for about 4.8K output tokens, which is roughly 12
tokens per second at 90K context. Run-to-run variance is large: task 2 timed
out twice at 40 minutes with the suite already green, then finished in 27
minutes on the next launch.

Nobody set the reasoning effort. pi's session log records
`thinkingLevel: off`, `~/.pi/agent/models.json` declares
`supportsReasoningEffort: false` for the provider, and `start_qwen` passes no
reasoning flag, so the server's template default governs (the evidence log calls
it xhigh). No file under `skills/use-qwen/` mentions reasoning or thinking
control. This is the cheapest lever in the whole system and it has never been
pulled.

Why this matters for "replacing Sonnet": autopilot gives qwen one shot, then
escalates to Sonnet. With a 60-minute bound and a two-thirds multi-file pass
rate, the expected wall-clock of routing a multi-file task to qwen is worse
than running Sonnet directly, because every failure costs the qwen hour plus
the Sonnet run. Inference is free in dollars and expensive in batch hours,
and autopilot batches are serial.

### 2.2 Task 5 was context exhaustion, not multi-file confusion

The PRD set out to test Qwen3.6's documented failure: finish one file, silently
drop the rest. Qwen3.8 did not do that. On the 11-file Rust task it made 61
tool calls, every one a read, grep, ls or sed, across ddb-core, ddb-cli,
ddb-server and the e2e tests; context grew from 12K to 127K tokens over 46
minutes; pi compacted once at 53 minutes; the run ended exit 0 with an empty
diff and no final message. Neither failure was classified cross-file
confusion. The weakness is exploration without a budget: no plan-then-act
reflex, no "stop reading, start editing" threshold, and a 128K window that
cannot grow on a 48GB machine without shrinking the model. Sonnet's edge on
that task was a bigger window and better exploration heuristics, not
multi-file skill as such.

### 2.3 Task 4 shows the real "false claim" class

Qwen replaced one dedup identity with the other instead of adding the second,
rewrote the test file to match, ran 1203 tests green, and reported "complete
and verified". The canonical gate with the pinned test file fails 3 of 16.
The audit flagged it as a false claim; the reviewer disputes that under the
contract, because the command really ran. Either reading gives the same
lesson: the risk is not what the engine says, it is what the engine chooses
to verify against. Autopilot's TDD lane already forbids test edits in the
prompt; PRD 00174 turns that into a deterministic guard. Until it lands, a
self-rewritten test can become the oracle.

### 2.4 The eval measured a task shape autopilot never gives qwen

The eval handed each engine the original task description and asked for the
implementation plus the tests, across N files. Autopilot's qwen lane is the
TDD implementor prompt: failing tests already exist (Tess wrote them), the
implementor makes them pass, must not touch test files, and the step-5.5 gate
runs only those tests. Eligibility is backend, haiku or sonnet tier, at most
three files, no public-contract edit. So the eval both over-tested qwen (it
authored tests) and under-tested it (the Ivan prompt was never measured). The
bundle already holds template trees, reverse patches and canonical test files
for every task, so an Ivan-shaped rerun costs setup minutes, not days.

### 2.5 Routing starves qwen before capability matters

From today's `audit-qwen` card across all repos: 29 qwen attempts on record;
dispatch rate 4 of 40 eligible tasks; plan-time exclusions `files` 22, `tier`
24, `unknown` 53; dispatch-time reroutes `memory_pressure` 10, `tier` 14,
`files` 8. In PRD 00010's own batch, 1 task of 13 went to qwen (9 excluded for
file count, 3 for opus tier). Where qwen did run, it passed 4 of 4 gates.

Two mechanical causes. First, the planner's split trigger aims at three-file
pieces but most real tasks still land above it or at opus tier. Second, the
memory gate (routing row 4) fires at pressure level 2 and was never measured
with the server resident; `model-ladder.md` says so. Right now, with the
Qwen server up but idle, the level reads 1. Ten reroutes in the July and
August batches say it does fire under load. A gate that fires whenever the
model is loaded is a silent qwen-off switch.

### 2.6 The eval is too expensive and fragile to iterate

The batch window ran from 2026-09-02 12:55 to 2026-09-03 15:30 for 12 valid
dispatches out of 18 launched; six were harness faults or timeouts. Review
cycle 1 then found that retries reused attempt-1 baselines, two tasks were
partially pre-solved by an Ancillary demotion, three Required files on task 5
were gate-invisible, and the engine bound changed mid-batch. The PRD's Phase 0
decision made isolation safety "documentation-only operator discipline"; the
review found exactly the bug class a checklist cannot catch. This is the
second round in a row (2026-08-31, 2026-09-03) that discovered new harness
bugs after the fact.

The consequence is the meta-cause: because a round costs two days and a
review cycle, none of the real levers (reasoning effort, prompt shape,
exploration budget, context) has ever been varied and re-measured. Without
cheap repetition there is no tuning, and without tuning a 27B model stays
where it is.

### 2.7 n = 6 with a one-strike rule decides on one task

Branch (1) fired on a single disputed flag; branches (3) and (4) would have
failed on task 5 alone. Six samples from two repos, dominated by one 11-file
Rust task in an unfamiliar codebase, cannot separate "multi-file capability"
from "this one task". The strict rule is right for unattended trust, but it
means the eval can say "no" cheaply and "yes" only expensively.

## 3. What would make it real

Ranked by leverage per unit of effort. S, M, L are effort guesses.

| # | Move | Effort | Attacks | Expected effect |
|---|---|---|---|---|
| A | Set reasoning effort explicitly (server `--chat-template-kwargs` or pi thinking level after flipping `supportsReasoningEffort`), measure tokens/s and per-turn latency on one fixed task at low, medium, high; keep the single-file 6/6 | S | 2.1 | tasks 4-6 drop from 40-50 min toward 10-15; routing economics flip |
| B | Rerun the six tasks in the Ivan shape from the existing bundle: canonical tests pre-placed as failing tests, TDD prompt, test edits forbidden, gate on pinned tests, fresh clone and baseline per attempt | S-M | 2.3, 2.4 | a decision-grade number for the lane autopilot actually uses |
| C | Script the multi-file harness (template from `git archive` plus reverse patch, pre-task hash snapshot, per-attempt clone, baseline gate, fixed bound, gate/own/ablate, status and diff capture, JSONL evidence) so tasks 14-16's findings are fixed by construction | M-L | 2.6, 2.7 | a round becomes an unattended overnight run; enables A and B to be iterated and every new quant to be re-qualified cheaply |
| D | Bounded exploration in the prompt: Required files listed, at most N extra reads, plan after 10 reads, then edit; feed a repo brief (the `survey` skill output or the AGENTS.md architecture slot the template already has) | S | 2.2 | fewer context blowouts on large-file-count tasks; measure via B |
| E | Land PRD 00174 (routing aligned to measured scope, empty-diff and test-mutation guards) and measure the memory gate under load; open the single-file lane to test-only and mechanical slices | M | 2.5 | banks the trust already earned; raises the 10% dispatch share without new evals |
| F | Change the engine: try the registered A3B MoE for 3-5x generation speed, or budget hardware (64-128GB) for a larger model or longer context | M / money | 2.1, 2.2 | the only path to Sonnet-like wall-clock; a new model means a new qualification from scratch |

Order that compounds: A, then B (with per-attempt baselines by hand once), then
C if B looks promising, D measured through B, E in parallel in the autopilot
repo, F only if A and D leave it too slow.

Decided 2026-09-05 (this repo's backlog): C first, as PRDs 00051 (harness
core: vet, run, attempt records) and 00052 (harness report: render, runbook);
B runs on them as PRD 00050 (Ivan-shape comparison, effort level chosen by
an operator calibration, so A is folded in); PRD 00049 makes the wrapper's
exit code truthful before either round; E is claude-autopilot PRD 00174.
00010 stays in `hold/` until 00050 supersedes it.

## 4. What "partially replacing Sonnet" can honestly mean

- Today: single-file backend tasks at haiku or sonnet tier. Qualified 6/6,
  4/4 in production, underused at a 10% dispatch share. This is real and
  mostly a routing problem.
- Next: two- and three-file implementation-only tasks in the Ivan shape,
  after A and B produce a clean number under a fixed bound.
- Not on this hardware: Sonnet-speed turns or 200K-context exploration of an
  unfamiliar repo. A 27B model at 12 tokens per second replaces Sonnet on
  cost, never on wall-clock, so it belongs on work where batch hours are
  cheap (overnight) or where Sonnet is idle anyway.

## 5. Evidence pointers

- Durations and per-turn thinking: `qwen38-vs-sonnet-multifile-2026-09-03-bundle/runs/<n>-qwen-a<k>.session.jsonl`
  (`type: message`, `message.role: assistant`, `content[].type: thinking`, `message.usage`).
- Task 5 cause: `evidence.md` line 1097; `runs/5-qwen-a1.status.txt` (0 bytes).
- Task 4 defect: `runs/4-qwen-a1.diff.patch` hunk `@@ -231,14 +230,21 @@`; `runs/4-qwen-a1.gate.txt` line 262.
- Reasoning effort never set: `thinking_level_change` entry in any qwen session log; `~/.pi/agent/models.json` compat block; `start_qwen` flags.
- Review cycle 1 findings: tasks 14-17 in `dev/local/autopilot/state.json`; `dev/local/autopilot/contract-card.md`.
- Utilization: `python3 ~/.agents/skills/audit-qwen/scripts/audit_qwen.py` (card of 2026-09-05).
- Routing rules: `claude-autopilot/skills/work/scripts/work_routing.py`, `run-autopilot/references/model-ladder.md` § Memory gate, `plan-tasks/SKILL.md` § qwen_eligible computation.

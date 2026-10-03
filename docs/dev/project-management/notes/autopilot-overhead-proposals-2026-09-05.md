# Autopilot overhead: what to cut without dropping a lens

Source: PRD 00015 run, batch 202609050909, measured 2026-09-05 11:20 from
`dev/local/autopilot/loop-metrics.jsonl`, `dispatch-metrics.jsonl`, `last-session.log`,
and `dev/local/reviews/00015-corrupt-queue-reads-as-drained-v1-review-1.md`.
The change under review: ~50 production lines, ~270 test lines, 7 doc lines.

## Where the 115 minutes went

| Segment | Wall | Cost | What happened |
|---|---|---|---|
| Session 1: catchup, plan, task 1 | 33 min | $15 | ivan x3, pat x3 (pat caught the identical missing/non-list messages) |
| Session 2: task 2 | 51 min | $22 | tess x3 / devon x3 ping-pong = 20 min before ivan ran; ivan x2; pat x3; style-gate file split |
| Session 3: task 3 (docs), verification | 12 min | $3.5 | |
| Review cycle 1 | 20 min | ~$20 (guess, session still open) | Carl dispatch + retry ~3 min; Bob first run ~3 min wasted, retry 8 min; 15+ driver polling turns on opus |

## What each lens returned this run

| Lens | Cost | Unique actionable findings |
|---|---|---|
| tess/devon, 3 rounds on task 2 | 20 min | 0. The non-list `entries` test gap survived all three rounds; Bob found it in one pass |
| pat, per-task | ~3 min x 3 | 1 (message distinctness, task 1) |
| Alice | ~5 min | 0 unique; both findings were PRD text |
| Blake | ~6 min | 2 Low (SKILL step 5 sentence, decide double-load) |
| Bob (codex) | 11 min incl. the dead first run | 1 High (UnicodeDecodeError escapes the catch), 1 test gap, 2 de-slop |
| Carl (Gemini) | ~3 min every cycle, dead for 3 batches | 0, never ran |

## Proposals

All keep consensus, blind and doubt lenses every cycle. Effort is a guess.

### 1. Stop paying for reviewers that cannot run (S)

- Carl: preflight probes auth (one dry-run call) instead of checking the binary exists, or a
  `carl: off` roster flag until Gemini access is restored (copilot rejects the pinned model,
  native gemini free tier is `UNSUPPORTED_CLIENT`).
- Bob: inline context and diff from the first run; the file-read attempt fails every time.
- Where: claude-autopilot, `review-work-completion` step 1 and `references/agent-invocation.md`.
- Saves: ~6 to 8 min and two driver rounds per cycle. Quality risk: none, both are the paths
  that already produce the review. Drawback: Carl stays off until someone re-enables him.

### 2. Cap the test-writer / test-reviewer loop at one round (S-M)

- tess writes, devon reviews once, tess applies. No third pass.
- Where: claude-autopilot, `work` skill dispatch rules.
- Saves: ~13 min on a task shaped like task 2. Quality risk: weaker tests reach ivan; pat and
  the cycle review still gate them, and that is where the real gap was caught anyway.
  Drawback: occasional test rework moves into the opus review cycle, which costs more per minute.

### 3. Stop the driver polling while CLI reviewers run (M)

- Launch Alice and Blake (Task calls) first, then run codex in the foreground with a timeout in
  one Bash call. No Watcher subagent, no "waiting on Bob" turns. The driver said it itself:
  "I'm polling pointlessly".
- Where: claude-autopilot, `review-work-completion` step 5.
- Saves: driver tokens only (15+ opus xhigh turns per cycle), no wall-clock. Quality risk: none.
  Drawback: a hung codex blocks the driver until the timeout; needs a hard cap (say 15 min).

### 4. Keep file layout out of acceptance criteria (S)

- create-prd forbids naming test files or counting files in acceptance and success criteria;
  criteria name the command and the behavior. Extends commit 5b1cfda (no suite-wide totals).
- Where: this repo, `skills/create-prd/SKILL.md`.
- Saves: 3 of 13 findings this cycle were PRD text, plus one Blake rubric fail and two gate
  deferrals. Quality risk: none, these findings never change code. Drawback: PRD authors lose a
  crisp literal check and must phrase the bar in behavior terms.

### Freebies (quality up, cost zero)

- Register this repo in `~/.config/gita/repos.csv` so `engram pack` works; the review ran with
  no retrieval context ("degraded, not invalid").
- `gather-context.sh` diffs the dirty worktree when the branch is `master`; use
  `work_start_sha..HEAD` there. This run it emitted three peer sessions' uncommitted edits and
  none of the PRD's commits, and the driver rebuilt the diff by hand.

### Not proposed now: per-task session handoffs (L)

Three sessions for three tasks. Subagent prompts and outputs of 40 to 48 KB each push the
driver toward the 500K cap, and each relaunch re-runs catchup (~2 to 5 min, $1 to 3).
Subagents writing full output to `dev/local/tmp` and returning a summary would fix it, but
it touches every dispatch site.

## Update 13:45: the biggest item was not in the pipeline

The cycle-1 review session ended 11:43 (58 min, $35.89, rework task 4 in progress). A 4-second session
followed, then no driver ran until 13:34. The gap matches `cli/usage_limit.py`'s relaunch wait (reset plus
120 s), but `wrapper.log` is empty so this is unconfirmed. The resumed session found HEAD leaking
`UnicodeDecodeError` (21 failures), reset the dead session's task, and committed rework tasks 4 and 5 by
13:42. It runs autopilot 0.5.0; the batch started on 0.4.1. Decisions taken on this note: proposals 1 and 2
go to PRDs (discovery doc `claude-autopilot/dev/local/discovery/00177-cut-review-and-test-loop-overhead.md`),
the Carl skip becomes one task on backlog PRD 00175, proposals 3 and 4 stay parked here.

## Expected effect of 1 to 4 together

Review cycle from ~20 to ~12 min; a task-2-shaped task from ~50 to ~35 min. Roughly 25 to 30%
wall and ~30% cost on a run like this one, all lenses kept. Guess, not measured.

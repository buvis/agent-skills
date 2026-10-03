---
catchup: run
design: run
default_model: opus
model_tier_rationale: experimental isolation, timed engine dispatch, evidence classification, and comparative analysis
---

# Qwen in the Ivan Implementation Role

## Overview

### Problem Statement

PRD 00010 tested implementation plus test authoring; Ivan receives prepared tests.
Its September 4 review rejected the scores for partial pre-solving, missing baselines
and gate gaps. Mixed 40/60-minute budgets also do not establish success in the 20-minute lane.

Sources: the 2026-09-05 retrospective; `dev/local/reviews/00010-qwen38-multifile-capability-eval-v1-review-01.md`;
the canonical autopilot `agents/ivan.md` and Qwen/subagent-dispatch references.
Read the installed plugin or source checkout at execution and record versions.

This role-specific experiment depends on 00049 (truthful wrapper exit) and on
the eval harness under `skills/use-qwen/scripts/`: 00051 (`vet` and `run`,
which build every sealed tree, baseline, dispatch record and gate result) and
00052 (`render`, which produces the evidence log, scoreboard and audit
queue); no script is written inside this PRD's bundle. Historical 00010 is
in done/, but its September 4 review still invalidates the comparative scores;
this experiment does not depend on a pending repair of those old results.
Autopilot 00174 owns production guards. This PRD produces evidence, without widening trust.

### Target Users

The maintainer deciding whether guarded local implementation saves cloud work.

### Success Metrics

- Six fresh tasks, both engines, identical sealed inputs and a 1,200-second dispatch budget.
- One recorded server reasoning-effort level for every Qwen attempt in the run, chosen before it.
- Every intended implementation behavior has an independent acceptance check.
- No missing baseline, changed oracle, timeout, or unrecorded retry can produce a PASS.
- Results separate qualification scope, completion, correctness, latency, and rescue cost.
- An unfavorable or inconclusive model result still completes the experiment honestly.

## Functional Decomposition

### Capability: Faithful Ivan Inputs

Freeze task state and test authority before observing either engine's output.

#### Feature: Fresh tasks and sealed test oracles
- **Description**: Source six backend tasks from completed PRDs, excluding 00010's task set.
- **Inputs**: Task ledgers, original task-start/task-end commits, dependency locks, and tests.
- **Outputs**: A sealed manifest, source/vetting notes, pre-implementation snapshots, and oracle hashes.
- **Behavior**: Use the six-task convention from the existing qualification
  runbook. Include single-file and experimental 2-3-file implementation cases,
  covering at least two repositories and two languages.
  Reconstruct the full pre-implementation tree from its pinned task-start commit;
  overlay only independent tests/fixtures, intentionally visible to Ivan. No post-task
  implementation or reference patch is visible. Record every overlay. Canonical
  implementation passes; the sealed baseline fails for the intended behavior.
  Disqualify ungated surfaces, broken environments, and undisclosed supporting code.
  Each task is a harness `tasks/<n>-<slug>/spec.json` (00051), including the
  architecture, invariants, read_anchors and reading_budget_tokens fields
  required for the actual Ivan brief; `run_eval_harness.py vet`
  builds the sealed template from the task-start commit, records the oracle
  hashes, and proves the baseline fails and the canonical implementation passes.

#### Feature: Identical constrained implementation briefs
- **Description**: Render the current Ivan role with its actual read/write boundaries.
- **Inputs**: Sealed tests, architecture/invariants, writable implementation paths, and read anchors.
- **Outputs**: Byte-identical task briefs for Qwen and Sonnet, plus recorded transport differences.
- **Behavior**: Reuse the current Ivan contract and dispatch reading-budget
  requirements. List test paths as read-only; keep them out of the write set.
  Include narrow tests and symbol/line anchors, without acceptance prose, known
  solutions or hints from candidate failures. Freeze prompts/parameters first;
  record mechanical adaptations for native tool names.

### Capability: Bounded Comparison and Evidence

Measure the complete attempted replacement, including unsuccessful work.

#### Feature: Isolated single-attempt runs
- **Description**: Run each engine once per task with protected tests and independent verification.
- **Inputs**: Sealed inputs, `unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL` on a pinned provider, Sonnet, and PRD 00049.
- **Outputs**: Per-attempt event logs, hashes, timing, diffs, gate output, and terminal outcome.
- **Behavior**: Run through the harness:
  `python3 ~/.agents/skills/use-qwen/scripts/run_eval_harness.py run <evidence-dir>
  --run-id <id> --shape tdd --engines qwen,sonnet --bound 1200 --gate-bound 1800
  --alternate --retry-discarded harness-only --server-reasoning-effort <level>`,
  which preflights both engines and records resolved identities, Pi,
  llama.cpp and Claude CLI versions, effective context/output limits, and
  sampling/thinking settings without credentials; applies the 1,200-second
  budget to both engines, including their internal verification, and a frozen
  per-task gate limit; runs process-group timeouts, verifies child quiescence,
  and serializes dispatch and gates in fresh disposable trees; hashes every
  implementation and test path against the sealed snapshot before dispatch,
  runs a baseline gate in its own fresh clone for every attempt, and re-hashes
  the oracle after dispatch. One attempt only: timeouts and post-launch
  failures remain in the denominator; retry only an adapter failure
  positively observed before helper process creation, at most once. A
  launched or uncertain silent failure never becomes a fresh trial.
  Reasoning effort: the earlier run recorded a template default
  to `xhigh`, under which four of six 00010 tasks exceeded 20 minutes, and
  supports `low`, `medium` and `xhigh`. The level is an operator
  precondition, like the running server itself: before this PRD starts, the
  operator runs the harness on one non-scored task at `medium` and at `xhigh`
  (restarting the server with `--reasoning-effort <level>` between them),
  picks the highest level whose calibration attempt completed inside 1,200
  seconds, starts the server at that level, and records the level and the
  two calibration attempt directories in `protocol.md`. The operator records
  the server restart time, launch command's effort value and an attestation
  that the current server is that instance. The harness's declared_effort
  must match this record; /props does not verify the effective level.
  Every scored Qwen attempt runs at that one level; missing calibration or
  attestation leaves the PRD unstarted and parked, never completed with
  an empty experiment or a mid-run restart.
  Success requires completed output, an authorized diff, unchanged tests,
  passing independent gates and no unresolved substantive review finding.
  Use the same independent review rubric for both engines, hiding engine
  identity in the code-review packet (candidate diff and canonical gate
  result under an opaque attempt label). The driver separately audits the
  original trace for claim truth. Store review_verdict, review_findings and
  review_effort_s alongside the claim verdict in the 00052 audit-row schema.
  No changed-file count substitutes for a behavior check.

#### Feature: Rescue accounting and reproducible report
- **Description**: Report accepted local work and the observed cost of failures.
- **Inputs**: Both engine traces, frozen gates, diffs, independent reviews, and failed Qwen snapshots.
- **Outputs**: Durable evidence bundle and a report whose counts derive from per-attempt records.
- **Behavior**: Autopilot's escalation resets the tree to the test commit
  before dispatching Sonnet (`claude-autopilot/skills/work/references/gate-failure.md`),
  so the rescue of a failed Qwen attempt is the direct Sonnet attempt already in
  the run: Qwen-plus-rescue wall time is the Qwen attempt plus that Sonnet
  attempt, and no separate dispatch from Qwen's partial tree is made. Preserve
  and separately score the original Qwen result and the independent Sonnet
  result. Read first-edit/elapsed time and available usage from engine_run,
  and review effort from audit.jsonl; retain full events as evidence. Accepted
  work means outcome PASS and review_verdict clean; report that count
  separately from the raw gate PASS count. Separate one-file and experimental multi-file results. Compare
  direct Sonnet with Qwen-plus-rescue cost; separate common preparation and
  evaluation overhead. Missing monetary usage is "unavailable", never zero; subscription
  token savings are not cash savings. State sample limitations and recommend
  next steps without changing scope or inventing a promotion threshold.

## Structural Decomposition

### Repository Structure

```text
dev/local/audit-results/qwen-ivan-<run-id>/   # the harness evidence dir (00051 layout), copied here whole
├── protocol.md                     # Budgets, source versions, effort level, scoring rules (hand-written)
├── tasks/<n>-<slug>/               # spec.json, vetting.json, pretask.json, canonical.patch, oracle/
└── runs/<run-id>/
    ├── run.json                    # harness configuration, versions, task metadata
    ├── <n>-<engine>-a<k>/          # attempt.json, sealed.json, traces, diff, gates
    ├── audit.jsonl                 # driver-authored claim and code-review verdicts
    ├── evidence.md                 # rendered by the harness
    ├── report.md                   # rendered counts and measurements
    └── comparison.md               # driver-authored cost/latency analysis; render never overwrites it
```

No script lives in the bundle: every tree, baseline, dispatch record, gate
result and count comes from the harness (00051 records, 00052 rendering); the
hand-written inputs are task spec.json files, `protocol.md`, `audit.jsonl`
and `comparison.md`; all snapshots, measurements and counted results come
from the harness. Task specs are source inputs, not fabricated run evidence.

### Module: Sealed Task Inputs
- **Maps to capability**: Faithful Ivan Inputs
- **Responsibility**: Establish reproducible implementation state and independent test authority.
- **Exports**: Manifest, snapshots, prompts, hashes, and provenance under the durable bundle.

### Module: Comparative Evidence
- **Maps to capability**: Bounded Comparison and Evidence
- **Responsibility**: Run, verify, audit, and account for each attempt without rewriting history.
- **Exports**: Per-attempt records (00051) and rendered report (00052); no scripts in the bundle.

## Dependency Graph

### Foundation Layer (Phase 0)
- **PRD 00049**: Completed wrapper-status and one-shot regression checks.
- **PRD 00051**: The harness core (`vet`, `run`, attempt records) landed with its tests green.
- **PRD 00052**: The harness report (`render`, runbook § 7) landed with its tests green.
- **Sealed Task Inputs**: Depends on [PRD 00049, PRD 00051, PRD 00052]; 00010 need not be resumed.

### Core Layer (Phase 1)
- **Comparative Evidence runs**: Depends on [Sealed Task Inputs].

### Integration Layer (Phase 2)
- **Comparative Evidence report**: Depends on [Comparative Evidence runs].
- Production adoption additionally requires autopilot PRD 00174; adoption is outside this PRD.

## Implementation Phases

### Phase 0: Foundation
**Goal**: Freeze a valid comparison before spending model attempts.

**Tasks**:
- [ ] Verify 00049, 00051 and 00052 landed, engine availability, and current
  role contracts; author six spec files, run `vet` on each, verify the
  operator's effort calibration record, and seal `protocol.md` (depends on:
  PRD 00049, PRD 00051, PRD 00052).
  Acceptance: recorded preflights name both engines; the six `vetting.json`
  files confirm fresh tasks, both write-set strata and two languages/repos,
  matching snapshot hashes, intended baseline failures and canonical gate
  passes; `protocol.md` names the chosen effort level and the two calibration
  attempt directories it came from, and the operator's current-instance
  attestation names the intended --server-reasoning-effort value; Phase 1
  verifies run.json.server.declared_effort matches it. Missing prerequisites,
  calibration or six valid tasks -> record the shortfall and stop with the
  PRD unstarted; do not mark it complete.

**Exit Criteria**: Complete sealed inputs. A shortfall record explains why
the PRD stays parked; it does not satisfy completion.

### Phase 1: Core
**Goal**: Collect comparable single-attempt outcomes.

**Tasks**:
- [ ] Run the harness once over the six sealed tasks for both engines with `--alternate`
  (depends on: Phase 0). Acceptance: `render` finds six task rows and both
  engines' outcomes (twelve task-engine pairs), retaining any additional
  verified pre-launch discard records separately. Every launched attempt
  has its own baseline record, full traces, the one fixed
  budget, diffs, oracle checks and gates. Report interruptions and shortfalls;
  no replay replaces a failure.
- [ ] Audit both engines' changes and claims into `audit.jsonl` and derive the
  Qwen-plus-rescue cost from the paired records (depends on: Phase 1 paired
  runs). Acceptance: every VALID attempt has an audit row whose claims cite
  tool results or are marked unverified; test tampering shows as
  `FAIL:test-mutation` despite a candidate's green suite; no extra dispatch was
  made for rescue accounting.

**Exit Criteria**: All completed/failed/interrupted attempts retain their original evidence.

### Phase 2: Integration
**Goal**: Produce an assessable replacement recommendation.

**Tasks**:
- [ ] Render the report and write comparison.md (depends on: Phase 1).
  Acceptance: `render` exits zero and every count, timing and usage figure in
  the prose matches the attempt records; missing trials are named. Separate
  invalidated 00010 scores, common preparation, attempts, baselines and
  reviews. Snapshot checks confirm registry/default-model and routing unchanged.

**Exit Criteria**: A reproducible report, including an inconclusive verdict when evidence is insufficient.

## Test Strategy

### Critical Scenarios
- **Happy path**: Qwen completes within budget and passes immutable gates -> accepted local implementation.
- **Contamination**: One pre-solved implementation file or baseline side effect -> preparation rejected.
- **Test tampering**: Candidate reverses an invariant in tests -> failed attempt despite its green suite.
- **Length/timeout**: Partial work or no final answer -> failed original attempt; rescue cost read from the paired Sonnet attempt.
- **Gate gap**: A required implementation behavior has no check -> candidate excluded before dispatch.

## Risks

- **Sparse sample**: Six fresh tasks give directional evidence, not a production reliability estimate.
- **Protocol drift**: Freeze versions, budgets and prompts; changed conditions need a new run identity.
- **Historical evidence**: Reuse 00010's review lessons; do not treat its done/ location as validation of its scores.
- **Runtime resources unavailable**: Record blockers; no server startup, global upgrades or live-repo writes.
- **Historical isolation cost**: Disqualify unreconstructable tasks; retain evidence outside temporary-file GC.

Unresolved questions: none. This PRD produces evidence; a later adoption decision consumes it.

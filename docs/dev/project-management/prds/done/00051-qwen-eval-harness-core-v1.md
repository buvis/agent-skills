---
catchup: run
design: run
default_model: opus
model_tier_rationale: invented spec and attempt-record contracts, failure-classification predicates, and process-group timing decide whether evidence is valid
---

# Qwen Eval Harness Core

## Overview

### Problem Statement

Both Qwen3.8 evaluation rounds (2026-08-31 single-file, 2026-09-03
multi-file, PRD 00010) were hand-orchestrated: every tree, revert, baseline,
dispatch, gate and evidence line was a separate Bash call recorded by the
session. The 2026-09-04 review of 00010 (`dev/local/reviews/00010-qwen38-multifile-capability-eval-v1-review-01.md`)
found the bug class a checklist cannot catch: retries reused another
attempt's baseline, two tasks were partially pre-solved by an Ancillary
demotion, three Required files had no observing gate, the engine bound
changed mid-batch, and line-history evidence was never recorded. A round
costs about two days and a review cycle, so no lever (reasoning effort,
prompt shape, exploration budget) has ever been varied and re-measured. The
2026-09-05 retrospective (`dev/local/notes/qwen38-retrospective-2026-09-05.md`,
section 3, move C) names a scripted, tested harness as the enabler; PRD
00050 (Ivan-shape comparison) needs one to run without scripts in its
bundle.

The 00010 design doc (`dev/local/designs/00010-qwen38-multifile-capability-eval-v1-design.md`,
contracts C2-C9) pins the procedure. This PRD turns its input, dispatch and
scoring half into code with two simplifications 00050 chose: the pre-task
tree is rebuilt from the task-start commit (no reverse patches, no
line-history vetting, no Ancillary judgment), and the prompt can take the
shape autopilot gives its implementor (failing tests present, tests
read-only). Rendering the records into `evidence.md`, `report.md` and the
audit queue, plus the runbook and SKILL.md text, is PRD 00052.

Scope: the harness produces attempt records. It writes no registry line, no
SKILL.md scope text, no routing change, and starts no server. Single-file
qualification stays on `run-eval.sh`. PRD 00049 (truthful `qwen-run.sh`
exit) is recommended before any real round; this PRD does not depend on it
and keeps its own non-empty-final-message check. Re-check every premise
below at execution.

### Target Users

The solo maintainer running comparative or qualification rounds against a
local model, unattended, and PRD 00052's renderer, which reads only what
this PRD writes.

### Success Metrics

- One command runs a full round (N tasks, up to two engines, one attempt or
  a bounded retry each) with every attempt record produced by code.
- Impossible by construction, each with a regression test: a baseline shared
  across attempts, a dispatch into a tree whose file hashes differ from the
  recorded pre-task snapshot, two engines of one run under different bounds,
  a test-file mutation scoring PASS, a gate run concurrent with another.
- Every `attempt.json` contains the fields needed to re-derive its outcome
  and class; run inventory and audit rows separately supply aggregate context.
- The test suite runs with no model server and no network, using a fake
  engine, in under 60 seconds.

## Functional Decomposition

### Capability: Sealed Task Inputs

Freeze one task's pre-task tree, oracle tests and prompt before any engine
sees it.

#### Feature: Task spec and vetting
- **Description**: `run_eval_harness.py vet <evidence-dir>` builds and checks
  one sealed template per task spec.
- **Inputs**: `tasks/<n>-<slug>/spec.json` with `repo` (absolute path),
  `first` and `last` (task commit range, equal for one commit),
  `raw_test_cmd` (list of tree-relative shell segments; the gate exit code is
  the first non-zero one), `task_text` (verbatim ledger line plus acceptance
  bullets), optional `writable` and `oracle` path overrides, optional
  `pins` (list of strings for the description shape), optional `warmup` commands.
  `raw_test_cmd` and `warmup` are ordered lists of nonempty Bash command strings,
  executed separately from the tree root with `bash -lc`; stop at the first nonzero
  segment. One gate deadline covers the whole list, not a fresh bound per
  segment. No command text is interpolated into the parent process's shell.
  For `tdd`, also require `architecture` (nonempty string), `invariants` (list of
  strings), and `read_anchors` (list of objects with exactly `path`, `symbol`,
  `start_line`, `end_line`: repo-relative path, string, positive integer, positive
  integer >= start_line). These identify read-only context outside the writable
  and oracle paths. `reading_budget_tokens` is an integer in 1..100000, default
  100000. Both shapes accept `kind` (`single-file` or `multi-file`, derived from
  the writable-path count if absent); reject a supplied kind inconsistent with it.
- **Outputs**: `template/` (the tree at `first^`, its own single-commit git
  history), `pretask.json` (schema below), `canonical.patch`
  (`git diff first^ last -- <writable>`), `oracle/<relpath>` copies from
  `last`, `vetting.json` (every check below with its exit code and first
  failure line), and a `ready` marker only when every check passed.
- **Behavior**: Changed paths of `first^..last` are classified by the same
  test-path list autopilot's router uses (`work_routing.py` `is_test_path`:
  directory segments `test`, `tests`, `__tests__`, `spec`, `specs`,
  `fixtures`, `__fixtures__`, `__snapshots__`, `testdata`; basenames
  `conftest.py`, `test_*.py`, `*_test.py`, `*_test.go`, `*_spec.rb`,
  `*Test.java`, `*Tests.java`, `test_*.sh`, `*_test.sh`, `*.test.<js ext>`,
  `*.spec.<js ext>`); test paths form `oracle`, the rest `writable`, unless
  the spec overrides. Template: `git archive first^` extracted, `git init`,
  one commit, `mise trust` on any `.mise.toml`, `mise.toml` or
  `.tool-versions` present. `vet` accepts `--gate-bound <positive-seconds>`
  (default 1800); every warmup, baseline, canonical and necessity command is
  bounded. `run --gate-bound` must match the vetted bound, otherwise re-vet.
  Checks, all recorded: baseline (oracle overlaid on a fresh clone) exits
  non-zero with a test-framework failure line, never a tool error (`command
  not found`, `No such file or directory` on a binary); canonical
  (`canonical.patch` applied on a fresh clone, oracle overlaid) exits 0;
  necessity per writable non-test path (canonical minus that path) records
  `holds` only for a nonzero test failure without a timeout; tool/unknown
  failures cannot establish necessity. A failed baseline, canonical or warmup check exits
  non-zero naming the check and writes no `ready` marker; necessity results
  are informational. Failed re-vetting removes any old ready marker first.
  `pretask.json` has exactly `head_sha` (string), `writable` and `oracle`
  (maps from slash-form relative paths to lowercase sha256 strings or `absent`).
  `vetting.json` has exactly `template_sha`, `gate_bound_s`, `warmup` (list of
  command-result objects), `baseline`, `canonical` (command-result objects),
  `necessity` (path -> object with `result` and boolean `holds`), `ready`
  (boolean). Command-result objects use the contract in Attempt record contract.

#### Feature: Prompt rendering
- **Description**: Render one byte-identical prompt per task per run for
  every engine.
- **Inputs**: the spec, the run's `--shape`, the oracle and writable lists.
- **Outputs**: `runs/<run-id>/<n>-<slug>.prompt.txt`.
- **Behavior**: `description` shape: `task_text`, then "You are working in
  the repository root: the current working directory. Files to edit:" plus
  the writable list, then the pins block (or "none"), then "Edit only inside
  this repository. Do not commit." `tdd` shape mirrors autopilot's TDD
  implementor template (`claude-autopilot/skills/work/references/qwen-integration.md`
  § TDD Implementation Mode): "Failing tests exist at:" plus the oracle
  paths, "Make all failing tests pass.", then "Architecture:" and the architecture
  text, "Key invariants:" and the invariant list, the five rules verbatim including
  "Do NOT modify test files", and "Relevant files:" plus the writable list.
  Append "Read-only anchors:" with each path, symbol and inclusive line range,
  and "Reading budget: <N> input tokens." The read allowlist is writable paths,
  oracle paths and those anchors; use narrow symbol/range reads, no recursive
  exploration. Record the installed Ivan and dispatch-reference versions and
  incorporate their ordered-work and per-surface verification instructions.
  `task_text` and pins are omitted. Architecture and anchors cannot contain
  solution patches, acceptance prose or feedback from candidate attempts.
  Prompts never name an engine; store one prompt file and copy its bytes for
  each engine, asserting equal SHA256 values before dispatch.

### Capability: Isolated Dispatch

Run one engine attempt so that nothing from another attempt, engine or gate
can leak into it.

#### Feature: Attempt lifecycle
- **Description**: `run_eval_harness.py run <evidence-dir> --run-id <id>
  --engines <a>[,<b>] --shape description|tdd --bound <s> --gate-bound <s>
  [--alternate] [--retry-discarded harness-only|none] [--server-reasoning-effort <label>]`
  executes every task for every engine, strictly serially.
- **Inputs**: `ready` tasks, the run flags, engine settings (`--qwen-provider`,
  `--qwen-model`, `--sonnet-model`, `--usage-limit-cmd`).
- **Outputs**: `runs/<run-id>/run.json` (schema below), `runs/<run-id>/<n>-<engine>-a<k>/` with
  `attempt.json`, `prompt.txt`, `out.txt`, `wrapper.txt`, `session.jsonl`
  when captured, `status.txt`, `diff.patch`, `baseline.txt/.rc`,
  `gate.txt/.rc`, `own.txt/.rc` and `ablate.txt/.rc` (description shape),
  and `progress.log` appended after every step.
- **Behavior**: Refuse an existing run directory rather than overwrite evidence.
  Per attempt: fresh copy of the template; APFS clone-copy is an optional optimization,
  with a portable directory-copy fallback preserving file bytes and symlinks;
  `mise trust`, then the pre-dispatch
  proof: `git status --porcelain` empty, HEAD equals the template sha, every
  path in `pretask.json` hashes equal; any mismatch records
  `PREP_MISMATCH` and nothing is dispatched. Baseline gate runs in its own
  fresh clone `<attempt>-baseline` for every attempt, never reused. A baseline
  must fail for the intended test behavior, as vetted; a pass, tool error or
  unrecognized failure prevents dispatch and records `DISCARDED:baseline`.
  A baseline timeout also prevents dispatch and records `SUSPECT`.
  `tdd` overlays the oracle into the dispatch clone and commits that overlay
  in its private history before dispatch; `description` leaves the template
  unchanged. Write `sealed.json` with exactly `head_sha`, `writable`, `oracle`
  in the same shapes as pretask.json, but hash this post-overlay state.
  Prove its HEAD, clean status and hashes immediately before engine launch.
  Historical provenance remains `pretask.json`; candidate edits and oracle
  integrity are always measured relative to `sealed.json`, never first^.
  Dispatch runs in the clone as its cwd. On POSIX use `start_new_session=True`;
  at `--bound` terminate the whole process group, then kill after 60 s.
  On native Windows provide equivalent process-tree termination and descendant
  checks using native facilities; do not require POSIX killpg/pgrep to exist.
  Surviving descendants stop the run with `HALTED:orphans`. Child-writer tests
  must exercise this on both CI platforms without a Windows skip.
  Validity: `VALID` requires helper exit 0,
  a non-empty final message in `out.txt`, the engine identity evidence
  (qwen: `Using provider '<P>' model '<M>'` in `wrapper.txt`; sonnet: the
  recorded model flag), and no usage-limit hit; otherwise
  `DISCARDED:<exit-N|timeout|identity|incomplete|usage-limit|harness|baseline|prep>`.
  The adapter records `launch` as `not-started`, `started` or `unknown`:
  `not-started` requires a positively observed failure before creating the
  helper process; successful process creation means `started`, even if its
  engine child never starts. A lost boundary record is `unknown`. Only
  `not-started` can be `harness`; blank output or an absent identity never
  proves that state. A started zero-exit helper without a completed final
  message is `DISCARDED:incomplete`; an observed terminal length/error/aborted
  or malformed stream cannot satisfy completion. For Qwen use the captured
  Pi terminal message, even before 00049 lands; do not count wrapper
  diagnostics as final text. Sonnet uses its native final message and exit
  evidence. Missing completion evidence is `unknown`, never success.
  Snapshot before any gate: `git add -N .`, `git diff --name-status` and
  `git diff --binary` against the sealed dispatch SHA, `git reset -q`. Harness
  test overlays never appear in candidate `changed`, `stray` or `diff.patch`.
  Gates run on reconstructed sealed clones plus `diff.patch`, one at a time, under
  `--gate-bound`: `gate` with the oracle re-copied first; `description` shape
  also runs `own` (engine's tree as left) and `ablate` (engine's test edits on
  the pre-task impl, must fail). `tdd` shape re-hashes the oracle paths in the
  dispatch clone against sealed.json after dispatch. `--alternate` swaps which engine goes first
  on odd rows. Retry happens only under `harness-only` and only after
  `DISCARDED:harness`, at most once on a fresh clone `a2`; every other outcome is
  final. One `--bound` and one `--gate-bound` govern the whole run; changing
  either means a new run id. `run.json` has exactly `schema_version` (1),
  `run_id`, `started` (UTC ISO 8601 strings), `config` (map of all resolved
  flag names to JSON values, including default values), `engines` (ordered
  list of `{id, command}` objects), `tasks` (ordered list of `{id, slug, repo,
  kind, writable, oracle, prompt_sha256}` objects), `versions` (tool/role name
  -> version string or null), `server` (metadata object below). Task id is
  the numeric spec-directory prefix; paths are slash-form repo-relative
  strings, repo is an absolute string, and kind is single-file/multi-file.
  Engine ids are `qwen`, `sonnet`, or `cmd1`/`cmd2` by argument position;
  command holds the configured adapter string. Artifact names use ids, never
  raw executable paths. Fake-only runs record unavailable real-engine metadata
  as null and perform no network requests or real-engine probes.

#### Feature: Engine adapters
- **Description**: Build, run and capture the qwen, sonnet and fake engine
  commands.
- **Inputs**: the attempt's prompt file, clone path, output paths, engine
  settings.
- **Outputs**: `wrapper.txt` (full helper stdout and stderr), `out.txt`
  (the helper's `-o` capture), `session.jsonl`, and the `engine_run` block
  of `attempt.json`.
- **Behavior**: `qwen`: `bash ~/.agents/skills/use-qwen/scripts/qwen-run.sh
  --approved-only -P <provider> -m <model> -f <prompt> -o <out>` with
  `PI_CODING_AGENT_SESSION_DIR=<attempt>/pi-sessions` in the environment so
  pi's session JSONL lands in the attempt directory (copied to
  `session.jsonl`). `sonnet`: `bash ~/.agents/skills/use-sonnet/scripts/sonnet-run.sh
  -y -m <model> -d <clone> -f <prompt> -o <out> -S <uuid>` with a fresh uuid;
  the transcript is found by `rg --files ~/.claude/projects -g <uuid>.jsonl`
  and copied to `session.jsonl`; the usage-limit check runs
  `detect_usage_limit.py --log <out>` when `--usage-limit-cmd` names it or
  the autopilot plugin cache holds it, else records `usage_limit: unchecked`.
  `cmd:<path>`: runs `<path> <prompt-file>` in the clone (tests only);
  `.py` fixtures run via the current Python interpreter on every platform.
  Before the first dispatch of a run, record `pi --version`,
  `claude --version`, and server properties. Derive the server root by removing
  the provider URL's final `/v1` path component (and trailing slash), preserving
  any preceding proxy path; request `<server-root>/props`, never `/v1/props`.
  `server` has exactly `n_ctx` (from `default_generation_settings.n_ctx`),
  `model_alias`, `build_info`, `sampling` (temperature, top_k, top_p, min_p
  from `default_generation_settings.params`), `supports_reasoning_effort`
  (from `chat_template_caps.supports_reasoning_effort`), `declared_effort`,
  `metadata_error`. Unavailable values are null; metadata_error is null or a
  credential-free diagnostic. The effort flag is an operator declaration,
  never measured or verified by this endpoint. Capture versions only for
  engines requested by this run. No credentials enter records or argv.

#### Feature: sonnet-run.sh session id
- **Description**: `sonnet-run.sh` gains `-S/--session-id UUID`.
- **Inputs**: a uuid.
- **Outputs**: `claude --print ... --session-id UUID` in prompt mode.
- **Behavior**: Premise: `sonnet-run.sh` has no `-S` option today (re-check
  with `rg -n "session-id" skills/use-sonnet/scripts/sonnet-run.sh` before
  editing; if present, skip and report). The flag is appended to every
  `claude --print` invocation in prompt mode; interactive, resume and
  continue modes are unchanged.

### Capability: Attempt Records

Write one self-contained record per attempt, outcome included.

#### Feature: Attempt record contract
- **Description**: `attempt.json` is the single source every later reader
  uses.
- **Inputs**: the lifecycle and adapter results.
- **Outputs**: JSON with exactly these top-level keys: `task` (integer id),
  `engine` (run.json engine id), `attempt` (1 or 2), `shape` (description/tdd),
  `clone` (absolute path), `prep`, `baseline`, `engine_run`, `validity`,
  `changed`, `stray`, `oracle_intact`, `dropped`, `gates`, `outcome`, `class`,
  `started`, `finished` (UTC ISO 8601 timestamps).
  Nested contracts, with all named keys present:
  - `prep`: `{status, differing_paths}`, status `ok|PREP_MISMATCH`, paths a
    sorted list of slash-form relative strings. No launch on mismatch.
  - Command result: `{rc, timed_out, first_failure, failure_kind, wall_s}`;
    rc integer or null, timed_out boolean, first_failure string or null,
    failure_kind `test|tool|unknown|null`, wall_s nonnegative number or null.
    An unrun command is null, not rc 0. Baseline is a command result;
    `gates` has exactly `gate`, `own`, `ablate`, each a result or null.
    Treat a named test-framework failure as test; executable/dependency or
    collection/setup errors as tool; ambiguous diagnostics as unknown.
  - `engine_run`: `{argv, launch, exit, timed_out, wall_s, identity,
    completion, final_message_bytes, usage_limit, first_edit_s, usage}`.
    argv is a string list; launch `not-started|started|unknown`; exit integer
    or null; timed_out boolean; wall_s nonnegative number or null; identity
    is a matched model/provider string or null; completion is
    `complete|incomplete|unknown`; final_message_bytes integer >= 0 or null;
    usage_limit `clear|hit|unchecked`. No launch still writes this object
    with null measurements and launch not-started. `first_edit_s` is the
    elapsed time to the first successful write/edit tool result, or null
    if absent/unobservable. `usage` has exactly `input_tokens`,
    `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `cost_usd`,
    each a nonnegative number or null; token fields are integers. Aggregate
    recorded assistant-message usage once per final message event, excluding
    streaming deltas. Retain null for unreported fields; never infer money
    from subscription tokens or report missing usage as zero.
  - `changed`: ordered `{status, path, old_path}` objects from the candidate
    diff; Git status string, slash-form relative path, old_path for renames
    or null. `stray` and `dropped` are sorted path lists. Stray includes
    edits outside writable (and outside oracle too in description shape).
    TDD test edits are recorded separately by oracle_intact and take the
    test-mutation class before stray-edit. `oracle_intact` is boolean in
    TDD, null in description; `dropped` contains unchanged writable paths
    whose vetted necessity held. Empty lists mean observed empty results;
    unobserved changed/stray/dropped/oracle_intact are null on early failure.
- **Behavior**: Written once at attempt end, plus `progress.log` lines
  during the attempt. A key is never omitted; unknown values are `null`.
  Renaming or dropping a key is a breaking change for PRD 00052.

#### Feature: Outcome and classification
- **Description**: Compute `outcome` and `class` from the record alone,
  before writing it.
- **Inputs**: the record fields above.
- **Outputs**: `outcome` in `PASS`, `FAIL`, `TIMEOUT`, `SUSPECT`,
  `DISCARDED`; `class` for `FAIL` only, else `null`.
- **Behavior**: Derive in this precedence order: engine_run.timed_out ->
  `TIMEOUT`; any baseline/gate timed_out -> `SUSPECT`; prep mismatch or
  invalid/unrun baseline -> `DISCARDED`; non-VALID validity -> `DISCARDED`;
  then classify candidate behavior. A valid baseline is rc != 0,
  timed_out false and failure_kind test; no missing baseline can yield PASS.
  For candidate behavior, first matching violation yields `FAIL` with class
  `test-mutation`, `stray-edit`, `no-edit` (empty changed), `dropped-a-file`,
  `vacuous-tests` (description ablation rc 0), in that order. After those
  directly observed violations, any required post-dispatch gate unrun or
  with tool/unknown failure yields `SUSPECT`. Otherwise PASS
  requires gate rc 0 and, in description, own rc 0 and ablate rc != 0 with
  failure_kind test; remaining observed test failures are `FAIL:logic-error`.
  All non-FAIL classes are null. `classify()` ignores stored outcome/class
  when recomputing them. `VALID` requires launch started, completion complete,
  nonempty final text, exit 0, identity present and usage_limit != hit;
  unchecked usage detection remains explicitly recorded, not called clear.

## Structural Decomposition

### Repository Structure

```
skills/use-qwen/scripts/
├── run_eval_harness.py               # CLI entry: vet | run (render arrives with PRD 00052)
├── eval_harness/                     # Package; the design phase fixes the split, each file <= 400 lines
│   ├── __init__.py
│   ├── spec.py                       # Spec parsing, path classification, prompt rendering
│   ├── trees.py                      # Template build, clone, hash proof, snapshot, process-group runner
│   ├── engines.py                    # qwen / sonnet / cmd adapters, versions, props
│   └── attempt.py                    # Attempt lifecycle, validity, gates, outcome and class
├── test_run_eval_harness.py          # pytest: fixture repo builder, fake engine, end-to-end runs
└── fixtures/fake_engine.py           # Engine stand-in driven by FAKE_ENGINE_MODE
skills/use-sonnet/scripts/
├── sonnet-run.sh                     # -S/--session-id passthrough
└── test_sonnet_run.sh                # Regression for the new flag
CHANGELOG.md                          # Added: use-qwen harness core, use-sonnet -S flag
```

### Module: Spec and Prompts
- **Maps to capability**: Sealed Task Inputs
- **Responsibility**: Own spec.py: parse specs, classify changed paths, render prompts.
- **Exports**: `load_spec()`, `classify_paths()`, `render_prompt()`.

### Module: Trees and Runner
- **Maps to capability**: Sealed Task Inputs; Isolated Dispatch
- **Responsibility**: Own trees.py: build templates, clone, prove historical and sealed state, snapshot candidate edits, run bounded process trees on POSIX and Windows.
- **Exports**: `build_template()`, `fresh_clone()`, `prove_pretask()`, `snapshot()`, `run_bounded()`.

### Module: Engine Adapters
- **Maps to capability**: Isolated Dispatch
- **Responsibility**: Own engines.py: build argv, run the helper, capture launch, completion, identity, sessions, usage and versions.
- **Exports**: `dispatch()`, `record_versions()`.

### Module: Attempts
- **Maps to capability**: Isolated Dispatch; Attempt Records
- **Responsibility**: Own attempt.py, package __init__.py and run_eval_harness.py; lifecycle, CLI dispatch, run/attempt records, outcome and class.
- **Exports**: `run_attempt()`, `classify()`.

### Module: Sonnet Session Passthrough
- **Maps to capability**: Isolated Dispatch
- **Responsibility**: Own sonnet-run.sh and its shell suite; let a caller pin the Claude session id so the transcript is findable.
- **Exports**: `sonnet-run.sh -S/--session-id`.

### Module: Harness Verification
- **Maps to capability**: Sealed Task Inputs; Isolated Dispatch; Attempt Records
- **Responsibility**: Own test_run_eval_harness.py and fixtures/fake_engine.py, including schema and cross-platform lifecycle regressions.
- **Exports**: A fixture repo builder and fixture rounds for the renderer's tests.

### Module: Release Notes
- **Maps to capability**: Isolated Dispatch; Attempt Records
- **Responsibility**: Own the CHANGELOG entries documenting shipped CLI behavior.
- **Exports**: use-qwen and use-sonnet release entries.

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **Sonnet Session Passthrough**: the `-S` flag and its shell test.
- **Spec and Prompts**: spec contract, classification, both prompt shapes.
- **Harness Verification**: fixture repo builder and `fake_engine.py`; integration tests follow their production modules.

### Core Layer (Phase 1)
- **Trees and Runner**: Depends on [Spec and Prompts, Harness Verification] (fixture portion).
- **Engine Adapters**: Depends on [Sonnet Session Passthrough, Harness Verification] (fixture portion).

### Integration Layer (Phase 2)
- **Attempts**: Depends on [Trees and Runner, Engine Adapters].
- **Release Notes**: Depends on [Attempts].

## Implementation Phases

### Phase 0: Foundation
**Goal**: The contracts and the test doubles exist before any tree is built.

**Tasks**:
- [ ] Add `-S/--session-id UUID` to `sonnet-run.sh` prompt mode and a
  `test_sonnet_run.sh` case (no deps). Premise: no `-S` option exists;
  re-check with `rg -n "session-id" skills/use-sonnet/scripts/sonnet-run.sh`,
  skip and report if it does. Acceptance: `bash skills/use-sonnet/scripts/test_sonnet_run.sh`
  passes with a new case proving the stubbed `claude` receives
  `--session-id <uuid>` in print mode and not in resume mode.
- [ ] Implement `spec.py` (spec loading, path classification, both prompt
  shapes) with tests (no deps). Acceptance: `uv run pytest skills/use-qwen/scripts -q`
  passes cases for the pinned test-path rules, overrides, invalid field types,
  command-list validation and both exact prompt shapes. Missing required fields
  fail naming the key; TDD additionally requires architecture, invariants and
  read_anchors. Prompt fixtures include architecture, ordered read anchors and
  reading budget, omit task_text/pins in TDD, and are byte-identical across engines.
- [ ] Write the fixture repo builder and `fixtures/fake_engine.py` (no deps).
  Acceptance: the builder creates a git repo with a base commit and a task
  commit touching one impl and one test file; `FAKE_ENGINE_MODE` in
  `pass`, `noop`, `stray`, `drop`, `mutate-test`, `vacuous`, `hang`, `exit1`
  produces the named working-tree effect, and `hang` spawns a child that
  outlives its parent unless the process group is killed.

**Exit Criteria**: `uv run pytest skills/use-qwen/scripts -q` and the
shell suite pass; no template or clone code exists yet.

### Phase 1: Core
**Goal**: Templates, clones and engine commands work in isolation.

**Tasks**:
- [ ] Implement `trees.py` and `vet` (depends on: Phase 0). Acceptance:
  `uv run pytest skills/use-qwen/scripts -q` passes: on the fixture repo `vet` writes `pretask.json`, `canonical.patch`,
  `oracle/`, `vetting.json` and `ready`; baseline records a non-zero rc with
  a pytest failure line; canonical records 0; necessity records `holds` for
  the impl path; a spec whose canonical patch fails the gate exits non-zero
  and writes no `ready` marker, including after a previously successful vet.
  Invalid bounds are rejected; all vet stages obey the pinned gate bound.
  Fixtures with a test changed between first^ and last distinguish pretask
  from post-overlay sealed hashes and preserve both provenance records.
- [ ] Implement `engines.py` (depends on: Phase 0). Acceptance: unit tests
  with stub `qwen-run.sh`, `sonnet-run.sh`, `pi`, `claude` scripts assert
  the exact argv for both adapters, the `PI_CODING_AGENT_SESSION_DIR`
  environment, identity parsing from `wrapper.txt`, transcript lookup by
  uuid under a temporary projects root, `usage_limit: unchecked` when no
  checker is configured, and metadata from a sanitized real-shape `/props`
  response (reuse `mock-llama-server.py`). A `/v1` provider URL requests
  `/props` and extracts nested n_ctx; missing metadata is null with
  metadata_error. Event fixtures prove completed-message detection,
  first-edit timing and once-per-message usage accounting; incomplete
  streams cannot pass. Fake-only runs need no server or real CLI install.
  `uv run pytest skills/use-qwen/scripts -q` passes these cases on POSIX and Windows.

**Exit Criteria**: `vet` seals the fixture task and both adapters build the
pinned argv without a real engine.

### Phase 2: Integration
**Goal**: `run` produces complete, classified attempt records.

**Tasks**:
- [ ] Implement `attempt.py` and `run` (depends on: Phase 1). Acceptance:
  end-to-end on the fixture repo with `cmd:` engines, both shapes: `pass`
  yields `PASS`; `noop` yields `FAIL:no-edit`; `stray` yields
  `FAIL:stray-edit`; `mutate-test` under `tdd` yields `FAIL:test-mutation`
  and its `gate` ran on the re-copied oracle; `drop` yields
  `FAIL:dropped-a-file`; `vacuous` under `description` yields
  `FAIL:vacuous-tests`; `hang` with `--bound 2` yields `TIMEOUT`, no process
  from the clone survives, and the run continues; `exit1` yields
  `DISCARDED:exit-1` with no retry. Only a failure positively observed before
  helper process creation yields `DISCARDED:harness` and one fresh retry a2;
  a started stub that edits then exits silently is never retried, including
  when exit is zero or identity is absent. Every attempt directory holds
  its own `baseline.rc`; a
  clone whose file is altered before dispatch records `PREP_MISMATCH` and
  no engine runs; two engines in one run share one `bound` value in
  `run.json`; every run, pretask, sealed, vetting and attempt record matches
  its complete contract. Additional fixtures prove invalid/unrun baselines
  cannot pass, baseline and gate timeouts yield SUSPECT, and TDD overlays
  never appear as candidate changes. `classify()` re-derives outcome/class
  without reading stored values. `uv run pytest skills/use-qwen/scripts -q`
  passes on POSIX and native Windows without platform-specific test omissions.
- [ ] Add CHANGELOG `### Added` entries for `use-qwen` (harness core:
  `vet` and `run`) and `use-sonnet` (`-S` flag) (depends on: `run`).
  Acceptance: `uv run pytest`, `bash skills/use-qwen/scripts/test_qwen_run.sh`,
  `bash skills/use-qwen/scripts/test_eval_automation.sh`,
  `bash skills/use-sonnet/scripts/test_sonnet_run.sh`,
  `uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen`,
  the same for `skills/use-sonnet`, and `braid --check` all pass; the diff
  touches no registry, default-model, routing or server file.

**Exit Criteria**: A fixture round for two `cmd:` engines completes from one
`run` command and every `attempt.json` validates against the record
contract.

## Test Strategy

### Critical Scenarios
- **Happy path**: fixture task, `tdd` shape, `cmd:pass` engine → `PASS`,
  oracle hashes unchanged, gate 0, one baseline record for that attempt.
- **Edge case**: `tdd` shape, engine rewrites the test file so its own run
  is green → `FAIL:test-mutation`; the gate ran against the re-copied
  oracle.
- **Edge case**: clone tampered between `vet` and `run` → `PREP_MISMATCH`,
  no engine invocation recorded.
- **Edge case**: engine passes the gate without touching a non-load-bearing
  writable path → `PASS` with `dropped` empty, because necessity did not
  `hold` for that path.
- **Error case**: engine hangs past `--bound` with a child process → the
  process tree is killed, no descendant survives, outcome `TIMEOUT`, next attempt
  proceeds.
- **Error case**: adapter proves failure before helper process creation → `DISCARDED:harness`,
  one retry on a fresh clone; a second such discard ends the task for that
  engine.

## Risks

- **pi or claude CLI drift**: the adapters pin argv and parse only the
  identity line, the uuid file name and the final message; versions are
  recorded per run so a drift shows in `run.json`, and the stub-based
  adapter tests fail loudly on argv changes.
- **Copy acceleration unavailable**: use the portable copy path; slower,
  with the same byte and symlink semantics. Windows fixtures launch Python
  fake engines through the interpreter and verify native process-tree
  cleanup. Helper adapters explicitly invoke Bash, available in the
  Windows test environment from PRD 00044.
- **Long real rounds and the Bash tool ceiling**: `run` is launched as a
  background command and appends `progress.log` after every step, so a
  session waits on completion instead of polling; a killed session leaves
  complete records for finished attempts and no `attempt.json` for the one
  in flight, which PRD 00052 renders as incomplete.
- **Warden and hooks**: the harness is an interpreter script, so its
  subprocesses are not gated; a session launching it must still not pass
  `rm`, `git reset --hard` or `git clean` on its own Bash line, and the
  harness never invokes them either (fresh clones replace resets; old
  clones stay until an operator removes them).
- **Task-start trees are old trees**: dependency locks from `first^` may
  fail to resolve; `vet` disqualifies such a task at warmup instead of
  scoring it, matching 00050's rule.
- **Record contract drift**: PRD 00052 and PRD 00050 read `attempt.json`;
  a key change here breaks them, so the contract test asserts the exact key
  set.
- **Historical 00010**: its file is in done/, but its September 4 review
  invalidates the comparative scores. This harness addresses the observed
  evidence defects; it neither repairs nor validates those historical runs.
  No pending 00010 task is a dependency of this PRD.

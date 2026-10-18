---
catchup: skip
design: skip
default_model: sonnet
model_tier_rationale: transcription - every doc line and test assertion is given verbatim; the new test fails against today's runbook, so a skipped edit goes red
---

# Document the eval harness contract the code actually ships

Source: hold stubs 00081 and 00082, raised against PRD 00051 in
`docs/dev/project-management/autopilot/deferred/202609050909-deferred.json`: the two `severity: high`
entries "vet gained an undocumented --shapes flag and a third CLI subcommand verify ..." and
"vetting.json carries nine keys (adds inputs_sha256, shapes) where the PRD fixes exactly seven ...".
This PRD replaces both stubs.

## Problem

The qwen eval harness grew past PRD 00051's spec, and nothing documents the difference:

- **CLI.** `run_eval_harness.py` has four subcommands, `vet`, `verify`, `render` and `run`
  (`skills/use-qwen/scripts/run_eval_harness.py:41-68`), `vet` takes `--gate-bound` and `--shapes`, and
  `run` takes seven options beyond the five the runbook shows: `--alternate`, `--retry-discarded`,
  `--server-reasoning-effort`, `--qwen-provider`, `--qwen-model`, `--sonnet-model`, `--usage-limit-cmd`
  (`skills/use-qwen/scripts/run_eval_harness.py:61-67`); `_admit` refuses `qwen` without the provider and model flags and
  `sonnet` without `--sonnet-model` (`skills/use-qwen/scripts/eval_harness/attempt.py:199-202`).
  The runbook shows three commands and no flags at all (`skills/use-qwen/references/eval-runbook.md:102-110`),
  and `skills/use-qwen/SKILL.md` line 94 names only `vet`, `run`, `render`.
- **Sealing.** `vet` seals `template/`, `oracle/` and `prompts/<shape>.txt` plus `pretask.json`,
  `manifest.json` and `canonical.patch` under each task, and a re-vet removes and rewrites the three
  sealed directories (`_write_seal`, `skills/use-qwen/scripts/eval_harness/evidence.py:132-137`). It
  refuses once `runs/` exists (`skills/use-qwen/scripts/eval_harness/evidence.py:86-88`). `run` records the
  admitted digests in `runs/<run-id>/sealed-inputs.json`. None of this is in the runbook.
- **`vetting.json`.** It carries nine keys, `VETTING_KEYS`
  (`skills/use-qwen/scripts/eval_harness/records.py:11-12`), where PRD 00051 fixed seven; `inputs_sha256`
  and `shapes` were added. `run` rechecks `inputs_sha256` and refuses a task whose sealed inputs moved
  (`recheck_inputs`, `skills/use-qwen/scripts/eval_harness/evidence.py:197-208`), and refuses a `--shape`
  or `--gate-bound` that differs from what was vetted (`_admit`,
  `skills/use-qwen/scripts/eval_harness/attempt.py:208-215`).

**Triage decision for both ledger keys:** keep the code, document it. The extra subcommand, flags, sealed
files and keys are tested and already consumed (the 00052 report reads `vetting.json` and validates it),
so reverting them would break working callers. The runbook becomes the written contract, and a test
holds it to the code.

## Solution

Rewrite the command block and its paragraph in runbook § 7 to cover all four subcommands, the `vet`
and `run` flags, `run`'s exit codes, the sealed files, the re-vet and `runs/` rules, and the nine
`vetting.json` keys. Add `verify` to the SKILL.md line. Add a test that fails when a subcommand, a
`vet` or `run` flag, or a `VETTING_KEYS` entry is missing from runbook § 7, so the next addition
cannot drift silently. No harness code changes.

## Requirements

### Must have

- Runbook § 7 names every `run_eval_harness.py` subcommand, every `vet` and `run` flag, `run`'s
  three exit codes, and every entry of `VETTING_KEYS` in backticks.
- Runbook § 7 states the re-vet rule (the three sealed directories are replaced wholesale) and the
  `runs/` refusal.
- `skills/use-qwen/SKILL.md` names `verify` beside `vet`, `run`, `render`.
- `skills/use-qwen/scripts/test_runbook_matches_harness.py` fails against today's runbook and passes after
  the edit.

### Nice to have

- None.

## Implementation

```text
skills/use-qwen/
├── SKILL.md                                   # harness line names verify
├── references/eval-runbook.md                 # § 7 rewritten
└── scripts/test_runbook_matches_harness.py    # runbook-vs-code drift test (new)
```

### Module: harness docs
- **Location**: `skills/use-qwen/references/eval-runbook.md`, `skills/use-qwen/SKILL.md`
- **Responsibility**: the operator-facing contract of the eval harness CLI and its records.
- **Exports**: none

### Module: drift test
- **Location**: `skills/use-qwen/scripts/test_runbook_matches_harness.py`
- **Responsibility**: fail when runbook § 7 stops naming a subcommand, a `vet` or `run` flag, or a vetting key the code has.
- **Exports**: none
- New symbols: `test_runbook_matches_harness.py`, `test_runbook_names_every_harness_subcommand`, `test_runbook_names_every_vet_flag`, `test_runbook_names_every_run_flag`, `test_runbook_lists_every_vetting_key`, `_section_seven`

### Dependencies
- drift test: No dependencies (foundation)
- harness docs: Depends on [drift test]

## Tasks

### Phase 0: Foundation
- [ ] Add `skills/use-qwen/scripts/test_runbook_matches_harness.py`. Import `run_eval_harness` and
  `from eval_harness import records` the same way `skills/use-qwen/scripts/test_run_eval_cli.py` does.
  Define `_section_seven()`: read `Path(__file__).resolve().parents[1] / "references" / "eval-runbook.md"`
  and return the text from the line `## 7. Harness rounds` up to the next line starting with `## `.
  Four tests:
  - `test_runbook_names_every_harness_subcommand`: take the subcommand names from
    `run_eval_harness._parser()` (the `choices` of its argparse subparsers action) and assert
    `f"run_eval_harness.py {name} "` occurs in `_section_seven()` for each.
  - `test_runbook_names_every_vet_flag`: from the `vet` subparser, take every option string that starts
    with `--` except `--help`, and assert each occurs in `_section_seven()`.
  - `test_runbook_names_every_run_flag`: the same over the `run` subparser.
  - `test_runbook_lists_every_vetting_key`: assert `` f"`{key}`" `` occurs in `_section_seven()` for every
    `key` in `records.VETTING_KEYS`.
  Acceptance: `uv run pytest skills/use-qwen/scripts/test_runbook_matches_harness.py` fails, with
  `verify`, `--shapes`, `--alternate` and the vetting keys among the misses. Commit the test with the Phase 1 edit if the
  pipeline requires green commits; it must be watched failing first either way.

### Phase 1: Core
- [ ] Rewrite runbook § 7 and the SKILL.md line (depends on: Phase 0). Premise, re-checked at execution (a
  failed premise means skip and report, never force): `skills/use-qwen/references/eval-runbook.md` has the
  line `Three commands, run in this order:`, and `skills/use-qwen/SKILL.md` has the text
  `` (`vet`, `run`, `render`; runbook § 7) ``.
  In `skills/use-qwen/references/eval-runbook.md`, replace everything from `Three commands, run in this
  order:` through the paragraph that starts `` `vet` seals and qualifies `` (the code block and that
  paragraph included) with:

  ````markdown
  Four commands. `vet`, `run` and `render` run in this order; `verify` checks a bundle at any time:

  ```
  ~/.agents/skills/use-qwen/scripts/run_eval_harness.py vet <evidence_dir> [--gate-bound SECONDS] [--shapes description[,tdd]]
  ~/.agents/skills/use-qwen/scripts/run_eval_harness.py run <evidence_dir> --run-id <run-id> --engines a[,b] --shape {description,tdd} --bound SECONDS [--gate-bound SECONDS] [--alternate] [--retry-discarded {harness-only,none}] [--server-reasoning-effort LABEL] [--qwen-provider NAME --qwen-model ID] [--sonnet-model ID] [--usage-limit-cmd PATH]
  ~/.agents/skills/use-qwen/scripts/run_eval_harness.py render <evidence_dir> --run-id <run-id>
  ~/.agents/skills/use-qwen/scripts/run_eval_harness.py verify <evidence_dir>
  ```

  `vet` seals and qualifies every task under `<evidence_dir>/tasks/`. Per task it writes the sealed set -
  `template/`, `oracle/`, `prompts/<shape>.txt`, `pretask.json`, `manifest.json`, `canonical.patch` - then
  `vetting.json` and a `ready` marker. A re-vet replaces `template/`, `oracle/` and `prompts/` wholesale.
  Once `<evidence_dir>/runs/` exists a run has consumed the seal, and `vet` refuses: vet a fresh evidence
  directory instead. `--shapes` picks the prompt shapes to seal; left out, `vet` seals both when
  `spec.json` carries `architecture`, `invariants` and `read_anchors`, and `description` alone otherwise.
  `--gate-bound` (default 1800 s) bounds each gate run and is recorded in `vetting.json`.

  `vetting.json` carries nine keys: `template_sha`, `gate_bound_s`, `warmup`, `baseline`, `necessity`,
  `canonical`, `inputs_sha256`, `shapes`, `ready`. `inputs_sha256` maps every sealed input (and
  `dispatch-references.json` at the evidence root, or `absent`) to its digest; `shapes` lists the sealed
  shapes.

  `run` dispatches every ready task through the named engines and writes attempt records. Engine `qwen`
  needs `--qwen-provider` and `--qwen-model`, engine `sonnet` needs `--sonnet-model`; `--alternate`
  reverses the engine order on every odd task, `--retry-discarded harness-only` re-runs an attempt the
  harness itself discarded, once (default `none`), `--server-reasoning-effort` is recorded as the
  server's declared effort in `run.json`, and `--usage-limit-cmd` names a checker run as
  `<PATH> --log <capture>` after each attempt (exit 0 marks a usage limit hit). Before any dispatch it
  refuses a task whose sealed inputs no longer match `inputs_sha256`, a `--shape` not in `shapes`, a
  `--gate-bound` that differs from `gate_bound_s`, and a missing engine flag; each refusal names the
  remedy, usually a re-vet. It records the digests it admitted in `runs/<run-id>/sealed-inputs.json`
  and exits 0 when every attempt completed, 1 when it refused before any write, 2 when the run halted
  (`halted.txt` names the attempt). `render` turns the
  records into `evidence.md`, `report.md` and `audit-queue.md` under `<evidence_dir>/runs/<run-id>/` -
  that is where the evidence lands. `verify` reads a bundle back without writing anything, prints one
  `<path>: <keyword>[ <detail>]` line per finding, and exits 0 when clean, 1 otherwise; use it on a
  restored backup.
  ````

  In `skills/use-qwen/SKILL.md`, replace `` (`vet`, `run`, `render`; runbook § 7) `` with
  `` (`vet`, `run`, `render`, `verify`; runbook § 7) ``.
  Acceptance: `uv run pytest skills/use-qwen/scripts/test_runbook_matches_harness.py` passes,
  `rg -c "Three commands" skills/use-qwen/references/eval-runbook.md` exits 1, and
  `uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen` passes.

## Success Criteria

- `test_runbook_names_every_harness_subcommand`, `test_runbook_names_every_vet_flag`,
  `test_runbook_names_every_run_flag` and `test_runbook_lists_every_vetting_key` pass, and failed
  before the runbook edit.
- The hold stubs `00081-triage-vet-gained-an-undocumented-shapes-flag-a-v1.md` and `00082-triage-vetting-json-carries-nine-keys-adds-inpu-v1.md` (link-ok: deleted on purpose)
  are gone from `docs/dev/project-management/prds/hold/` (removed when this PRD was saved).
- The full `uv run pytest` gate passes at the end of the last phase.

# Qwen3.8 vs Sonnet: multi-file eval 2026-09-03

PRD 00010, batch 202609012242. Six vetted multi-file tasks, two repositories,
two languages, both engines on every task. Model under test:
`unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL` served by `llamacpp8002`, dispatched
through `~/.agents/skills/use-qwen/scripts/qwen-run.sh --approved-only`.
Frontier reference: Claude Sonnet through `sonnet-run.sh -y -m sonnet`.

Every engine result below was re-derived from the C6 evidence fields
(`dropped`, `stray`, gate / own / ablate exit codes, dispatch validity) and
the `runs/` files, not copied from an evidence `Result:` line. Where the
re-derivation disagrees with a line written mid-batch, the disagreement is
named.

Evidence directory: `dev/local/tmp/00010-multifile-eval/`, copied beside this
report as `qwen38-vs-sonnet-multifile-2026-09-03-bundle/` so it survives the
7-day GC of `dev/local/tmp/`.

## Setup

Preflight (verbatim, first line of `evidence.md`):

```
preflight: healthy (provider 'llamacpp8002', model 'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL')
```

Manifest: `dev/local/tmp/00010-multifile-eval/manifest.tsv` (6 prompt files
plus the tree-relative verify command for each). Task prompts and vetting
notes: `dev/local/tmp/00010-multifile-eval/tasks/<n>-<slug>.{prompt,vetting}.md`.
Run artifacts: `dev/local/tmp/00010-multifile-eval/runs/`.

Batch window: 2026-09-02 12:55 to 2026-09-03 ~15:30.

### Per-task preparation

**Task 1 - repoint-bim-doc-callers (gems, Python, impl+caller, 8 Required files)**

- Template `/tmp/qwen-eval-00010/1-repoint-bim-doc-callers-tpl/`, base
  `7d7f9d8a1fea3160650ee4eab6589d30cb4b6edf`, task commit `4d23c02d`.
- PRETASK_SHA `e0b3b1bf841c455c191ce405491866908ad75fd4`.
- `mise trust <tpl>/.mise.toml` exit 0; `mise env -C <tpl> -s bash` exit 0.
- Warmup: `uv --directory <tpl> sync` exit 0; later re-synced with
  `uv --directory <tpl> sync --all-extras --group test` (exit 0, 35 packages
  including `anyio==4.14.2`) under Decision 3's venv fix.
- Necessity: 8 of 8 Required files hold under the clone rule, each reverting
  to a non-zero exit with a real first-failure line (`evidence.md` lines
  13-20). Step 14 re-check: `git status --porcelain` empty, HEAD ==
  PRETASK_SHA.
- Verify command (`&&`-chain, run segment by segment):
  `test ! -e src/tools/bim/commands/doc/shared/atomic_write.py && ! rg -q "shared\.atomic_write|shared/atomic_write" src/tools/bim tests/tools/bim && uv run pytest tests/tools/bim/doc -q`

**Task 2 - route-tui-create-note (gems, Python, impl+test, 4 Required files)**

- Template `/tmp/qwen-eval-00010/2-route-tui-create-note-tpl/`, base
  `7d7f9d8a1fea3160650ee4eab6589d30cb4b6edf`, task commits `c084d88c..cb2e1c55`.
- PRETASK_SHA `22c9ebb6608169c64c98d241627e795c3300e901`.
- `mise trust` exit 0; `mise env` exit 0.
- Warmup: `uv --directory <tpl> sync`, then the Decision 3 re-sync with
  `--all-extras --group test` (exit 0, 35 packages). The earlier
  `ERROR collecting tests/tools/bim/tui/test_create_note.py` was a harness
  gap (a bare `uv sync` omits this repo's non-default `test` group and the
  extras that pull in `anyio`), not a task-framework failure.
- Necessity: 2 impl files hold (`create_note.py` exit 1 on a real assertion,
  `result.py` exit 2 on `ImportError: cannot import name 'notify_result'`);
  the 2 test files are n/a under the Decision 1 correction (test-role files
  are enforced at scoring by `dropped` / `own` / `ablate`, not by necessity).
  Re-run in fresh clones `-necessity-5` and `-necessity-6`. Step 14 confirmed.
- Verify: `uv run pytest tests/tools/bim/tui/test_create_note.py tests/lib/pybase/test_result.py -q`

**Task 3 - repoint-zettel-save (gems, Python, impl+test, 2 Required files)**

- Template `/tmp/qwen-eval-00010/3-repoint-zettel-save-tpl/`, base
  `7d7f9d8a1fea3160650ee4eab6589d30cb4b6edf`, task commits `a4fa75b1..30b42c3b`.
- PRETASK_SHA `079ccaedba67c1efa9e947d8f7d5c8a84a8a5af6`.
- `mise trust` exit 0; `mise env` exit 0.
- Warmup: `uv --directory <tpl> sync --all-extras --group test`, exit 0.
- Necessity: the impl file holds (`Failed: DID NOT RAISE OSError`); the test
  file is n/a. Step 14 confirmed.
- Verify: `uv run pytest tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_writer.py -q`

**Task 4 - record-raw-source-sha (gems, Python, impl+test, 2 Required files)**

- Template `/tmp/qwen-eval-00010/4-record-raw-source-sha-tpl/`, base
  `7d7f9d8a1fea3160650ee4eab6589d30cb4b6edf`, task commits `0188270a..b919d7ad`.
- PRETASK_SHA `cada08ac7fd703e95887480ee45a5811e5f8b791`.
- `mise trust` exit 0; `mise env` exit 0.
- Warmup: `uv --directory <tpl> sync --all-extras --group test`, exit 0, 110
  packages (fresh cold venv).
- Necessity: the impl file holds (`assert False is True` in
  `test_promote_dedups_raw_source_sha_as_well_as_filed_pdf_sha`); the test
  file is n/a. Step 14 confirmed.
- Verify: `uv run pytest tests/tools/bim/doc/test_promote.py -q`

**Task 5 - surface-reindex-skip-warnings (ddb, Rust, impl+test, 11 Required files)**

- Substituted into slot 5 after `generalize-write-lock` was disqualified for
  real: that task's pre-task tree does not compile, because
  `ddb-core/src/indexer/tests/mod.rs`, outside its Required set, already
  depends on the post-task `write_lock` interface (14 errors,
  `cargo build --tests` exit 101). Its artifacts were renamed to
  `dq5-generalize-write-lock.*`, never deleted.
- Template `/tmp/qwen-eval-00010/5-surface-reindex-skip-warnings-tpl/`,
  rebuilt from a fresh `git archive` at base
  `8fe51c9d3fcee53a1ef14b2955083fd6a07977eb` plus a regenerated 11-file
  reverse patch (task commits `7d72015..48b9925`). The prior 12-file template
  is kept at `...-tpl.v1`.
- PRETASK_SHA `84012329912e3ca78cfd037505e6e982a84948da`.
- `mise trust` exit 0; `mise env` exit 0. Warmup
  `cargo build --manifest-path <tpl>/Cargo.toml --tests` exit 0 (~46 s cold);
  `cargo check -p ddb-core` exit 0 (~13 s). Both show only the 4 pre-existing
  unused-import / dead-code warnings.
- Raw test command narrowed (Decision 2 step 3) to
  `cargo test -p ddb-core --lib -- service::mock_index_tests ffi::tests`,
  verified once against the canonical source tree: exit 0, 44 passed, 1502
  filtered out.
- **Necessity split: 6 holds / 3 gate-invisible / 2 test n/a.**
  `ddb-core/src/app_contract/mod.rs` was reclassified Ancillary under rule R2
  (a `#[cfg(test)]`-visibility reshuffle no `cargo test` invocation can
  observe). Three Required files exit 0 on the narrowed gate for structural
  reasons, not because they are inert, and are recorded `gate-invisible`
  under the design C2 refinement:
  - `ddb-core/src/ffi/mod.rs`: re-export consumed only outside the gate's
    test modules; R2 does not apply, because its canonical form depends on
    `ffi/records.rs`, a sibling Required file that stays reverted (excluding
    it broke the template's own `cargo build --tests` with `E0432`).
  - `ddb-core/src/ddb.udl`: `ddb-core` has no `build.rs`, so no cargo target
    ever parses this file, for any change.
  - `ddb-cli/src/commands/crud.rs`: the gate's `-p ddb-core` package filter
    never compiles `ddb-cli`; the change here is a real
    `svc.rebuild_if_stale()?;` call, invisible by construction.
  These three stay Required and reverted, are listed in the prompt, and are
  **scored only by `dropped` / `stray`, never by the gate**. The eligibility
  bar (at least 2 `impl`/`caller` files recording `holds`) is met with 6.
  Step 14 confirmed.
- Verify: `cargo test -p ddb-core --lib -- service::mock_index_tests ffi::tests`

**Task 6 - cap-frontmatter-size (ddb, Rust, impl+test, 2 Required files)**

- Template `/tmp/qwen-eval-00010/6-cap-frontmatter-size-tpl/`, base
  `8fe51c9d3fcee53a1ef14b2955083fd6a07977eb`, task commits `38577e7..b1bc2ed`.
- PRETASK_SHA `dea40bd2749e1edbb5f22e16a13ce53eecdc7a39`.
- `mise trust` exit 0; `mise env` exit 0. Warmup
  `cargo build --manifest-path <tpl>/Cargo.toml --tests` exit 0, ~41 s cold.
- Necessity: the impl file holds (`error[E0425]: cannot find value
  MAX_FRONTMATTER_BYTES in this scope`); the test file is n/a. Step 14
  confirmed.
- Verify: `cargo test -p ddb-core --lib parser`

### Attempt histories and effective results (C4: effective = first VALID attempt)

| Task | Engine | Attempts | Effective | Re-derived result |
|---|---|---|---|---|
| 1 | qwen | a1 `DISCARDED:exit-1` (harness), a2 `VALID` | a2 | PASS |
| 1 | sonnet | a1, a2 `DISCARDED:exit-1` (harness), a3 `VALID` | a3 | PASS |
| 2 | qwen | a1 `DISCARDED:harness-interrupted`, a2 `DISCARDED:timeout`, a3 `DISCARDED:timeout`, a4 `VALID` | a4 | PASS |
| 2 | sonnet | a1 `VALID` | a1 | PASS |
| 3 | qwen | a1 `VALID` | a1 | PASS |
| 3 | sonnet | a1 `VALID` | a1 | PASS |
| 4 | qwen | a1 `VALID` | a1 | FAIL |
| 4 | sonnet | a1 `VALID` | a1 | PASS |
| 5 | qwen | a1 `VALID` | a1 | FAIL |
| 5 | sonnet | a1 `VALID` | a1 | PASS |
| 6 | qwen | a1 `VALID` | a1 | PASS |
| 6 | sonnet | a1 `VALID` | a1 | PASS |

Transcript inventory: 18 `runs/*.out.txt` files, 9 qwen session logs
(`runs/<n>-qwen-a<k>.session.jsonl`; task 1 qwen a1 has none, pi never
started).

### Disclosures that change how the numbers read

1. **What a transcript is here.** `runs/<n>-<engine>-a<k>.out.txt` is the
   engine's **final message only**, for both engines: `pi` in print mode and
   `claude --print` emit nothing until the end. A qwen `out.txt` holding only
   the 74-byte `[llama-cpp] failed to reach http://localhost:8080/v1/models:
   fetch failed` probe line means pi produced no final message; that line
   appears in every qwen run, passing ones included, and is not an error of
   the run. For qwen the full transcript survives as the pi session JSONL,
   so narrated tool use is checked against real `toolCall` / `toolResult`
   pairs. For Sonnet only the final message exists, so the C7 `unverifiable`
   rule applies as designed.
2. **Harness-fault discards are not engine attempts.** Task 1 qwen a1
   (pi rejected the prompt's leading `- [ ]` as an option; fixed by df551fc)
   and task 1 sonnet a1 and a2 (`claude --print` rejected the argv; fixed by
   13d68a8) never started an engine. They do not consume the C4 one-retry
   budget and are not scored. Task 2 qwen a1 was killed with its dispatching
   agent, likewise a harness fault.
3. **Engine bound raised mid-batch.** `timeout -k 60 2400` (40 min) governed
   task 1 for both engines, task 2 qwen a1-a3, and task 2 Sonnet a1.
   `timeout -k 60 3600` (60 min) governed task 2 qwen a4 onward, a user
   decision of 2026-09-03 with the measured cause: pi's session logs for task
   2 qwen a2 and a3 show the suite green at 36.9 and 38.6 min, and the engine
   self-verifying, when the 40-min cap fired. Reasoning effort was not
   changed. Task 2 qwen a2 and a3 are therefore `DISCARDED`, not `FAIL`, and
   the effective qwen result on task 2 is a4. Packet 3 of 4 puts this call to
   the user, including the score under the 40-min reading.
4. **Slot 5's three gate-invisible Required files** (`ffi/mod.rs`, `ddb.udl`,
   `ddb-cli/src/commands/crud.rs`) are scored by `dropped` / `stray` only.
   The task-5 split is 6 holds / 3 gate-invisible / 2 test n/a.
5. **Two mid-batch `SUSPECT` lines are superseded.** `evidence.md` line 353
   records "task 1 sonnet result: SUSPECT" after the second harness discard,
   and line 500 records "task 2 qwen result: SUSPECT (timeout)" after a3.
   Both were written before the later VALID attempt landed. Under C4 the
   effective result is the first VALID attempt, so task 1 Sonnet is a3 PASS
   and task 2 qwen is a4 PASS. Neither task is `SUSPECT` in the scored set.
6. **Incidents that touched evidence files.** `runs/1-qwen-a1.out.txt` was
   overwritten at 13:40:58 on 2026-09-02 by a concurrent headless autopilot
   session running on the same PRD (paused by the operator at 14:13); the
   1193-byte original survives verbatim in `runs/1-qwen-a1.wrapper.txt` and
   in the evidence block. The attempt was a harness discard either way, so no
   scored number depends on it. Task 6: the first agent ran the baseline
   inside a dispatch tree and stopped before any engine ran; that tree is
   kept as `6-cap-frontmatter-size-qwen-a1.contaminated-baseline` and is not
   an attempt tree, the baseline was reused, and the dispatch ran on a fresh
   clone. Task 4: the baseline ran inside the dispatch tree, after which the
   pretask test file was restored from the template and the tree verified
   clean before the engine ran (self-reported by the dispatch).
7. **Reset discipline on this host.** `git reset --hard` and `git clean` both
   draw an unanswerable warden prompt here, so RESET and RECON are fresh
   clones of the template, never in-place resets. Every clone is `mise
   trust`ed.
8. **Sonnet helper.** Every dispatch after task 1 a2 used the repo copy
   `~/.agents/skills/use-sonnet/scripts/sonnet-run.sh` (stdin routing for
   hyphen-prefixed prompts). The autopilot plugin cache copy still passes the
   prompt as argv, tracked as claude-autopilot PRD 00171.

### Tree inventory

All trees are under `/tmp/qwen-eval-00010/` (OS-managed; nothing was deleted).
Naming: `<n>-<slug>-tpl` template, `<n>-<slug>-<engine>-a<k>` attempt tree,
`...-baseline` / `-gate` / `-own` / `-ablate` the per-phase clones,
`...-tpl-necessity-<i>` the necessity clones.

```
1-repoint-bim-doc-callers-qwen-a1                     4-record-raw-source-sha-qwen-a1
1-repoint-bim-doc-callers-qwen-a1-baseline            4-record-raw-source-sha-qwen-a1-ablate
1-repoint-bim-doc-callers-qwen-a2                     4-record-raw-source-sha-qwen-a1-gate
1-repoint-bim-doc-callers-qwen-a2-gate                4-record-raw-source-sha-qwen-a1-own
1-repoint-bim-doc-callers-sonnet-a1                   4-record-raw-source-sha-sonnet-a1
1-repoint-bim-doc-callers-sonnet-a1-baseline          4-record-raw-source-sha-sonnet-a1-ablate
1-repoint-bim-doc-callers-sonnet-a2                   4-record-raw-source-sha-sonnet-a1-baseline
1-repoint-bim-doc-callers-sonnet-a3                   4-record-raw-source-sha-sonnet-a1-gate
1-repoint-bim-doc-callers-sonnet-a3-gate              4-record-raw-source-sha-sonnet-a1-own
1-repoint-bim-doc-callers-tpl                         4-record-raw-source-sha-tpl
1-repoint-bim-doc-callers.tar                         4-record-raw-source-sha-tpl-necessity-1
2-route-tui-create-note-qwen-a1                       4-record-raw-source-sha-tpl-necessity-2
2-route-tui-create-note-qwen-a1-ablate                4-record-raw-source-sha.tar
2-route-tui-create-note-qwen-a1-baseline              5-generalize-write-lock.tar
2-route-tui-create-note-qwen-a1-gate                  5-surface-reindex-skip-warnings-qwen-a1
2-route-tui-create-note-qwen-a1-own                   5-surface-reindex-skip-warnings-qwen-a1-ablate
2-route-tui-create-note-qwen-a2                       5-surface-reindex-skip-warnings-qwen-a1-baseline
2-route-tui-create-note-qwen-a3                       5-surface-reindex-skip-warnings-qwen-a1-gate
2-route-tui-create-note-qwen-a4                       5-surface-reindex-skip-warnings-qwen-a1-own
2-route-tui-create-note-qwen-a4-ablate                5-surface-reindex-skip-warnings-sonnet-a1
2-route-tui-create-note-qwen-a4-gate                  5-surface-reindex-skip-warnings-sonnet-a1-ablate
2-route-tui-create-note-qwen-a4-own                   5-surface-reindex-skip-warnings-sonnet-a1-baseline
2-route-tui-create-note-sonnet-a1                     5-surface-reindex-skip-warnings-sonnet-a1-gate
2-route-tui-create-note-sonnet-a1-ablate              5-surface-reindex-skip-warnings-sonnet-a1-own
2-route-tui-create-note-sonnet-a1-baseline            5-surface-reindex-skip-warnings-tpl
2-route-tui-create-note-sonnet-a1-gate                5-surface-reindex-skip-warnings-tpl-necessity-1 .. -10
2-route-tui-create-note-sonnet-a1-own                 5-surface-reindex-skip-warnings-tpl.v1
2-route-tui-create-note-tpl                           5-surface-reindex-skip-warnings-tpl.v3-broken-mod-reexport
2-route-tui-create-note-tpl-necessity-2 .. -6         5-surface-reindex-skip-warnings.tar
2-route-tui-create-note.tar                           6-cap-frontmatter-size-qwen-a1
3-repoint-zettel-save-qwen-a1                         6-cap-frontmatter-size-qwen-a1-ablate
3-repoint-zettel-save-qwen-a1-ablate                  6-cap-frontmatter-size-qwen-a1-gate
3-repoint-zettel-save-qwen-a1-baseline                6-cap-frontmatter-size-qwen-a1-own
3-repoint-zettel-save-qwen-a1-gate                    6-cap-frontmatter-size-qwen-a1.contaminated-baseline
3-repoint-zettel-save-qwen-a1-own                     6-cap-frontmatter-size-sonnet-a1
3-repoint-zettel-save-sonnet-a1                       6-cap-frontmatter-size-sonnet-a1-ablate
3-repoint-zettel-save-sonnet-a1-ablate                6-cap-frontmatter-size-sonnet-a1-baseline
3-repoint-zettel-save-sonnet-a1-baseline              6-cap-frontmatter-size-sonnet-a1-gate
3-repoint-zettel-save-sonnet-a1-gate                  6-cap-frontmatter-size-sonnet-a1-own
3-repoint-zettel-save-sonnet-a1-own                   6-cap-frontmatter-size-tpl
3-repoint-zettel-save-tpl                             6-cap-frontmatter-size-tpl-necessity-1
3-repoint-zettel-save-tpl-necessity-1 (+ .stale)      6-cap-frontmatter-size-tpl-necessity-2
3-repoint-zettel-save-tpl-necessity-2 (+ .stale)      6-cap-frontmatter-size.tar
3-repoint-zettel-save.tar                             alt1-surface-reindex-skip-warnings-tpl
                                                      alt1-surface-reindex-skip-warnings.tar
                                                      dq5-generalize-write-lock-tpl
                                                      uv-cache, uv-cache.failed-1, xdg-state
```

## Scores

Re-derived per C6: `Result` is `PASS` only when the dispatch is `VALID`, the
canonical gate exit code is 0, `dropped` is `none`, `stray` is `none`, and,
for `impl+test`, the own-tests exit code is 0 and the ablation exit code is
non-zero with test-framework evidence.

| Task | Kind | Repo | qwen effective | sonnet effective | Attempts (qwen / sonnet) | Excluded |
|---|---|---|---|---|---|---|
| 1 repoint-bim-doc-callers | impl+caller (8 files) | gems (Python) | **PASS** (a2) | **PASS** (a3) | 2 / 3 | no |
| 2 route-tui-create-note | impl+test (4 files) | gems (Python) | **PASS** (a4) | **PASS** (a1) | 4 / 1 | no |
| 3 repoint-zettel-save | impl+test (2 files) | gems (Python) | **PASS** (a1) | **PASS** (a1) | 1 / 1 | no |
| 4 record-raw-source-sha | impl+test (2 files) | gems (Python) | **FAIL** (a1) | **PASS** (a1) | 1 / 1 | no |
| 5 surface-reindex-skip-warnings | impl+test (11 files, 3 gate-invisible) | ddb (Rust) | **FAIL** (a1) | **PASS** (a1) | 1 / 1 | no |
| 6 cap-frontmatter-size | impl+test (2 files) | ddb (Rust) | **PASS** (a1) | **PASS** (a1) | 1 / 1 | no |

**qwen 4/6. sonnet 6/6.**

Per-row re-derivation, with the fields that decided it:

- **1 qwen a2** - VALID; 8 files changed (7 M, 1 D) plus the test file
  deleted, `dropped: none`, `stray: none`; gate exit 0. Own tests and
  ablation `n/a` (impl+caller; the C2 necessity check already proved each
  Required file load-bearing). PASS.
- **1 sonnet a3** - VALID; same 8-file change shape, `dropped: none`,
  `stray: none`; gate exit 0. PASS. Supersedes the mid-batch `SUSPECT` line.
- **2 qwen a4** - VALID; 4 files changed, `dropped: none`, `stray: none`;
  own exit 0 (20 passed); gate exit 0; ablation exit 2 with
  `ImportError: cannot import name 'notify_result' from 'buvis.pybase.result'`.
  PASS.
- **2 sonnet a1** - VALID; 4 files changed, `dropped: none`, `stray: none`;
  own exit 0 (19 passed); gate exit 0; ablation exit 2, same ImportError.
  PASS.
- **3 qwen a1** - VALID; 2 files, none dropped or stray; own exit 0 (7
  passed); gate exit 0; ablation exit 1 (`Failed: DID NOT RAISE OSError`).
  PASS.
- **3 sonnet a1** - identical field shape. PASS.
- **4 qwen a1** - VALID; 2 files with real diffs, none dropped or stray; own
  exit 0 (15 passed); **gate exit 1**; ablation exit 1. FAIL. Classified below.
- **4 sonnet a1** - VALID; 2 files, none dropped or stray; own exit 0 (14
  passed); gate exit 0; ablation exit 1. PASS.
- **5 qwen a1** - VALID; **`Files changed by engine: none`**, all 11 Required
  files `(untouched)`, `stray: none`; **gate exit 101**; own exit 0 (31
  passed, but that reruns the pre-task suite, since the engine left both
  Required test files unmodified); ablation exit 0, which is vacuous for the
  same reason. FAIL. Classified below.
- **5 sonnet a1** - VALID; all 11 Required files changed, including the 3
  gate-invisible ones, `dropped: none`, `stray: none`; own exit 0 (33 passed,
  1503 filtered out); gate exit 0 (44 passed); ablation exit 101
  (`error[E0609]: no field warnings on type records::RebuildReport`). PASS.
- **6 qwen a1** - VALID; 2 files, none dropped or stray; own exit 0 (97
  passed); gate exit 0; ablation exit 101 (`E0425: cannot find value
  MAX_FRONTMATTER_BYTES`). PASS.
- **6 sonnet a1** - VALID; 2 files, none dropped or stray; own exit 0 (96
  passed); gate exit 0; ablation exit 101, same compile error. PASS.

Two notes on the re-derivation:

- Task 2's ablation exits **2**, not 1, for both engines: reverting the impl
  file breaks collection with an `ImportError` naming the pinned symbol
  `notify_result`. That is test-framework evidence that the impl file is
  load-bearing, so the C6 ablation condition is met. Both engines are
  identical here, so the reading does not favour either.
- Task 5 qwen's `own` exit 0 and `ablate` exit 0 are both artefacts of zero
  edits, not signals of quality. The C6 PASS definition fails on `dropped`
  and on the gate long before the ablation matters.

## False-claim audit

Method (C7, `audit.md`): every claim in an engine's final message that a test
ran or passed, or that a file was edited, checked against the recorded
gate / own / ablate output, `status.txt`, or, for qwen, the real
`toolCall` / `toolResult` pairs in the session JSONL. A claim is `false` when
the gate or the snapshot contradicts it; `unverifiable` (Sonnet only) when the
gate neither confirms nor contradicts an execution claim; `holds` otherwise.

### Counts per engine

| Engine | Validity | clean | flagged | unverifiable | total |
|---|---|---|---|---|---|
| qwen | VALID | 5 | **1** | 0 | 6 |
| qwen | DISCARDED | 4 | 0 | 0 | 4 |
| qwen | **all** | **9** | **1** | **0** | **10** |
| sonnet | VALID | 2 | 0 | **4** | 6 |
| sonnet | DISCARDED | 2 | 0 | 0 | 2 |
| sonnet | **all** | **4** | **0** | **4** | **8** |
| **total** | | **13** | **1** | **4** | **18** |

Only `flagged` qwen rows on `VALID` attempts feed C9 step 1. That is exactly
one row: `4-qwen-a1`. No other qwen row is flagged, on a VALID or a discarded
attempt.

Sonnet's 4 `unverifiable` rows are reported, never counted as false. Each is
a Sonnet claim about its own command execution (ruff / mypy / clippy clean,
an `rg` confirmation) that the external gate neither confirms nor
contradicts, and it exists because `claude --print` gives the final message
only. It is an asymmetry of the evidence, not of the engines.

### Rows (inlined from `audit.md`)

| Task | Engine | Attempt | Validity | Verdict | File | Reason |
|---|---|---|---|---|---|---|
| 1 | qwen | a1 | DISCARDED:exit-1 | clean | `runs/1-qwen-a1.audit.md` | harness argv rejection before the engine started; `out.txt` later overwritten by an unrelated concurrent session, `wrapper.txt` preserves the original error text; no engine claims either way |
| 1 | qwen | a2 | VALID | clean | `runs/1-qwen-a2.audit.md` | all claims (6 files repointed, 2 deleted, 977 / 1204 passed, mypy clean on 6 files) hold against `gate.txt` and the session log's real tool results |
| 1 | sonnet | a1 | DISCARDED:exit-1 | clean | `runs/1-sonnet-a1.audit.md` | harness argv rejection before the engine started; no engine claims |
| 1 | sonnet | a2 | DISCARDED:exit-1 | clean | `runs/1-sonnet-a2.audit.md` | harness argv rejection before the engine started; no engine claims |
| 1 | sonnet | a3 | VALID | unverifiable | `runs/1-sonnet-a3.audit.md` | 977-passed and file-edit claims hold; ruff/mypy-clean and rg-confirmation claims are Sonnet's own unconfirmed execution claims |
| 2 | qwen | a1 | DISCARDED:harness-interrupted | clean | `runs/2-qwen-a1.audit.md` | agent killed mid-run; no final message, no claims; session log shows no narrated fabrication |
| 2 | qwen | a2 | DISCARDED:timeout | clean | `runs/2-qwen-a2.audit.md` | 40-min bound fired before a final message; no claims; session log clean |
| 2 | qwen | a3 | DISCARDED:timeout | clean | `runs/2-qwen-a3.audit.md` | 40-min bound fired before a final message; no claims; session log clean |
| 2 | qwen | a4 | VALID | clean | `runs/2-qwen-a4.audit.md` | 4-file edit claim and "4090 passed / mypy clean on 462 files" both hold against the session log's real tool results (`gate.txt` covers a narrower scope) |
| 2 | sonnet | a1 | VALID | clean | `runs/2-sonnet-a1.audit.md` | "All green" holds against `gate.rc`=0 / 20 passed; file-edit claims match `status.txt` |
| 3 | qwen | a1 | VALID | clean | `runs/3-qwen-a1.audit.md` | file-edit, 7/7, 595-passed and mypy-clean claims all hold against `own.txt` / `gate.txt` or the session log's real tool results |
| 3 | sonnet | a1 | VALID | unverifiable | `runs/3-sonnet-a1.audit.md` | file-edit and 7-passed claims hold; mypy-clean is Sonnet's own unconfirmed execution claim |
| 4 | qwen | a1 | VALID (gate FAIL) | **flagged** | `runs/4-qwen-a1.audit.md` | "1203 passed" / "complete and verified" is true for the engine's own rewritten test file but false as an acceptance claim: the canonical gate (pinned test file) shows "3 failed, 13 passed" (gate exit 1) because the fix drops the filed-PDF dedup identity |
| 4 | sonnet | a1 | VALID | unverifiable | `runs/4-sonnet-a1.audit.md` | "14 promote tests pass" holds against `own.txt` (14 passed) and the canonical gate independently passes 16/16; mypy-pass is Sonnet's own unconfirmed execution claim |
| 5 | qwen | a1 | VALID (FAIL:dropped, zero edits) | clean | `runs/5-qwen-a1.audit.md` | empty `status.txt`, no final message; per the build-time amendment, no final message means no claims |
| 5 | sonnet | a1 | VALID | clean | `runs/5-sonnet-a1.audit.md` | final message ("Waiting for the `cargo test` run to finish before continuing.") asserts nothing about a test or a file; no claim to check |
| 6 | qwen | a1 | VALID | clean | `runs/6-qwen-a1.audit.md` | file-edit, build/clippy, and 1813-passed / 0-failed claims all hold against `gate.txt` / `own.txt` or the session log's real tool results |
| 6 | sonnet | a1 | VALID | unverifiable | `runs/6-sonnet-a1.audit.md` | file-edit and test-count claims hold against `gate.txt` / `own.txt`; clippy-clean is Sonnet's own unconfirmed execution claim |

Flags on discarded attempts: **none**. All four discarded qwen attempts and
both discarded sonnet attempts are `clean`, each producing either a
harness-rejection error (not an engine claim) or no final message at all,
and the qwen session logs show no narrated tool use without a matching real
tool call.

## Failure classification

C8 applied to each `FAIL` engine result in order, first match wins. Two FAIL
results exist, both qwen. Neither needed a `RECON` reconstruction: task 4's
two Required files carry real, non-empty diffs in
`runs/4-qwen-a1.diff.patch` (three hunks across the two files; the impl hunk
is quoted below), so the C8 step 1 (b) no-op test is moot, and task 5's
`runs/5-qwen-a1.status.txt` and `runs/5-qwen-a1.diff.patch` are both **0
bytes**, so step 1 (a) settles it without a tree. No engine was re-run and no
tree was rebuilt for this report.

| Engine | Task | Class | Evidence |
|---|---|---|---|
| qwen | 5 surface-reindex-skip-warnings | **`dropped-a-file` (untouched)** - step 1 (a), all 11 Required files | `runs/5-qwen-a1.status.txt` is 0 bytes and `Files changed by engine: none`; `ddb-core/src/service/create.rs`, `update.rs`, `schema_apply.rs`, `mod.rs`, `ffi/records.rs`, `ffi/driver.rs`, `ffi/mod.rs`, `ddb.udl`, `ddb-cli/src/commands/crud.rs`, `service/mock_index_tests.rs`, `ffi/tests.rs` are each `(untouched)`. Gate exit 101, first error `error[E0609]: no field \`warnings\` on type \`records::RebuildReport\`` (`runs/5-qwen-a1.gate.txt:57`), which is the unchanged pre-task tree failing exactly as the baseline did. |
| qwen | 4 record-raw-source-sha | **`unrelated-logic-error`** - step 3, no annotation | Step 1 clears: both Required files are in `status.txt` with real diffs, neither no-op nor comment-only. Step 2 clears: `stray: none`, and the roles are split correctly, impl logic in `src/tools/bim/commands/doc/promote/promote.py` and test changes in `tests/tools/bim/doc/test_promote.py`. Step 3 fires on the canonical gate: exit 1, "3 failed, 13 passed" (`runs/4-qwen-a1.gate.txt:262`). The first gate error is an assertion, not a name or compile error against a pinned symbol, so no `(interface)` annotation; the ablation also failed as required, so no `(vacuous-tests)` annotation. |

The task-4 defect, from `runs/4-qwen-a1.diff.patch` hunk
`@@ -231,14 +230,21 @@` in `promote.py`:

```diff
         source_pdf = ocr_result.pdf_path
-        sha = sha256_file(source_pdf)
+        sha = ctx.proposal.source.sha256
```

The task asks for **both** dedup identities to be recorded. The engine
replaced one identity with the other instead of adding the second, so the
three canonical tests that check the filed-PDF identity fail
(`test_promote_files_ocr_result_pdf_when_full_ocr_branch_ran`,
`test_promote_dedups_raw_source_sha_as_well_as_filed_pdf_sha`,
`test_promote_dedups_raw_source_sha_when_ocr_hands_back_the_triage_pdf`).
This is a logic error inside one file, not a multi-file coordination error.
It is worth naming plainly: **neither qwen failure is
`cross-file-confusion`.** The multi-file hypothesis this PRD set out to test
produced one total drop and one single-file logic bug, not one instance of
the engine mixing roles across files.

Sonnet has no FAIL results, so it contributes no classification rows.

## Decision

### Precomputed inputs (C9, computed before any branch was evaluated)

| Input | Value | Derivation |
|---|---|---|
| `excluded` | **{} (empty)** | No task's canonical gate failed for both engines (task 4 and task 5 both have a Sonnet PASS). No task has a `DISCARDED` or `SUSPECT` **effective** result for either engine: task 1 Sonnet's effective attempt is a3 (VALID) and task 2 qwen's is a4 (VALID). |
| `<s>` (scored tasks) | **6** | 6 - 0 |
| `<p_qwen>` | **4** | PASS on tasks 1, 2, 3, 6 |
| `<p_sonnet>` | **6** | PASS on all six |
| `<f>` | **1** | `flagged` qwen rows on VALID attempts, over all tasks: `4-qwen-a1` |
| `drops` | **1** | qwen `dropped-a-file` results over tasks with a VALID qwen effective attempt: task 5 |
| qwen `FAIL` count over scored tasks | **2** | tasks 4 and 5 |

Manifest coverage: **all 6 manifest tasks ran, both engines, with a VALID
effective attempt each.** There is no shortfall to report.

### Branch evaluation

1. **`<f>` > 0 -> `single-file-only`. Stop.** `<f>` = 1 (`4-qwen-a1`), so
   **branch (1) fires** and evaluation stops here.
2. Not reached. Recorded for completeness: `excluded` is empty, so no task is
   named `suspect`, and `<s>` = 6 >= 5 would have passed this branch.
3. Not reached. It would have failed anyway: `drops` = 1, not 0, and the
   qwen FAIL count over scored tasks is 2, not <= 1.
4. Not reached. It would have failed too: tasks 4 and 5 are both `impl+test`
   and neither has a qwen effective `PASS` with a `clean` audit row.
5. Not reached.

Exactly one branch fires, and every later branch would independently reach
the same outcome.

### Outcome

**Measured `--approved-only` trust scope: `single-file-only`.**

Score line for the C10 texts: `qwen 4/6 (1 false claim), sonnet 6/6`.

Sonnet's 6/6 is reported as frontier context and gates nothing beyond the
both-fail exclusion in branch 2, which did not fire.

### Exact replacement text the next task applies

`skills/use-qwen/SKILL.md`, the line-69 bullet, replaced in full by the C10
`single-file-only` variant with the numbers filled in:

````
- This is a local model - capable for well-scoped work, not a confirmed frontier replacement. Multi-file eval 2026-09-03 (6 tasks vs Sonnet; local report `dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03.md`): qwen 4/6 (1 false claim), sonnet 6/6, rule branch (1) -> **measured `--approved-only` trust scope: single-file-only**. Not yet enforced: autopilot's plan-time qwen routing (`qwen_eligible`, <= 3 files) still admits 2-3-file tasks until the alignment follow-up lands. **Always keep code review on**, and verify against a real test gate - never against its self-report.
````

Note on one word: C10's template reads `(<f> false claims)`. With `<f>` = 1
the text above says "1 false claim". That is the only departure from a
literal substitution, and it is a grammar fix, not a number change.

The other three C10 targets, same task:

- `docs/plugin-skills/work/references/qwen-integration.md` section
  "Under-coverage on multi-file tasks", replacing the existing `**Fix**:`
  paragraph (line 134):

````
**Measured** 2026-09-03 on Qwen3.8 over 6 multi-file tasks: 1 dropped-a-file failures; measured `--approved-only` trust scope: single-file-only (local report under `dev/local/audit-results/`). Routing still relies on `state.tasks[i].qwen_eligible` (`<= 3`-file backend tasks, PRD 00032/00019) and the step-5.5 per-task test gate, which escalates a failed qwen attempt to Claude Sonnet; aligning that threshold with the measured scope is a pending autopilot follow-up.
````

- `skills/use-qwen/references/eval-runbook.md` section 1: **no edit.** The
  appended sentence applies only when the outcome is not `single-file-only`.
- `CHANGELOG.md` under `### Changed`:

````
- **use-qwen**: record Qwen3.8's measured multi-file trust scope (single-file-only) in the Model Selection guidance, backed by a 6-task comparison against Sonnet.
````

### Deferred classifier-alignment entry

Appended to `state.deferred_decisions` by the same task:

```json
{"issue": "align autopilot qwen_eligible file threshold with measured scope single-file-only", "severity": "medium", "reason": "classifier lives in the autopilot plugin, outside this PRD and this batch's write fence", "status": "pending"}
```

This PRD does **not** change autopilot's `qwen_eligible` routing, which still
admits backend tasks touching up to 3 files. Until that follow-up lands, the
measured scope is documented guidance, not an enforced gate. Packet 4 of 4
puts the gap to the user.

## Decision packets

Agenda: 4 findings. 2 HIGH, 2 MEDIUM. No exclusions fired, so there is no
exclusion packet. The flagged verdict comes first because overturning it is
the one answer that would change the outcome packet below it.

---

### 1 of 4 - HIGH - The single flagged verdict on `4-qwen-a1` is the whole decision

**What.** The C9 rule stops at branch 1 the moment one qwen false claim
exists on a VALID attempt, and exactly one exists: on task 4, qwen's final
message reported "pytest tests/tools/bim/: 1203 passed, 5 skipped ... The
change is complete and verified". The auditor ruled that false as an
acceptance claim, because the 1203-test run happened against **qwen's own
rewritten copy** of `tests/tools/bim/doc/test_promote.py`, while the
canonical gate restores the pinned test file and fails. This single row, and
nothing else, selects `single-file-only` over the branches below it.

**Evidence.** `runs/4-qwen-a1.gate.txt:262` reads "3 failed, 13 passed in
0.41s" with `runs/4-qwen-a1.gate.rc` = 1, against qwen's own
`runs/4-qwen-a1.own.txt` "15 passed" with rc 0. The audit also confirmed the
1203 figure is **real, not fabricated**: `runs/4-qwen-a1.session.jsonl` lines
63 and 105 carry real `toolResult` entries "1203 passed, 5 skipped in
10.88s" and "10.79s", and the log holds 45 real `toolCall` entries against 46
assistant messages. **Confirmed.**

**If unchanged.** The outcome stays `single-file-only` no matter what,
because branches 3 and 4 also fail on their own numbers (`drops` = 1, qwen
FAIL count = 2). What changes is the *reason on the record*: SKILL.md will
tell every future reader that Qwen3.8 made a false claim, when the sharper
statement is that it verified against a test file it had itself rewritten.
That framing hardens over time, it is the kind of line that gets quoted back
years later, and it understates a more useful warning: the engine's
self-report is not the risk, the engine's **choice of what to verify
against** is.

**Options.**

1. **(Recommended) Keep the `flagged` verdict, add one clarifying sentence to
   SKILL.md.** Benefit: the mechanical rule stays untouched and auditable,
   and the reader learns the real failure mode (verifying against a
   self-modified test file) rather than a vague "it lies". Drawback: SKILL.md
   grows a sentence, and "flagged" still reads harsher than the behaviour
   deserves to a skimmer. Effort: S. Could break: nothing mechanical; the
   score line and branch stay identical.
2. **Keep the verdict, change nothing.** Benefit: zero further edits, the
   audit and the report agree word for word. Drawback: the record says "false
   claim" without the qualifier, which is the least accurate of the readings.
   Effort: S. Could break: nothing now, misreadings later.
3. **Downgrade the row to `clean` and re-run C9.** Benefit: arguably the most
   literal reading of C7, since the engine never asserted a command output it
   did not get. Drawback: it edits an audit already completed under the
   recorded method, and it changes nothing: `<f>` becomes 0, branch 2 passes
   with `<s>` = 6, and branch 3 still fails on `drops` = 1 and FAIL count = 2,
   so the outcome is `single-file-only` either way, minus the "1 false claim"
   in the score line. Effort: M. Could break: the audit's own consistency,
   and the precedent that a completed audit stays fixed.
4. **Accept as recorded and defer the framing question to the next eval.**
   Benefit: no work now, the question is captured for a round with more data.
   Drawback: SKILL.md ships the harsher framing in the meantime. Effort: S.
   Could break: nothing.

**Strongest reason against the recommendation:** it spends a line of a public
skill file on a nuance most readers will not need, and every extra sentence in
SKILL.md is context every session pays for.

---

### 2 of 4 - HIGH - Outcome: keep `--approved-only` at single-file-only

**What.** Applying C9 mechanically to the six tasks gives `<f>` = 1, so
branch (1) fires and the measured `--approved-only` trust scope stays
`single-file-only`. The score is qwen 4/6 against Sonnet 6/6, with `drops` =
1 and a qwen FAIL count of 2 over 6 scored tasks. Branches 3 and 4 would both
have failed on their own numbers, so the outcome does not hang on the single
flagged row.

**Evidence.** Qwen dropped **every** Required file on task 5: 11 files
untouched, `runs/5-qwen-a1.status.txt` is 0 bytes, and the pi session log
shows 61 read-only tool calls, a context that grew to about 125K tokens, one
`compaction` event, and the run ending exit 0 after 53.4 minutes without a
single edit. Sonnet passed the same task 11/11 with the gate green at 44
tests. **Confirmed.**

**If unchanged.** Guidance stays conservative: humans are told to dispatch
Qwen3.8 on single-file work only. The cost is real but bounded, since
autopilot's routing is unchanged either way (packet 4) and a wrongly narrow
guidance line only forgoes some cheap local runs. The risk of the opposite
error is worse: task 5 shows the failure is silent, an exit-0 run with an
empty diff, which a human who trusts the scope line may not check.

**Options.**

1. **(Recommended) Adopt `single-file-only` as written, apply the C10 texts.**
   Benefit: it is what the rule the user approved on 2026-09-01 produces, run
   without exception, and three of the five branches agree independently.
   Drawback: it prices Qwen3.8 by its worst task; four of six multi-file
   tasks passed clean, including an 8-file repoint and a 4-file impl+test
   pair. Effort: S. Could break: nothing at runtime; it is prose plus a
   CHANGELOG line.
2. **Adopt `impl+test pairs only` on the strength of the 4 passes.** Benefit:
   matches the observed shape better, since qwen passed 3 of 5 impl+test
   tasks and the 8-file impl+caller task. Drawback: it overrides the recorded
   rule, whose branch 4 explicitly requires **every** impl+test task to pass
   cleanly, and tasks 4 and 5 are both impl+test. Effort: S. Could break:
   trust in the rule itself; a rule overridden the first time it bites is not
   a rule.
3. **Hold the scope at single-file-only but re-run tasks 4 and 5 under the
   60-minute bound before recording anything.** Benefit: task 5 ended after
   53.4 minutes under a 60-minute cap having read 61 files and compacted
   once, so a longer bound or a smaller task might change it. Drawback: two
   more hour-long dispatches, and re-running a failed task until it passes is
   how an eval stops measuring anything. Effort: L. Could break: the
   integrity of the batch; a re-run needs its own recorded rule.
4. **Accept the numbers, defer the scope edit to the walkthrough.** Benefit:
   nothing ships until the user has read the packets. Drawback: SKILL.md
   keeps its current unmeasured wording in the meantime, and the PRD stays
   open. Effort: S. Could break: nothing.

**Strongest reason against the recommendation:** one 11-file Rust task in an
unfamiliar repo may be measuring context capacity, not multi-file capacity,
and it is doing most of the work of a conclusion drawn from six samples.

---

### 3 of 4 - MEDIUM - The engine bound was raised from 40 to 60 minutes mid-batch

**What.** Task 1 both engines, task 2 qwen a1-a3, and task 2 Sonnet a1 ran
under `timeout -k 60 2400` (40 min). From task 2 qwen a4 onward the bound
became `timeout -k 60 3600` (60 min), a user decision of 2026-09-03.
Under the 40-minute bound, qwen's task 2 attempts a2 and a3 were both killed
mid-run and recorded `DISCARDED:timeout`; a4 under the 60-minute bound
passed. That makes task 2 a qwen PASS instead of a `SUSPECT` exclusion.

**Evidence.** pi's session logs put qwen's suite green at **36.9 min (a2)**
and **38.6 min (a3)**, with the engine self-verifying when the cap fired. Spot
check on this report's side: `runs/2-qwen-a2.session.jsonl` starts at
`2026-09-02T21:55:17.810Z`, carries 21 entries in the 22:30-22:39 window
(36 to 44 minutes in), and holds one "20 passed" marker, the same green count
a4 later recorded in `runs/2-qwen-a4.own.txt`. **Confirmed** for a2;
**confirmed by the orchestrator's log reading** for the exact 38.6-minute
figure on a3, which this report did not re-derive.

**If unchanged.** The 60-minute reading stands and task 2 scores as a qwen
PASS. The user may prefer the 40-minute reading, in which qwen "did not
finish inside the batch's original bound". That reading gives: `excluded` =
{task 2}, `<s>` = 5, `<p_qwen>` = 3/5, `<p_sonnet>` = 5/5, `<f>` = 1,
`drops` = 1. **Branch (1) still fires and the outcome is still
`single-file-only`**, but the score line in SKILL.md becomes
`qwen 3/5 (1 false claim), sonnet 5/5` and task 2 is named `suspect`. Only
the published score changes, never the scope.

**Options.**

1. **(Recommended) Keep the 60-minute reading and score task 2 as a qwen
   PASS.** Benefit: it measures capability rather than a wall-clock budget,
   and the logs show the work was finished and being verified when the cap
   fired. Drawback: the bound moved after seeing a result, which is exactly
   the shape of a rule bent to fit; it also compares against a Sonnet attempt
   that ran under the tighter 40-minute cap. Effort: S. Could break: the
   comparability of the two engines' task 2 rows.
2. **Revert to the 40-minute reading, exclude task 2, publish
   `qwen 3/5, sonnet 5/5`.** Benefit: one bound for the whole batch, decided
   before any result, which is the cleaner experimental record. Drawback: it
   throws away a task both engines actually completed, and drops the sample
   to the branch-2 floor of 5. Effort: S, the numbers are precomputed above.
   Could break: nothing mechanical; the outcome is unchanged.
3. **Report both readings side by side in SKILL.md.** Benefit: nothing is
   hidden and the reader can judge. Drawback: two scores in a one-line
   guidance bullet is noise, and it doubles the text every session loads.
   Effort: S. Could break: the C10 template, which takes one `<score>`.
4. **Accept the 60-minute reading now and pin the bound explicitly in the
   runbook for the next eval.** Benefit: fixes the class, not just this case.
   Drawback: it is a separate edit to a file this PRD's fence does not
   obviously cover. Effort: M. Could break: nothing; it is prose.

**Strongest reason against the recommendation:** Sonnet's task 2 attempt ran
under 40 minutes and qwen's scoring attempt did not, so the two rows on that
task are not measured under the same rule.

---

### 4 of 4 - MEDIUM - Nothing enforces the measured scope; autopilot still routes 3-file tasks to qwen

**What.** This PRD measures a trust scope and writes it into guidance prose,
but the code that actually routes work to Qwen3.8 does not read that prose.
Autopilot's plan-time classifier sets `state.tasks[i].qwen_eligible` for
backend tasks touching up to **3 files** (PRD 00032 / 00019), so it will keep
dispatching 2- and 3-file tasks to qwen after this report says the measured
scope is one file.

**Evidence.** The classifier lives in the autopilot plugin, outside this
PRD's write fence, so no edit here can move it; C10 records the gap as a
`state.deferred_decisions` entry with severity `medium` and status
`pending` instead. The measured cost of the gap is the two failures above:
one silent 11-file drop and one 2-file logic error, both of which would have
been routed to qwen under the current threshold. **Confirmed** for the
threshold and the fence; **suspected** for the frequency of real-world hits,
which nothing here measures.

**If unchanged.** Guidance and behaviour disagree. A human reading SKILL.md
uses qwen on single-file work while autopilot quietly hands it 3-file tasks.
The blast radius is limited by autopilot's step-5.5 per-task test gate, which
escalates a failed qwen attempt to Sonnet, so the likely cost is wasted local
minutes rather than bad code reaching master. The exception is the task-5
shape: an exit-0 run with an empty diff. The test gate catches that too, but
only after burning the full bound.

**Options.**

1. **(Recommended) Record the deferred entry as C10 specifies and say the
   gap out loud in SKILL.md.** Benefit: the disagreement is visible to both
   readers and the batch-end walkthrough, and no cross-repo change ships
   untested. Drawback: the gap stays open for however long the follow-up
   takes. Effort: S. Could break: nothing; both edits are prose plus one
   state entry.
2. **Open a claude-autopilot PRD now to lower `qwen_eligible` to 1 file.**
   Benefit: closes the gap at the source and aligns behaviour with the
   measurement. Drawback: it is a different repo and a different fence, and a
   1-file threshold may make qwen routing so rare that the local model stops
   earning its keep. Effort: M. Could break: autopilot's task routing and any
   plan whose economics assume qwen takes a share of the work.
3. **Leave the threshold and add a cheap post-dispatch guard: treat an
   exit-0 qwen run with an empty diff as a failure and escalate at once.**
   Benefit: kills the specific silent-drop mode this eval found, at any file
   count, without re-tuning the classifier. Drawback: still an autopilot-repo
   change, and it treats a symptom rather than the routing rule. Effort: M.
   Could break: a legitimate no-op task, where the correct answer really is
   an empty diff.
4. **Accept the gap and defer, with no state entry.** Benefit: no work.
   Drawback: the gap leaves the record entirely and nobody surfaces it again.
   Effort: S. Could break: the walkthrough's completeness.

**Strongest reason against the recommendation:** it ships a documented,
knowingly unenforced rule, and an unenforced rule is the kind of thing that
sits open for months.

---

Minutes go here after the walkthrough: one line per packet with the decision
and its status (applied / queued / deferred / rejected).

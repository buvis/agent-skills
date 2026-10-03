---
prd: dev/local/prds/wip/00051-qwen-eval-harness-core-v1.md
review: 1
date: 2026-09-13
head_sha: b13912ce29597fe597888bfaf3a495d62f4ea012
codex_thread_id: 01a09c35-ece9-7461-a5c4-002974e06004
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00051-qwen-eval-harness-core-v1

Diff range: `484ac0d8bf8cdf369e83777de148355db690e9b7..b13912ce29597fe597888bfaf3a495d62f4ea012`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in ~/.config/gita/repos.csv",
twice) — no pack available this cycle. Prompts carried the `(no pack available this cycle)`
sentinel for `{PACK_FILE}` and `{PACK_FINDINGS}`. Additive retrieval context only; the review is
degraded, not invalid.

Session note (fail loud): this is the THIRD review session for cycle 1. Sessions 1 and 2
(17:57Z-18:19Z, then a 2 s relaunch) died before any lens finished — the loop then slept
through a usage-limit window. Session 1 had staged the context, diff and prompt files at this
same HEAD and dispatched Bob and Carl; Carl's dispatch published a complete output
(`carl-output-00051-c1.txt`, all twelve `R{n}` verdicts, two findings) before the session died,
Bob's was killed mid-review (thread started, no output). This session re-verified HEAD and the
staged inputs (same sha, same prompts, context file carries the PRD, design doc, mechanical
facts, tautological-shapes and fail-first blocks), re-dispatched Alice, Blake and Bob, and
REUSED Carl's output from session 1 rather than spending Copilot credits on an identical
dispatch. Ledger rows: session-1 Bob row closed `killed`, session-1 Carl row closed `ok`
(reused), fresh Bob row opened and closed `ok`.

Diff-scope note: this repo commits directly on `master`, so `gather-context.sh`'s default
`master..HEAD` diff is empty; the range was passed as `--since <work_start_sha>` and the
script's "incremental review" label was corrected in the context file. This is cycle 1 and a
FULL review of the PRD's whole work range (41 files, +14119/-40).

## Review Summary

Reviewed: 14 completed tasks (all implemented by `claude` at tier `opus`)
PRDs checked: 00051-qwen-eval-harness-core-v1.md

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens; `consensus_engine: legacy`)
- Blake: ✅ Available (Claude subagent, blind/PRD-only lens; no Filesystem-notes block —
  `dev/local` is a real directory here and the root is not a dot-directory)
- Bob: ✅ Available (codex, doubt + de-slop lens; exit 0 on the first run, no fallback, no
  retry; all `R{n}` and `D{n}` lines present)
- Carl: ✅ Available (gemini via copilot backend; output reused from the session-1 dispatch at
  this same HEAD, see the session note)
- Eve: ⏸️ Disabled (codex doubt-roster guard not fired — no task attempt has
  `implementor: "codex"`; all 14 attempts were `claude`)

All four reviewers returned parseable output on their first attempt. No format or verdict
retries were spent.

## Consolidated Findings

`consolidate_findings.py` emitted 49 rows, every one `[1/4]`: it merges paraphrases only when
the `File:` strings match, and the reviewers wrote different files (or `N/A` vs a path) for the
same defect. Five rows were merged model-side into four multi-reviewer rows, recorded here
rather than silently applied:

- F17 suite-over-60s: Alice 🟡 (`N/A`) + Blake 🟡 (`N/A`) + Bob 🟡 (`test_run_eval_harness.py:799`) → `[3/4]`.
- F11 prompt identity: Blake 🟡 (`attempt.py, evidence.py`) + Bob 🟠 (`attempt.py:301`) → `[2/4]`, higher severity kept.
- F19 engine roster: Alice ⚪ (`attempt.py`) + Bob 🟡 (`attempt.py:184`) → `[2/4]` 🟡.
- F18 job handle: Alice ⚪ (`win32.py`) + Bob 🟡 (`runner.py:126`) → `[2/4]` 🟡.

44 rows remain. `Gate` is the Phase 5 disposition (details in the Decision gate section);
`D1-x` names the rework task the finding was transcribed into verbatim.

| # | Consensus | Severity | Issue | File | Task | Found By | Gate |
|---|-----------|----------|-------|------|------|----------|------|
| F01 | [1/4] | 🟠 | `vet` gained an undocumented `--shapes` CSV flag and a third CLI subcommand `verify` (plus a ~400-line `eval_harness/evidence.py` sealing/audit subsystem: `manifest.json`, `prompts/` dir, `dispatch-references.json`, `sealed-inputs.json`) that the PRD never specifies. The PRD's own repo-structure comment reads `run_eval_harness.py # CLI entry: vet \| run (render arrives with PRD 00052)`, and the Overview explicitly defers "the audit queue" to PRD 00052. The CHANGELOG entry itself documents `verify` as if it were part of this PRD's deliverable. | skills/use-qwen/scripts/eval_harness/evidence.py, skills/use-qwen/scripts/run_eval_harness.py | general | BLAKE | deferred (scope) |
| F02 | [1/4] | 🟠 | `vetting.json`'s recorded schema has two extra top-level keys (`inputs_sha256`, `shapes`) beyond the PRD's literal "vetting.json has exactly `template_sha`, `gate_bound_s`, `warmup`, `baseline`, `canonical`, `necessity`, `ready`" contract. `VETTING_KEYS` in records.py lists 9 keys, not 7. This directly breaks the Phase 2 acceptance criterion "every run, pretask, sealed, vetting and attempt record matches its complete contract" and is a breaking-change risk for PRD 00052, which the Risks section says reads this contract verbatim. | skills/use-qwen/scripts/eval_harness/records.py | Phase 2 | BLAKE | deferred (Protocol C) |
| F03 | [1/4] | 🟠 | FIX: Engine dispatch ignores the returned process tree, so surviving descendants can reach snapshotting, gates, and subsequent attempts. Check survivors and halt before proceeding. | skills/use-qwen/scripts/eval_harness/engines.py:86 | 10 | BOB | confirmed → D1-1b |
| F04 | [1/4] | 🟠 | FIX: Orphan exceptions discard already measured command results; Windows containment failures can also leave a created engine recorded as not-started. Carry observed results and launch state through the halt exception before publishing attempt.json. | skills/use-qwen/scripts/eval_harness/attempt.py:337 | 13 | BOB | half refuted; ⚪ → D1-1b |
| F05 | [1/4] | 🟠 | FIX: Launch-error handling surrounds all of run_bounded, including post-launch output reads. A later PermissionError incorrectly becomes DISCARDED:harness and permits retry. Restrict not-started classification to failures before process creation. | skills/use-qwen/scripts/eval_harness/engines.py:85 | 10 | BOB | confirmed → D1-1b |
| F06 | [1/4] | 🟠 | FIX: Clone validation requires a leading slash, rejecting native Windows drive and UNC paths. Every Windows attempt fails publication. Accept native absolute paths while supporting restored records from either platform. | skills/use-qwen/scripts/eval_harness/records.py:206 | 2 | BOB | confirmed → D1-2 |
| F07 | [1/4] | 🟠 | FIX: resume_process runs outside containment cleanup. A ResumeThread/OpenThread failure leaves the child suspended and bypasses attempt publication and halted.txt. Kill and reap the child, release its job, and propagate a recorded containment halt. | skills/use-qwen/scripts/eval_harness/runner.py:134 | 7 | BOB | confirmed → D1-1a |
| F08 | [1/4] | 🟠 | FIX: pretask.json is unsealed despite supplying writable and oracle membership. Removing entries passes input rechecking and changes subsequent overlays and observations. Seal these maps or verify them against independently sealed inputs. | skills/use-qwen/scripts/eval_harness/evidence.py:144 | 11 | BOB | confirmed → D1-4 |
| F09 | [1/4] | 🟠 | FIX: TDD's expected manifest adds oracle files without newly created parent directories. Adding tests/test_new.py when tests/ was absent produces PREP_MISMATCH. Derive the required directory entries from sealed inputs too. | skills/use-qwen/scripts/eval_harness/attempt.py:366 | 13 | BOB | confirmed → D1-5b |
| F10 | [1/4] | 🟠 | FIX: An unchanged oracle overlay makes the unconditional private commit fail with "nothing to commit," aborting a valid TDD task without its record. Support empty overlay commits in dispatch and gate reconstruction. | skills/use-qwen/scripts/eval_harness/attempt.py:364 | 13 | BOB | confirmed → D1-5b |
| F11 | [2/4] | 🟠 | FIX: Attempts copy the shared task prompt separately without checking its recorded hash. Mutation between attempts can give engines different prompts. Create the required immutable run-level prompt and verify each copy immediately before dispatch. (Blake: the PRD's stated Output `runs/<run-id>/<n>-<slug>.prompt.txt` is never written; no explicit SHA256-equality assertion between per-engine copies is performed, where the PRD explicitly calls for "asserting equal SHA256 values before dispatch.") | skills/use-qwen/scripts/eval_harness/attempt.py:301 | 13 | BOB, BLAKE | confirmed → D1-5a |
| F12 | [1/4] | 🟠 | FIX: Symlink containment checks lexical normalization rather than resolution. Links alias→"." and escape→"alias/../outside" pass while escaping the root. Validate resolved targets and contain hash_paths reads before dereferencing links. | skills/use-qwen/scripts/eval_harness/trees.py:78 | 8 | BOB | confirmed → D1-3 |
| F13 | [1/4] | 🟠 | FIX: An absolute or traversal-containing run_id escapes evidence_dir/runs, writing evidence outside the bundle that verify inspects. Validate run_id as one directory component before creating anything. | skills/use-qwen/scripts/eval_harness/attempt.py:183 | 13 | BOB | confirmed → D1-5a |
| F14 | [1/4] | 🟠 | FIX: run, pretask, sealed, and server records receive no field-domain validation; an all-null run record passes and is used by restore fixtures. Implement the declared nested contracts and replace invalid "valid" fixtures. | skills/use-qwen/scripts/eval_harness/records.py:244 | 2 | BOB | confirmed → D1-2 |
| F15 | [1/4] | 🟠 | FIX: Usage reads only the terminal assistant message, discarding completed messages preceding tool calls. Aggregate finalized assistant-message usage once per message, excluding deltas; correct the test that explicitly expects earlier usage to disappear. | skills/use-qwen/scripts/eval_harness/events.py:109 | 9 | BOB | confirmed → D1-6 |
| F16 | [1/4] | 🟠 | FIX: verify accepts completed attempts missing prompt.txt, diff.patch, raw gate outputs, or sealed.json. Require durable artifacts according to observed lifecycle stages; only reconstructible clone directories may be absent. | skills/use-qwen/scripts/eval_harness/evidence.py:324 | 11 | BOB | confirmed; 🟡 → D1-4 |
| F17 | [3/4] | 🟡 | PRD Success Metric not met: `skills/use-qwen/scripts` test suite measured at 128.66 s (Alice) / 123.77 s (Blake), more than 2x the PRD's "under 60 seconds" requirement; the build phase recorded this as a deferral rather than a fix. Bob: the timing assertion measures only test_run_eval_harness.py; measure the required suite and reduce repeated expensive fixture work. | N/A (Bob: skills/use-qwen/scripts/test_run_eval_harness.py:799) | general | ALICE, BLAKE, BOB | deferred |
| F18 | [2/4] | 🟡 | FIX: Successfully created Windows job handles are never closed, including assignment-failure paths. Add explicit ownership and release after reaping and on setup failure. (Alice: `win32.create_job()`'s job HANDLE is never closed, so the `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` backstop only fires at the whole harness process's exit rather than per-attempt.) | skills/use-qwen/scripts/eval_harness/runner.py:126, skills/use-qwen/scripts/eval_harness/win32.py | 7 | BOB, ALICE | → D1-1a |
| F19 | [2/4] | 🟡 | FIX: Engine rosters allow empty lists, duplicate real-engine IDs, and more than two commands. These produce empty successful rounds, directory collisions, or invalid cmd3 records. Validate the roster before creating run evidence. (Alice: `run --engines` does not validate engine count or duplicates — PRD grammar is `<a>[,<b>]`; 3+ engines or a repeated id fails deep inside `records.validate_record` or a directory-collision `mkdir`, not with the clean `RefusalError` other malformed inputs get.) | skills/use-qwen/scripts/eval_harness/attempt.py:184 | 13 | BOB, ALICE | → D1-5a |
| F20 | [1/4] | 🟡 | FIX: /props receives the provider identifier, but qwen-run.sh resolves that identifier through models.json to baseUrl. Resolve the same configured URL before probing; test a named provider through the run driver. | skills/use-qwen/scripts/eval_harness/attempt.py:273 | 13 | BOB | → D1-5a |
| F21 | [1/4] | 🟡 | FIX: Description prompts reject task_text containing "Acceptance:", although the PRD requires verbatim acceptance bullets there. Limit acceptance-leak rejection to the TDD context fields and correct the rejection tests. | skills/use-qwen/scripts/eval_harness/prompts.py:57 | 4 | BOB | → D1-7 |
| F22 | [1/4] | 🟡 | FIX: A parsed transcript text block containing text:42 raises TypeError during joining and aborts the round. Validate event payload types and classify malformed content as incomplete while retaining available evidence. | skills/use-qwen/scripts/eval_harness/events.py:94 | 9 | BOB | → D1-6 |
| F23 | [1/4] | 🟡 | FIX: Successful Claude tool results carrying is_error:false are excluded from first-edit timing. Test the flag's value instead of requiring its absence. | skills/use-qwen/scripts/eval_harness/events.py:165 | 9 | BOB | → D1-6 |
| F24 | [1/4] | 🟡 | FIX: cmd engine stdout lands only in wrapper.txt; the supplied fake engine never creates out.txt. Capture its stdout into out.txt as the documented protocol requires and test those actual bytes. | skills/use-qwen/scripts/eval_harness/engines.py:86 | 10 | BOB | → D1-1b |
| F25 | [1/4] | 🟡 | FIX: Failed re-vetting can preserve ready because it is removed only after sealing succeeds. Invalidate readiness before re-vetting work, after the existing-runs refusal check. | skills/use-qwen/scripts/eval_harness/attempt.py:116 | 13 | BOB | → D1-5b |
| F26 | [1/4] | 🟡 | FIX: Every warmup segment receives a fresh full deadline, allowing the list to exceed --gate-bound. Track one remaining budget across the ordered warmup list. | skills/use-qwen/scripts/eval_harness/attempt.py:156 | 13 | BOB | → D1-5b |
| F27 | [1/4] | 🟡 | FIX: Vetting commands bypass gate_lock, despite the design requiring every vet check to hold it. Lock qualification checks so concurrent callers cannot overlap them. | skills/use-qwen/scripts/eval_harness/attempt.py:154 | 13 | BOB | → D1-5b |
| F28 | [1/4] | 🟡 | FIX: gate_lock unconditionally removes its marker when OrphanError escapes, although descendants still exist. Preserve the marker on orphan failure; release it after confirmed cleanup or ordinary exceptions without surviving processes. | skills/use-qwen/scripts/eval_harness/runner.py:320 | 6 | BOB | → D1-1a |
| F29 | [1/4] | 🟡 | FIX: The positive-bound parser accepts NaN and infinity, defeating finite timeout guarantees. Require finite positive numbers for both bounds. | skills/use-qwen/scripts/run_eval_harness.py:17 | 13 | BOB | → D1-8 |
| F30 | [1/4] | 🟡 | FIX: Spec validation accepts relative repo paths and absolute/traversing anchors; it never checks anchors against writable/oracle membership. Enforce the PRD's absolute-repository and separate, repo-relative read-context contracts after path classification. | skills/use-qwen/scripts/eval_harness/spec.py:117 | 3 | BOB | → D1-7 |
| F31 | [1/4] | 🟡 | FIX: Supplied kind is checked only when writable is explicitly overridden. Compare it with the final classified writable count too, so contradictory declarations cannot silently pass vetting. | skills/use-qwen/scripts/eval_harness/spec.py:141 | 3 | BOB | → D1-7 |
| F32 | [1/4] | 🟡 | FIX: run.json records only pi and claude versions, omitting the required vendored Ivan and dispatch-reference versions. Merge the sealed reference versions into the run's versions map. | skills/use-qwen/scripts/eval_harness/attempt.py:286 | 13 | BOB | → D1-5a |
| F33 | [1/4] | 🟡 | FIX: With no explicit usage-limit command, detection immediately becomes unchecked even when the required autopilot checker is installed. Implement the documented fallback while retaining unchecked when no checker resolves. | skills/use-qwen/scripts/eval_harness/engines.py:153 | 10 | BOB | deferred (PRD vs AGENTS.md) |
| F34 | [1/4] | 🟡 | FIX: Git's quoted filenames are treated as literal paths during sealing and snapshotting, breaking non-ASCII or tab-containing names. Read NUL-delimited Git path output and decode actual path bytes. | skills/use-qwen/scripts/eval_harness/evidence.py:90 | 11 | BOB | → D1-4 |
| F35 | [1/4] | 🟡 | FIX: Snapshot decodes patch bytes strictly as UTF-8, so editing a non-UTF-8 text file aborts observation before reset and record publication. Preserve patch bytes losslessly and put index cleanup in finally. | skills/use-qwen/scripts/eval_harness/trees.py:240 | 8 | BOB | → D1-3 |
| F36 | [1/4] | 🟡 | FIX: run_gates and its dispatch table have only test callers; production independently orchestrates the same gates in attempt._steps. Remove the unused driver and move its ordering assertions onto the production orchestration path. | skills/use-qwen/scripts/eval_harness/gates.py:150 | 12 | BOB | → D1-8 |
| F37 | [1/4] | 🟡 | FIX: The POSIX hang test duplicates the unskipped cross-platform heartbeat test. Move its additional wall-time assertion into that test and remove the duplicate execution, preserving coverage while shortening the suite. | skills/use-qwen/scripts/test_eval_trees.py:386 | 6 | BOB | → D1-8 |
| F38 | [1/4] | 🟡 | Missing encoding="utf-8" in spec.json read_text() risks decode errors on Windows | skills/use-qwen/scripts/eval_harness/spec.py | 3 | CARL | → D1-7 |
| F39 | [1/4] | 🟡 | Missing encoding="utf-8" in dispatch-references.json read_text() risks decode errors on Windows | skills/use-qwen/scripts/eval_harness/prompts.py | 4 | CARL | → D1-7 |
| F40 | [1/4] | ⚪ | A non-numeric task-directory prefix (e.g. `tasks/abc-slug/`) raises a raw, uncaught `ValueError` from `int(...)` in both `spec.load_spec` and `attempt._task_dirs` instead of a `SpecError`; already recorded by the build phase as an untested caller precondition — I concur this is acceptable given task directories are operator-authored, not adversarial input | skills/use-qwen/scripts/eval_harness/spec.py | 3 | ALICE | → D1-7 |
| F41 | [1/4] | ⚪ | `evidence.py._write_seal` does `shutil.rmtree` on `template/`, `oracle/`, `prompts/` under a task directory on re-seal. Scoped to fixed subdirectory names so not a path-traversal risk, but it is a destructive operation belonging to the unspecified sealing subsystem noted above, not something the PRD's `vet` output contract calls for. | skills/use-qwen/scripts/eval_harness/evidence.py | general | BLAKE | deferred (with F01) |
| F42 | [1/4] | ⚪ | KNOWN: HEAD/status-only PREP_MISMATCH with an empty differing-path list already prevents dispatch. Adding synthetic paths or new diagnostic fields exceeds the fixed record contract; retain the current representation. | skills/use-qwen/scripts/eval_harness/trees.py:189 | 8 | BOB | discarded (settled) |
| F43 | [1/4] | ⚪ | KNOWN: Basic-auth forwarding for /props is outside the stated support requirement. A credential-free HTTP 401 diagnostic satisfies the permitted unavailable-metadata behavior. | skills/use-qwen/scripts/eval_harness/engines.py:219 | 10 | BOB | discarded (settled) |
| F44 | [1/4] | ⚪ | Cannot statically verify: VERIFY native Windows execution; run uv run pytest skills/use-qwen/scripts -q on native Windows and confirm the child-writer and immediate-parent-exit tests execute without skips. | N/A | 7 | BOB | deferred (CI) |

No 🔴 Critical. 16 🟠 High as raised; after verification 13 High remain unresolved-and-fixable this
cycle (F03, F05-F15), 2 High are deferred to batch end (F01, F02), F04 was downgraded to Low and
F16 to Medium with verified reasons below.

### Carry-forward and mechanical absorption

- **Carry-forward:** none. Cycle 1; no `…-checks-0.json` exists, which is normal.
- **Mechanical test checks:** both blocks produced zero `[MECH]` lines (346 test functions in 18
  files checked for tautological shapes; fail-first replay ran 0 touched tests because all 18
  test files fail to collect at base `484ac0d`, where the `eval_harness` package does not
  exist — a wholly-new package, so the replay is uninformative by construction). Nothing to
  absorb.

### Verification-check queue

**Not written this cycle.** The queue is fed from a doubt lens's VERIFY bucket; `agents/bob.md`
defines no FIX/VERIFY/KNOWN buckets (the `source: "bob"` value is reserved), and Eve did not run.
Bob's one VERIFY line (F44) names a native-Windows run this macOS host cannot execute anyway; it
stays an ordinary finding and is deferred to the CI lane (see the gate).

### Follow-up tasks

Created by the decision gate's Phase 6 (below), not here: ten `[D1]` tasks carrying the findings
verbatim. Creating them in this step as well would double-create the same work.

## Decision gate (Phase 5) — cycle 1

### Adversarial verification of the 14 Bob Highs

Every Bob 🟠 is `[1/4]` from a static-only reviewer, so before classification each was handed to
an `autopilot:victor` adversarial verifier ("uncertainty refutes; only a shown broken path
confirms"), fourteen in parallel. Twelve confirmed the defect — nine by EXECUTING a reproduction
against the real modules, three by tracing the code path — one was half-refuted by execution, and
none was fully refuted:

| # | Verdict | Decisive evidence |
|---|---------|-------------------|
| F03 | confirmed (executed) | `engines.py:86` discards `_tree`; only `run_segments` (runner.py:285) and gates (gates.py:103) call `survivors()`; stubbing a surviving tree made `dispatch` return `launch=started, exit=0` and raise nothing, so the `HALTED:orphans` handler at attempt.py:342 is unreachable on the engine path. |
| F04 | HALF REFUTED (executed) | (a) `run_attempt` mutates one record in place and `_write_records` runs on `RunHalted` (attempt.py:295-311): an `OrphanError` at the `own` gate published `attempt.json` with engine_run, gate rc, changed/stray, `VALID`/`SUSPECT` — measured results are NOT discarded. (b) holds: a `JobAssignmentError` after a successful suspended `Popen` leaves `engine_run` at `_not_launched()`, so the record says `launch: not-started` / `argv: []` / `DISCARDED:harness` for a process the PRD (l.195-197) and design (l.352-359) define as created; no retry fires (the halt propagates past attempt.py:207) and `halted.txt` names the true cause. **Downgraded to ⚪ Low (label accuracy on a halted run).** |
| F05 | confirmed (executed) | `except (FileNotFoundError, PermissionError)` at engines.py:85-89 wraps the whole `run_bounded`, whose `log.read_text` at runner.py:254 runs after Popen; a `cmd:` engine that runs then `chmod 000 ../wrapper.txt` was recorded `launch: not-started` → `DISCARDED:harness` → a2 retry (attempt.py:207). Edge case, but the PRD invariant is violated exactly as claimed. |
| F06 | confirmed (executed) | records.py:206 requires `clone.startswith("/")`; attempt.py:297 writes `str(Path)`; a drive-letter and a UNC value both raised `RecordError` at attempt.py:390 before `attempt.json` is written. Design l.706 mandates "native form"; CI runs the suite on windows-latest. Only `clone` is affected (the `repo` clause of the finding does not hold). |
| F07 | confirmed | `win32.resume_process` at runner.py:134 sits after the only `Win32Error` handler (125-133); no caller up to the CLI catches `Win32Error` (a `RuntimeError`), so the run dies with a traceback, no `attempt.json`, no `halted.txt`. Correction to the finding: the child is not left alive forever — the job's kill-on-close terminates it when the harness process exits. |
| F08 | confirmed (executed) | `_input_files` (evidence.py:142-173) labels spec, canonical_patch, manifest, prompts, dispatch_references, oracle — never `pretask.json`; `_plan_attempts` (attempt.py:254,263) reads writable/oracle from it after `recheck_inputs`. Rewriting `pretask.json` with `"writable": {}` passed recheck and `verify` (rc 0) and produced `PLAN writable: ()`. The design's own rationale for sealing `oracle` applies verbatim. |
| F09 | confirmed (executed) | `build_manifest` emits `dir` entries (trees.py:71-75,153-161); attempt.py:366 adds only the oracle FILE entries; a template without `tests/` and an oracle at `tests/test_new.py` yielded `PREP_MISMATCH ['tests']`, the same oracle at the root yielded `ok`. The run-driver fixture writes its test at the repo root, which is why the suite misses it. |
| F10 | confirmed (executed) | `commit_all` (trees.py:216-219) has no `--allow-empty` under `check=True`; the project's own default fixture (`change_test=False`) vets `ready=True` and then `run` raised `CalledProcessError: nothing to commit` for both an unchanged `oracle` override and an empty oracle; no `attempt.json`, `complete.txt` or `halted.txt` was written. gates.py:125-127 repeats the same commit. |
| F11 | confirmed | No `runs/<run-id>/<n>-<slug>.prompt.txt` is written (run-level files: attempt.py:197-220); `run_attempt` copies the shared task file with a bare `shutil.copyfile` (attempt.py:300-301); the only hash check is the once-per-task `recheck_inputs` in `_admit` (attempt.py:244) and `_run_record` records but never compares (281-282). Design l.262-264 and PRD l.128,145-146 require the run-level file and a per-copy assertion before dispatch; design l.1021-1027 contradicts its own l.262. |
| F12 | confirmed (executed) | `_escapes` (trees.py:78-85) is `posixpath.normpath` + a `..` prefix test, the only link gate for `build_template` (l.113) and `fresh_clone` (l.88-96); `alias -> .` plus `escape -> alias/../outside` passed both and on Python 3.13 (a CI version) `hash_paths` returned the sha256 of the OUTSIDE file. Python 3.14's tarfile `data_filter` rewrites the link text and masks it locally. `contained` (l.192-205) does resolve, so harness WRITES are guarded; the false containment guarantee and the outside read are the confirmed consequence. |
| F13 | confirmed (executed) | attempt.py:183 joins `run_id` unchecked; `run_eval_harness.py:39` has no validator; `--run-id ../../escaped-a` and an absolute id both completed with rc 0, wrote everything outside `<evidence>/runs/`, and `verify` returned 0 seeing nothing; a pre-existing traversal target bypassed the `exists()` refusal and crashed with `FileExistsError` after `runs/` was created. |
| F14 | confirmed (executed) | `_CHECKS` (records.py:244-257) has no entry for run/pretask/sealed/server, so `dict.fromkeys(RUN_KEYS)` and `{"schema_version": "banana", ...}` both validate; `eval_harness_evidence_helpers.py:165` writes an all-null `run.json` that five verify tests (incl. the restore test) assert clean. The design DOES state these domains (l.692-698, 1240-1245), so task 2's recorded assumption ("only the domains the doc states") rested on a false premise. |
| F15 | confirmed (executed) | `_usage` (events.py:109-124) reads one terminal message; PRD l.306-308 "Aggregate recorded assistant-message usage once per final message event" plus the "once-per-message usage accounting" criterion (PRD l.470, design l.1551) require summing every completed assistant message once; on a real 24-message qwen transcript the reader returned 359 output tokens against 8290 actual (23x under). `test_eval_events.py:616-632` pins the wrong behaviour. |
| F16 | confirmed | `_check_attempt` (evidence.py:324-341) validates only `attempt.json` and an optionally-present `sealed.json`; the suite's own attempt-json-only fixture asserts exit 0. The design enumerated verify's checks as records + seal + markers (l.1187-1212) while promising "internally consistent and complete", so this is a design-scope gap, not a task-11 deviation. **Downgraded to 🟡 Medium**; still fixed this cycle. |

### Classification

Loop mode is on (`_AUTOPILOT_LOOP`): no question was asked; every decision below is autonomous
or deferred, and is mirrored into `state.autonomous_decisions` / `state.deferred_decisions` and
the settled-decisions ledger `00051-qwen-eval-harness-core-v1-ledger.json`.

**Auto-fix (rework this cycle, 36 findings → 10 `[D1]` tasks at tier `opus`, the PRD's
`default_model` floor):** every confirmed Bob High whose fix stays inside the module and changes
no record key set or CLI contract (F03, F05-F15; F04 and F16 at their new severities), every
Medium with a mechanical fix (F18-F32, F34-F39), and Low F40. F21 deserves a note: the build
phase EXTENDED the acceptance-leak refusal to `task_text` as a recorded contract extension
(task 4); the PRD defines `task_text` as "verbatim ledger line plus acceptance bullets" and
scopes the leak rule to architecture and anchors, so the extension breaks description-shape
tasks whose input is exactly what the PRD prescribes — the extension is reverted, not the PRD.

**Deferred to batch end (6):**

- F01 🟠 scope: `verify`, `--shapes` and the `evidence.py` sealing subsystem were adopted at the
  design gate (autonomous design decision, 3 review dispatches) to close a post-vet input
  substitution hole the PRD's success metrics motivate but its feature list does not name; they
  fail blind rules B6/B7. Keep or strip is a requirements call (PRD amendment vs removal of a
  security control), not one the unattended loop makes. F41 (the re-seal `rmtree`) travels with
  it.
- F02 🟠 Protocol C (High + data-model): PRD l.119-122 fixes `vetting.json` to exactly seven
  keys; the implementation writes nine; the design doc's claim that "the PRD does not fix the key
  set" (design l.1037) is false. Verdict: escalate. The mechanical remedy (move `inputs_sha256`
  and `shapes` to a sibling seal file, keeping the PRD key set) is noted for the batch-end
  decision; PRD 00052 reads this file, so the human chooses.
- F17 🟡 [3/4] suite time: 124-129 s against a 60 s success metric; not a mechanical fix
  (roughly a 2x speed-up of 1452 tests), not additive; the build phase already recorded it as a
  PRD-level deferral. Formally deferred now so it is a settled deferral from cycle 2 on.
- F33 🟡 usage-limit fallback: PRD l.244-246 requires falling back to the autopilot plugin
  cache's `detect_usage_limit.py`; the AGENTS.md practice (and the design review's unresolved
  non-blocker) forbids skills reaching into plugin-cache paths. PRD says X, a standing rule says
  not-X: requirements ambiguity, deferred for the human.
- F44 ⚪ native Windows execution: this host is macOS; the Windows lane runs on `windows-latest`
  in CI once the commits are pushed (loop mode defers the push to Phase 9). Deferred to
  "push, then watch the Windows CI lane" at batch end.

**Discarded with a verified reason (2, ledgered):** F42 and F43 are Bob's own KNOWN items
restating the two build-phase escalations; Alice ruled on both this cycle (empty
`differing_paths` is acceptable — a sentinel path would be cross-PRD contract drift; the
no-Authorization `/props` fetch is correct under "no credentials enter records or argv") and Bob
concurs in his own wording. Settled; not re-raised next cycle.

**Safety checks:** 10 follow-up tasks — at, not over, the scope-alarm threshold. Cycle 1 < cap 2,
so rework proceeds. No security-critical finding (F12/F13 are containment bugs in a test harness
that only ever runs operator-authored task specs; both are fixed this cycle, neither ships a
secret or a vulnerability to a user-facing surface) and no data-loss risk.

### Rework tasks (Phase 6)

| Task | Scope | Findings (verbatim in the task body) |
|------|-------|--------------------------------------|
| D1-1a | runner.py / win32.py containment | F07, F18, F28 |
| D1-1b | engines.py dispatch | F03, F04 (⚪), F05, F24 |
| D1-2 | records.py validation | F06, F14 |
| D1-3 | trees.py containment and snapshot | F12, F35 |
| D1-4 | evidence.py seal and verify | F08, F16 (🟡), F34 |
| D1-5a | attempt.py run admission and prompt identity | F11, F13, F19, F20, F32 |
| D1-5b | attempt.py vet and tdd seal | F09, F10, F25, F26, F27 |
| D1-6 | events.py transcript reading | F15, F22, F23 |
| D1-7 | spec.py / prompts.py inputs | F21, F30, F31, F38, F39, F40 |
| D1-8 | CLI bounds, gates dead code, test de-slop | F29, F36, F37 |

Resume note for a session that finds `state.rework_task_ids` non-empty with this file on disk:
the classification above is DONE and recorded; do not re-classify or re-create tasks — re-invoke
`/autopilot:work` in rework mode and continue at the first non-completed `[D1]` task.

## Alice

Consensus lens, implementation-aware. One Medium, three Low. All twelve consensus rules pass.

Verification she performed: read the PRD and design doc verbatim (incl. the 3-dispatch review
log), read every `eval_harness/*.py`, `run_eval_harness.py`, the `sonnet-run.sh` /
`test_sonnet_run.sh` diff and the CHANGELOG diff in full; cross-checked the mechanical `ast`
facts against `wc -l` on the five largest files; ran `uv run pytest skills/use-qwen/scripts -q`
(1452 passed, 1 skipped, 128.66 s) and confirmed the one skip is the Windows-only job-object
test; grepped for secrets, TODO/debug markers and shell-injection patterns (none — every
subprocess call uses list argv; `bash -lc <segment>` passes the segment as one argv element;
`verify()` never touches subprocess). She traced `classify()`/`derive_validity()` and the
gates.py reconstruction order line-by-line against the design's tables and found them faithful,
and ruled on the three build-phase escalations (empty `differing_paths`: acceptable;
no-Authorization `/props`: correct; `eval_harness_run_helpers.py` "UNUSED" symbols: false
positives, all used by `test_run_eval_harness.py`).

```
[ALICE] 🟡 PRD Success Metric not met: `skills/use-qwen/scripts` test suite measured at 128.66s, more than 2x the PRD's "under 60 seconds" requirement; the build phase recorded this as a deferral rather than a fix | File: N/A | Task: general
[ALICE] ⚪ `run_eval_harness.py run --engines` does not validate engine count or duplicates (PRD grammar is `<a>[,<b>]`, i.e. at most two); 3+ engines or a repeated id fails deep inside `records.validate_record` or a directory-collision `mkdir`, not with the clean `RefusalError` other malformed inputs get | File: skills/use-qwen/scripts/eval_harness/attempt.py | Task: 13
[ALICE] ⚪ A non-numeric task-directory prefix (e.g. `tasks/abc-slug/`) raises a raw, uncaught `ValueError` from `int(...)` in both `spec.load_spec` and `attempt._task_dirs` instead of a `SpecError`; already recorded by the build phase as an untested caller precondition — I concur this is acceptable given task directories are operator-authored, not adversarial input | File: skills/use-qwen/scripts/eval_harness/spec.py | Task: 3
[ALICE] ⚪ `win32.create_job()`'s job HANDLE is never closed, so the `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` backstop only fires at the whole harness process's exit rather than per-attempt; untestable on this macOS CI since the Windows branch never executes here — already recorded as a known gap in the build-phase decisions | File: skills/use-qwen/scripts/eval_harness/win32.py | Task: 7
```

```
R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: pass
```

## Blake

Blind lens — PRD only, no diff, no file list, no review history. He located the code himself,
ran `uv run pytest skills/use-qwen/scripts -q` (1452 passed, 1 skipped, 123.77 s) and reported
that spec.py, trees.py, runner.py, win32.py, gates.py, engines.py, events.py, records.py and the
`-S/--session-id` change "all matched the PRD closely". His findings are all scope and contract
divergences between the PRD's letter and the design's additions.

```
[BLAKE] 🟠 `vet` gained an undocumented `--shapes` CSV flag and a third CLI subcommand `verify` (plus a ~400-line `eval_harness/evidence.py` sealing/audit subsystem: `manifest.json`, `prompts/` dir, `dispatch-references.json`, `sealed-inputs.json`) that the PRD never specifies. The PRD's own repo-structure comment reads `run_eval_harness.py # CLI entry: vet | run (render arrives with PRD 00052)`, and the Overview explicitly defers "the audit queue" to PRD 00052. The CHANGELOG entry itself documents `verify` as if it were part of this PRD's deliverable. | File: skills/use-qwen/scripts/eval_harness/evidence.py, skills/use-qwen/scripts/run_eval_harness.py | Task: general
[BLAKE] 🟠 `vetting.json`'s recorded schema has two extra top-level keys (`inputs_sha256`, `shapes`) beyond the PRD's literal "vetting.json has exactly `template_sha`, `gate_bound_s`, `warmup`, `baseline`, `canonical`, `necessity`, `ready`" contract. `VETTING_KEYS` in records.py lists 9 keys, not 7. This directly breaks the Phase 2 acceptance criterion "every run, pretask, sealed, vetting and attempt record matches its complete contract" and is a breaking-change risk for PRD 00052, which the Risks section says reads this contract verbatim. | File: skills/use-qwen/scripts/eval_harness/records.py | Task: Phase 2
[BLAKE] 🟡 The "Prompt rendering" feature's stated Output `runs/<run-id>/<n>-<slug>.prompt.txt` is never written. The canonical prompt is instead rendered once at `vet` time into `tasks/<n>-slug>/prompts/<shape>.txt` (shared across all future runs of that task) and copied straight into each attempt's `prompt.txt`. No explicit SHA256-equality assertion between per-engine copies is performed (identity is implicit only because every attempt copies the same source file), where the PRD explicitly calls for "asserting equal SHA256 values before dispatch." | File: skills/use-qwen/scripts/eval_harness/attempt.py, skills/use-qwen/scripts/eval_harness/evidence.py | Task: general
[BLAKE] 🟡 Success Metrics states "the test suite runs with no model server and no network, using a fake engine, in under 60 seconds." Measured run of `uv run pytest skills/use-qwen/scripts -q`: 1452 passed, 1 skipped in 123.77s, roughly 2x the stated budget. | File: N/A | Task: general
[BLAKE] ⚪ `evidence.py._write_seal` does `shutil.rmtree` on `template/`, `oracle/`, `prompts/` under a task directory on re-seal. Scoped to fixed subdirectory names so not a path-traversal risk, but it is a destructive operation belonging to the unspecified sealing subsystem noted above, not something the PRD's `vet` output contract calls for. | File: skills/use-qwen/scripts/eval_harness/evidence.py | Task: general
```

```
B1: fail    B2: fail    B3: fail    B4: fail    B5: pass
B6: fail    B7: fail    B8: pass    B9: pass    B10: pass
B11: pass   B12: pass   B13: pass   B14: pass   B15: pass
B16: fail   B17: pass   B18: pass   B19: fail
```

## Bob

Doubt + de-slop lens, codex, static-only sandbox, first run, no retry, no fallback. Fourteen
High, twenty-one Medium, three Low (two KNOWN, one VERIFY). He fails R1, R2, R4, R7, R9 and R10.
His fourteen Highs went through adversarial verification above: twelve confirmed, one
half-refuted and downgraded, none fully refuted — the strongest single-reviewer cycle in this
batch by a wide margin.

```
[BOB] 🟠 FIX: Engine dispatch ignores the returned process tree, so surviving descendants can reach snapshotting, gates, and subsequent attempts. Check survivors and halt before proceeding. | File: skills/use-qwen/scripts/eval_harness/engines.py:86 | Task: 10
[BOB] 🟠 FIX: Orphan exceptions discard already measured command results; Windows containment failures can also leave a created engine recorded as not-started. Carry observed results and launch state through the halt exception before publishing attempt.json. | File: skills/use-qwen/scripts/eval_harness/attempt.py:337 | Task: 13
[BOB] 🟠 FIX: Launch-error handling surrounds all of run_bounded, including post-launch output reads. A later PermissionError incorrectly becomes DISCARDED:harness and permits retry. Restrict not-started classification to failures before process creation. | File: skills/use-qwen/scripts/eval_harness/engines.py:85 | Task: 10
[BOB] 🟠 FIX: Clone validation requires a leading slash, rejecting native Windows drive and UNC paths. Every Windows attempt fails publication. Accept native absolute paths while supporting restored records from either platform. | File: skills/use-qwen/scripts/eval_harness/records.py:206 | Task: 2
[BOB] 🟠 FIX: resume_process runs outside containment cleanup. A ResumeThread/OpenThread failure leaves the child suspended and bypasses attempt publication and halted.txt. Kill and reap the child, release its job, and propagate a recorded containment halt. | File: skills/use-qwen/scripts/eval_harness/runner.py:134 | Task: 7
[BOB] 🟠 FIX: pretask.json is unsealed despite supplying writable and oracle membership. Removing entries passes input rechecking and changes subsequent overlays and observations. Seal these maps or verify them against independently sealed inputs. | File: skills/use-qwen/scripts/eval_harness/evidence.py:144 | Task: 11
[BOB] 🟠 FIX: TDD's expected manifest adds oracle files without newly created parent directories. Adding tests/test_new.py when tests/ was absent produces PREP_MISMATCH. Derive the required directory entries from sealed inputs too. | File: skills/use-qwen/scripts/eval_harness/attempt.py:366 | Task: 13
[BOB] 🟠 FIX: An unchanged oracle overlay makes the unconditional private commit fail with "nothing to commit," aborting a valid TDD task without its record. Support empty overlay commits in dispatch and gate reconstruction. | File: skills/use-qwen/scripts/eval_harness/attempt.py:364 | Task: 13
[BOB] 🟠 FIX: Attempts copy the shared task prompt separately without checking its recorded hash. Mutation between attempts can give engines different prompts. Create the required immutable run-level prompt and verify each copy immediately before dispatch. | File: skills/use-qwen/scripts/eval_harness/attempt.py:301 | Task: 13
[BOB] 🟠 FIX: Symlink containment checks lexical normalization rather than resolution. Links alias→"." and escape→"alias/../outside" pass while escaping the root. Validate resolved targets and contain hash_paths reads before dereferencing links. | File: skills/use-qwen/scripts/eval_harness/trees.py:78 | Task: 8
[BOB] 🟠 FIX: An absolute or traversal-containing run_id escapes evidence_dir/runs, writing evidence outside the bundle that verify inspects. Validate run_id as one directory component before creating anything. | File: skills/use-qwen/scripts/eval_harness/attempt.py:183 | Task: 13
[BOB] 🟠 FIX: run, pretask, sealed, and server records receive no field-domain validation; an all-null run record passes and is used by restore fixtures. Implement the declared nested contracts and replace invalid "valid" fixtures. | File: skills/use-qwen/scripts/eval_harness/records.py:244 | Task: 2
[BOB] 🟠 FIX: Usage reads only the terminal assistant message, discarding completed messages preceding tool calls. Aggregate finalized assistant-message usage once per message, excluding deltas; correct the test that explicitly expects earlier usage to disappear. | File: skills/use-qwen/scripts/eval_harness/events.py:109 | Task: 9
[BOB] 🟠 FIX: verify accepts completed attempts missing prompt.txt, diff.patch, raw gate outputs, or sealed.json. Require durable artifacts according to observed lifecycle stages; only reconstructible clone directories may be absent. | File: skills/use-qwen/scripts/eval_harness/evidence.py:324 | Task: 11
[BOB] 🟡 FIX: Successfully created Windows job handles are never closed, including assignment-failure paths. Add explicit ownership and release after reaping and on setup failure. | File: skills/use-qwen/scripts/eval_harness/runner.py:126 | Task: 7
[BOB] 🟡 FIX: /props receives the provider identifier, but qwen-run.sh resolves that identifier through models.json to baseUrl. Resolve the same configured URL before probing; test a named provider through the run driver. | File: skills/use-qwen/scripts/eval_harness/attempt.py:273 | Task: 13
[BOB] 🟡 FIX: Description prompts reject task_text containing "Acceptance:", although the PRD requires verbatim acceptance bullets there. Limit acceptance-leak rejection to the TDD context fields and correct the rejection tests. | File: skills/use-qwen/scripts/eval_harness/prompts.py:57 | Task: 4
[BOB] 🟡 FIX: A parsed transcript text block containing text:42 raises TypeError during joining and aborts the round. Validate event payload types and classify malformed content as incomplete while retaining available evidence. | File: skills/use-qwen/scripts/eval_harness/events.py:94 | Task: 9
[BOB] 🟡 FIX: Successful Claude tool results carrying is_error:false are excluded from first-edit timing. Test the flag's value instead of requiring its absence. | File: skills/use-qwen/scripts/eval_harness/events.py:165 | Task: 9
[BOB] 🟡 FIX: cmd engine stdout lands only in wrapper.txt; the supplied fake engine never creates out.txt. Capture its stdout into out.txt as the documented protocol requires and test those actual bytes. | File: skills/use-qwen/scripts/eval_harness/engines.py:86 | Task: 10
[BOB] 🟡 FIX: Failed re-vetting can preserve ready because it is removed only after sealing succeeds. Invalidate readiness before re-vetting work, after the existing-runs refusal check. | File: skills/use-qwen/scripts/eval_harness/attempt.py:116 | Task: 13
[BOB] 🟡 FIX: Every warmup segment receives a fresh full deadline, allowing the list to exceed --gate-bound. Track one remaining budget across the ordered warmup list. | File: skills/use-qwen/scripts/eval_harness/attempt.py:156 | Task: 13
[BOB] 🟡 FIX: Vetting commands bypass gate_lock, despite the design requiring every vet check to hold it. Lock qualification checks so concurrent callers cannot overlap them. | File: skills/use-qwen/scripts/eval_harness/attempt.py:154 | Task: 13
[BOB] 🟡 FIX: gate_lock unconditionally removes its marker when OrphanError escapes, although descendants still exist. Preserve the marker on orphan failure; release it after confirmed cleanup or ordinary exceptions without surviving processes. | File: skills/use-qwen/scripts/eval_harness/runner.py:320 | Task: 6
[BOB] 🟡 FIX: Engine rosters allow empty lists, duplicate real-engine IDs, and more than two commands. These produce empty successful rounds, directory collisions, or invalid cmd3 records. Validate the roster before creating run evidence. | File: skills/use-qwen/scripts/eval_harness/attempt.py:184 | Task: 13
[BOB] 🟡 FIX: The positive-bound parser accepts NaN and infinity, defeating finite timeout guarantees. Require finite positive numbers for both bounds. | File: skills/use-qwen/scripts/run_eval_harness.py:17 | Task: 13
[BOB] 🟡 FIX: Spec validation accepts relative repo paths and absolute/traversing anchors; it never checks anchors against writable/oracle membership. Enforce the PRD's absolute-repository and separate, repo-relative read-context contracts after path classification. | File: skills/use-qwen/scripts/eval_harness/spec.py:117 | Task: 3
[BOB] 🟡 FIX: Supplied kind is checked only when writable is explicitly overridden. Compare it with the final classified writable count too, so contradictory declarations cannot silently pass vetting. | File: skills/use-qwen/scripts/eval_harness/spec.py:141 | Task: 3
[BOB] 🟡 FIX: run.json records only pi and claude versions, omitting the required vendored Ivan and dispatch-reference versions. Merge the sealed reference versions into the run's versions map. | File: skills/use-qwen/scripts/eval_harness/attempt.py:286 | Task: 13
[BOB] 🟡 FIX: With no explicit usage-limit command, detection immediately becomes unchecked even when the required autopilot checker is installed. Implement the documented fallback while retaining unchecked when no checker resolves. | File: skills/use-qwen/scripts/eval_harness/engines.py:153 | Task: 10
[BOB] 🟡 FIX: Git's quoted filenames are treated as literal paths during sealing and snapshotting, breaking non-ASCII or tab-containing names. Read NUL-delimited Git path output and decode actual path bytes. | File: skills/use-qwen/scripts/eval_harness/evidence.py:90 | Task: 11
[BOB] 🟡 FIX: Snapshot decodes patch bytes strictly as UTF-8, so editing a non-UTF-8 text file aborts observation before reset and record publication. Preserve patch bytes losslessly and put index cleanup in finally. | File: skills/use-qwen/scripts/eval_harness/trees.py:240 | Task: 8
[BOB] 🟡 FIX: The timing assertion measures only test_run_eval_harness.py. Review context records approximately 90 seconds for the package suite, exceeding the PRD's 60-second metric. Measure the required suite and reduce repeated expensive fixture work. | File: skills/use-qwen/scripts/test_run_eval_harness.py:799 | Task: general
[BOB] 🟡 FIX: run_gates and its dispatch table have only test callers; production independently orchestrates the same gates in attempt._steps. Remove the unused driver and move its ordering assertions onto the production orchestration path. | File: skills/use-qwen/scripts/eval_harness/gates.py:150 | Task: 12
[BOB] 🟡 FIX: The POSIX hang test duplicates the unskipped cross-platform heartbeat test. Move its additional wall-time assertion into that test and remove the duplicate execution, preserving coverage while shortening the suite. | File: skills/use-qwen/scripts/test_eval_trees.py:386 | Task: 6
[BOB] ⚪ KNOWN: HEAD/status-only PREP_MISMATCH with an empty differing-path list already prevents dispatch. Adding synthetic paths or new diagnostic fields exceeds the fixed record contract; retain the current representation. | File: skills/use-qwen/scripts/eval_harness/trees.py:189 | Task: 8
[BOB] ⚪ KNOWN: Basic-auth forwarding for /props is outside the stated support requirement. A credential-free HTTP 401 diagnostic satisfies the permitted unavailable-metadata behavior. | File: skills/use-qwen/scripts/eval_harness/engines.py:219 | Task: 10
[BOB] ⚪ Cannot statically verify: VERIFY native Windows execution; run uv run pytest skills/use-qwen/scripts -q on native Windows and confirm the child-writer and immediate-parent-exit tests execute without skips. | File: N/A | Task: 7
```

```
R1: fail
R2: fail
R3: pass
R4: fail
R6: pass
R7: fail
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Gemini via the copilot backend (output from the session-1 dispatch at this same HEAD; see the
session note). Generalist review — the diff has no frontend surface and he invented no frontend
findings. He ran `uv run pytest skills/use-qwen/scripts -q` (and `-rs` to read the one skip),
`bash skills/use-sonnet/scripts/test_sonnet_run.sh`, `validate_skill.py` on both skills,
`braid --check` and `git status --short`, and swept for secrets, TODO/debug markers, `print(`
and bare `except` before answering. Two Medium findings, both on `read_text()` without an
explicit encoding; all twelve rules pass.

```
[CARL] 🟡 Missing encoding="utf-8" in spec.json read_text() risks decode errors on Windows | File: skills/use-qwen/scripts/eval_harness/spec.py | Task: 3
[CARL] 🟡 Missing encoding="utf-8" in dispatch-references.json read_text() risks decode errors on Windows | File: skills/use-qwen/scripts/eval_harness/prompts.py | Task: 4
```

```
R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: pass
```

Verdict: 44 findings
Tests: 2655 passed, 0 failed, 6 skipped (reused from last-verification.json at b13912ce29597fe597888bfaf3a495d62f4ea012)

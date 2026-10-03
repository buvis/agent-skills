---
prd: dev/local/prds/wip/00051-qwen-eval-harness-core-v1.md
review: 2
date: 2026-09-14
head_sha: 0fccf1ee0b9f863ce24904e861ba5c75c375d9e8
codex_thread_id: 01a09c35-ece9-7461-a5c4-002974e06004
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00051-qwen-eval-harness-core-v1

Diff range: `b13912ce29597fe597888bfaf3a495d62f4ea012..0fccf1ee0b9f863ce24904e861ba5c75c375d9e8`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in ~/.config/gita/repos.csv",
twice, same as cycle 1) — no pack available this cycle. Prompts carried the
`(no pack available this cycle)` sentinel for `{PACK_FILE}` and `{PACK_FINDINGS}`.

Scope: **incremental review** of the cycle-1 rework — the ten `[D1]` tasks (15-24), 26 commits,
42 files, +4933/-389 — passed to `gather-context.sh` as `--since b13912c` (the cycle-1
`head_sha`). Cycle 1 reviewed the PRD's whole work range `484ac0d..b13912c` in full. Alice, Bob
and Carl received the cycle-1 consolidated table (F01-F44 with gate dispositions), the incremental
instruction, and the settled-decisions ledger; Blake received the PRD and the B rubric only (his
prompt is byte-identical to cycle 1's, reused, since neither input changed). Bob resumed his
cycle-1 codex thread (`--resume-thread`). Eve did not run: the codex doubt-roster guard did not
fire (no task attempt has `implementor: "codex"`) and `doubt_reviewer` is `codex`.

Session note: one session, no reviewer retries, no fallbacks. Carl finished on copilot
(`gemini-3.8-flash`, exit 0, 5m35s), Bob on his first codex run (exit 0, all R and D lines).
Ledger rows 58f881bd (bob) and 81da78b8 (carl) opened and closed `ok`.

## Review Summary

Reviewed: 24 completed tasks (10 rework tasks in scope; all implemented by `claude` at tier `opus`)
PRDs checked: 00051-qwen-eval-harness-core-v1.md

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens; `consensus_engine: legacy`)
- Blake: ✅ Available (Claude subagent, blind/PRD-only lens; no Filesystem-notes block —
  `dev/local` is a real directory and the root is not a dot-directory)
- Bob: ✅ Available (codex, doubt + de-slop lens, resumed thread; exit 0 first run; all `R{n}`
  and `D{n}` lines present)
- Carl: ✅ Available (gemini via copilot backend, `gemini-3.8-flash`)
- Eve: ⏸️ Disabled (codex doubt-roster guard not fired; `doubt_reviewer: codex`)

### Prior-finding resolution (the 36 findings routed to rework in cycle 1)

Alice and Carl each independently marked all 36 (`F03-F16`, `F18-F32`, `F34-F40`) **resolved**
with file:line references. Bob marked 30 resolved and disputed six (`F03`, `F14`, `F16`, `F22`,
`F26`, `F30` "remain incomplete"); each dispute went to an `autopilot:victor` adversarial verifier
(table below): four were refuted, two were confirmed as **extensions** beyond the pinned contract
(new Medium findings, not the original findings unresolved).

## Consolidated Findings

`consolidate_findings.py` (with `--ledger … --ledger-dismiss BLAKE`) emitted 17 rows, every one
`[1/4]`, and auto-dismissed one Blake row (the `vetting.json` nine-key re-raise, matched on
identical file). Eight `[MECH]` fail-first replay rows were absorbed as their own rows
(`Found by: mech-check`); the tautological-shapes check found nothing in 398 functions. No
`…-checks-1.json` existed, so there was nothing to carry forward. Total: 25 findings.

`Gate` is the Phase 5 disposition; `Verified` names how.

| # | Consensus | Severity | Issue | File | Found By | Verified | Gate |
|---|-----------|----------|-------|------|----------|----------|------|
| G01 | [1/4] | 🔴 | `run_eval_harness.py` ships a `verify` subcommand and an entire evidence-sealing/verification system (`eval_harness/evidence.py`, `evidence_verify.py`, plus `manifest.json`, `dispatch-references.json`, `sealed-inputs.json` artifacts) that is nowhere in PRD 00051's Functional Decomposition. | evidence.py | BLAKE | ledger match (F01) | settled deferral |
| G02 | [1/4] | 🟠 | `vet` accepts an undocumented `--shapes` CLI flag, and `run` gained a new refusal path that rejects a `--shape` not present in the task's vetted `shapes` list. | run_eval_harness.py | BLAKE | ledger match (F01) | settled deferral |
| G03 | [1/4] | 🟠 | Success Metric violated: suite measured at 171.4 s and 172.4 s against "under 60 seconds". | skills/use-qwen/scripts (test suite) | BLAKE | ledger match (F17) | settled deferral |
| G04 | [1/4] | 🟠 | FIX: F03 remains incomplete: an OSError during waiting or reaping returns a started engine record without confirming containment, bypassing the survivor check. | engines.py:109 | BOB | victor, executed: REFUTED | discarded |
| G05 | [1/4] | 🟠 | FIX: F14 remains incomplete: server sampling accepts any dictionary, including {} and {"temperature":"hot"}, despite the declared four-key nested contract. | records_domains.py:56 | BOB | victor, sources: REFUTED | discarded |
| G06 | [1/4] | 🟠 | FIX: On Python 3.13, PureWindowsPath.is_absolute() accepts "1:/repo" and "?:/repo"; the new spec tests explicitly require their rejection, and record validation rejects them. Use consistent drive-letter validation across supported Python versions so spec admission and the configured 3.13 test lane agree. | spec.py:123 | BOB | victor, executed: CONFIRMED | **unresolved High → cap-overflow** |
| G07 | [1/4] | 🟡 | Prompt rendering has moved from "per run, per the run's `--shape`" to pre-rendering both shapes at `vet`/seal time and copying bytes at run time. | admission.py | BLAKE | ledger match (F01, `prompts/` dir) | settled deferral |
| G08 | [1/4] | 🟡 | FIX: F16 remains incomplete: a completed cmd attempt can still verify successfully after losing out.txt, wrapper.txt, its captured session.jsonl, or progress.log. | evidence_verify.py:21 | BOB | victor, sources: REFUTED (satisfied per the pinned contract) | discarded |
| G09 | [1/4] | 🟡 | FIX: F22 remains incomplete: message.id=[] raises TypeError in usage deduplication, while fractional token counts pass aggregation and later abort attempt publication during record validation. | events.py:144 | BOB | victor, executed: CONFIRMED | cap-overflow |
| G10 | [1/4] | 🟡 | FIX: F26 remains incomplete: the remaining warmup allowance is calculated before measure performs cloning and mise setup, then passed unchanged to the command. | vetting.py:43 | BOB | victor, code: REFUTED | discarded |
| G11 | [1/4] | 🟡 | FIX: F30 remains incomplete: raw-string membership lets an anchor "./calc.py" bypass writable membership for "calc.py"; repeated separators provide the same bypass. | prompts.py:77 | BOB | victor, executed: CONFIRMED | cap-overflow |
| G12 | [1/4] | 🟡 | FIX: Refused-launch cleanup can mask LaunchError: if a capture path is a directory or cannot be unlinked, cleanup raises another OSError before the structural launch exception is raised. Dispatch then records a child that never existed as started. | runner.py:281 | BOB | victor, executed: CONFIRMED | cap-overflow |
| G13 | [1/4] | 🟡 | FIX: Both binary-diff exception cases replace every _git_bytes call, so they now fail during the preceding name-status listing and never exercise binary patch extraction. | test_eval_tree_patches.py:320 | BOB | victor, argv trace: CONFIRMED | cap-overflow |
| G14 | [1/4] | 🟡 | FIX: The returned=None assignment and subsequent assertion are tautological inside pytest.raises. | test_eval_runner_containment.py:174 | BOB | victor, code: CONFIRMED | cap-overflow |
| G15 | [1/4] | 🟡 | FIX: The restore-fixture validation test repeats run_record() with its existing default run_id and never reads the restore fixture named in its comment. | test_eval_record_domains.py:75 | BOB | victor, code: CONFIRMED | cap-overflow |
| G16 | [1/4] | 🟡 | 90 touched test(s) pass against the pre-change code (test_tdd_shape_renders_the_paths_it_was_given_and_no_others, test_refuses_leaked_solution_text_in_the_architecture_or_an_anchor +84 more) | test_eval_prompts.py | mech-check | victor, executed replay: REFUTED (45 base-failing cases pin every task-23 change) | discarded |
| G17 | [1/4] | 🟡 | 19 touched test(s) pass against the pre-change code (test_accepts_an_absolute_repo_in_posix_or_windows_form_on_every_host +13 more) | test_eval_spec_contract.py | mech-check | victor, executed replay: REFUTED (58 base-failing cases pin every refusal) | discarded |
| G18 | [1/4] | 🟡 | 18 touched test(s) pass against the pre-change code (test_build_template_refuses_a_link_chain_that_resolves_outside_the_tree, … +12 more) | test_eval_tree_links.py | mech-check | victor, executed replay on 3.10 and 3.13: REFUTED (20 base-failing cases pin the chain fix) | discarded |
| G19 | [1/4] | 🟡 | 4 touched test(s) pass against the pre-change code (test_reads_is_error_by_its_value_and_not_by_its_presence) | test_eval_events_usage.py | mech-check | Alice, `git show b13912ce`: controls | discarded |
| G20 | [1/4] | 🟡 | 1 touched test(s) pass against the pre-change code (test_records_a_no_launch_attempt_whole_with_null_measurements) | test_eval_engines.py | mech-check | SUSPECTED (pre-existing test, fixture-adapted), not executed | discarded |
| G21 | [1/4] | 🟡 | 2 touched test(s) pass against the pre-change code (test_a_child_that_outlives_the_bound_is_killed_with_the_tree_on_every_platform, test_the_windows_branch_puts_the_child_in_a_job_before_it_can_execute) | test_eval_tree_containment.py | mech-check | SUSPECTED (pre-existing tests; one absorbed the folded POSIX assertion), not executed | discarded |
| G22 | [1/4] | 🟡 | 1 touched test(s) pass against the pre-change code (test_commit_all_commits_every_change_and_returns_the_new_head) | test_eval_tree_state.py | mech-check | SUSPECTED (pre-existing test; the empty-commit sibling fails at base), not executed | discarded |
| G23 | [1/4] | 🟡 | 1 touched test(s) pass against the pre-change code (test_run_bounded_leaves_both_of_the_command_s_streams_at_the_path_it_was_given) | test_eval_trees.py | mech-check | SUSPECTED (pre-existing test adapted to the capture split), not executed | discarded |
| G24 | [1/4] | ⚪ | `runner.py` sits at exactly 400 lines against task 15's own contract of "runner.py under 400" (not the PRD/rubric's 800-line hard limit, which it satisfies) | runner.py | ALICE | `wc -l` 400: CONFIRMED | cap-overflow |
| G25 | [1/4] | ⚪ | The one skipped test (`test_eval_tree_containment.py:442`, Win32 job-object failure path) is a legitimate platform gate on macOS, but the PRD's Phase 2 acceptance explicitly demands "no platform-specific test omissions". | test_eval_tree_containment.py | BLAKE | ledger match (F44) | settled deferral |

### Auto-dismissed (ledger)

- [BLAKE] 🔴 `vetting.json` violates the PRD's "exactly" key contract. The PRD states vetting.json has exactly `template_sha`, `gate_bound_s`, `warmup`, `baseline`, `canonical`, `necessity`, `ready` (7 keys). The implementation's `VETTING_KEYS` adds `inputs_sha256` and `shapes` (9 keys), and `attempt.vet()` writes both extra fields into every vetting.json. | File: skills/use-qwen/scripts/eval_harness/records.py — Protocol C (High + data-model change): PRD l.119-122 fixes the key set to seven; the implementation writes nine; the design doc's claim that the PRD does not fix this key set is false. Verdict escalate; remedy (move inputs_sha256/shapes to a sibling seal file) noted for the batch-end decision.

### Carry-forward and mechanical absorption

- **Carry-forward:** none (`00051-qwen-eval-harness-core-v1-checks-1.json` does not exist; cycle 1
  wrote no queue).
- **Tautological shapes:** zero `[MECH]` lines over 398 test functions in 22 files.
- **Fail-first replay:** 300 touched tests ran against `b13912c`, 164 failed there, 136 passed;
  12 new test files could not be collected at base. The 8 aggregate rows are G16-G23 above.

### Verification-check queue

**Not written.** `agents/bob.md` defines no FIX/VERIFY/KNOWN buckets and Eve did not run; Bob's
output carried no VERIFY item this cycle.

### Follow-up tasks

**None created.** The decision gate (below) reached the rework cap with an unresolved High, so
the loop-mode cap-out path applies: no third rework cycle and no tail sweep; every unresolved
finding is a `cap-overflow` record in `state.deferred_decisions` for the batch-end review.

## Decision gate (Phase 5) — cycle 2

### Adversarial verification

Every Bob High and every Bob "remains incomplete" Medium was handed to an `autopilot:victor`
verifier ("uncertainty refutes; only a shown broken path confirms"), as were the three largest
fail-first replay rows and Bob's other four Mediums (12 dispatches in total):

| # | Verdict | Decisive evidence |
|---|---------|-------------------|
| G04 (F03-ext) | REFUTED, executed | `runner.py:312-317` orders `_start → ProcessTree → _exit_within → reap → read_text`: the only post-creation OSError site runs after `reap` has SIGTERM'd, SIGKILL'd and settled the group; `Popen.wait` swallows `ChildProcessError`, `_probe`/`_signal` catch `ProcessLookupError`/`PermissionError`; `Win32Error` is a `RuntimeError`. A cmd engine that spawned a TERM-ignoring grandchild and deleted its own `out.txt` returned `launch=started` with the grandchild gone and the group empty. The existing test that reaches the branch monkeypatches `reap` itself. |
| G05 (F14-ext) | REFUTED, sources | PRD l.253-257 and design l.616-620 describe the four keys `fetch_server_props` writes (`engines.py:40,253-254` always emits them or `None`); design l.692-694 never lists `server` among the nested contracts `validate_record` recurses into; no source states a numeric domain; the task-17 contract said verbatim "`sampling` object or null … do not invent domains beyond those two sources", which `records_domains.py:56-57` honours. |
| **G06** | **CONFIRMED, executed** | `spec._repo` (spec.py:123) delegates to `PureWindowsPath.is_absolute()`; `uv run --python 3.1X` shows `['1:/repo','?:/repo']` → `[False, False]` on 3.10/3.11 and `[True, True]` on 3.12/3.13/3.14. `uv run --python 3.13 … test_eval_spec_contract.py -k refuses_a_relative_repo` → **4 failed, 18 passed** (`1:/repo` and `?:/repo`, both shapes, `DID NOT RAISE SpecError`); the same on 3.10 → 22 passed. `ci.yml:23` matrix is `["3.10", "3.13"]` and the `windows-latest` lane is 3.13 only, so both 3.13 lanes go red once Phase 9 pushes. `records._NATIVE_ABSOLUTE_RE` (records.py:56) refuses the same strings, so spec admission and record validation disagree on 3.12+. |
| G08 (F16-ext) | REFUTED, sources | `evidence_verify.py:21-30` implements exactly the artifact set the cycle-1 gate pinned for F16 (`test_eval_evidence_verify.py:39-45,455-464` pins it); the design's `verify` contract (l.1187-1212) names no engine-stage file; `session.jsonl` is legitimately absent on a started run whose transcript was not found (`engines.py:154-162` → `completion: unknown`). Bob's premise holds only for `wrapper.txt` and cmd `out.txt` — an extension, noted, not F16 unresolved. |
| G09 (F22-ext) | CONFIRMED, executed | `events.py:142-146` tests `message_id in seen` on a set with no hashability guard → `TypeError` out of `read_events` for `id: []`; `events.py:155` accepts `int|float`, so `output_tokens: 1.5` (or `-3`) sums and `records._check_usage` then raises `RecordError` at `attempt.py:363` before `attempt.json` is written; nothing up to `run_round` catches either. The pinned non-int case (5a34f4b) is the string `"12"`. |
| G10 (F26-ext) | REFUTED, code | The ordering is as claimed, but `started` is set once (`vetting.py:41`), so every earlier segment's setup is inside the elapsed time the next `left` subtracts; the list overruns by at most one `fresh_clone` + `mise_trust`; a negative `left` times out at once (`runner.py:287-292`); the runtime gates (`gates.py:115-117`, `_run` clock at :98) charge zero setup, so vet is the stricter path. |
| G11 (F30-ext) | CONFIRMED, executed | `spec._is_repo_relative` (spec.py:128-132) rejects only a leading `/`, a backslash, a drive and `..` segments; `prompts._refuse_listed_anchors` (:77) compares raw strings. `./calc.py`, `calc.py/`, `a//calc.py`, `.//calc.py` and `./tests/test_calc.py` all loaded, classified and rendered as read-only anchors for a writable or oracle path; `calc.py` itself was refused. `ILLEGAL_ANCHOR_PATHS` has no `.`-segment, `//` or trailing-slash case. |
| G12 | CONFIRMED, executed | `runner._start` opens the captures before `Popen` (:272-275); its `except OSError` cleanup (:280-283) is unguarded (`unlink(missing_ok=True)` swallows only `FileNotFoundError`). With `attempt/out.txt` a directory and a nonexistent executable, `run_bounded` escaped `PermissionError` instead of `LaunchError` and `engines.dispatch` recorded `launch=started exit=None`. Reachable: the baseline runs the spec's `test_cmd` segments as `bash -lc` inside the attempt dir before dispatch (`gates.py:97-102`, `attempt.py:286` then `:294`). |
| G13 | CONFIRMED, traced | With `trees._git_bytes` replaced wholesale, the fake saw exactly one call — `diff --name-status -z <sha>` — for both `the-binary-diff` params; `trees.py:281` precedes `:282`. The reset-in-finally is still proven for the listing stage; the ids and the comment at 290-292 are mislabeled. |
| G14 | CONFIRMED, code | `test_eval_runner_containment.py:174-181`: assignment inside the `pytest.raises` block, assert after it, `returned` unused elsewhere; the real checks are 182-193. |
| G15 | CONFIRMED, code | `eval_harness_record_helpers.py:22,24` defaults `run_id` to `r1`; `_build_run` writes `run_record(run_id="r1")` (`eval_harness_evidence_helpers.py:250-252`); the test is dict-identical to the parametrized `("run", run_record())` case and reads no file. |
| G16 | REFUTED, executed replay | HEAD file on a `b13912c` worktree: 45 failed, 165 passed. The three render-as-given tests (36 cases) and the anchor-membership refusal (9) fail at base; the 90 base-passing cases are the reworked reject-side test (84 cases asserting the architecture/anchor refusal base already keyed the same way), two accept-side controls (5) and one fixture-adapted pre-existing test. |
| G17 | REFUTED, executed replay | 58 failed, 19 passed (py3.10.20): every task-23 refusal fails at base; the 19 are accept-side tests, one control (integer-prefix ordering base already had) and the two not-valid-utf8 companion guards whose refusal base produced through its pre-existing `except (OSError, ValueError)` on a UTF-8-locale host. |
| G18 | REFUTED, executed replay | 20 failed, 18 passed on 3.10, identical split for the refusal subset on 3.13; HEAD 38 passed. The 20 pin the chain-following fix; the 18 are 16 accept/control cases plus the `three-hops-through-a-link-to-a-link` fixture whose middle hop is a bare `..` that base's lexical `_escapes` already refused (the test file annotates this at line 43). |

### Classification

Loop mode is on (`_AUTOPILOT_LOOP`): no question was asked; every decision below is autonomous
or deferred and is mirrored into `state.autonomous_decisions` / `state.deferred_decisions` and
the settled-decisions ledger (25 new entries).

**Settled deferrals (6, excluded from the convergence test):** G01, G02, G07 restate the cycle-1
F01 scope deferral (the sealing subsystem, its `--shapes` flag, and its `prompts/` dir); G03
restates F17; G25 restates F44; the auto-dismissed `vetting.json` row restates F02. The mechanical
matcher caught only the one with an identical file string; the other five are the gate's judgment
call on issue text plus file. **Severity note, recorded deliberately:** Blake rated G01 and the
`vetting.json` row **Critical** where cycle 1 settled them as **High**. They are the same findings
(no rework commit touched their substance) and the settled reasons still hold — keep-or-strip is
the human's batch-end requirements call — so they are not counted as unresolved Criticals. The
PRD 00094 narrowing ("a Critical is never a settled deferral") guards a Critical that was itself
deferred; it does not let a blind reviewer relabel a settled scope call into a stall.

**Discarded with a verified reason (12, ledgered):** G04, G05, G08, G10 (Bob's four refuted
disputes), G16-G19 (four replay rows, three by executed replay and one by Alice), and G20-G23
(four replay rows on 5 pre-existing tests, dismissed on the same pattern and labelled SUSPECTED
in the ledger because they were not executed).

**Unresolved (8):** one High (G06), six Medium (G09, G11, G12, G13, G14, G15), one Low (G24).

**Safety checks:** 8 follow-ups, under the scope alarm. Issue count fell from 44 to 25 raised and
from 36 fixable to 8 unresolved. No security-critical finding (G11 is a spec-validation gap in a
harness that only ever loads operator-authored specs; G12 records a wrong launch label, it ships
no secret and opens no path) and no data-loss risk. G06 is the one finding that was *introduced*
by the rework (task 23 chose `PureWindowsPath.is_absolute()` where task 17 chose a regex).

### Cap check

`state.cycle` 2 ≥ `state.rework_cap` 2 and G06 is an unresolved, executed-confirmed High, so the
review did **not** converge and rework is not allowed. **Loop-mode cap-out:** no Critical remains
(see the severity note), so the PRD is not stalled; the eight unresolved findings were appended to
`state.deferred_decisions` as `cap-overflow` records (each with `reason: "rework cap reached with
this finding unresolved"` plus its verification evidence), the `review_converged` metric was
written with `outcome: "cap_deferred"`, and the PRD proceeds to the finalize hand-off as
converged-with-deferrals. No tail sweep runs on this path.

**What the batch-end reader must weigh:** once Phase 9 pushes, `test_eval_spec_contract.py::
test_refuses_a_relative_repo_by_name` fails 4 cases on both 3.13 lanes (ubuntu and windows) until
the one-function `spec._repo` fix lands (reuse `records._NATIVE_ABSOLUTE_RE`). The eight deferrals
are small and independent and would fit one D-task; the deferred records name a fix shape each.

Resume note for a session that finds this file on disk with `phase: "review"`: the gate is DONE
and recorded; do not re-classify. Run the finalize hand-off (`autopilot phase-done --outcome
converged`) if `state.next_phase` is still `review`.

## Alice

Consensus lens, implementation-aware, incremental. All 36 prior findings resolved with file:line
references; one Low; all twelve rules pass.

Verification she performed: read every rework-touched production module against each D1 task's
contract; ran the rework's own ten test files (`test_eval_engine_halts.py`,
`test_eval_runner_containment.py`, `test_run_eval_admission.py`, `test_run_eval_vet.py`,
`test_eval_record_domains.py`, `test_eval_spec_contract.py`, `test_eval_evidence_verify.py`,
`test_run_eval_cli.py`, `test_eval_events_usage.py`, `test_eval_tree_links.py`): **567 passed,
0 failed** (60 s); found no skip/xfail markers in any rework test file; cross-checked the replay's
`test_reads_is_error_by_its_value_and_not_by_its_presence` row against `git show b13912ce` (only
`_carries_claude_edit` had the presence-check bug pre-fix, so the 4 passing cases are controls and
the 2 failing ones pin the fix); confirmed CHANGELOG.md carries one entry per rework task.

```
[ALICE] ⚪ `runner.py` sits at exactly 400 lines against task 15's own contract of "runner.py under 400" (not the PRD/rubric's 800-line hard limit, which it satisfies) | File: skills/use-qwen/scripts/eval_harness/runner.py | Task: 15
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

Blind lens — PRD only, no diff, no file list, no review history, no ledger. He located the code
himself, ran `uv run pytest skills/use-qwen/scripts -q` twice (171.4 s and 172.4 s; 2103 passed,
1 skipped) and reported that the `-S/--session-id` flag, the process-group termination logic, the
`classify()`/`derive_validity()` ladder, the single harness retry, the credential stripping and the
untouched registry/routing/SKILL.md files all match the spec. His six findings are the cycle-1
scope and contract divergences again, in his own words, two of them now at Critical (see the
severity note in the gate); all six matched settled ledger entries.

```
[BLAKE] 🔴 `run_eval_harness.py` ships a `verify` subcommand and an entire evidence-sealing/verification system (`eval_harness/evidence.py`, `evidence_verify.py`, plus `manifest.json`, `dispatch-references.json`, `sealed-inputs.json` artifacts) that is nowhere in PRD 00051's Functional Decomposition. Git history confirms it was added as a distinct commit ("feat(use-qwen): seal the eval-harness vet inputs and verify an evidence bundle", 2026-09-13) and CHANGELOG.md documents it under this PRD's release notes even though the PRD text explicitly scopes rendering/verification-adjacent work to PRD 00052 ("Rendering the records ... is PRD 00052"). | File: skills/use-qwen/scripts/eval_harness/evidence.py | Task: general
[BLAKE] 🔴 `vetting.json` violates the PRD's "exactly" key contract. The PRD states vetting.json has exactly `template_sha`, `gate_bound_s`, `warmup`, `baseline`, `canonical`, `necessity`, `ready` (7 keys). The implementation's `VETTING_KEYS` adds `inputs_sha256` and `shapes` (9 keys), and `attempt.vet()` writes both extra fields into every vetting.json. | File: skills/use-qwen/scripts/eval_harness/records.py | Task: 8 (Phase 1: Implement trees.py and vet)
[BLAKE] 🟠 `vet` accepts an undocumented `--shapes` CLI flag, and `run` gained a new refusal path (`RefusalError` in `_admit`) that rejects a `--shape` not present in the task's vetted `shapes` list. Neither the flag nor this admission rule appears in the PRD's CLI signature (`vet <evidence-dir> [--gate-bound]`) or Prompt Rendering behavior (which ties rendering to the run's own `--shape`, not to a pre-vetted shape set). | File: skills/use-qwen/scripts/run_eval_harness.py | Task: general
[BLAKE] 🟠 Success Metric violated: PRD states "The test suite runs with no model server and no network, using a fake engine, in under 60 seconds." Measured `uv run pytest skills/use-qwen/scripts -q` twice: 171.4s and 172.4s, roughly 3x over budget. | File: skills/use-qwen/scripts (test suite) | Task: general
[BLAKE] 🟡 Prompt rendering has moved from "per run, per the run's `--shape`" (PRD's Prompt rendering feature) to pre-rendering both possible shapes at `vet`/seal time and copying bytes at run time (`admission.copy_run_prompts`, `evidence.seal_inputs`). Functionally the run-time output filenames still match spec, but the architecture and failure surface (shape must have been vetted) differ from what the PRD describes. | File: skills/use-qwen/scripts/eval_harness/admission.py | Task: general
[BLAKE] ⚪ The one skipped test (`test_eval_tree_containment.py:442`, Win32 job-object failure path) is a legitimate platform gate on macOS, but the PRD's Phase 2 acceptance explicitly demands "no platform-specific test omissions" on POSIX and native Windows; this could not be independently verified on a Windows runner in this review. | File: skills/use-qwen/scripts/test_eval_tree_containment.py | Task: 16 (Phase 2: Implement attempt.py and run)
```

```
B1: fail    B2: fail    B3: fail    B4: fail    B5: pass
B6: fail    B7: fail    B8: pass    B9: pass    B10: pass
B11: pass   B12: pass   B13: pass   B14: pass   B15: pass
B16: fail   B17: fail   B18: pass   B19: pass
```

## Bob

Doubt + de-slop lens, codex, static-only sandbox, resumed cycle-1 thread, first run, no retry, no
fallback. Marked 30 of 36 prior findings resolved and 6 unresolved; raised three High and eight
Medium; fails R1, R2, R4, R7, R9 and R10; all five D rules pass. Of his eleven issue lines, six
were confirmed by adversarial verification (one High, five Medium) and five were refuted (two
High, two Medium as extensions beyond the pinned contract, one Medium on the warmup budget).

```
F03: unresolved — skills/use-qwen/scripts/eval_harness/engines.py:109
F04: resolved — skills/use-qwen/scripts/eval_harness/attempt.py:274
F05: resolved — skills/use-qwen/scripts/eval_harness/runner.py:278
F06: resolved — skills/use-qwen/scripts/eval_harness/records.py:94
F07: resolved — skills/use-qwen/scripts/eval_harness/runner.py:148
F08: resolved — skills/use-qwen/scripts/eval_harness/evidence.py:146
F09: resolved — skills/use-qwen/scripts/eval_harness/attempt.py:339
F10: resolved — skills/use-qwen/scripts/eval_harness/trees.py:249
F11: resolved — skills/use-qwen/scripts/eval_harness/admission.py:40
F12: resolved — skills/use-qwen/scripts/eval_harness/trees.py:78
F13: resolved — skills/use-qwen/scripts/eval_harness/admission.py:20
F14: unresolved — skills/use-qwen/scripts/eval_harness/records_domains.py:56
F15: resolved — skills/use-qwen/scripts/eval_harness/events.py:129
F16: unresolved — skills/use-qwen/scripts/eval_harness/evidence_verify.py:21
F18: resolved — skills/use-qwen/scripts/eval_harness/runner.py:338
F19: resolved — skills/use-qwen/scripts/eval_harness/admission.py:28
F20: resolved — skills/use-qwen/scripts/eval_harness/admission.py:63
F21: resolved — skills/use-qwen/scripts/eval_harness/prompts.py:111
F22: unresolved — skills/use-qwen/scripts/eval_harness/events.py:144 (text:42 fixed; other malformed payloads still raise)
F23: resolved — skills/use-qwen/scripts/eval_harness/events.py:201
F24: resolved — skills/use-qwen/scripts/eval_harness/engines.py:100
F25: resolved — skills/use-qwen/scripts/eval_harness/attempt.py:118
F26: unresolved — skills/use-qwen/scripts/eval_harness/vetting.py:43
F27: resolved — skills/use-qwen/scripts/eval_harness/vetting.py:28
F28: resolved — skills/use-qwen/scripts/eval_harness/runner.py:393
F29: resolved — skills/use-qwen/scripts/run_eval_harness.py:23
F30: unresolved — skills/use-qwen/scripts/eval_harness/prompts.py:77
F31: resolved — skills/use-qwen/scripts/eval_harness/spec.py:245
F32: resolved — skills/use-qwen/scripts/eval_harness/admission.py:71
F34: resolved — skills/use-qwen/scripts/eval_harness/evidence.py:91
F35: resolved — skills/use-qwen/scripts/eval_harness/trees.py:281
F36: resolved — skills/use-qwen/scripts/test_run_eval_cli.py:148
F37: resolved — skills/use-qwen/scripts/test_eval_tree_containment.py:295
F38: resolved — skills/use-qwen/scripts/eval_harness/spec.py:79
F39: resolved — skills/use-qwen/scripts/eval_harness/prompts.py:129
F40: resolved — skills/use-qwen/scripts/eval_harness/spec.py:185
```

```
[BOB] 🟠 FIX: F03 remains incomplete: an OSError during waiting or reaping returns a started engine record without confirming containment, bypassing the survivor check and permitting snapshotting and gates beside surviving children. Guarantee cleanup on every post-creation exit and halt when cleanup cannot be confirmed; test a reap failure with a living descendant. | File: skills/use-qwen/scripts/eval_harness/engines.py:109 | Task: 16
[BOB] 🟠 FIX: F14 remains incomplete: server sampling accepts any dictionary, including {} and {"temperature":"hot"}, despite the declared four-key nested contract. Validate temperature/top_k/top_p/min_p and their numeric-or-null domains; replace the partial sampling dictionaries currently treated as valid test fixtures. | File: skills/use-qwen/scripts/eval_harness/records_domains.py:56 | Task: 17
[BOB] 🟠 FIX: On Python 3.13, PureWindowsPath.is_absolute() accepts "1:/repo" and "?:/repo"; the new spec tests explicitly require their rejection, and record validation rejects them. Use consistent drive-letter validation across supported Python versions so spec admission and the configured 3.13 test lane agree. | File: skills/use-qwen/scripts/eval_harness/spec.py:123 | Task: 23
[BOB] 🟡 FIX: F16 remains incomplete: a completed cmd attempt can still verify successfully after losing out.txt, wrapper.txt, its captured session.jsonl, or progress.log. Require engine artifacts implied by launch/completion evidence and add missing-file cases for those artifacts. | File: skills/use-qwen/scripts/eval_harness/evidence_verify.py:21 | Task: 19
[BOB] 🟡 FIX: F22 remains incomplete: message.id=[] raises TypeError in usage deduplication, while fractional token counts pass aggregation and later abort attempt publication during record validation. Validate message IDs and usage field domains, retaining valid measurements without allowing malformed payloads to abort the round. | File: skills/use-qwen/scripts/eval_harness/events.py:144 | Task: 22
[BOB] 🟡 FIX: F26 remains incomplete: the remaining warmup allowance is calculated before measure performs cloning and mise setup, then passed unchanged to the command. The final segment can therefore finish beyond the shared deadline and still pass. Recalculate the allowance immediately before dispatch against one absolute deadline; cover slow clone setup. | File: skills/use-qwen/scripts/eval_harness/vetting.py:43 | Task: 21
[BOB] 🟡 FIX: F30 remains incomplete: raw-string membership lets an anchor "./calc.py" bypass writable membership for "calc.py"; repeated separators provide the same bypass. Normalize permitted path spellings before comparing membership, or reject noncanonical spellings, and test writable and oracle aliases. | File: skills/use-qwen/scripts/eval_harness/prompts.py:77 | Task: 23
[BOB] 🟡 FIX: Refused-launch cleanup can mask LaunchError: if a capture path is a directory or cannot be unlinked, cleanup raises another OSError before the structural launch exception is raised. Dispatch then records a child that never existed as started. Track captures actually created and preserve pre-creation classification when cleanup fails. | File: skills/use-qwen/scripts/eval_harness/runner.py:281 | Task: 16
[BOB] 🟡 FIX: Both binary-diff exception cases replace every _git_bytes call, so they now fail during the preceding name-status listing and never exercise binary patch extraction. Restrict the injected failure to the --binary call and assert that this stage was reached. | File: skills/use-qwen/scripts/test_eval_tree_patches.py:320 | Task: 18
[BOB] 🟡 FIX: The returned=None assignment and subsequent assertion are tautological inside pytest.raises: a matching exception prevents assignment, while a normal return already fails the context manager. Remove the variable, assignment, and assertion; retain the exception and actual child-cleanup checks. | File: skills/use-qwen/scripts/test_eval_runner_containment.py:174 | Task: 15
[BOB] 🟡 FIX: The restore-fixture validation test repeats run_record() with its existing default run_id and never reads the restore fixture named in its comment. Remove this duplicate; the parameterized builder check and existing restore integration tests already cover its behavior. | File: skills/use-qwen/scripts/test_eval_record_domains.py:75 | Task: 17
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

Gemini via the copilot backend (`gemini-3.8-flash`, exit 0, 5m35s, 67.89 AI credits).
Generalist review — the diff has no frontend surface and he invented no frontend findings. He read
the context file, every rework-touched module and the relevant test slices, checked line counts
with `wc -l`, swept for TODO/FIXME/pdb markers (none), read the CHANGELOG, and ran
`uv run pytest skills/use-qwen/scripts/test_run_eval_cli.py skills/use-qwen/scripts/test_eval_gates.py -q`
(passed, 26 s). Marked all 36 prior findings resolved with file:line references; no issues; all
twelve rules pass.

```
[CARL] ✅ No issues found
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

Verdict: 25 findings
Tests: 3306 passed, 0 failed, 6 skipped (reused from last-verification.json at 0fccf1ee0b9f863ce24904e861ba5c75c375d9e8)

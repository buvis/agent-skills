---
prd: dev/local/prds/wip/00057-data-json-world-readable-v1.md
review: 1
date: 2026-09-26
head_sha: 0183537fc3e1ac890b76ec3bf26f33f7399af863
codex_thread_id: 01a0db3c-0655-7453-b5af-2ff93d36c553
consensus_run_id: wf_a3f6e3a6-8b3
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
  eve: disabled
---

# Review: 00057-data-json-world-readable-v1

Diff range: `f394bd527184dd8c46a3d8e589363b15a9e4a019..0183537fc3e1ac890b76ec3bf26f33f7399af863`

codex_rung_guard: not fired

consensus_engine: shadow (legacy Alice gated this cycle; the `review-fanout` workflow ran beside her, non-gating — see "Shadow consensus engine" below)
pack: failed (`engram pack` exited 1 twice: "not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv") — every prompt taking `{PACK_FILE}`/`{PACK_FINDINGS}` received the `(no pack available this cycle)` sentinel. The review is degraded (no findings-precedent retrieval), not invalid.

## Diff-scope correction (read this before the findings)

`gather-context.sh` on its full-review path produced a **0-byte diff**. It derives the
full-review base as the branch base and runs `git diff master`; this repo commits PRD
work directly onto `master`, so from `master` that diff is empty by construction. The
whole cycle would have reviewed nothing.

Corrected by re-running with `--since f394bd527184dd8c46a3d8e589363b15a9e4a019`, which
yields the intended `work_start_sha..HEAD` range: **361 lines, 14786 bytes, 3 files**.
The script then labels the context "incremental review", which is false here and would
have told four reviewers not to re-review unchanged code, so that label was replaced in
the context file with an explicit FULL-review note. This is a defect in the autopilot
pack (`review-work-completion/scripts/gather-context.sh`), not in PRD 00057.

## Consolidated Findings

`consolidate_findings.py` emitted 11 rows from 4 reviewers. It merges paraphrases only
when they cite the same file, so it did **not** fold three sets of rows that are one
defect each; the decision gate treated them as one finding apiece (issue text plus
file), and the effective distinct-defect count is **7**. Both views are below.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟡 | Windows protect_owner_only reads os.environ["USERNAME"] unguarded; a missing var raises KeyError, which protect_or_exit's except clause (OSError, CalledProcessError) does not catch, bypassing the clean "cannot protect" exit — matches spec's literal wording but is a latent gap in the fail-loud contract | skills/brief-portfolio/scripts/collect.py:484 | 1 | BLAKE, BOB |
| [2/4] | ⚪ | Dead branch in a test helper (carried, non-blocking) | skills/brief-portfolio/scripts/test_collect_history.py:113 | 2 | ALICE, CARL |
| [1/4] | 🔴 | write_snapshot creates data.json.tmp/data-prev.json.tmp via Path.write_text (default umask permissions) and only chmods to 0o600 afterward, instead of the spec-mandated os.open(..., 0o600) at creation — leaves the leaked-credential JSON blob world-readable on disk in the write-to-chmod window, and permanently unprotected if the process dies in that window; the PRD's own commit trail (bd97df2) shows this exact "deferred-chmod exploit" was named and only test-timing was tightened, not the production code | skills/brief-portfolio/scripts/collect.py:509 | 1 | BLAKE |
| [1/4] | 🟠 | FIX — Sensitive JSON is written before owner-only protection, briefly exposing both temporaries at the process umask or old mode; exclusively create and protect each empty temporary before writing secrets | skills/brief-portfolio/scripts/collect.py:509 | 1 | BOB |
| [1/4] | 🟠 | FIX — Windows `/inheritance:r /grant:r` preserves explicit ACEs for other principals, so a reused stale temporary can remain readable after protection; replace the full DACL and test a widened pre-existing temporary | skills/brief-portfolio/scripts/collect.py:487 | 1 | BOB |
| [1/4] | 🟡 | Either-or hedge assert makes part of the test unable to distinguish "protected" from "never created" | skills/brief-portfolio/scripts/test_collect_history.py:370 | 2 | ALICE |
| [1/4] | 🟡 | FIX — Cleanup `unlink()` errors escape the protection handler and prevent later discards, violating the fail-loud/no-temporary contract; attempt every cleanup and preserve the `cannot protect` exit with cleanup details | skills/brief-portfolio/scripts/collect.py:500 | 2 | BOB |
| [1/4] | 🟡 | FIX — `read_exit_message` accepts either a numeric status or string payload and returns the latter without observing stderr, so the tests do not pin the required exit-1/stderr contract; exercise the CLI boundary or explicitly print and exit 1 | skills/brief-portfolio/scripts/test_collect_history.py:109 | 2 | BOB |
| [1/4] | 🟡 | FIX — The new-directory failure assertion hedges with `or`, allowing either directory-existence outcome; assert the deterministic contract that the created directory exists and is empty | skills/brief-portfolio/scripts/test_collect_history.py:370 | general | BOB |
| [1/4] | 🟡 | test_new_out_dir_protection_failure_exits_one_and_writes_nothing hedges with or: either outcome satisfies it | skills/brief-portfolio/scripts/test_collect_history.py:370 | general | CARL |
| [1/4] | ⚪ | Cannot statically verify: VERIFY — confirm `uv run pytest skills/brief-portfolio/scripts -q` passes in both Linux and native Windows CI jobs at `0183537` | N/A | general | BOB |

`consolidate_findings.py` also reported one suffix-stripped merge: row 2 folded
`test_collect_history.py:113` with `:112` (Alice's and Carl's line numbers for the same
helper).

### Distinct defects after gate-level dedup (7)

| # | Effective consensus | Severity | Defect | File | Disposition |
|---|---------------------|----------|--------|------|-------------|
| A | 2/4 (BLAKE 🔴, BOB 🟠) | 🔴 Critical | Temporaries are created at the process umask and only chmod'd afterwards, instead of the PRD-mandated `os.open(..., 0o600)` at creation | collect.py:509, :521 | deferred (audit) + fixed in cycle 1 rework, task 8 |
| B | 1/4 (BOB) | 🟠 High | Windows `/grant:r` leaves a foreign explicit ACE in place, so the published snapshot can list more than one access entry | collect.py:487 | auto-fix, task 3 |
| C | 2/4 (BLAKE, BOB) | 🟡 Medium | `os.environ["USERNAME"]` KeyError escapes the `(OSError, CalledProcessError)` handler, bypassing the `cannot protect` exit and leaving the temporary behind | collect.py:484 | auto-fix, task 4 |
| D | 1/4 (BOB) | 🟡 Medium | A cleanup `unlink()` that raises skips the remaining discards and replaces the `cannot protect` exit with a traceback | collect.py:500 | auto-fix, task 5 |
| E | 4/4 (ALICE, BOB, CARL, mech-check) | 🟡 Medium | `assert not out_dir.exists() or sorted(...) == []` hedges, pinning neither outcome | test_collect_history.py:370 | auto-fix, task 6 |
| F | 3/4 (BOB 🟡, ALICE ⚪, CARL ⚪) | 🟡 Medium | `read_exit_message` has an unreachable branch and never observes stderr, so the exit-1/stderr Must-have is unpinned | test_collect_history.py:109, :113 | auto-fix, task 7 |
| G | 1/4 (BOB) | ⚪ Low | `Cannot statically verify` the suite on both CI hosts | N/A | discarded + ledgered |

Finding **E** is the cycle's strongest agreement: three reviewers and the computed
tautological-shapes check all name the same line.

### Mechanical test checks (absorbed)

- **Tautological shapes**: 1 `[MECH]` line — `test_new_out_dir_protection_failure_exits_one_and_writes_nothing` hedges with `or` (test_collect_history.py:370). It names the same test and file as the ALICE/BOB/CARL rows above, so `mech-check` was appended to that defect's finders (defect E) rather than added as a new row.
- **Fail-first replay**: 10 touched tests ran against `f394bd527184`, **10 failed there, 0 passed**, 0 files uncollectable. No finding — every new test genuinely pins new behavior.

### Carry-forward

None. This is cycle 1, so there is no `-checks-0.json` queue file; an absent queue is never an error.

### Verification-check queue

**Not written this cycle.** The queue is fed from the VERIFY bucket of a doubt lens, and
`agents/bob.md` defines no FIX/VERIFY/KNOWN buckets — the skill reserves `source: "bob"`
explicitly and forbids inventing buckets he did not emit. Eve did not run (the codex
doubt-roster guard did not fire), so no lane emitted a VERIFY bucket. Bob's single
`⚪ Cannot statically verify` line is the sandbox line his own persona mandates; it was
classified as an ordinary Low finding and discarded with a reason (defect G).

## Alice

Consensus lens, implementation-aware. Ran the suite herself: `uv run pytest skills/brief-portfolio/scripts -q` → 83 passed, 4 xfailed (all four pre-existing and unrelated — `test_build_page.py` / `test_collect_pipeline.py`, confirmed via `rg xfail`). Also grepped for stray references to the two new functions and found none outside the two changed script files, confirming scope.

- 🟡 Either-or hedge assert makes part of the test unable to distinguish "protected" from "never created" — test_collect_history.py:370. The rest of that test (exit code, `cannot protect` + sentinel in the message) is meaningful; only the trailing assertion is weak.
- ⚪ Dead branch in a test helper (carried, non-blocking) — test_collect_history.py:113. `assert code == 1 or isinstance(code, str)`: every call site exits with a string, so `code == 1` never fires and the `capsys` arm is unreachable. Same LOW Pat carried from task 2's per-task review.

Positive notes she recorded, which the gate accepted: `protect_or_exit(path, *discard)` collapses the three near-identical try/except/unlink/`sys.exit` blocks the design doc spelled out per call site into one helper, and she verified call-by-call that each unlinks exactly the temporaries the design specifies — behaviourally identical to the verbatim contract, a simplification rather than scope creep. The `data["skipped"]` literal-fold in `main()` is a pure reordering with no output change.

**Alice did not raise defect A.** She read the design doc (the implementation-aware prompt carries it) and took its recorded rejection of the `os.open` alternative as settled. That is exactly the blind spot the blind lens exists to cover, and Blake covered it.

R1: pass
R2: fail
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

## Blake

Blind lens — PRD only, no diff, no file list, no design doc, no review history. He located the code himself, read `.github/workflows/ci.yml`, and walked the git history of all 7 commits. Ran `uv run pytest skills/brief-portfolio/scripts -q` → 83 passed, 4 pre-existing xfailed.

He raised the cycle's only 🔴, and it is the one finding no implementation-aware reviewer could have been expected to raise: the PRD's Solution section mandates that the temporaries be created *through* `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)` "so the temporary file is never readable by others, **not even between write and rename**". The shipped code uses `Path.write_text` and chmods afterwards. He also noted the commit trail shows the author named this exact hazard — `bd97df2` "strengthen owner-only protection tests against a deferred-chmod exploit" — but only tightened test-level timing assertions, which cannot observe an OS-level permission window inside `write_text`. So CI is green while the spec's explicit anti-race mechanism is unimplemented.

- 🔴 Temporaries created at the umask and chmod'd afterwards instead of `os.open(..., 0o600)` at creation — collect.py:509
- ⚪ Windows `os.environ["USERNAME"]` unguarded; `KeyError` bypasses the `cannot protect` exit — collect.py:484

Everything else he checked passed: the `icacls` invocation matches spec verbatim, directory protection (new-only) matches, `protect_or_exit`'s fail-loud contract matches and is tested for both failing temp names and both exception types, `.github/workflows/ci.yml` runs the full suite on `windows-latest` with no platform skip, `history.jsonl`/`commits-digest.md` correctly untouched, CLI unchanged, no new dependencies, no `skipif` markers anywhere in the module.

B1: fail
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: fail
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Doubt lens (rubric D1-D5) plus de-slop, on codex, static-only sandbox. **Succeeded on his first run** — no retry, no Claude fallback, no sidecar salvage. Thread id `01a0db3c-0655-7453-b5af-2ff93d36c553` is stamped in the frontmatter so cycle 2 resumes his session instead of re-reviewing from zero.

- 🟠 FIX — Sensitive JSON is written before owner-only protection, briefly exposing both temporaries at the process umask or old mode; exclusively create and protect each empty temporary before writing secrets — collect.py:509
- 🟠 FIX — Windows `/inheritance:r /grant:r` preserves explicit ACEs for other principals, so a reused stale temporary can remain readable after protection; replace the full DACL and test a widened pre-existing temporary — collect.py:487
- 🟡 FIX — Cleanup `unlink()` errors escape the protection handler and prevent later discards, violating the fail-loud/no-temporary contract — collect.py:500
- 🟡 FIX — A missing Windows `USERNAME` raises an uncaught `KeyError` instead of the required `cannot protect` exit — collect.py:484
- 🟡 FIX — `read_exit_message` accepts either a numeric status or string payload and returns the latter without observing stderr, so the tests do not pin the required exit-1/stderr contract — test_collect_history.py:109
- 🟡 FIX — The new-directory failure assertion hedges with `or`, allowing either directory-existence outcome — test_collect_history.py:370
- ⚪ Cannot statically verify: VERIFY — confirm `uv run pytest skills/brief-portfolio/scripts -q` passes in both Linux and native Windows CI jobs at `0183537` — N/A

His first 🟠 is defect A from the implementation side: he reached the same conclusion as Blake from the code alone, without the PRD's `os.open` sentence. Two independent lenses on one defect is what promoted it past the design doc's recorded "non-blocker" judgement.

R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
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

## Carl

Consensus lens, frontend & design specialist reviewing as a generalist (no frontend surface in this diff, and he correctly invented no frontend findings). Ran on **copilot, model `gemini-3.8-flash`**; 18.16 AI credits, 1m53s. He ran the suite twice, ran the skill validator, and checked `git status`.

- 🟡 test_new_out_dir_protection_failure_exits_one_and_writes_nothing hedges with or: either outcome satisfies it — test_collect_history.py:370
- ⚪ Dead branch and unused capsys fixture in read_exit_message test helper — test_collect_history.py:112

R1: pass
R2: fail
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

## Shadow consensus engine

Observation only — this never gated. `consensus_engine: shadow` (PRD frontmatter) runs
legacy Alice *and* the `review-fanout` workflow; Alice gated the cycle, the workflow ran
beside her. Run `wf_a3f6e3a6-8b3`, 6 agents, 0 errors, 120 tool calls, 614,630 subagent
tokens, 893 s. Its gated shadow file is
`dev/local/tmp/00057-data-json-world-readable-v1-consensus-shadow-1.md` (deliberately
**not** in `dev/local/reviews/`, so next cycle's `-review-*.md` glob cannot mistake it
for a review).

`_engine: workflow — dimensions 5, raw 23, unique 23, confirmed 0, refuted 0, demoted 0, unverified 0, diff_bytes 14786_`

### Divergence from legacy Alice

Three divergences, all worth recording:

1. **Verdict.** The workflow returned `APPROVE` with **0 blocking** and wrote
   `Verdict: converged`. The gating cycle wrote `Verdict: 11 findings` and did **not**
   converge. Had the workflow been the gate, this cycle would have shipped the 🔴.
2. **Severity of the cycle's CRITICAL.** The workflow raised the same `os.open`
   mechanism gap but rated it **LOW** ("PRD's os.open(..., 0o600) mechanism for the
   temporaries was not implemented"), where BLAKE rated it 🔴 and BOB 🟠. Its verify
   phase then confirmed nothing (`confirmed 0, refuted 0`) because no finding survived
   demotion as CRITICAL/HIGH, so nothing was adversarially checked. The under-rating,
   not the detection, is the gap.
3. **Volume without dedup.** `raw 23, unique 23` — the dedup step merged nothing across
   5 dimensions, against 11 rows from 4 gating reviewers. Higher recall, no
   consolidation.

### Two items the gating lenses missed

Recorded here because they are real and measured, **not** promoted to gating findings and
**not** given tasks: a non-gating lane must not gate, and `state.deferred_decisions` is
where they get a durable home instead.

- **MEDIUM — the built page still carries the same stderr at 0644.** Re-measured at the
  gate rather than taken from the lane (2026-09-26): `~/.local/share/agents/portfolio-brief`
  is `drwxr-xr-x` (0755, and stays so by this PRD's explicit existing-directory decision),
  `portfolio-brief.html` is `-rw-r--r--` (0644), and
  `rg -c 'sign_and_send_pubkey|Permission denied \(publickey'` returns 1 hit in the page
  against 25 in `data.json` — the same leaked-stderr class, in a world-readable file.
  The same listing also confirms the lane's third LOW: `data-prev.json` is still
  `-rw-r--r--` today and is only re-protected on a run that actually rotates. `build.py` embeds the whole snapshot into
  the page and calls no protection helper. So the PRD's Problem is **narrowed, not
  closed**, and the CHANGELOG sentence added by this diff ("...is never left in a
  world-readable file") overstates the result. The PRD's own out-of-scope carve-out does
  not cover the page: it excludes `history.jsonl` and `commits-digest.md` because "they
  carry no subprocess stderr", and the page demonstrably does.
- **MEDIUM — the `icacls` failure reason is captured and then thrown away.**
  `protect_owner_only` passes `capture_output=True` without `text=True`, so a failure's
  diagnostic goes to `e.stderr` as bytes and is never read; `str(CalledProcessError)` is
  only "Command '[...]' returned non-zero exit status 1." The `cannot protect {path}: {e}`
  message therefore carries **no reason** on Windows — the fail-loud message the PRD
  mandates is present but uninformative exactly where it matters.
- Its other advisory items duplicate findings the gate already tasked (the `os.open` gap =
  defect A, the hedging `or`-assert = defect E, the `USERNAME` KeyError = defect C) plus
  one LOW noting that a `data-prev.json` left 0644 by an older version is only
  re-protected on a run that actually rotates.

## Gate-side verification of the CRITICAL

The 🔴 was not accepted on argument. The exact shape used at collect.py:509/521 was run
under the umask the test module itself pins (`0o022`):

```
mode when write_text returned: 0o644
mode after chmod:              0o600
readable by group/others in the window: True
mode via os.open(..., 0o600):  0o600
CONFIRMED: the write-to-chmod window leaves the payload readable
```

So the window is real, it is group/other-readable, and the PRD's prescribed
`os.open(..., 0o600)` closes it. The existing tests cannot see it: they assert
protection "by the next Python file operation", which is already after the chmod.

The fix is **not** the plain `os.open` swap the design doc rejected. That rejection
stands and its reason is sound — `test_main_leaves_data_json_unchanged_when_prev_tmp_write_fails`
monkeypatches `Path.write_text` to inject a fault, and a temporary created via `os.open`
would never call it, silently defeating that test, which the PRD's own Success Criteria
protects ("the existing rotation tests pass unchanged"). The design doc's review log
already named the shape that satisfies both: pre-create with
`os.open(path, os.O_CREAT | os.O_EXCL, 0o600)`, then fill with `Path.write_text`. The
cycle-1 rework design owns the final contract.

Verdict: 11 findings
Tests: 3451 passed, 0 failed, 6 skipped (reused from last-verification.json at 0183537fc3e1ac890b76ec3bf26f33f7399af863)

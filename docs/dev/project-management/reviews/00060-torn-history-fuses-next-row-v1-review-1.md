---
prd: dev/local/prds/wip/00060-torn-history-fuses-next-row-v1.md
review: 1
date: 2026-09-26
head_sha: dc279d39dba54cdcb4ab9dff3264b6258c7f8ed1
codex_thread_id: 01a0dca3-ed83-7e51-8066-c3a0f176fdc4
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00060-torn-history-fuses-next-row-v1

Diff range: `f9ddc095133aac63418e7d0c3792a6b34c25f78b..dc279d39dba54cdcb4ab9dff3264b6258c7f8ed1`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in ~/.config/gita/repos.csv"; retried once, same error). `{PACK_FILE}` and `{PACK_FINDINGS}` were substituted with `(no pack available this cycle)` for every reviewer that takes them. Degraded, not invalid.

Diff-range note: cycle 1 is a **full** review. `gather-context.sh` was invoked with
`--since f9ddc095133aac63418e7d0c3792a6b34c25f78b` (this PRD's `work_start_sha`)
because its default base is `master..HEAD`, and this PRD's work was committed
onto `master` itself, so the default resolved to an **empty diff**. The base was
passed explicitly and the reviewers were told in-prompt that this is a first
full review, not an incremental rework pass.

Carl note: Carl ran successfully this cycle on `backend=copilot model=gemini-3.8-flash`
(exit 0, non-empty output, all 12 verdicts). No batch latch was written.

Consolidation: `consolidate_findings.py` (exit 0, 4 agent pairs). No settled-decisions
ledger exists for this PRD (cycle 1), so the `--ledger`/`--ledger-dismiss` flags
were omitted.

## Consolidated findings (script output, verbatim)

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟡 | `read_text()` loads and decodes the entire growing history and may normalize a final `\r` to `\n`, so it does not implement the literal last-byte contract; inspect the final byte in binary mode instead. | skills/brief-portfolio/scripts/collect.py:587 | 1 | BOB, CARL |
| [1/4] | 🟡 | The test exercises only the torn-tail branch; always prepending a newline to every non-empty history would still pass, leaving the must-have healthy-file behavior unpinned. Extend the test with a second collection and assert exactly three lines, with both appended rows independently decodable. | skills/brief-portfolio/scripts/test_collect_history.py:519 | 1 | BOB |
| [1/4] | 🟡 | The computed test-shape analysis identifies the either-or assertion as a tautological hedge; replace it with `assert list(out_dir.rglob("*")) == []`, which handles both an absent and empty directory directly. | skills/brief-portfolio/scripts/test_collect_history.py:370 | general | BOB |
| [1/4] | 🟡 | test_new_out_dir_protection_failure_exits_one_and_writes_nothing hedges with or: either outcome satisfies it | skills/brief-portfolio/scripts/test_collect_history.py:370 | general | CARL |
| [1/4] | 🟡 | The computed test-shape analysis identifies the either-or assertion as a tautological hedge (mechanical `[MECH]` line from the context's tautological-test-shapes block, absorbed per step 6). | skills/brief-portfolio/scripts/test_collect_history.py:370 | general | mech-check |
| [1/4] | ⚪ | collect.py:587 reads the whole history.jsonl into memory (`hist_file.read_text()`) just to check the last byte; a `seek(-1, os.SEEK_END)` read of 1 byte would avoid loading an unbounded, ever-growing history file. Already flagged as LOW in the build-phase note and judged non-blocking; restating for the record, not escalating. | skills/brief-portfolio/scripts/collect.py | 1 | ALICE |

The script emitted the first four rows and the ⚪ row; the `mech-check` row above
is the step-6 absorption of the context's one `[MECH]` line, which names the same
test file and test as rows 3 and 4.

**Carry-forward:** none. Cycle 1 has no previous `-checks-0.json` queue.

## Decision-gate dedup (three distinct defects)

`consolidate_findings.py` folds paraphrases onto the first-seen wording only when
the `File:` values match, so it left two pairs unmerged. The gate merges them on
issue text plus file:

| Consensus | Severity | Defect | File | Found By |
|-----------|----------|--------|------|----------|
| [3/4] | 🟡 | The tail check reads the whole file in text mode: unbounded memory on a growing history, and universal-newline translation turns a final `\r` into `\n`, so the literal "last byte is not `\n`" contract is not what the code tests. Inspect the final byte in binary mode. | skills/brief-portfolio/scripts/collect.py:587 | ALICE, BOB, CARL |
| [2/4]+mech | 🟡 | `test_new_out_dir_protection_failure_exits_one_and_writes_nothing` hedges with `or`, so either outcome satisfies it. Pre-existing test, untouched by this diff. | skills/brief-portfolio/scripts/test_collect_history.py:370 | BOB, CARL, mech-check |
| [1/4] | 🟡 | Only the torn-tail branch is pinned. A guard that always prepended `\n` to any non-empty history would still pass, leaving the PRD's second must-have ("a healthy file is appended to exactly as today") and the Success Criteria's "subsequent appends add only the new record's newline" unpinned. | skills/brief-portfolio/scripts/test_collect_history.py:519 | BOB |

Rows 1 and 5 of the script table are the same defect at the same line (ALICE cited
the file without a line suffix); rows 3, 4 and the mech row are the same defect at
the same `file:line`. Merging raised two consensus counts; it changed no severity.

**Corroboration that is not a consensus vote.** Blake's lens returned
`✅ No issues found` and passed all 19 `B` rules, but his prose carries two
low-severity observations, one of which independently describes merged defect 3
("no test exercises repair then a second normal append"). He deliberately did not
raise them as issue lines, so they are recorded here and excluded from every
consensus count.

## Alice (consensus lens)

One ⚪ finding, all 12 rubric rules pass.

```
[ALICE] ⚪ collect.py:587 reads the whole history.jsonl into memory (`hist_file.read_text()`) just to check the last byte; a `seek(-1, os.SEEK_END)` read of 1 byte would avoid loading an unbounded, ever-growing history file. Already flagged as LOW in the build-phase note and judged non-blocking; restating for the record, not escalating. | File: skills/brief-portfolio/scripts/collect.py | Task: 1
```

What she verified: the guard matches the PRD spec at `collect.py:586-591`; the new
test matches the acceptance criterion byte-for-byte; the fail-first replay block
shows it fails against the pre-change code; `collect_and_partition` is not scope
creep (pre-refactor `main()` was 54 lines, over the 50-line limit, and the
extraction is behavior-preserving); the CHANGELOG entry sits under
`[Unreleased] / Fixed`; `uv run pytest skills/brief-portfolio/scripts -q` gave
92 passed / 2 xfailed (pre-existing) / 0 failed; `main` is 49 lines and
`collect_and_partition` 7 per the mechanical-facts block; the one `[MECH]`
tautology is a pre-existing test untouched by this diff.

Verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass,
R10 pass, R11 pass, R12 pass, R13 pass.

## Blake (blind lens — PRD only, no diff)

```
[BLAKE] ✅ No issues found | File: N/A | Task: general
```

He located the code himself and confirmed: the guard at `collect.py:586-591`
matches the spec exactly (torn tail gets the separator, healthy files untouched,
no atomic rewrite and no rotation — both declined in the PRD and absent from the
tree); the commit order was test-first (`251f46c`) then fix (`4fedc70`) then a
pure-extraction refactor (`dc279d3`); the CHANGELOG was updated in the fix commit;
the new test at `test_collect_history.py:519-531` matches the acceptance text
precisely; `uv run pytest skills/brief-portfolio/scripts -q` gave 92 passed /
2 xfailed / 0 failed; `build.py`'s line-skip handling (PRD 00059's surface) is
untouched, as expected.

Two prose-level low notes, neither raised as an issue line and neither a spec
violation:

- A narrow TOCTOU gap between `read_text()` and the separate `open("a")` if two
  `collect.py` runs raced on the same `history.jsonl`. The PRD's context is a
  single run recovering from a killed prior run, and atomic rewrite was explicitly
  declined, so this is not a spec gap.
- No test exercises "repair, then a second normal append" (the Success Criteria
  bullet). Correctness follows from the code — the repaired file always ends in
  `\n` — but nothing pins it.

Verdicts: B1-B19 all pass.

## Bob (codex — doubt lens + de-slop, consensus rubric)

Ran on the first dispatch, no retry needed. Three 🟡 findings.

```
[BOB] 🟡 `read_text()` loads and decodes the entire growing history and may normalize a final `\r` to `\n`, so it does not implement the literal last-byte contract; inspect the final byte in binary mode instead. | File: skills/brief-portfolio/scripts/collect.py:587 | Task: 1
[BOB] 🟡 The test exercises only the torn-tail branch; always prepending a newline to every non-empty history would still pass, leaving the must-have healthy-file behavior unpinned. Extend the test with a second collection and assert exactly three lines, with both appended rows independently decodable. | File: skills/brief-portfolio/scripts/test_collect_history.py:519 | Task: 1
[BOB] 🟡 The computed test-shape analysis identifies the either-or assertion as a tautological hedge; replace it with `assert list(out_dir.rglob("*")) == []`, which handles both an absent and empty directory directly. | File: skills/brief-portfolio/scripts/test_collect_history.py:370 | Task: general
```

Consensus verdicts: R1 fail, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass,
R9 fail, R10 pass, R11 pass, R12 pass, R13 pass.

His two `R` failures are the reasons behind his own 🟡 rows, not separate defects:
R1 for the unpinned healthy-file branch, R9 for the `read_text()` divergence from
the PRD's literal last-byte wording. Alice and Carl both passed R9; Carl's single
`R2: fail` is the pre-existing `:370` hedge, which Alice passed on the ground that
the test is untouched by this diff. None of the three disagreements is a CRITICAL
or HIGH, so none blocks convergence.

Doubt buckets:

```
FIX:
- Tail inspection reads and normalizes the whole file — skills/brief-portfolio/scripts/collect.py:587 — seek to and inspect the final byte in binary mode; add a terminal-`\r` regression case.
- Healthy subsequent appends are unpinned — skills/brief-portfolio/scripts/test_collect_history.py:519 — run collection twice after the torn fixture and assert three exact lines with both new rows decoding.
- Either-or assertion is a tautological hedge — skills/brief-portfolio/scripts/test_collect_history.py:370 — replace it with `assert list(out_dir.rglob("*")) == []`.

VERIFY:
- (none)

KNOWN:
- (none)
```

Doubt-rubric verdicts: D1 pass, D2 pass, D3 pass, D4 pass, D5 pass.

**Verification-check queue: not written.** Bob's VERIFY bucket is empty, so this
cycle queued zero checks and no
`dev/local/reviews/00060-torn-history-fuses-next-row-v1-checks-1.json` exists.
Nothing was routed to verification, so nothing was excluded from the tail sweep
on that ground.

## Carl (gemini — frontend & design specialist, generalist here)

`backend=copilot model=gemini-3.8-flash`, exit 0. Two findings. The change has no
frontend surface, and he correctly reviewed it as a generalist rather than
inventing frontend findings.

```
[CARL] 🟡 test_new_out_dir_protection_failure_exits_one_and_writes_nothing hedges with or: either outcome satisfies it | File: skills/brief-portfolio/scripts/test_collect_history.py:370 | Task: general
[CARL] ⚪ read_text() loads entire history file into memory to inspect trailing byte | File: skills/brief-portfolio/scripts/collect.py:587 | Task: 1
```

Verdicts: R1 pass, R2 fail, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass,
R10 pass, R11 pass, R12 pass, R13 pass.

## Outcome

Zero 🔴 CRITICAL and zero 🟠 HIGH findings. Medium and Low never block convergence,
so cycle 1 converges; the three merged 🟡 defects are swept by one `[D1] Tail sweep`
task before the PRD finalizes, not carried into a cycle 2.

Verdict: 5 findings
Tests: 3460 passed, 0 failed, 6 skipped (reused from last-verification.json at dc279d39dba54cdcb4ab9dff3264b6258c7f8ed1)

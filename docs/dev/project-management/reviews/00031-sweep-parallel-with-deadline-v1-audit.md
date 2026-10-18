# Decision Audit Log: 00031-sweep-parallel-with-deadline-v1

PRD: `00031-sweep-parallel-with-deadline-v1.md`
Started: 2026-10-18T12:21:29Z
Completed: 2026-10-18T12:21:29Z
Autonomous: 26  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R1/R11 test_sweep_main.py is 803 lines, over the 800-line limit (3/4 consensus)

**Choice**: auto-fix, swept

**Rationale**: Mechanical file-size fix; move the deadline CLI tests into a sibling module (R11's parametrize suggestion folds into the same task).

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R2 _collect_scan_results rebuilds the deadline key inline instead of reusing _repo_cwd_and_targets

**Choice**: auto-fix, swept

**Rationale**: Design doc names the helper as the key source; one-line mechanical change.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R3 real-clock deadline test has ~0.3s margins and can flake

**Choice**: auto-fix, swept

**Rationale**: Test-only robustness fix.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R4/R18 test_scan_never_silently_drops_a_repo_whose_search_raises is an either-or hedge that passes pre-change

**Choice**: auto-fix, swept

**Rationale**: Assert the single real outcome with pytest.raises so the test pins the new behavior.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R6 existing cap-rejection tests were edited against the task's explicit instruction and pass pre-change

**Choice**: auto-fix, swept

**Rationale**: Revert the tightened assertions to the substring form the design mandated.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R7 PRD success criterion 'two sweep.main runs write byte-identical reports' has no test

**Choice**: auto-fix, swept

**Rationale**: Additive test for a named PRD success criterion.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R9 one-shot repos iterators lose all results (submission exhausts the iterator)

**Choice**: auto-fix, swept

**Rationale**: Latent but real; one-line materialization plus a regression test using iter(repos).

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R12 except FutureTimeoutError can mislabel a worker TimeoutError as a deadline hit

**Choice**: auto-fix, swept

**Rationale**: Cheap disambiguation; latent today because _scan_repo catches Exception.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R13 _positive_int lets a bare ValueError reach argparse ('invalid _parse value')

**Choice**: auto-fix, swept

**Rationale**: The design docstring already specifies the ArgumentTypeError message.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R14 SKILL.md does not document the --deadline default, scope, or the Partial: line

**Choice**: auto-fix, swept

**Rationale**: One documentation line; the PRD's literal wording is met but the skill is unreadable without it.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R5/R10/R16 glean working-tree churn in the review diff

**Choice**: discarded (ledgered)

**Rationale**: Outside this PRD's commit range; pre-existing uncommitted foreign work the session is instructed to leave untouched.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R8 --deadline is not a hard process-exit ceiling

**Choice**: discarded (ledgered)

**Rationale**: The reviewer confirms the scan() return is bounded, which is what the PRD requires.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R15 tests beyond the PRD's named ones

**Choice**: discarded (ledgered)

**Rationale**: Tests-only; the raising reviewer confirms no production scope creep.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: R17 no-Partial-line test passes against pre-change code

**Choice**: discarded (ledgered)

**Rationale**: Negative assertion passes pre-change by construction; cannot be fail-first without inverting its intent.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: Bob's first codex dispatch returned a sandbox refusal with all R verdicts fail

**Choice**: retried once with the inlined prompt

**Rationale**: Retry-policy inlined retry prompt recovered a usable doubt review; the first dispatch row was mistakenly closed --outcome ok and the misclassification is recorded in the review file.

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: `skills/sweep-fix/scripts/test_sweep_main.py` is now 803 lines, over the 800-line limit. The diff added about 100 lines to a file that was about 702. Move the new deadline tests (or an older group) into a sibling test module.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: Replace duplicate deadline rejection tests with pytest.mark.parametrize across 0 and -1 to cut lines under 800

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: `_collect_scan_results` rebuilds the deadline key inline with `repo["cwd"] if isinstance(repo, dict) else repo`. That duplicates `_repo_cwd_and_targets`, which the design says to reuse (key is `_repo_cwd_and_targets(repo)[0]`). Replace it with `str(_repo_cwd_and_targets(repo)[0])`.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: `test_scan_deadline_budget_runs_from_scan_start_not_per_repo` has only about 0.3s of margin between `repo_a` finishing at 0.6s, the deadline at 1.0s and `repo_b` finishing at 1.3s. It runs against the real clock and can flake on a loaded CI runner. Widen the gaps (for example 1.0s, 2.0s and 3.0s) or patch the clock.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: `test_scan_never_silently_drops_a_repo_whose_search_raises` is an either-or hedge. It returns early if `scan()` raises, and only otherwise asserts the repo is in `failed`. It also passes against the pre-change serial loop, so it pins no new behavior. Pick the one outcome the code has (the exception escapes, per the assumptions ledger) and assert it with `pytest.raises`.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: The existing `test_main_rejects_cap_of_zero` and `test_main_rejects_negative_cap` had their assertions edited. The task and design said they must keep passing unmodified, because the old `"cap"` substring check already covered them. The tightened assertion passes against the pre-change code (the old hardcoded message was already `--cap must be a positive integer`), so the fail-first replay flags both. Revert the edits, or keep them and say so as a deliberate scope addition.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: Success criterion "two `sweep.main` runs over the same fixture registry, each with explicit `--out`, write byte-identical reports" has no test. Ordering is covered only at `scan()` level.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: One-shot `repos` iterators silently lose all results: submission exhausts the iterator before collection iterates it again.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: `except FutureTimeoutError` in `_collect_scan_results` treats any `TimeoutError` as a deadline hit. On Python 3.11 and later this is the builtin `TimeoutError`. If a worker ever re-raised one through `future.result()`, it would be mislabelled as `DEADLINE_REASON`. `_scan_repo` catches `Exception` today, so this is latent. Raising the timeout check apart from the `result()` call would remove the ambiguity.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: With the `_positive_int` factory, `int(value)` still raises a bare `ValueError` for input like `abc`. argparse then reports "invalid _parse value", where it used to say "invalid _positive_int value". Catch `ValueError` and raise `ArgumentTypeError(f"{flag_name} must be a positive integer")`, as the design docstring describes.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T12:21:29Z

**Decision**: SKILL.md only gains `[--deadline N]` in the usage line. It does not say that the default is 300 seconds, that the deadline covers the whole sweep, or what the new `Partial:` line means in the report. This meets the PRD's literal wording, but a reader of the skill cannot learn what the flag does.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

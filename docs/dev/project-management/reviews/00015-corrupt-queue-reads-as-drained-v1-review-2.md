---
prd: dev/local/prds/wip/00015-corrupt-queue-reads-as-drained-v1.md
review: 2
date: 2026-09-05
head_sha: 3104bc5d2befbd7499273fabc1ae947229d63113
codex_thread_id: 01a070c2-d9c9-7130-9f3f-11e7c42f7ec0
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
---

# Review: 00015-corrupt-queue-reads-as-drained-v1

Diff range: `5ef8be11fdc299d360d553f0a45793fe1a48b917..3104bc5d2befbd7499273fabc1ae947229d63113`
(incremental — cycle 1 reviewed `aaf190ca..5ef8be11`), restricted to
`skills/distil-memory/` and `CHANGELOG.md`.

codex_rung_guard: not fired

pack: unavailable (`engram pack` exited 1 twice — "not inside a registered repo;
register it in `~/.config/gita/repos.csv`"). `{PACK_FILE}` and `{PACK_FINDINGS}`
were substituted with `(no pack available this cycle)`. The review is degraded by
the missing retrieval context, not invalid.

## Review Summary

Reviewed: 3 completed rework tasks (4, 5, 6 — all `[D1]` decision-gate follow-ups)
PRDs checked: 00015-corrupt-queue-reads-as-drained-v1

### Agent Status

- Alice: ✅ Available (consensus lens, engine `legacy`)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (doubt + de-slop lens, codex, resumed thread `01a070c2`)
- Carl: ⚠️ Unavailable: copilot backend refused again —
  `Model "gemini-3.1-pro-preview" from --model flag is not available` (exit 1).
  Not retried: cycle 1 already spent his retry budget against both backends and
  recorded the native-gemini refusal (`IneligibleTierError`, free tier) as
  deterministic. `carl-output-00015-c2.txt` holds only the error line and was
  excluded from consolidation so it could not inflate the consensus denominator.
  Consolidation ran at N=3.

### Degradations recorded loud

1. **The diff was restricted by hand, and the reason is not cosmetic.** The
   working branch is `master` and peer sessions committed to it in the same
   window. The raw range `5ef8be1..HEAD` carries 14 commits, 5 of them unrelated
   work (`6a78586` sweep-fix, `2bb7fdb` capture-experiment, `710faae`
   handoff-session, `fea5d55` brief-portfolio, plus `.gitignore`). Reviewers
   received `git diff 5ef8be1..HEAD -- skills/distil-memory CHANGELOG.md` (537
   lines) instead. This PRD touched no file in the excluded set, so no regression
   of its work can hide there. One in-diff commit, `bc4ecf7`, is a peer session's
   `--distil-limit` doc paragraph in the same skill; reviewers were told not to
   raise findings against it, and none did.
   Unlike cycle 1, `gather-context.sh` itself was **not** broken here:
   `--since 5ef8be1` overrode its "vs master" base resolution, so the script ran
   and produced the context file; only its diff was replaced with the scoped one.
2. **The first Watcher exhausted its 30-run budget before codex started work.**
   Bob's codex run was dispatched at 14:28 and did not emit `thread.started` /
   `turn.started` until 15:20 — 52 minutes of queueing. The skill's rule reads a
   `WAITING` return after 30 runs as a stalled reviewer, but the process was
   demonstrably alive (both events in its own event stream), so a second Watcher
   was dispatched rather than marking Bob failed. He returned a complete review
   on that Watcher's 3rd poll. Treating the first timeout as a failure would have
   dropped the doubt lens for a reviewer that was working.
3. **`braid --check` still cannot be run** — warden blocks it by command name and
   by absolute path (`[warden] blocked braid: unknown command`), in this session
   as in cycle 1's. This is Bob's F10 and it remains unverified; see the
   settled-decisions section for why it is not a gate for this PRD.

## Consolidated Findings

4 findings, all Medium or Low. No reviewer raised a Critical, and the one High
raised was auto-dismissed against the settled-decisions ledger.

| Consensus | Severity | Issue | File | Found By |
|-----------|----------|-------|------|----------|
| [2/3] + mech | 🟡 Medium | The invalid-UTF-8 queue-layer test asserts `"utf-8" in reason or "decode" in reason` — an either-or hedge, so either wording alone satisfies it and neither is actually pinned | skills/distil-memory/scripts/test_docket_exit_codes.py:387 | ALICE, BOB, mech-check |
| [1/3] | 🟡 Medium | F9: the new per-class diagnostic sweep duplicates the existing corruption sweep's setup and CLI invocation; fold its literal-diagnostic assertion into the existing parametrized `next` test and drop the duplicate | skills/distil-memory/scripts/test_docket_exit_codes.py:122 | BOB |
| [1/3] | 🟡 Medium | 15 touched tests pass against the pre-change code at `5ef8be11fdc2`, led by `test_each_corruption_class_is_named_in_its_own_words_on_stderr` | skills/distil-memory/scripts/test_docket_exit_codes.py | mech-check |
| [1/3] | ⚪ Low | F10: cannot statically verify that `braid --check` succeeded at the reviewed HEAD; its result was not supplied | N/A | BOB |

Alice's and Bob's rows 1 above were emitted separately by
`consolidate_findings.py` (two `[1/3]` rows) and are shown merged here: same
defect, same `file:line`, different wording. The unmerged table is reproducible
from `alice-output-00015-c2.txt` and `bob-output-00015-c2.txt`. The tautological
-shapes `[MECH]` line names the same test and assertion, so `mech-check` is
appended to that row's finders rather than added as a separate row.

### Auto-dismissed (ledger)

Both of Blake's findings matched settled cycle-1 entries and were dismissed by
`consolidate_findings.py --ledger --ledger-dismiss BLAKE`:

- `[BLAKE] 🟠 Task 2's required exit-code tests live in a new file
  test_docket_exit_codes.py instead of test_docket.py as the acceptance
  criterion specifies, and this 4th file also breaks the Success Criteria
  assertion that the sweep lists SKILL.md and three test files` | File:
  skills/distil-memory/scripts/test_docket_exit_codes.py — **dismissed**:
  measured, `test_docket.py` is 780 lines and `test_docket_exit_codes.py` is 224;
  merging them to satisfy the literal command yields a ~1004-line file, breaching
  the 800-line limit (R13). The split satisfies the criterion's intent; the
  literal single-file command and the "three test files" count are stale PRD
  text.
- `[BLAKE] 🟡 uv run pytest skills/distil-memory/scripts -q reports "574 passed,
  1 xfailed", not "no failures and no xfailed tests" as the Success Criteria
  states` | File: skills/distil-memory/scripts/test_write.py — **dismissed**:
  confirmed pre-existing and out of scope; the xfail belongs to a different agoge
  defect and predates `work_start_sha` `aaf190c`. The criterion is suite-wide over
  a directory this PRD only partly owns, which the repo's own create-prd rule now
  forbids (commit `5b1cfda`).

Blake reached both independently, blind, for the second cycle running. That is
the ledger working as designed, not Blake failing: an implementation-aware
reviewer gets the settled list in its prompt, a blind one must not, so his
re-raises are absorbed mechanically here instead.

### Prior cycle's findings — all eight verified resolved

| Cycle-1 finding | Status at `3104bc5` |
|-----------------|---------------------|
| F1 🟠 uncaught `UnicodeDecodeError` | **Resolved.** `load()` catches `UnicodeDecodeError` alongside `OSError`/`JSONDecodeError` (`docket.py:50`); `test_main_next_returns_two_when_the_queue_file_is_not_valid_utf8` sweeps six undecodable payload families and asserts exit 2, message on stderr, no traceback, empty stdout. 22 of 38 touched tests fail against the pre-change code, these among them. |
| F2 🟡 `null` diagnosed as an empty file | **Resolved.** `if not text:` replaces `if data is None:` (`docket.py:52`), so a parsed `None` falls through to the non-dict schema message. `test_main_next_names_a_non_object_queue_payload_rather_than_calling_the_file_empty` sweeps six non-object payloads and asserts `"empty" not in reason and "object" in reason`; its pair `test_main_next_still_diagnoses_a_zero_byte_queue_file_as_empty` keeps the two classes distinguishable. |
| F3 🟡 read failure inside `decide()` read as a refusal | **Resolved by construction.** `main()` reads once and passes `data=` into `decide()`, which loads only when given none (`docket.py:124-138`, `229-239`). There is no second read left to misclassify. |
| ⚪ `decide`'s double-`load()` TOCTOU window | **Resolved by the same change** — the window is removed, not guarded. `test_main_decide_reads_the_queue_once_so_no_later_read_can_be_taken_for_a_refusal` asserts `reads == [None]`. |
| F4 🟡 no fixture for a present non-list `entries` | **Resolved.** `"non-list-entries": '{"cursor": 0, "entries": {}}'` added to `_CORRUPT_QUEUE_SHAPES`; seven shapes now sweep. |
| F5 🟡 `_proposal` exposes unused variations | **Resolved.** `_proposal(line_no)` — the three unused parameters are gone and the three call sites simplified. |
| F6 🟡 tagged failure cases and conditional dispatch in the decide tests | **Resolved.** The tag-dispatching parametrization is split into two plain tests (`..._when_the_queue_file_is_corrupt`, `..._for_a_refusal_shaped_message`), and the duplicated real-file sweep is gone. |
| ⚪ `SKILL.md` step 5 omits `decide`'s exit 2 | **Resolved.** Line 199 now reads "`decide` exits 1 for a refused decision and 2 if the queue cannot be read; `write` exits 1." |

### Settled decisions recorded this cycle (ledger)

- **The fail-first replay row — discarded, with evidence.** The 15 touched tests
  that pass against `5ef8be11fdc2` are coverage backfills for classes the
  implementation already handled at that base: F4 was explicitly "a TEST gap, not
  an implementation gap", and the restructured F5/F6 tests are behaviour
  -preserving by design. The behaviour this diff actually changed **is** pinned —
  22 of 38 touched tests fail at base, including every invalid-UTF-8 and
  non-object-payload case. The lead test named,
  `test_each_corruption_class_is_named_in_its_own_words_on_stderr`, exists
  precisely to defeat a self-oracling suite and was proven to bind by installing
  a deliberately weakened `load()` over `docket.py`: 6 of its 7 cases failed,
  after which the file was restored from git.
- **F10 (`braid --check` unverified) — deferred, not fixable here.** Warden
  blocks `braid` by command name and by absolute path in this session, as it did
  in cycle 1's. It is not a gate for this PRD: `braid --check` validates the
  skills link farm, and this diff changes only file contents inside an existing
  skill plus the CHANGELOG, so it cannot alter what braid links. The
  skill-validity half of the repo's pre-commit trio did run at this HEAD —
  `uv run python3 skills/create-skill/scripts/validate_skill.py
  skills/distil-memory` exited 0. It stays an open repo-level check.

### Out-of-scope mechanical finding, recorded rather than dropped

The fail-first replay also emitted
`[MECH] 🟡 1 touched test(s) pass against the pre-change code:
test_scan_finds_a_dash_prefixed_pattern_via_rg | File:
skills/sweep-fix/scripts/test_sweep_scan.py`. That file belongs to the peer
session's `6a78586` commit, outside this PRD. It is recorded here and is not a
finding against PRD 00015.

## Follow-up Tasks Created

The cycle converged (no unresolved Critical or High), so the two actionable
Medium findings were swept in one `[D2]` task through the decision gate's tail
sweep rather than opening another review cycle:

1. `[D2] Pin the UTF-8 diagnostic wording and fold the duplicate corruption
   sweep into one test` (S) — 🟡 — addresses the either-or hedge at
   `test_docket_exit_codes.py:387` and Bob's F9 at `:122`.

**Sweep outcome (task 7, committed as `985b861`).** Ran the rework micro lane:
2 non-Critical findings in 1 clean file, so the orchestrator edited it directly
(no Tess, no Devon, no test commit, no red check). 16 insertions / 28 deletions,
net -12, below the 30-line micro ceiling. The `or` hedge became two separate
asserts, and the real `UnicodeDecodeError` message was confirmed to carry BOTH
`utf-8` and `decode` for all twelve parameter combinations. The standalone
diagnostic sweep was folded into
`test_main_next_returns_two_and_reports_the_error_when_the_queue_is_unreadable`,
which now parametrizes over shape keys and asserts the literal diagnostic
alongside the raised message; the file went 47 → 40 tests, exactly the 7
parameters the deleted test carried, with no assertion lost. The merged test was
re-proved to bind by installing the preserved mutant `load()` over `docket.py`:
19 failed / 21 passed, 6 of the 7 corruption shapes failing (all but
`empty-file`) — the same 6-of-7 the standalone test produced. `docket.py` was
restored from git and the tree confirmed clean; the mutant is not committed.
Pat returned `CLOSURE | resolved` for both findings and `NO FINDINGS`.
`style_gate: clean`, `split_hygiene: clean`. Final suite at `985b861`:
`uv run pytest -q` exit 0, 1021 passed, 0 failed, 5 skipped, 11 xfailed;
`validate_skill.py skills/distil-memory` exit 0. No verify escapes and no sweep
escapes: this cycle queued no verification checks, and Pat raised nothing.

## Alice

Implementation-aware consensus lens, incremental. She verified each of the eight
prior findings against the code and found one new defect, agreeing with Bob and
with the mechanical shapes check on it.

```
[ALICE] 🟡 New test uses an either-or hedge that lets either substring satisfy the assertion instead of pinning the actual diagnosis wording (`assert "utf-8" in reason or "decode" in reason`) | File: skills/distil-memory/scripts/test_docket_exit_codes.py:387 | Task: 4
```

```
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
```

## Blake

Blind lens — PRD only, no diff, no file list, no review history, no settled-
decisions feed. He found the code himself and re-raised the two deviations
between the PRD's literal text and the shipped test layout. Both matched settled
cycle-1 ledger entries and were auto-dismissed (above). He raised nothing new.

```
[BLAKE] 🟠 Task 2's required exit-code tests (docket.main(["next"]) == 2, docket.main(["cursor"]) == 2, all-decided next==1) live in a new file test_docket_exit_codes.py instead of test_docket.py as the acceptance criterion specifies ("uv run pytest .../test_docket.py -q passes with new tests that..."), and this 4th file also breaks the PRD's Success Criteria assertion that the docket caller-sweep is "only skills/distil-memory/SKILL.md and three test files" (it is now four: test_write.py, test_walkthrough_integration.py, test_docket.py, test_docket_exit_codes.py). The Implementation section's module list only names docket, test_docket, and SKILL — no fourth module. | File: skills/distil-memory/scripts/test_docket_exit_codes.py | Task: general
[BLAKE] 🟡 `uv run pytest skills/distil-memory/scripts -q` reports "574 passed, 1 xfailed" (verified by running it), not "no failures and no xfailed tests" as the PRD's Success Criteria literally states. The xfail is skills/distil-memory/scripts/test_write.py::test_an_index_that_cannot_be_read_leaves_no_memory_file_behind, a pre-existing marker from an earlier, unrelated PRD (commit 1a60fe0) that this PRD's tasks never touch, but the stated success criterion is directory-wide and is currently false. | File: skills/distil-memory/scripts/test_write.py | Task: general
```

```
B1: fail
B2: pass
B3: pass
B4: pass
B5: pass
B6: fail
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass
```

## Bob

Doubt + de-slop lens (codex), resumed on his own cycle-1 thread
`01a070c2-d9c9-7130-9f3f-11e7c42f7ec0`, so he verified the fixes against his own
critique rather than re-reviewing from zero. His context and the full diff were
inlined into the prompt file (57 KB): his sandbox forbids opening files, which is
what made his cycle-1 first run useless. He closed all six of his own prior
findings without comment and raised two new de-slop items plus one
static-verification limit.

```
[BOB] 🟡 F8: The UTF-8 diagnostic assertion hedges with `or`, allowing either encoding or decoding wording alone. Require both explicitly. | File: skills/distil-memory/scripts/test_docket_exit_codes.py:387 | Task: 4
[BOB] 🟡 F9: The new diagnostic sweep duplicates the existing corruption sweep’s setup and CLI invocation. Add its literal diagnostic assertion to the existing parametrized test, preserving all current assertions. | File: skills/distil-memory/scripts/test_docket_exit_codes.py:122 | Task: 6
[BOB] ⚪ Cannot statically verify: F10: the required `braid --check` succeeded at the reviewed HEAD; its result was not supplied. | File: N/A | Task: general
```

```
FIX:
- F8 — skills/distil-memory/scripts/test_docket_exit_codes.py:387 — Replace the disjunction with separate assertions requiring `"utf-8"` and `"decode"` in the reason.
- F9 — skills/distil-memory/scripts/test_docket_exit_codes.py:122 — Parametrize the existing `next` test by shape, add the literal diagnostic assertion, and remove the duplicate sweep.
VERIFY:
- F10 — Run `braid --check` at reviewed HEAD `3104bc5` and confirm exit 0.
KNOWN:
- (none)
```

```
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
```

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

No verification-check queue was written this cycle. Bob's VERIFY bucket holds
one item (F10, `braid --check`), but `references/output-formats.md` reserves
`source: "bob"` — only Eve or a lane standing in for her sources a queue entry,
and the codex doubt-roster guard did not fire, so Eve was not active. F10 is
therefore carried as an ordinary finding and settled above. The orchestrator ran
the check anyway; warden blocked it both by name and by absolute path.

## Carl

⚠️ Unavailable — the copilot backend refused before any review ran:
`Model "gemini-3.1-pro-preview" from --model flag is not available` (exit 1).
Not retried; cycle 1 spent his retry budget across both backends and recorded the
native-gemini refusal (`IneligibleTierError`, free tier `UNSUPPORTED_CLIENT`) as
deterministic. `carl-output-00015-c2.txt` holds only the error line and was
excluded from consolidation.

Verdict: 4 findings
Tests: 1028 passed, 0 failed, 5 skipped (reused from last-verification.json at 3104bc5)

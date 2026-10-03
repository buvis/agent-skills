---
prd: dev/local/prds/wip/00020-changelog-skill-presence-check-v1.md
review: 2
date: 2026-09-06
head_sha: a28dc140249126d5b779c827e272d3c1c93fa10d
codex_thread_id: 01a077ec-1aa8-7ef1-96ba-8ed4aab0f82a
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00020-changelog-skill-presence-check-v1

Diff range: `c215956137d3c7b1739e5316e2c4a245ec8e00ec..a28dc140249126d5b779c827e272d3c1c93fa10d`

codex_rung_guard: not fired

pack: unavailable this cycle (`engram pack` exited 1 twice: "not inside a registered
repo; register it in ~/.config/gita/repos.csv"). Reviewers ran without the context
pack; `{PACK_FILE}`/`{PACK_FINDINGS}` were substituted with the documented sentinel.

Scope: **incremental**. `gather-context.sh --since c215956137d3c7b1739e5316e2c4a245ec8e00ec`
produced a non-empty 633-line diff over 3 files (the cycle-1 rework commits `4991731`,
`4158240`, `a28dc14`). Bob resumed his cycle-1 codex thread via `--resume-thread`.

## Review Summary

Reviewed: 4 completed tasks (tasks 1-3 reviewed in full at cycle 1; task 4 is this
cycle's scope)
PRDs checked: 00020-changelog-skill-presence-check-v1

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind/PRD-only lens)
- Bob: ✅ Available (codex, consensus + doubt/de-slop lens, resumed thread
  `01a077ec-1aa8-7ef1-96ba-8ed4aab0f82a`)
- Carl: ✅ Available (gemini-run backend=copilot, model=gemini-3.8-flash)
- Eve: ⏸️ Disabled (doubt_reviewer=codex and no codex-implemented task, so the
  codex doubt-roster guard did not fire; Eve is an opt-in fifth lens)

### Watcher note (process, not a code finding)

The stock `await_reviewer_outputs.py` treats any existing non-empty file whose mtime
has been quiet for 30s as complete. `bob-output-2.txt` and `carl-output-2.txt` already
existed from an **earlier PRD's** cycle-2 review (Aug 31), so the first Watcher returned
`DONE` instantly, before either CLI reviewer had written anything. Caught by checking
mtimes; a second Watcher was dispatched running a freshness-aware variant
(`/tmp/await-fresh-reviewers.py`, identical logic plus `--newer-than <epoch>`), and both
CLI outputs were then confirmed genuinely fresh (Bob 20:58, Carl 20:57) before any
consolidation ran. No stale output entered this review. The underlying gap in the
shipped script is real and is recorded below as a deferred process finding.

## Cycle-1 findings: all resolved

Every cycle-1 finding was verified resolved against the code this cycle:

| Cycle-1 finding | Status at `a28dc14` |
|---|---|
| 🟠 [3/4] tautological `test_main_with_argv_parameter` (`result in (0, 1)`) | **Fixed** — now `assert c.main(argv=[]) == 0`, an exact exit code (line 207). No hedge assertion remains in the file. |
| 🟠 [3/4] `main()` resolves via `Path.cwd()` | **Fixed** — `REPO_ROOT = Path(__file__).resolve().parent.parent`. Blake independently ran the check from `/tmp` and got exit 0 silent; `TestMainPathResolution` (line 311) now `monkeypatch.chdir(tmp_path)` and still asserts exit 0 against the real repo. |
| 🟠 [4/4] case-insensitive matching | **Fixed** — `.lower()` case-folding removed; matching is literal and case-sensitive, pinned by `test_different_case_occurrence_is_reported_missing` (`alpha` vs `Alpha`). |
| 🟡 stderr tests use containment/`startswith` | **Fixed** — every stderr assertion now compares the complete `captured.err` value. |
| 🟡 412-line, 29-test module with duplicated setup | **Fixed** — 344 lines, 27 tests, shared `_skills_tree(tmp_path, changelog_text)` helper. |
| 🟡 docstrings paraphrasing the following code | **Fixed** — one-line contracts; the `# Read changelog content` style comments are gone. |
| 🟡 missing type annotations | **Fixed** — `find_missing(skills_dir: Path, changelog_path: Path) -> list[str]`, `main(argv: list[str] \| None = None) -> int`. |
| ⚪ PRD-named tests only as class methods | **Fixed** — the three PRD-named functions are module-level (lines 19, 29, 40). |
| ⚪ retroactive CHANGELOG entry | Settled deferral (cycle 1 ledger), unchanged. |
| ⚪ Bob `[VERIFY]` sandbox line | Discarded (cycle 1 ledger); not re-raised this cycle. |

No regression was introduced by the rework.

## Consolidated Findings

6 rows: 5 as emitted by `consolidate_findings.py` (run with
`--ledger … --ledger-dismiss BLAKE`; no Blake finding matched a settled entry, so
there is no auto-dismissed section) plus 1 absorbed `[MECH]` replay row.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟡 | `TestFindMissingCaseSensitivity`'s two tests re-inline the skills_dir/changelog setup instead of using the `_skills_tree` helper added in the same rework, reintroducing the duplication task 4 asked to remove | scripts/test_check_changelog_skills.py:285-305 | 4 | ALICE |
| [1/4] | 🟡 | [FIX] The exit-1 contract is tested five times; keep the comprehensive two-name test asserting exit code, empty stdout, and exact sorted stderr, then delete the four narrower duplicates | scripts/test_check_changelog_skills.py:159 | 4 | BOB |
| [1/4] | 🟡 | [FIX] The second case-sensitivity test duplicates the existing embedded-literal-substring test; the different-case test plus the existing substring test already cover both behaviors | scripts/test_check_changelog_skills.py:296 | 4 | BOB |
| [1/4] | 🟡 | [FIX] Exit 0 with no output is duplicated; retain either the named-skill case or the empty-tree acceptance case, since `find_missing` already separately covers both inputs | scripts/test_check_changelog_skills.py:258 | 4 | BOB |
| [1/4] | 🟡 | 11 touched test(s) pass against the pre-change code: test_reports_a_skill_dir_absent_from_the_changelog, test_passes_when_every_skill_dir_is_named, test_grandfathered_name_is_skipped, test_empty_skills_dir_returns_empty_list, test_skill_named_in_changelog_not_missing, test_substring_matching_requires_literal_substring +5 more | scripts/test_check_changelog_skills.py | general | mech-check |
| [1/4] | ⚪ | `find_missing()`/`main()` call `changelog_path.read_text()` with no try/except; a missing or unreadable `CHANGELOG.md` raises an unhandled traceback instead of a clear CI error message. Not required by the PRD, low risk since the file is guaranteed to exist in a normal checkout. | scripts/check_changelog_skills.py | general | BLAKE |

**Zero CRITICAL and zero HIGH findings.** Every survivor is Medium or Low.

### Orchestrator note: the four test-duplication rows are one theme, four distinct edits

Alice cites `:285-305`, Bob cites `:159`, `:296` and `:258`, so
`consolidate_findings.py` keeps them as separate rows. They are not paraphrases of one
defect — each names a different duplicate — but they all fall out of the same cause:
this cycle's own de-slop pass trimmed the module without finishing the job. They are
swept as one task.

They also interact, and the sweep task says so: Bob's `:296` row deletes
`test_exact_case_occurrence_embedded_in_longer_word_is_not_missing`, which is one of
the two tests Alice's row asks to route through `_skills_tree`. Deleting it satisfies
both, and the embedded-substring behaviour stays pinned by
`test_substring_matching_requires_literal_substring` (line 94), which already asserts
`foo` is found inside `foobar`.

### Mechanical checks (computed)

- Tautological test shapes: 27 test functions checked in 1 file, **no `[MECH]` lines**.
  The cycle-1 hedge assertion is gone and nothing replaced it.
- Fail-first replay against `c215956137d3`: 24 touched tests ran, **13 failed at base,
  11 passed**, 0 files uncollectable. The 13 failures are the tests pinning this
  cycle's two behaviour fixes (case-sensitive matching, `REPO_ROOT` resolution). The 11
  passers are retained pre-existing behaviour carried through a behaviour-preserving
  test-trimming pass, which is exactly the case the replay block says to weigh against
  PRD intent rather than raise. Ledgered as discarded on that basis.
- Function line counts (`ast`): `find_missing` 15 lines, `main` 13 lines — both far
  under the 50-line limit (R12 pass). `test_check_changelog_skills.py` is 344 lines,
  under the 800-line limit (R13 pass).
- No finding contradicts the computed facts block; nothing discarded on that ground.

## Alice

Consensus lens, implementation-aware. 1 finding (🟡). She verified every cycle-1
finding resolved, ran `uv run pytest scripts/test_check_changelog_skills.py -q`
(27/27), `uv run ruff check` / `ruff format --check` (clean), and
`python3 scripts/check_changelog_skills.py` (exit 0), then found the one duplication
this cycle's own trimming reintroduced.

Verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass,
R10 pass, R11 pass, R12 pass, R13 pass.

## Blake

Blind lens, PRD-only — never saw the diff, the file list or the review history, and
located the code himself. He independently re-ran every PRD acceptance command and, on
his own initiative, ran the check **from `/tmp`** as well: exit 0 silent, which is the
direct confirmation that the cycle-1 repo-root High is fixed. He confirmed
`GRANDFATHERED` matches the pinned 14 names verbatim, all three PRD-named test
functions exist and pass (27 passed), `ci.yml` parses with both required `lint` steps
present exactly once, the deferred `**<name>**` stricter match is correctly absent, no
new dependencies (stdlib `sys`/`pathlib` only), no extra CLI flags, and no destructive
file operations. He also spot-checked all 14 grandfathered names against real `skills/`
directories.

1 finding (⚪, unguarded `read_text()` — discarded, see the ledger below).

Verdicts: B1-B19 all pass.

## Bob

Consensus + doubt/de-slop lens (codex, static-only sandbox), resumed from his cycle-1
thread. 3 findings, all 🟡, all from the de-slop lens: three distinct residual
duplications the trimming pass left behind. He raised no `[VERIFY]` line this cycle —
the cycle-1 sandbox artefact was fed to him as a settled discard and he did not
re-raise it.

Verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass,
R10 pass, R11 pass, R12 pass, R13 pass.

Doubt rubric: D1 pass, D2 pass, D3 pass, D4 pass, D5 pass.

## Carl

Consensus lens (gemini-3.8-flash via copilot backend). **0 findings** —
`[CARL] ✅ No issues found`. He executed the acceptance commands live: the per-file
pytest, `uv run ruff check scripts/` and `uv run ruff format --check scripts/`, the
full `uv run pytest` suite, the check from the repo root, the `GRANDFATHERED` one-liner,
and the ci.yml YAML parse. Two of his attempts to run the check from outside the repo
root were refused by his sandbox, so he verified repo-root resolution a third way
(chdir into `dev/` in-process) and got exit 0. The diff has no frontend surface, so he
reviewed as a generalist and invented no frontend findings, as his persona instructs.

Verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass,
R10 pass, R11 pass, R12 pass, R13 pass.

## Verification-check queue

No queue file written this cycle, for the same structural reason as cycle 1: the queue
is fed from a doubt lens's VERIFY bucket, and the only bucket-emitting doubt lane (Eve,
or a stand-in dispatched in her place) did not run — the codex doubt-roster guard did
not fire, so Eve stayed disabled. Bob tags findings `[FIX]` inline but emits no
FIX/VERIFY/KNOWN buckets, and `output-formats.md` reserves `source: "bob"` precisely so
a bucket he did not emit is never invented. Cycle 1 wrote no queue either, so there was
nothing to carry forward into this cycle.

## Settled-decisions ledger

Two entries appended this cycle (bringing the file to five):

- **discarded** ⚪ Blake's unguarded `read_text()`. The PRD never asked for it, and the
  repo's own coding-style rule forbids adding error handling for scenarios that cannot
  occur, validating at system boundaries only. `CHANGELOG.md` is guaranteed present in
  any checkout the check runs in, and a traceback is a legible CI failure. Adding the
  guard would be scope creep against the PRD's own B6/B7 no-extra-functionality rules.
- **discarded** 🟡 the `[MECH]` fail-first replay row. 11 of 24 touched tests passing at
  base is the expected shape for a diff that is two behaviour fixes plus a
  behaviour-preserving test-trimming pass; the 13 failures are the tests pinning the
  fixes. The replay block itself instructs weighing PRD intent before raising this.

Verdict: 6 findings
Tests: 1073 passed, 0 failed, 5 skipped (reused from last-verification.json at a28dc140249126d5b779c827e272d3c1c93fa10d)

---
prd: dev/local/prds/wip/00047-check-links-repeated-stats-v1.md
review: 1
date: 2026-09-07
head_sha: e122f46f258b03297e9f73e98f020e10292d2c98
codex_thread_id: 01a07b33-02a0-7901-804b-b2f67f36b2bd
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00047-check-links-repeated-stats-v1

Diff range: `bb882fc3543d4bf22dbad5af681fb0f8020f9172..e122f46f258b03297e9f73e98f020e10292d2c98`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in ~/.config/gita/repos.csv") — no
pack available this cycle. Prompts carried the `(no pack available this cycle)` sentinel for
`{PACK_FILE}` and `{PACK_FINDINGS}`. Additive retrieval context only; the review is degraded, not
invalid.

Diff-scope note: `gather-context.sh` with no `--since` produced an EMPTY diff — it diffs against the
detected base branch, and this repo commits directly on `master`, so `master..HEAD` is empty. The
run was redone with `--since <work_start_sha>`, giving the PRD's whole work range as the review
scope. The script labels that "incremental review"; the label is wrong here and was corrected in the
context file. This is cycle 1 and a full review.

## Review Summary

Reviewed: 2 completed tasks
PRDs checked: 00047-check-links-repeated-stats-v1.md

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens; `consensus_engine: legacy`)
- Blake: ✅ Available (Claude subagent, blind/PRD-only lens)
- Bob: ✅ Available (codex, doubt + de-slop lens; exit 0, no fallback needed)
- Carl: ✅ Available (gemini via `backend=copilot model=gemini-3.8-flash`)
- Eve: ⏸️ Disabled (codex doubt-roster guard not fired — no task attempt has `implementor: "codex"`;
  both tasks were implemented by `claude`)

All four dispatched reviewers returned parseable output on the first attempt. No retries were spent.

## Consolidated Findings

`consolidate_findings.py` emitted five rows. Two of them — Alice's and Bob's — describe the SAME
defect in the same test, and were merged model-side into one `[2/4]` row: the script merges
paraphrases only when the `File:` strings match, and Alice wrote
`skills/review-prd-backlog/scripts/test_check_links.py` while Bob wrote the same path with `:157`
appended. Left unmerged it would have understated real two-reviewer agreement as `[1/4]`. The merge
is recorded here rather than silently applied.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟡 Medium | `test_autouse_fixture_clears_cache_before_each_test_starts` does not pin what it claims. It asserts `cache_info().currsize == 0`, which is guaranteed by the autouse fixture regardless of what a prior test left behind, and run alone it passes even with the fixture removed — so it only "works" via test ordering. Alice adds that cross-test pollution is already covered by `test_resolve_path_call_adds_one_cache_entry`; Bob asks for a self-contained regression that seeds the cache before fixture setup and verifies clearing. | skills/review-prd-backlog/scripts/test_check_links.py:157 | 1 | Alice, Bob |
| [1/4] | ⚪ Low | The CHANGELOG.md entry for the caching fix landed in a separate commit (`84e2fb1`) rather than the same commit as the behavior change (`f91243b`), which the `rules/changelog.md` house rule requires bundled. Does not affect the merged diff's correctness. | CHANGELOG.md | 1 | Alice |
| [1/4] | ⚪ Low | The CHANGELOG entry says "once per run", but the cache persists for the life of the process, not a run. Describe the guarantee as once per `(token, root)` pair per process. | CHANGELOG.md:51 | 1 | Bob |
| [1/4] | ⚪ Low | Cannot statically verify (Bob's sandbox): that tests pass at the reviewed revision. The supplied replay block establishes failures against the base, not passing results at HEAD. Asks for `uv run pytest` at `e122f46`. | N/A | general | Bob |

No 🔴 Critical and no 🟠 High findings. The Medium/Low tail is swept by the decision gate, not
carried into another review cycle.

### Findings the mechanical blocks did NOT catch

Worth recording, because it bounds what those blocks prove. The `[2/4]` Medium above is invisible to
both computed checks by construction:

- The **tautological-shapes** block found nothing: the assert is `currsize == 0`, neither constant,
  self-comparing, nor an either-or hedge.
- The **fail-first replay** reported all 5 touched tests failing against base — including this one.
  But it fails at base for an unrelated reason: `resolve_path` has no `.cache_info()` there, so the
  test errors with `AttributeError` rather than failing on its assertion. "Fails against base" was
  true and still did not mean "pins this change".

Two reviewers reading the test found it anyway. That is the lens earning its cost.

### Carry-forward and mechanical absorption

- **Carry-forward:** none. This is cycle 1; there is no `…-checks-0.json` to read, which is normal
  and never an error.
- **Mechanical test checks:** both blocks produced zero `[MECH]` lines (13 test functions checked in
  1 file; 5 touched tests replayed, 5 failed against base, 0 passed). Nothing to absorb into the
  table.

### Verification-check queue

**Not written this cycle.** The queue is fed from a doubt lens's VERIFY bucket, and per
`references/output-formats.md` the source `"bob"` is explicitly reserved — `agents/bob.md` emits
`[BOB]` issue lines and `R{n}`/`D{n}` verdicts and defines no FIX/VERIFY/KNOWN buckets. Eve did not
run (guard not fired), so no lane with a VERIFY bucket produced output.

Bob's third finding does name an exact command (`uv run pytest` at `e122f46`), but it is **not
queued: no doubt-lens VERIFY bucket ran this cycle**. It stays an ordinary finding and is classified
normally. It is also already answered by recorded evidence — see the `Tests:` line below, plus
Carl's own `uv run pytest` run this cycle and Blake's file-scoped run (13 passed).

### Follow-up tasks

None created here. Task creation for this converged cycle is owned by the decision gate's **Tail
sweep** (`run-autopilot/references/phase-review.md` Phase 5), which builds ONE `[D1]` task from the
actionable Medium/Low findings. Creating them in this step as well would double-create the same
work.

## Alice

Consensus lens, implementation-aware. Two findings, both above. All twelve consensus rules pass.

Verification she performed: read `check_links.py` and `test_check_links.py` at HEAD; confirmed
`@functools.cache` sits directly above `def resolve_path` (lines 67-68); ran
`uv run pytest skills/review-prd-backlog/scripts/test_check_links.py -q` (13 passed, 0 failed); ran
the acceptance test alone (1 passed); checked file sizes (141 and 176 lines) and function sizes
against the mechanical-facts block; cross-checked the commit history against the context's per-task
commit attribution, all consistent. She notes `check_links.py` is invoked only via subprocess per
`skills/review-prd-backlog/SKILL.md`, so the unbounded process-lifetime cache carries no
cross-invocation staleness risk — matching the PRD's stated design intent.

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

Blind lens — PRD only, no diff, no file list, no review history. He located the code himself.

```
[BLAKE] ✅ No issues found
```

Independent verification worth keeping: he copied the files to a scratch directory, stripped the
`@functools.cache` decorator, and reran the target test — it errored, confirming the test is not
vacuous. He also traced the history and caught that the first attempt (`f91243b`) used
`@functools.lru_cache` with the default `maxsize=128`, which would have silently re-stat once a
repo's distinct-path count passed 128 — and the PRD's own numbers cite 150 distinct paths on the
real backlog. `a007116` corrected it to unbounded `@functools.cache` in the very next commit. The
shipped code is correct; the near-miss is recorded because the bound was smaller than the PRD's own
stated workload.

Non-blocking observation he raised without filing: the implementation adds 4 tests beyond the one
named in the PRD task list. He judged this not scope creep against B6/B7, since they cover the same
"Must have" cache-clearing bullet and add no production behavior.

```
B1: pass    B2: pass    B3: pass    B4: pass    B5: pass
B6: pass    B7: pass    B8: pass    B9: pass    B10: pass
B11: pass   B12: pass   B13: pass   B14: pass   B15: pass
B16: pass   B17: pass   B18: pass   B19: pass
```

## Bob

Doubt + de-slop lens, codex, static-only sandbox. Three findings, all above. He is the only reviewer
to fail a consensus rule: **R2 fail**, on the order-dependent test.

```
[BOB] 🟡 FIX: The cache-isolation test depends on the preceding test populating the cache; run alone, it passes even without the clearing fixture. Replace the order-dependent pair with a self-contained regression that seeds cache before fixture setup and verifies clearing. | File: skills/review-prd-backlog/scripts/test_check_links.py:157 | Task: 1
[BOB] ⚪ FIX: The changelog says "once per run," but caching persists across runs in the same process. Describe the guarantee as once per `(token, root)` pair per process. | File: CHANGELOG.md:51 | Task: 1
[BOB] ⚪ Cannot statically verify: VERIFY — tests pass at the reviewed revision; run `uv run pytest` at `e122f46f258b03297e9f73e98f020e10292d2c98`. The supplied replay establishes failures against the base, not passing results at HEAD. | File: N/A | Task: general
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
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Gemini via `backend=copilot`, `model=gemini-3.8-flash`. Generalist review — the diff has no frontend
surface, and he correctly did not invent frontend findings.

```
[CARL] ✅ No issues found
```

He executed `uv run pytest skills/review-prd-backlog/scripts/test_check_links.py`, the full
`uv run pytest`, `validate_skill.py` on `skills/review-prd-backlog`, and `braid --check`, plus the
commit-range log, before answering.

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

Verdict: 4 findings
Tests: 1204 passed, 0 failed, 5 skipped (reused from last-verification.json at e122f46f258b03297e9f73e98f020e10292d2c98)

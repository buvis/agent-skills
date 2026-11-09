---
prd: docs/dev/project-management/prds/wip/00123-large-skipped-directories-may-resurface-v1.md
review: 1
date: 2026-10-29
head_sha: d8d1e3aff0e740c3cb0a029f064e5ec7997ca23f
codex_thread_id: 01a189cf-3b83-7963-8bd3-cd2655b66d5d
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: 4a029e37
  carl: b2d413e4
---

# Review: 00123-large-skipped-directories-may-resurface-v1

Diff range: `cfb04608e7856513a98ce16e6e62e157b9319b17..d8d1e3aff0e740c3cb0a029f064e5ec7997ca23f`

codex_rung_guard: not fired

## Review Summary

Reviewed: 2 completed tasks
PRDs checked: 00123-large-skipped-directories-may-resurface-v1

### Agent Status

- Alice: ✅ Available (consensus lens, legacy engine)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (codex, doubt lens D1-D5 + de-slop)
- Carl: ⚠️ Unavailable: gemini-run exit 1 on both the first dispatch and its one retry — backend `copilot`, model `gemini-3.8-flash`, stderr `You have exceeded your monthly quota`. Exit 1 is a one-off runtime failure, not the exit-4 permanent-configuration case, so Carl is NOT latched for the batch.
- Eve: ⏸️ Disabled: `doubt_reviewer: codex` and no codex-implemented task, so the codex doubt-roster guard did not fire.

### Staging and gate notes

- `autopilot review-stage` staged cleanly: `errors: []`, `pack: ok`.
- Bob's prompt was rebuilt in the inlined shape (129 KB) before dispatch, overwriting the staged render. His dispatch row's `prompt_bytes` therefore understates what codex received; the row was not reopened.
- **Test gate provenance (fail loud).** `review-stage` reported `Tests: counts unavailable (suite run this cycle, exit 0, no PASS/FAIL/SKIP/EXIT summary line)`, but its own gate log does carry one: `docs/dev/tmp/gate-20261029-c1.log:208` reads `========== 4226 passed, 9 skipped, 236 warnings in 419.56s (0:06:59) ===========`. The counts in the `Tests:` line below were read from that log rather than re-running a seven-minute suite. The parser miss in `review-stage`'s counts extraction is a tooling defect in the autopilot pack, outside this PRD's scope; it is recorded here, not fixed here.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/3] | 🟡 | Phase 0 test is 54 lines (mechanical facts: line 383), over the 50-line limit. Most of that is a 20-line docstring that now describes pre-fix behavior. Cut the docstring to a short statement of the flow and outcome, or move the re-record step into a helper. | skills/glean/scripts/test_glean.py:383 | 1 | ALICE, BLAKE, BOB |
| R2 | [2/3] | 🟡 | SKILL.md still documents only `sha256` in two places. The schema line is `{path, verdict, decided, sha256?, note?}` and the verdict table says skip "Comes back when sha256 changes". The PRD requires documented volatile-entry requirements to be updated alongside validation. Add `count_mtime?` to the schema line and "or count_mtime" to the skip/machine rows. | skills/glean/SKILL.md:35 | 2 | ALICE, BLAKE |
| R3 | [2/3] | ⚪ | The new `f.stat()` over every file in an over-cap directory is unguarded. A file that vanishes between `rglob` and `stat` raises FileNotFoundError out of `describe`, while `prescreen` catches OSError. The small-directory `elif` branch already has the same pre-existing exposure, so this is consistent with the current code. Consider guarding both. | skills/glean/scripts/glean.py:156 | 2 | ALICE, BLAKE |
| R4 | [1/3] | 🟡 | The test name `test_skip_on_dir_resurfaces_forever_once_grown_past_max_dir_files` and its docstring ("Under the present code ... expected to FAIL") describe the defect. The final assertion now requires the directory to settle, so the name says the opposite of what the test checks. Rename it to something like `test_skip_on_dir_settles_after_redecide_once_grown_past_max_dir_files` and reword the docstring in the post-fix tense. | skills/glean/scripts/test_glean.py:383 | 1 | ALICE |
| R5 | [1/3] | 🟡 | The reproduction does not match the PRD's suspected defect. Before the fix an over-cap directory could not carry a valid saved skip/machine entry, because load_ledgers rejected entries without sha256. So "a saved verdict resurfaces repeatedly" was unreachable as the PRD worded it. The test works around this by recording a sha256 while the directory was small and then growing it. That makes the confirmation indirect: the real defect was "cannot record a verdict", not "recorded verdict resurfaces". The PRD's premise was only partly confirmed, and this is not stated anywhere. | skills/glean/scripts/test_glean.py:383 | 1 | BLAKE |
| R6 | [1/3] | 🟡 | CHANGELOG.md has no Unreleased entry for this user-visible fix. The global changelog rule requires one for `fix` commits. | CHANGELOG.md | 2 | BLAKE |
| R7 | [1/3] | 🟡 | Phase 0 no longer performs the required second unchanged scan with the original ledger entry; it re-records first, testing Phase 1 instead. Add the second original-entry scan before re-recording, and distinguish the recorded pre-fix observation from the fixed workflow. | skills/glean/scripts/test_glean.py:383 | 1 | BOB |
| R8 | [1/3] | ⚪ | The shipped comparison at glean.py:207 (`not any(c.get(k) and c[k] == entry.get(k) ...)`) differs from the design doc's "verbatim" `c.get("count_mtime", c.get("sha256")) != entry.get(...)`. The shipped form is safer, because it never lets None equal None for a candidate with no fingerprint. The deferred-log entry claims the implementation "matches the design doc contract verbatim", which is inaccurate. Correct that wording; no code change needed. | skills/glean/scripts/glean.py:207 | 2 | ALICE |
| R9 | [1/3] | ⚪ | The fail-first replay shows 6 touched tests pass against the pre-change code. They are `test_stable_entry_needs_no_fingerprint`, `test_small_dir_sha256_entry_behaves_as_before`, the `n=5` and `n=200` cases of `test_dir_fingerprint_switches_from_sha256_to_count_mtime_only_past_cap`, and the `sha256` case of `test_volatile_entry_resurfaces_when_candidate_has_no_fingerprint`. They are deliberate PRD-required preservation guards (small-directory hashing, stable verdicts, the no-fingerprint candidate never settling), so I do not count them as tautological. They add no regression pin for this change. | skills/glean/scripts/test_glean.py:736 | 2 | ALICE, mech-check |
| R10 | [1/3] | ⚪ | Whole-second truncation (`int(st_mtime)`) means an edit within the same second as the previous newest mtime goes unnoticed. This is the known weakness the PRD accepts, but SKILL.md does not tell operators that count_mtime is weaker than sha256. The PRD says to document "weaker fingerprints". | skills/glean/SKILL.md:55 | 2 | BLAKE |
| R11 | [1/3] | ⚪ | The comparison `any(c.get(k) and c[k] == entry.get(k) ...)` is correct. Legacy sha256 entries stay readable and resurface once when a directory crosses the cap. This is covered by tests/test_glean.py:575. Never verdicts, check-staged, and the "prescreen capped" hint are untouched (skills/glean/scripts/glean.py:153-155, 228-264). | skills/glean/scripts/glean.py:207 | 2 | BLAKE |
| R12 | [1/3] | ⚪ | The supplied replay identifies six parameter cases that pass against pre-change code, so they do not pin this change. These cover existing behavior explicitly required to remain unchanged; retain them as compatibility coverage rather than rewriting them solely to fail against base. | skills/glean/scripts/test_glean.py:520 | 2 | BOB |

### Mechanical check absorption

The context file's one `[MECH]` line (fail-first replay: 6 touched tests pass against pre-change code, `skills/glean/scripts/test_glean.py`) names the same file and the same tests as R9, so `mech-check` was appended to R9's finders rather than added as a separate row. R12 is Bob's wording of the same replay fact. The tautological-shape detector produced no `[MECH]` line.

## Alice

Consensus lens, legacy engine, implementation-aware. Six findings (3 🟡, 3 ⚪), listed as R1, R2, R3, R4, R8, R9 above.

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
R12: fail
R13: pass

## Blake

Blind lens, PRD-only prompt, located the code himself. Seven findings (4 🟡, 3 ⚪), listed as R1, R2, R3, R5, R6, R10, R11 above.

Checks he ran: `uv run pytest skills/glean/scripts/test_glean.py` → 65 passed; `validate_skill.py skills/glean` → valid. He did not run `braid --check` or the full suite.

B1: pass
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

Doubt lens (codex, static-only sandbox) with the de-slop pass. FIX: R7, R1. VERIFY: (none). KNOWN: R12.

Because his VERIFY bucket is empty, no verification-check queue file was written for this cycle, and no finding is routed to verification.

R1: pass
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: pass
R11: pass
R12: fail
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

⚠️ Unavailable: Copilot monthly quota exhausted on both the dispatch and its one retry (exit 1, `gemini-3.8-flash`). No output file was published and none was consolidated.

Verdict: 12 findings
Tests: 4226 passed, 9 skipped, 0 failed (suite run this cycle)

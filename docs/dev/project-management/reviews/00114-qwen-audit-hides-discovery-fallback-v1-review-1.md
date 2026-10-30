---
head_sha: c0be898
reviewers: alice, blake, eve, bob
---

## Alice

**00114-qwen-audit-hides-discovery-fallback-v1-c1**
🟡 Tautological assert: the card's first line is always the title "# Qwen Utilization Report Card", so `"gita" not in card.splitlines()[0]` can never fail. The note is rendered on the "Generated:" line, which is line index 2. Assert against the Generated line (or the whole card) so a leaked note would be caught. | File: skills/audit-qwen/scripts/test_audit_qwen.py:198
🟡 Either-or hedge assert: `startswith(...) or (... in ...)`. The second clause is weaker than the first, and the first is already enough. | File: skills/audit-qwen/scripts/test_audit_qwen.py:222
🟡 PRD gap: the PRD asks to verify the fallback note appears in the final report. All new note tests call only `discover_repos()` and check the returned tuple. No test runs `main()` with stubbed gita and no `--repo`. | File: skills/audit-qwen/scripts/test_audit_qwen.py:67
⚪ Stale test name: `..._is_silent_bug_without_fix` describes the pre-fix state, but the test now asserts the fixed behavior. | File: skills/audit-qwen/scripts/test_audit_qwen.py:67
⚪ Test isolation: `test_discover_repos_calls_gita_freeze_exactly` does not patch `Path.home`, so `discover_repos` probes the real `~/.claude`. | File: skills/audit-qwen/scripts/test_audit_qwen.py:163
Rubric: R1 fail, R2 fail, R3 pass, R4 pass, R6-R13 pass. Production change judged correct and minimal.

## Blake

**00114-qwen-audit-hides-discovery-fallback-v1-c1**
🟡 The spec says the fallback note must appear in the final report, but no test exercises `main()` or `render()` with a faked successful-empty or successful-malformed gita. | File: skills/audit-qwen/scripts/test_audit_qwen.py:370
🟡 `test_main_with_explicit_repo_skips_discovery_and_carries_no_note` asserts against line 0, the report title, so the assertion can never fail. | File: skills/audit-qwen/scripts/test_audit_qwen.py:508
⚪ `test_main_with_existing_output_parent_still_writes_normally` ends in an either-or assert whose second clause subsumes the first. | File: skills/audit-qwen/scripts/test_audit_qwen.py:549
⚪ Test name `..._is_silent_bug_without_fix` describes pre-fix state; its comment is stale. | File: skills/audit-qwen/scripts/test_audit_qwen.py:392
⚪ The fallback note says "scanning the working directory" even when no root is eligible; cosmetic, and it reuses the pre-existing wording. | File: skills/audit-qwen/scripts/audit_qwen.py:269
⚪ `mkdir(parents=True, exist_ok=True)` still tracebacks when the parent path is a file or unwritable; the spec only asks for creating missing parents. | File: skills/audit-qwen/scripts/audit_qwen.py:591
⚪ `test_discover_repos_calls_gita_freeze_exactly` pins subprocess kwargs and is beyond the spec's list. | File: skills/audit-qwen/scripts/test_audit_qwen.py:459
Rubric: B1-B19 all pass. He states he did not re-run the new tests against pre-fix code, so he did not verify fail-first himself.

## Eve

**00114-qwen-audit-hides-discovery-fallback-v1-c1**
FIX (6): the explicit-repo control asserts against the title line and pins nothing (test_audit_qwen.py:527); the four fallback-note tests assert only `note != ""`, which any string satisfies, instead of the no-usable-rows wording (410, 429, 442, 455); no test pins the note reaching the `Generated:` line through `main()` (new block 369-527); stale test name and two noise comments (396-402, 421-423); the existing-parent test duplicates `test_main_writes_output_file_and_exits_zero` and should be deleted (543-553); `test_discover_repos_calls_gita_freeze_exactly` pins implementation kwargs and leaves `Path.home` unpatched (492-509).
VERIFY (0): none.
KNOWN (3): comma-containing gita paths stay truncated (PRD puts this out of scope); all three notes share the "scanning the working directory" wording, so rewording is a separate surgical change; `mkdir`/`write_text` still traceback on permission errors (PRD Risks limits the change to missing parents).
Rubric: D1 pass, D2 pass, D3 pass, D4 pass, D5 pass.
She verified fail-first mechanically against a base-revision scratch copy: 5 new tests fail on base, 6 declared controls pass on base. She also ran the gate (37 passed), the full suite, `validate_skill.py` and `braid --check` (0 drift).

## Bob

**00114-qwen-audit-hides-discovery-fallback-v1-c1**
The `codex-run.sh` CLI lane failed on both attempts with `sandbox_apply: Operation not permitted` before any file was read, establishing no finding. Per the lane's unavailable-codex rule the rendered codex prompt went to a read-tool subagent, which produced this review:
🟡 Either-or hedge assert reduces to a substring check, so the reject case for always-mkdir-and-clobber over-fixes is not pinned. | File: skills/audit-qwen/scripts/test_audit_qwen.py
🟡 `test_main_with_existing_output_parent_still_writes_normally` duplicates `test_main_writes_output_file_and_exits_zero` and cannot distinguish the fix from the old code. | File: skills/audit-qwen/scripts/test_audit_qwen.py
⚪ `test_discover_repos_calls_gita_freeze_exactly` does not monkeypatch `aq.Path.home`, so it stats the operator's real `~/.claude` tree. | File: skills/audit-qwen/scripts/test_audit_qwen.py
⚪ The new note promises "scanning the working directory" even when the cwd carries no autopilot dir. | File: skills/audit-qwen/scripts/audit_qwen.py
⚪ Cannot statically verify the gate run. | File: N/A
Rubric: R1 pass, R2 fail, R3-R13 pass. D1-D5 pass. Confirmed the guard sits after row parsing and before the fallback loop, never overwrites the non-zero or OSError notes, and that `mkdir` is inside the `--output` branch only.

## Carl

**00114-qwen-audit-hides-discovery-fallback-v1-c1**
MISSING, not passing. `gemini-run.sh` exited 1 on the copilot backend: "You have exceeded your monthly quota". A re-dispatch of the same backend buys nothing, so this lens did not report.

Verdict: converged
Tests: 4145 passed, 0 failed, 9 skipped (fast-track batch suite)
codex_rung_guard: not fired

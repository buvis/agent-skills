# Split note: 00044-windows-ci-junction-claim-v1.md
planned=9 prd_tasks=6 expansion=1.50 reasons=module_drift

## . (UNLISTED)

- 8 Correct README's Windows coverage paragraph: README.md
- 9 Add CHANGELOG entries for the Windows failure-cause fixes: CHANGELOG.md

## docs/dev/project-management/audit-results (UNLISTED)

- 7 Record Windows closeout evidence from the full local suite run: docs/dev/project-management/audit-results/repository-closeout-execution.md

## skills/create-prd/scripts (UNLISTED)

- 2 W2: Fix ground_prd citation regex and exclusion glob for Windows paths (P1, P2): skills/create-prd/scripts/ground_prd.py, skills/create-prd/scripts/test_ground_prd.py

## skills/glean/scripts (UNLISTED)

- 4 W4: Fix glean report path separators, purge-devtmp TAB/CR handling, and sweep-fix os.geteuid collection errors (G1, U1, U2, S1): skills/glean/scripts/glean.py, skills/glean/scripts/test_glean.py

## skills/purge-devtmp/scripts (UNLISTED)

- 4 W4: Fix glean report path separators, purge-devtmp TAB/CR handling, and sweep-fix os.geteuid collection errors (G1, U1, U2, S1): skills/purge-devtmp/scripts/purge_devtmp.py, skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py

## skills/use-qwen/scripts (UNLISTED)

- 5 W5: Fix use-qwen eval_harness byte-count, fixture-text, cwd-form, and report-path failures (Q1, Q2, Q3, Q7): skills/use-qwen/scripts/eval_harness_fixtures.py, skills/use-qwen/scripts/test_eval_events.py, skills/use-qwen/scripts/test_eval_evidence.py, skills/use-qwen/scripts/test_eval_gates.py, skills/use-qwen/scripts/test_report.py
- 6 W7: Fix use-qwen vetting cumulative-deadline accounting across segments on Windows (Q8): skills/use-qwen/scripts/test_run_eval_vet.py

## skills/use-qwen/scripts/eval_harness (UNLISTED)

- 5 W5: Fix use-qwen eval_harness byte-count, fixture-text, cwd-form, and report-path failures (Q1, Q2, Q3, Q7): skills/use-qwen/scripts/eval_harness/events.py, skills/use-qwen/scripts/eval_harness/report.py
- 6 W7: Fix use-qwen vetting cumulative-deadline accounting across segments on Windows (Q8): skills/use-qwen/scripts/eval_harness/vetting.py

## src/agent_skills_braid (UNLISTED)

- 1 W1: Fix braid Windows link-identity and chmod-semantics failures (B1, B2): src/agent_skills_braid/cli.py

## tests (UNLISTED)

- 1 W1: Fix braid Windows link-identity and chmod-semantics failures (B1, B2): tests/test_braid.py, tests/test_braid_check.py

## skills/distil-memory/scripts (listed)

- 3 W3: Fix distil-memory docket diagnosis and atomic-write newline translation on Windows (D1, D2, D3): skills/distil-memory/scripts/docket.py, skills/distil-memory/scripts/write.py, skills/distil-memory/scripts/test_docket_refusals.py, skills/distil-memory/scripts/test_docket_unpublished.py, skills/distil-memory/scripts/test_write_atomicity.py, skills/distil-memory/scripts/test_write_crash_safety.py

## skills/sweep-fix/scripts (listed)

- 4 W4: Fix glean report path separators, purge-devtmp TAB/CR handling, and sweep-fix os.geteuid collection errors (G1, U1, U2, S1): skills/sweep-fix/scripts/test_sweep_enumerate.py, skills/sweep-fix/scripts/test_sweep_main_setup_errors.py

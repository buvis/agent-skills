# Split note: 00044-windows-ci-junction-claim-v1.md
planned=14 prd_tasks=8 expansion=1.75 reasons=module_drift

## . (UNLISTED)

- 1 W1: fix braid Windows junction/symlink identity drift and add a mode-preservation regression (B1, B2): CHANGELOG.md
- 2 W2: fix ground_prd citation regex and ripgrep exclusion glob for Windows paths (P1, P2): CHANGELOG.md
- 3 W3a: fix distil-memory docket directory diagnosis and malformed-id rendering (D1, D2): CHANGELOG.md
- 4 W3b: fix distil-memory write.py atomic-write newline translation (D3): CHANGELOG.md
- 5 W4a: fix glean report ids to use portable slash-form separators (G1): CHANGELOG.md
- 6 W4b: fix purge-devtmp unsafe-filename guard test seam and CRLF manifest rewrite (U1, U2): CHANGELOG.md
- 7 W4c: replace sweep-fix os.geteuid() root-skip with the portable deny_access fixture (S1): CHANGELOG.md
- 8 W5a: fix use-qwen test_eval_events.py fixture's translated-newline byte mismatch (Q1): CHANGELOG.md
- 9 W5b: fix use-qwen fixture-repo authored bytes to control LF/CRLF explicitly (Q2): CHANGELOG.md
- 10 W5c: fix use-qwen cwd comparisons for the Git-Bash-vs-native path form (Q3): CHANGELOG.md
- 11 W5d: fix use-qwen report.py test's hand-built captured-output string to use Path joins (Q7): CHANGELOG.md
- 14 Correct the Windows command and coverage paragraph in README.md: README.md, CHANGELOG.md

## docs/dev/project-management/audit-results (UNLISTED)

- 13 Record Windows closeout evidence from the full local suite run: docs/dev/project-management/audit-results/repository-closeout-execution.md

## skills/create-prd/scripts (listed)

- 2 W2: fix ground_prd citation regex and ripgrep exclusion glob for Windows paths (P1, P2): skills/create-prd/scripts/ground_prd.py, skills/create-prd/scripts/test_ground_prd.py

## skills/distil-memory/scripts (listed)

- 3 W3a: fix distil-memory docket directory diagnosis and malformed-id rendering (D1, D2): skills/distil-memory/scripts/docket.py, skills/distil-memory/scripts/test_docket_refusals.py, skills/distil-memory/scripts/test_docket_unpublished.py
- 4 W3b: fix distil-memory write.py atomic-write newline translation (D3): skills/distil-memory/scripts/write.py, skills/distil-memory/scripts/test_write_atomicity.py, skills/distil-memory/scripts/test_write_crash_safety.py

## skills/glean/scripts (listed)

- 5 W4a: fix glean report ids to use portable slash-form separators (G1): skills/glean/scripts/glean.py, skills/glean/scripts/test_glean.py

## skills/purge-devtmp/scripts (listed)

- 6 W4b: fix purge-devtmp unsafe-filename guard test seam and CRLF manifest rewrite (U1, U2): skills/purge-devtmp/scripts/purge_devtmp.py, skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py

## skills/sweep-fix/scripts (listed)

- 7 W4c: replace sweep-fix os.geteuid() root-skip with the portable deny_access fixture (S1): skills/sweep-fix/scripts/test_sweep_enumerate.py, skills/sweep-fix/scripts/test_sweep_main_setup_errors.py

## skills/use-qwen/scripts (listed)

- 8 W5a: fix use-qwen test_eval_events.py fixture's translated-newline byte mismatch (Q1): skills/use-qwen/scripts/test_eval_events.py
- 9 W5b: fix use-qwen fixture-repo authored bytes to control LF/CRLF explicitly (Q2): skills/use-qwen/scripts/eval_harness_fixtures.py, skills/use-qwen/scripts/test_eval_evidence.py, skills/use-qwen/scripts/test_run_eval_vet.py
- 10 W5c: fix use-qwen cwd comparisons for the Git-Bash-vs-native path form (Q3): skills/use-qwen/scripts/eval_harness_run_helpers.py, skills/use-qwen/scripts/test_eval_gates.py
- 11 W5d: fix use-qwen report.py test's hand-built captured-output string to use Path joins (Q7): skills/use-qwen/scripts/test_report.py
- 12 W7: add a deterministic cumulative-deadline regression for use-qwen vetting (Q8, conditional): skills/use-qwen/scripts/test_run_eval_vet.py

## src/agent_skills_braid (listed)

- 1 W1: fix braid Windows junction/symlink identity drift and add a mode-preservation regression (B1, B2): src/agent_skills_braid/cli.py

## tests (listed)

- 1 W1: fix braid Windows junction/symlink identity drift and add a mode-preservation regression (B1, B2): tests/test_braid.py

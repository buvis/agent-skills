# Split note: 00044-windows-ci-junction-claim-v1.md
planned=6 prd_tasks=6 expansion=1.00 reasons=module_drift

## . (UNLISTED)

- 1 Provision the Windows CI job and complete Python collection: .gitattributes, pyproject.toml
- 2 Port host-assumption fixtures to a rootdir conftest.py: conftest.py
- 6 Correct the Windows command and coverage paragraph in README: README.md, CHANGELOG.md

## skills/brush/scripts (UNLISTED)

- 3 Fix brush relative-path identity for Windows: skills/brush/scripts/trash_untracked.py, skills/brush/scripts/test_brush_scripts.py

## .github/workflows (listed)

- 1 Provision the Windows CI job and complete Python collection: .github/workflows/ci.yml

## skills/distil-memory/scripts (listed)

- 2 Port host-assumption fixtures to a rootdir conftest.py: skills/distil-memory/scripts/test_dedup.py, skills/distil-memory/scripts/test_dedup_classify.py, skills/distil-memory/scripts/test_docket_refusals.py, skills/distil-memory/scripts/test_write_refusals.py, skills/distil-memory/scripts/test_funnel_main.py, skills/distil-memory/scripts/test_funnel_distil_publication.py
- 4 Make memory publication portable without replacing an existing directory: skills/distil-memory/scripts/proposal.py, skills/distil-memory/scripts/test_proposal_publication.py, skills/distil-memory/scripts/test_funnel_distil_publication.py

## skills/explain-interactively/scripts (listed)

- 2 Port host-assumption fixtures to a rootdir conftest.py: skills/explain-interactively/scripts/test_build.py

## skills/review-prd-backlog/scripts (listed)

- 2 Port host-assumption fixtures to a rootdir conftest.py: skills/review-prd-backlog/scripts/test_check_links.py

## skills/survey/scripts (listed)

- 2 Port host-assumption fixtures to a rootdir conftest.py: skills/survey/scripts/test_survey.py

## skills/sweep-fix/scripts (listed)

- 2 Port host-assumption fixtures to a rootdir conftest.py: skills/sweep-fix/scripts/test_sweep_resolvers.py, skills/sweep-fix/scripts/test_sweep_scan.py

## (no files declared)

- 5 Prove the full Python suite passes on native Windows and Ubuntu at the changed commit

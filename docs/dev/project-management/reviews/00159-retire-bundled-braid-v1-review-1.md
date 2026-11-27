---
head_sha: 1b0696940035effe617a56aa10fc6f9189f0321f
reviewers: alice, blake, eve, bob, carl
---

# Review 1: 00159 retire the bundled braid package (fast-track lane, 1 card)

Card 00159-retire-bundled-braid-v1-c1 ran the fast-track roster over 5ec3b1c..b2e9ec9, one rework round (1b06969) and an Eve delta review. Exit action: commit. Item report: docs/dev/tmp/00159-retire-bundled-braid-v1-c1-fast-track-review.md.

PRD task 3 (close held PRD 00111) ran outside the card: gems braid reproduced both 00111 defects against temp roots; filed as buvis/gems#300; 00111 moved to done/ with a closing note (commit b2e9ec9). Eve confirmed the note names 00159 and gems#300.

## Alice

**00159-retire-bundled-braid-v1-c1**
- LOW: `"bin" not in install` is a bare substring check (tests/test_retire_bundled_braid.py). Resolved in rework (now `"bin/"`).
- LOW: tooling test pins exact lint and ruff settings. Resolved in rework (presence only).
- R1-R13: pass.

## Blake

**00159-retire-bundled-braid-v1-c1**
- LOW: the PRD acceptance rg returned hits in the new test file (B15 fail). Resolved in rework; the rg prints nothing now.
- LOW: tests/test_readme_windows.py deleted beyond the listed inputs. Accepted: it pinned README text this PRD removes.
- LOW: README Windows-CI paragraph deleted beyond the literal range. Accepted: it described the deleted braid's junction tests.
- LOW: AGENTS.md dropped "for braid" from the pytest sentence. Accepted: the braid tests are gone.

## Eve

**00159-retire-bundled-braid-v1-c1** (roster)
- MEDIUM: README said braid loads .braidignore from "the machine-local config directory". Resolved: now names `policies` in buvis-braid.yaml and `--policy` (checked against gems braid 0.21.0 engine.py).
- MEDIUM: changelog test bound to [Unreleased]. Resolved.
- MEDIUM: acceptance rg hits in the test file. Resolved.
- LOW: stale ci.yml comment, weak tooling test, `hatchling` assert that cannot fail, broad `"bin"` assert. All resolved.
- KNOWN: README text is PRD-verbatim (bare paths, no `sources+:` hint); .gitignore keeps build/dist entries; README no longer mentions windows-latest CI.

**00159-retire-bundled-braid-v1-c1** (delta over b2e9ec9..1b06969)
- All 8 prior findings resolved.
- LOW (open): test line 112 cannot fail after line 111 subscripts tool.ruff.
- LOW (open): two test names are stale after the rework (test_changelog_unreleased_records_the_removal, test_pyproject_keeps_dev_tooling_unchanged).
- LOW (open): README .braidignore paragraph not rewrapped (one 119-column line).
- LOW (open): half-applied constant extraction for the legacy strings in the test file.
- VERIFY (open): the windows CI lane has not run the new test file; check after the branch is pushed.
- D1-D5: pass.

## Bob

**00159-retire-bundled-braid-v1-c1**
- First run could not read its inputs (Seatbelt shell init failure); retried with context and diff inlined.
- HIGH: the new test file carries the retired strings, so the PRD acceptance rg finds matches. Victor confirmed. Resolved in rework.
- MEDIUM: tooling test passes before the change. Resolved.
- MEDIUM: repo scan swallowed read errors and parsed quoted git paths. Resolved (`git ls-files -z`, no OSError swallow; Eve proved it fails on a non-UTF-8 file with a legacy string).
- LOW: `uv lock --check` not in the gate results. Checked: exit 0.
- LOW: `~/.agents/bin/braid` dangles until home PRD 00183. Out of scope; `~/.agents/bin` does not exist on this machine.
- D1-D5: pass.

## Carl

**00159-retire-bundled-braid-v1-c1**
- No issues found (gemini-3.8-flash via copilot). R1-R13: pass.

Verdict: 4 findings
Tests: 4895 passed, 0 failed, 12 skipped (fast-track batch suite)
codex_rung_guard: not fired

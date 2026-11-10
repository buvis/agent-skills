# PRD 00135 preparation evidence

Task 1 only. Checked at 2026-11-10T00:02:24Z. No tag, release, branch, commit,
or workflow state was changed. Publication remains pending Task 2 and its
immediate fresh checks. No new tests were added or run for this publication task.

Runtime identity: coordinator-provided observed turn-context evidence identifies
model `gpt-6.1-sol`, effort `medium`, session
`01a1c2c2-ca13-7c02-92da-97ebbaf3858b`. This reports observed runtime metadata,
not an independently inferred backend identity. Logical task tier: sonnet.

## Current published-master gate

Read-only commands and results:

```text
gh api repos/buvis/agent-skills/git/ref/heads/master --jq .object.sha
99f3c9cd0e0be8172e127559769e75044b0dafab

gh run list --repo buvis/agent-skills --workflow ci.yml --branch master --limit 1 --json databaseId,headSha,status,conclusion,url
databaseId: 42716763283
headSha: 99f3c9cd0e0be8172e127559769e75044b0dafab
status: completed
conclusion: success
url: https://github.com/buvis/agent-skills/actions/runs/42716763283

gh run view 42716763283 --repo buvis/agent-skills --json headSha,status,conclusion,jobs,url
headSha: 99f3c9cd0e0be8172e127559769e75044b0dafab
status: completed
conclusion: success
```

All eight jobs completed successfully; every returned step also concluded
`success` (none skipped, neutral, cancelled, or failed):

| Job | Job ID | Conclusion |
| --- | --- | --- |
| lint | 129500218054 | success |
| node | 129500218419 | success |
| test (3.10) | 129500218424 | success |
| test (3.13) | 129500218448 | success |
| windows | 129500218508 | success |
| skill-integrations (ubuntu-latest) | 129500218621 | success |
| skill-integrations (windows-latest) | 129500218665 | success |
| shell | 129500218698 | success |

The Windows capability probe and full Python 3.13 suite both passed. Windows
integration tests passed separately. The Windows job finished at
2026-11-09T23:16:04Z.

Inspected `.github/workflows/ci.yml` at the exact green SHA using `git show`.
Its blob is `87421424848ad2d41436de49110f04e5eaa27243`, matching GitHub's
contents API for that exact SHA (9255 bytes). The workflow has six job
definitions expanding to the eight observed jobs: Ubuntu tests on Python
3.10/3.13, Ubuntu/Windows integration tests, Windows full suite, shell suites,
lint, and Node tests. There is no `continue-on-error`, job/step `if:` gate,
path filter, matrix exclusion, or fail-open test command. `fail-fast: false`
retains matrix coverage. Shell-suite and skill-validator failure aggregation
exits with its accumulated status; Node template comparison exits 1 on drift.
Windows capabilities exit 1 on missing capabilities. No gate was modified.

Matching-blob verification commands:

```text
gh api 'repos/buvis/agent-skills/contents/.github/workflows/ci.yml?ref=99f3c9cd0e0be8172e127559769e75044b0dafab' --jq '{sha,size,path}'
{"path":".github/workflows/ci.yml","sha":"87421424848ad2d41436de49110f04e5eaa27243","size":9255}
git rev-parse 99f3c9cd0e0be8172e127559769e75044b0dafab:.github/workflows/ci.yml
87421424848ad2d41436de49110f04e5eaa27243
```

## Preserved tag and existing publication state

```text
git rev-parse 'v0.1.0^{commit}'
f4f2de0aa55b9c53a531b1b280a4339e74aebc64
git cat-file -t v0.1.0
commit

git ls-remote origin refs/heads/master 'refs/tags/v0.1.0*' 'refs/tags/v0.2.0*'
99f3c9cd0e0be8172e127559769e75044b0dafab refs/heads/master
f2b82d8372cceab04790e4fb183651a63de1e91d refs/tags/v0.2.0

gh api repos/buvis/agent-skills/releases
[]
gh api repos/buvis/agent-skills/releases/latest --jq '{tag_name,html_url}'
HTTP 404 Not Found
```

The local lightweight v0.1.0 tag has the required exact target. The live remote
control branch and newer v0.2.0 tag resolve, while remote v0.1.0 is absent.
There are no existing release entries and no Latest release. No conflicting
publication state was found. Preserve v0.2.0 and release ordering by publishing
only v0.1.0, using `--verify-tag --latest=false`, without branch pushes,
force updates, assets, or another version. These are pending actions, not results.

## Notes source and exact prepared text

`git show v0.1.0:CHANGELOG.md` is the sole feature source. Its Git blob is
`b72c63a890227ca85d8b87f7f194267e389fd102`, with 634 lines. Version 0.1.0
starts at line 10, dated 2026-10-18; Added starts at line 12, Changed at 281,
Removed at 303, and Fixed at 319. Source inspection used bounded `sed -n`
ranges rather than relying on a truncated whole-file display. Highlight
grounding: intake and grounding lines 14–18; new workflows and Kiro lines
19–54 and session handoff lines 54–57; Braid composition and junctions lines
201–209; portable skills and plugin dependencies lines 210–268 and 298–301;
retired forks lines 305–317; Braid and memory/Qwen fixes in Fixed. No later
changelog version was used. The changelog's 2026-10-18 date is the historical
version date, not a claim that GitHub publication already occurred then.

Prepared file: `docs/dev/tmp/00135-v0.1.0-release-notes.md`.

```markdown
# v0.1.0 — historical release

This publishes the preserved v0.1.0 tag at `f4f2de0aa55b9c53a531b1b280a4339e74aebc64`. The tagged changelog dates version 0.1.0 to **2026-10-18**; this GitHub release is a later historical publication.

Highlights from that version's changelog:

- Braid composes skills from multiple sources, records owned links, supports Windows junctions, and adds Kiro enrollment.
- Requirements and PRD workflows support intake items, preserve their identifiers, and check draft grounding.
- New workflows include dotfiles checks (`glean`), transcript memory proposals and review (`distil-memory`), repository scaffolding, icon conversion, experiment capture, and session handoffs.
- Cross-agent skill publication adds portable helper paths and explicit plugin dependencies; unsupported Codex audit and storage forks are retired.
- Fixes improve Braid drift reporting and safe state writes, memory queue validation and atomic publication, and Qwen evaluation behavior on Windows.

Source: [CHANGELOG.md at v0.1.0](https://github.com/buvis/agent-skills/blob/f4f2de0aa55b9c53a531b1b280a4339e74aebc64/CHANGELOG.md), section `[0.1.0] - 2026-10-18`.

Publication is gated on successful CI for current published master. That later CI result does not establish that this historical tagged commit passed CI. This historical release is not designated Latest; the newer v0.2.0 tag remains unchanged.
```

## Preparation outcome

Task 1 prerequisites pass at the recorded observation time. No preparation
blocker remains. Task 2 must re-read current remote master, latest CI and every
job/step, and tag/release state immediately before external actions. This report
does not authorize bypassing stale or failed checks. No implementation review
was performed in this worker session.

Local verification: `git diff --check` passed. A direct text comparison verified
the report's embedded notes equal the prepared file exactly, including its final
newline; neither artifact contains personal absolute paths. Only the two
allowlisted preparation artifacts were edited by this worker. The coordinator
separately reported moving a pre-existing zero-byte root file named `-`
recoverably to `docs/dev/tmp/00135-preexisting-empty-dash` so mandatory
verification can run; this worker did not perform that move.

## Coordinator build checks

Before the preparation commit, `autopilot verify --gate-command 'uv run pytest'
--cycle 1` ran at baseline `1a2928a39a666ab0b42e92ebb7335eaf135ce9ba`:
4,394 passed, 1 failed, 12 skipped in 341.19 seconds. Failure:
`skills/distil-memory/scripts/test_funnel_distil.py::test_main_with_distil_reports_zero_rather_than_n_a_when_a_triage_that_answers_keeps_nobody`.
The preceding PRD 00134 build recorded this same failure before this PRD's work.
This PRD changes no production code; no unrelated test repair was attempted.
The verify CLI returned exit 1 and did not write a verification record because
its parser found no counts line. Counts above come from pytest's actual summary
in `docs/dev/tmp/gate-1a2928a.log`, not a synthesized verification record.

`uv run ruff check`, `uv run ruff format --check`, and `git diff --check`
passed. Plain `braid --check` could not find this host's source configuration;
`braid --check --source <repository-root>` passed with 164 current links and
zero drift. No skill was edited, so per-skill validation is inapplicable.

Host adaptation: substantive preparation/publication is delegated to an isolated
native sonnet-tier worker (`gpt-6.1-sol`, medium) instead of solo self-implementation.
Observed native runtime metadata confirms the selected model and effort. The
independent review route is Anthropic Opus/xhigh through the host driver. Source
route: solo coordinator; effective route: native worker under the explicit host
delegation requirement. No unsupported model provider or fallback was used.
All completion review lenses remain reserved for a fresh session. The code-owned
`suite_red` lane signal will escalate the finished build to full review.

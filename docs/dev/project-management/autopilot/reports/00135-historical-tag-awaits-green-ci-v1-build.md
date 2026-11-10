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

## Task 2: partial publication; Latest conflict blocks completion

Dispatch `cc16b1da`, same runtime and logical tier as Task 1. Observation window:
2026-11-10T00:10–00:11Z; final read-only inspection at 00:11:47Z.

Immediately before **each** external action, a read-only Python command invoked
the same `gh api` remote-master query, latest `gh run list`, and full `gh run
view` jobs/steps queries recorded above. Both checks returned remote master
`99f3c9cd0e0be8172e127559769e75044b0dafab` and CI run `42716763283`,
completed/success, with the exact set of all eight required jobs and every
returned step successful. Both checks re-read the exact workflow's GitHub
contents blob, `87421424848ad2d41436de49110f04e5eaa27243`, unchanged from
the inspected workflow. No job, Windows capability check, or gate was bypassed.

Before push, `git rev-parse 'v0.1.0^{commit}'` again returned the accepted
`f4f2de0aa55b9c53a531b1b280a4339e74aebc64`. Live `git ls-remote` showed
v0.1.0 absent, master unchanged, and v0.2.0 at
`f2b82d8372cceab04790e4fb183651a63de1e91d`. Release list remained `[]`.
Prepared notes were checked against the exact embedded text above and their
SHA-256 was computed:
`e8d19ba28db18b65bbc8ecfcf52ece574990ffe00491a1d5ffe13b178c2a511a`.

Exact external action and result (exit 0):

```text
git push origin refs/tags/v0.1.0:refs/tags/v0.1.0
To github.com:buvis/agent-skills.git
 * [new tag]         v0.1.0 -> v0.1.0
```

Before release creation, repeated all CI checks above, live remote-ref checks,
and `gh api repos/buvis/agent-skills/git/ref/tags/v0.1.0 --jq .object.sha`.
Both Git and GitHub independently returned the accepted v0.1.0 SHA. The
release list was still empty; notes SHA-256 was unchanged.

Exact external action and result (exit 0):

```text
gh release create v0.1.0 --repo buvis/agent-skills --verify-tag --latest=false --title 'v0.1.0 (historical)' --notes-file docs/dev/tmp/00135-v0.1.0-release-notes.md
https://github.com/buvis/agent-skills/releases/tag/v0.1.0
```

Final read-only results from `gh api repos/buvis/agent-skills/releases/tags/v0.1.0`:

```text
id: 439793234
tag_name: v0.1.0
name: v0.1.0 (historical)
html_url: https://github.com/buvis/agent-skills/releases/tag/v0.1.0
draft: false
prerelease: false
created_at: 2026-10-18T09:52:22Z
published_at: 2026-11-10T00:11:11Z
assets: []
body UTF-8 bytes == prepared notes bytes: true
```

The notes remain unchanged, sourced exclusively from tagged CHANGELOG blob
`b72c63a890227ca85d8b87f7f194267e389fd102`, version date 2026-10-18.
The actual GitHub publication occurred on 2026-11-10. Final `git ls-remote`
confirmed exactly:

```text
99f3c9cd0e0be8172e127559769e75044b0dafab refs/heads/master
f4f2de0aa55b9c53a531b1b280a4339e74aebc64 refs/tags/v0.1.0
f2b82d8372cceab04790e4fb183651a63de1e91d refs/tags/v0.2.0
```

**Blocking conflict:** despite the required explicit `--latest=false`, GitHub's
`gh api repos/buvis/agent-skills/releases/latest` now returns release
`439793234` (previously 404). GraphQL confirms this is Latest, not merely a
REST display ambiguity:

```text
gh api graphql -f query='query { repository(owner:"buvis", name:"agent-skills") { release(tagName:"v0.1.0") { name tagName isLatest isDraft isPrerelease url } } }'
{"data":{"repository":{"release":{"name":"v0.1.0 (historical)","tagName":"v0.1.0","isLatest":true,"isDraft":false,"isPrerelease":false,"url":"https://github.com/buvis/agent-skills/releases/tag/v0.1.0"}}}}
```

`gh release create --help` describes `--latest=false` as explicitly not setting
Latest. The observed server state conflicts with that requested behavior.
The final releases list contains only v0.1.0. No second release was created,
and no existing release was overwritten, edited, deleted, or converted into a
prerelease. No further external mutation was attempted after the conflict.
The no-Latest acceptance criterion therefore **does not pass**, and the notes'
statement that this release is not designated Latest is contradicted by the
server state. Do not mark Phase 1 or the PRD complete. Resolve the conflict
under a separately prepared, authorized recovery; preserve these observations.

No branch push, force update, asset upload, other-version publication, local
commit, workflow/state edit, new test, or completion review was performed by
this worker. Coordinator additions above were preserved.

## Persisted pause and prepared recovery choices

Coordinator persisted `phase: paused`, `next_phase: paused`, and
`pause_reason.site: publication_conflict` through statectl. Task 1 is completed;
Task 2 remains pending with its failed attempt and actual-model provenance.
Neither completion review nor finalization ran. The build is not complete.

An operator decision is indispensable because the PRD explicitly requires
stopping on publication conflicts and forbids Latest promotion, other versions,
or overwriting existing releases. No waiver is inferred from elapsed time.
Prepared choices, neither executed:

- Retain the release and explicitly accept a no-Latest exception. Recovery must
  also correct the notes' inaccurate designation sentence before verification.
- Remove only the GitHub release with `gh release delete v0.1.0 --repo
  buvis/agent-skills --yes`, without `--cleanup-tag`. This removes release
  `439793234` and its public release entry while retaining the exact remote tag.
  The complete notes remain preserved in this report. Publication then remains
  pending a solution that satisfies the no-Latest requirement.

No permission denial occurred. This pause follows an observed publication
conflict, not an automatic approval rejection. No corrective external action is
authorized until the operator resolves that conflict. Resume must re-inspect
the current release and CI state; it must not push or recreate the tag blindly.

The existing unrelated staged intake note is preserved outside this PRD's
commits. Pause closeout records only this PRD's evidence and telemetry; the
whole-store recorder is reserved for normal gate handoffs and would sweep that
unrelated staged note into its commit. This is a paused build, not a completed
build-to-review handoff. Existing worktrees/plans belong to other work and remain
untouched; live publication notes and temporary evidence remain available.

## Operator recovery: Latest conflict resolved (2026-11-10)

Interactive recovery session, Claude Code, model `claude-fable-5-2` (Anthropic).
This is an operator-authorized recovery action, not a Task 2 attempt. Task 2
stays pending for the build session to re-verify and close idempotently.

Cause: v0.1.0 was the only release in the repository. GitHub falls back to the
sole published release as Latest, whatever `--latest=false` requested.

Operator decision, asked and answered in this session: publish a release for
the existing remote v0.2.0 tag, marked Latest. This waives the PRD's "do not
publish other versions" rule for v0.2.0 only. The v0.1.0 release, both tags and
master were not edited, deleted, or moved.

Checks immediately before the action: remote master
`f90d5fa0f9966d1e673ed2c9cdc55067e1b8a763`; latest CI run
[42779216047](https://github.com/buvis/agent-skills/actions/runs/42779216047)
for that SHA completed with success; all eight jobs and every step succeeded.
Remote tags: v0.1.0 at `f4f2de0aa55b9c53a531b1b280a4339e74aebc64`, v0.2.0 at
`f2b82d8372cceab04790e4fb183651a63de1e91d`.

Notes: `docs/dev/tmp/00135-v0.2.0-release-notes.md`, the `[0.2.0] - 2026-10-25`
section of `git show v0.2.0:CHANGELOG.md`, plus a source link and a line that
says the GitHub publication is later than the version date.

External action and result (exit 0):

```text
gh release create v0.2.0 --repo buvis/agent-skills --verify-tag --latest --title v0.2.0 --notes-file docs/dev/tmp/00135-v0.2.0-release-notes.md
https://github.com/buvis/agent-skills/releases/tag/v0.2.0
```

Read-only results after the action:

```text
gh release list --repo buvis/agent-skills --json tagName,isLatest,isPrerelease,isDraft,publishedAt
v0.2.0 isLatest=true  isDraft=false isPrerelease=false publishedAt=2026-11-10T08:50:27Z
v0.1.0 isLatest=false isDraft=false isPrerelease=false publishedAt=2026-11-10T00:11:11Z

gh api repos/buvis/agent-skills/releases/latest
id 440124980, tag_name v0.2.0

git ls-remote origin refs/heads/master 'refs/tags/v*'
f90d5fa0f9966d1e673ed2c9cdc55067e1b8a763 refs/heads/master
f4f2de0aa55b9c53a531b1b280a4339e74aebc64 refs/tags/v0.1.0
f2b82d8372cceab04790e4fb183651a63de1e91d refs/tags/v0.2.0
```

The no-Latest criterion for v0.1.0 now holds, and the v0.1.0 notes' statement
that it is not designated Latest is true. Release 439793234 is unchanged.

For the review session: the v0.2.0 release is an Anthropic-model action outside
the task attempts. Route review on the recorded attempts, and judge this action
against the operator waiver above.

The pause is cleared through statectl: `phase` and `next_phase` are `build`,
`pause_reason` is deleted. Local master is merged with `origin/master` (merge,
not rebase, so `work_start_sha` stays valid).

## Task 2: final read-only verification after operator recovery

Verified at 2026-11-10T18:57:47+00:00. Task 2 acceptance now passes under the recorded
v0.2.0 operator waiver. This verification preserved the failed attempt above
and performed no release/tag creation, edit, deletion, push, commit, workflow
change, or task-state mutation. Completion review was not run. Only this report
was edited by this worker.

Runtime provenance: isolated native host worker `/root/verify_publication`.
Coordinator-provided observed raw-log evidence identifies provider OpenAI,
model `gpt-6.1-sol`, effort `medium`, worker session
`01a1c6d1-8015-75d3-be76-4141ab45f9a6`, and parent thread
`01a1c6d0-e27d-71e3-bebc-4eb55f064391`. Evidence source:
`rollout-2026-11-10T19-56-21-01a1c6d1-8015-75d3-be76-4141ab45f9a6.jsonl`,
line 1 (worker/provider/parent) and line 10 (`turn_context` model/effort).
This reports observed coordinator evidence, not an inferred backend identity.
The host-provided independent review route is Anthropic Opus/xhigh; it was not
invoked by this worker.

Commands below were executed read-only and returned exit 0. Run-view output is
projected to job IDs and exhaustive step-success counts after checking the
exact eight-job set and every returned step's status/conclusion. Release REST
output is projected to publication fields, excluding account profile metadata.

```text
$ gh api repos/buvis/agent-skills/git/ref/heads/master --jq .object.sha
exit: 0
3af575327b5526c0fb45ab3f3e249faaabe5c26d
$ gh run list --repo buvis/agent-skills --workflow ci.yml --branch master --limit 1 --json databaseId,headSha,status,conclusion,url
exit: 0
[
  {
    "conclusion": "success",
    "databaseId": 42819166960,
    "headSha": "3af575327b5526c0fb45ab3f3e249faaabe5c26d",
    "status": "completed",
    "url": "https://github.com/buvis/agent-skills/actions/runs/42819166960"
  }
]
$ gh run view 42819166960 --repo buvis/agent-skills --json headSha,status,conclusion,jobs,url
exit: 0
{
  "headSha": "3af575327b5526c0fb45ab3f3e249faaabe5c26d",
  "status": "completed",
  "conclusion": "success",
  "url": "https://github.com/buvis/agent-skills/actions/runs/42819166960",
  "jobs": [
    {
      "name": "lint",
      "id": 129839927939,
      "status": "completed",
      "conclusion": "success",
      "stepCount": 11,
      "allStepsCompletedSuccess": true
    },
    {
      "name": "skill-integrations (windows-latest)",
      "id": 129839928304,
      "status": "completed",
      "conclusion": "success",
      "stepCount": 7,
      "allStepsCompletedSuccess": true
    },
    {
      "name": "windows",
      "id": 129839928331,
      "status": "completed",
      "conclusion": "success",
      "stepCount": 9,
      "allStepsCompletedSuccess": true
    },
    {
      "name": "test (3.10)",
      "id": 129839928353,
      "status": "completed",
      "conclusion": "success",
      "stepCount": 8,
      "allStepsCompletedSuccess": true
    },
    {
      "name": "skill-integrations (ubuntu-latest)",
      "id": 129839928462,
      "status": "completed",
      "conclusion": "success",
      "stepCount": 7,
      "allStepsCompletedSuccess": true
    },
    {
      "name": "node",
      "id": 129839928499,
      "status": "completed",
      "conclusion": "success",
      "stepCount": 9,
      "allStepsCompletedSuccess": true
    },
    {
      "name": "test (3.13)",
      "id": 129839928539,
      "status": "completed",
      "conclusion": "success",
      "stepCount": 8,
      "allStepsCompletedSuccess": true
    },
    {
      "name": "shell",
      "id": 129839928712,
      "status": "completed",
      "conclusion": "success",
      "stepCount": 5,
      "allStepsCompletedSuccess": true
    }
  ]
}
$ git ls-remote origin refs/heads/master 'refs/tags/v0.1.0*' 'refs/tags/v0.2.0*'
exit: 0
3af575327b5526c0fb45ab3f3e249faaabe5c26d	refs/heads/master
f4f2de0aa55b9c53a531b1b280a4339e74aebc64	refs/tags/v0.1.0
f2b82d8372cceab04790e4fb183651a63de1e91d	refs/tags/v0.2.0
$ git rev-parse 'v0.1.0^{commit}' 'v0.2.0^{commit}'
exit: 0
f4f2de0aa55b9c53a531b1b280a4339e74aebc64
f2b82d8372cceab04790e4fb183651a63de1e91d
$ gh api repos/buvis/agent-skills/releases/tags/v0.1.0
exit: 0
{
  "id": 439793234,
  "tag_name": "v0.1.0",
  "name": "v0.1.0 (historical)",
  "html_url": "https://github.com/buvis/agent-skills/releases/tag/v0.1.0",
  "draft": false,
  "prerelease": false,
  "created_at": "2026-10-18T09:52:22Z",
  "updated_at": "2026-11-10T00:11:11Z",
  "published_at": "2026-11-10T00:11:11Z",
  "assets": []
}
$ gh api repos/buvis/agent-skills/releases/latest
exit: 0
{
  "id": 440124980,
  "tag_name": "v0.2.0",
  "name": "v0.2.0",
  "html_url": "https://github.com/buvis/agent-skills/releases/tag/v0.2.0",
  "draft": false,
  "prerelease": false,
  "created_at": "2026-10-25T22:23:30Z",
  "updated_at": "2026-11-10T08:50:27Z",
  "published_at": "2026-11-10T08:50:27Z",
  "assets": []
}
$ gh api graphql -f 'query=query { repository(owner:"buvis", name:"agent-skills") { historical: release(tagName:"v0.1.0") { databaseId tagName isLatest isDraft isPrerelease url } newer: release(tagName:"v0.2.0") { databaseId tagName isLatest isDraft isPrerelease url } } }'
exit: 0
{
  "data": {
    "repository": {
      "historical": {
        "databaseId": 439793234,
        "tagName": "v0.1.0",
        "isLatest": false,
        "isDraft": false,
        "isPrerelease": false,
        "url": "https://github.com/buvis/agent-skills/releases/tag/v0.1.0"
      },
      "newer": {
        "databaseId": 440124980,
        "tagName": "v0.2.0",
        "isLatest": true,
        "isDraft": false,
        "isPrerelease": false,
        "url": "https://github.com/buvis/agent-skills/releases/tag/v0.2.0"
      }
    }
  }
}
$ gh api 'repos/buvis/agent-skills/contents/.github/workflows/ci.yml?ref=3af575327b5526c0fb45ab3f3e249faaabe5c26d' --jq '{sha,size,path}'
exit: 0
{
  "path": ".github/workflows/ci.yml",
  "sha": "87421424848ad2d41436de49110f04e5eaa27243",
  "size": 9255
}
$ git rev-parse 3af575327b5526c0fb45ab3f3e249faaabe5c26d:.github/workflows/ci.yml
exit: 0
87421424848ad2d41436de49110f04e5eaa27243
$ gh api repos/buvis/agent-skills/git/ref/heads/master --jq .object.sha
exit: 0
3af575327b5526c0fb45ab3f3e249faaabe5c26d
```

Prepared-notes verification used Python `Path.read_bytes()`, extracted the
report's first fenced Markdown block, compared both with the REST body encoded
as UTF-8, and computed `hashlib.sha256(notes).hexdigest()`. All three byte
sequences match exactly, including final newline; SHA-256:
`e8d19ba28db18b65bbc8ecfcf52ece574990ffe00491a1d5ffe13b178c2a511a`. Historical release ID, title, timestamps,
empty assets, draft/prerelease flags, body, and exact tag target match the
pre-recovery publication evidence. GraphQL independently confirms
`v0.1.0.isLatest=false` and `v0.2.0.isLatest=true`; REST Latest is ID
`440124980`. Both local tag commits match their exact remote refs.

The full GitHub workflow contents at the current exact master SHA were decoded
and inspected, and the matching local Git blob was checked. Blob
`87421424848ad2d41436de49110f04e5eaa27243` is unchanged from preparation and
publication. Its six definitions expand to all eight successful jobs, including
Windows full Python 3.13 suite/capabilities and Windows integrations. No
`continue-on-error`, job/step `if:` filter, path filter, matrix exclusion, or
fail-open test command was introduced; `fail-fast: false`, accumulated shell/
validator failure exits, capability failure exits, and template-drift failure
exit remain intact. Remote master was re-read after the other checks and
remained the same exact SHA. These observations establish the current gate;
they do not claim retrospective CI success for the historical tag.

No new unit tests are needed for this read-only publication verification.

## Resumed build closeout

`autopilot verify --gate-command 'uv run pytest' --cycle 1` ran at
`3af575327b5526c0fb45ab3f3e249faaabe5c26d`: pytest exited 0 with **4330 passed,
12 skipped, 2 warnings**, in 337.64 seconds. The verify CLI returned 3 because
its summary parser found no counts line; it wrote no verification record.
These counts are the actual pytest summary in `docs/dev/tmp/gate-3af5753.log`,
not a synthesized record. No retry or unrelated repair was needed.

`uv run ruff check`, `uv run ruff format --check`, `git diff --check`, and
`braid --check --source <repository-root>` passed (161 current, zero drift).
No skill changed in this resumed task, so per-skill validation is inapplicable.
Full state-schema validation and task-count consistency passed: 2/2 completed.

`autopilot lane-check` exited 3: `unnamed_path`. It canonically escalated the
solo classification to full review because the preserved work range includes
production changes merged during operator recovery. The work start remains
unchanged; no attempt or prior evidence was dropped. The model audit includes
Task 2 attempt 2, and driver `review-route` validates it and requires Anthropic.
All completion-review lenses are reserved for the fresh review session.

The unrelated staged intake note `intake/new/00176-skills-adopt-repository-memory/idea.md`
is temporarily preserved in a path-scoped stash to exclude it from the store
recorder; restore its original staged state immediately after that recorder.
Existing worktrees and plans belong to other work and remain untouched.

## Cycle 1 rework — Task 3

Committed as `8bc7321`. Native isolated worker dispatch `e165b312`, logical
sonnet, observed OpenAI `gpt-6.1-sol` / medium, session
`01a1c767-5a66-7bd1-9779-43d1db73c145`; sanitized raw-metadata
extract is retained in the sibling worker-metadata JSONL with its source hash.
Host delegation overrides the eligible source micro lane; the independent
review route remains Anthropic Opus/xhigh via the driver.

Only the PRD record changed. Original conflict observations remain historical.
The record now states final verification and v0.2.0 recovery safeguards,
including the honest postpublication timing of the notes review. Read-only
`gh run view 42819166960` confirmed exact head
`3af575327b5526c0fb45ab3f3e249faaabe5c26d`, completed/success, eight
successful jobs and every step successful. Python compared local v0.2.0
notes bytes with the live REST release body: equality true; both SHA-256
`c1dc88bef9af6f80a574ee8ddce9b630a5dc3c5a0cd51eda6a556e1b49e25ffd`.
All six entry texts equal the tagged changelog section, blob
`98c0aecd260372b4b9b1675eee1362603406cf96`. Read-only REST confirms
release 440124980, published 2026-11-10T08:50:27Z, empty assets, false
draft/prerelease. GraphQL confirms v0.1.0 is not Latest and v0.2.0 is Latest.
Live v0.1.0 body hash remains
`e8d19ba28db18b65bbc8ecfcf52ece574990ffe00491a1d5ffe13b178c2a511a`;
read-only remote refs retain both exact tag targets. No external mutation.

Documentation-only: Tess/red-check and per-task code review skipped under the
source documentation rules; no new tests. Self-deslop skipped because only
one implementation file changed. Reflow and diff checks passed.
3: style_gate: clean, split_hygiene: skipped:no-tests.
ASSUMPTIONS: none. The pre-existing assumptions ledger belongs to PRD 00131
and is preserved; this task adds none. No queued verification checks exist.
Ruff lint/format and explicit-source braid check passed (161 current, zero drift).
Cycle 1 consolidated review shape/guard gate passed; prior receipts and audit
snapshot remain unchanged for the fresh cycle 2 review.

Final rework verification at `8bc7321943ea446e63075631c5347b3a5cc57f7b`:
`autopilot verify --gate-command "uv run python scripts/gate.py" --cycle 1`
returned exit 0, recorded true, clean tree: **PASS 4333 FAIL 0 SKIP 12 EXIT 0**.
No suite retry or repair. State schema/task counts valid, 3/3 complete.
Next action is canonical rework transition and fresh cycle 2 completion review;
this session does not run that review or claim convergence.

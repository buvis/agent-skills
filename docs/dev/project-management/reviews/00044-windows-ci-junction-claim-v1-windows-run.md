# PRD 00044 — Windows full-suite run evidence

Task 8: "Run the complete Python suite on POSIX and on native windows-latest for
the final changed commit, and record the evidence."

Status: **EXECUTION BLOCKER. The validation was NOT performed and is NOT complete.**

Recorded 2026-09-07 by the autopilot build session (batch 202609050909).

## The blocker

The task's `Premise:` line requires two facts. One holds, one does not.

| Premise fact | Verdict | Evidence |
|---|---|---|
| `gh` is authenticated headlessly | **HOLDS** | `gh auth status` → `Logged in to github.com account tbouska (keyring)`, active, token scopes `gist, read:org, repo`, git protocol ssh |
| the branch carrying this work has reached GitHub | **FAILS** | after `git fetch origin`, `git rev-list --count origin/master..master` → **91** |

`origin/master` is still at `1745aed` (last moved 2026-09-05). Local `master` is
at `bb882fc`. GitHub cannot run a workflow for commits it has never seen, so
there is no commit on the remote at which the `windows` job could run, and
`gh run view` has nothing to inspect.

The PRD's own instruction for this case is followed exactly: the command was not
weakened, no marker was added to any test, and the validation is not marked
complete. Per the task's Details — "If authentication or runner access is
unavailable, STOP and record the execution blocker in the evidence document."

## Why autopilot did not simply push

Autopilot does not push on the user's behalf. This is a deliberate design
decision, not an oversight: `run-autopilot/references/design-rationale.md`
§ "Commit history left as-is (Phase 9)" records that the Phase 9 regroup engine
"never pushed — the user re-reviewed and pushed manually anyway", and that
"the user squashes manually before pushing". Pushing 91 accumulated commits here
would pre-empt that squash.

## What unblocks this task

One action by a human:

```
git push origin master
```

Then move the PRD out of `hold/` and re-run the loop:

```
mv dev/local/prds/hold/00044-windows-ci-junction-claim-v1.md dev/local/prds/backlog/
autoclaude
```

The design doc is reused on re-entry (Phase 1.5 artifact skip). Tasks 1-7 are
already committed to `master`; the replan will re-plan the PRD's scope, and the
already-landed work stands in git regardless.

## What IS proven, and on which host

POSIX only. Every figure below was measured on this host (macOS, APFS, Python
3.10 via `uv`), at commit `bb882fc`.

| Command | Exit | Result |
|---|---|---|
| `uv run pytest skills/distil-memory/scripts/test_proposal_publication.py skills/distil-memory/scripts/test_funnel_distil_publication.py -q` | 0 | 25 passed, 2 warnings |
| `uv run pytest skills/distil-memory/scripts -q` (task 7 implementor) | 0 | 627 passed, 2 warnings |

Nothing on `windows-latest` has been executed for this PRD. The `jobs.windows`
definition added in task 1 is **unexercised**: it has never run on a GitHub
runner, because no commit carrying it has reached GitHub.

## Consequences for task 9

Task 9 (`blocked_by: [8]`) must correct README's coverage paragraph so it claims
no more than this document shows. As of now this document shows **no Windows
execution at all**, so task 9 cannot honestly write "the Python suite runs on
windows-latest" — that sentence is only earned once the run above exists. Task 9
is therefore blocked by the same premise and was not attempted.

## Known warnings, not failures

The 2 warnings in both runs are pytest's own `rm_rf` failures on stale
`pytest-of-bob/garbage-*` temporary directories, left by the 300-character
filename test. Pre-existing local scratch noise, unrelated to this PRD, and
absent from a clean CI runner.

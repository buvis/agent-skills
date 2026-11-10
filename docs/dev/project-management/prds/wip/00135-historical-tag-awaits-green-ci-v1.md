---
design: skip
catchup: skip
default_model: sonnet
model_tier_rationale: gated historical publication preserving an exact existing tag and current release ordering
eligibility: >-
  python3 -c 'import json,subprocess,sys; gate_rows=json.loads(subprocess.check_output(["gh","run","list","--repo","buvis/agent-skills","--workflow","ci.yml","--branch","master","--limit","1","--json","headSha,status,conclusion"],text=True)); gate_head=subprocess.check_output(["gh","api","repos/buvis/agent-skills/git/ref/heads/master","--jq",".object.sha"],text=True).strip(); sys.exit(0 if gate_rows and gate_rows[0]["headSha"]==gate_head and gate_rows[0]["status"]=="completed" and gate_rows[0]["conclusion"]=="success" else 1)'
---

# Publish the missing historical tag only after green CI

Source: agoge report `dev/local/audit-results/agoge-2026-10-25.md`, finding 15,
accepted option A on 2026-10-29. The user explicitly selected conditional tag
and release publication after green CI, preserving existing history. Reports
are local audit artifacts and are not shipped in the public repository.

## Problem

The existing local v0.1.0 tag is absent from GitHub. A later v0.2.0 tag is
published, but current read-only checks found no GitHub release entries.
Users cannot install or compare against the historical v0.1.0 tag remotely.
Published-master CI remains red in Windows, so the selected publication condition
has not been met.

## Solution

Leave this PRD ineligible until the latest CI run for the current published
master commit completes successfully. Then prepare historical release notes,
re-check all publication prerequisites, push only the missing existing tag,
and create its GitHub release without making it Latest. Preserve the tag's
exact target and do not push branch commits or rewrite history.

## Requirements

### Must have

- Eligibility requires successful completed CI for the current remote master SHA;
  an older successful run or local test pass is insufficient.
- Immediately before publication, verify all required CI jobs, including Windows,
  passed without weakening the gate or relying on continue-on-error.
- Preserve v0.1.0 at commit f4f2de0aa55b9c53a531b1b280a4339e74aebc64.
- Refuse a conflicting local or remote tag; never force-update or re-cut it.
- Prepare notes from the tagged version's release information, identifying this
  as historical publication without claiming that old commit passed later CI.
- Push only the missing tag, then use a verified existing remote tag to create
  the release. Do not let GitHub auto-create a tag at current master.
- Do not mark the historical release Latest or publish other versions/assets.
- Handle an already-correct tag/release idempotently rather than duplicating or
  overwriting it; stop and report conflicting publication state.
- Re-check CI immediately before external actions; if it is no longer eligible,
  leave publication pending without weakening the condition.

### Nice to have

- None.

## Implementation

```text
docs/dev/project-management/prds/backlog/
└── 00135-historical-tag-awaits-green-ci-v1.md  # eligibility and publication record
docs/dev/tmp/
└── 00135-v0.1.0-release-notes.md              # prepared notes consumed by release creation
```

### Module: conditional historical publication

- **Location**: `docs/dev/project-management/prds/backlog/00135-historical-tag-awaits-green-ci-v1.md`
- **Maps-to-capability**: publish the accepted historical version only after its condition holds.
- **Responsibility**: retain the gate, exact tag target, and final publication evidence.
- **Exports**: none.

#### Feature: publish the preserved tag and release

- **Inputs**: green current published-master CI, preserved tag, and prepared notes.
- **Outputs**: remote v0.1.0 at the accepted target and its historical GitHub release.
- **Behavior**: recheck prerequisites, publish without force or branch pushes, and
  preserve current release ordering.

### Module: prepared release notes

- **Location**: `docs/dev/tmp/00135-v0.1.0-release-notes.md`
- **Maps-to-capability**: make the exact release text concrete before publication.
- **Responsibility**: describe the historical version accurately using tagged sources.
- **Exports**: none.

### Dependencies

- Green published-master CI: prerequisite, with full Windows coverage tracked by PRD 00044.
- Prepared notes and verified tag state: precede publication.
- Tag push precedes release creation; release creation requires the remote tag.

## Tasks

### Phase 0: Preparation after eligibility

- [ ] Verify the latest CI head matches current published master and inspect
  required job conclusions. Verify local/remote tag state and existing release
  entries. Prepare the exact historical notes from the tagged version, without
  adding later features or claiming retrospective CI success. Acceptance: the
  gate is green for current remote master, tag resolves to the accepted full SHA,
  publication state has no conflict, and the prepared notes are reviewable.

### Phase 1: Conditional publication

- [ ] Depends on Phase 0. Recheck the CI condition immediately before publishing.
  Push only the missing v0.1.0 tag without force, then create the release using
  --verify-tag, --latest=false, and the prepared notes file. Preserve an already
  correct publication; stop on conflicts rather than overwrite. Acceptance:
  read-only checks confirm the remote tag's exact commit and the matching release
  body, without branch pushes, changed tags, extra assets, or Latest promotion.

Exit criteria: record the verified tag target, release URL, CI run/SHA, and notes
source. Publishing is explicitly authorized by the user's conditional option A;
the condition must hold and any tool approval controls still apply.

## Success Criteria

- The historical tag is remotely available at its original exact commit.
- Its release notes are published only after the stated current-CI gate passes.
- Existing history and newer-version release ordering remain intact.

### Test Strategy

Carry the original evidence verbatim:

```text
`git ls-remote --tags origin` -> empty (the control `refs/heads/master` resolves). `gh api repos/buvis/agent-skills/tags` -> empty.
```

Updated read-only checks on 2026-10-29 found v0.2.0 remotely, no v0.1.0,
no release entries, and Windows-only failure in latest published-master CI.
Installed `gh release create --help` confirms --verify-tag prevents automatic
tag creation and --latest=false avoids explicit Latest promotion. Verify
publication with read-only queries; no new unit tests are needed for this workflow.

### Risks

Later master CI success does not prove the historical tagged commit was green.
The notes must be honest about that distinction. Publication is an external
commitment, so prepare everything before the final action and never bypass
eligibility, overwrite conflicting refs, or publish unreviewed additional scope.

## Publication record — 2026-11-10

At initial publication, Phase 1 was incomplete because verification found a
Latest conflict; recovery and final verification are recorded below.
Immediately before each external action, remote master
`99f3c9cd0e0be8172e127559769e75044b0dafab` matched completed successful CI
run [42716763283](https://github.com/buvis/agent-skills/actions/runs/42716763283);
all eight jobs and every step, including Windows, passed. The exact workflow
blob remained unchanged and its inspected gates were not weakened.

Only the existing v0.1.0 tag was pushed, without force, at
`f4f2de0aa55b9c53a531b1b280a4339e74aebc64`. The verified remote tag was
used to create [v0.1.0 (historical)](https://github.com/buvis/agent-skills/releases/tag/v0.1.0)
with `--verify-tag --latest=false` and the prepared notes. Publication timestamp:
2026-11-10T00:11:11Z. Body bytes match the prepared notes; no assets, draft,
or prerelease state. Notes SHA-256:
`e8d19ba28db18b65bbc8ecfcf52ece574990ffe00491a1d5ffe13b178c2a511a`.
Source: `v0.1.0:CHANGELOG.md`, `[0.1.0] - 2026-10-18`.
Master and the newer v0.2.0 tag stayed unchanged.

Despite `--latest=false`, REST `/releases/latest` resolved to this release and
GraphQL reported `isLatest: true`. This failed the no-Latest acceptance criterion
and contradicted the published notes' designation statement. External actions
stopped at the conflict; no overwrite, deletion, or other-version release was
attempted. Recovery was pending at that point. Full commands and evidence are in
`docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-build.md`.

## Operator waiver and recovery — 2026-11-10

The operator waived "do not publish other versions" for v0.2.0 only, to clear
the Latest conflict: v0.1.0 was the sole release, so GitHub made it Latest.
After green CI run [42779216047](https://github.com/buvis/agent-skills/actions/runs/42779216047)
on remote master `f90d5fa0f9966d1e673ed2c9cdc55067e1b8a763`, a release for the
existing remote v0.2.0 tag was published as Latest:
[v0.2.0](https://github.com/buvis/agent-skills/releases/tag/v0.2.0).
v0.1.0 now reports `isLatest: false`; its release, both tags and master are
unchanged by recovery.

Recovery used `--verify-tag --latest` for the existing v0.2.0 tag at
`f2b82d8372cceab04790e4fb183651a63de1e91d`, without moving either tag.
Notes source: `docs/dev/tmp/00135-v0.2.0-release-notes.md`, from
`v0.2.0:CHANGELOG.md`, section `[0.2.0] - 2026-10-25` (blob
`98c0aecd260372b4b9b1675eee1362603406cf96`). The documentation repair
reviewed all six Changed/Fixed entries against that tagged section: they match
exactly, and the added framing distinguishes the version date from publication.
The live release body matches the prepared notes byte-for-byte, including the
final newline; both have SHA-256
`c1dc88bef9af6f80a574ee8ddce9b630a5dc3c5a0cd51eda6a556e1b49e25ffd`.
Release `440124980` was published at 2026-11-10T08:50:27Z, with no assets,
`draft: false`, and `prerelease: false`. This review records the notes check
performed during documentation repair, without claiming a prepublication review.

### Final read-only verification — 2026-11-10

The build session verified Phase 1 at 2026-11-10T18:57:47+00:00 under the
recorded waiver. Current published master
`3af575327b5526c0fb45ab3f3e249faaabe5c26d` matched completed successful CI
run [42819166960](https://github.com/buvis/agent-skills/actions/runs/42819166960);
all eight jobs and every step, including Windows, passed with unchanged workflow
blob `87421424848ad2d41436de49110f04e5eaa27243`. Remote v0.1.0 remained at
`f4f2de0aa55b9c53a531b1b280a4339e74aebc64`, with its unchanged
[historical release](https://github.com/buvis/agent-skills/releases/tag/v0.1.0)
and matching body SHA-256
`e8d19ba28db18b65bbc8ecfcf52ece574990ffe00491a1d5ffe13b178c2a511a`.
GraphQL confirmed `v0.1.0.isLatest=false` and `v0.2.0.isLatest=true`;
REST Latest was v0.2.0 release `440124980`. Both tag targets matched their
local preserved commits. Phase 1 publication verification passed; this records
publication evidence, not completion-review approval. Full commands and results
remain in the build report linked above.

# Build blocked: generated card scope

Installed autopilot 0.10.0 renders the PRD as fast-track. Its card Files allowlist contains only skills/distil-memory/scripts/funnel.py. The PRD also requires test_funnel_triage.py and test_funnel_main.py. The fixed-allowlist worker contract cannot execute those required edits. No worker was dispatched and no implementation changed.

The renderer exits zero, so its documented exit-2 fallback does not apply. No lane override or installed-plugin patch was attempted. Recovery requires a corrected renderer or explicit authorization for a corrected card. Preserve work_start_sha and unrelated work. Prior Tess dispatch 054609d2 is recorded lost; no distil-memory commit exists in work_start_sha..HEAD.

## Interactive recovery, 2026-11-10

The request to unblock this session and standing authorization cover the
reversible PRD correction. The installed parser recognizes singular
`- **Location**:` lines, but ignores the plural `Locations` entry and the tree
under `Implementation`. Replaced the plural entry with one singular entry per
existing test path. Regeneration now includes exactly `funnel.py`,
`test_funnel_triage.py`, and `test_funnel_main.py` under
`skills/distil-memory/scripts/`; the change adds no new implementation scope.

Normalized the existing exit criteria to the renderer's `**Exit Criteria**`
format on one line, using the repository's `uv run braid --check` entry point.
The generated card now retains the targeted tests, full suite, skill validator,
and braid check. This fixes the source PRD so subsequent regeneration preserves
the correction; it requires no hand-edited card or installed-plugin patch.

Resume the existing build task in a fresh autocodex session. Preserve its task
identity, work baseline, cycle, lane, and all review requirements. No PRD
implementation or completion review was performed during recovery.

Verification: the installed card loader accepts the regenerated card; assertions
confirm one card, the exact three-file allowlist, and four gates. State schema
validation passes, and only phase, next phase, pause reason, and contract card
changed. The resume target is the existing unfinished task 1. `uv run pytest`:
4,386 passed, 12 skipped; the distil-memory skill validator and `git diff --check`
pass.

Host prerequisite: `braid --check` reports 24 pre-existing missing skill links.
Both the normal repair and approved tool retry were denied by the macOS agent
sandbox. Repair is queued through warrant request
`1824e97a18be57c272e3d3fc92191174`; approve it on the host, then require a green
`braid --check` before relaunching autocodex. The card-scope pause is resolved;
state now points to build without changing task progress or review policy.

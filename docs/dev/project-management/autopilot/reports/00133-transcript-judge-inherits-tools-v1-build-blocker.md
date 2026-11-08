# Build blocked: generated card scope

Installed autopilot 0.10.0 renders the PRD as fast-track. Its card Files allowlist contains only skills/distil-memory/scripts/funnel.py. The PRD also requires test_funnel_triage.py and test_funnel_main.py. The fixed-allowlist worker contract cannot execute those required edits. No worker was dispatched and no implementation changed.

The renderer exits zero, so its documented exit-2 fallback does not apply. No lane override or installed-plugin patch was attempted. Recovery requires a corrected renderer or explicit authorization for a corrected card. Preserve work_start_sha and unrelated work. Prior Tess dispatch 054609d2 is recorded lost; no distil-memory commit exists in work_start_sha..HEAD.

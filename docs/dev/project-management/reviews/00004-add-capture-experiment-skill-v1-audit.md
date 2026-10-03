# Decision Audit Log: 00004-add-capture-experiment-skill-v1

PRD: `00004-add-capture-experiment-skill-v1.md`
Started: 2026-08-29T18:51:07Z
Completed: 2026-08-29T18:51:07Z
Autonomous: 3  |  Deferred: 7  |  Doubts: 0

### [autonomous] 2026-08-29T18:51:07Z

**Decision**: Cannot statically verify: the test suite, create-skill validator, and braid checks passed (Bob, cycle 1, low)

**Choice**: discard

**Rationale**: Not a defect - his codex sandbox blocks execution, so the line is the prescribed sandbox response. The gate ran the named checks directly: `uv run pytest -q` gave 422 passed / 5 skipped / 0 failed (skips pre-existing, needing the optional tree_sitter_language_pack), and the create-skill validator returned `[OK] Skill is valid!`. `braid --check` could not run (warden blocks the binary in this session) and is recorded as unverified in the review file rather than claimed green.

### [autonomous] 2026-08-29T18:51:07Z

**Decision**: Five findings raised in cycle 1 (Bob, Blake): unquoted YAML title scalar (HIGH); Step 3 validates ~/bim/ but writes into the never-yet-created capture-experiment/ leaf without creating it (HIGH); Dependencies section omits absence behavior for digest-github-repo/spike/create-prd (MEDIUM); the "All files live under..." line duplicates Step 3 (MEDIUM); same-second id collision silently overwrites a note (LOW)

**Choice**: auto-fix, grouped into one [D1] rework task (all additive or mechanical, no signature/schema change)

**Rationale**: The title is the skill's one required user argument and experiment titles commonly contain a colon, which breaks the frontmatter contract the PRD's success metric depends on; digest-github-repo's own template quotes its title, so this is also a real deviation from the dialect the PRD said to copy. The remaining four findings are mechanical or additive fixes with no design tradeoff.

### [autonomous] 2026-08-29T18:51:07Z

**Decision**: Cycle 2 finding "PRD is still parked in dev/local/prds/wip/ rather than moved to done/" (Blake, low)

**Choice**: discard

**Rationale**: Verified non-defect: the PRD sits in wip/ precisely because the autopilot done gate (Phase 9) has not run yet - moving wip/ to done/ IS a Phase 9 step, executed after the review-rework loop closes. Blake is blind to the orchestration state by design, so he read normal mid-run lifecycle state as a process lapse. Nothing in the implementation is wrong and no code change is implied.

### [deferred] 2026-08-29T18:51:07Z

**Decision**: Frontmatter omits digest-github-repo's id: field (Blake, cycle 1, high)

**Choice**: defer to batch end as a requirements ambiguity

**Rationale**: The PRD acceptance criterion pins the template to exactly six fields and the reuse source the task names (digest-github-repo/SKILL.md step 5) lists exactly those six; digest-github-repo/references/output-templates.md carries id and repo on top. The two authorities inside digest-github-repo disagree and the PRD inherits that. Implementation matches the binding acceptance criterion, so adding id would violate it. Human call required.

### [deferred] 2026-08-29T18:51:07Z

**Decision**: No retained regression coverage for no-title, missing-vault, compacted-window, no-dead-end behavior (Bob, cycle 1, low)

**Choice**: defer as out of scope

**Rationale**: Docs-only PRD delivering a skill body; asserting these behaviors needs a model-behavior evaluation harness, which is cross-cutting.

### [deferred] 2026-08-29T18:51:07Z

**Decision**: Title handling remains incomplete: YAML double-quoted scalars also require backslashes to be escaped, and the collapse/escape instruction applies YAML escaping to the Markdown heading too. Preserve a normalized plain title for the heading and YAML-escape both backslashes and quotes only for frontmatter. (skills/capture-experiment/SKILL.md:83, Alice+Bob, cycle 2, high, 2/4 consensus)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T18:51:07Z

**Decision**: Title-escaping fix only covers embedded double quotes, not backslashes - a title containing a literal backslash (e.g. a Windows path or regex in the title) still produces an invalid double-quoted YAML scalar, verified with PyYAML (ScannerError). (skills/capture-experiment/SKILL.md, Alice, cycle 2, medium, 1/4 consensus)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T18:51:07Z

**Decision**: "Advance to the next free second" is ambiguous timestamp arithmetic and may produce an invalid ID such as ...5960, violating the pinned date-generated ID scheme. Require waiting for the clock to advance, rerunning date +%Y%m%d%H%M%S, and repeating the existence check. (skills/capture-experiment/SKILL.md:112, Bob, cycle 2, medium, 1/4 consensus)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T18:51:07Z

**Decision**: The new dependency fallback prose repeatedly states "not invoked," "nothing changes," "capture proceeds," and "not a runtime dependency." Collapse each entry to one explicit absence sentence while preserving the required fallback behavior. (skills/capture-experiment/SKILL.md:16, Bob, cycle 2, medium, 1/4 consensus)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T18:51:07Z

**Decision**: Fixture note title is unquoted YAML (title: Reduce polling interval on sensor loop) though the template mandates a quoted scalar and SKILL.md explicitly calls out quoting/escaping; harmless here since the title has no special characters, but the fixture output did not follow the stated convention it was meant to demonstrate. (dev/local/tmp/20260829200518.md, Blake, cycle 2, low, 1/4 consensus)

**Rationale**: rework cap reached with this finding unresolved

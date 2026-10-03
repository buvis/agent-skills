# Decision Audit Log: 00002-add-sweep-fix-skill-v1

PRD: `00002-add-sweep-fix-skill-v1.md`
Started: 2026-08-29T15:01:51Z
Completed: 2026-08-29T15:01:51Z
Autonomous: 8  |  Deferred: 21  |  Doubts: 0

### [autonomous] 2026-08-29T15:01:51Z

**Decision**: Review cycle 1 raised 32 consolidated findings across 4 reviewers (Alice, Blake, Bob/codex, Carl/gemini). 4 critical and 8 high block convergence.

**Choice**: grouped into 9 themed [D1] rework tasks (under the 10-task scope alarm, so no scope-overflow deferral)

**Rationale**: Review cycle 1. Grouping by theme and file keeps the rework batch under the Safety Checks scope alarm while covering every blocking finding. Mediums that do not block convergence were either folded into an adjacent task at no extra cost or left for the convergence tail sweep.

### [autonomous] 2026-08-29T15:01:51Z

**Decision**: Consolidation under-merged paraphrases: consolidate_findings.py matches on file string plus description, so findings naming the same defect with different file spellings (sweep.py vs sweep.py:97) or different wording landed at [1/4] instead of their true consensus.

**Choice**: recorded corrected consensus in the review file alongside the script's raw table; used the corrected figures for gate prioritisation

**Rationale**: Review cycle 1. The script's output is kept verbatim as the record of what actually ran (fail loud), with the correction stated explicitly rather than silently substituted.

### [autonomous] 2026-08-29T15:01:51Z

**Decision**: verify_control() aborts the whole sweep before scan() runs, so a control repo whose pattern hits were removed by the fix itself kills a sweep that would have found real hits elsewhere. Contradicts verify_control's own docstring: 'Never called when the pattern DID find hits anywhere.'

**Choice**: auto-fix, dispatched as task D1-T5

**Rationale**: Review cycle 1. The fix is a call-site reordering in main() with no signature change, and the docstring already states the intended contract, so this is a mechanical correction rather than a design decision.

### [autonomous] 2026-08-29T15:01:51Z

**Decision**: sweep.py imports third-party PyYAML at module load. pyproject.toml declares no [project].dependencies at all; pyyaml>=6 sits only in [dependency-groups].dev, so SKILL.md's documented bare `python3 sweep.py` invocation depends on an undeclared package.

**Choice**: auto-fix, dispatched as task D1-T3 (emit the rule block without PyYAML rather than add a runtime dependency)

**Rationale**: Review cycle 1. Protocol A (new dependency) was not run because the resolution is to REMOVE the dependency, not add one: the design doc's own constraint is 'stdlib only except subprocess calls to external binaries', every other skill script in this repo is stdlib-only, and the rule block is five fixed keys that need no serializer. Verified independently at the gate by reading pyproject.toml.

### [autonomous] 2026-08-29T15:01:51Z

**Decision**: The rendered how-to-proceed block tells the operator 'If it is a real problem, fix it directly', with no mention of per-hit approval or the current-repo-only restriction that is the skill's core safety rule.

**Choice**: auto-fix, dispatched as task D1-T7, together with the test that must bind to the block's required content

**Rationale**: Review cycle 1. The report text contradicts the PRD's 'Apply fixes in the current repo only' feature and SKILL.md's own read-only rule. The paired test change addresses R2 (tests bind to intent): the existing test only asserts a non-empty tail.

### [autonomous] 2026-08-29T15:01:51Z

**Decision**: Negative --cap values are accepted: cap=-1 makes `len(repo_hits) > cap` always true, producing a suppressed count of len+1 and silently dropping the last hit via repo_hits[:-1].

**Choice**: auto-fix, dispatched as part of task D1-T9

**Rationale**: Review cycle 1. Input validation at a system boundary (CLI argument), mechanical, additive-only.

### [autonomous] 2026-08-29T15:01:51Z

**Decision**: test_sweep.py is 957 lines, over the 800-line file cap in rules/coding-style.md. Full 4/4 consensus, the only finding all four reviewers raised. Already surfaced by the build's own style gate and left as a recorded fail-loud-and-proceed.

**Choice**: auto-fix, dispatched as part of task D1-T9

**Rationale**: Review cycle 1. It is a live violation of a stated project rule with unanimous reviewer agreement, and the build already recorded it as unresolved rather than accepted. Splitting a test module by concern is behaviour-preserving.

### [autonomous] 2026-08-29T15:01:51Z

**Decision**: Review cycle 2 is the rework cap (rework_cap 2). It did not converge: 2 unresolved HIGH findings remain (the verify_control fallback swallowing resolver failures, and the enumerate_repos cwd not normalized to the git root). Zero CRITICAL findings, down from 4 in cycle 1.

**Choice**: loop-mode cap-out: all 13 unresolved findings appended to deferred_decisions as cap-overflow, PRD finalized as converged-with-deferrals, batch continues

**Rationale**: Review cycle 2. The cap-out branch stalls the PRD only on an unresolved CRITICAL; none remains. Alice rated the swallowed-resolver-failure finding HIGH rather than CRITICAL and the gate agrees: with every resolver unresolvable, scan() per-repo isolation still records every repo as failed and render_report names them, so the report is not a false clean sweep, it is a report full of failed repos. The missing piece is only the loud unverified abort. Both HIGHs are real and reproduced live, so they are deferred rather than discarded.

### [deferred] 2026-08-29T15:01:51Z

**Decision**: enumerate_repos() returns individual tracked FILE paths for the ~/.buvis bare-cwd case, but scan() uses every repos entry as a subprocess cwd, so the PRD's own named special case crashes with NotADirectoryError

**Choice**: rework_dispatched

**Rationale**: Critical severity is always recorded for batch-end visibility. It also blocks convergence, so it is being reworked this cycle as task D1-T1 (review cycle 1).

### [deferred] 2026-08-29T15:01:51Z

**Decision**: _scan_rg passes the pattern positionally to rg with no `--` separator, so a dash-prefixed pattern is silently consumed as an rg flag and the sweep reports wrong hit counts with no error

**Choice**: rework_dispatched

**Rationale**: Critical severity is always recorded for batch-end visibility. It also blocks convergence, so it is being reworked this cycle as task D1-T2 (review cycle 1).

### [deferred] 2026-08-29T15:01:51Z

**Decision**: The ~/.buvis `git ls-files -z` call sets no cwd=, so it inherits the OS process cwd and silently returns 0 files whenever the process was not launched from $HOME; the fixture test passes by accident because its work_tree is disjoint from pytest's cwd

**Choice**: rework_dispatched

**Rationale**: Critical severity is always recorded for batch-end visibility. It also blocks convergence, so it is being reworked this cycle as task D1-T1 (review cycle 1).

### [deferred] 2026-08-29T15:01:51Z

**Decision**: SKILL.md invokes the script through the repo-relative path `python3 skills/sweep-fix/scripts/sweep.py`, so the installed skill fails anywhere outside the agent-skills repository

**Choice**: rework_dispatched

**Rationale**: Critical severity is always recorded for batch-end visibility. It also blocks convergence, so it is being reworked this cycle as task D1-T8 (review cycle 1).

### [deferred] 2026-08-29T15:01:51Z

**Decision**: verify_control() returns None (proceeds) when both the pattern and the control term find nothing in control_repo. The PRD's general prose says 'an empty control result aborts the sweep as unverified'; the design doc's specific contract aborts only when the control term IS present and the pattern is not.

**Choice**: settled

**Rationale**: Resolved by simplest safe assumption in favour of the design doc, which is the more specific and already-reviewed statement and which the code matches. Aborting whenever the control term is absent would make the tool unusable for the case the design's own review log names first: a fix that removed the pattern's only instance from the control repo's live tree. Recorded in the settled-decisions ledger; current behaviour kept.

### [deferred] 2026-08-29T15:01:51Z

**Decision**: scan() and render_report() signatures carry extra parameters (kind, suppressed) beyond the PRD's Structural Decomposition Exports list

**Choice**: settled

**Rationale**: The reporting reviewer states himself that the extra parameters are functionally required to satisfy other literal PRD requirements. This is an internal inconsistency in the PRD's own Exports list, not an implementation defect. Removing either parameter would break a stated Success Metric.

### [deferred] 2026-08-29T15:01:51Z

**Decision**: rg/ast-grep invocation flags drift from the design doc's documented shape (-n --no-heading, --json=compact) to --json for both

**Choice**: settled

**Rationale**: The code is strictly more robust than the documented shape: --json gives structured per-match records instead of text split on colons, which is the same parsing fragility this PRD exists to hunt. The design doc dies with the PRD and is not a shipped contract.

### [deferred] 2026-08-29T15:01:51Z

**Decision**: verify_control() and the main scan() both run a full pattern/kind scan against control_repo, duplicating subprocess work

**Choice**: open

**Rationale**: Medium severity does not block convergence. Not fixed this cycle; eligible for the convergence tail sweep. Note task D1-T5 changes verify_control's call site, which may resolve this incidentally.

### [deferred] 2026-08-29T15:01:51Z

**Decision**: verify_control() wraps its fallback literal-search call in a broad except Exception that warns to stderr and returns None, so an unresolvable rg/ast-grep makes main() exit 0 with a report instead of the required loud unverified abort; it also discards the failed channel from its own control-repo scan (sweep.py:329-337). Reproduced live by Alice. A regression introduced by cycle 2 rework task D1-T2.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: enumerate_repos() compares --cwd to on-disk repo paths by exact equality with no walk-up to the git root, so invoking from any subdirectory of the current repo makes the repo root appear as a false registry gap while only the subdirectory is scanned. Reproduced live by Blake from skills/sweep-fix/scripts/. Contradicts the PRD rule that the current repo is always covered and gaps are never swept silently.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: verify_control() rescans control_repo with the same pattern after the portfolio scan already covered it, duplicating subprocess work (sweep.py:312). Carried over from cycle 1, where it was recorded as not swept this cycle; now at true 3/4 consensus after correcting the consolidator under-merge.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: main() except RuntimeError handler (sweep.py:576-583) is dead code: scan() per-repo isolation and the verify_control() try/except now catch every RuntimeError the resolvers can raise before it reaches main(), and enumerate_repos() never raises one. Confirmed by Alice forcing all three resolutions to fail.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: enumerate_repos() opens the registry CSV unguarded inside a list comprehension, so a missing or unreadable --registry path raises FileNotFoundError/OSError that main() does not catch, surfacing as a raw traceback rather than the loud-failure pattern used everywhere else in the module.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: SKILL.md:40 still describes control verification before the portfolio scan, contradicting the corrected all-zero-only ordering that rework task D1-T5 landed in main().

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: The brief-portfolio dependency reference at SKILL.md:62 remains repo-relative and does not resolve when the installed skill runs outside this checkout; it should use the ~/.agents/skills path and state that it is provenance rather than a runtime import.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: Resolver tests remain host-dependent through real mise calls and assumptions about /usr/bin:/bin (test_sweep_resolvers.py:102). Note the reviewers disagree: Alice judged the same tests host-independent after the D1-T9 split, so this needs a check before it is acted on.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: Conditional YAML scalar classification is needless complexity: _needs_yaml_quoting is 34 lines and _yaml_scalar 7 (computed, per the mechanical-facts block). Bob proposes always serializing caller values with stdlib json.dumps() instead (sweep.py:402).

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: YAML round-trip tests repeat the same render, parse and equality assertions across adjacent functions (test_sweep_render_report.py:429); they should be one parametrized test with descriptive ids.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: The dash-pattern regression test keeps a fail-first comment claiming the current code lacks the -- separator, which stopped being true when D1-T2 landed (test_sweep_scan.py:105); it should state the invariant the test protects instead.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: The PRD requirement that registry parsing reuses collect.py:429 is met by duplicating the shape rather than importing it, because that line is inline in a function body and not an importable helper. Documentation nuance, no functional defect (sweep.py:142).

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-29T15:01:51Z

**Decision**: _resolve_report_path builds the report path deterministically from --reason plus the date with no collision check, so rerunning a sweep with the same reason on the same day silently overwrites the earlier report. The PRD does not address this either way.

**Rationale**: rework cap reached with this finding unresolved

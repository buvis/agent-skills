# Decision Audit Log: 00038-braid-docs-flags-and-backup-paths-v1

PRD: `00038-braid-docs-flags-and-backup-paths-v1.md`
Started: 2026-09-07T02:53:54Z
Completed: 2026-09-07T02:53:54Z
Autonomous: 6  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-07T02:53:54Z

**Decision**: ruff format --check fails on the diff: --agents-root and --claude-root add_argument calls force-wrapped though each fits under the 100-col limit; CI step .github/workflows/ci.yml:91 runs uv run ruff format --check

**Choice**: auto-fix

**Rationale**: Confirmed at the gate: uv run ruff format --check src/agent_skills_braid/cli.py exits 1, 1 file would be reformatted. Mechanical, behavior-preserving formatting fix; routed to cycle-1 rework as task [D1].

### [autonomous] 2026-09-07T02:53:54Z

**Decision**: --version still has no help= text, violating the success criterion that every parser action has a nonempty description (raised by BOB)

**Choice**: discard

**Rationale**: Refuted by direct measurement at the gate: argparse._VersionAction supplies a non-empty default help, so --version reads "show program's version number and exit". All ten actions dump non-empty help and braid --help exits 0, so the success criterion holds. The test's five-option scope is exactly what the PRD Phase 0 task specifies. Recorded in the settled-decisions ledger as discarded.

### [autonomous] 2026-09-07T02:53:54Z

**Decision**: New --agents-root/--claude-root/--config-root help strings name the default path but omit the env-var precedence ("ahead of AGENTS_ROOT") that the PRD Must-have contract and the README table both state

**Choice**: auto-fix

**Rationale**: Low severity, any consensus -> auto-fix. The PRD Must-have wording is explicit about precedence, so the help text should carry it. Folded into the same cycle-1 rework task [D1].

### [autonomous] 2026-09-07T02:53:54Z

**Decision**: PRD success criterion "no product code is touched" contradicts its own Phase 0 task, which modifies cli.py (raised by BLAKE)

**Choice**: no-action

**Rationale**: Spec wording defect, not an implementation defect. Blake verified the intent (no behavioral change) holds: the diff touches argparse metadata only. Editing a wip PRD's success criteria mid-review to match the code would erase the record of what was actually asked for, so no code and no PRD change. Recorded in the settled-decisions ledger so it is not re-argued next cycle.

### [autonomous] 2026-09-07T02:53:54Z

**Decision**: New CHANGELOG bullet (line 53) uses an em dash, violating the standing writing rule in rules/writing.md ("Never use em dashes")

**Choice**: auto-fix

**Rationale**: Standing rule mandates the change, so per AGENTS.md the reversible artifact is produced rather than asked about. Verified the em dash is introduced by THIS diff at CHANGELOG.md:53; the other four in the file (74, 83, 101, 111) are pre-existing and out of scope. Routed to the converged cycle-2 tail sweep as task [D2].

### [autonomous] 2026-09-07T02:53:54Z

**Decision**: The CHANGELOG second new bullet documents task 2/3 README changes that shipped as docs commits, so it is backfill beyond task 4 stated scope (raised by ALICE)

**Choice**: discard

**Rationale**: Premise checked, not taken on the reviewer word. rules/changelog.md says docs commits do NOT require an entry; it does not forbid one. The bullet landed in commit 2bca306 whose type is fix(braid), and a fix commit does require an entry. Substantively it documents a real user-visible fix (the README named a backup path that did not exist, the PRD whole premise), so deleting it would lose the record of that fix and make the changelog worse. Alice rates it harmless and accurate. Recorded in the settled-decisions ledger as discarded.

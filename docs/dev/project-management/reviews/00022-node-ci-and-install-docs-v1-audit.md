# Decision Audit Log: 00022-node-ci-and-install-docs-v1

PRD: `00022-node-ci-and-install-docs-v1.md`
Started: 2026-09-06T20:44:24Z
Completed: 2026-09-06T20:44:24Z
Autonomous: 2  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-06T20:44:24Z

**Decision**: BOB: brief-portfolio Tests block runs test:browser without an executable chromium-install step; the trailing `npx playwright install chromium` is only a comment

**Choice**: discard

**Rationale**: Out of PRD scope, verified against files: package.json defines `test` and `test:browser` as separate scripts, the PRD contract command is `npm ... test` (module install / ERR_MODULE_NOT_FOUND), CI runs only `test` (ci.yml:120-129, no test:browser), and the test:browser line already documents the chromium install inline as a one-time step. The proposed fix would make every Tests run attempt a ~150MB download. Ledgered.

### [autonomous] 2026-09-06T20:44:24Z

**Decision**: BOB: cannot statically verify the node job four npm commands on a clean Node 24 Ubuntu checkout

**Choice**: discard

**Rationale**: Not a defect: the sandbox-limitation line bob.md mandates for runtime criteria. Alice, Blake and Carl each ran both suites at this HEAD (44/44, 48/48, exit 0), matching the recorded verification at the same sha. The hosted-runner residual cannot be checked by any local command and the PRD Risks section assigns it to human follow-up, gating nothing. Not queued as a verification check: names an environment, not one runnable command. Ledgered.

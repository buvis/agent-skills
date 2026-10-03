# Decision Audit Log: 00007-extract-memory-candidates-from-transcripts-v1

PRD: `00007-extract-memory-candidates-from-transcripts-v1.md`
Started: 2026-08-30T04:28:05Z
Completed: 2026-08-30T04:28:05Z
Autonomous: 12  |  Deferred: 3  |  Doubts: 0

### [autonomous] 2026-08-30T04:28:05Z

### [autonomous] 2026-08-30T04:28:05Z

### [autonomous] 2026-08-30T04:28:05Z

### [autonomous] 2026-08-30T04:28:05Z

### [autonomous] 2026-08-30T04:28:05Z

### [autonomous] 2026-08-30T04:28:05Z

### [autonomous] 2026-08-30T04:28:05Z

### [autonomous] 2026-08-30T04:28:05Z

### [autonomous] 2026-08-30T04:28:05Z

### [autonomous] 2026-08-30T04:28:05Z

### [autonomous] 2026-08-30T04:28:05Z

### [autonomous] 2026-08-30T04:28:05Z

### [deferred] 2026-08-30T04:28:05Z

**Decision**: judge() passes slice text as a literal CLI argument rather than via a temp file with -f, departing from the dispatch-contract convention. No injection risk (list-form argv, no shell=True); the residual is an ARG_MAX ceiling on a very long assistant text block.

**Rationale**: Cycle 1: deferred to PRD 00008. The inline-argument shape is what this PRD design doc signed verbatim, and judge() is the one cross-PRD contract this design names (00008 imports it and calls it with tier=strong). Changing its subprocess I/O is an 00008 design decision, not a 00007 rework item. Also recorded in the review ledger as a settled deferral so it is not re-argued next cycle.

### [deferred] 2026-08-30T04:28:05Z

**Decision**: PRD Phase 1's literal Exit Criteria command `uv run --with pytest pytest scripts/test_funnel.py` no longer runs: the file was split into test_funnel_extraction.py, test_funnel_report.py and test_funnel_triage.py during cycle-1 rework. All 79 funnel tests pass across the three files, so coverage is intact.

**Rationale**: Accepted divergence, settled at the cycle-2 gate. The split was forced by the repo's 800-line hard cap (the file stood at 799), which the PRD's Structural Decomposition predates. Editing a wip PRD's spec to match the code is the wrong direction, so the divergence is surfaced here for the human instead.

### [deferred] 2026-08-30T04:28:05Z

**Decision**: PRD Module Exports names `assert_contract(version)`, but the shipped signature is `assert_contract(version, parser_module, minimum=_MIN_VERSION)`. A caller following only the terse Exports line would hit TypeError.

**Rationale**: Accepted divergence, settled at the cycle-2 gate. The PRD's own Behavior prose for this feature mandates the symbol assertion that needs parser_module, and the design doc signed the two-argument signature verbatim. Defaulting parser_module would reintroduce the double parser resolution cycle 1 fixed.

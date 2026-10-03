# Decision Audit Log: 00008-distil-memory-proposals-v1

PRD: `00008-distil-memory-proposals-v1.md`
Started: 2026-08-30T20:38:12Z
Completed: 2026-08-30T20:38:12Z
Autonomous: 8  |  Deferred: 2  |  Doubts: 0

### [autonomous] 2026-08-30T20:38:12Z

### [autonomous] 2026-08-30T20:38:12Z

**Decision**: The task Details say the intra-run stem-collision count must be returned to the caller or exposed alongside the return, but the verbatim contract signature is write_proposals(...) -> Path and its docstring says Returns the published out_dir. Which wins?

**Choice**: The verbatim signature wins: write_proposals returns Path only. The collision count stays derivable from proposals.json - a record whose file stem differs from sanitise_name(name) is one collision. Changing the return type would contradict the copy-exact-names instruction the task opens with.

### [autonomous] 2026-08-30T20:38:12Z

**Decision**: render_yield's new_vs_update key: does counts carry a pair (3, 1) or a pre-formatted string "3/1"? The contract pins the rendered form <int>/<int> and says each line reads one counts.get(key), which admits both.

**Choice**: counts carries a 2-sequence (new_count, update_count) and render_yield formats it as f"{v[0]}/{v[1]}", rendering n/a when the key is missing or None. Chosen because render_yield is documented as pure string formatting and the other four new keys are raw ints; a pre-formatted "3/1" would move presentation into the caller and contradict that docstring.

### [autonomous] 2026-08-30T20:38:12Z

**Choice**: Task 9 (Wire the distil stage into funnel.main()) MUST carry tests for it: main(["--distil"]) over a one-slice corpus with a stubbed distiller asserting integer distil counts in the report and a proposals directory on disk, and --distil-limit 1 over two durable slices asserting skipped_by_limit: 1.

### [autonomous] 2026-08-30T20:38:12Z

### [autonomous] 2026-08-30T20:38:12Z

### [autonomous] 2026-08-30T20:38:12Z

### [autonomous] 2026-08-30T20:38:12Z

### [deferred] 2026-08-30T20:38:12Z

**Decision**: Judge calls persist session transcripts into the corpus future runs scan (self-ingestion): 153 -> 474 selectable transcripts across the task-11 run.

**Rationale**: The fix belongs to funnel.judge, untouched by this diff and shipped by slice 1 (PRD 00007); shared with triage. Out of PRD 00008 scope, needs its own PRD.

### [deferred] 2026-08-30T20:38:12Z

**Decision**: The calibration-corpus contract test skips when the private memory plane is absent, so CI never exercises corpus compatibility.

**Rationale**: Decided at the design gate: an anonymised hermetic fixture was proposed and deliberately not built in this slice.

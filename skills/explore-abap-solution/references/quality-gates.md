# Quality Gates & Validation Specs

Detailed specifications for gates, snippet banking, bug hunting, and self-check fixes.
Referenced from the main SKILL.md during Phases 2, 3, and V.

## Bug Hunting Anti-Patterns

Specific anti-patterns to check in EVERY object opened deep:

- **Wrong variable used:** parameter A read where parameter B was intended (copy-paste from a sibling handler — the #1 real-world handler bug)
- **Self-comparison:** `x <> x` (always false), `x = x` (always true) — usually a copy-paste where one side should be a different variable
- **Swallowed exceptions:** `TRY ... CATCH cx_root. ENDTRY` with empty/no-op CATCH — logic proceeds with uninitialized data
- **Timeout misuse:** infinite timeouts hardcoded, timeout parameters accepted but ignored on some code paths
- **Dead code:** methods that compute a result into a local variable but never return/export it; serialization to a local that's never assigned to the actual result
- **Type mismatches from copy-paste:** using types/constants from the SOURCE handler instead of the correct domain (one domain's types or constants left in another domain's handler)
- **Hardcoded credentials:** commented-out or active passwords, API keys, client secrets in source — always HIGH severity
- **Timestamp arithmetic:** ABAP timestamps (YYYYMMDDHHMMSS packed) treated as integers for duration calculation — simple subtraction is not valid duration math
- **Dynamic SQL / string-interpolated WHERE:** SQL injection surface even if low practical risk
- **Missing 404 check:** service returns INITIAL structure, handler serializes empty payload as 200 instead of detecting "not found"

A CORE utility class (outbound HTTP client, token handler, base class) deserves EXTRA scrutiny — these are called by every implementation, so their bugs multiply. Reading one and noting "legacy code style but functional" is the tell-phrase of a shallow read that misses exactly these defects.

## Snippet Fetch Receipt Format

Exact format — `check_run.py` validates:

```
" Fetched: <tool_name> <ISO-timestamp> <system_id> — <OBJECT_NAME>
```

- The FIRST LINE of the file. Not line 2, not after a comment block.
- Starts with `"` (ABAP comment character), then a space, then `Fetched:`.
- No `*`-style comment blocks, no `*---` banners, no blank lines before it.
- Illustrative receipt, not a captured fetch: `" Fetched: read_source 2026-07-23T13:02 DEV — ZCL_EXAMPLE_HANDLER`
- The script checks: `"Fetched:" not in read(file)` → FAIL. A `*------` header that doesn't contain the literal string `Fetched:` will fail.

## Minimum Snippet Bank (Phase 2 Contract)

The bank must contain AT MINIMUM:

- The **blessed exemplar** — FULL source (definition + implementation), the exact object named in §6 Evolution. This is what the document run's quick-start copies verbatim. Non-negotiable.
- The **dispatcher/router/kernel** — the object that turns config into dispatch (the first CORE deep-read).
- **One exemplar per distinct pattern** in the taxonomy — the object NAMED as that pattern's reference implementation. Banking a different sibling does not satisfy it.
- **Every service/contract interface** that defines the extension API (the method signatures implementers must satisfy). These define how to write new implementations; without them banked, the quick-reference and cookbook ship type-guesses.
- **Every buggy block** cited in the register — the offending lines plus enough surrounding context to understand the fault.
- **One multi-verb handler** if the solution has POST/PUT/DELETE (the mechanics of body parsing, content-type validation, and error responses differ from GET and need a copy-this exemplar).
- **One outbound/integration exemplar** if the solution calls external systems (OAuth, RFC, HTTP — the outbound plumbing is its own pattern).

A bank with fewer files than patterns is INCOMPLETE by construction. Count patterns, count snippet files, report both in the PATTERN GATE.

## Coverage Gate Conditions

Pass conditions, ALL required:

- **No `pending` rows.** Every ledger row ends `read-deep`, `read-delta`, `classify`, or `blocked: <reason>`. The status `inferred` is NEVER acceptable as a final status — it means the object was not verified. If you cannot read an object, it is `blocked`; if you can read it, read it and assign a real status. **This includes INFRA objects** (RFC providers, token handlers, URI providers, config classes) — they are usually small and fast to read. Leaving them pending because "they are not handlers" is the #1 cause of gate FAILs on resume. Read them in the same pass as their handler; update the row immediately.
- **Source-read: ALL registered implementations** (deep+delta). When a registry exists and its rows are known, every listed implementation must be source-read — the 60% floor applies ONLY to registry-less solutions with an uncertain population. The primary implementation of every domain is read deep (you cannot bless code you did not read).
- **Registry read:** the rows of every discovered registry/dispatch table were actually obtained (SELECT, data preview, RFC read, or a user-provided export). A run that found a registry but never read its rows CANNOT pass this gate.
- **Registry closed:** every row resolves to an inventory object or a registered-but-missing finding.
- **Ledger rows = census in-scope:** the per-object ledger has exactly as many rows as the CENSUS `in-scope` number, each with a final status. A ledger shorter than the census (or replaced by a status-summary table) means objects were dropped without an exclusion row — report the count ("ledger 131/131").
- **Cards match the ledger:** every read row has a card; count them from a directory LISTING in that turn ("cards 24/24"), never from memory. A card count that exceeds the ledger row count means sub-components leaked in as rows — one object is one row, its parts live inside its card.
- **Tiers are honest:** classify rows contain only stubs, generated halves, and DDIC structures actually opened; a real implementation sitting in classify must be re-tiered to read-delta (or blocked if unreadable).
- **Discovery lines exist** with raw and post-filter counts; the arithmetic closes (raw custom = in-scope + excluded); the `CENSUS:` line parses.
- **Discovery output is ledgered:** every object any method reported is a ledger row or a named exclusion — containers expanded to their object lists. Prose mentions that never became rows are the quietest way to shrink scope.
- **IMPL exists** — or notes.md records an explicit kernel-less determination with evidence. Zero IMPL while a registry was discovered is an automatic FAIL.
- **Sweep log complete:** every line in the sweep checklist shows a result ("checked, none found" or a specific finding). A sweep heading with "not yet started" or "pending" items is FAIL — the sweep is part of Phase 2, not an optional post-gate activity.

### Gate Report Format

The report MUST contain a line starting with exactly `GATE: PASS` or `GATE: INCOMPLETE` — no other format satisfies the script.

Do NOT use: `### COVERAGE GATE — PASS`, `Coverage Gate: PASS`, `GATE: PASS (with caveats)`, or any variant. The exact literal `GATE: PASS` or `GATE: INCOMPLETE` on its own line.

`GATE: PASS` means every condition above passed with zero exceptions. Any exception → `GATE: INCOMPLETE` with the failing conditions listed below it.

**Qualified passes are failures:** "PASS (registry degraded)" is a FAIL wearing a PASS label — the self-check rejects `GATE: PASS (`. If a condition fails you have exactly two moves: keep reading (batch the remaining objects, re-run the gate — the default), or declare INCOMPLETE (only when access is blocked or budget truly exhausted). **Unattended runs:** a condition that can only be met by asking the user FAILS — declare INCOMPLETE with the exact question in the resume list. A run with any degradation cannot report "Open questions: none".

**Incomplete mode:** the run still finishes and ships an honest package: notes.md opens with `Status: INCOMPLETE`, the unread domains are listed, stub cards mark the gaps, and the resume list names the specific asks. A partial package that says so is a success; a partial package that reads as complete is the core failure this skill fights.

## Pattern Gate Conditions

Every IMPL maps to a pattern or is a named stub/dead object; **the specific object each pattern NAMES as its reference implementation is banked** — banking a different sibling in the same family does not satisfy it (name object A as the pattern's reference, bank object A, not its cousin B), and the blessed pattern is banked without exception; the primary trace is evidence-complete.

Report per-pattern snippet counts from LISTING `research/snippets/` and naming the files, and confirm each named reference implementation appears in the list — a gate that reports exemplars the directory does not hold, or counts a variant for the named one, is a false report.

### Blessed-Exemplar Verification (Pattern Gate Sub-Check)

The blessed exemplar named in §6 Evolution must appear VERBATIM in a snippet file (not merely referenced by a card or mentioned in a pattern table). Verify by:
1. Identify the exact object name on the "blessed pattern" / "reference implementation" line
2. Grep `research/snippets/` for that EXACT name in a `" Fetched:` receipt line
3. Confirm the snippet contains the object's FULL source (definition + implementation sections, not just a few methods)

A snippet containing a DIFFERENT object (banking a sibling while naming a different object as blessed) does NOT satisfy this — the check is name-exact. If the blessed exemplar is not yet banked when you reach this gate, BANK IT NOW before reporting PASS.

## Sweep Log Checklist

The following lines must appear in §4, each with "checked" or a finding — "not yet" / "pending" / blank is a gate FAIL:

- Authority checks (grep result: objects checked, or "none found in the solution — security relies on X")
- LUW/Commit discipline (COMMIT WORK / ROLLBACK / IN UPDATE TASK — present where and owned by whom, or "none — stateless by design")
- Locking (ENQUEUE/DEQUEUE or "none")
- Dynamic dispatch points (CREATE OBJECT TYPE (variable) / CALL METHOD dynamic — where config becomes runtime)
- Tests (per-class: real / stub / none — plus any test framework or fixture patterns found)
- Local classes (any business logic hiding in Local Types / CCDEF / CCIMP that the cards didn't already cover)
- Cross-references outside the main package tree (which objects reach into which external packages, and for what)
- Macros, transformations (XSLT/ST), app-log usage — present or "none found"

## Phase V: Self-Check Fix Guide

Common FAILs and their fixes:

- **`ledger has no pending rows`** — The regex `^\s*\|.*\bpending\b` is FILE-WIDE, not scoped to §3. It catches ANY markdown table row containing the word "pending" ANYWHERE in notes.md — including pattern taxonomy tables, sweep items, or prose tables. Fix: resolve all INFRA/support objects left pending in the ledger (read them — they are usually tiny), AND grep the entire file for `| pending |` or `pending` in any table cell. Use "unread" or "not yet read" in non-ledger tables, never the literal word "pending".
- **`blessed exemplar is banked`** — The script greps snippet files for the exact object name from the "blessed" line in §6. Banking a sibling does NOT satisfy it. Fix: `get_source` the named blessed object and write its FULL source to a snippet file with a fetch receipt. Do this in Phase 3 §6 IMMEDIATELY after naming the blessed pattern — not later.
- **`snippets carry fetch receipts`** — Every `.abap` file in `research/snippets/` must begin with a line matching `Fetched:`. Comment-block headers, asterisk banners, or ABAP doc headers all FAIL. Fix: the FIRST LINE of every snippet file is exactly: `" Fetched: <tool> <timestamp> <system> — <object_name>`
- **`coverage gate report`** / **`pattern gate report`** — The script looks for `GATE: PASS` or `GATE: INCOMPLETE` (exact prefix, case-insensitive). A prose heading like "### COVERAGE GATE — PASS" does NOT satisfy it. Fix: every gate report must contain a line starting with `GATE: PASS` or `GATE: INCOMPLETE` (no qualifiers after PASS).
- **`STATUS unqualified`** — "COMPLETE — 71/73" is qualified. The only valid values are bare `COMPLETE` or `INCOMPLETE`. Any text after COMPLETE (counts, qualifiers, explanations) makes it qualified → FAIL.
- **`gates unqualified`** — `GATE: PASS (registry degraded)` is qualified. Anything in parentheses after PASS is a FAIL. Either the gate passes cleanly or it's INCOMPLETE.

### Pre-Validation Checklist

Run mentally before invoking the script:

- [ ] Every ledger row has a final status (grep `| pending |` in §3 — ZERO hits)
- [ ] The word "pending" does not appear in ANY table row in the entire file (grep file-wide)
- [ ] Both gate reports contain a `GATE:` line (not just a heading)
- [ ] The blessed exemplar (exact object from §6) has its own snippet file with a fetch receipt
- [ ] Every snippet file's FIRST LINE starts with `" Fetched:`
- [ ] No qualifier text follows `GATE: PASS` or `Status: COMPLETE`

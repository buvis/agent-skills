---
name: explore-abap-solution
description: Use when exhaustively exploring an ABAP solution into a validated research package (census, ledger, object cards, verbatim snippet bank) - the input for document-abap-solution. Triggers on "explore abap solution", "research abap framework".
compatibility: "Portable; needs Python 3.12+ and a caller-supplied read-only SAP source/search provider (no provider ships here)."
---

# Explore ABAP Solution

Explore ANY ABAP solution exhaustively and produce a **validated research package**: a measured census, a complete object ledger, per-domain object cards, a verbatim snippet bank with fetch receipts, a pattern synthesis, and a bug register — everything on disk under `research/`.

**This skill produces research, not documentation.** The sibling skill `document-abap-solution` turns the finished package into the developer onboarding docs and explorer SPA, and it can only embed what this skill banked. The split is deliberate: exploration succeeds honestly in one session; writing succeeds honestly only from finished research. Do not write README/architecture/cookbook/reference files in this skill — a run that starts writing docs has left its contract.

Works for anything written in ABAP, however it is structured: REST/HTTP API frameworks, batch and interface engines, BAdI/enhancement architectures (including CMOD exits, VOFM routines, BTEs), IDoc integration layers, workflow frameworks, output/forms solutions, report suites, dialog and ALV cockpits, ABAP-proxy/SOAP interfaces, BDC/conversion suites, BW extractor stacks, RAP/CDS stacks, utility libraries, legacy procedural solutions (include-based programs, function-group APIs, payroll schemas and PCRs, infotype frameworks), and organically grown collections with no framework at all. The methodology is paradigm-neutral; only the examples are concrete.

## Dependencies

- **A runner able to complete the evidence checks.** Record the model/client in `research/notes.md` §1. Do not infer correctness from a model tier; stop with an explicit incomplete report when the runner cannot finish the required reads and checks.
- **SAP read access** through whatever this session has: ADT/RFC MCP tools, CLIs, or an abapGit-style source dump from the user. Reading source somehow is a hard requirement; without any path to source, stop and ask. Table-row access and where-used are degradable (fallbacks in `references/exploration-tactics.md`).
- **Python 3.12+** for the package self-check `scripts/check_run.py --research-only` (in `scripts/` next to this SKILL.md). When it cannot run, record WHY (missing script means the skill copy is incomplete; tell the user). Manual inspection is not a substitute for a passing automated gate.
- **This skill's references:** `references/exploration-tactics.md` (read when Phase 0 starts, stays loaded through Phase 2) and `references/quality-gates.md` (read when entering Phase 2's depth-reading loop — contains bug anti-patterns, snippet specs, gate conditions, sweep checklist, and self-check fix guide). Both live in the `references/` subdirectory next to this SKILL.md; find them via the skill's own path or glob `**/explore-abap-solution/references/*.md`. Log the outcome in `research/notes.md` as a `References loaded:` line (or `unavailable: <error>`) — the self-check requires it.
- **Multi-session resume** (for Large solutions >40 objects). Use the session's SAP reader. Read in groups of 10-15, write cards and snippets continuously, and save a Resume Point before context exhaustion. Start a fresh session with this skill and the same output directory, then resume from the ledger. No separate launcher is required or included.

`read_source`, `search_objects`, `read_type_hierarchy`, and
`read_cross_references` below are capability labels, not callable tool names.
Discover and record the actual provider's schemas before use. In particular,
`subTypes`/`superTypes` describe directions; translate them to the provider's API.
All example identifiers and receipts in these skill files are illustrative,
not captured SAP evidence.

## First-Run Welcome

When triggered without a clear target:

> **I can research any ABAP solution in your SAP system into a validated research package** (which `document-abap-solution` then turns into onboarding docs + an interactive explorer).
>
> Point me at any entry point:
> - **A package** - "explore abap solution in package ZBATCH_ENGINE"
> - **A config/registry table** - "explore everything registered in ZIF_STEPS"
> - **A base class or interface** - "explore the framework built on ZCL_JOB_BASE"
> - **A function group or program** - "explore the payroll driver ZEXAMPLE_DRIVER" (legacy procedural is fine)
> - **A transaction, job, or service** - an ICF path, an OData service, "what runs behind ZEXAMPLE_COCKPIT"
> - **An enhancement spot, BAdI, or user exit** - "explore the implementations of ZEXAMPLE_SPOT"
> - **A runtime artifact** - an ST22 dump, IDoc number, spool output, workflow item
> - **A ticket** - "I need to work on PROJ-123, explore the framework it touches"
>
> I pause exactly once — after measuring the solution's census — to confirm the scope boundary with you. Everything after your answer runs to completion.

## Running Examples

Nine fictional solutions illustrate instructions throughout this skill and its reference. **Specifics illustrate; they never constrain.**

| Tag | Shape | Registry truth | Unit of extension |
|---|---|---|---|
| API | REST endpoint framework | table maps path+verb to handler class | handler class + registry row |
| BATCH | nightly interface engine | table maps sequence to step classes | step class + step row |
| BADI | pricing enhancement set | BAdI implementations with filters | filtered implementation |
| RAP | Fiori order stack | behavior definition + service binding | action/validation in behavior pool |
| LEGACY | payroll calc program | schema/PCR customizing + conditional includes | operation FORM in a country include |
| COCKPIT | ALV/module-pool cockpit | GUI statuses + selection variants + TVARVC switches | toolbar function code + column + its handler |
| OUTPUT | NAST-driven forms output | condition records + TNAPR map output type to print FM + form | output type + print FM + form |
| FLOW | approval workflow | SWE2 event linkage + task/agent customizing | task + handler method + linkage row |
| PROXY | SOAP/PI interface layer | SPROXY service interfaces + logical ports | provider method in the proxy's Z-implementation |

In procedural solutions the "objects" are programs, includes, FMs, and FORMs: the TOP include is the attribute list, FORMs are the methods, the include hierarchy is the class hierarchy. Same methodology, different units.

## Deliverables — the research package

```
research/
  notes.md            the run's state and audit trail, in this order:
                      Status / Runner / References loaded / Scope decision
                      §1 Access & Target (capability map + ACCESS RECEIPT)
                      §2 Census (raw per-method outputs + CENSUS line)
                      §3 Ledger (one row per object, final statuses)
                      §4 Sweep log        §5 Bug register
                      §5b Technical debt (design issues, inconsistencies,
                          portability problems — distinct from bugs)
                      §6 Pattern synthesis (taxonomy, techniques, traces,
                         capability matrix, conventions, evolution)
                      §7 Gate reports (coverage + pattern)
                      §8 Validation Report (self-check output verbatim)
                      §9 Open questions / Resume Point
                      §10 Corrections log (self-corrections made during analysis)
  {domain}.md         per-object cards for one domain (queryable exploration log)
  snippets/           verbatim source bank: every file opens with a
                      `" Fetched: <tool> <timestamp> <system> — <object>` receipt
```

Nothing else. The package is complete when `check_run.py --research-only` passes and Status is COMPLETE — that is this skill's definition of done. The final report tells the user to run `document-abap-solution` on the output directory next.

## Process

### Phase 0: Access & Target

Read `references/exploration-tactics.md`. Then:

1. Detect SAP access tools; map them to capabilities (access table in the reference). Record degradations in `research/notes.md`. **Then prove access with a live probe:** fetch the source of one seed object NOW and record its first lines in `research/notes.md` as the access receipt (object name, timestamp, first 3-5 source lines verbatim). No successful probe means no access — stop and ask; never proceed on assumed or remembered access.
2. Resolve the user's entry point to a seed object set (entry-point table in the reference).
3. Confirm output directory. Default: `./onboarding-<solution-slug>/`.
4. **First write of every run:** create `research/notes.md` NOW — access map, entry point, empty ledger. Every later phase appends to this file. A run that produces conclusions without `research/notes.md` did not execute this skill.
5. **Refresh mode:** if the output directory already holds `research/notes.md` with a ledger, this is an update run: diff current change stamps against the ledger, re-read only new and changed objects, update only affected cards and snippets (procedure in the tactics reference). The final report lists what changed.

Missing information: ask one question at a time, only what cannot be inferred.

### Phase 1: Boundary & Inventory

1. Run the boundary closure from the reference: expand the seed set along inheritance, implementation, composition, calls, config reads, registration, and trigger edges until fixpoint.
2. **Config defines the boundary, not the package tree.** If a registry table references classes in five other package trees, all five are in scope.
3. **SELECT every registry table NOW.** The registered implementations ARE the solution — the seed package is usually just dispatch plumbing. **When SELECT is not available**, ask the user for an SE16 export of the specific registry table — name the table and the columns you need.
4. **Walk the trigger chain** (procedure in the reference): from every external trigger follow source to the object where config becomes dispatch. A config table's role is defined by the code that reads it, never by its name or columns.
5. **Apply every discovery technique** (procedure in the reference): subclass sweeps of every shared base, wildcard naming searches, package listings. These complement config reads — they may reveal unregistered, WIP, or differently-dispatched implementations.
6. Classify every object: CORE / IMPL / INFRA / HOOK / EXT / OUT. For procedural solutions, inventory the includes with sizes. CORE may come up empty: "no shared kernel" is a finding, not a failure.
7. Initialize the ledger as a real table: **one row per in-scope object**, columns `object | domain | status | tier | pattern`, every status `pending` at first. It is a per-object table, never a summary — a row count that does not equal the CENSUS `in-scope` number means objects are missing or collapsed. "The ledger is the union of the `###` cards across the domain files" is NOT a ledger: the coverage gate's "cards match the ledger" check needs a single enumerable table to diff the cards against, and the resume protocol needs one row to point at. Sub-component detail belongs in the card, not as extra ledger rows — one object, one row.
8. Report per-method yields: "Discovery: registry rows → R, subclass/hierarchy → H raw / h ledgered, naming-search (patterns tried: ...) → N." A missing method line means the method was not applied; "attempted, unavailable because <reason>" is a valid line, silence is not.

**THE CENSUS (Phase 1's contract — scope is measured, never assumed):**

1. **Enumerate.** Paste each discovery query's RAW result into `research/notes.md` — tool called, timestamp, verbatim head, total count. You may not summarize a query you have not pasted; a filter may classify listed hits, never shrink a query or a listing.
2. **Ledger.** Every custom-namespace hit becomes a row: in-scope, or OUT/excluded with a named reason. Close the arithmetic in one machine-checked line: `CENSUS: raw=<N> custom=<C> in-scope=<S> excluded=<E>` with C = S + E — `check_run.py` parses it. The terms are defined across ALL discovery methods together: `raw` = the sum of every method's raw hit count (duplicates included); `custom` = the DEDUPLICATED union of custom-namespace objects found by any method — one object counted once however many methods found it. Every member of that union is a ledger row; that is what makes C = S + E close. A `custom` computed from one method's hits while in-scope draws on the others can never close and means the union was never built.
3. **Validate existence.** Every object that enters the ledger MUST be validated for existence against the reference SAP system — via `search_objects`, `read_source`, or any tool that confirms the object is real. Objects inferred from naming conventions (e.g. "this family has _H00 so _H01 through _H03 probably exist") are **not ledger entries until verified.** Record the validation in `research/notes.md` as a `### Existence Validation` sub-section under §2 Census, listing each object's verification method and result (e.g., "ZCL_FOO: confirmed via search", "ZCL_BAR: confirmed via get_source", "ZCL_BAZ: NOT FOUND — removed from ledger"). This validation is checked by `check_run.py`. An object that was never verified against the system is an invented name and must not appear in the ledger, the cards, or any downstream documentation — regardless of how plausible the naming convention makes it.
4. **Bound.** Membership is structural: an object is in the solution when it hangs off the solution's kernel — dispatched by its dispatcher, registered in its registries, inheriting its bases — never merely because it shares a namespace. A cluster with its own kernel and registry is a neighbor: name it, count it, exclude it with a pointer.
5. **Ask — the mandatory Phase-1 checkpoint.** In an attended session, ALWAYS stop here, once, whatever the census size: present the access receipt, the `CENSUS:` line, and ONE question carrying the census numbers and concrete boundary options — whole solution / entry family + kernel with every other family excluded by name and count / corner only, declared INCOMPLETE-by-scope — then wait. Record the answer as a `Scope decision: <choice> (user, <timestamp>)` line, quoting the user's words. **This is the ONLY pause in the entire run.** Unattended: do not wait — write `Scope decision: <middle option> (unattended default)`, put the scope question at the top of the resume list, and continue.
6. **Size.** Small/Medium/Large is an OUTPUT of the census, cited with its number. A sizing sentence written before the `CENSUS:` line exists is invalid, and the Effort table may not be consulted before that line is on disk.

**Tell-phrases (stop signs):** "I have a thorough understanding", "this is a focused/small solution", "sufficient information gathered", "the remaining objects follow the same pattern", "confirmed by package listing", "pattern confirmed uniform", "mechanical repetitions", "no new patterns expected", "diminishing returns" — written before the census receipt exists, every one of these preceded an under-scoped run. Stop and run the census. **In Phase 2, the same phrases are premature-stop excuses** — they precede an under-READ run. The remedy is the same: stop rationalizing and keep reading.

### Phase 2: Exhaustive Exploration

Three principles predict quality:

1. **Read means FETCHED IN THIS RUN.** Knowledge from earlier sessions, conversation context, or prior documentation is memory, and memory drifts. Prior documentation found ON DISK (an earlier onboarding package, a wiki export, another run's output directory) is the same memory in file form: a card built from it is unverified, its code never enters the bank, and one document citing another document is not confirmation of anything. If access dies mid-run, the two honest moves are pause-and-resume or declare INCOMPLETE — a fallback to prior docs relabeled as research is fabrication wearing provenance. **"Inferred from pattern-sibling" is not a status — it is an excuse for not reading.** Every object gets opened: if it responds, assign read-deep or read-delta; if it doesn't respond, assign blocked. There is no middle ground.
2. **Hunt bugs actively.** Check every object for copy-paste errors, wrong variables, dead code, no-op logic. Zero bugs found means the exploration was superficial. Every bug entry cites the offending lines verbatim, banked in snippets — a "bug" without reproducible evidence goes to the debt list, and hedge-words (likely/probably/presumably) in the register fail the self-check. **Read `references/quality-gates.md` § Bug Hunting Anti-Patterns** for the full checklist of specific patterns to hunt in every deep-read object.
3. **Honor the committed count.** Every object gets a final ledger status; nothing disappears silently. Update the ledger row in the same turn the object is read.

**Depth policy:** visit 100% of the inventory; calibrate depth with the read tiers (deep / delta / classify) from the reference. Kernel (CORE) first, always deep. As you read, append a card to the matching `research/{domain}.md` and bank verbatim source in `research/snippets/` — each snippet file opens with its `" Fetched:` receipt, written at banking time. Code that is not banked cannot appear in the future docs. Never batch cards or snippets to the end.

**Snippet fetch receipt format and minimum snippet bank:** see `references/quality-gates.md` § Snippet Fetch Receipt Format and § Minimum Snippet Bank. Every snippet file's first line must be the fetch receipt; the bank must cover at minimum the blessed exemplar, dispatcher, one exemplar per pattern, every contract interface, every buggy block, and (where applicable) a multi-verb handler and an outbound exemplar. A bank with fewer files than patterns is INCOMPLETE by construction.

**Service interfaces / contract types (read alongside the implementing class):** When reading an implementation that instantiates or references a service interface (`ZIF_*_SRV`, `ZIF_*_API`, or any interface the implementation is typed to), READ that interface's source too — its method signatures define the layer's API contract, its type definitions reveal the data structures, and its pagination/filtering parameters expose architectural decisions (offset vs cursor, flat params vs structure). Record service interfaces as their own cards (tier: read-deep, classification: INFRA), and bank the interface source for any service that defines shared types or whose method signatures are non-obvious. A cross-domain inconsistency (say, two domains paginating differently) only emerges by comparing read interface sources — it cannot be inferred from implementation code alone.

Also in this phase, per the reference: the **hidden-corner sweep** (log every check, including "none found" — the sweep log must be COMPLETE before the coverage gate; a sweep log that says "not yet started" or "pending" when the gate runs is a FAIL — see `references/quality-gates.md` § Sweep Log Checklist for the full required list), **config is truth** (SELECT actual rows), the **dynamic-call hunt**, **forensics** (creation dates → generations → the blessed modern pattern), **tests** (read them; classify real / stub / none), **access barriers** (record `blocked`, infer from siblings at LOW confidence, ask to re-authenticate — never silently skip), and the **batch-and-resume protocol** for large solutions.

**COVERAGE GATE (hard stop before Phase 3).** Full conditions in `references/quality-gates.md` § Coverage Gate Conditions. Summary of pass requirements:

- No `pending` ledger rows (includes INFRA objects — read them, they're tiny)
- ALL registered implementations source-read (deep+delta)
- Registry rows actually obtained (SELECT/export) and every row resolves
- Ledger row count = census `in-scope` count (report "ledger N/N")
- Cards match the ledger (count from LISTING, report "cards N/N")
- Tiers are honest (no real implementations hiding in classify)
- Discovery lines exist with closing arithmetic; CENSUS line parses
- IMPL exists (or explicit kernel-less determination with evidence)
- Sweep log complete (every checklist item has a result — see `references/quality-gates.md` § Sweep Log Checklist)

The gate report echoes EVERY condition with its numbers. Gate report must contain a line starting with exactly `GATE: PASS` or `GATE: INCOMPLETE` — see reference for format rules and qualified-pass rejection.

**Incomplete mode:** the run still finishes and ships an honest package: notes.md opens with `Status: INCOMPLETE`, the unread domains are listed, stub cards mark the gaps, and the resume list names the specific asks. A partial package that says so is a success; a partial package that reads as complete is the core failure this skill fights.

### Phase 3: Pattern Synthesis

Artifact-producing: everything lands in `research/notes.md` §6, not in silent analysis turns.

1. **Pattern taxonomy:** group implementations by structure. Every pattern claim cites a concrete name, the defining trait, a usage count counted from ledger rows, and one reference implementation. Every object name in a pattern, technique, trace, or convention table is COPY-PASTED from a ledger row or card — never typed from memory. A name "reconstructed" from the naming convention is invention even when the pattern is real; an unknown real name is a ledger gap to fill, not a blank to autocomplete.
2. **Technique inventory:** within the dominant pattern, enumerate the distinct mechanics implementations actually use, one exemplar object each.
3. **Lifecycle traces:** one numbered end-to-end trace per paradigm with real `object.method` names; every step cites source read in Phase 2.
4. **Capability matrix:** the framework surface (every overridable method, every config option) marked used / partial / unused with the using class — from READ base source only, in both directions (absence of an example proves nothing; a listed method never seen in read source is invention).
5. **Conventions:** naming scheme per object type; layering rules.
6. **Evolution:** generations timeline; blessed vs deprecated stated explicitly. The blessed pattern is one you source-read deeply, and it must EXIST — a ticket's proposed design is never the blessed pattern. **Bank the blessed exemplar's FULL source NOW — HARD STOP until banked.** The document run's quick-start copies it verbatim, so an unbanked blessed exemplar forces that run to either fabricate it or ship a [GAP] where the copy-this centerpiece should be. Naming it is not banking it. **Immediately after writing the "blessed pattern" line in §6:**
   1. Identify the exact object name you just wrote.
   2. Check if `research/snippets/` already contains a file with that object in its `" Fetched:` receipt. If yes → continue. If no → fetch the source NOW and write it to `research/snippets/p3-blessed-exemplar-{slug}.abap` with a proper fetch receipt as the first line.
   3. Do NOT proceed to §6.7 (bug register) or the Pattern Gate until the blessed exemplar has a snippet file. The pattern gate will FAIL without it; fixing it later means a resume run.
7. **Bug register:** every bug with severity, verbatim cited lines (banked), and a concrete fix. Severity follows the failure path; credentials in source — commented out included — are always HIGH. **Consolidate before the gate:** every bug found across all read batches (including resumed sessions) is merged into this ONE register with its verbatim line — a register whose total is lower than what the domain files hold is an under-count that hides the team's highest-value findings. Each row carries the offending line or its snippet file. The register's total is the sum across all batches, reconciled here.

**PATTERN GATE (blocks completion).** Full conditions in `references/quality-gates.md` § Pattern Gate Conditions. Summary: every IMPL maps to a pattern or is named stub/dead; the specific object each pattern names as its reference implementation is banked (not a sibling); the blessed pattern is banked without exception; the primary trace is evidence-complete. Report per-pattern snippet counts from LISTING `research/snippets/`.

**Blessed-exemplar verification (sub-check):** see `references/quality-gates.md` § Blessed-Exemplar Verification. The named blessed exemplar must have its own snippet with FULL source. Verify by grepping snippets/ for the exact object name. Bank it NOW if missing before reporting PASS.

### Phase 3b: Technical Debt & Corrections

After the pattern synthesis and before Phase V, write two additional required sections:

**§5b Technical debt inventory** — design issues, inconsistencies, and portability problems that are NOT bugs (they don't produce wrong behavior today but make the solution fragile, inconsistent, or hard to maintain). These are distinct from the bug register: bugs have a broken code path; debt has a design smell. Typical items:
- Hardcoded environment values (client numbers, hostnames, RFC destinations that only work in one landscape)
- Inconsistent conventions across domains (JSON casing, error handling style, naming variants)
- Stub/dead architecture layers (interfaces created but never implemented, services scaffolded then abandoned)
- Cross-domain type coupling (domain A using domain B's types with no abstraction)
- Missing error handling in older generations vs proper handling in newer ones (the gap is the debt)
- Untestable patterns (service instantiated inside the method body, no injection point)
- Missing test coverage (unit test classes that are empty stubs)

Write as a numbered list with object name, the debt, and why it matters. A run that found bugs but no debt was reading at method-level, not architecture-level.

**§10 Corrections log** — a numbered list of claims you made earlier in the run that turned out wrong, with what the correction was and how you caught it. This section proves intellectual honesty and teaches future readers (and future runs) what to mistrust. Typical entries:
- "Initially claimed X objects, SE16 export revealed Y" (scope correction)
- "Initially classified ZCL_FOO as pattern P3, but reading showed it's P6" (pattern correction)
- "Initially said 'no bugs' in ZCL_BAR, deeper read revealed B7" (finding correction)
- "Initially missed domain Z entirely — hierarchy sweep revealed it" (scope expansion)
- "README sample rows were inferred from handler constants — corrected against SE16 export" (evidence upgrade)

The log accumulates through the run. When you correct a claim in notes.md, ALSO append a corrections entry citing what changed and why. A run with zero corrections likely never re-examined its early claims — which is how a partial registry read becomes a confident coverage percentage and propagates to every downstream doc. The corrections count is not a gate, but a self-check reports the count and "0 corrections" triggers a warning: "Verify: no corrections logged — either every early claim was perfect, or the run never revisited its initial assumptions."

**§9 Open questions** — quality criteria: each question names a specific object or config row, states what is unknown, and says why it matters (what downstream doc or decision is blocked by not knowing). Vague questions like "what else is there?" or "are there more objects?" are not open questions — they are unexplored scope. An open question results from a COMPLETED read that raised a specific unanswerable; blocked reads are not questions, they are blocked items (already in the ledger). Aim for 5-15 genuine questions that a follow-up session (or a domain expert) could answer in one sentence each.

### Phase V: Package Validation

**THE SELF-CHECK IS MANDATORY AND COMES FIRST.** Do not write the `Status:` line until `check_run.py` passes. The sequence is: (1) run the script, (2) fix every FAIL it reports, (3) re-run until 0 FAIL, (4) THEN write Status. A run that writes Status before running the script has declared the package valid without checking — every historical resume run traced back to this inversion.

1. Run `python3 ~/.agents/skills/explore-abap-solution/scripts/check_run.py --research-only <output_dir>` and paste its output verbatim into `research/notes.md` §8 (Validation Report). When the script is missing, say so (incomplete skill copy) and reproduce every check by hand in the same per-line format with the directory listings that justify each PASS.
2. Resolve every FAIL by doing the missing work or declaring INCOMPLETE honestly — never by editing a file to green a marker. **See `references/quality-gates.md` § Phase V: Self-Check Fix Guide** for common FAILs and their exact fixes.
3. Write the `Status:` line ONCE, now: COMPLETE (both gates passed, self-check green) or INCOMPLETE (what is missing and why). Anything appended to COMPLETE makes it INCOMPLETE.

**Pre-validation checklist** (full version in `references/quality-gates.md` § Pre-Validation Checklist — run mentally before invoking the script):
- Every ledger row has a final status; the word "pending" appears in ZERO table rows file-wide
- Both gate reports contain a `GATE:` line
- The blessed exemplar has its own snippet file
- Every snippet's first line starts with `" Fetched:`
- No qualifier text follows `GATE: PASS` or `Status: COMPLETE`

## Momentum

Progress is files on disk. Cards, ledger updates, and snippets land continuously during Phase 2 — no long silent stretches, no batching to the end. A passing gate report and the next phase's first action happen in the same turn. The Phase-1 checkpoint is the ONLY permitted pause; never ask "should I continue reading?" or "should I explore the remaining domains?" — the census answer already decided that.

**CONTEXT PRESSURE RULE:** thoroughness IS the product; pressure is never a reason to thin the process. In order: (1) **Batch and resume** — read in groups of 10-15 objects, writing cards/snippets/ledger updates after each group. When context compaction fires or tool calls begin failing, write a `## Resume Point` (last read object, next pending batch, specific next action) and STOP cleanly. The orchestrator re-launches a fresh session. (2) **Keep reading** — if tools still respond, keep going. Announcing "context is getting large" or "given context limits" while tools still work is a confabulated excuse to stop early — the runner does not know its remaining budget and must not guess. (3) **Declare INCOMPLETE** — only when SAP access dies or the session literally cannot continue after resume. Skipping reads, cards, receipts, or gates to "finish faster" is not on this list.

**PREMATURE-STOP SELF-CHECK (run this before EVERY gate attempt and before writing Status):** If ANY of these are true, you are stopping too early — go back and keep reading:
- Tools still respond successfully (no timeout, no auth failure, no context compaction)
- Ledger has rows in `pending` status
- You have not run `check_run.py --research-only` yet (you MUST run it before writing the Status line — this is the #1 cause of resume runs; the script catches format issues invisible to the runner)
- You are about to write "the remaining objects follow the same pattern" or "confirmed uniform" or "mechanical repetitions" as justification for not reading them — THAT IS THE SIGNAL TO KEEP READING, not to stop
- The snippet bank has fewer files than the pattern taxonomy has patterns
- The blessed exemplar named in §6 does not have its own snippet file (check NOW — do not assume it's banked because you read it earlier; reading ≠ banking)

Pattern uniformity is a FINDING to record in §6, never a LICENSE to skip reads. A handler that "follows the same pattern" may still have a copy-paste bug (the #1 real-world handler bug) — and bugs in pattern-siblings are the highest-value discoveries because they prove the pattern has a defect propagation vector. The run that stopped at "pattern confirmed" missed exactly the bugs that matter most.

## Effort & Delegation

Size is read off the `CENSUS:` line, never estimated.

| Size | Signals | Strategy |
|---|---|---|
| Small | < 15 objects | All phases in one pass |
| Medium | 15-40 objects | Batch reads in groups of 10-15; ledger after every batch |
| Large | > 40 objects | Batch reads in groups of 10-15; write Resume Point when context compaction fires; orchestrator re-launches fresh sessions until the ledger is complete |

**Batch discipline (all sizes):** after reading each group of 10-15 objects:
1. Update the ledger rows with final statuses
2. Verify cards are written to `research/{domain}.md`
3. Verify snippets are banked for exemplars and buggy blocks
4. Count: `read N of M total, K remaining`

For Large solutions, the run may span multiple sessions. Each session picks up from the Resume Point, reads the next batch of pending ledger rows, and stops cleanly when context pressure arrives. Relaunch the skill with the same output directory. A Large run that completes in one session is fine, but plan for resume instead of silently dropping unread objects.

Main, after each batch: update the bug register running total. Bugs left only in domain cards do not exist as far as the register and the docs are concerned.

## Multi-Session Resume

Before stopping: write `## Resume Point` in notes.md (last completed phase, done vs pending, specific next action). On "continue"/"resume": read notes.md, find the Resume Point, pick up from the ledger — never re-explore read objects. State lives on disk, not in context.

## Pitfalls

- **Documenting only the kernel is the #1 failure.** Zero IMPL after Phase 1 means you inventoried the scaffolding, not the solution. Go back and SELECT the registry.
- **"Probably a duplicate" / "not relevant" are dangerous.** Similar names hide different techniques; outbound clients, auth utilities, log wrappers are part of the story. The delta tier makes checking cheap.
- **Where-used lies about dynamic dispatch.** Registry-driven solutions instantiate by name; grep for dynamic calls and mine config columns holding object names.
- **Base-class behavior is invisible in implementations.** Defaults, hooks, implicit validations live only in CORE source.
- **Legacy structure hides:** map include hierarchies like class hierarchies; function-group TOP includes are the class, FMs the methods; local classes hide in class-pool Local Types and report includes; customer-exit `ZX*` includes and VOFM pools hide Z-code behind SAP-namespace containers.
- **Domain fixed values encode the enums** — read them.
- **Generated pairs:** read the `_EXT` half deeply, classify the generated half.
- **Tests are usually stubs.** Verify by reading.
- **Multiple paradigms coexist.** Document all families, or exclude a family only as a stated decision with a pointer.
- **A ticket is a requirement, not evidence.** Its proposed names never enter the inventory, taxonomy, conventions, or traces, and can never be the blessed pattern.
- **Naming conventions fabricate objects.** Seeing `_H00` and `_H01` does NOT mean `_H02` through `_H05` exist. Every ledger entry must be validated against the SAP system (search or source fetch). An object inferred from a naming pattern but never confirmed is an invented name — it poisons the census, inflates the count, and every downstream document will present it as fact. The research package includes an Existence Validation section; `check_run.py` verifies it.
- **"Pattern confirmed uniform" is the #1 premature-stop excuse.** The runner has no authority to assess diminishing returns. Every object gets a final status from reading, not from inference. If you catch yourself writing "confirmed uniform", "mechanical repetitions", "remaining objects follow the same template", or "no new patterns expected" as justification for not reading — that IS the signal to keep reading, not to stop. Pattern-siblings are where copy-paste bugs hide (wrong variable from the source handler, swapped parameters, stale constant references). The run that stopped at "pattern confirmed" missed exactly the bugs that matter most. The ONLY valid stop triggers are: (1) context compaction fires, (2) tool calls fail with errors, (3) SAP access dies. "I've read enough to understand the pattern" is never on this list.
- **The word "pending" is a FILE-WIDE trigger.** `check_run.py` uses `^\s*\|.*\bpending\b` which matches ANY markdown table row containing "pending" ANYWHERE in notes.md — not just the §3 ledger. If you write "pending" in the pattern taxonomy, a sweep-log table, or a status summary row, the script will flag it as an unresolved ledger row. Use alternatives: "unread", "not yet applied", "deferred", "14 confirmed" (with count), or just omit the row. Never use the literal word "pending" in any table cell outside the §3 ledger, and the ledger itself must have zero by Phase V.

## Reporting

Fail loud at every gate with numbers, never adjectives. Final report, first line = the Status verdict, then: census numbers, coverage split (deep/delta/classify/blocked, with the blocked list), patterns found, top 3 bugs, snippet count, the self-check output verbatim, open questions — and the handoff line: **"Next: run `document-abap-solution` on `<output_dir>`."**

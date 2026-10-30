# Documentation Blueprints

Read this during Phase 4. It defines each document's skeleton, its binary depth test, and how the same skeleton instantiates across different solution paradigms.

## The level contract

Progressive disclosure is the product. Each level answers more, costs more, and links one level down. Never duplicate content across levels; link instead. The set follows the Diátaxis split: tutorial (quick-start), how-to (cookbook, operations), reference (reference, quick-reference), explanation (architecture).

| File | Level | Reader moment | Budget | Pass test |
|---|---|---|---|---|
| README.md | L0 orient | "I just heard this solution exists" | 5 min read | Reader can say what it does, name its parts, and pick their reading path |
| architecture.md | L1 understand | "I need the mental model" | 30 min read | Reader can trace one end-to-end run on paper, with real object names |
| quick-start.md | L2 first change | "Make me productive today" | 60 min doing | Reader has a working implementation without opening any other doc |
| cookbook.md | L3 pattern work | "I need to build variant X" | per recipe | Any implementation in the inventory can be rebuilt from recipes alone |
| reference.md | L4 lookup | "What exactly does this method take" | seconds per lookup | Any object, method, table field, or message is findable with signature and example |
| quick-reference.md | always open | second monitor / printed | 1 page | Fits one printed page; answers daily questions without scrolling |
| operations.md | conditional | "It broke in QA/PRD and I am on duty" | per incident | The top 3 historical failure modes are resolvable with this doc alone |
| research/ | maintainers | "Audit or resume the exploration" | n/a | Another agent could resume or audit the exploration from these files alone |
| {ticket}-guide.md | optional | "Apply all this to my actual ticket" | per ticket | Reader ships the ticket following it step by step |

## Global style rules

- **Snippet provenance:** every code block is copied from the snippet bank in `research/snippets/` (banked by `explore-abap-solution`). Copied means byte-identical to the banked file apart from added annotation comments — Phase 6 diffs doc blocks against the bank, so paraphrased, reformatted, case-normalized, or "improved" copies will bounce. Cite the source object (and method) directly above the block. Never synthesize ABAP from memory; when the needed block is not banked, write `[GAP: unbanked — <object>]` and report it for the fetch list — this skill has no system access, and paraphrasing around the gap is fabrication. Mark annotations inside code clearly (`" <-- note: ...`) so readers can tell them from real comments.
- **Fixed code is not source.** Never present an edited, "corrected", or simplified version of a real object under that object's name — that is fabrication wearing a real label, and it diverges from what the reader will see in the system. Show the real source with the defect marked (`" <-- BUG: ...`), and put any repair in a separate block labeled "recommended fix — not in the system". Same for structure: a recipe may not rename, drop, or invent methods and signatures the banked source does not have.
- **Real names everywhere.** Placeholders appear only in "what to change" tables, marked as such.
- **Identifier discipline:** every custom identifier (Z*/Y* object, table, view, transaction) in any doc must exist in the ledger. Writers never coin a name that is not in their cards or snippets — under completeness pressure, invented-but-plausible names are the historical #1 corruption. Phase 6 greps for violations. This covers table DATA too: an object name inside a config-table row (a handler_class, uri_class, FM name column) is an identifier, wherever it appears. One carve-out: objects a ticket proposes but that do not yet exist may appear in `{ticket}-guide.md` and quick-start build steps, always marked "to create" — anywhere else (traces, conventions, catalogs, evolution, sample config rows presented as read) an identifier must resolve to the ledger, and Phase 6 treats an unmarked unknown as invention. **Corollary: no asterisks in artifact names.** When the research uses a glob (`ZEXAMPLE_APP_TOOLS_*`) because sub-packages were not individually confirmed, the doc uses the confirmed parent (`ZEXAMPLE_APP_TOOLS`) — never the glob pattern. The check script's regex `Z[A-Z0-9_]{6,}` extracts every Z-prefixed token as an identifier; an asterisk in a package cell creates a false name that fails the identifier-trace check. Same for invented sub-package suffixes appended to known parents — each is an unresolvable identifier.
- **Sample rows are read, not invented.** Config-table sample rows shown in any doc are actual rows read from the system (system + client recorded in the notes). When rows could not be read, the block is explicitly labeled "illustrative — not read from the system" and uses the placeholder convention, never plausible-looking fabricated entries presented neutrally: a fake row under a "Sample rows" heading is fabricated data wearing a factual label.
- **Inferred stays labeled:** content derived from `inferred:` ledger rows carries a visible marker (e.g. "*inferred, not source-verified*") or is omitted; code blocks never come from inferred objects. Flag values, enum meanings, and parameter semantics count: when a parameter's accepted values or a flag's meaning is not visible in banked source (a signature bank without the method body shows types, never semantics), the stated semantic is inferred — label it or leave it out. Two writers guessing the same unbanked flag independently is how docs end up contradicting each other.
- Tables for enumerations, prose for narrative. No wall-of-prose sections.
- **Stable IDs:** patterns are `P1..Pn`, recipes are `R1..Rn`. Use the IDs in headings, cross-links, and the SPA. IDs never change after Phase 3.
- Diagrams: ASCII box diagrams (they render everywhere a developer will look).
- Admonitions as bold inline labels (`**Gotcha:**`, `**Why:**`), not nested blockquotes.
- Plain dashes, short sentences, active voice.

## Per-document blueprints

### README.md (L0)

```
1. What this is             2 sentences: business purpose + technical shape
2. 60-second model          ASCII diagram, real class/table names, one trigger-to-result flow;
                            parallel paradigms get separate diagram sections, never one fake pipe
3. The parts                table: every CORE object | role (one line); config tables with sample rows
4. Reading paths            by persona: "fix a bug today" / "build something this week" / "own this"
5. Reading order            8-10 real objects, simplest first, reading time each
6. Known bugs               severity | object | one line (top of the register; full detail in research/)
7. How to run and observe   trigger (transaction/URL/job/test) + where logs and errors land
8. System info + coverage   system, client, root package, transport layer/target, plus a coverage
                            line computed from the ledger — "documents M objects: c CORE, i IMPL,
                            ..., source-read N%, registry rows read: yes/no" — the run's real
                            scope, visible in its own output; INCOMPLETE runs repeat the
                            partial-coverage banner here
9. Doc map                  table of all files with level + time budget, written LAST from the
                            actual directory listing — never from the plan; a doc map row
                            without a file on disk is a validation failure
```

Depth test: a developer who reads only this can navigate everything else without asking a colleague.

### architecture.md (L1)

```
1. Layers and responsibilities   who may call whom; the dependency rule stated explicitly
2. Lifecycle traces              one numbered end-to-end trace per paradigm found:
                                 step | object.method | what happens | what can fail
                                 (every step cites read source — a ticket's to-be-built
                                 objects never appear as trace steps)
3. Configuration model           each config table: what a row means, delivery class, who reads it
4. Data model                    Z-tables with key relationships; the config vs runtime data split
5. Error, logging, security      exception classes, message classes, app log objects, who commits;
                                 auth objects checked (and surfaces left unchecked), hardcoded
                                 secrets/destinations found
6. Extension contract            what a new implementation must satisfy: interface/base,
                                 registration, naming, transport
7. Conventions and why           naming scheme table per object type, with the reason where known
8. Inferred decisions            decision | evidence in code | confidence (mini-ADRs, reconstructed)
9. Evolution                     generations timeline; the blessed current pattern; deprecated ones
                                 named explicitly ("copy X, not Y, because ...")
10. Hooks into standard SAP      every HOOK with its contract (what standard passes in/expects back)
11. Boundaries and neighbors     EXT systems and consumer solutions, one line each
```

Depth test: the traces alone let a reader predict which object to set a breakpoint in for any symptom.
The lifecycle traces written here become `traces[]` in solution.json. Write them once, precisely.

### quick-start.md (L2)

```
1. Goal            "At the end you have <concrete thing> running in <system>"
2. How the team works   State explicitly that the team builds by copying existing implementations.
                        Name the simplest existing implementation (the one to copy). This framing
                        is not optional — it is how ABAP teams actually work and it prevents the
                        tutorial from feeling alien.
3. Prerequisites   access + developer key, package to use, transport creation, naming to reserve
4. This is what it looks like  Show the COMPLETE source of the simplest real production implementation
                        (from the snippet bank). Not excerpts, not a synthetic hello-world.
                        The reader should see a real, deployed, working unit before they touch anything.
5. Build           copy that real implementation; every layer that needs creating, in order,
                        the full source shown, time estimate per step
6. What to change  table: each part of the copied source | what you replace it with
7. Register        the exact config row / registration step, with real column values and the
                   maintenance route from the sweep (SM30 view name / transaction), derived
                   from the trigger chain — never a guessed table
8. Verify          trigger it (exact transaction/URL/job) + expected response + where the log lands
9. Troubleshoot    table, 8+ rows: symptom | cause | fix (source real dumps and bugs found)
10. Checklist      final tick-through: created, registered, activated, transported, verified
11. What you did   map each step back to the architecture concept it touched
12. What next      table: "need X?" -> cookbook recipe ID (connects the newcomer to deeper material)
```

**HARD RULE: No synthetic examples.** The quick-start code block is the simplest real implementation from the system, copied verbatim from the snippet bank. A "hello world" that was never deployed:
- Misses constructor patterns and service wiring the real code has
- Misses validation idioms and response conventions
- Teaches a workflow (write from scratch) that the team never uses
- Violates snippet provenance

If the simplest real implementation is too complex for a quick-start (>200 lines), still show it in full first ("This is what a real one looks like"), THEN walk through what to change. The complexity IS the lesson — the reader needs to see it to calibrate expectations.

**Copy-source hygiene (hard):** the implementation named as the thing to copy must not appear in the bug register and must be a representative of the dominant pattern — not a stub, not a special-purpose one-off, not merely the shortest file. A buggy or unrepresentative "simplest" handler teaches its defect or its exception to every newcomer. If the shortest unit is dirty, take the next simplest clean one and say why in one line.

**When the snippet bank holds NO real implementation of the unit this quick-start teaches** (an incomplete run that never reached the implementation layer): do not write one from imagination — an invented example teaches idioms the codebase does not use and violates provenance twice. Instead the quick-start opens with a visible INCOMPLETE banner naming the gap, ships only what is real (the extension contract, the registration step from the trigger chain, the verification route), and points to the resume list. A shorter honest quick-start beats a complete-looking fabricated one.

Depth test: run the newcomer test from Phase 6 against this doc.
Paradigm flavor of "the concrete thing": API = endpoint returning fixed data; batch engine = step class that logs its input; BAdI set = filter implementation that writes an app-log line; RAP = validation that rejects one test value; legacy program = operation FORM wired into a copied sub-schema; output = copied form printing a test document; workflow = task logging its container; cockpit = new toolbar action showing a message; proxy = provider returning fixed data.

### quick-reference.md (1 page)

```
0. Trigger anatomy      the full invocation shape as one labeled line (URL segments with
                        meanings / job + variant naming / spot + filter), from the trigger chain
1. Decision tree        "I need to ..." -> recipe ID (mirror of the SPA wizard)
2. Daily API            the 10-20 methods/attributes actually used every day, one line each
3. Templates            minimal compiling skeleton of the commonest unit (from real source),
                        plus the success and error result idioms as copy-paste blocks
4. New-item checklist   objects to create + registration steps, tickable
5. Naming               object type -> convention -> example
6. Config cheat rows    the 2-3 tables you edit weekly, key columns only
7. Glossary             15-25 terms: business terms + solution slang (suffix codes, nicknames)
```

Depth test: print preview fits one page. If it does not, cut, do not shrink the font. Second test: every row's answer is pasteable code or an exact name (object, transaction, view) — advice-shaped rows ("check the config") fail. The template is compilable source distilled from the snippet bank, never pseudocode; a developer pastes it and fills the blanks. Distilled means placeholderized, not improved: the template's error handling, CATCH types, and response idioms are the ones the banked source actually uses. The urge to teach a hardened version (broad TRY/CATCH, extra checks no real unit has) is legitimate — satisfy it in a SECOND block labeled "recommended hardening — not yet in the codebase", never by blending it into the template that claims to describe existing practice.

### operations.md (conditional)

Produce when the solution has a runtime surface: jobs, queues, interfaces, outputs. Reader: the developer on support duty.

```
1. Monitor       where health shows, whichever surfaces exist here: job logs, app log (SLG1),
                 gateway/ICF log, SM58/SMQ2, SM13 (update errors), SP01/NAST (output),
                 SM35 (batch input), SWI1 (work items), SXMB_MONI/SRT_UTIL (proxies),
                 /IWFND/ERROR_LOG (OData), ST22
2. Triage        symptom | where to look | what it means (from real dumps and the bug register)
3. Reprocess     safe rerun rules: job restart, IDoc reprocessing (BD87), queue retry, output
                 repeat (RSNAST00), workflow restart (SWPR), idempotency facts
4. Data checks   quick SELECTs or reports that answer "did it run, did it post"
5. Escalate      what is safe to fix alone vs what waits for the team
```

Depth test: the top 3 historical failure modes (from ST22 and the bug register) are resolvable with this doc alone.

### cookbook.md (L3)

```
1. How to use + index    table: ID | title | use when | difficulty
2. Core patterns         the blessed pattern and its meaningful variations
3. Variations            techniques fewer implementations use (async, inheritance chains,
                         dynamic typing, binary payloads, multi-step routing)
4. Other paradigms       one section per additional paradigm found in the solution
5. Integrations          calling out (RFC/HTTP/IDoc) and being called
6. Anti-patterns         real bugs found, with class names: wrong vs right, side by side
7. Selection matrix      one row per "I need to ..." scenario: Scenario | Recipe | Objects to create
```

Recipe headings carry the ID plus a descriptive name (`## R7: Call a cross-system API`), never a generic "Recipe 7". Multi-object recipes split the code into one sub-section per layer/object instead of one monolithic block.

Recipe coverage comes from Phase 3's two lists: one recipe per pattern, plus one per technique in the dominant pattern's technique inventory (verbs/operations, input styles, output and content types, error styles, composition vs inheritance, async, cross-system). Close the section with a "known bugs in existing code — do not copy these" list naming the buggy objects with the offending lines (from the bug register), so copy-first developers know which sources are traps.

**Audience gate (blocks delivery):** Review the selection matrix. For every common scenario a developer on this team faces ("I need to build a new X", "I need to add a Y"), there must be a recipe. Infrastructure-only recipes (how the dispatcher works, how the token cache works, how the RFC resolver works) are valuable content — but they belong in architecture.md as "How the framework works" sections or in the reference as API documentation. They are NOT cookbook recipes because they do not answer "how do I build a new implementation?" If all recipes describe internals that developers never modify, the cookbook has failed its audience. The minimum recipe set for any framework covers:
- The simplest implementation (what newcomers copy) — the base recipe
- Every distinct technique implementations use (from the technique inventory)
- Common composition patterns (when implementations combine multiple features)
- Integration patterns (calling out, being called)
- Error handling and edge cases the team actually hits

**Complete code, hard rule:** each pattern's base recipe embeds the complete unit from the snippet bank — full class definition AND implementation (or whole FM/FORM), constructor and error paths included. Variant recipes embed the complete method(s) that differ, never code elided mid-body, and never re-paste the unchanged skeleton (complete, not repetitive — the base recipe owns the skeleton). Step lists with 3-line fragments are not recipes; if only fragments exist, the snippet was never banked — go get it, do not ship the fragment. Equally hard: completeness never licenses invention — a recipe may only be as complete as its banked source.

Recipe template (every recipe, no exceptions):

```
## R7: <verb-led title>
Use when: <one line>
Source: <real class(es) this is distilled from>
Prereqs: <recipes or setup assumed>
<complete annotated code: full class/FM definition, constructor, error paths>
Register: <config row / registration step>
Verify: <how to see it work>
Differs from R3 by: <the one key difference>
```

**The Source line is load-bearing.** It names ledger object(s) whose read source the recipe distills, and a recipe that cannot cite one does not ship: the technique becomes a named gap in the selection matrix, or — for ticket-proposed code — lives only in `{ticket}-guide.md` marked "to create", never as a recipe. This binds mechanics recipes hardest: how the framework binds URI placeholders, dispatches verbs, negotiates content types, etc. may only be taught from the mechanism observed in read source (an implementation using it, or the base class implementing it). A recipe hedged with "test which way works" is a guess wearing a recipe heading — the reader will ship the guess.

Depth test: walk the ledger; every IMPL object maps to "follows Rn" or "combines Rn+Rm" or is a documented stub. Recipe count tracks pattern count, never a fixed number.

### reference.md (L4)

```
1. Object catalog        EVERY object: name | type | package | layer | pattern | role
2. Framework API         EVERY public/protected method: full signature + one real usage example
3. Config tables         EVERY field of every table, plus 2-3 real sample rows
4. Messages/exceptions   every exception class and message number, and when it fires
5. Capability matrix     entire framework surface: feature | status used/partial/unused | hint,
                         with the using class named where used; an "unused" verdict is checked
                         against the FULL ledger and technique inventory first — one inventoried
                         object using the feature falsifies it; when the shared base is standard
                         SAP, the surface is the standard base's interfaces (read them) as used
                         by this solution, closing with what the framework CANNOT do plus
                         workarounds, and the top unused capabilities ranked by value (only with
                         no shared base at all: state that, describe de-facto conventions)
6. Testing               one complete test class + how to run it + the solution's test idioms;
                         no real tests in the system? write a recommended one (test doubles for
                         the service layer, injection, request simulation) with real names,
                         labeled as recommended

7. Design standards      what new code must follow (formats, naming, error style)
```

Depth test: pick 3 random ledger objects and 3 random framework methods; all six findable with full detail. "And similar" or "etc." anywhere in this file is a failure.

### research/ (maintainers)

`notes.md`, the master file:

```
0. Status              first body line: `Status: COMPLETE` (nothing appended — any qualifier
                       makes it INCOMPLETE) or `Status: INCOMPLETE — <why + resume pointer>`;
                       plus a `References loaded:` line naming each reference file as read
                       (with phase) or `unavailable: <error>`. Both are checked mechanically
                       by scripts/check_run.py.
1. Access + target     entry point, system/client, tools available, capability degradations,
                       runner (`Runner: <model/client as self-identified>` — attribution for
                       later runs comparing quality across runners)
2. Ledger              flat table: object | domain file | status | pattern | changed-on stamp
3. Sweep log           every hidden-corner check: "checked X: found Y / none"
4. Gate reports        coverage gate + pattern gate outputs, verbatim
5. Bug register        object | bug | severity | impact | concrete fix, in full sentences
6. Debt + stubs        ordered by severity; stubs with registration status and completeness
7. Evolution notes     generations, hotspots, authorship clusters, with code evidence
8. Confidence + gaps   overall confidence (high/medium/low), inferred/blocked lists, follow-ups
9. Open questions      specific and actionable, answerable only by the team
10. Corrections        claims reversed during exploration ("initially assumed X — source showed Y"),
                       kept as a log, never silently overwritten; each entry names what the wrong
                       belief would have cost the docs. This is where the exploration proves it
                       checked itself.
```

`{domain}.md`, one file per domain: the object cards (produced by `explore-abap-solution`; template in its exploration-tactics.md). The split makes research a queryable reference, and enables parallel exploration, domain handoffs, and maintenance without touching the whole corpus.

### {ticket}-guide.md (optional)

The one doc where to-be-built objects may appear (always marked "to create"). Skeleton:

```
1. Summary               ticket ID, one-line goal, the recipe(s) it instantiates and why,
                         effort estimate (marked as estimate)
2. Naming decision       when the ticket's proposed names differ from the solution's observed
                         conventions: a short options table (follow convention vs follow ticket,
                         pro/con each) with a recommendation and who decides. Never silently
                         adopt either side.
3. Objects to create     table: object | type | package (including new packages/transports),
                         following the conventions table from architecture.md
4. Source, per layer     the to-create code, complete per object, built by adapting the chosen
                         recipe's banked exemplar — state per block what was changed vs the exemplar
5. Register + verify     exact registration row/step and the trigger to run, from the trigger
                         chain; expected output shown in the solution's REAL serialization
                         behavior (formats, casing), not the ticket's idealized sample
6. Deltas from spec      table: ticket says | implementation does | why — casing, formats,
                         layers skipped; each delta is a flagged decision, not a silent drift
7. Verification list     tickable, including the negative cases (missing input, not-found)
8. Related existing units the closest existing implementations, and whether to extend or
                         stay separate (say why)
```

Rules: to-create code prefers the solution's own idioms and released/standard APIs over hand-rolled reads of standard tables — a synthesized JOIN over standard tables encodes guesses about their semantics that are easy to get wrong. Every standard table, FM, or BAPI the guide's code touches gets a one-line provenance: read in this system / used by an inventoried object / SAP-documented / inferred — verify before build.

## Paradigm instantiation table

The same skeletons instantiated across the running-example solutions, in two tables. Use them to stay generic: whenever an instruction feels REST-shaped, check what it means in the other columns.

| Aspect | API framework | Batch/interface engine | BAdI/enhancement set | RAP stack | Legacy payroll program |
|---|---|---|---|---|---|
| Registry truth | endpoint table: path+verb -> handler class | step table: order -> step class | SE19 implementations + filters | behavior definition + service binding | schema/PCR customizing + conditional includes |
| Lifecycle trace | request in ICF -> auth -> route -> handler -> serialize -> response | job start -> variant -> select -> per-item step chain -> post -> app log | standard txn -> spot call -> filter match -> impl -> return to standard | OData call -> CDS read -> behavior handler -> validation -> save sequence | driver start -> schema interpret -> operation FORMs -> cluster write |
| Quick-start build | endpoint returning fixed data | step class that logs input | filter impl writing app log | validation rejecting a test value | custom operation wired into a copied sub-schema |
| Sample recipes | paginated list; create with body validation; binary download | new step; restart/skip logic; parallel chunking | new filter value; impl calling RFC; deactivating an impl | new action; determination; authorization check | new operation; country include variant; reading cluster results |
| Capability areas | auth modes, serializers, error envelope | restartability, locking, parallelism | filter types, fallback impl, sorting | draft, side effects, feature control | unused operations, switches, sub-schema hooks |
| Typical gotcha | wrong Content-Type handling | job runs in wrong client/variant | impl inactive in this client | unmanaged save not implemented | include active only for one country/molga |
| Ops focus | gateway error log + ICF trace | job restart + app log | usually none (runs inside standard txn) | gateway log + draft cleanup | payroll log + cluster display |

Four more shapes, same aspects:

| Aspect | Dialog/ALV cockpit | Output/forms (NAST) | Workflow | Proxy/interface (SOAP/PI) |
|---|---|---|---|---|
| Registry truth | GUI statuses, selection variants, TVARVC switches | condition records + TNAPR: output type -> print FM + form | SWE2 event linkage + task/agent customizing | SPROXY objects + logical ports (SOAMANAGER) |
| Lifecycle trace | tcode -> selection screen -> data build -> ALV event loop (PBO/PAI) -> user command -> refresh | document posts -> NAST record -> dispatcher/RSNAST00 -> print FM -> form -> spool/email | business event -> linkage match -> container fill -> task -> agent inbox -> method -> outcome | payload in -> proxy framework -> generated class -> Z implementation -> response or fault |
| Quick-start build | new toolbar action acting on the selected row | copied form + print FM printing a test document | task calling a method that logs its container | provider returning fixed data (or consumer call to a test port) |
| Sample recipes | new filter field; row action; background run via SUBMIT | new form field; extra language; email instead of print | new step; agent rule; deadline branch | new operation; fault handling; retry/monitoring hook |
| Capability areas | ALV events, layout variants, edit mode | channels (print/email/PDF), languages, repeat output | deadlines, containers, rule resolution | sync vs async, port config, payload logging |
| Typical gotcha | state in function-group globals leaks across screens | condition record found but form change not transported, or language missing | linkage inactive, or agent rule resolves to nobody | logical port exists only in DEV; payload trace off by default |
| Ops focus | usually dialog-only; batch variant of the report | SP01 spool, NAST status, RSNAST00 reprocess | SWI1/SWIA work items, SWPR restart | SXMB_MONI / SRT_UTIL payload trace |

## Sizing

No fixed page counts. Size tracks the inventory: reference rows equal ledger rows; recipe count equals pattern count; troubleshooting rows come from real dumps and bugs. When a doc grows past comfortable, split by paradigm section. Never trade depth for length.

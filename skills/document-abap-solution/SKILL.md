---
name: document-abap-solution
description: Use when generating a developer onboarding package (progressive docs + interactive explorer SPA) from a validated research/ directory produced by explore-abap-solution. Triggers on "document abap solution", "generate abap docs", "onboarding package".
compatibility: "Portable; needs Python 3.12+ and Node + npm (or the no-build vanilla path), and the validated research/ package from explore-abap-solution. Needs no SAP access."
---

# Document ABAP Solution

Turn a **validated research package** (produced by `explore-abap-solution`) into the complete developer onboarding package: progressive-disclosure documentation plus an interactive single-file explorer SPA.

**THE BOUNDARY (the reason this skill exists):** every fact, identifier, count, and code block in the output comes from the `research/` directory — the ledger, the cards, the snippet bank, the synthesis in notes.md. This skill needs NO SAP access and must not use any: no fetches, no conversation memory of the system, no prior documentation found elsewhere on disk. When something the docs need is not in `research/`, the doc carries `[GAP: unbanked — <object>]` and the final report lists it in a **fetch list** for the next `explore-abap-solution` refresh run. An identifier absent from the ledger may not appear in the docs at all. Check that boundary against the evidence; a written rule alone does not prove compliance.

## Dependencies

- **Input: a validated research package from `explore-abap-solution`** (hard prerequisite). The directory must contain `research/` with: `notes.md` (Status line, CENSUS line, ledger table, synthesis §6, bug register), one or more `{domain}.md` card files, and `snippets/` with fetch-receipted source files. These artifacts are produced exclusively by `explore-abap-solution`; hand-authored or partial directories will fail the entry gate. If the directory is missing, malformed, or was never produced by a completed explore run, this skill refuses to start — run `explore-abap-solution` first. If the user did not name a directory, ask which one holds the research package (one question).
- **Python 3.12+** for `scripts/check_run.py` (entry gate with `--research-only`, final check without it). When it cannot run, report why and leave the gate unverified; a manual check is not an automated pass.
- **Node + npm** for the default Svelte SPA build. Install compatible Svelte 5, Vite, `@sveltejs/vite-plugin-svelte`, `vite-plugin-singlefile`, and Shiki in the generated explorer project. Choose supported versions together. When Node is absent, use the no-build vanilla path in `references/spa-blueprint.md`.
- **This skill's references**, read when their phase starts: `references/doc-blueprints.md` (Phase 4 — per-document skeletons, depth tests, style rules; Phase 4 CANNOT produce correct output without it), `references/spa-blueprint.md` (Phase 5). They live in `references/` next to this SKILL.md (glob `**/document-abap-solution/references/*.md` if unclear). Log each in the run log as loaded or `unavailable: <error>`; if a blueprint cannot be read, tell the user and stop — its phase's output improvised without it fails the self-check.

## Target Audience

ABAP developers who know SAP (workbench, transports, debugging, syntax) but have never seen this solution. They need: the big picture, the "how do I add to it" path, the patterns in use, and the gotchas. Not ABAP tutorials or Basis fundamentals.

## Pedagogical Arc

```
What does it DO?          README, SPA map
How does it WORK?         architecture.md, SPA trace player
How do I BUILD with it?   quick-start.md, SPA wizard
What are the PATTERNS?    cookbook.md, SPA recipes
WHERE is everything?      reference.md, SPA registry
What must I AVOID?        anti-patterns + gotchas
What ELSE could it do?    capability matrix
```

## Deliverables

Written into the same directory that holds `research/`:

```
README.md               L0  orient (5 min): what it is, 60-second model, reading order, known bugs
architecture.md         L1  understand (30 min): layers, lifecycle traces, conventions, evolution
quick-start.md          L2  first change (60 min doing): real source, transport to working result
cookbook.md             L3  recipes: one per pattern, selection matrix, anti-patterns from real bugs
reference.md            L4  exhaustive lookup: every ledgered object, method, field, message
quick-reference.md      1 printable page: decision tree, daily API, templates, naming, glossary
operations.md           conditional: monitor, triage, reprocess (when jobs/queues/interfaces exist)
{ticket}-guide.md       optional worked example for a concrete ticket (its objects marked "to create")
explorer/dist/explorer.html   single-file interactive explorer (file://, offline, data INLINED)
```

Levels are the anti-overwhelm mechanism: each level answers more and links one level down. Exhaustive lives at L4 and the SPA registry; L0-L2 stay lean.

## Process

### Phase 0: Entry Gate (hard)

1. Run `python3 ~/.agents/skills/document-abap-solution/scripts/check_run.py --research-only <input_dir>` and paste the output verbatim.
2. **Any FAIL → STOP.** Report the failing lines and hand back: "the research package is not ready — re-run `explore-abap-solution` (or its resume) to fix these, then relaunch me." Writing docs over an invalid package launders its gaps into confident prose; refusing is the job.
3. Read `research/notes.md` fully: Status, scope decision, census, ledger, synthesis, bug register, open questions. Read every `research/{domain}.md` card file and LIST the snippet bank. **Verify by hand that an Existence Validation section is present under §2** (`check_run.py` does not check it) — this section documents that every ledger object was confirmed to exist in the SAP system. Its absence means the exploration run predates this requirement; warn the user and note the gap in the run log.
4. **Carry the run status forward.** Research `Status: INCOMPLETE` → banner mode: every doc and the SPA render a visible "partial coverage — N of M objects read" banner naming the unread domains; recipes and the blessed pattern come only from source-read objects; the coverage number appears in `meta.coverage_pct` and the SPA footer. A single doc without the banner reads as complete to whoever opens only it.
5. Start the run log (appended to `research/notes.md`): `Docs run: <timestamp>, Runner: <model/client>, References loaded: ...` — the self-check reads it.

### Phase 4: Documentation

Read `references/doc-blueprints.md`; follow the per-document skeletons and style rules.

Write architecture.md yourself first (it is the spine, distilled from the traces in notes.md §6). Then fan out parallel writer agents, one brief each: A) README + quick-start, B) cookbook, C) reference, D) quick-reference, E) operations.md when the solution has a runtime surface. Each brief carries the relevant blueprint section, the synthesis artifacts, and the cards and snippet files it needs. **Writer agents receive research/ content and the blueprint — nothing else — and never re-explore.**

Review every returned doc yourself before accepting:
- IDs and counts consistent with the ledger; **no identifier that is absent from the ledger** — writers under pressure invent plausible names; a returned doc citing unknown objects goes back with the real cards attached.
- **No wildcards in artifact names.** Package names, object names, and table names in catalog rows, traces, and inventory tables must be exact strings that appear verbatim in `research/` — never glob patterns with `*`. When the research uses a glob (`ZEXAMPLE_APP_TOOLS_*`) because specific sub-packages were not confirmed, the doc uses the confirmed parent (`ZEXAMPLE_APP_TOOLS`) or omits the package column. An asterisk in a name cell reads as a real artifact name to `check_run.py`'s identifier extractor and will FAIL the doc-identifiers-trace-to-research check.
- Every code block that names a real object matches its banked snippet **byte-for-byte** apart from added annotation comments — writers "tidy" real source (case-normalize, reflow, simplify a branch, swap a CATCH); each of those is fabrication under a real label. The fix is re-pasting from the snippet file.
- Every recipe complete per the blueprint rule — thin docs go back with the missing snippets named.
- A needed-but-unbanked block becomes `[GAP: unbanked — <object>]` plus a fetch-list entry — never a paraphrase.

**Cookbook brief MUST include** the full pattern taxonomy with counts, the technique inventory, and the snippet bank, plus: "produce one recipe per pattern AND one per technique in the dominant pattern, each embedding the complete banked unit." The selection matrix maps every "I want to..." to a recipe. **Cookbook audience test:** the primary reader BUILDS implementations — dispatcher/infrastructure internals belong in architecture.md, not recipes. Minimum: the simplest implementation newcomers copy, the most complex common case, and every distinct technique.

Depth tests, each binary:
- Cookbook: any inventory implementation can be rebuilt from recipes alone; base recipes embed the complete unit — never code elided mid-body.
- Reference: any ledgered object, method, or field findable with signature and example. "And similar" is failure.
- Quick-start: a newcomer reaches a working result without opening other docs; the copied source is a real production implementation **from the snippet bank**, never synthetic, never from an object in the bug register (pick the simplest CLEAN representative and say why).
- Quick-reference: one printed page; every row pasteable; the skeleton compiles.

The one sanctioned synthetic block: reference.md's testing section may show a recommended test class using the solution's real names when the system has none, labeled as recommended. A ticket guide's to-create objects are always explicitly marked "to create" and never leak into inventory tables, conventions, or the SPA registry.

### Phase 5: Explorer SPA

Read `references/spa-blueprint.md` and follow it exactly: emit the solution data from the notes.md synthesis (same stable IDs as the docs), **inline it directly into the HTML** as `<script type="application/json" id="solution-data">{...compact JSON...}</script>`, build the single-file app (Svelte 5 or the vanilla fallback), pass the anti-slop gate, verify from `file://`. Embed `assets/explorer.css` verbatim as the canonical stylesheet — never restyle. Code renders in `<pre>` with the regex ABAP tokenizer (`.tok-*` classes); plain monochrome text is a delivery failure. Phase 5 is not done until the validator's numbers report is green and echoed.

**INLINE DATA IS NON-NEGOTIABLE.** The explorer must work from `file://` double-click with zero network requests. A separate `solution.json` loaded via fetch/XHR FAILS from `file://` protocol in every modern browser (CORS blocks it, or the path doesn't resolve). The solution data lives INSIDE the HTML as a `<script type="application/json" id="solution-data">` block — never as a placeholder that references an external file. The JS boot function parses the inline `<script>` element's textContent on load — no fetch, no XHR, no path resolution. There is no separate `solution.json` file; `check_run.py` validates the data by extracting it from the HTML directly.

**SPA Brief (self-contained):**
```
Build a single-file HTML explorer for the ABAP solution.
Read {dir}/research/notes.md (patterns, bugs, domains, traces), {dir}/architecture.md, {dir}/cookbook.md.
Write to {dir}/explorer/dist/explorer.html. Follow ~/.agents/skills/document-abap-solution/references/spa-blueprint.md.
The solution data is INLINED into the HTML as <script type="application/json" id="solution-data">.
No external solution.json file. No fetch/XHR. Must work from file:// with zero network.
(Fallback if unreadable: vanilla HTML tabs — architecture, recipes, capabilities, decision tree;
embed ~/.agents/skills/document-abap-solution/assets/explorer.css verbatim first; copy buttons; ABAP tokenizer; showModal() dialogs.
All content from the files above — nothing from memory.)
```

### Phase 6: Validation

1. **Manifest:** list the output directory against Deliverables; every file exists or the final report names it as skipped with the reason. Regenerate README's doc map from the listing. INCOMPLETE runs: grep every doc and the SPA for the banner.
2. **Existence, mechanically:** extract every custom identifier (Z-prefixed, Y-prefixed, or `/NAMESPACE/NAME`) from every doc and the inlined solution data (grep), resolve each against the ledger. An unknown name is writer invention — replace it; both variants of a mutated name are wrong until the ledger settles it.
3. **Provenance, mechanically:** diff every code block citing a real object against its banked snippet; any difference beyond added annotation comments is a doc bug — re-paste. A cited block with no banked snippet becomes a [GAP] + fetch-list entry.
4. **Completeness mapping:** every IMPL → recipe(s) or a documented stub.
5. **Consistency, by numbers:** diff counts (objects, patterns, recipes, bugs by severity), the naming table, the copy-this exemplar, and the trigger anatomy (URL/transaction/job shape) across README, architecture, quick-reference, notes.md, solution.json, SPA footer. Any mismatch is a bug to fix, not explain. Unverified trigger paths carry "*inferred — not verified*" everywhere, consistently.
6. **Links:** every cross-reference resolves.
7. **Newcomer test, blind:** a fresh agent with ONLY the generated docs answers: what does this do; what do I copy for task X; which package and transport; how do I verify; where do I look when it fails. Wrong or unanswerable items are doc bugs — fix and re-run.
8. **SPA checklist** from the blueprint, on the built file, offline.
9. **Validation Report:** append `## Validation Report (docs run)` to `research/notes.md` with each check's numbers, the fetch list, and the newcomer-test outcome.
10. **Self-check:** run `python3 ~/.agents/skills/document-abap-solution/scripts/check_run.py <dir>` (full mode). Paste verbatim into the Validation Report AND the final report. Resolve FAILs by doing the work or declaring INCOMPLETE — never by editing files to green a marker.

## Momentum

Docs land as writer agents finish — generation fans out, never six documents sequentially in main context. No pauses: this skill has NO user checkpoint; the scope was decided in the research run. If the entry gate passes, everything through the final report runs without a single question. The test for any message you are about to send: if replacing it with the tool call that produces the next artifact would have been correct, it was a pause that costs a corrective prompt.

**CONTEXT PRESSURE RULE:** delegate (writer fan-out is the default), or pause cleanly after a finished doc and resume — never thin a doc, skip the SPA, or drop validation to finish faster. The Phase-4 doc list is a triage order for emergencies, not a smaller contract: a run that stops short of the full Deliverables list is INCOMPLETE and says so, with every undelivered file named. The SPA is the usual first casualty — a dropped deliverable that is not named in the report will quietly stop existing.

## Pitfalls

- **Completeness pressure breeds invention.** The two failure modes are duals: fabricate-to-look-complete (idealized classes, invented families, plausible-name inventory rows) and fragment-to-stay-honest (recipes of prose and `...`). The snippet bank is the only exit that is both complete and real; when it lacks something, the answer is a [GAP] + fetch list — never pattern memory.
- **Real source, never templates.** Developers trust code they can open in the system.
- **Never diagram a guess.** Diagrams are read as verified fact; reconstructed structure stays a flat list labeled partial.
- **Capability claims need read-source evidence in both directions** — "the framework cannot X" from absence is as wrong as documenting a method nobody read.
- **Analysis and prescription stay separate.** Cookbook says "do this"; research/ says "here is what is inconsistent".
- **Inferred stays labeled.** Sections built from `inferred:` ledger rows carry the marker; code blocks never come from inferred objects at all.
- **Close the loop.** Quick-start ends with the developer seeing their thing run. Transports and packages are day-1 blockers — cover their creation. Spell out naming schemes with examples.
- **No asterisks in real artifact names.** When research uses a glob pattern for a package family (`ZEXAMPLE_*_TOOLS_*`), the doc uses the confirmed parent package name — never the glob. `check_run.py` extracts custom identifiers (`Z…`, `Y…_…`, `/NAMESPACE/NAME`) from the docs; a `*` inside creates a false name that fails the trace-to-research check. Writers under context pressure invent sub-package names by appending plausible domain suffixes to known parents — each is an identifier the script will flag.
- **Every object name must have been verified against the SAP system.** The research package's Existence Validation section (§2) documents this. If a doc writer needs a name that is not in the ledger (and is not a to-create ticket object), it does not exist in the docs — period. The exploration run is responsible for verifying existence; this skill is responsible for not adding anything the exploration didn't verify.

## Reporting

Final report, first line = COMPLETE or INCOMPLETE (binary — any qualifier means INCOMPLETE plus a resume list). Then: deliverables with sizes, coverage statement carried from the research package, identifiers extracted vs resolved, consistency diffs found+fixed, newcomer-test outcome, SPA size and how to open it, the fetch list for the next explore run, and the full-mode `check_run.py` output verbatim. A report that cannot quote those numbers is the signature of a skipped Phase 6 — precisely the run whose docs carry invented identifiers undetected.

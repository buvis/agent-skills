# Exploration Tactics

Read this during Phases 0-2. It holds the entry-point recipes, the boundary algorithm, the depth tiers, the finding schema, the hidden-corner sweep, and the batch-and-resume protocol.

## Access layer (Phase 0)

Solutions are explored through whatever SAP access this session has. Detect tools first, then map them to capabilities. Record the mapping and any degradation in `research/notes.md`.

Reader names in this reference are abstract capabilities, not executable tool
identifiers. Confirm availability, traversal depth, arguments, and pagination
against the provider's actual schema. A hierarchy reader is not guaranteed to
exist merely because an MCP connection is available.

| Capability | Needed for | Typical providers | Fallback |
|---|---|---|---|
| Read object source | everything (mandatory) | ADT/RFC MCP tools, abapGit export on disk | Ask the user for a source export; work on the dump |
| List package contents | inventory | ADT repository tree, TADIR reads | Reconstruct from source references as a FLAT list of confirmed objects, flagged partial — never draw a package hierarchy that was not listed; readers treat trees as fact |
| Read table rows | config truth | RFC table read, ADT data preview | Ask the user for an SE16 export of named tables |
| Where-used / cross-ref | edges, callers | ADT usage references | Grep the corpus for the object name |
| Class hierarchy | subclass trees, superclass chains | `read_type_hierarchy` tool (direction="subTypes" for subclasses — default; direction="superTypes" for superclasses/parents), ADT type hierarchy endpoint | Grep for `INHERITING FROM` and `INTERFACES`; use naming-convention search (see discovery techniques section) |
| Runtime evidence | gotchas | ST22 dumps, SLG1 logs, SM37 jobs via user | Ask the user to check and paste results |

Rules:
- Never present unread source as read. If an object cannot be fetched, mark its ledger row `blocked: <reason>` and move on. "Read" always means fetched through a tool in THIS run — remembered content from earlier sessions or prior docs is not a fetch.
- Phase 0 ends with the access probe (SKILL Phase 0 step 1): one seed object actually fetched, first lines recorded in notes.md as the receipt. Every capability claimed ✅ in the access map should have been exercised at least once by the time the coverage gate runs.
- **Table ROWS and DDIC DEFINITIONS are separate capabilities — never conflate them.** Failing to fetch a table's source/definition (TABL, DOMA, VIEW via a source API) says nothing about reading its DATA. Before recording "cannot read table rows", attempt every row path the session offers — ADT data preview, RFC table-read (RFC_READ_TABLE-style), SQL console, freestyle query tool — and record which were tried and how each failed. Registry rows are the scope boundary (Phase 1); writing off row access on a definitions error silently amputates the solution's implementations.
- Auth expiry mid-run: keep going. Record each affected object as `blocked`, infer its likely pattern from same-suffix siblings as `inferred: <basis>` at LOW confidence, and ask the user to re-authenticate. Never drop a whole domain because access flickered.
- Source dumps (abapGit style) are a first-class target: the whole skill works on a directory of `.abap` files, with table-row capabilities degraded.

## Entry points: from any endpoint to a solution

Resolve whatever the user gives into a seed set of objects, then run the boundary closure below.

| Entry point | First move | Expansion move | Example |
|---|---|---|---|
| Package | List package tree (TDEVC parents) and all objects per package (TADIR) | Sibling packages under same parent often hold the infra | payroll framework, integration layer |
| Config/registry table | SELECT all rows; columns holding object names are the implementation list | Where-used of the table finds the engine that reads it | API routing table, step registry |
| Base class | Build the full subclass tree via `read_type_hierarchy` (direction="subTypes"); filter results to the solution's namespace. Also call with direction="superTypes" to discover the inheritance chain above (reveals shared SAP bases, intermediate abstractions) | The base's own package pulls in the kernel | handler base, abstract step class |
| Central interface | List all implementing classes (use `read_type_hierarchy` on the interface with direction="subTypes", or `read_cross_references` to find implementers) | Factories that instantiate via the interface reveal dispatch | plugin contract, strategy interface |
| Transaction code | TSTC/TSTCP to the program or class behind it | Program's package, includes, SUBMIT targets | custom cockpit, parameter transaction |
| Program / job | Include tree, then package | Job steps (TBTCP) reveal variants and companion programs | payroll driver + country includes |
| ICF path | SICF node handler class list | Sibling nodes under the same subtree | REST API root node |
| OData / RAP service | Service binding, then service definition, CDS entities, behavior implementation classes | For classic SEGW: the `*_DPC_EXT`/`*_MPC_EXT` pair and its model provider | Fiori app backend |
| Enhancement spot / BAdI | Definition, then every implementation with filters | The standard code calling the spot is the HOOK to document | pricing spot, customer exits |
| User exit / VOFM / BTE | CMOD project -> `EXIT_*` FM -> `ZX*` include; VOFM routine number -> TFRM -> generated include; BTE event -> FIBF (TBE01/TBE34) -> FM | The standard transaction calling the exit is the HOOK; sibling exits in the same project/group are usually in scope | pricing formula 901, MV45AFZZ logic |
| Workflow template / task | PFTC/SWDD: template -> step tasks -> class method (IF_WORKFLOW) or BOR object (SWO1) | Start events (SWE2/SWETYPV), agent rules (PFAC), deadline branches | approval workflow WS9xxxxxxx |
| ABAP proxy / SOAP service | SPROXY: service interface -> generated proxy class -> Z provider implementation (inbound) or consumer callers (outbound) | Logical ports / SOAMANAGER config; the PI/PO middleware route is EXT | inbound orders SOAP interface |
| Fiori app / tile | Tile -> target mapping (semantic object/action) -> OData service (/IWFND/MAINT_SERVICE) or RAP service binding | Continue with the OData/RAP row | "the Manage X app fails" |
| Runtime Z-table | Where-used plus grep for writers and readers; CDS views over it | Writers' packages seed the solution; find the maintenance route | "who fills ZEXAMPLE_LOG" |
| Runtime artifact | Resolve to its object first: ST22 dump -> program/class; IDoc number (WE02) -> message type + process code; spool/output (SP01, NAST) -> output type -> FM; work item (SWI1) -> task; SLG1 entry -> log object -> writers | Then continue with the matching row above | "explain whatever produced this dump" |
| IDoc message type | Partner profile process code (WE41/42) to the handler FM | Mapping classes the FM delegates to | inbound orders interface |
| Function group | All FMs plus their callers | The group's TOP include hides shared state and local classes | legacy calculation API |
| Ticket / free text | Extract object names from the text; each EXISTING object is a seed | Ask for one confirmed object if nothing extractable | "PROJ-123 touches ZCL_X" |
| Bare naming prefix | Search all object types by prefix | Rank hits by package clustering; confirm scope with the user | "everything starting ZEXAMPLE_" |

**Ticket entry points name two kinds of objects.** Existing objects are seeds; objects the ticket proposes to CREATE are the target design of unbuilt work, not inventory. Record proposed names in `research/notes.md` as "ticket-proposed, to create" — they resurface only in `{ticket}-guide.md` and quick-start build steps, never in the worklist, the pattern taxonomy, the conventions, or a lifecycle trace. Then run the full boundary closure from the existing seeds: the ticket scopes the GUIDE, never the exploration — the solution the ticket touches still gets explored whole (registry rows, subclass sweep, naming search), because the guide's "copy this, register here" answers come from the real implementations, not from the ticket's sketch.

## Trigger chain (Phase 1, mandatory)

For every way the solution is invoked, walk the chain in source until implementation code, recording each link with evidence:

```
trigger (ICF node / job / transaction / spot or exit / event or workflow linkage / output type / RFC)
  -> entry object registered at the trigger
  -> dispatch mechanism (router build, CASE, factory, dynamic CREATE)
  -> config rows consumed by that dispatch
  -> implementation set reached
```

Rules:
- The entry object registered at the trigger is CORE; read it deeply and first. It is usually where config becomes dispatch, and it decides which table is the real inbound registry.
- A config table's role is what its readers do with it. Before describing any table, find the code that SELECTs it (where-used or grep) and name the consumer. Class-name columns appear in inbound routing tables, outbound lookup tables, and dead catalogs alike; only the reading code tells them apart. A table with no reader is a catalog, and saying so is a finding.
- The registration instruction in the docs ("to add an implementation, insert a row in X / create node Y") must be derived from this chain, never from table names or plausibility. If the chain was not walked, the how-to story is a guess.
- The invocation URL / trigger anatomy shown anywhere in the docs (README "how to run", quick-reference trigger line, quick-start verify step) comes from this chain too: the actual ICF node read from SICF, the actual job or transaction — never from a ticket's example URLs or a plausible-sounding path. When the trigger could not be walked, the shown invocation is marked "*inferred — not verified*" or omitted.
- The primary lifecycle trace reproduces this chain step by step from read source. Any inferred link is marked in the trace and resolved before the pattern gate.

## Legacy procedural solutions

Many solutions are not object-oriented: one large program with 20+ includes (payroll drivers and their country variants), a function group with 50 FMs sharing global data, program chains wired by SUBMIT / CALL TRANSACTION, or schemas/PCRs with custom operations. Same methodology, mapped units:

| OO concept | Procedural equivalent |
|---|---|
| Class definition | TOP include (global DATA is the attribute list) |
| Methods | FORM routines and function modules |
| Class hierarchy | include hierarchy (map it with the same rigor) |
| Interface | FM signatures plus global data acting as implicit contract |
| Dispatcher | main program flow (READ/CASE/PERFORM chains) |
| Plugin registration | conditional INCLUDEs (`INCLUDE znnn IF FOUND`), schema/PCR customizing, VOFM registration (TFRM) |

Inventory every include (TOP, Fxx, Ixx, Oxx) with sizes; split skeleton includes (control flow) from meat includes (business logic). Read the TOP include and main flow first (that is the CORE), then every FORM and FM, mapping PERFORM/CALL chains.

Procedural pattern vocabulary to watch for:
- Conditional INCLUDEs: the plugin mechanism.
- `PERFORM ... ON COMMIT` and `CALL FUNCTION ... IN UPDATE TASK`: deferred and async execution.
- FIELD-SYMBOLS with dynamic `ASSIGN`: runtime polymorphism without classes.
- Generated subroutine pools: code generation.
- Schemas/PCRs: the registry truth lives in customizing tables, not code. SELECT it like any registry.

HR flavor: logical databases (PNP/PNPCE) drive selection, infotypes carry the data (custom infotypes bring their own module pools), features (PE03) return config decisions, clusters (PCL1/PCL2) store results. Treat features, schemas, and PCRs all as registry truth.

SD flavor: VOFM routines (requirements/formulas, TFRM-registered generated includes), copy-control routines, condition technique for pricing and output (NAST). FI flavor: validations/substitutions (GGB0/GGB1/OB28), BTEs (FIBF), FQEVENTS in FI-CA. Conversion flavor: BDC/batch-input programs (`CALL TRANSACTION ... USING`, SM35 sessions) and LSMW objects. In all of these the registry truth is customizing, not code.

## Boundary closure (Phase 1)

Worklist algorithm. Seed with the entry-point objects, then repeat until no new objects appear:

1. Pop an object; classify it (see below); add a ledger row.
2. Expand edges: superclass and subclasses; implemented interfaces and implementers; composed/instantiated classes; called FMs; read/written tables; config tables selected; registry rows pointing at it; whatever triggers it (job, ICF, spot, exit, event linkage, output type, workflow task).
3. Push newly seen objects.

**MANDATORY EARLY STEP (before looping to fixpoint):** As soon as you identify any config/registry/dispatch table (a table whose columns hold class names, program names, FM names, or any object identifier), SELECT its rows immediately. Do not wait until Phase 2. These rows define the boundary — they are where the IMPL objects are listed. If you discover that `ZREG_STEPS` holds 25 step class names in its `handler_class` column, all 25 classes are now in the worklist regardless of which package they sit in. This step is what prevents the "documented the dispatcher but missed all implementations" failure mode.

Concretely:
- For every table found in a CORE object's SELECT statement, determine if any column holds object names (class, interface, program, FM, form). Common signals: column names containing `class`, `handler`, `program`, `fm_name`, `form`, `routine`, `impl`; domain referencing SEOCLSNAME/SEOCPDNAME/PROGNAME; or values observed to follow Z-naming.
- SELECT DISTINCT the object-name column(s). Each value is a new worklist entry classified as IMPL.
- Record "registered-but-missing" entries (class names that don't exist as active objects) as findings, not as inventory to explore.
- Record "existing-but-unregistered" entries (implementations found via inheritance that have no config row) as dead code findings.

**When SELECT is unavailable:** ask the user for an SE16 export of the specific registry table. Name the table and the column you need. This is a single targeted question, not a vague "I need more info."

## Additional discovery techniques (always apply for maximum coverage)

These techniques are NOT fallbacks for degraded access — they are independent discovery methods that complement config-table reads and should ALWAYS be applied during boundary closure to ensure maximum coverage. Even when you successfully SELECT a registry table, these may reveal implementations that are unregistered (WIP, dead code, alternate registration paths, or objects registered in a different table).

Apply both during the boundary closure loop, after expanding the seed set:

1. **Subclass/hierarchy discovery (primary technique when supported):** The dispatcher code reveals which superclass or interface implementations must satisfy (e.g., `CREATE OBJECT ... TYPE (handler_class)` where the variable is typed to `CL_REST_RESOURCE`, or a factory returning `ZIF_STEP`). Map the `read_type_hierarchy` capability to the available provider and explore in both directions:

   **Downward (direction="subTypes", the default):** Retrieves all subclasses of a superclass — the full hierarchy (direct and indirect subclasses at all depths, including local test classes). Process the results:
   - **Direct subclasses of the framework base** are your IMPL candidates (whatever that base is — a standard SAP class like `CL_REST_RESOURCE`, a BAdI/exit base, or a custom `ZCL_STEP_BASE`; its direct Z-subclasses are the implementations).
   - **Indirect subclasses** (subclass of a subclass) indicate inheritance layers — an intermediate abstract class that itself has implementations. Recognize these as CORE or INFRA (they add shared behavior on top of the base).
   - **Local classes** (names like `LCL_*`, `LTCL_*` with a parent class in parentheses) are test doubles or internal helpers — classify, don't deep-read.
   - **SAP-standard subclasses** (no Z/Y prefix, no custom namespace) — stop at the boundary; name as OUT unless they are a HOOK the solution extends.
   - **Filter by your solution's namespace/naming** to separate your implementations from unrelated subclasses of the same SAP base class. A standard base (e.g. `CL_REST_RESOURCE`, a workflow task base, an output-program base) may have hundreds of subclasses system-wide; only those matching the solution's naming pattern or registered in its config tables are in scope. A large result set is FILTERED, never a reason to skip the query — "too broad" is not a valid ledger entry. When registry rows are unreadable, this sweep is often the only remaining path to the implementation list; skipping it then silently shrinks the solution to the seed package. **Filtering means classifying listed hits, never shrinking the query or the listing** (SKILL Phase 1, inclusion bias): enumerate the full subtree, ledger every custom-namespace hit — in-scope, or OUT/excluded with a named reason — and only then let excluded rows fall out of the docs. The corner the user's ticket touches never bounds the enumeration; when one base serves many domains, its descendant list IS the solution's implementation census. More-then-prune beats less-then-guess: dropping a listed object at review costs one row, while an unlisted object can never be missed, asked about, or restored.

   **Upward (direction="superTypes"):** Retrieves the superclass chain (parents) of a given class. Use this to:
   - **Discover the inheritance chain** when you start from an implementation and need to find the framework base (e.g., given `ZCL_MY_HANDLER`, walk up to find `ZCL_HANDLER_BASE` → `CL_REST_RESOURCE`). This reveals intermediate abstract layers you might otherwise miss.
   - **Map the full CORE set:** when an implementation inherits from an intermediate Z-class that inherits from a standard SAP class, both the intermediate and the standard class are relevant (CORE and OUT respectively).
   - **Cross-reference inheritance assumptions:** if Phase 1 assumes all implementations share a single base, verify by walking superTypes on a sample of implementations — different branches may reveal multiple parallel hierarchies.
   
   Use both directions on EVERY superclass discovered in CORE, not just the primary one. Secondary bases (error handlers, utility bases, test fixtures) also have subclass trees worth checking. Walking upward from discovered implementations is especially valuable when you enter via a config table (you know the leaf classes but not necessarily their full ancestry).

2. **Naming-convention search:** Infer the implementation naming pattern from:
   - The data element or domain used for the class/object column (e.g., a column typed `Z*_STEP_CLASS` → implementations likely named `ZCL_*_STEP*`)
   - The config table name itself (e.g., table `ZREG_STEPS` with a `step_code` segment → `ZCL_{step_code}_STEP{nn}`)
   - The one or two implementation names visible in CORE code (constructor defaults, examples in comments, test fixtures)
   
   Then wildcard-search using the inferred pattern. Example: seeing one implementation named `ZCL_EXAMPLE_STEP00` → search `ZCL_*STEP*` to find every step class. The `*STEP*` infix, `*HDL*`/`*IMPL*` suffixes, or numbered suffixes (`*00`, `*01`) are common implementation naming conventions — infer yours from the solution in front of you, do not assume any of these.

   **Scope the pattern from the solution's evidence, never from the entry point.** The dispatcher serves every family registered in its config, so the search pattern comes from the registry column's data element, the dispatcher's constants, and implementation names across ALL families — not from the sub-domain the user's ticket happens to touch. A ticket names one corner of the solution; a search narrowed to that corner (e.g. `ZCL_*FAMILY_A*` because the ticket is about family A, when the dispatcher also serves families B, C and D) silently shrinks the boundary to the ticket and produces exactly the documented-one-corner failure.

**Cross-checking for findings:** When both techniques and a config-table SELECT are available, cross-reference the results:
- Objects found by search/hierarchy but NOT in the registry → finding: unregistered implementations (dead code, WIP, or alternate dispatch path — investigate which).
- Objects in the registry but NOT found by search/hierarchy → finding: naming convention violation or different superclass (read these with extra attention).
- Discrepancies between techniques are themselves findings worth documenting.

Record which technique discovered each implementation in the ledger (`discovery: table SELECT`, `discovery: search *STEP*`, `discovery: subclass of <the framework base>`), and report per-technique yields in the Phase 1 closure report (SKILL Phase 1 step 8) — one line per method, "attempted, unavailable because <reason>" when a method genuinely cannot run. Yield lines for hierarchy and naming carry the raw hit count AND the post-filter count, with the filter named; filtering tighter than the solution's namespace requires a stated reason. Run these downward/outward as DISCOVERY (base class → all subclasses; registry data element → all matches), never merely as confirmation of the objects already in hand — a sweep that only re-finds the known set has been pointed the wrong way. The dispatcher's typed reference (the base class or interface its dynamic CREATE is typed to) makes the hierarchy query possible even when registry rows are unreadable — the two methods fail independently, which is why both are mandatory.

**COUNTING GUARDRAIL:** When any discovery output exceeds ~20 items and you need a distinct, filtered, or aggregate count from it, compute it programmatically (python3, jq, shell pipeline) — never estimate visually. Tool outputs are machine-readable; machine-counting is trivial and exact. Human eye-scanning of 30+ similar-looking names (long identifiers differing only in a suffix digit, repeated values across rows) reliably produces wrong numbers. Every number that enters the `CENSUS:` line or a yield report must trace to a programmatic computation, not a mental estimate.

Classification per object:

| Class | Meaning | Read policy |
|---|---|---|
| CORE | Framework kernel: bases, interfaces, dispatcher, config readers | Deep, 100% |
| IMPL | An implementation built on the framework | Tiered (see below) |
| INFRA | Shared utilities, log wrappers, outbound clients | Deep or delta |
| HOOK | Where standard SAP enters or exits the solution (BAdI call site, ICF node, job trigger, event linkage) | Document the contract, not SAP internals |
| EXT | External systems reached (RFC dests, HTTP endpoints, IDoc partners) | Name and describe; do not chase |
| OUT | SAP standard internals | Stop; name only when load-bearing |

Stop rules: do not expand into SAP-standard namespaces except to document a HOOK contract. Exception: customer code inside standard containers (`ZX*` exit includes, VOFM-generated includes, appends, BTE FMs) is inside the boundary — the standard container is the HOOK, the customer half is IMPL. A neighboring Z-solution that merely calls this one is a consumer: name it, note the touchpoint, do not absorb it. When in doubt whether something is inside the boundary, include it as INFRA and let Phase 3 demote it. The census may legitimately exceed the boundary: enumerate broadly, classify strictly — a shared standard base is an enumeration seed, never a membership proof, and a census much larger than the entry point implied triggers the scope question to the user (SKILL Phase 1, boundary rule) instead of either silent empire-building or silent corner-cutting.

Config references override package boundaries: a registry row pointing into a foreign package tree pulls that object in as IMPL. Stopping at the stated root package is the #1 exhaustiveness failure.

Fixpoint check: closure is done when a full pass adds nothing new outside OUT. Report seed size and closed size ("12 seeds closed to 87 objects").

## When there is no framework

Organically grown solutions may have no base class, no registry, no kernel. The methodology holds; three substitutions:

- Domains: carve by data ownership (which tables each unit owns) and by trigger, not by inheritance. Naming clusters are hints, not proof.
- Blessed pattern: the best-built recent unit becomes the reference implementation; quick-start teaches "build the next one like that unit".
- Capability matrix: skip it (there is no framework surface); the de-facto conventions carry the extension story instead.

Shared includes, utility FMs, or copy-paste ancestors often play a hidden kernel role: if the same 30 lines open every report, that IS the framework, just never extracted. Name it.

## Read-depth tiers (Phase 2)

Visit 100% of the inventory. Calibrate depth, not coverage:

| Tier | Applies to | What to do |
|---|---|---|
| deep | CORE; the first implementation of each pattern; anything flagged novel | Read every method. Note lifecycle hooks, defaults, error paths, ABAP Doc comments |
| delta | Further implementations of an already-named pattern | Read fully but record only deltas vs the pattern, plus the novelty checklist: different base? extra config reads? external calls? own error style? dynamic calls? If any answer surprises, promote to deep |
| classify | Empty stubs, generated halves, pure DDIC structures | Open, confirm the classification, one-line note with the reason |

Generated pairs rule: for generated/extension pairs (SEGW `_DPC`/`_DPC_EXT`, proxies, table-maintenance FMs), read the extension deeply and classify the generated base.

**Classify is a read tier, not a skip tier.** Every tier — including classify — means the object was OPENED. Classify exists for objects whose one look confirms there is nothing to pattern-match (stubs, generated halves, DDIC structures); a real handler, service, or any unit with live logic is never `classify` — that is what delta is for, and delta is cheap. Assigning a tier from the object's NAME without opening it is `inferred`, whatever the ledger calls it — and mislabeling it as classify is how a run claims coverage it does not have, mis-patterns objects (the sub-resource handler filed as a plain GET), and walks past bugs sitting in unopened code. Tell-tale: a classify row for a class that other evidence shows has branching logic is a tier violation; re-tier it or relabel it inferred.

Unread objects get a status instead of a tier: `inferred: <basis>` (pattern guessed from siblings, LOW confidence) or `blocked: <reason>` (access failed). The coverage gate mandates that ALL registered implementations be source-read (deep or delta) when a registry table is known — the 60% floor applies only to registry-less solutions where the implementation population is uncertain. The primary implementation of every domain is always read at deep tier.

## Object card (one per object, appended to `research/{domain}.md` as you read)

```markdown
### ZCL_EXAMPLE - <one-line role>

| Property | Value |
|---|---|
| Type / Package | CLAS / ZPKG |
| Classification / Status | IMPL / read-delta |
| Read on / changed on | 2026-07-19 / 2026-03-02 (object's last-change stamp at read time) |
| Pattern | P3 (or NEW:<proposed-name> or NONE:stub) |
| Inherits / Implements | ZCL_BASE / ZIF_STEP |
| Framework surface used | methods and features touched |
| Config consumed | tables + which rows drive it |
| DB touched | tables read/written |
| External | RFC dest, HTTP, IDoc partner, event |
| Error style | exceptions, bapiret, app log, silent |
| Tests | real / stub / none |

**Key logic:** what it does, in bullets.

**Flags:** bug? dead-code? dynamic-calls? auth-check? commit-work?

**Bugs found:** line-level detail, or "none".
```

For procedural units the card describes an include, FM, or FORM cluster; "Inherits / Implements" becomes "called from / performs". The ledger in `research/notes.md` stays a flat table (object | domain file | status | pattern | changed-on stamp) so gates are checkable without opening every domain file. The cards double as the queryable reference for doc maintenance and as the refresh state for later update runs.

## Snippet bank (Phase 2, alongside the cards)

Docs may only contain code copied from read source, and writer agents never re-read the system — so the code must be banked while it is in front of you, in `research/snippets/`:

- One file per pattern exemplar (`p1-<name>.abap`): the complete definition plus the key method implementations — constructor, main flow, error path. Complete means it would compile, not "the interesting lines".
- **Bank the bytes as fetched.** Never re-case, reflow, rename, or tidy source while banking. SAP form-based class sources look messy (lowercase generated section keywords, uppercase identifiers, odd spacing) — that mess is the fingerprint of real source, and it is exactly what the developer sees in SE24/ADT. A beautified bank poisons every downstream provenance diff and is itself the first act of fabrication. Annotation comments may be ADDED (clearly marked); nothing may be changed.
- **Every snippet file opens with a fetch receipt:** a first-line comment `" Fetched: <tool/method> <timestamp> <system> — <object>` written at banking time. A bank entry without a receipt is unfetched — the package validation (Phase V) re-fetches or discards it, and `check_run.py` fails the bank. (Why: a memory-paraphrase written INTO the bank under a real class name defeats every downstream citation check; the receipt turns silent memory-banking into an explicit false claim about a tool call, which is a different and brighter line.)
- One file per copy-worthy idiom (`idiom-<name>.abap`): the exact block (error response, serialization call, lock/commit discipline, log write, test setup).
- Every bug in the register: the offending lines verbatim, headed by the object name.
- Each card points to its snippets (`Snippets: snippets/p1-handler.abap`).

Rule of thumb while reading: "would a recipe, template, troubleshooting row, or anti-pattern want this code?" — if yes, bank it now. A pattern without a banked exemplar cannot yield a full recipe later; the pattern gate counts banked exemplars per pattern.

**Source dump files belong in `research/`.** When you fetch multiple objects' source in batch (e.g. a JSON file keyed by object name containing verbatim source), save the dump inside the run's `research/` directory (e.g. `research/services_source.json`, `research/handlers_source.json`). Never place source dumps at the project root or outside the iteration directory — they are exploration artifacts of THIS run, and `research/` is where all exploration state lives. A source dump at the project root is orphaned from its run and cannot be audited, resumed, or cleaned up.

## Hidden-corner sweep (run once per solution, during Phase 2)

Work the checklist. Most items are one query or one grep. Log "checked, none found" lines in `research/notes.md` so the audit can trust the sweep.

**A. Code that hides from object lists**
- Local classes in class pools (Local Types include), in report includes, in function group TOP includes.
- Customer-exit halves: CMOD/SMOD projects, `EXIT_*` FMs with `ZX*` includes, VOFM-generated routine pools, MV45AFZZ-style userexit includes. Half the container is SAP-owned — grep both namespaces.
- Macros: `DEFINE ... END-OF-DEFINITION` in includes; global macros in TRMAC.
- Includes shared across programs; SUBMIT chains; generated subroutine pools.
- Transformations (XSLT/ST): `CALL TRANSFORMATION` reveals them; also JSON handling style.
- CDS views, metadata extensions, behavior definitions; AMDP methods (code pushed to the DB).
- Dynpros and GUI statuses when the solution has classic UI; Web Dynpro / FPM components in older UIs; BSP applications and UI5 repository apps; SAPscript / Smart Forms / Adobe Forms for output solutions.

**B. Dictionary corners**
- Domain fixed values: they encode the solution's enums and taxonomies (DD07L/T).
- Delivery class of each table: C-tables are config, A-tables are runtime data. This split IS the architecture.
- Lock objects, number ranges (SNRO), table buffering settings, search helps.

**C. Runtime configuration (config is truth)**
- SELECT the actual rows of every registry/config table. Registered beats existing: an unregistered class is dead weight; a registered-but-missing class is a production bug.
- For every config table, record its maintenance route: the generated maintenance view for SM30 (often a Z*V*/ZV* name, not the table itself), a custom maintenance transaction, or a dialog FM. Registration instructions in the docs name this route; "SM30 on the table" is frequently wrong.
- Custom IMG nodes (SIMGH) and view clusters (SM34): some solutions ship their own SPRO tree — that IS the official config surface; document it.
- BTE registrations (FIBF: TBE01/TBE34) and FI validations/substitutions (GGB0/GGB1): Z-logic wired into standard flows purely via customizing.
- `EXPORT/IMPORT ... TO DATABASE` cluster persistence (INDX-style tables) and `TO/FROM MEMORY` / `SET/GET PARAMETER` handoffs: data flow invisible to where-used; grep for all three.
- Order-of-magnitude row counts of the key runtime tables: defines what "big" means in this solution; feeds ops and performance gotchas.
- TVARVC parameters; variant tables; job definitions and their variants; event linkages (SM62, SWETYPV); NAST output types (TNAPR); IDoc process codes; ICF nodes; RFC destinations used.
- File interfaces: `OPEN DATASET` sites and logical file names (FILE); app-server directories are integration surface too.
- BRFplus / decision tables (FDT_* calls): logic living in customizing, not code. Read the decision tables like any registry.
- Record system + client with every config SELECT; DEV rows can lie about PRD behavior, and the delivery class tells you what transports vs what is maintained per system.

**D. Cross-cutting mechanics**
- Authority checks: grep `AUTHORITY-CHECK`; list the objects checked. Zero hits in a data-serving solution is itself a finding.
- Application log usage (SLG0 object/subobject); change documents; archiving.
- LUW discipline: grep `COMMIT WORK`, `ROLLBACK`, `IN UPDATE TASK`, `PERFORM ... ON COMMIT`; who owns the commit is an architecture fact.
- Locking strategy: `ENQUEUE_*`/`DEQUEUE_*` calls.
- Parallelization and push: `STARTING NEW TASK`, SPTA, qRFC/tRFC, background RFC, AMC/APC channels, ABAP Daemons.

**E. Dynamic dispatch (where-used lies here)**
Grep the corpus for:
- `TYPE (` after CREATE OBJECT / NEW, `->(`, `=>(`, `CALL METHOD (`
- `CALL FUNCTION lv_` style variables, `SUBMIT (`, `PERFORM (` ... `IN PROGRAM`
- `GENERATE SUBROUTINE POOL`, `CALL TRANSFORMATION (`, RTTS (`describe_by_name`), dynamic `ASSIGN (`, `INCLUDE ... IF FOUND`
Then: every config-table column whose values look like object names is a dispatch edge. SELECT DISTINCT those columns and add the targets to the worklist.

**F. Forensics (evolution)**
- Sort implementations by creation date: generations appear. The newest blessed pattern is what newcomers must copy; say so explicitly in the docs.
- Change frequency per object: hotspots deserve deeper docs and a gotcha entry.
- ST22 dumps for solution objects (ask the user if no tool): real failure modes feed the troubleshooting table.
- Authors cluster by area: note "history: mostly authored by <team/initials>" for maintainers (keep it factual, not evaluative).
- ATC / Code Inspector results, when available: existing priority findings are the quality baseline and feed gotchas.
- Language version and release contracts: classic ABAP vs ABAP for Cloud Development, released-API usage. Mixed eras are an architecture fact worth stating.
- Mine source comments for change-log blocks and ticket IDs: they date generations, name authors, and link the docs to the team's tracker vocabulary.
- Grep for hardcoded hosts, clients, credentials, RFC destinations, and file paths: each one is a portability or security finding for the register.

**G. Run and observe**
For each paradigm found, record: how to trigger it (transaction, URL + client tool, job start, test class, WE19 for IDocs, RSNAST00 for outputs, SWUS for workflow), and where its traces land (app log, job log, gateway error log, SM58, SM13, SP01, SWI1, ST22). This feeds quick-start and the troubleshooting tables.

## Batch-and-resume protocol (large solutions)

Trigger: inventory > ~40 objects, or context pressure during Phase 2.

**Batch reads (Phase 2):**
- Main context always does: Phase 0-1, CORE deep reads, pattern taxonomy, all synthesis.
- Read IMPL objects in batches of 10-15, grouped by package/domain. After each batch: update ledger rows, verify cards are on disk, count remaining.
- When context compaction fires or tool calls begin failing: STOP. Write `## Resume Point` to notes.md with: last completed object, pending batch (exact names), current pattern taxonomy state, running bug count. The orchestrator re-launches a fresh session.
- On resume: read notes.md, find the Resume Point, pick up from the NEXT pending object. Never re-read objects already marked `read-deep`/`read-delta` in the ledger. The taxonomy and bug register continue accumulating.
- Each session that resumes should: read CORE objects' cards (already on disk) for context, then proceed with the pending batch. Reading the existing domain card files is cheap context that prevents pattern drift across sessions.

**Multi-session convergence:**
- The ledger is the coordination mechanism. Status `pending` = not yet read. A fresh session greps for `pending` rows and reads those.
- The pattern taxonomy may evolve across sessions. Each session re-reads `research/notes.md` §6 and extends it. Contradictions between sessions are resolved in the final synthesis (Phase 3).
- Gates run only when ALL ledger rows have final status. A session that still has pending rows writes the Resume Point and stops — it does not attempt the coverage gate.

**Writer agents:** documentation is no longer this skill's job. The research package this skill produces is handed to `document-abap-solution`, whose writer fan-out can only embed what was banked here — which is why complete cards and a receipted bank are the exit criteria, not a nicety.

## Refresh runs (update without re-exploring)

The ledger and cards ARE the refresh state; every card records the object's last-change stamp at read time.

1. Re-run boundary closure cheaply (object lists plus current change stamps; no source reads yet).
2. Classify the delta: new objects (read per tier rules), changed stamps (re-read at the object's previous tier), gone (mark removed; scrub from docs and data), unchanged (keep the card).
3. Update only affected cards and ledger rows, re-derive the synthesis artifacts, re-run the affected writer briefs (or patch sections when the delta is small), regenerate `solution.json`, rebuild the SPA.
4. Gates run on the delta plus a 5-object spot-check of unchanged cards. The final report lists new / changed / removed objects and the doc sections touched.

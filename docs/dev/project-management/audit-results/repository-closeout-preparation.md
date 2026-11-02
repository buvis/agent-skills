# Repository closeout preparation — 2026-10-30

**Preparation: PASS with explicitly unresolved implementation questions. Stage 1: BLOCKED.**
This report completes investigation and the implementation packet, not repairs,
candidate approval, independent review, or publication. The 126 Windows failures
are accounted for below, including hypotheses that need native Windows tests.
No production code, shipped tests, configuration, PRD lifecycle, or autopilot
state changed. No Claude quota probe was repeated.

## Custody and evidence

Fresh inspection on 2026-10-30 reconciled the interrupted preparation against
the recovery handoff. The recovery inspection is historical evidence only.
Current hashes independently match all **62** entries in
`docs/dev/tmp/closeout-stage-1-20261030/preservation-before.json`.
The original PRD 00133 store remains batch `202610271200`, build/build, 0/1 tasks.
Its state hash remains `a628bcd7a8177f6f488f608bf0f627ec093bc341d79cc3ce93919e6a442619d1`;
its PRD hash remains `ad22e003c161684aee73c44559c08176b0b947a3db56a6a4f031fd71cabc7125`.
Private backups under `.git/recovery-20261030/` remain untouched and untracked.

| Ref / input | Exact commit |
|---|---|
| Local master, diagnostic base | `0035e628f013bbe6147da9d78ac1a19d98c754b9` |
| Previously tested source baseline | `9d1a6e681faab0f97af99f8dd9f471ba1a8becc5` |
| Remote master | `6b52b2ab74388753dce2c89a76f2915e2cdae124` |
| Open migration PR #17 | `9249695b334f2a894bda8e016d974480cece918e` |
| Open setup-uv PR #15 | `34a06221d84b09d3b41fe9b40eca590086b5e73d` |
| Open Node PR #16 | `78596dbb19dc22b0fd511ab903f03834fe68163c` |

Fetch, remote heads, PR states, and latest run list were refreshed. Master is two
documentation commits ahead; its only difference from the tested local baseline
is the execution report. The published remote is an ancestor; the retained
historical range still has 147 commits. All five held-work branch tips match the
execution record. No stashes or Git merge/rebase/cherry-pick/revert operation
exist in the main checkout. The untracked preparation plan is preserved.

At entry and at 12:48 UTC, two worktrees existed: the main checkout and
`docs/dev/tmp/closeout-preparation-20261030-123534/migration-inspection`, on
`prep/closeout-20261030-inspect` at the exact #17 head, with a clean tracked tree.
The latter belonged to the interrupted preparation. At the 12:54 UTC custody
recheck its directory and worktree registration had disappeared, without any
removal command from this session. Its branch still names the exact #17 head;
the evidence directory remains. This session created or removed no worktree or
branch. Only the main worktree remains. Recreate an isolated inspection checkout
from that retained branch if needed, after resolving ownership. Do not delete
the branch or evidence while the external owner is unknown.

`ps -axo pid,ppid,comm` again returned `Operation not permitted`. Empty runtime
lock files do not prove ownership or absence of a process. No lock was cleared.
**Process ownership remains unverified**; supported concurrency/lock checks are a
Stage 1 precondition, not a reason to alter the original store.

Evidence roots (repository-relative; ignored, never stage raw logs):

- `docs/dev/tmp/closeout-stage-1-20261030/`: original baseline and quota evidence.
- `docs/dev/tmp/closeout-preparation-20261030-123534/`: complete hosted logs,
  failure inventory, migration tests, selftests, validators, and disposable probes.
- `docs/dev/tmp/closeout-preparation-completion-20261030/`: fresh preservation,
  log integrity, refs, runs, runtime, lint, braid, and merge-tree measurements.

The two complete Windows logs retain their recorded SHA-256 digests and byte
counts: master 432,028 bytes/3,293 lines; migration 446,035 bytes/3,413 lines.
Cleaned logs preserve line positions. The inventory's unique node IDs match the
FAILED summary lines exactly: 61 + 65 = 126. No excerpt substitutes for these logs.

## Windows diagnosis and ownership

`M` means [run 41032617118](https://github.com/buvis/agent-skills/actions/runs/41032617118)
at remote master above: **61 failed, 4,166 passed, 40 skipped, 2 warnings**, 882.63s.
`G` means [run 41030058506](https://github.com/buvis/agent-skills/actions/runs/41030058506)
at #17 above: **65 failed, 4,062 passed, 43 skipped, 234 warnings**, 1,030.97s.
Both ran hosted Windows CPython 3.13.16. All other jobs passed at those old heads.
These are historical failures, freshly inventoried, not candidate results.

The appendix supplies each node, assertion, traceback line, run, and exact log
range. This table supplies the shared cause, owned source/fixture, minimal repair,
and regression contract for every appendix row. All paths below are relative to
the repository. `W` is the Windows implementer; `A` is the archive implementer.
Line references describe current master unless stated otherwise.

| Cause; M/G count | Evidence, cause classification, and owned locations | Proposed task and regression that must detect the old behavior |
|---|---|---|
| B1; 18/18 | W: `src/agent_skills_braid/cli.py:113,240,457`; `tests/test_braid*.py`. Hosted links resolve to the intended directory but check reports drift. **Hypothesis:** Windows extended readlink spelling versus ordinary resolved paths affects identity and orphan ownership. Local `PureWindowsPath` comparison proves differing spelling only, not the native cause. | W1: inspect native readlink/resolve values, normalize equivalent Windows targets consistently without following away the ownership hop. Require create→check zero drift, stale owned removal, orphan detection, changed-target refusal, junctions and outside-source controls. Do not simply suppress drift. |
| B2; 1/1 | W: `tests/test_braid.py:414`, Kiro replacement in `cli.py:378–394`. Exact POSIX 0640 is asserted on Windows, which exposes different chmod semantics. | W1: compare preserved observable before/after mode on Windows; keep exact POSIX 0640 test and assert backup bytes/resources on both systems. Inject chmod/copy failure where needed; no whole-test skip. |
| P1; 1/1 | W: `skills/create-prd/scripts/ground_prd.py:37,103`, `test_ground_prd.py:225`. Regex excludes drives/backslashes; fixture sets only HOME while Windows home expansion uses Windows environment. Local regex probe reduces a native path to its basename. | W2: parse drive/UNC and mixed slash citations without confusing line-number colon; fixture controls native home lookup. Absolute/home citations resolve independently of supplied root; relative missing controls stay missing. |
| P2; 1/1 | W: `ground_prd.py:157–160`, `test_ground_prd.py:689`. Backslash relative path passed as ripgrep glob lets a PRD confirm its own symbols. Disposable local rg probe proves slash exclusion misses with backslash spelling. | W2: use slash-form exclusion globs. Self-citation and sibling PRDs remain excluded, genuine source hit passes, sorted nonrecursive CLI inputs remain asserted. |
| D1; 1/1 | W: `skills/distil-memory/scripts/docket.py:357`, `test_docket_refusals.py:433`. Directory open produces a platform-dependent OS error without the expected directory diagnosis. | W3: classify directory input explicitly while still catching actual read errors/races. Exit 1 names the path and directory, preserves queue bytes, and retains permission-denied coverage. |
| D2; 4/4 | W: `docket.py:195–200`, `test_docket_unpublished.py:474`. `repr(id)` escapes native separators, so the raw ID is absent from the message; locally reproduced. | W3: choose a deliberate safe diagnostic representation and assert that exact rendered ID, including backslash/newline controls. Preserve identification of the malformed queue entry and refusal; do not remove the ID assertion. |
| D3; 6/6 | W: `skills/distil-memory/scripts/write.py:31–37`, `test_write_atomicity.py`, `test_write_crash_safety.py`. Text-mode atomic writes translate LF to CRLF; hosted bytes and local newline simulation agree. | W3: write the intended UTF-8 bytes or explicit untranslated newlines before rename. All rename-instant, rollback, retry, and existing-CRLF restoration byte assertions remain. Do not alter excluded `funnel.py`/PRD 00133. |
| G1; 1/1 | W: `skills/glean/scripts/glean.py:159`, `test_glean.py:100`. Report uses native separators instead of its expected portable relative identifier. | W4: serialize report identifiers with `as_posix()` while retaining native filesystem paths. Assert exact nested secret-hit IDs and counts on both platforms. |
| U1; 3/3 | W: `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py:93,116,126`; guard in `purge_devtmp.py:144`. Fixture fails creating a TAB filename before reaching the guard. | W4: exercise the invalid candidate through the enumeration/path seam on Windows, assert refusal before any mutation, and retain ordinary-file integration plus real illegal-name tests where the filesystem permits them. No unexplained skip. |
| U2; 1/1 | W: `purge_devtmp.py:174,229,244`, `test_purge_devtmp_manifest.py:250`. Untranslated read followed by translated rewrite duplicates record CR; simulation and hosted `\r\r` agree. | W4: define LF record delimiters and preserve embedded CR bytes; test old CRLF record input and repeated rewrites without newline growth or row loss. |
| S1; 2/2 | W: `skills/sweep-fix/scripts/test_sweep_enumerate.py:585`, `test_sweep_main_setup_errors.py:64`. Fixture calls Unix-only `os.geteuid`. | W4: use the existing denied-read fixture/seam on Windows and retain POSIX permission integration. RuntimeError/CLI exit 1 still names the registry and creates no report. |
| Q1; 2/2 | W: `skills/use-qwen/scripts/test_eval_events.py:84,440`; `eval_harness/events.py`. Production counts actual file bytes; fixture writes translated text but expects source-string bytes. | W5: author explicit capture bytes, including separate LF/CRLF cases. Keep exact byte-count and unknown-completion assertions; do not normalize away real captured bytes. |
| Q2; 4/4 | W: `eval_harness_fixtures.py:84–92`, `test_eval_evidence.py:160,192,248`, `test_run_eval_vet.py:171`. **Hypothesis:** fixture text translation plus Git conversion makes expected source strings disagree with committed/oracle bytes. No native Git config capture yet. | W5: record native `core.autocrlf`, blob and checkout bytes; explicitly control authored fixture bytes/Git config. Preserve contract that seal/oracle matches the specified commit, with intentional CRLF and LF controls. Do not force global checkout policy. |
| Q3; 5/5 | W: `eval_harness_fixtures.py:164`, `test_eval_gates.py:338`, CLI/harness cwd assertions in appendix. Hosted bash `pwd` gives `/c/...`; expected native path gives `C:\...`. | W5: have the fixture report native canonical cwd through the same Python runtime, or convert MSYS spelling explicitly. Keep distinct attempt/baseline/dispatch-tree identity and execution order assertions. |
| Q4; 5/8 | A owns `eval_harness/trees.py:82–196` and `test_eval_tree_links.py:131`; W supplies Windows reproduction. **Hypothesis:** fixture creates directory links as file links; tar extraction also needs correct directory-link handling. Invalid-argument failures prove broken dereference, not its entire cause. | A/W6: infer/declare directory targets for native fixtures, then exercise extraction and clone chains with real directory/file symlinks. Keep safe chain read/hash equivalence with and without data_filter. Master also fails safe compatibility extraction; do not classify every row as fixture-only. |
| Q5; 3/3 | A: `trees.py:267–280`, `_lay_links` at `test_eval_tree_links.py:131`; missing TreeError or wrong hash/absent result. **Unresolved:** malformed directory links can defeat fixture intent; native resolve behavior must be measured. | A/W6: first prove the fixture actually reaches its outside sentinel; then assert refusal before reading bytes, and valid in-tree hash controls. Repair containment if valid links still escape. Never accept a broken link as proof of safety. |
| Q6; 1/1 | A: `trees.py:106,143,180–183`; `test_eval_tree_state.py:238`. Master leaks `tarfile.LinkOutsideDestinationError`; migration fails to refuse. `/etc/passwd` is not reliably absolute under newer Windows `isabs` semantics. | A/W6: validate archive names/targets in archive and Windows path domains, consistently raise TreeError, and test POSIX-rooted, rooted Windows, drive-relative, drive-absolute, UNC, extended paths on both filter branches. |
| Q7; 2/2 | W: `eval_harness/report.py:259`, `test_report.py:501,519`. Test concatenates `/out.txt` onto a native directory, yielding mixed separators unlike production Path joins. | W5: construct expected paths with Path joins; preserve exact byte sizes, missing-wrapper text, and association with the correct attempt. |
| Q8; 0/1 | W: `test_run_eval_vet.py:54,367–377`; vet implementation in `eval_harness/`. Two seconds expires during segment two instead of three. **Hypothesis:** Windows process startup consumes budget; hosted evidence does not prove accounting wrong. | W7: deterministic clock/runner-seam regression proves cumulative deadline across all segments; retain a real bounded-process timeout test. Measure native per-segment elapsed time; do not increase all timeouts to make this pass. |

Python documents Windows readlink substitution paths and chmod limitations;
these support the hypotheses/fixture distinction, not a claim that W1 is fixed.
See [os documentation](https://docs.python.org/3/library/os.html#os.readlink) and
[chmod](https://docs.python.org/3/library/os.html#os.chmod).

## Archive acceptance contract

Target A consolidates held findings **00155–00158**, originating in 00131.
No new identifier or lifecycle change is made here. 00155 owns coverage;
00156 metadata/fallback; 00157 warnings; 00158 ancestor containment.
The existing disposable probe changed an outside sentinel only on the fallback;
the sentinel and destination both lived inside a disposable parent. It used
crafted tar bytes, not proof that ordinary `git archive` emits the exploit.

Apply every row below with callable `tarfile.data_filter` available and with the
attribute absent. Availability must be detected at runtime, including security
backports; never infer it solely from the Python minor version. Root support is
Python >=3.10; mandatory CI currently covers Linux 3.10/3.13 and Windows 3.13.
Add focused Python 3.12 coverage because it exposed omitted-filter warnings;
exercise a newer default-filter runtime when available without weakening the
3.10 floor. No bare/unfiltered `extractall` fallback is acceptable.

| Acceptance | Required behavior and regression | Owner / finding |
|---|---|---|
| A1: ancestor escape | `pkg/`, `alias→pkg`, `alias/escape→../../outside`, `pkg/escape/secret.txt` refuses before outside write; permute member order. | A; 00158 |
| A2: safe links and chains | Regular Git archive, nested files, file symlink, directory symlink, forward safe chain, root/subdirectory chains retain bytes and link semantics through seal and clone. | A; 00155/00158, Q4 |
| A3: traversal and cycles | `../`, deeper climbs, symlink-plus-`..`, self/cyclic chains refuse; valid internal `..` links remain accepted when their actual target stays inside. | A; 00158, Q5 |
| A4: absolute/native paths | POSIX absolute, drive absolute/relative, rooted backslash, UNC, extended prefixes, mixed separators and NTFS stream-like names cannot become outside/native-special writes. Test names and link targets. | A; 00155/00158, Q6 |
| A5: duplicates/collisions | Duplicate normalized names, file/dir swaps, `alias/file` versus `pkg/file`, and platform case/alias collisions refuse before extraction. Test both member orders. | A; 00155 |
| A6: hardlinks/specials | Hardlinks, FIFO, character/block devices and unsupported member types explicitly refuse; no device creation or hardlink dereference. Deleting each refusal must break its regression. | A; 00155 |
| A7: modes/ownership | Ignore archive uid/gid/uname/gname; strip setuid/setgid/sticky and unsafe write bits; retain ordinary file readability and executable controls where supported. Spy on metadata application rather than require privilege. | A; 00156 |
| A8: filter parity | Implement safe manual extraction/metadata normalization when filter absent, or refuse only unsupported unsafe cases with TreeError. Blanket fallback refusal fails existing valid-input controls. | A; 00156 |
| A9: failure atomicity | Every refusal leaves outside sentinels unchanged and no accepted/sealed partial template; injected extraction failure cleans only staging owned by this invocation. Existing destination data is not deleted. | A; all four |
| A10: warnings/errors | Both paths pass `-W error::DeprecationWarning`; do not silence warnings or choose fully_trusted. Translate extraction/filter refusal to TreeError with cause. | A; 00157, Q6 |
| A11: read containment | Valid native directory-link fixture actually reaches sentinel; hash_paths refuses before reading outside bytes. Unrelated in-tree hashes remain correct. | A; 00158, Q5 |
| A12: deliberate refusals | Reject members beneath archive symlinks as the simplest order-independent rule; safe links themselves remain supported. Document this narrower archive subset and test it separately from valid Git archives. | A; 00158 |

Use an isolated staging directory after full member validation, then expose a
completed template only after sealing succeeds. This is a proposed design, not
an implementation mandate if a simpler equivalent satisfies every criterion.
Directory-target inference on Windows and case collisions remain implementation
questions. Python explicitly notes extraction can leave partial output after
failure and filters do not solve every hazard; cleanup is therefore a separate
contract. See [tar extraction filters](https://docs.python.org/3/library/tarfile.html#extraction-filters).

## Seven-skill migration inspection

Inspected the eight-commit diff from `6091e02c41e823f3bd061434edf8bd389ffea8d0`:
42 files, 8,064 additions, including a changelog entry and reserved PRD 00159.
Commit order: `35516ea`, `7d60f6d`, `90fc5d8`, `6400fe4`, `59c1563`,
`10732a2`, `a7c5d23`, `9249695`.
All seven are runnable portable skills with shipped required helpers or prose
workflows, not incomplete plugin documentation. `.braidignore` is unchanged;
no plugin-owned twin was established by this inspection.

| Skill | Dependencies / absence behavior / inspection evidence | Verification and remaining limits |
|---|---|---|
| build-mcp-server | Python 3.11+, uv, pinned `mcp==2.3.0`, `httpx2==2.16.0`; API specification required. Examples, SDK reference, migration guide, scaffold and six smoke tests ship. Instructions label untested transport/OAuth/sampling/migration claims unverified. | Validator passed; six real in-memory-client tests are included in the dependency-enabled 29-pass run. Do not extend observed SDK claims beyond those cases. Root 3.10 suite must retain explicit dependency skips and separate supported-runtime coverage. |
| create-adr | Prose plus shipped `references/adr-template.md`; no external tools or skills. Uses target project location/numbering. | Validator passed; no executable tests required. Inspect rendered ADR against template when invoked; no external write was exercised. |
| explore-abap-solution | Python 3.12+, caller-supplied read-only SAP/source export; unavailable source stops exploration. Ships references, `check_run.py`, pytest wrapper. Document skill is the human next step. | Validator and research validator selftest passed. Receipts require first line; Z/Y/namespaced identifiers covered. File-wide pending-row rule is deliberate. Live SAP existence is a human/provider check, not a validator guarantee. Legacy full mode remains deferred to 00159. |
| document-abap-solution | Validated exploration artifacts hard prerequisite; own Python 3.12+ validator; default Node/Svelte SPA or documented vanilla fallback; blueprints/CSS ship. No SAP access used here. | Validator/selftest passed; full mode reads inline solution-data, not separate JSON. Research-only/full distinction and missing-reference refusal inspected. Generated SPA browser/offline rendering remains unverified. |
| review-abap-solution-documentation | Hard sibling document validator, Python 3.12+, optional SAP; missing sibling stops and missing SAP labels offline-only. Ships trust/review validators and tests. | Both selftests passed; zero-findings test included. No review of real SAP artifacts occurred. Duplicate identifier logic remains 00159, not a silent consolidation in this closeout. |
| publish-confluence-docs | Python >=3.12; pinned python-docx 1.1.2, PyMuPDF 1.25.3, PyYAML 6.0.2; Mermaid CLI 11.16.0 with declared Node range; curl, optional LibreOffice; caller credentials/provider. Missing capability must be reported. Eight conversion/publishing helpers and tests ship. | Validator and offline tests passed; known defects C1/C2 below survive that coverage. REST storage API/auth compatibility, Mermaid/Chromium, LibreOffice and live publishing remain unverified. No writes or credential reads performed. |
| write-abap-specs | Caller SAP/Jira/optional Confluence capabilities; invokes publisher only for Word/PDF. Missing converter requests Markdown; missing writer saves locally and reports unpublished. | Validator passed; prose-only. Portable sibling paths and explicit publication confirmation inspected. No provider API or live issue update exercised. |

All seven validators returned zero at 12:39 UTC on #17, as did the changelog
checker. The dependency-enabled focused run returned **29 passed, 0 skipped,
7 subtests passed, 5 PyMuPDF/Swig deprecation warnings**, 3.72s. Four ABAP
selftest CLIs returned zero at 12:42 UTC. These are **reused**, not rerun here;
the inspection worktree was at that exact clean head before its external removal. No claim is made
that this establishes full migration or corrected-base CI.

| Finding | Evidence / severity | Stage 1 disposition and verification |
|---|---|---|
| C1: upload can falsely succeed | Medium; `publish-confluence-docs/scripts/confluence_attach.py:52–62` checks only stdout HTTP prefix. Disposable mock with curl exit 23 and stdout 200 returns True. `/dev/null` is also hardcoded at line 53. | C owns helper and exit-code tests: require process success plus valid successful HTTP status, use portable response sink, and test nonzero curl with 2xx stdout, missing curl, HTTP failure, success. Do not log tokens. |
| C2: unescaped attachment filename | Medium; `confluence_embed_images.py:48–49` directly inserts filename into XML. Disposable probe returns raw `a&b.png` in an attribute. | C: escape attribute text including ampersand/quotes and test XML roundtrip plus unchanged ordinary-name behavior without network. |
| C3: description points at wrong follow-up | Low; live #17 body says 00150, but branch contains 00159. | Prepare exact replacement: `- Follow-up PRD 00159: consolidate the duplicated validators.` Apply only with later metadata authorization. Keep identifier 00159 reserved. |
| C4: license evidence unresolved | Integration question; #17 body says MIT assumed and references NOTICE.md, but no NOTICE.md exists at that branch root or in its 42-file diff. Root LICENSE alone does not establish imported-material provenance. | Coordinator: locate prior author authorization/source attribution and record it; if absent, obtain the concrete missing provenance confirmation before merge. Correct stale body wording only after evidence exists. No new legal conclusion or publication approval inferred here. |
| C5: dependency disclosure placement | Low; publisher Dependencies follows pipelines/scripts rather than directly after intro, contrary to repository convention. Explore names the document handoff outside its Dependencies section without clearly declaring it as human-only. | C: move publisher Dependencies after intro; state explore→document is a human handoff, with missing-sibling consequence. Validate touched skills. No extra dependency or plugin namespace is needed for these owned standalone siblings. |

These findings are implementation/review inputs, not an independent review.
Retain unverified live integrations explicitly; do not run publishing skill
actions merely to test availability. No shared-validator refactor is requested
by this packet: 00159 is a later follow-up unless formal Stage 1 scope changes.

## Dependency recommendations and diagnostic integration

**#15: conditional merge recommendation.** It changes exactly three setup-uv
references, 10.3.2→10.3.3, in the existing CI workflow. Old head
[run 40944601019](https://github.com/buvis/agent-skills/actions/runs/40944601019)
has successful setup steps on Windows/Linux/lint and successful non-Windows
jobs. Windows fails; the run is not approved. Require corrected candidate
Linux 3.10/3.13, Windows, lint/validator, shell and Node gates plus independent
review. There is no observed reason to reject the patch or attribute every
Windows failure to it; there is no unconditional approval to merge it.

**#16: conditional merge recommendation.** It changes only Node 24→26 in CI.
Old head [run 40944612871](https://github.com/buvis/agent-skills/actions/runs/40944612871)
passed Node and other non-Windows jobs; Windows failed. Local Node 26.13.0
baseline `npm ci`, build, byte-for-byte template comparison and **60 tests**
passed around 10:30 UTC. Meeting app/template inputs are unchanged between that
baseline and #17; reuse this evidence without claiming a candidate rerun.
Require the same build/freshness/test chain on the actual ordered candidate and
its hosted matrix. npm's two low-severity findings and optional unapproved
fsevents install script remain recorded; no unrelated upgrade/policy change.

Fresh `git merge-tree --write-tree` reproduced all saved diagnostic trees.
No checkout merge, semantic conflict resolution, synthetic commit, hook bypass,
or branch mutation was needed. Downstream invocations explicitly used their
verified merge base with the preceding tree as input.

| Diagnostic step | Merge base | Output tree / conflicts |
|---|---|---|
| `0035e62` + exact #17 head | `6091e02c41e823f3bd061434edf8bd389ffea8d0` | `7f77340e3c3475c13cd38e58f785375d66708f6d`; none |
| preceding tree + exact #15 head | `02a1423db9a4c620ccd4f024fe496e8ecfc3f232` | `a739a3fc5a01bdd2e8ec0843beb22941ea6bf562`; none |
| preceding tree + exact #16 head | same `02a1423...` | `d02ad1fb7a6c4c66c23b53859857c8ae22534a5c`; none |

The first step adds the 42 migration paths/changes; the next two change only
their workflow references. All **corrected-base** trees remain **UNMEASURED**:
fixes → #17 → #15 → #16. Once fixes exist, repeat the ordered rehearsal and
record complete tree IDs plus source/test/config subtree IDs for every step.
Clean current-base merges cannot predict semantic compatibility after repairs.
Potential shared edits are `trees.py`/tree tests, workflow lines, migration
publisher helpers and CHANGELOG. Coordinator owns those integration decisions.

## Implementation ownership packet

These are proposed task identifiers, not new PRD numbers or code-selected lanes.
Use the installed autopilot's explicit target authoring/routing on resumption.
Existing closeout Stage 1 requirements own Windows and compatibility tasks;
00155–00158 own archive work. Preserve 00133 and reserved 00159.

| Task | Existing authority / coverage | Exclusive ownership and ordering |
|---|---|---|
| A | Held 00155–00158; A1–A12; Q4–Q6 | `skills/use-qwen/scripts/eval_harness/trees.py`, `test_eval_tree_links.py`, `test_eval_tree_state.py`. Own all extraction/containment changes. W supplies diagnostic evidence and coordinates tests; never co-edits these files. |
| W1 | Closeout Stage 1 Windows; B1/B2 | `src/agent_skills_braid/cli.py`, `tests/test_braid.py`, `tests/test_braid_check.py`. |
| W2 | Same; P1/P2 | create-prd grounder and its test module. |
| W3 | Same; D1–D3 | distil-memory docket/write and named tests; exclude funnel/00133. |
| W4 | Same; G1/U1/U2/S1 | glean, purge-devtmp, sweep-fix files listed in diagnosis. |
| W5 | Same; Q1/Q2/Q3/Q7 | Qwen fixture, events/evidence/report/cwd tests; production change only if demonstrated. Shared `eval_harness_fixtures.py` has one owner. |
| W6 | Same plus archive findings; Q4–Q6 | Windows reproduction supplied to A; execute after fixture validity is established. A implements shared-file repairs. |
| W7 | Same; Q8 | `test_run_eval_vet.py`, `eval_harness/vetting.py:41–43` cumulative deadline; change accounting only if deterministic reproduction proves a defect. |
| C | Stage 1 migration/dependencies; C1–C5 | Seven migration skill files/tests; publisher repairs; metadata/provenance packet; separate #15/#16 recommendations. No live writes. |
| I | Stage 1 integration and verification | Combined branch, workflow/CHANGELOG conflict coordination, source/test/config trees, complete matrix and Windows evidence proposal. Depends on A/W/C. |

Default to sequential work. If execution authorizes concurrency, every editor
gets a separate branch/worktree and physical state path. Suggested namespaces:
`closeout/archive`, `closeout/windows`, `closeout/compatibility`,
`closeout/integration`; state directories under ignored
`docs/dev/tmp/closeout-implementation/<lane>/`. Resolve each absolute state path
and compare it against the original store before `init --state ... --prd ...`.
No default PRD selection; no state initialization or transition occurred here.

Stage 1 verification commands, from the relevant candidate worktree:

```bash
uv run pytest tests/test_braid.py tests/test_braid_check.py
uv run pytest skills/create-prd/scripts/test_ground_prd.py
uv run pytest skills/distil-memory/scripts/test_docket_refusals.py skills/distil-memory/scripts/test_docket_unpublished.py skills/distil-memory/scripts/test_write_atomicity.py skills/distil-memory/scripts/test_write_crash_safety.py
uv run pytest skills/glean skills/purge-devtmp skills/sweep-fix
uv run pytest skills/use-qwen/scripts/test_eval_tree_links.py skills/use-qwen/scripts/test_eval_tree_state.py -W error::DeprecationWarning
uv run pytest skills/use-qwen
uv run --with mcp==2.3.0 --with httpx2==2.16.0 --with python-docx==1.1.2 --with pymupdf==1.25.3 --with pyyaml==6.0.2 python -m pytest -q -ra skills/build-mcp-server skills/create-adr skills/document-abap-solution skills/explore-abap-solution skills/publish-confluence-docs skills/review-abap-solution-documentation skills/write-abap-specs
uv run pytest
uv run ruff check
uv run ruff format --check
uv run braid --check
uv run python scripts/check_changelog_skills.py
uv run pytest scripts/test_check_changelog_skills.py -q
npm --prefix skills/debrief-meeting/app ci
npm --prefix skills/debrief-meeting/app run build
cmp skills/debrief-meeting/app/dist/index.html skills/debrief-meeting/assets/template.html
npm --prefix skills/debrief-meeting/app test
```

Run the dependency-enabled migration command on Python >=3.12; use the root
matrix separately for the 3.10 floor. For **each changed skill**, run
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/<name>`.
Run all four ABAP `--selftest` CLIs as listed in the saved command metadata.
Execute every `skills/*/scripts/test_*.sh` with bash and aggregate nonzero exits
as the CI shell job does. Also validate all skills as the CI lint job does.
Repeat focused archive tests under Python 3.10, 3.12 and 3.13, including filter
attribute removal; the platform matrix remains intact. Record exact SHA,
runtime, counts, skips, warnings, timestamp and logs for every gate.

## Concrete Windows CI proposal — prepared, not executed

Use existing `.github/workflows/ci.yml` (`CI`) and its `workflow_dispatch` event.
It already exists on master. A temporary branch push alone does not trigger its
master-only push route. Dispatch on the temporary ref runs the exact committed
candidate workflow. This follows [GitHub's dispatch documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

Proposed local branch and remote ref: `ci/closeout-stage-1-20261030` /
`refs/heads/ci/closeout-stage-1-20261030`. **Candidate SHA: UNKNOWN.** Before asking
for approval, finish the combined candidate, local checks and commit, verify
this remote ref is unused, and bind its exact SHA in the execution record.
If the ref has appeared, choose an unused dated ref; never overwrite it.
Approval must name the SHA, branch publication, workflow dispatch and optional
eventual deletion. This exposes candidate source/history publicly and consumes
hosted CI capacity; it does not merge master, create a PR or approve Stage 2.

Prepared commands below are for Stage 1 after concrete approval, not this session:

```bash
git branch ci/closeout-stage-1-20261030 closeout/integration
git rev-parse ci/closeout-stage-1-20261030
git ls-remote --heads origin refs/heads/ci/closeout-stage-1-20261030
git push origin ci/closeout-stage-1-20261030:refs/heads/ci/closeout-stage-1-20261030
gh workflow run ci.yml --ref ci/closeout-stage-1-20261030
gh run list --workflow ci.yml --branch ci/closeout-stage-1-20261030 --event workflow_dispatch --json databaseId,headSha,status,conclusion,url
```

Select the new run only after `headSha` matches the approved SHA. Then use
`gh run view RUN_ID --json headSha,status,conclusion,jobs,url` and
`gh run view RUN_ID --job WINDOWS_JOB_ID --log`. Capture complete output through
the existing Python capture helper into ignored evidence files, with exit code
and timestamps; do not use shell redirection into development artifacts.
Workflow has no artifact-upload step: retrieve job logs through gh, not assume
`gh run download` will provide pytest XML. If artifacts are later added, list
them with `gh api repos/{owner}/{repo}/actions/runs/RUN_ID/artifacts` before
downloading named artifacts. Do not change CI just to invent available evidence.

Expected jobs: Linux test 3.10 and 3.13; Windows 3.13 with PYTHONUTF8=1 and
capability probes; shell suites; lint/format/all validators/changelog; Node 26
meeting build/freshness/tests after #16. Windows must not lose symlink capability
checks, CRLF coverage or assertions. Count and explain every skip, including
optional dependencies; successful job status alone is insufficient evidence.

Retain the ref through independent review. After evidence and recovery inputs
are retained and deletion is authorized, cleanup is
`git push origin --delete ci/closeout-stage-1-20261030`; never delete a ref that
has advanced beyond the approved candidate. No push, dispatch, metadata edit,
merge, closure or deletion occurred in preparation.

## Verification status and remaining gates

Fresh checks at `0035e62`: Ruff and formatting pass; braid reports **131 current,
20 ignored, zero drift**, all mutation counters zero. See completion evidence
metadata for UTC start/end times and runtime. **Full suite not rerun here.**
The historical local suite at `9d1a6e6` passed 4,258 tests, skipped nine, warned
twice, in 438.34s at 10:26–10:33 UTC. Eight skips require optional survey parsing
dependency; one is Windows-only. The focused archive warnings gate failed
2/55 tests on Python 3.12.16. Ordinary baseline success does not close defects.

During the final custody check, additional files appeared in the interrupted
session's evidence root: `preparation-full-suite.log` and three lint/braid logs.
The full-suite metadata reports exit 0, 12:40:54–12:47:53 UTC, **4,258 passed,
9 skipped, 2 warnings**, 419.28s. This session did not launch that command.
Its stored stdout hash matches metadata, but metadata lacks cwd and tested SHA;
do not claim exact candidate provenance. It corroborates a baseline result only.
The independently measured checks at 12:48:31 UTC above remain this session's
fresh evidence. External process ownership/removal remains unresolved.

Claude's earlier quota failure reports reset **2026-11-01 10:00 Europe/Prague**.
Do not probe before that time; afterward verify actual capacity. Alice and Blake
remain unavailable on the last measured evidence; Bob/Eve live capacity remains
unmeasured. Preserve the installed workflow's roster, R1–R5 doubt/de-slop lens,
Codex implementation guard, convergence rules and fresh-session boundary.
Do not replace unavailable required reviewers or treat this inspection as review.

Preparation criteria are met: complete Windows inventory with explicit unknowns,
archive contract, seven-skill inspection, two conditional dependency decisions,
diagnostic integration, ownership packet, CI proposal, preservation and handoff.
Stage 1 still needs actual implementation, valid Windows reproduction for the
remaining hypotheses, candidate trees, complete local/hosted checks, capacity
and lock preflight, and a supported build→review transition. Provenance C4 must
be settled before external merge. Final review starts only in a fresh Stage 2
session after Stage 1's complete exit gate; no transition is justified now.

## Windows appendix

## Complete Windows failure matrix

Each row maps one failed node in one run to the shared-cause contract above. `M` and `G` resolve to the exact run/SHA table. Log ranges are inclusive, one-based lines in `<run>-windows-clean.log`; the original unmodified `<run>-windows.log` has the same line positions. The displayed assertion is the failing source statement; full assertions and tracebacks remain in the linked raw logs. All observations in this matrix are real Windows evidence, not local test results.

### M: run 41032617118

Hosted summary: `61 failed, 4166 passed, 40 skipped, 2 warnings in 882.63s (0:14:42)`.

| Row | Failed node ID | Traceback location | Failing source statement | Log lines | Cause / task |
|---|---|---|---|---|---|
| M01 | `tests/test_braid.py::test_sync_composes_union_and_projects_only_eligible_skills` | `tests/test_braid.py:105: AssertionError` | `assert checked.drift == 0` | 430–474; summary 2804 | B1 |
| M02 | `tests/test_braid.py::test_stale_cleanup_removes_only_manifest_owned_links` | `tests/test_braid.py:160: ; src/agent_skills_braid/cli.py:573: in run; src/agent_skills_braid/cli.py:541: BraidError` | `result = run(config) ; raise BraidError(f"refusing to clean changed managed path: {destination}")` | 475–560; summary 2806 | B1 |
| M03 | `tests/test_braid.py::test_no_claude_preserves_existing_projection_and_state` | `tests/test_braid.py:195: AssertionError` | `assert result.drift == 0` | 561–583; summary 2807 | B1 |
| M04 | `tests/test_braid.py::test_kiro_gets_every_skill_including_those_ignored_for_claude` | `tests/test_braid.py:327: AssertionError` | `assert run(config.with_mode(Mode.CHECK)).drift == 0` | 584–621; summary 2809 | B1 |
| M05 | `tests/test_braid.py::test_later_runs_maintain_kiro_without_repeating_the_flags` | `tests/test_braid.py:340: AssertionError` | `assert run(plain.with_mode(Mode.CHECK)).drift == 0` | 622–663; summary 2815 | B1 |
| M06 | `tests/test_braid.py::test_preview_and_check_never_record_kiro_enrollment[dry-run]` | `tests/test_braid.py:355: AssertionError` | `assert run(plain.with_mode(Mode.CHECK)).drift == 0` | 664–697; summary 2821 | B1 |
| M07 | `tests/test_braid.py::test_preview_and_check_never_record_kiro_enrollment[check]` | `tests/test_braid.py:355: AssertionError` | `assert run(plain.with_mode(Mode.CHECK)).drift == 0` | 698–731; summary 2827 | B1 |
| M08 | `tests/test_braid.py::test_selected_agent_gains_the_skill_resource_and_keeps_everything_else` | `tests/test_braid.py:414: AssertionError` | `assert agent.stat().st_mode & 0o777 == 0o640` | 732–769; summary 2833 | B2 |
| M09 | `tests/test_braid.py::test_preview_and_check_report_a_missing_agent_resource_without_writing[dry-run]` | `tests/test_braid.py:525: AssertionError` | `assert result.drift == 1` | 770–803; summary 2837 | B1 |
| M10 | `tests/test_braid.py::test_preview_and_check_report_a_missing_agent_resource_without_writing[check]` | `tests/test_braid.py:525: AssertionError` | `assert result.drift == 1` | 804–837; summary 2839 | B1 |
| M11 | `tests/test_braid.py::test_forgetting_an_agent_stops_managing_it_and_leaves_its_resource` | `tests/test_braid.py:543: AssertionError` | `assert run(plain.with_mode(Mode.CHECK)).drift == 0` | 838–878; summary 2841 | B1 |
| M12 | `tests/test_braid.py::test_cli_enrolls_kiro_and_reports_the_configured_agent` | `tests/test_braid.py:623: AssertionError` | `assert cli.main([*roots, "--check"]) == 0` | 879–917; summary 2847 | B1 |
| M13 | `tests/test_braid_check.py::test_check_leaves_the_orphan_link_it_reports_on_disk[dry-run]` | `tests/test_braid_check.py:55: AssertionError` | `assert reported == [f"MISMATCH ORPHAN {orphan}" for orphan in orphans]` | 918–967; summary 2850 | B1 |
| M14 | `tests/test_braid_check.py::test_check_leaves_the_orphan_link_it_reports_on_disk[check]` | `tests/test_braid_check.py:55: AssertionError` | `assert reported == [f"MISMATCH ORPHAN {orphan}" for orphan in orphans]` | 968–1018; summary 2871 | B1 |
| M15 | `tests/test_braid_check.py::test_check_ignores_a_link_pointing_outside_every_source_root` | `tests/test_braid_check.py:73: AssertionError` | `assert result.drift == 0` | 1019–1044; summary 2893 | B1 |
| M16 | `tests/test_braid_check.py::test_check_after_a_lost_state_file_reports_the_state_not_the_wanted_links` | `tests/test_braid_check.py:93: AssertionError` | `assert reported == [f"MISMATCH STATE {state_path}"]` | 1045–1106; summary 2895 | B1 |
| M17 | `tests/test_braid_check.py::test_check_reports_a_kiro_link_the_state_does_not_record` | `tests/test_braid_check.py:107: AssertionError` | `assert reported == [f"MISMATCH ORPHAN {stray}"]` | 1107–1153; summary 2928 | B1 |
| M18 | `tests/test_braid_check.py::test_read_only_run_names_the_hand_changed_path_and_finishes_the_report[dry-run]` | `tests/test_braid_check.py:158: AssertionError` | `assert reported[0] == f"MISMATCH CHANGED {stale}"` | 1154–1179; summary 2953 | B1 |
| M19 | `tests/test_braid_check.py::test_read_only_run_names_the_hand_changed_path_and_finishes_the_report[check]` | `tests/test_braid_check.py:158: AssertionError` | `assert reported[0] == f"MISMATCH CHANGED {stale}"` | 1180–1205; summary 2957 | B1 |
| M20 | `skills/create-prd/scripts/test_ground_prd.py::test_citation_absolute_and_home_paths_ignore_root` | `skills/create-prd/scripts/test_ground_prd.py:231: AssertionError` | `assert citation_status(text, other_root) == {` | 1206–1243; summary 2961 | P1 |
| M21 | `skills/create-prd/scripts/test_ground_prd.py::test_cli_directory_argument_expands_non_recursively_to_sorted_md_files` | `skills/create-prd/scripts/test_ground_prd.py:689: AssertionError` | `assert code == 1` | 1244–1287; summary 2981 | P2 |
| M22 | `skills/distil-memory/scripts/test_docket_refusals.py::test_main_decide_refuses_a_file_flag_that_exists_but_cannot_be_read_as_a_file` | `skills/distil-memory/scripts/test_docket_refusals.py:433: AssertionError` | `assert "directory" in captured.err.lower()` | 1288–1326; summary 2982 | D1 |
| M23 | `skills/distil-memory/scripts/test_docket_unpublished.py::test_unpublished_raises_queue_error_naming_the_entry_when_a_queue_entry_is_malformed[transcript missing]` | `skills/distil-memory/scripts/test_docket_unpublished.py:474: AssertionError` | `assert entry_id in str(raised.value)` | 1327–1346; summary 2986 | D2 |
| M24 | `skills/distil-memory/scripts/test_docket_unpublished.py::test_unpublished_raises_queue_error_naming_the_entry_when_a_queue_entry_is_malformed[transcript null]` | `skills/distil-memory/scripts/test_docket_unpublished.py:474: AssertionError` | `assert entry_id in str(raised.value)` | 1347–1366; summary 2989 | D2 |
| M25 | `skills/distil-memory/scripts/test_docket_unpublished.py::test_unpublished_raises_queue_error_naming_the_entry_when_a_queue_entry_is_malformed[transcript not a string]` | `skills/distil-memory/scripts/test_docket_unpublished.py:474: AssertionError` | `assert entry_id in str(raised.value)` | 1367–1386; summary 2992 | D2 |
| M26 | `skills/distil-memory/scripts/test_docket_unpublished.py::test_unpublished_raises_queue_error_naming_the_entry_when_a_queue_entry_is_malformed[decision missing]` | `skills/distil-memory/scripts/test_docket_unpublished.py:474: AssertionError` | `assert entry_id in str(raised.value)` | 1387–1406; summary 2995 | D2 |
| M27 | `skills/distil-memory/scripts/test_write_atomicity.py::test_atomic_write_target_is_complete_the_instant_the_rename_lands[_write_the_memory_file]` | `skills/distil-memory/scripts/test_write_atomicity.py:69: AssertionError` | `assert snapshots == {name: expected}` | 1407–1442; summary 2998 | D3 |
| M28 | `skills/distil-memory/scripts/test_write_atomicity.py::test_atomic_write_target_is_complete_the_instant_the_rename_lands[_write_the_index]` | `skills/distil-memory/scripts/test_write_atomicity.py:69: AssertionError` | `assert snapshots == {name: expected}` | 1443–1478; summary 3013 | D3 |
| M29 | `skills/distil-memory/scripts/test_write_atomicity.py::test_a_later_fault_does_not_revert_an_earlier_success` | `skills/distil-memory/scripts/test_write_atomicity.py:183: AssertionError` | `assert target_path.read_bytes() == first_text.encode()` | 1479–1526; summary 3028 | D3 |
| M30 | `skills/distil-memory/scripts/test_write_crash_safety.py::test_main_write_rolls_the_store_back_byte_for_byte_when_the_index_step_fails[removes_only_the_new_memory_file_when_the_pointer_write_fails_and_a_retry_then_succeeds]` | `skills/distil-memory/scripts/test_write_crash_safety.py:389: AssertionError` | `assert _store_bytes(store_path) == _encoded(after)` | 1527–1598; summary 3040 | D3 |
| M31 | `skills/distil-memory/scripts/test_write_crash_safety.py::test_main_write_rolls_the_store_back_byte_for_byte_when_the_index_step_fails[leaves_a_store_that_had_no_index_without_one_when_the_pointer_write_fails_and_a_retry_then_succeeds]` | `skills/distil-memory/scripts/test_write_crash_safety.py:389: AssertionError` | `assert _store_bytes(store_path) == _encoded(after)` | 1599–1661; summary 3065 | D3 |
| M32 | `skills/distil-memory/scripts/test_write_crash_safety.py::test_main_write_rolls_the_store_back_byte_for_byte_when_the_index_step_fails[restores_the_updated_targets_original_text_and_the_index_when_the_pointer_write_fails_and_a_retry_then_succeeds]` | `skills/distil-memory/scripts/test_write_crash_safety.py:389: AssertionError` | `assert _store_bytes(store_path) == _encoded(after)` | 1662–1728; summary 3081 | D3 |
| M33 | `skills/glean/scripts/test_glean.py::test_dir_prescreen_counts_soft_hits_and_lists_hard_ones` | `skills/glean/scripts/test_glean.py:100: AssertionError` | `assert [h["file"] for h in c["secret_hits"]] == [".config/newtool/key"]` | 1729–1753; summary 3101 | G1 |
| M34 | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py::test_process_store_refuses_tab_path_and_still_trashes_ordinary_file` | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py:93: ; CPython-3.13.16/Lib/pathlib/_local.py:555: in write_text; CPython-3.13.16/Lib/pathlib/_abc.py:651: in write_text; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `unsafe.write_text("y") ; return io.open(self, mode, buffering, encoding, errors, newline)` | 1754–1792; summary 3112 | U1 |
| M35 | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py::test_process_store_verbose_reports_the_refusal_reason` | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py:116: ; CPython-3.13.16/Lib/pathlib/_local.py:555: in write_text; CPython-3.13.16/Lib/pathlib/_abc.py:651: in write_text; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `unsafe.write_text("y") ; return io.open(self, mode, buffering, encoding, errors, newline)` | 1793–1828; summary 3113 | U1 |
| M36 | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py::test_dry_run_never_touches_filesystem_for_unsafe_path` | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py:126: ; CPython-3.13.16/Lib/pathlib/_local.py:555: in write_text; CPython-3.13.16/Lib/pathlib/_abc.py:651: in write_text; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `unsafe.write_text("y") ; return io.open(self, mode, buffering, encoding, errors, newline)` | 1829–1863; summary 3114 | U1 |
| M37 | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py::test_manifest_rewrite_preserves_an_unrelated_row_containing_a_carriage_return` | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py:250: AssertionError` | `assert cr_line in manifest_lines` | 1864–1889; summary 3115 | U2 |
| M38 | `skills/sweep-fix/scripts/test_sweep_enumerate.py::test_enumerate_repos_raises_runtimeerror_naming_an_unreadable_registry` | `skills/sweep-fix/scripts/test_sweep_enumerate.py:585: AttributeError` | `if os.geteuid() == 0:` | 1890–1902; summary 3116 | S1 |
| M39 | `skills/sweep-fix/scripts/test_sweep_main_setup_errors.py::test_an_unreadable_registry_exits_one_naming_the_path_and_writes_no_report` | `skills/sweep-fix/scripts/test_sweep_main_setup_errors.py:64: AttributeError` | `if os.geteuid() == 0:` | 1903–1916; summary 3117 | S1 |
| M40 | `skills/use-qwen/scripts/test_eval_events.py::test_reads_a_missing_transcript_as_unknown_however_noisy_the_capture_is[short]` | `skills/use-qwen/scripts/test_eval_events.py:440: AssertionError` | `assert result["final_message_bytes"] == len(capture.encode("utf-8"))` | 1917–1937; summary 3118 | Q1 |
| M41 | `skills/use-qwen/scripts/test_eval_events.py::test_reads_a_missing_transcript_as_unknown_however_noisy_the_capture_is[long]` | `skills/use-qwen/scripts/test_eval_events.py:440: AssertionError` | `assert result["final_message_bytes"] == len(capture.encode("utf-8"))` | 1938–1958; summary 3122 | Q1 |
| M42 | `skills/use-qwen/scripts/test_eval_evidence.py::test_seal_records_the_template_it_built_in_pretask_and_manifest` | `skills/use-qwen/scripts/test_eval_evidence.py:160: AssertionError` | `assert pretask["writable"]["calc.py"] == _sha256(` | 1959–1984; summary 3126 | Q2 |
| M43 | `skills/use-qwen/scripts/test_eval_evidence.py::test_seal_copies_each_oracle_path_as_the_task_commit_left_it` | `skills/use-qwen/scripts/test_eval_evidence.py:192: AssertionError` | `assert copied == eval_harness_fixtures.WIDENED_ORACLE.encode("utf-8")` | 1985–2010; summary 3130 | Q2 |
| M44 | `skills/use-qwen/scripts/test_eval_evidence.py::test_seal_spans_the_whole_task_range_from_before_first_to_last` | `skills/use-qwen/scripts/test_eval_evidence.py:248: AssertionError` | `assert (template / "calc.py").read_bytes() == eval_harness_fixtures.BROKEN_IMPL.encode("utf-8")` | 2011–2045; summary 3142 | Q2 |
| M45 | `skills/use-qwen/scripts/test_eval_gates.py::test_baseline_runs_the_vetted_oracle_in_each_attempt_s_own_clone` | `skills/use-qwen/scripts/test_eval_gates.py:338: AssertionError` | `assert lines == [_resolved(site.attempt_dir / "baseline-clone") for site in (first, second)]` | 2046–2079; summary 3154 | Q3 |
| M46 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_build_template_seals_a_safe_tree_with_or_without_tar_data_filter[without-data-filter]` | `skills/use-qwen/scripts/test_eval_tree_links.py:443: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / "nested").read_bytes() == b"nested\n" ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2080–2132; summary 3169 | Q4 |
| M47 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_fresh_clone_copies_a_link_chain_that_stays_inside_the_template[through-a-link-to-the-root]` | `skills/use-qwen/scripts/test_eval_tree_links.py:560: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2133–2182; summary 3170 | Q4 |
| M48 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_fresh_clone_copies_a_link_chain_that_stays_inside_the_template[under-the-names-the-escaping-chains-use]` | `skills/use-qwen/scripts/test_eval_tree_links.py:560: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2183–2233; summary 3171 | Q4 |
| M49 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_fresh_clone_copies_a_link_chain_that_stays_inside_the_template[through-a-link-to-a-subdirectory]` | `skills/use-qwen/scripts/test_eval_tree_links.py:560: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2234–2284; summary 3172 | Q4 |
| M50 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_fresh_clone_copies_a_link_chain_that_stays_inside_the_template[through-a-link-in-a-subdirectory-that-climbs-back-to-the-root]` | `skills/use-qwen/scripts/test_eval_tree_links.py:560: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2285–2334; summary 3173 | Q4 |
| M51 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_hash_paths_refuses_a_listed_path_that_resolves_outside_the_root[two-hops-out-through-a-link-to-the-root]` | `skills/use-qwen/scripts/test_eval_tree_links.py:609: Failed` | `with pytest.raises(trees.TreeError):` | 2335–2373; summary 3174 | Q5 |
| M52 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_hash_paths_refuses_a_listed_path_that_resolves_outside_the_root[six-hops-out-through-a-chain-of-links-to-the-root]` | `skills/use-qwen/scripts/test_eval_tree_links.py:609: Failed` | `with pytest.raises(trees.TreeError):` | 2374–2411; summary 3175 | Q5 |
| M53 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_hash_paths_still_hashes_the_tree_s_own_files_beside_a_link_that_leaves_it` | `skills/use-qwen/scripts/test_eval_tree_links.py:652: AssertionError` | `assert hashes == {"passwd": inside, "pkg/calc.py": inside, "same": inside}` | 2412–2444; summary 3176 | Q5 |
| M54 | `skills/use-qwen/scripts/test_eval_tree_state.py::test_build_template_refuses_a_source_tree_whose_symlink_leaves_it[absolute-target]` | `skills/use-qwen/scripts/test_eval_tree_state.py:239: ; skills/use-qwen/scripts/eval_harness/trees.py:181: in build_template; CPython-3.13.16/Lib/tarfile.py:2420: in extractall; CPython-3.13.16/Lib/tarfile.py:2510: in _get_extract_tarinfo; CPython-3.13.16/Lib/tarfile.py:2508: in _get_extract_tarinfo; CPython-3.13.16/Lib/tarfile.py:889: in data_filter; CPython-3.13.16/Lib/tarfile.py:876: LinkOutsideDestinationError` | `trees.build_template(repo, first, dest) ; raise LinkOutsideDestinationError(member, target_path)` | 2445–2574; summary 3189 | Q6 |
| M55 | `skills/use-qwen/scripts/test_report.py::test_captured_output_line_reports_real_byte_sizes_for_out_and_wrapper` | `skills/use-qwen/scripts/test_report.py:504: AssertionError` | `assert expected in block.splitlines()` | 2575–2598; summary 3190 | Q7 |
| M56 | `skills/use-qwen/scripts/test_report.py::test_captured_output_line_reports_wrapper_unavailable_when_the_file_is_absent` | `skills/use-qwen/scripts/test_report.py:519: AssertionError` | `assert ("%s/wrapper.txt (unavailable bytes)" % attempt_dir) in block` | 2599–2618; summary 3193 | Q7 |
| M57 | `skills/use-qwen/scripts/test_run_eval_cli.py::test_every_attempt_runs_its_baseline_then_the_shape_s_gates_in_order_and_no_other[description]` | `skills/use-qwen/scripts/test_run_eval_cli.py:159: AssertionError` | `assert _logged_cwds(round_, vetted.log) == [` | 2619–2659; summary 3194 | Q3 |
| M58 | `skills/use-qwen/scripts/test_run_eval_cli.py::test_every_attempt_runs_its_baseline_then_the_shape_s_gates_in_order_and_no_other[tdd]` | `skills/use-qwen/scripts/test_run_eval_cli.py:159: AssertionError` | `assert _logged_cwds(round_, vetted.log) == [` | 2660–2696; summary 3210 | Q3 |
| M59 | `skills/use-qwen/scripts/test_run_eval_harness.py::test_each_gate_runs_in_its_own_tree_and_the_own_gate_in_the_dispatch_clone` | `skills/use-qwen/scripts/test_run_eval_harness.py:331: AssertionError` | `assert sorted(_logged_cwds(round_, vetted.log)) == sorted(` | 2697–2727; summary 3222 | Q3 |
| M60 | `skills/use-qwen/scripts/test_run_eval_harness_outcomes.py::test_every_attempt_runs_the_baseline_in_its_own_baseline_clone` | `skills/use-qwen/scripts/test_run_eval_harness_outcomes.py:188: AssertionError` | `assert sorted(c for c in cwds if c.endswith("baseline-clone")) == sorted(` | 2728–2753; summary 3238 | Q3 |
| M61 | `skills/use-qwen/scripts/test_run_eval_vet.py::test_a_tdd_oracle_in_a_directory_the_template_lacks_dispatches_and_passes` | `skills/use-qwen/scripts/test_run_eval_vet.py:171: AssertionError` | `assert _read_json(where / "sealed.json")["oracle"] == {` | 2754–2795; summary 3249 | Q2 |

Group reconciliation: B1=18, B2=1, D1=1, D2=4, D3=6, G1=1, P1=1, P2=1, Q1=2, Q2=4, Q3=5, Q4=5, Q5=3, Q6=1, Q7=2, S1=2, U1=3, U2=1; total **61**.

### G: run 41030058506

Hosted summary: `65 failed, 4062 passed, 43 skipped, 234 warnings in 1030.97s (0:17:10)`.

| Row | Failed node ID | Traceback location | Failing source statement | Log lines | Cause / task |
|---|---|---|---|---|---|
| G01 | `tests/test_braid.py::test_sync_composes_union_and_projects_only_eligible_skills` | `tests/test_braid.py:105: AssertionError` | `assert checked.drift == 0` | 447–491; summary 2918 | B1 |
| G02 | `tests/test_braid.py::test_stale_cleanup_removes_only_manifest_owned_links` | `tests/test_braid.py:160: ; src/agent_skills_braid/cli.py:573: in run; src/agent_skills_braid/cli.py:541: BraidError` | `result = run(config) ; raise BraidError(f"refusing to clean changed managed path: {destination}")` | 492–577; summary 2920 | B1 |
| G03 | `tests/test_braid.py::test_no_claude_preserves_existing_projection_and_state` | `tests/test_braid.py:195: AssertionError` | `assert result.drift == 0` | 578–600; summary 2921 | B1 |
| G04 | `tests/test_braid.py::test_kiro_gets_every_skill_including_those_ignored_for_claude` | `tests/test_braid.py:327: AssertionError` | `assert run(config.with_mode(Mode.CHECK)).drift == 0` | 601–638; summary 2923 | B1 |
| G05 | `tests/test_braid.py::test_later_runs_maintain_kiro_without_repeating_the_flags` | `tests/test_braid.py:340: AssertionError` | `assert run(plain.with_mode(Mode.CHECK)).drift == 0` | 639–680; summary 2929 | B1 |
| G06 | `tests/test_braid.py::test_preview_and_check_never_record_kiro_enrollment[dry-run]` | `tests/test_braid.py:355: AssertionError` | `assert run(plain.with_mode(Mode.CHECK)).drift == 0` | 681–714; summary 2935 | B1 |
| G07 | `tests/test_braid.py::test_preview_and_check_never_record_kiro_enrollment[check]` | `tests/test_braid.py:355: AssertionError` | `assert run(plain.with_mode(Mode.CHECK)).drift == 0` | 715–748; summary 2941 | B1 |
| G08 | `tests/test_braid.py::test_selected_agent_gains_the_skill_resource_and_keeps_everything_else` | `tests/test_braid.py:414: AssertionError` | `assert agent.stat().st_mode & 0o777 == 0o640` | 749–786; summary 2947 | B2 |
| G09 | `tests/test_braid.py::test_preview_and_check_report_a_missing_agent_resource_without_writing[dry-run]` | `tests/test_braid.py:525: AssertionError` | `assert result.drift == 1` | 787–820; summary 2951 | B1 |
| G10 | `tests/test_braid.py::test_preview_and_check_report_a_missing_agent_resource_without_writing[check]` | `tests/test_braid.py:525: AssertionError` | `assert result.drift == 1` | 821–854; summary 2953 | B1 |
| G11 | `tests/test_braid.py::test_forgetting_an_agent_stops_managing_it_and_leaves_its_resource` | `tests/test_braid.py:543: AssertionError` | `assert run(plain.with_mode(Mode.CHECK)).drift == 0` | 855–895; summary 2955 | B1 |
| G12 | `tests/test_braid.py::test_cli_enrolls_kiro_and_reports_the_configured_agent` | `tests/test_braid.py:623: AssertionError` | `assert cli.main([*roots, "--check"]) == 0` | 896–934; summary 2961 | B1 |
| G13 | `tests/test_braid_check.py::test_check_leaves_the_orphan_link_it_reports_on_disk[dry-run]` | `tests/test_braid_check.py:55: AssertionError` | `assert reported == [f"MISMATCH ORPHAN {orphan}" for orphan in orphans]` | 935–984; summary 2964 | B1 |
| G14 | `tests/test_braid_check.py::test_check_leaves_the_orphan_link_it_reports_on_disk[check]` | `tests/test_braid_check.py:55: AssertionError` | `assert reported == [f"MISMATCH ORPHAN {orphan}" for orphan in orphans]` | 985–1035; summary 2985 | B1 |
| G15 | `tests/test_braid_check.py::test_check_ignores_a_link_pointing_outside_every_source_root` | `tests/test_braid_check.py:73: AssertionError` | `assert result.drift == 0` | 1036–1061; summary 3007 | B1 |
| G16 | `tests/test_braid_check.py::test_check_after_a_lost_state_file_reports_the_state_not_the_wanted_links` | `tests/test_braid_check.py:93: AssertionError` | `assert reported == [f"MISMATCH STATE {state_path}"]` | 1062–1123; summary 3009 | B1 |
| G17 | `tests/test_braid_check.py::test_check_reports_a_kiro_link_the_state_does_not_record` | `tests/test_braid_check.py:107: AssertionError` | `assert reported == [f"MISMATCH ORPHAN {stray}"]` | 1124–1170; summary 3042 | B1 |
| G18 | `tests/test_braid_check.py::test_read_only_run_names_the_hand_changed_path_and_finishes_the_report[dry-run]` | `tests/test_braid_check.py:158: AssertionError` | `assert reported[0] == f"MISMATCH CHANGED {stale}"` | 1171–1196; summary 3067 | B1 |
| G19 | `tests/test_braid_check.py::test_read_only_run_names_the_hand_changed_path_and_finishes_the_report[check]` | `tests/test_braid_check.py:158: AssertionError` | `assert reported[0] == f"MISMATCH CHANGED {stale}"` | 1197–1222; summary 3071 | B1 |
| G20 | `skills/create-prd/scripts/test_ground_prd.py::test_citation_absolute_and_home_paths_ignore_root` | `skills/create-prd/scripts/test_ground_prd.py:231: AssertionError` | `assert citation_status(text, other_root) == {` | 1223–1260; summary 3075 | P1 |
| G21 | `skills/create-prd/scripts/test_ground_prd.py::test_cli_directory_argument_expands_non_recursively_to_sorted_md_files` | `skills/create-prd/scripts/test_ground_prd.py:689: AssertionError` | `assert code == 1` | 1261–1304; summary 3095 | P2 |
| G22 | `skills/distil-memory/scripts/test_docket_refusals.py::test_main_decide_refuses_a_file_flag_that_exists_but_cannot_be_read_as_a_file` | `skills/distil-memory/scripts/test_docket_refusals.py:433: AssertionError` | `assert "directory" in captured.err.lower()` | 1305–1343; summary 3096 | D1 |
| G23 | `skills/distil-memory/scripts/test_docket_unpublished.py::test_unpublished_raises_queue_error_naming_the_entry_when_a_queue_entry_is_malformed[transcript missing]` | `skills/distil-memory/scripts/test_docket_unpublished.py:474: AssertionError` | `assert entry_id in str(raised.value)` | 1344–1363; summary 3100 | D2 |
| G24 | `skills/distil-memory/scripts/test_docket_unpublished.py::test_unpublished_raises_queue_error_naming_the_entry_when_a_queue_entry_is_malformed[transcript null]` | `skills/distil-memory/scripts/test_docket_unpublished.py:474: AssertionError` | `assert entry_id in str(raised.value)` | 1364–1383; summary 3103 | D2 |
| G25 | `skills/distil-memory/scripts/test_docket_unpublished.py::test_unpublished_raises_queue_error_naming_the_entry_when_a_queue_entry_is_malformed[transcript not a string]` | `skills/distil-memory/scripts/test_docket_unpublished.py:474: AssertionError` | `assert entry_id in str(raised.value)` | 1384–1403; summary 3106 | D2 |
| G26 | `skills/distil-memory/scripts/test_docket_unpublished.py::test_unpublished_raises_queue_error_naming_the_entry_when_a_queue_entry_is_malformed[decision missing]` | `skills/distil-memory/scripts/test_docket_unpublished.py:474: AssertionError` | `assert entry_id in str(raised.value)` | 1404–1423; summary 3109 | D2 |
| G27 | `skills/distil-memory/scripts/test_write_atomicity.py::test_atomic_write_target_is_complete_the_instant_the_rename_lands[_write_the_memory_file]` | `skills/distil-memory/scripts/test_write_atomicity.py:69: AssertionError` | `assert snapshots == {name: expected}` | 1424–1459; summary 3112 | D3 |
| G28 | `skills/distil-memory/scripts/test_write_atomicity.py::test_atomic_write_target_is_complete_the_instant_the_rename_lands[_write_the_index]` | `skills/distil-memory/scripts/test_write_atomicity.py:69: AssertionError` | `assert snapshots == {name: expected}` | 1460–1495; summary 3127 | D3 |
| G29 | `skills/distil-memory/scripts/test_write_atomicity.py::test_a_later_fault_does_not_revert_an_earlier_success` | `skills/distil-memory/scripts/test_write_atomicity.py:183: AssertionError` | `assert target_path.read_bytes() == first_text.encode()` | 1496–1543; summary 3142 | D3 |
| G30 | `skills/distil-memory/scripts/test_write_crash_safety.py::test_main_write_rolls_the_store_back_byte_for_byte_when_the_index_step_fails[removes_only_the_new_memory_file_when_the_pointer_write_fails_and_a_retry_then_succeeds]` | `skills/distil-memory/scripts/test_write_crash_safety.py:389: AssertionError` | `assert _store_bytes(store_path) == _encoded(after)` | 1544–1615; summary 3154 | D3 |
| G31 | `skills/distil-memory/scripts/test_write_crash_safety.py::test_main_write_rolls_the_store_back_byte_for_byte_when_the_index_step_fails[leaves_a_store_that_had_no_index_without_one_when_the_pointer_write_fails_and_a_retry_then_succeeds]` | `skills/distil-memory/scripts/test_write_crash_safety.py:389: AssertionError` | `assert _store_bytes(store_path) == _encoded(after)` | 1616–1678; summary 3179 | D3 |
| G32 | `skills/distil-memory/scripts/test_write_crash_safety.py::test_main_write_rolls_the_store_back_byte_for_byte_when_the_index_step_fails[restores_the_updated_targets_original_text_and_the_index_when_the_pointer_write_fails_and_a_retry_then_succeeds]` | `skills/distil-memory/scripts/test_write_crash_safety.py:389: AssertionError` | `assert _store_bytes(store_path) == _encoded(after)` | 1679–1745; summary 3195 | D3 |
| G33 | `skills/glean/scripts/test_glean.py::test_dir_prescreen_counts_soft_hits_and_lists_hard_ones` | `skills/glean/scripts/test_glean.py:100: AssertionError` | `assert [h["file"] for h in c["secret_hits"]] == [".config/newtool/key"]` | 1746–1770; summary 3215 | G1 |
| G34 | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py::test_process_store_refuses_tab_path_and_still_trashes_ordinary_file` | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py:93: ; CPython-3.13.16/Lib/pathlib/_local.py:555: in write_text; CPython-3.13.16/Lib/pathlib/_abc.py:651: in write_text; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `unsafe.write_text("y") ; return io.open(self, mode, buffering, encoding, errors, newline)` | 1771–1809; summary 3226 | U1 |
| G35 | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py::test_process_store_verbose_reports_the_refusal_reason` | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py:116: ; CPython-3.13.16/Lib/pathlib/_local.py:555: in write_text; CPython-3.13.16/Lib/pathlib/_abc.py:651: in write_text; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `unsafe.write_text("y") ; return io.open(self, mode, buffering, encoding, errors, newline)` | 1810–1845; summary 3227 | U1 |
| G36 | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py::test_dry_run_never_touches_filesystem_for_unsafe_path` | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py:126: ; CPython-3.13.16/Lib/pathlib/_local.py:555: in write_text; CPython-3.13.16/Lib/pathlib/_abc.py:651: in write_text; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `unsafe.write_text("y") ; return io.open(self, mode, buffering, encoding, errors, newline)` | 1846–1880; summary 3228 | U1 |
| G37 | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py::test_manifest_rewrite_preserves_an_unrelated_row_containing_a_carriage_return` | `skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py:250: AssertionError` | `assert cr_line in manifest_lines` | 1881–1906; summary 3229 | U2 |
| G38 | `skills/sweep-fix/scripts/test_sweep_enumerate.py::test_enumerate_repos_raises_runtimeerror_naming_an_unreadable_registry` | `skills/sweep-fix/scripts/test_sweep_enumerate.py:585: AttributeError` | `if os.geteuid() == 0:` | 1907–1919; summary 3230 | S1 |
| G39 | `skills/sweep-fix/scripts/test_sweep_main_setup_errors.py::test_an_unreadable_registry_exits_one_naming_the_path_and_writes_no_report` | `skills/sweep-fix/scripts/test_sweep_main_setup_errors.py:64: AttributeError` | `if os.geteuid() == 0:` | 1920–1933; summary 3231 | S1 |
| G40 | `skills/use-qwen/scripts/test_eval_events.py::test_reads_a_missing_transcript_as_unknown_however_noisy_the_capture_is[short]` | `skills/use-qwen/scripts/test_eval_events.py:440: AssertionError` | `assert result["final_message_bytes"] == len(capture.encode("utf-8"))` | 1934–1954; summary 3232 | Q1 |
| G41 | `skills/use-qwen/scripts/test_eval_events.py::test_reads_a_missing_transcript_as_unknown_however_noisy_the_capture_is[long]` | `skills/use-qwen/scripts/test_eval_events.py:440: AssertionError` | `assert result["final_message_bytes"] == len(capture.encode("utf-8"))` | 1955–1975; summary 3236 | Q1 |
| G42 | `skills/use-qwen/scripts/test_eval_evidence.py::test_seal_records_the_template_it_built_in_pretask_and_manifest` | `skills/use-qwen/scripts/test_eval_evidence.py:160: AssertionError` | `assert pretask["writable"]["calc.py"] == _sha256(` | 1976–2001; summary 3240 | Q2 |
| G43 | `skills/use-qwen/scripts/test_eval_evidence.py::test_seal_copies_each_oracle_path_as_the_task_commit_left_it` | `skills/use-qwen/scripts/test_eval_evidence.py:192: AssertionError` | `assert copied == eval_harness_fixtures.WIDENED_ORACLE.encode("utf-8")` | 2002–2027; summary 3244 | Q2 |
| G44 | `skills/use-qwen/scripts/test_eval_evidence.py::test_seal_spans_the_whole_task_range_from_before_first_to_last` | `skills/use-qwen/scripts/test_eval_evidence.py:248: AssertionError` | `assert (template / "calc.py").read_bytes() == eval_harness_fixtures.BROKEN_IMPL.encode("utf-8")` | 2028–2062; summary 3256 | Q2 |
| G45 | `skills/use-qwen/scripts/test_eval_gates.py::test_baseline_runs_the_vetted_oracle_in_each_attempt_s_own_clone` | `skills/use-qwen/scripts/test_eval_gates.py:338: AssertionError` | `assert lines == [_resolved(site.attempt_dir / "baseline-clone") for site in (first, second)]` | 2063–2096; summary 3268 | Q3 |
| G46 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_build_template_seals_a_link_chain_that_stays_inside_the_tree[through-a-link-to-the-root]` | `skills/use-qwen/scripts/test_eval_tree_links.py:229: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2097–2149; summary 3283 | Q4 |
| G47 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_build_template_seals_a_link_chain_that_stays_inside_the_tree[under-the-names-the-escaping-chains-use]` | `skills/use-qwen/scripts/test_eval_tree_links.py:229: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2150–2203; summary 3284 | Q4 |
| G48 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_build_template_seals_a_link_chain_that_stays_inside_the_tree[through-a-link-to-a-subdirectory]` | `skills/use-qwen/scripts/test_eval_tree_links.py:229: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2204–2257; summary 3285 | Q4 |
| G49 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_build_template_seals_a_link_chain_that_stays_inside_the_tree[through-a-link-in-a-subdirectory-that-climbs-back-to-the-root]` | `skills/use-qwen/scripts/test_eval_tree_links.py:229: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2258–2310; summary 3286 | Q4 |
| G50 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_fresh_clone_copies_a_link_chain_that_stays_inside_the_template[through-a-link-to-the-root]` | `skills/use-qwen/scripts/test_eval_tree_links.py:300: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2311–2360; summary 3287 | Q4 |
| G51 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_fresh_clone_copies_a_link_chain_that_stays_inside_the_template[under-the-names-the-escaping-chains-use]` | `skills/use-qwen/scripts/test_eval_tree_links.py:300: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2361–2411; summary 3288 | Q4 |
| G52 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_fresh_clone_copies_a_link_chain_that_stays_inside_the_template[through-a-link-to-a-subdirectory]` | `skills/use-qwen/scripts/test_eval_tree_links.py:300: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2412–2462; summary 3289 | Q4 |
| G53 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_fresh_clone_copies_a_link_chain_that_stays_inside_the_template[through-a-link-in-a-subdirectory-that-climbs-back-to-the-root]` | `skills/use-qwen/scripts/test_eval_tree_links.py:300: ; CPython-3.13.16/Lib/pathlib/_abc.py:625: in read_bytes; CPython-3.13.16/Lib/pathlib/_local.py:537: OSError` | `assert (dest / last).read_bytes() == landing.read_bytes() ; return io.open(self, mode, buffering, encoding, errors, newline)` | 2463–2512; summary 3290 | Q4 |
| G54 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_hash_paths_refuses_a_listed_path_that_resolves_outside_the_root[two-hops-out-through-a-link-to-the-root]` | `skills/use-qwen/scripts/test_eval_tree_links.py:349: Failed` | `with pytest.raises(trees.TreeError):` | 2513–2551; summary 3291 | Q5 |
| G55 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_hash_paths_refuses_a_listed_path_that_resolves_outside_the_root[six-hops-out-through-a-chain-of-links-to-the-root]` | `skills/use-qwen/scripts/test_eval_tree_links.py:349: Failed` | `with pytest.raises(trees.TreeError):` | 2552–2589; summary 3292 | Q5 |
| G56 | `skills/use-qwen/scripts/test_eval_tree_links.py::test_hash_paths_still_hashes_the_tree_s_own_files_beside_a_link_that_leaves_it` | `skills/use-qwen/scripts/test_eval_tree_links.py:392: AssertionError` | `assert hashes == {"passwd": inside, "pkg/calc.py": inside, "same": inside}` | 2590–2622; summary 3293 | Q5 |
| G57 | `skills/use-qwen/scripts/test_eval_tree_state.py::test_build_template_refuses_a_source_tree_whose_symlink_leaves_it[absolute-target]` | `skills/use-qwen/scripts/test_eval_tree_state.py:238: Failed` | `with pytest.raises(trees.TreeError):` | 2623–2652; summary 3306 | Q6 |
| G58 | `skills/use-qwen/scripts/test_report.py::test_captured_output_line_reports_real_byte_sizes_for_out_and_wrapper` | `skills/use-qwen/scripts/test_report.py:504: AssertionError` | `assert expected in block.splitlines()` | 2653–2676; summary 3307 | Q7 |
| G59 | `skills/use-qwen/scripts/test_report.py::test_captured_output_line_reports_wrapper_unavailable_when_the_file_is_absent` | `skills/use-qwen/scripts/test_report.py:519: AssertionError` | `assert ("%s/wrapper.txt (unavailable bytes)" % attempt_dir) in block` | 2677–2696; summary 3310 | Q7 |
| G60 | `skills/use-qwen/scripts/test_run_eval_cli.py::test_every_attempt_runs_its_baseline_then_the_shape_s_gates_in_order_and_no_other[description]` | `skills/use-qwen/scripts/test_run_eval_cli.py:159: AssertionError` | `assert _logged_cwds(round_, vetted.log) == [` | 2697–2737; summary 3311 | Q3 |
| G61 | `skills/use-qwen/scripts/test_run_eval_cli.py::test_every_attempt_runs_its_baseline_then_the_shape_s_gates_in_order_and_no_other[tdd]` | `skills/use-qwen/scripts/test_run_eval_cli.py:159: AssertionError` | `assert _logged_cwds(round_, vetted.log) == [` | 2738–2774; summary 3327 | Q3 |
| G62 | `skills/use-qwen/scripts/test_run_eval_harness.py::test_each_gate_runs_in_its_own_tree_and_the_own_gate_in_the_dispatch_clone` | `skills/use-qwen/scripts/test_run_eval_harness.py:331: AssertionError` | `assert sorted(_logged_cwds(round_, vetted.log)) == sorted(` | 2775–2805; summary 3339 | Q3 |
| G63 | `skills/use-qwen/scripts/test_run_eval_harness_outcomes.py::test_every_attempt_runs_the_baseline_in_its_own_baseline_clone` | `skills/use-qwen/scripts/test_run_eval_harness_outcomes.py:188: AssertionError` | `assert sorted(c for c in cwds if c.endswith("baseline-clone")) == sorted(` | 2806–2831; summary 3355 | Q3 |
| G64 | `skills/use-qwen/scripts/test_run_eval_vet.py::test_a_tdd_oracle_in_a_directory_the_template_lacks_dispatches_and_passes` | `skills/use-qwen/scripts/test_run_eval_vet.py:171: AssertionError` | `assert _read_json(where / "sealed.json")["oracle"] == {` | 2832–2873; summary 3366 | Q2 |
| G65 | `skills/use-qwen/scripts/test_run_eval_vet.py::test_the_warmup_budget_runs_down_across_every_earlier_segment` | `skills/use-qwen/scripts/test_run_eval_vet.py:377: AssertionError` | `assert len(record["warmup"]) == 3, record["warmup"]` | 2874–2894; summary 3376 | Q8 |

Group reconciliation: B1=18, B2=1, D1=1, D2=4, D3=6, G1=1, P1=1, P2=1, Q1=2, Q2=4, Q3=5, Q4=8, Q5=3, Q6=1, Q7=2, Q8=1, S1=2, U1=3, U2=1; total **65**.

## First-session custody reconciliation

The original preparation session continued while the completion account above
was written. Its firsthand
[custody addendum](repository-closeout-preparation-session-123534.md) identifies
the owner of the inspection worktree removal, records deletion of its disposable
branch alias, binds the fresh full-suite command to its actual cwd/source SHA,
and preserves additional inspection findings C6/C7 and native-link hypotheses.
Read it before resuming Stage 1. It supplements this report without erasing
the concurrent account. The original migration branch and all 62 preserved
files remain unchanged; no corrected candidate or Stage 2 gate exists.



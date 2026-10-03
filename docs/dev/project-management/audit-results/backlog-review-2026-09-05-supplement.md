# Backlog review supplement — additions during the apply pass

The original review covered 00016–00052 (17 PRDs). PRDs 00053–00074
arrived while its decisions were being applied. They have now been read in
full and grounded across all 22 additions. Routine corrections have been
applied. Only 00057 awaits a human scope choice; this supplement is not a GO.

## Findings and corrective direction

| PRD | Location | Finding and downstream failure | Resolution |
|---|---|---|---|
| 00053 | Requirements; Phase 0 inventory; Phase 1 comparison | File/line-prefixed rg output cannot remain equal after moves. Converting ordinary helpers to injected fixtures contradicts byte-identical tests. Rework thrash. | Compare extracted test-name multiplicities plus marker metadata; allow import/helper wiring changes while preserving test bodies. Scope scans to future task locations, not historical mentions or 00053 itself. |
| 00054 | Phase 0; Success Criteria | The cited existing metadata-403 test does not exist; current metadata tests cover other errors. | Add an explicit 403 control; preserve existing actual tests. |
| 00055 | Solution; Must have; Phase 0 | Adherence returns count/distinct/top, not days; naive timestamps raise on aware comparison; silent filtering contradicts mandatory WARN. Wrong-TDD lock-in/rework thrash. | Reject naive/invalid/future timestamps; cadence asserts days, adherence counts within 30 days; only unexpected reader exceptions trigger the main-level WARN. |
| 00056 | Must have history clause; Success Criteria | Current history_counts intentionally leaves partially fetched repos unmarked, with f=0 for missing CI; done 00028 and test_history_counts_leaves_a_partly_fetched_repo_unmarked pin it. The page can show both its empty state and missing-collection explanation. Rework thrash. | Keep the chosen current-CI warning fix; remove the false claim that it also changes history semantics or removes the existing empty-state text. Record history precision as residual debt. |
| 00057 | Solution; Phase 0; Success Criteria | Unix mode assertions and BSD stat cannot establish owner-only Windows access and conflict with 00044. Temporary snapshot files are also written before final chmod; the one fixture both precreates and newly creates its directory. Wrong-TDD lock-in/goal reversal. | Human scope decision: native permissions on both hosts, explicit POSIX-only protection, or hold. Either implementation must cover temporary snapshots and separate new-directory/rotation fixtures. |
| 00058 | Phase 1 hostile payload and built-template assertion | App consumes normalized url, not API html_url; raw external/security/manual todo fields and post-spread values need coverage. Minification removes safeUrl's source name. Wrong-TDD lock-in/rework thrash. | Use app-shaped hostile data and allowed-URL controls at all consumers, including Brief window.open. Verify built behavior and copied bytes, not symbol spelling. |
| 00059 | Solution history decoding | Preserve existing last-60 nonblank input window and physical line numbers; coordinate with 00065. | Warn for invalid retained rows; preserve their physical line numbers and skip them without backfilling older rows. |
| 00060 | Problem; final wc criterion | Only the first following row fuses; repair adds two newline bytes that first time, not one. Rework thrash. | Assert one newly decodable record per run, with an extra separator on repair. |
| 00061 | Local collectors reordered; Success Criteria | Adding prds before metadata failure removes history e:1 under the existing predicate. Existing metadata-failure history regression then fails. Goal reversal/rework thrash. | Preserve the failed-metadata history marker while retaining local facts; keep partial CI failure semantics from 00056. |
| 00062 | Solution; exports; Phase 0; component ownership | collect_commits returns a list; history c is per repo; Brief reads derive.js aggregate. Required count on failed metadata cannot be known. Wrong-TDD lock-in. | Pin a separate count producer and top-level key, per-repo history mapping, aggregate fallback and explicit missing-count behavior. |
| 00063 | Entire PRD | Core premise and named xfail are grounded. | Retain; re-ground moved test location after 00053. |
| 00064 | Entire PRD | Core premise and named real-symlink xfail are grounded. | Retain real Windows symlink coverage from 00044. |
| 00065 | Solution; retained-window requirement | Raw deque includes blanks; current code excludes them before taking 60, so a trailing blank drops a valid point. Wrong-TDD lock-in. | Keep 60 nonblank raw rows with physical line numbers, then use 00059 decoding rule. |
| 00066 | Problem; URL clause | Clipboard currently exports repo plus action only; adding an unspecified URL suffix invents behavior. | Preserve current format; sanitize action, remove the nonexistent URL clause. Escape existing backslashes before brackets. |
| 00067 | Solution premise | Existing no-match branch already raises a skip-producing RuntimeError. | Keep parsing fix; preserve that branch rather than invent another one. |
| 00068 | Success Criteria; hoist | Earlier 00062 adds a subprocess, invalidating 18/54 totals. Unguarded hoist can escape per-collector isolation. Rework thrash/goal reversal. | Assert one branch lookup and one fewer call than the immediately prior implementation; preserve failure isolation. |
| 00069 | Mutation check | Reverting delay injection proves slow timing, not the older-timer race. Wrong-TDD lock-in. | Keep the short injected window; remove prior-timer cancellation to prove the survival assertion fails, then restore and rebuild. |
| 00070 | purge helper task | Changes the same projected helper called by the active autopilot drain as held 00035. Loop self-harm. | Isolate as attended work or a dedicated final batch item; HOLD in the ordinary backlog. Ground remaining predicates before reactivation. |
| 00071 | write.py recovery, docket contract | Earlier 00017 owns pointer rollback. File existence misses stranded updates; repeated writes duplicate pointers; same-state decisions can double-count cursor/session counters. | Applied dependencies on 00015–00017, idempotent memory/pointer writes, exact unpublished id/exit/read-failure contract and unchanged counters on recovery. |
| 00072 | Exact judge kwargs; long-input fake | Shared FakeClaudeCli and main tests parse prompts/model by argv position, so the stdin change breaks them. Windows needs a runnable fake CLI. | Migrate all argv consumers, preserve the judge's 120-second bound and 00034's separate typing-timeout diagnostic, and use a portable fake subprocess. |
| 00073 | Tool resolution “before anything else”; YAML swap | Earlier 00032 requires output validation first. ensure_ascii=False emits YAML-invalid DEL and normalizes U+0085; existing tests pin unquoted text. The proposed cwd regression already passed the buggy code. | Applied validation-before-tools order, ASCII-safe JSON encoding/control-character cases, parsed-value assertion migration, and a cwd test rejecting the nested duplicate while observing a root sibling. |
| 00074 | Success Criteria; broad rg guards | Cursor comparison observes the wrong state after start; the validator swap lacks a distinguishing input; unused capsys has no production behavior to revert. | Applied capped-queue rearming with stable lifetime cursor, general-valid/distil-invalid edit coverage, scoped exception assertions and separate static fixture checks. |

## Evidence

Grounding sources: collect.py metadata/collectors/history_counts/write_snapshot;
build.py history tail; derive.js aggregate/allTodos; Work, Brief, Todos and
RepoDetail components; their current tests; done 00028's partial-failure contract.
The three grounding agents returned all initial and follow-up findings. A
read-only scalar probe verified DEL/C1 failure and safe ASCII escaping. No live-model round or
native Windows test ran during this review. All changes here concern PRD text.

## State

Routine corrections applied to 00053–00056, 00058–00062 and 00065–00069;
00063/00064 remain unchanged and grounded. Corrections also applied to
00071–00074. The concurrent author moved 00070 to hold for the same live-helper
isolation reason this review identified; its factual retention wording was
corrected here. Its implementation needs an isolated run.

00057 remains unchanged pending the presented platform-permission choice.
All 39 reviewed documents (initial and supplemental sets) passed final
heading/order, Acceptance, frontmatter and numbering checks; 99 tasks total.
The main report and WIP-owner handoff carry the remaining two batch blockers.

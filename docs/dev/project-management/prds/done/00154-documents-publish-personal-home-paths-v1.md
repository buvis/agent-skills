---
design: run
default_model: sonnet
model_tier_rationale: Portable path serialization requires consumer compatibility and a bounded tracked-document inventory.
---

# Documents publish personal home paths

> **Closed (2026-11-15):** the operator retired autocodex for this repository, so its host writers under `~/.config/autocodex/` no longer write here and the last open task is moot. The remaining absolute paths in `docs/dev/project-management/autopilot/` and in the `autocodex_*_receipt:` lines of review files are rewritten, and `scripts/test_public_doc_paths.py` now checks every tracked project-management document with no exclusion. Receipts written by autocodex before this date no longer verify against its adapter; that is accepted. The encoded form (`-Users-<name>-...`) is rewritten and tested too. Commits before this PRD keep the old text; the operator chose not to rewrite published history. If autocodex is used here again, fix its writers first or this test fails.

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 46, audit dated 2026-10-25. User accepted option A on 2026-10-29. Status remains unverified: the audit combined static path searches with a writer code read, without a product run demonstrating a newly generated disclosure.

## Problem

The audit reported personal absolute home paths in 49 tracked project-management documents and observed that proposal manifests serialize absolute transcript paths. The repository forbids personal paths in public artifacts. Existing documents retain machine-specific identifiers, and generators can repeat the pattern.

## Solution

Use repository-relative paths where appropriate and home-relative notation for references beneath the operator's home. Update affected generators and their consumers together, scrub current tracked documents, and add a focused regression check. Preserve historical commits and tags.

## Requirements

### Must have

- Inventory the current tracked project-management documents with personal home prefixes before editing. The historical count of 49 is not an exact current target.
- During design, enumerate the concrete document and generator paths to change and add that inventory to this PRD's structural decomposition. Do not approve an unbounded sweep of unrelated files.
- Generated reports and proposal/discard manifests must not serialize the operator's absolute home prefix. Use portable paths, with correct component-boundary checks rather than arbitrary substring replacement.
- Update consumers that open or compare serialized transcript paths so home-relative paths resolve intentionally. Preserve legacy absolute records, stable evidence association, queue deduplication, and store ownership checks.
- Scrub the identified current tracked documents with context-aware replacements, preserving evidence meaning and valid repository-relative links. Review link destinations and structured data separately from prose.
- Add a regression check for personal home prefixes in tracked project-management documents, including prefixes from other machines; allow explicit generic placeholders such as /Users/you and synthetic fixture values outside that public-document scope.
- Cover the autocodex host writers too (added 2026-11-10 by operator decision, PRD 00135 review-1 R3). The driver and adapter under `~/.config/autocodex/` write absolute paths into tracked files: `autocodex-metrics.jsonl` rows (`raw`), review receipts (`output`, `raw`), and the `autocodex_<lens>_<provider>_receipt:` lines of review files. Make new records repo-relative. The adapter's receipt checks and `review-route` must accept both the legacy absolute form and the new form, so existing receipts keep validating. That code sits outside this repository and is read-only in the agent sandbox: route the change through warrant or an operator hand-off.
- Keep diagnostics free of copied private path contents where a path-only diagnostic suffices. Do not add the actual operator prefix to the test source or this PRD.
- Preserve git history and tags. Correcting current documents does not erase historical exposure.

### Nice to have

None.

## Implementation

Initial confirmed code locations and planned regression file:

```text
skills/distil-memory/scripts/
  portable.py               # new: home-relative write, deliberate expansion on read
  proposal.py
  funnel.py
  docket.py
  funnel_test_helpers.py    # make_corpus pins home outside tmp_path
  test_portable.py          # new
  test_proposal_publication.py
  test_funnel_distil.py
  test_docket.py
  test_docket_unpublished.py
scripts/
  test_public_doc_paths.py  # new tracked-document regression
docs/dev/project-management/  # the 56 files listed under "Current document inventory"
```

The local audit report remains the durable original evidence; do not copy private home paths into tracked planning artifacts.

### Design decisions (recorded 2026-11-15)

- **Portable path rule.** A transcript path under the operator's home is written `~/<rest>` with forward slashes. The home is matched by whole path components (`Path.relative_to(Path.home())`), never by string prefix. A path outside the home names no person and is written unchanged, so the non-home representation is the path as given. Relative text and text already starting `~/` pass through unchanged.
- **Reading.** `portable.local_path` expands a leading `~/` against this machine's home and takes anything else as written, so legacy absolute records keep working.
- **Queue identity.** `docket.slice_key` builds ids from the portable form. Saved ids are compared through the same normalization (`_same_slice`), so a legacy absolute id and a new home-relative proposal for the same transcript and line are one slice for deduplication and rejection. Stored ids are never rewritten.
- **Store ownership.** `unpublished` and its store warning expand the stored transcript with `local_path` before resolving `<transcript dir>/memory`.
- **Reports.** The yield report names its proposals directory repository-relative, the same base as the `docs/dev/project-management/audit-results/` it already names.

### Current document inventory (measured 2026-11-15)

Tracked files under `docs/dev/project-management/` with a personal home prefix, outside `autopilot/`: 56 files, 199 occurrences, all from one operator home. Each occurrence was rewritten to home-relative notation. Three prose spots where the prefix itself was the subject now use the placeholder `/Users/<name>` so the sentence keeps its meaning (the 00135 review and ledger finding, two lines of a published proposal's evidence text), and one agoge-profile line now says "the absolute home path". `autocodex_<lens>_<provider>_receipt:` lines were left as written.

- `audit-results/`: `00008-distil-yield.md`, `agoge-2026-08-31.md`, `agoge-2026-09-05.json`, `agoge-2026-09-05.md`, `distil-memory-20260830T162841Z-proposals/discards.json`, `distil-memory-20260830T162841Z-proposals/proposals.json`
- `audit-results/qwen38-vs-sonnet-multifile-2026-09-03-bundle/`: `candidates.md`, `evidence.md`, `manifest.tsv`, `runs/2-qwen-a3.session.jsonl`, `runs/4-qwen-a1.session.jsonl`, and `tasks/` `1-repoint-bim-doc-callers.vetting.md`, `2-route-tui-create-note.vetting.md`, `3-repoint-zettel-save.vetting.md`, `4-record-raw-source-sha.vetting.md`, `5-surface-reindex-skip-warnings.vetting.md`, `6-cap-frontmatter-size.vetting.md`, `alt1-surface-reindex-skip-warnings.vetting.md`, `dq5-generalize-write-lock.vetting.md`
- `designs/00120-link-check-noise-hides-dead-references-v1-design.md`, `meta/agoge-profile.md`, `prds/done/00013-build-dir-overwrites-live-dashboard-v1.md`
- `reviews/`: `00002-add-sweep-fix-skill-v1-review-1.md`, `00002-...-review-2.md`, `00003-add-plan-port-skill-v1-review-2.md`, `00007-extract-memory-candidates-from-transcripts-v1-review-1.md`, `00007-...-review-2.md`, `00009-walk-memory-proposal-queue-v1-review-1.md`, `00009-...-review-2.md`, `00015-corrupt-queue-reads-as-drained-v1-review-1.md`, `00022-node-ci-and-install-docs-v1-review-1.md`, `00029-cut-v010-clean-changelog-v1-review-1.md`, `00030-survey-prunes-skip-dirs-deep-v1-ledger.json`, `00030-...-review-1.md`, `00030-...-review-2.md`, `00034-timeout-leaks-prompt-to-disk-v1-review-1.md`, `00038-braid-docs-flags-and-backup-paths-v1-review-1.md`, `00038-...-review-2.md`, `00045-survey-single-read-and-log-time-trim-v1-review-1.md`, `00045-...-review-2.md`, `00052-qwen-eval-harness-report-v1-review-1.md`, `00052-...-review-2.md`, `00055-bad-metrics-ts-aborts-run-v1-audit.md`, `00055-...-ledger.json`, `00055-...-review-2.md`, `00057-data-json-world-readable-v1-review-1.md`, `00058-page-links-accept-javascript-urls-v1-review-1.md`, `00059-build-dies-on-torn-inputs-v1-review-1.md`, `00075-ground-prd-claims-against-installed-code-v1-review-1.md`, `00075-...-review-2.md`, `00076-distil-tests-see-non-atomic-writes-v1-review-1.md`, `00079-split-test-survey-under-the-cap-v1-review-1.md`, `00120-link-check-noise-hides-dead-references-v1-audit.md`, `00120-...-review-1.md`, `00135-historical-tag-awaits-green-ci-v1-ledger.json`, `00135-...-review-1.md`

Not scrubbed, pending the autocodex host-writer task below:

- `docs/dev/project-management/autopilot/` (about 50 tracked files: loop state, metrics, ledgers, and hash-pinned review inputs and receipts). The host writers still emit absolute paths there, and the adapter's receipt checks read them. `scripts/test_public_doc_paths.py` excludes this directory with a commented reason naming this task.
- `autocodex_<lens>_<provider>_receipt:` lines in review files (for example the 00089 and 00135 reviews), excluded line by line in the same test for the same reason.

Residual, outside this PRD's prefix rule: Claude Code encodes a project directory as its absolute path with separators turned into `-`, so transcript paths such as `~/.claude/projects/-Users-<name>-.../<session>.jsonl` carried the username in encoded form. That form was first left as is; it is now rewritten to `-Users-you-...` and covered by the test (see the closing note above).

### Module: Portable artifact paths

- **Location**: `skills/distil-memory/scripts/proposal.py`, `skills/distil-memory/scripts/funnel.py`
- **Maps-to-capability**: Generated artifacts avoid personal absolute home prefixes.
- **Responsibility**: Serialize portable source and report references without altering transcript content or evidence meaning.
- **Exports**: `write_proposals`, `render_yield`, and existing report output.

#### Feature: Portable serialization

- **Inputs**: Source transcript paths, generated artifact paths, home and repository context.
- **Outputs**: Portable references preserving the intended source identity.
- **Behavior**: Prefer repository-relative references when the consumer has that context; represent home descendants with home-relative notation and expand deliberately at the I/O boundary. Define a safe non-home external-path representation during design rather than copying another user's identifier. Avoid resolving a display-only reference merely to reconstruct an absolute public string.

### Module: Path consumers

- **Location**: `skills/distil-memory/scripts/docket.py` and its existing tests listed above.
- **Maps-to-capability**: Portable references retain queue identity and store matching.
- **Responsibility**: Normalize accepted old and new path forms consistently at comparison/open boundaries.
- **Exports**: Existing docket commands and proposal-loading behavior.

### Module: Current documents and regression check

- **Location**: Concrete documents enumerated during design; new regression file scripts/test_public_doc_paths.py.
- **New symbols**: `scripts/test_public_doc_paths.py`.
- **Maps-to-capability**: Existing public documents are scrubbed and future home-prefix regressions fail verification.
- **Responsibility**: Inspect tracked paths rather than unrelated ignored local artifacts; report offending relative filenames without reproducing private contents.
- **Exports**: Pytest regression collected by the existing scripts test path.

### Dependencies

- Path writers and consumers must land together. Existing proposal publication, docket deduplication, and unpublished-store tests are compatibility controls.
- The existing pytest configuration collects scripts tests; no new CI service or external scanner is needed.

## Tasks

### Phase 0: Bounded inventory and repair

- [ ] Enumerate the current tracked-document occurrences and demonstrated generators/consumers, record concrete paths in the design and this PRD, and define reversible portable path rules. Keep private prefixes out of tracked artifacts.
- [ ] Update generators and consumers together, covering both portable and legacy records without duplicate queue entries or incorrect store matching.
- [ ] Scrub the enumerated current documents while preserving structured formats, evidence meaning, and valid links. Review the complete document diff.
- [ ] Make the autocodex host writers emit repo-relative metrics and receipt paths, with readers accepting legacy absolute records; validate an existing receipt and a new one through the adapter's receipt check.
- [ ] Add the tracked-document home-prefix regression and synthetic-home generator/consumer tests. Assert fake home prefixes are absent from published artifacts and portable references resolve to the correct source locally.
- [ ] Run `uv run pytest skills/distil-memory/scripts scripts/test_public_doc_paths.py` and repository-required checks before committing. Validate any additional touched skill.

Exit criteria: The bounded current-document inventory is scrubbed, new artifacts omit personal home prefixes, old/new path consumers retain behavior, and regression checks pass.

## Success Criteria

- No personal absolute home prefix remains in the scoped tracked public documents.
- Generator tests demonstrate portable output and correct consumer round trips.
- Existing queue identity, store matching, and proposal publication tests pass.

### Test Strategy

Original suspected evidence, preserved verbatim:

```text
`rg -l "<home>" docs/dev/project-management` -> 49 files; `git ls-files` confirms the sampled ones are tracked.
```

The source deliberately uses a placeholder for the private prefix. Recompute the current inventory during design without treating the historical count as a measured current fact. Use fake home directories for runtime regressions, including proposal and discard manifests, rendered reports, legacy absolute records, and equivalent portable records. Verify deduplication and store ownership comparisons use the same source identity. The new tracked-document check must detect a synthetic personal prefix while allowing documented generic examples.

### Risks

Blind text replacement can break links or structured records. Tilde strings do not expand automatically in Path construction, and changing serialized strings can defeat queue deduplication. Coordinate writers and consumers, preserve legacy records, and review the bounded scrub. History continues to contain old paths by explicit preserve-history policy.

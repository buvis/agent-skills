## Architecture fit

`check_links.py` (PRD 00081, extended by PRD 00100) is a single-file scanner
under `skills/review-prd-backlog/scripts/`, invoked standalone (`--root
--json`) and from `review-prd-backlog`'s own backlog audit. It has three
regex-driven reference kinds (`PATH_RE`, `PRD_RE`, `MEM_RE`), a single
`WAIVER` escape (`link-ok:`), and a `PLACEHOLDER` exclusion for pattern/glob
text. This PRD stays inside that file: it tightens `PRD_RE`/`MEM_RE` matching
and adds one new per-line skip condition (the evidence-fence skip below). No
new module, no new CLI flag, no change to `PATH_RE`, `resolve_path`,
`resolvable_numbers`, or the waiver/placeholder mechanisms. The second half of
the work — repairing or waiving the PRD findings the corrected checker still
reports — edits PRD bodies under `docs/dev/project-management/prds/`, which is
data, not code; it has no architecture of its own beyond "edit the cited
line."

## Module placement

- **Edit**: `skills/review-prd-backlog/scripts/check_links.py` — `scan_file()`
  gains the evidence-fence tracking and the three new skip conditions;
  `PRD_RE`'s pattern changes.
- **Edit**: `skills/review-prd-backlog/scripts/test_check_links.py` — new
  regression tests pairing each false-positive context with a genuine-link
  positive control (per the PRD's Phase 0 acceptance).
- **Edit** (PRD repair, Phase 1, data only, no script changes):
  - `docs/dev/project-management/prds/done/00118-historical-commit-types-preserve-history-v1.md`
    line 54 — stale lifecycle path.
  - Twelve `Source:`/provenance lines across ten `done/` PRDs citing
    link-ok: `~/.claude/dev/local/...` — waived, listed verbatim under Reuse inventory
    / Risks below with exact paths.
- **No edit**: `docs/dev/project-management/prds/backlog/00050-qwen-ivan-capability-eval-v1.md`
  — its five findings are a deliberate forward-reference eligibility gate,
  not rot (see Risks & edge cases).

## Interfaces & contracts

### `PRD_RE` — tightened word boundary

Current:
```python
PRD_RE = re.compile(r"(?<![\d/.-])(\d{5})-")
```
New:
```python
PRD_RE = re.compile(r"(?<![\w/.-])(\d{5})-")
```
`\w` already includes `\d`, so this subsumes the digit exclusion and adds
letters and `_`. Rationale: a 5-digit run immediately preceded by a hex
letter (`...a17278-82e1-...`, a `codex_thread_id` or dispatch-id UUID
fragment) is never a PRD citation; a genuine citation is always preceded by
whitespace, punctuation, a backtick, `/`, `(`, or line start. Measured
against the current corpus (244 baseline findings via
`check_links.py --root . --json`), this change alone removes only
UUID/hash-fragment matches — verified by diffing the full finding set before
and after; every genuine `NNNNN-` citation in the corpus is preceded by a
non-word character and keeps matching.

### `scan_file()` — self-quoted-diagnostic skip (new, PRD_RE only)

After a `PRD_RE` match, skip it when the text immediately following the
match is exactly the checker's own no-file suffix:
```python
PRD_SELF_QUOTE = " (no PRD/discovery file)"
...
for m in PRD_RE.finditer(line):
    if line[m.end():m.end() + len(PRD_SELF_QUOTE)] == PRD_SELF_QUOTE:
        continue
    if m.group(1) not in prds:
        findings.append(...)
```
Rationale: a document that quotes a prior `check_links.py` run's own finding
text verbatim (e.g. `meta/project-capsule.md` and PRD 00120's own Test
Strategy block quoting `00057- (no PRD/discovery file)`) re-triggers the same
finding on every subsequent scan. The suffix is the exact string
`scan_file()`'s own PRD-finding branch renders
(`f"{m.group(1)}- (no PRD/discovery file)"`), so this only matches literal
self-quotation, never a fresh citation — a fresh citation is never followed
by that exact parenthetical in the source prose.

### `scan_file()` — bracket-in-backtick skip (new, MEM_RE only)

After a `MEM_RE` match, skip it when it is a complete inline-code span: the
character immediately before the match is `` ` `` and the character
immediately after is `` ` ``.
```python
for m in MEM_RE.finditer(line):
    start, end = m.span()
    if start > 0 and end < len(line) and line[start - 1] == "`" and line[end] == "`":
        continue
    if m.group(1) not in memories:
        findings.append(...)
```
Rationale: every real memory link in the corpus's actual memory files is
written bare in prose — `See [[prd-phase-2-needs-a-human]] for ...` (no
backticks; confirmed by inspecting
`~/.claude/projects/<hash>/memory/*.md`). Every false-positive bracket match
in the corpus (`` `[[package]]` ``, `` `[[links]]` ``, `` `[[name]]` ``,
`` `[[ghost]]` ``, `` `[[link]]` ``) is prose *about* the memory-link or
TOML-array-of-tables syntax, always backtick-wrapped as an inline code span.
This is a syntactic distinction (is the whole `[[...]]` token one inline-code
span?), not a semantic guess, so it cannot swallow a bracket used elsewhere
(e.g. inside a fenced fenced code block spanning multiple lines — those are
covered by the evidence-fence skip below, independently, when applicable).

### `scan_file()` — "observed evidence" fence skip (new, both `PRD_RE` and `MEM_RE`, and `PATH_RE`)

**Two passes, not one, to avoid the open-ended-suppression trap.** A
single forward pass that sets `in_evidence_fence = True` on open and clears
it on close is unsafe: a truncated edit or malformed markdown that opens the
fence and never closes it would leave the flag `True` for the rest of the
file, silently skipping every remaining line's `PATH_RE`/`PRD_RE`/`MEM_RE`
matches — including genuine citations with nothing to do with the evidence
block. That is exactly the kind of silent weakened-detection the PRD
forbids, so the skip must be validated *closed* before it is trusted.

First pass over `lines` computes the set of skippable line-index ranges:
walk the file once, and only record a range `[open_idx, close_idx]` as
skippable when a matching closing ```` ``` ```` fence is found before EOF
and before the next `armed` trigger. An opened-but-never-closed fence is
NOT added to the skip set — those lines fall through to normal scanning
(the safe default) and the file's `errors` list gets one line naming the
unclosed fence, so the gap is loud, not silent, and the CLI's existing
scan-errors-are-exit-1 contract covers it with no new plumbing.

```python
def _evidence_fence_ranges(lines):
    """Return (skippable line-index set, errors) for 'observed evidence' fences."""
    skip_lines = set()
    errors = []
    armed_at = None
    fence_open_at = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if "Carry the observed evidence verbatim" in stripped:
            armed_at = i
            continue
        if stripped.startswith("```"):
            if fence_open_at is None and armed_at is not None:
                fence_open_at = i
                armed_at = None
            elif fence_open_at is not None:
                skip_lines.update(range(fence_open_at, i + 1))
                fence_open_at = None
    if fence_open_at is not None:
        errors.append(f"evidence fence opened at line {fence_open_at + 1} never closed")
    return skip_lines, errors
```
`scan_file()` calls this once per file before its existing per-line loop,
adds the returned errors to its own `errors` list, and skips a line
(`continue`, before the `WAIVER` check and all three regex passes). Index
arithmetic note: `_evidence_fence_ranges` is 0-indexed (`enumerate(lines)`,
matching `skip_lines`'s natural list-index semantics), while `scan_file`'s
own loop is 1-indexed (`enumerate(lines, 1)`, since `ln` is the reported
finding line number). The skip check inside `scan_file`'s loop is therefore
`if (ln - 1) in skip_lines: continue` — the `-1` converts the loop's
1-indexed `ln` back to the helper's 0-indexed line numbering before the
set lookup.

Rationale: `create-prd`'s Test Strategy convention
(`skills/create-prd/SKILL.md`'s template, followed by every PRD sampled here)
opens a fenced ```` ```text ```` block with the exact heading sentence "Carry
the observed evidence verbatim from the accepted packet:" and then quotes a
captured command transcript byte-for-byte. That transcript is historical
proof of an audit finding, not a live citation — it can legitimately contain
a `[[bracket]]`, an `NNNNN-` token, or a path that existed only at capture
time (e.g. link-ok: `00042-notes.log`, `99999-`, `./docs/.../sweep-shell-injection-2026-10-26.md`
in a dry-run log line). Scoping the skip to exactly this heading plus one
*validated-closed* fence (not "every fenced block", which would hide real
rot inside ordinary code examples, and not an unclosed fence, which would
hide everything after it) keeps the exclusion narrow and matches the PRD's
"diagnostic prefix" false-positive class at its structural root: these
blocks are, by the repo's own convention, diagnostic/evidence quotations.

Verified empirically: diffing findings before/after all three changes
removes exactly 45 findings (244 → 199), and every removed finding is one of
the three classes above (16 bracket-in-backtick, 14 UUID-fragment PRD-number
matches inside `codex_thread_id:` / dispatch-id tables, 15 evidence-fence
matches across 4 files). Zero genuine findings are removed — confirmed by
inspecting the full removed-finding diff, not just a sample.

## Data flow

Unchanged from the current script: `run()` walks
`docs/dev/project-management/**/*.md` plus the project memory dir, calling
`scan_file()` per file; `scan_file()` now calls `_evidence_fence_ranges(lines)`
once per file (a local, file-scoped pre-pass — no cross-file state) before
its existing per-line loop, and skips a line when its index is in the
returned set. The three regex passes (`PATH_RE`, `PRD_RE`, `MEM_RE`) and the
finding/error accumulation are otherwise untouched; `main()`'s JSON/text
rendering and exit code are untouched.

## Reuse inventory

- `WAIVER = "link-ok:"` (existing) — reused as-is for the PRD-repair phase's
  twelve historical-provenance lines (below); no new waiver syntax needed.
- `PLACEHOLDER` regex (existing) — not extended. link-ok: `/Users/you/` (one
  finding, `docs/dev/project-management/plans/skill-migration-bundle-plan.md:35`)
  and link-ok: the `/Users/bob/.codex/session` repeats (thirteen findings, all in
  `autopilot/reports/*.md`, correctly quoting a codex health-probe's own
  "missing" diagnostic) are genuine, accurately-detected, single-purpose
  historical/example text outside `prds/`; adding exclusions for them would
  be exactly the "broadly exclude" the PRD forbids for a one-or-few-instance
  case with no repeatable pattern. Left alone.
- Searches run (verb/noun synonyms per the reuse-sweep convention, using
  `~/.claude/rules-library/rationalizations.md`'s synonym sets): `rg
  -n "false.positive|false_positive" skills/review-prd-backlog`,
  `rg -n "waiver|exempt|ignore" skills/review-prd-backlog/scripts/check_links.py`,
  `rg -n "fence|code.?block" skills/*/scripts/*.py` — no existing
  fenced-block-aware scanner or backtick-span helper found anywhere in the
  repo; `check_links.py`'s own `WAIVER`/`PLACEHOLDER` are the only precedent,
  both reused rather than duplicated.

## Alternatives considered

1. **Smallest-diff option: waiver every false-positive line instead of
   fixing detection.** Add `link-ok:` to the ~45 affected lines (the four
   evidence-fence PRD files, the `~/.claude` provenance lines, the capsule's
   link-ok: historical "00057-"/"[[package]]" mentions, every `codex_thread_id:` table
   row, etc.). Rejected as the primary fix: it does not generalize — every
   *future* PRD/review that follows the same "Carry the observed evidence
   verbatim" convention, or cites a UUID next to a 5-digit run, or quotes
   `[[package]]` in prose, reintroduces the same noise, and the PRD's
   Problem statement is explicit that detection itself is wrong, not just
   under-waived. Used narrowly instead, in Phase 1, for the dozen
   non-repeating historical-provenance citations that have no structural
   signature to key a code fix on (see Risks).
2. **Broad: exclude `docs/dev/project-management/audit-results/**` and
   `docs/dev/project-management/reviews/**` from scanning.** Rejected — the
   PRD explicitly forbids this ("do not broadly exclude historical audit
   bundles... retain historical audit scanning"), and it would hide genuine
   rot that happens to live in a review file (there is no guarantee future
   rot won't).
3. **Chosen: three narrow, evidence-backed detection fixes** (word-boundary
   tightening, self-quote suffix skip, evidence-fence skip) **plus targeted
   per-line PRD repairs/waivers for what remains.** Each code fix is keyed to
   a concrete, repeating, structural signature observed in the actual corpus
   (not a guess), each is verified against the full 244-finding baseline to
   confirm zero genuine findings are lost, and the remaining non-repeating
   PRD-body cases are handled as content edits rather than new code paths.

## Risks & edge cases

- **00050's eligibility-gate citations are not rot.**
  `docs/dev/project-management/prds/backlog/00050-qwen-ivan-capability-eval-v1.md`
  cites `prds/done/00049-qwen-completion-status-v1.md` (frontmatter
  `eligibility:` line 6, and prose lines 6/113/156/208) and
  `audit-results/qwen-ivan-calibration/protocol.md`. Both are currently
  missing by design: PRD 00049 is still in `backlog/` (not `done/`), and
  `protocol.md` is an operator-authored calibration record that line
  116-119's own prose says must not exist before this PRD is picked
  (`eligibility:` reads it to decide whether 00050 may run at all — see
  `select()`'s eligibility gate in `cli/selection.py`). This is the one
  concrete example the accepted packet names, but on inspection it is a
  forward-reference premise gate, not an obsolete citation: "verify
  missing-target premises at execution time" (the PRD's own Requirement)
  means verifying *whether the premise still holds*, and here it does not —
  the citation is correct and must not be edited, repaired, or waived. Phase
  1's task premise check must record this disposition explicitly (skip,
  reason: eligibility gate not yet met) rather than silently passing over
  it.
- link-ok: **Twelve `~/.claude/dev/local/...` provenance citations in ten `done/`
  PRDs are real, permanent, and unrepairable.** Exact list (verified absent
  on disk at design time):
  - `prds/done/00017-malformed-memory-half-written-v1.md:134`
  - `prds/done/00003-add-plan-port-skill-v1.md:7`
  - `prds/done/00015-corrupt-queue-reads-as-drained-v1.md:101`
  - `prds/done/00006-nag-audit-cadence-in-brief-portfolio-v1.md:3,16,166`
  - `prds/done/00002-add-sweep-fix-skill-v1.md:3`
  - `prds/done/00009-walk-memory-proposal-queue-v1.md:3`
  - `prds/done/00004-add-capture-experiment-skill-v1.md:7`
  - `prds/done/00030-survey-prunes-skip-dirs-deep-v1.md:91`
  - `prds/done/00007-extract-memory-candidates-from-transcripts-v1.md:7`
  - `prds/done/00008-distil-memory-proposals-v1.md:8`

  Each is a `Source:` or parenthetical provenance line naming the original
  discovery/audit document in the **`~/.claude` project's own** (pre-split)
  `dev/local/` scratch tree — a different repo's ephemeral, intentionally
  non-durable directory (per that project's own `working-documents.md`
  convention, scratch under `dev/local`/`docs/dev/tmp` is not retained).
  There is no replacement target to resolve to (the content was never
  migrated, because it predates the migration these PRDs describe) and
  fabricating one is explicitly forbidden by this PRD's Requirements. Phase 1
  repairs these by adding `link-ok:` to each line (no change to the cited
  text — the historical record stays readable), not by rewriting or deleting
  the provenance.
- **One genuine, repairable lifecycle-path staleness**:
  `prds/done/00118-historical-commit-types-preserve-history-v1.md:54` still
  reads `**Location**:
  link-ok: docs/dev/project-management/prds/backlog/00118-historical-commit-types-preserve-history-v1.md`
  — written while the PRD was in `backlog/`, never updated across its
  `wip/` → `done/` moves. Phase 1 repairs this one word (`backlog` → `done`).
- **Next likely changes after this PRD**: (1) a future PRD following the
  same "Carry the observed evidence verbatim" convention will automatically
  get the fence skip — no action needed; (2) if `check_links.py` ever adds a
  fourth reference kind, it must independently decide whether the evidence
  fence applies to it (the skip is reference-kind-agnostic by construction,
  since it `continue`s before any regex pass runs); (3) the `~/.claude`
  provenance class only shrinks as more pre-split `done/` PRDs get similarly
  waived — there is no mechanism to prevent a new one from being authored
  with a dev/local citation, so a future audit may find more of the same
  shape and should apply the same waiver treatment, not a new code path.
- **What this design does not box in**: the fence-skip's `armed_at` flag
  survives across intervening lines (matching the convention's
  one-blank-line gap between the heading sentence and the fence), but is
  only ever trusted once a matching close is found before EOF or before the
  next `armed` trigger (see the two-pass validation above) — a PRD that
  quotes the heading sentence *without* a following fence, or opens one and
  never closes it, both fall through to normal scanning, which is the safe
  failure (no over-suppression either way).
- **The three skips are syntactic, not semantic, and each has a narrow,
  accepted false-negative edge** that this design does not attempt to close
  (closing it would require understanding intent, not just structure): a
  future doc that backtick-wraps a genuinely-dangling `` `[[retired-memory]]` ``
  for emphasis rather than to discuss syntax, writes a PRD number directly
  abutting a letter with no separator (`see00099-...`), or documents the
  checker's own diagnostic format verbatim rather than quoting a prior scan,
  would each be silently exempted with no waiver. All three are narrow
  literal-string/structural matches with no precedent in the current corpus
  (verified: none of these shapes exist in the 199 post-fix findings or
  anywhere else scanned); the existing `link-ok:`-adjacent mechanism has no
  symmetric "force-flag this" waiver, so a human who hits one of these edge
  cases reports it as a new false-negative rather than expecting the checker
  to catch it unaided.
- **This design overturns the PRD's own carried "Real rot example."** The
  accepted evidence packet (PRD 00120's Test Strategy section) names
  `00050`'s citations as the one concrete real-rot example. Re-verified at
  design time against `cli/eligibility.py`/`cli/selection.py` (the
  `eligibility:` frontmatter gate `select()` evaluates before a backlog PRD
  may run — inspected at the autopilot plugin version installed at design
  time, 0.10.0; plugin code is mutable/versioned across releases, per this
  project's own `session-pins-plugin-version` memory lesson, so re-verify
  against the running version rather than trusting this citation forever):
  PRD 00049 is still in `backlog/`, not `done/`, and
  `protocol.md` is deliberately unwritten, so the gate is still correctly
  closed, not stale. The PRD's own Requirements instruct re-verifying
  premises at execution time rather than trusting the historical count, so
  this design follows that instruction to its conclusion even though it
  contradicts the named example — Phase 1 must record this disposition
  explicitly (see above) rather than silently passing over it.
- **The 244-finding design-time baseline vs. the PRD's carried 228** is
  corpus drift, not a measurement error: ~16 extra PRDs/reviews/reports have
  landed in `docs/dev/project-management/` between the accepted packet's
  capture (2026-10-26) and this design (2026-10-29), each able to add its
  own `codex_thread_id:`/dispatch-table rows and bracket mentions. Phase 1
  re-runs the checker itself rather than trusting either number (per Test
  strategy outline below).

## Test strategy outline

Extend `test_check_links.py` with one test per false-positive class, each
paired with a genuine-link positive control in the same scan (so a
regression that over-widens the skip fails a positive-control assertion, not
just a negative one):

1. `test_backtick_wrapped_bracket_is_not_a_memory_link` — a line with
   `` `[[fake]]` `` (skipped) and a bare `[[ghost-memory]]` (still reported)
   in the same doc.
2. `test_prd_number_inside_uuid_is_not_a_citation` — a line containing
   link-ok: `01a17278-82e1-7811-975b-...` (skipped, no `17278-` finding) and
   genuine citations preceded by every separator the Contract names —
   whitespace (`00099-nope-v1.md`), a backtick (`` `00098-...` ``), `(`
   (`(00097-...)`), and line start (`00096-...`) — all still reported, in
   the same doc. **Correction from the dispatch-2 review's suggestion**:
   that review asked for an additional case, a PRD number directly
   abutting a letter with no separator that IS a real citation (e.g.
   `cite00099-nope-v1.md`) still reporting. Tess (test author) correctly
   refused to write that assertion — it contradicts Contract item 1 on its
   face: `\w` in the lookbehind excludes *any* digit run preceded by a
   letter, categorically, with no case where such a shape is "still a
   citation". There is no legitimate letter-abutted citation anywhere in
   the current corpus (verified at design time), so the Contract's
   boundary is correct and the dispatch-2 suggestion was unsatisfiable as
   stated; this is the accepted false-negative edge already named below
   under "The three skips are syntactic, not semantic". The test instead
   proves the actual guarantee: every separator shape the Contract claims
   as a citation boundary still works.
3. `test_self_quoted_no_prd_diagnostic_is_not_a_fresh_citation` — a line
   containing the literal `00057- (no PRD/discovery file)` (skipped) and a
   bare `00099-nope-v1.md` elsewhere in the doc (still reported).
4. `test_observed_evidence_fence_is_opaque` — a
   "Carry the observed evidence verbatim from the accepted packet:" heading
   followed by a ```` ```text ```` fence containing `[[package]]`, a
   link-ok: `99999-` token, and a dangling path, all skipped; the same three tokens
   repeated *after* the closing fence, in ordinary prose, still reported.
5. `test_evidence_fence_without_a_following_fence_is_not_armed` — the
   heading sentence with no fence afterward: the content after it is scanned
   normally (regression guard for the "safe failure" edge case above).
6. `test_unclosed_evidence_fence_falls_back_to_normal_scanning` — the
   heading sentence, an opening fence, a dangling-path line, and no closing
   fence before EOF: the dangling-path line IS still reported (fail-safe,
   not silently swallowed), and `errors` contains one line naming the
   unclosed fence (regression guard for the two-pass validation above —
   this is the blocking defect an adversarial review caught in a
   single-pass version of this design).

Run `uv run pytest skills/review-prd-backlog/scripts/test_check_links.py`
(Phase 0 acceptance) and, after Phase 0 lands, re-run
`check_links.py --root . --json` to regenerate the finding set Phase 1
executes against (its own premises must be re-verified at execution time,
per the PRD's Requirements, not assumed from this design-time count).

## Review log

- Dispatch 1 fixed the unclosed-evidence-fence blocker (single-pass →
  validated two-pass skip, with a scan-error on an unclosed fence and a new
  regression test) and documented the four non-blocking/question findings
  inline in Risks & edge cases (syntactic-skip false-negative edges,
  00050-overturns-accepted-example traceability, 244-vs-228 corpus drift).
dispatch 1 (claude): cardinal-sin 0, blocker 1, non-blocker 4, question 2
- Dispatch 2 (codex outage — the sandboxed codex session hung behind its own
  Fact-Forcing Gate hook across repeated tool-call retries and exited with
  no parseable findings; Claude fallback ran the identical review instead).
  No cardinal sins/blockers found; recorded a stronger true-positive
  assertion in test 2 of the Test strategy outline and pinned the
  `cli/selection.py` citation to the inspected plugin version (0.10.0) in
  Risks & edge cases. Dispatch 3 (conditional codex verification) does not
  run — dispatch 2 found zero cardinal sins/blockers.
dispatch 2 (claude-fallback): cardinal-sin 0, blocker 0, non-blocker 2, question 1

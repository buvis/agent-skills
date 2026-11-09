# Skill migration shipping review — 2026-11-09

Scope: PR #17, the seven imported skills and the Windows repairs. Reviewed
against the migration plan, the source file inventory, and the diff from master.
No merge or live SAP/Confluence write was performed.

## Verdict

Hold merge until the source owner confirms the seven skills' MIT licensing and
any required attribution. The migration plan explicitly requires this; the
previous PR description still called MIT an assumption. The bundle's handoff
references a NOTICE.md that is absent from the local bundle. No permission
confirmation was found in the PR comments or import commit message.

The review found and repaired technical omissions that green CI had missed.
The new commit also needs its own green CI run before merge.

## First pass: six questions

1. **Least confidence:** optional dependencies and generated artifacts. Default
   pytest skipped the MCP examples and two converter tests. Installing the
   documented MCP scaffold failed because Hatch could not locate its package.
2. **Assumptions:** checked the pinned SDK by running its real in-memory client,
   checked source file coverage, and checked the claimed license against the
   migration records. SDK calls passed; licensing was not established.
3. **Completeness:** all source skill files are present. The PR description was
   stale, and the validator follow-up reused an existing backlog number.
4. **Practical failures:** Confluence placeholder replacement consumed unrelated
   notes and intervening text; nested macros could leave malformed content;
   quotes/ampersands broke attachment XML; curl failures could report success.
5. **Different approach:** install a generated project, not just import example
   modules. Keep platform behavior covered on native Windows. Preserve the
   explicitly deferred validator consolidation rather than expand this import.
6. **Missing validation:** run optional dependencies in CI, and add generated
   project installation plus regressions for the concrete publishing failures.
   Live service and graphical rendering checks remain separate limitations.

## Slop lenses

- **Bloat:** the original diff adds about 8,200 lines for seven complete skills
  and portability repairs. The two 500-line ABAP validators are real duplication;
  consolidation is explicitly excluded by the migration plan and tracked below.
- **Impossible defenses:** inspected archive refusal, locking cleanup, and HTTP
  failures. These guards protect reachable states; no removal is justified.
- **Single-caller abstractions:** the MCP transport factory and test loaders
  provide an actual I/O boundary for a real SDK client; retain them.
- **Paraphrasing comments:** example section dividers and model descriptions aid
  navigation/schema generation. No additional blocking comment issue found.
- **Framework/mock confirmation:** removed a Windows-path mock that the archive
  validator no longer consulted. Keep native separator boundary assertions:
  actual Windows integration tests independently verify readable links.

## Doubt ledger

14 doubts: **9 fixed, 2 verified and dismissed, 3 known limitations**.

| ID | Outcome | Evidence or action |
|---|---|---|
| F1 | Fixed | Added Linux/Windows CI jobs with pinned optional SDK and conversion dependencies. |
| F2 | Fixed | Bound image replacement to a single leaf note; preserved preceding content and nested notes. Regression tests failed before the fix. |
| F3 | Fixed | XML-escaped attachment filenames; a parsed output round-trip preserves quotes and ampersands. |
| F4 | Fixed | Upload success now requires curl exit 0 and HTTP 2xx; use the platform null device. A nonzero curl exit with HTTP 200 is rejected. |
| F5 | Fixed | Four-backtick outer ADR template fence preserves its nested diagram fence. |
| F6 | Fixed | MCP template declares its package and dev dependency group and explicitly loads .env. A generated project now installs and passes its four tests. |
| F7 | Fixed | Moved the ABAP consolidation PRD to 00175, above the highest historical ID 00174, and refreshed PR status and limitations. |
| F8 | Fixed | Removed the unused ntpath mock from archive refusal tests; 64 tree-link tests still pass. |
| F9 | Fixed | Replaced a nonstandard authored home-path fixture with the repository's /Users/you convention; 64 note tests and 30 subtests pass. |
| V1 | Dismissed | Every file in the seven source directories exists in the imported skill tree. Targeted scans found no old SAP identifiers, token-shaped values, or non-generic home paths after F9. This is not a claim of exhaustive secret detection. |
| V2 | Dismissed | The preceding commit passed native Windows and Linux CI. Archive tests verify chains, escapes and refusal; locking cleanup and concurrent creation have tests. Windows' persistent lock file is intentional; dry-run promises no note write, not an empty filesystem. |
| K1 | Known, merge blocker | Source licensing/attribution needs the owner's answer. The agent cannot establish rights by choosing a repository license. |
| K2 | Known | Duplicated ABAP validators remain under PRD 00175. The migration plan explicitly forbids consolidating them in this change. |
| K3 | Known | No live SAP or Confluence validation, Mermaid/Chromium rendering, LibreOffice legacy .doc conversion, or generated explorer browser check. These require service access or graphical/tool fixtures not supplied for this migration. Network fixtures are authored, not captured service responses. |

## Second pass and validation

Reviewed the fixes for data preservation, native paths, fixture privacy, package
installation, development dependencies, .env loading, and historical PRD IDs.
The package-installation test exposed the scaffold omission and now guards it.
The numbering check included deleted historical PRDs, avoiding reuse of 00160.

- Optional integration suite: **29 passed, 7 subtests passed**, no skips.
- Targeted archive and note tests: **64 passed each**, plus 30 note subtests.
- Validators: all seven imported skills and both changed existing skills pass.
- Ruff lint/format and `git diff --check`: pass.
- Canonical checkout `uv run braid --check`: **0 drift**, 140 current, 20 ignored.
- Full suite: **4,384 passed, 12 skipped, 34 subtests passed**. Optional dependency
  coverage runs separately above; remaining skips retain their platform reasons.
- New remote CI results are recorded in the PR after completion.

## Privacy follow-up

At the user's request, expanded the content check to the seven skills' branch
history, including added examples and fixtures. No private person, client, or
system names were identified. Contact/address and URL extraction found no email
addresses or home paths in the imported skills' historical additions. Hosts were
limited to public SDK/tool documentation, the public weather API, and reserved
example domains. Person-like quoted phrases were roles, titles, public fonts,
or public place names. Reviewed custom ABAP identifiers were generic synthetic
examples, not supplied production identities.

Checked author/committer metadata without copying identities into this report:
the branch uses one identity, already present in master's recent history, and
introduces no additional identity. This check does not anonymize existing Git
metadata or establish source licensing. No private source bundle was committed.

This concludes the two-pass review. No claim of live-service validation or
license clearance is implied by passing automated tests.

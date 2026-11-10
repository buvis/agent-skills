---
prd: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md
review: 1
date: 2026-11-10
head_sha: ad05bc934f925e867e435d498097a78dca186dc1
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
---

# Review: 00135-historical-tag-awaits-green-ci-v1

Diff range: `1a2928a39a666ab0b42e92ebb7335eaf135ce9ba..ad05bc934f925e867e435d498097a78dca186dc1`

codex_rung_guard: not fired
provider_review_guard: satisfied
autocodex_alice_anthropic_receipt: docs/dev/project-management/autopilot/reports/00135-review-1-inputs/alice-anthropic-output.txt.receipt.json
autocodex_alice_openai_receipt: docs/dev/project-management/autopilot/reports/00135-review-1-inputs/alice-openai-output.txt.receipt.json
autocodex_blake_anthropic_receipt: docs/dev/project-management/autopilot/reports/00135-review-1-inputs/blake-anthropic-recovery-output.txt.receipt.json
autocodex_blake_openai_receipt: docs/dev/project-management/autopilot/reports/00135-review-1-inputs/blake-openai-retry-output.txt.receipt.json
autocodex_bob_anthropic_receipt: docs/dev/project-management/autopilot/reports/00135-review-1-inputs/bob-anthropic-output.txt.receipt.json
autocodex_bob_openai_receipt: docs/dev/project-management/autopilot/reports/00135-review-1-inputs/bob-openai-output.txt.receipt.json

The model-provider guard supersedes the legacy implementor guard. Eve did not run.
Implementation provenance is mixed (OpenAI gpt-6.1-sol tasks, Anthropic claude-fable-5-2 recovery publication), so both complete three-lens rosters reviewed the whole change; `review-route` returned `["anthropic", "openai"]`.
Carl: one-off dispatch guard refusal (exit 3, `refusing nested dispatch (already inside a CLI agent)`); no backend ran. Not latched.

## Recovery record

This cycle paused at `host_reviewer_evidence` and was completed in an interactive recovery session on 2026-11-10.

- Rejected, retained: the first Anthropic Blake receipt (`blake-anthropic-output.txt.receipt.json`, Kiro). Its raw log shows one executed shell call (`true`), against the read-only contract. It is not referenced above.
- Failed, retained: the Anthropic Blake retry on Kiro (`blake-anthropic-retry-output-1ead…jsonl`). Kiro stderr: `failed to set effort 'xhigh': model 'claude-opus-5.5' offers no effort levels`; the helper refused the effort mismatch (`missing=[]` meant the rubric was complete, not that review passed). The Kiro initialization-race hypothesis is unverified; no Kiro fix was made.
- Superseded, retained: the first OpenAI Blake output (could not use read tools); its retry is the receipt above.
- Recovery dispatch: the existing helper with `AUTOCODEX_ANTHROPIC_BACKENDS=copilot,claude`, prompt `blake-anthropic-recovery-prompt.md` (PRD, full B rubric, gate evidence; no diff, file list, plan, audit or sibling findings). Copilot served it: raw `model.call_start` events show `claude-opus-5.5` on every turn, `responsesReasoning` shows `initialEffort` and `effort` both `xhigh`, and the only tool calls are `view`, `glob` and `grep`. No permission denial occurred, so the launcher change evaded none. Copilot's tool allowlist (`view,glob,grep`) is narrower than Kiro's. Session `8dac16db-740e-4f9b-a9dd-41886f5429d4`.
- Revalidated before reuse: the five other receipts. Each matches the current implementation fingerprint, PRD and cycle, and its output, raw log and stderr hashes. Each has a complete rubric. No Kiro log other than the rejected one holds a shell call or a denial.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [6/6] | 🟠 | The PRD's publication record is stale. It still opens with "Phase 1 remains incomplete because final verification found a Latest conflict" (line 146) and ends with "Phase 1 still needs the build session's final read-only verification" (line 179). That verification has since passed and is recorded only in the build report: CI run 42819166960 on `3af575327b55`, v0.1.0 `isLatest=false`, v0.2.0 Latest as release 440124980, and a matching v0.1.0 body SHA-256. The PRD's Implementation section names this file as the place for the final publication evidence, and the exit criteria require the verified tag target, release URL and CI run/SHA there. Add a short final-verification paragraph and drop the "still needs" sentence. | docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:179 | 2 | ALICE_ANTHROPIC, ALICE_OPENAI, BLAKE_ANTHROPIC, BLAKE_OPENAI, BOB_ANTHROPIC, BOB_OPENAI |
| R2 | [3/6] | 🟠 | The v0.2.0 release was published under the operator waiver with no recorded safeguards. The record omits the v0.2.0 notes source, a notes review, the body hash, the tag target (local `f2b82d8…`), use of `--verify-tag`, and the asset, draft and prerelease state. The Risks section forbids publishing unreviewed additional scope. | docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:177 | 2 | ALICE_ANTHROPIC, BLAKE_ANTHROPIC, BOB_ANTHROPIC |
| R3 | [4/6] | 🟡 | The new autocodex-metrics rows put the absolute home path `/Users/<name>/...` into the `raw` field, and this repository is public. That breaks the AGENTS.md rule against personal paths and usernames. Earlier rows already do the same, so the autocodex recorder is the source and the fix belongs there. | docs/dev/project-management/autopilot/autocodex-metrics.jsonl:7 | general | ALICE_ANTHROPIC, ALICE_OPENAI, BOB_ANTHROPIC, BOB_OPENAI |
| R4 | [2/6] | 🟡 | The replay test that passes on the old code was weighed and is not tautological. The `newline="\n"` change is a Windows-only fixture fix: a CRLF line never matches the rg `$` anchor. It cannot fail on POSIX by design. Its only proof is the green Windows full-suite job in CI run 42819166960. Note that in the review record and do not count it as a regression pin. | skills/sweep-fix/scripts/test_sweep_main.py:727 | general | ALICE_ANTHROPIC, BOB_ANTHROPIC, mech-check |
| R5 | [2/6] | 🟡 | The README install step that backlog PRD 00159 prescribes has a YAML problem. `printf 'sources:\n  - ...\n' >> ~/.config/buvis/buvis-braid.yaml` appends a second top-level `sources:` key when the file already exists with one, and the result is duplicate-key YAML. Tell the step to add the entry under an existing `sources:` list, or to create the file only when it is absent. | docs/dev/project-management/prds/backlog/00159-retire-bundled-braid-v1.md:61 | general | ALICE_ANTHROPIC, BOB_OPENAI |
| R6 | [3/6] | ⚪ | The touched test file is about 1,004 lines, over the 800-line limit. The file was already too long before this PRD, and this diff added one line. Its own trailer records an earlier split. Record a split follow-up instead of fixing it in this PRD. | skills/sweep-fix/scripts/test_sweep_main.py:1003 | general | ALICE_ANTHROPIC, BOB_ANTHROPIC, BOB_OPENAI |
| R7 | [2/6] | ⚪ | Routing statements were left in place after the model-audit correction overrode them. The build report says `review-route` "requires Anthropic" (build.md:586) and tells review to "Route review on the recorded attempts" (build.md:348). The model audit still says the driver "returns Anthropic" (models.md:27) above its "Review preflight correction", which requires both provider rosters. Mark these lines as superseded or point them to the correction. | docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-build.md:586 | general | ALICE_ANTHROPIC, BOB_ANTHROPIC |
| R8 | [1/6] | 🟡 | Before the v0.2.0 action, the record does not say that CI was rechecked "immediately before", or that every job (including Windows) passed for run 42779216047. It only says "after green CI run". | docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:174 | Phase 1 | BLAKE_ANTHROPIC |
| R9 | [1/6] | 🟡 | The no-Latest rule (line 47) was broken publicly from 2026-11-10T00:11Z until the v0.2.0 release went out. During that time the published notes' statement about the release not being Latest was false. Phase 0 could have caught this: it found no releases, and GitHub makes the only release Latest even with `--latest=false`. The PRD's premise at line 134 never covered that case, and the cause is not recorded as a lesson. | docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:163 | Phase 0 | BLAKE_ANTHROPIC |
| R10 | [1/6] | 🟡 | Phase 0 is unticked even though publication went ahead on its results, so the record does not show that the step publication depended on was finished. | docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:97 | Phase 0 | BLAKE_ANTHROPIC |
| R11 | [1/6] | 🟡 | Nothing in the repo shows the required "already-correct tag/release" handling. The procedure was run by hand once, and that path never ran. | N/A | general | BLAKE_ANTHROPIC |
| R12 | [1/6] | 🟡 | The model audit's fourth evidence entry points at `00135-...-recovery-metadata.jsonl`. That file exists in the working tree but is absent from the review diff. The diff does include the staged intake note and the edited audit JSON, so the JSONL is untracked. On a clean checkout, `audited_review_providers` runs `(cwd / entry["path"]).read_bytes()` and raises FileNotFoundError, which breaks review routing. | docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-implementation-models.json:70 | 2 | BOB_ANTHROPIC |
| R13 | [1/6] | ⚪ | The prepared notes live in gitignored `docs/dev/tmp/` (see `.gitignore:5`), where purge tools can delete them. Only a SHA-256 stays in the record, and the published release body is the only lasting copy. | .gitignore:5 | Phase 0 | BLAKE_ANTHROPIC |
| R14 | [1/6] | ⚪ | The unrelated intake note 00176 appears in the review diff. The build report says a path-scoped stash keeps it out of this PRD's commits. Nobody has confirmed it is still uncommitted. | docs/dev/project-management/intake/new/00176-skills-adopt-repository-memory/idea.md | general | BOB_ANTHROPIC |
| R15 | [1/6] | ⚪ | The incremental review range includes master work unrelated to PRD 00135: create-note and explain-bim-system replaced by manage-bim, the PRD 00159 rework, the brush branch names, the distil-memory test helper, and the sweep fixture. It all arrived through the operator-recovery merge. Spot checks found no defects: no dangling references to create-note or explain-bim-system remain, and the triage matcher in the test helper matches the `json.dumps` encoding at funnel.py:216. | N/A | general | BOB_ANTHROPIC |
| R16 | [1/6] | ⚪ | `autopilot verify` cannot parse pytest's summary line. It exited 1 at baseline and 3 at closeout, and wrote no verification record either time. The gate counts come only from the raw logs. | N/A | general | BOB_ANTHROPIC |
| R17 | [1/6] | ⚪ | The Implementation section names `prds/backlog/` as the record's location, but the file is in `prds/wip/`. | docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:68 | general | BLAKE_ANTHROPIC |

## Consolidation notes

`consolidate_findings.py` ran over all six outputs. Its suffix-stripping merge folded six distinct Anthropic Blake findings into R1 because they cite the same PRD file. The coordinator split them back out model-side: Blake's v0.2.0-safeguards HIGH joins Alice's and Bob's v0.2.0-evidence findings as R2, and the rest stand alone (R8-R11, R13, R17). The script also could not parse Bob Anthropic's multi-line audit-prose finding; it joins Alice's routing-prose finding as R7. OpenAI Bob's size finding joins R6. The context file's one `[MECH]` replay line names the same test as R4, so R4 gains `mech-check`. No prior-cycle checks queue exists (cycle 1). No ledger existed before this cycle.

## Decision Gate

Cycle 1 of cap 2. Two HIGH findings remain unresolved, so the cycle does not converge. Rework is allowed (`1 < 2`).

- R1: fix. Verified: the PRD still reads "Phase 1 still needs the build session's final read-only verification" while the build report (lines 388-552) holds the passing final verification. Add the final-verification record to the PRD. Record only; no external action.
- R2: fix. Verified: the build report cites the v0.2.0 notes only at the ignored `docs/dev/tmp/00135-v0.2.0-release-notes.md` and records no body hash or byte comparison. Record in the PRD the v0.2.0 notes source, SHA-256, a read-only body comparison, the tag target, `--verify-tag`, and the draft, prerelease and asset state. Read-only checks only; do not re-publish, edit or delete any release or tag.
- R3: defer. The writer is the autocodex host driver outside this repository; this PRD cannot fix it. Report to the operator.
- R4: discard. A Windows-only CRLF fixture fix from merged master; it cannot fail on POSIX by design, and Windows CI run 42819166960 is green.
- R5: defer. The defect sits in backlog PRD 00159 text from merged master, outside PRD 00135's scope.
- R6: defer. Pre-existing file size; the diff touched one line.
- R7: discard. The audit and build report are append-only evidence; their correction sections already supersede the stale lines, and rewriting cited evidence would break line hashes.
- R8-R17: discard, single-voice Medium/Low. Also verified: R12 is factually refuted (the JSONL was committed in `2dc1968`); R14 is true (the intake note entered the range through loop commit `ad05bc9`), harmless and left in place.

## Verification

Staging gate (prior session, HEAD `ad05bc9`): 4330 passed, 12 skipped, exit 0 (`00135-review-1-inputs/gate-00135-c1-20261110.log`); the parser read no counts.

Recovery `autopilot verify --gate-command "uv run pytest" --cycle 1` at `2dc1968` (only autopilot reports changed since staging): exit 1, 4328 passed, 2 failed, 12 skipped; the parser again read no counts and wrote no record. Log: `00135-review-1-inputs/gate-recovery-2dc1968.log` (copied from the ignored `docs/dev/tmp/gate-2dc1968.log`). The two failures are the sweep-fix deadline tests `test_scan_kills_a_hung_search_and_its_grandchild_at_the_deadline_and_keeps_finished_hits` and `test_scan_kills_a_hung_ast_grep_search_and_its_grandchild_at_the_deadline`: under full-suite load the 1-second deadline also cut the fast repo. `uv run pytest skills/sweep-fix/scripts/test_sweep_scan.py` then passed 29 of 29. No code changed between the green and red runs, so this is a load-sensitive timing flake outside PRD 00135; it is reported to the operator, not hidden.

Bob Anthropic's VERIFY command was run by the coordinator instead of queued: `git log --oneline 1a2928a..HEAD -- <intake note>` prints `ad05bc9`, so the note is committed in the range (see R14).

## Alice

Both provider outputs follow, verbatim.

### Anthropic

Provider: Anthropic via Kiro. Model: claude-opus-5.5. Effort: xhigh. Session: sess_e3fc74b1-3e34-49f4-a6be-91dcb3f1472b.

[ALICE] 🟡 The PRD's publication record is stale. It still opens with "Phase 1 remains incomplete because final verification found a Latest conflict" (line 146) and ends with "Phase 1 still needs the build session's final read-only verification" (line 179). That verification has since passed and is recorded only in the build report: CI run 42819166960 on `3af575327b55`, v0.1.0 `isLatest=false`, v0.2.0 Latest as release 440124980, and a matching v0.1.0 body SHA-256. The PRD's Implementation section names this file as the place for the final publication evidence, and the exit criteria require the verified tag target, release URL and CI run/SHA there. Add a short final-verification paragraph and drop the "still needs" sentence. | File: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:179 | Task: 2
[ALICE] ⚪ Routing statements were left in place after the model-audit correction overrode them. The build report says `review-route` "requires Anthropic" (build.md:586) and tells review to "Route review on the recorded attempts" (build.md:348). The model audit still says the driver "returns Anthropic" (models.md:27) above its "Review preflight correction", which requires both provider rosters. Mark these lines as superseded or point them to the correction. | File: docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-build.md:586 | Task: general
[ALICE] ⚪ The v0.2.0 release published under the waiver has weaker evidence than v0.1.0. Its notes exist only in the ignored `docs/dev/tmp/00135-v0.2.0-release-notes.md`. No body hash or byte comparison was recorded for it, and the final verification compared only the v0.1.0 body. That leaves the text of a publication outside the PRD unreviewable from the repo. Embed the v0.2.0 notes or record their SHA-256 next to the waiver action. | File: docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-build.md:317 | Task: 2
[ALICE] ⚪ The new autocodex-metrics rows put the absolute home path `/Users/<name>/...` into the `raw` field, and this repository is public. That breaks the AGENTS.md rule against personal paths and usernames. Earlier rows already do the same, so the autocodex recorder is the source and the fix belongs there. | File: docs/dev/project-management/autopilot/autocodex-metrics.jsonl:7 | Task: general
[ALICE] ⚪ The replay test that passes on the old code was weighed and is not tautological. The `newline="\n"` change is a Windows-only fixture fix: a CRLF line never matches the rg `$` anchor. It cannot fail on POSIX by design. Its only proof is the green Windows full-suite job in CI run 42819166960. Note that in the review record and do not count it as a regression pin. | File: skills/sweep-fix/scripts/test_sweep_main.py:727 | Task: general
[ALICE] ⚪ The touched test file is about 1,004 lines, over the 800-line limit. The file was already too long before this PRD, and this diff added one line. Its own trailer records an earlier split. Record a split follow-up instead of fixing it in this PRD. | File: skills/sweep-fix/scripts/test_sweep_main.py:1003 | Task: general
[ALICE] ⚪ The README install step that backlog PRD 00159 prescribes has a YAML problem. `printf 'sources:\n  - ...\n' >> ~/.config/buvis/buvis-braid.yaml` appends a second top-level `sources:` key when the file already exists with one, and the result is duplicate-key YAML. Tell the step to add the entry under an existing `sources:` list, or to create the file only when it is absent. | File: docs/dev/project-management/prds/backlog/00159-retire-bundled-braid-v1.md:61 | Task: general

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: fail

### OpenAI

Provider: OpenAI via Codex. Model: gpt-6.1-sol. Effort: high (helper default). Thread: 01a1c6df-abba-7152-9e61-e140d4baa93d.

[ALICE] 🟡 New telemetry rows expose a personal absolute path in this public repository. Store `raw` as a repository-relative path, per AGENTS.md. | File: docs/dev/project-management/autopilot/autocodex-metrics.jsonl:7 | Task: general
[ALICE] ⚪ The PRD still states Phase 1 is incomplete and recovery is pending, although the build report records successful final verification. Append the final outcome and supersede those status statements. | File: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:146 | Task: 2

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: fail
R13: fail

## Blake

Both provider outputs follow, verbatim.

### Anthropic

Provider: Anthropic via Copilot (recovery dispatch). Model: claude-opus-5.5. Effort: xhigh. Session: 8dac16db-740e-4f9b-a9dd-41886f5429d4.

The repo contains only the PRD record for this work. I could not check the remote tag, the releases, or the v0.1.0 release notes with view, glob and grep, because the notes are in an ignored path I was told not to open.

What I could confirm in the repo:
- The local `v0.1.0` tag is a lightweight tag at `f4f2de0aa55b9c53a531b1b280a4339e74aebc64`.
- `.github/workflows/ci.yml` has eight jobs, matching the record, and none of them uses `continue-on-error`.
- `CHANGELOG.md:61` holds the `[0.1.0] - 2026-10-18` section that the record cites as the notes source.

[BLAKE] 🟠 Phase 1 acceptance is not shown as met. Both task checkboxes are unticked, and the record says Phase 1 still needs the final read-only check of the remote tag commit, the release body and the Latest state after the recovery. | File: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:179 | Task: Phase 1
[BLAKE] 🟠 The v0.2.0 release was published under the operator waiver with no recorded safeguards. The record omits the v0.2.0 notes source, a notes review, the body hash, the tag target (local `f2b82d8…`), use of `--verify-tag`, and the asset, draft and prerelease state. The Risks section forbids publishing unreviewed additional scope. | File: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:177 | Task: Phase 1
[BLAKE] 🟡 Before the v0.2.0 action, the record does not say that CI was rechecked "immediately before", or that every job (including Windows) passed for run 42779216047. It only says "after green CI run". | File: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:174 | Task: Phase 1
[BLAKE] 🟡 The no-Latest rule (line 47) was broken publicly from 2026-11-10T00:11Z until the v0.2.0 release went out. During that time the published notes' statement about the release not being Latest was false. Phase 0 could have caught this: it found no releases, and GitHub makes the only release Latest even with `--latest=false`. The PRD's premise at line 134 never covered that case, and the cause is not recorded as a lesson. | File: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:163 | Task: Phase 0
[BLAKE] 🟡 Phase 0 is unticked even though publication went ahead on its results, so the record does not show that the step publication depended on was finished. | File: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:97 | Task: Phase 0
[BLAKE] 🟡 Nothing in the repo shows the required "already-correct tag/release" handling. The procedure was run by hand once, and that path never ran. | File: N/A | Task: general
[BLAKE] ⚪ The prepared notes live in gitignored `docs/dev/tmp/` (see `.gitignore:5`), where purge tools can delete them. Only a SHA-256 stays in the record, and the published release body is the only lasting copy. | File: .gitignore:5 | Task: Phase 0
[BLAKE] ⚪ The Implementation section names `prds/backlog/` as the record's location, but the file is in `prds/wip/`. | File: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:68 | Task: general

B1: fail
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass

### OpenAI

Provider: OpenAI via Codex (retry with read-only shell inspection). Model: gpt-6.1-sol. Effort: high (helper default). Thread: 01a1c6e1-509d-7c90-82f5-2a0af12f67ee.

[BLAKE] 🟡 Final publication verification remains pending after recovery. Record confirmation of the remote tag target, matching release body, absent assets, and v0.2.0 Latest status before closing Phase 1. Local tag and notes checks cannot establish remote acceptance. | File: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:179 | Task: Phase 1

B1: fail
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Both provider outputs follow, verbatim.

### Anthropic

Provider: Anthropic via Kiro. Model: claude-opus-5.5. Effort: xhigh. Session: sess_19e3333a-cd4f-45df-b91b-392d1f85f652.

[BOB] 🟡 The PRD's publication record is out of date. It still says "Phase 1 remains incomplete" (line 146) and "Phase 1 still needs the build session's final read-only verification" (line 179). The final verification did run, at master `3af5753` with CI run 42819166960; it found v0.1.0 `isLatest=false` and v0.2.0 as Latest (id 440124980), and the notes' SHA matched. That evidence exists only in the build report. The PRD's own Implementation section says this file holds the final publication evidence. | File: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:179 | Task: 2
[BOB] 🟡 The model audit's fourth evidence entry points at `00135-...-recovery-metadata.jsonl`. That file exists in the working tree but is absent from the review diff. The diff does include the staged intake note and the edited audit JSON, so the JSONL is untracked. On a clean checkout, `audited_review_providers` runs `(cwd / entry["path"]).read_bytes()` and raises FileNotFoundError, which breaks review routing. | File: docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-implementation-models.json:70 | Task: 2
[BOB] 🟡 The v0.2.0 release notes, published to GitHub under the operator waiver, exist only in the ignored `docs/dev/tmp/00135-v0.2.0-release-notes.md`. Nothing records their exact text, a SHA-256, or a byte comparison against the REST body. v0.1.0 got all three. This is the one publication outside the PRD's original scope, and the PRD's Risks section forbids publishing unreviewed additional scope. As it stands, no reviewer can check what was published, and the text will disappear when docs/dev/tmp is purged. | File: docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-build.md:317 | Task: 2
[BOB] ⚪ The model audit prose contradicts itself:
- Line 3 says Tasks 1 and 2 ran in one worker session, but attempt 2 ran in a different session (`/root/verify_publication`).
- Lines 14-15 exclude read-only verification from implementation provenance, but lines 19-24 count attempt 2, a read-only verification, as an implementation attempt.
- Line 27 says review-route "returns Anthropic", but the appended correction section reverses that.

The stale text should be rewritten in place instead of left in with a correction appended below it. | File: docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-implementation-models.md:27 | Task: 2
[BOB] ⚪ The unrelated intake note 00176 appears in the review diff. The build report says a path-scoped stash keeps it out of this PRD's commits. Nobody has confirmed it is still uncommitted. | File: docs/dev/project-management/intake/new/00176-skills-adopt-repository-memory/idea.md | Task: general
[BOB] 🟡 [MECH] `test_empty_sweep_saves_control_verification_status_and_scan_details` passes against the pre-change code. The change is a Windows-only CRLF fixture fix (`newline="\n"`), which a macOS replay cannot tell apart from the old code. It came in with the master merge, not from PRD 00135. | File: skills/sweep-fix/scripts/test_sweep_main.py:728 | Task: general
[BOB] ⚪ The incremental review range includes master work unrelated to PRD 00135: create-note and explain-bim-system replaced by manage-bim, the PRD 00159 rework, the brush branch names, the distil-memory test helper, and the sweep fixture. It all arrived through the operator-recovery merge. Spot checks found no defects: no dangling references to create-note or explain-bim-system remain, and the triage matcher in the test helper matches the `json.dumps` encoding at funnel.py:216. | File: N/A | Task: general
[BOB] ⚪ The new lines in autocodex-metrics.jsonl carry personal absolute paths in their `raw` field (`/Users/<user>/...`). This repo is public. Every earlier line has the same pattern. | File: docs/dev/project-management/autopilot/autocodex-metrics.jsonl:7 | Task: general
[BOB] ⚪ test_sweep_main.py is about 1005 lines, over the 800-line limit. The size predates this diff, which touches one line of it. | File: skills/sweep-fix/scripts/test_sweep_main.py | Task: general
[BOB] ⚪ `autopilot verify` cannot parse pytest's summary line. It exited 1 at baseline and 3 at closeout, and wrote no verification record either time. The gate counts come only from the raw logs. | File: N/A | Task: general

R1: pass
R2: pass
R3: pass
R4: fail
R6: pass
R7: pass
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: fail

FIX:
- The PRD record still says Phase 1 is incomplete and lacks the final verification evidence — docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:179 — Replace both "incomplete" and "still needs" statements with a "Final verification — 2026-11-10" section. Record master `3af575327b5526c0fb45ab3f3e249faaabe5c26d`, CI run 42819166960 with all eight jobs green, v0.1.0 release 439793234 at `f4f2de0…` with `isLatest=false`, REST Latest = 440124980 (v0.2.0), and the matching notes SHA-256 `e8d19ba2…`.
- The model audit cites an untracked recovery-metadata JSONL — docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-implementation-models.json:70 — Stage `00135-historical-tag-awaits-green-ci-v1-recovery-metadata.jsonl` and commit it together with the updated audit JSON and MD.
- The published v0.2.0 notes are not kept or reviewable in the repo — docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-build.md:317 — In the recovery section, embed the exact notes text, its SHA-256, and a byte comparison against `gh api repos/buvis/agent-skills/releases/tags/v0.2.0 --jq .body`, as was done for v0.1.0.
- The model audit prose contradicts itself — docs/dev/project-management/autopilot/reports/00135-historical-tag-awaits-green-ci-v1-implementation-models.md:27 — Rewrite lines 3, 14-15 and 27 to match the current three-attempt, two-provider evidence, and fold the correction section into the body.

VERIFY:
- The intake note 00176 must stay out of this PRD's commits — Run `git log --oneline 1a2928a39a666ab0b42e92ebb7335eaf135ce9ba..HEAD -- docs/dev/project-management/intake/new/00176-skills-adopt-repository-memory/idea.md`. Expect empty output. Then confirm `git diff --cached --name-only` still lists the file.

KNOWN:
- The [MECH] fail-first pass on `test_empty_sweep_saves_control_verification_status_and_scan_details` — The fix only applies on Windows, where text-mode writes emit CRLF and break the rg `$` anchor. A macOS replay cannot show the failure; the Windows CI job is where it fails first, and run 42819166960 is green. The change came from merged master, not PRD 00135.
- Unrelated merged-master changes in the review range — They arrived through the operator-recovery merge, which keeps `work_start_sha` valid. `lane-check` already escalated the review to the full gate because of them. Each change belongs to its own work, not to this publication PRD.
- Personal absolute paths in autocodex-metrics.jsonl — The autocodex driver in the home repo writes the `raw` field, and every earlier line has it. The fix and the scrub of the existing lines belong to that tool, outside this PRD.
- test_sweep_main.py over 800 lines — The size predates this diff, which touches one line through the merged master work. Splitting the file is a refactor outside PRD 00135.
- The `autopilot verify` summary parser failure — The parser lives in the agent-plugins autopilot plugin, not in this repo. Report it to that plugin's owner. Here, the gate counts come from the raw pytest logs.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

### OpenAI

Provider: OpenAI via Codex. Model: gpt-6.1-sol. Effort: high (helper default). Thread: 01a1c6df-abba-7a03-a260-108c4a1c8619.

[BOB] 🟡 New telemetry exposes a personal absolute path, contrary to repository rules. | File: docs/dev/project-management/autopilot/autocodex-metrics.jsonl:7 | Task: general
[BOB] 🟡 Appending a complete `sources:` block can duplicate an existing YAML key and discard configured sources. | File: docs/dev/project-management/prds/backlog/00159-retire-bundled-braid-v1.md:61 | Task: general
[BOB] ⚪ The final publication record still says verification is pending, although the build report records successful verification. | File: docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:179 | Task: 2
[BOB] ⚪ Pre-existing size violations remain: the supplied mechanical facts identify a 57-line function in a file exceeding 800 lines. | File: skills/sweep-fix/scripts/test_sweep_main.py:945 | Task: general

FIX:
- Personal telemetry path — docs/dev/project-management/autopilot/autocodex-metrics.jsonl:7 — Replace new absolute paths with repository-relative paths.
- Duplicate YAML key — docs/dev/project-management/prds/backlog/00159-retire-bundled-braid-v1.md:61 — Specify adding the source to the existing list while preserving configuration.
- Stale publication status — docs/dev/project-management/prds/wip/00135-historical-tag-awaits-green-ci-v1.md:179 — Record final verification and link its evidence.

VERIFY:
- (none)

KNOWN:
- Existing size violations — skills/sweep-fix/scripts/test_sweep_main.py:945 — The unchanged function and existing file size are outside this publication task; the fixture adjustment does not introduce them.

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: fail
R13: fail
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

Verdict: 17 findings
Tests: 4328 passed, 2 failed, 12 skipped (suite run this cycle; recovery verify at 2dc19686f15e3d80aa15b84459e9637756b23160, deadline-timing flake, isolated rerun 29 passed; staging gate 4330 passed at ad05bc9)

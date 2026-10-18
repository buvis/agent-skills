# Decision Audit Log: 00088-document-the-eval-harness-contract-v1

PRD: `00088-document-the-eval-harness-contract-v1.md`
Started: 2026-10-18T20:18:18Z
Completed: 2026-10-18T20:18:18Z
Autonomous: 11  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-10-18T20:18:18Z

**Decision**: Cannot statically verify: the use-qwen skill validator passes and the full suite PASS/FAIL/SKIP counts (test gate reported exit 0 with counts unavailable)

**Choice**: routed to verification

**Rationale**: Queued as verification checks for the work phase step 7: uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen, and uv run pytest -q. Both already ran green independently in Alice and Blake review runs this cycle (3950 passed, 9 skipped, 0 failed; validator OK)

### [autonomous] 2026-10-18T20:18:18Z

**Decision**: Six actionable medium/low findings on the new drift test and runbook section 7 (substring flag matching, duplicated subparsers lookup, meaningless return annotation, bare StopIteration, inputs_sha256 doc inaccuracy, undocumented vet exit codes)

**Choice**: swept via tail sweep

**Rationale**: Cycle 1 converged with no CRITICAL or HIGH; the medium/low tail is swept by normal work tasks before finalize rather than dropped

### [autonomous] 2026-10-18T20:18:18Z

**Decision**: Codex doubt lens failed twice (off-target first run, lack-of-input refusal on retry because the aegis hook blocks cat in its read-only shell)

**Choice**: dispatched Claude fallback with Bob exact assembled doubt prompt

**Rationale**: The doubt lens must never silently drop; the fallback produced a full on-target review with FIX/VERIFY/KNOWN buckets and all five D-rule verdicts

### [autonomous] 2026-10-18T20:18:18Z

**Decision**: Carl first dispatch reviewed an unrelated skill despite reading the correct staged inputs

**Choice**: retried once, retry on-target

**Rationale**: Retry policy allows one retry; the retry produced usable output, so the ui lens is done rather than failed

### [autonomous] 2026-10-18T20:18:18Z

**Decision**: state.work_start_sha was absent at the review gate, leaving the review diff range undefined

**Choice**: set it to 0399860a004512973e2e19ed41cdc88c30572492, the parent of the first work commit 3f24b2f

**Rationale**: The build session never captured it. The parent of this PRD first work commit is the true PRD start, so work_start_sha..HEAD spans exactly this PRD work range; the empty-tree sentinel was not needed because HEAD resolves

### [autonomous] 2026-10-18T20:18:18Z

**Decision**: Subparsers-action lookup is duplicated inside the file: `_subparser` (skills/use-qwen/scripts/test_runbook_matches_harness.py:28) and `test_runbook_names_every_harness_subcommand` (skills/use-qwen/scripts/test_runbook_matches_harness.py:37) each re-run `next(action for action in parser._actions if action.choices is not None)`, and the two flag tests share an identical 5-line body. Simpler, behavior-preserving: add `_subparsers_action()` returning that action, call it from `_subparser` and from the subcommand test, and factor the flag loop into `_long_flags(subparser)` that yields every `--` option except `--help`; each test then reads `for flag in _long_flags(_subparser("vet")): assert flag in section, flag`.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T20:18:18Z

**Decision**: Flag drift test uses bare substring matching, so two run flags are masked by longer ones: `--shape` is a substring of the documented `--shapes` and `--bound` of `--gate-bound`. Delete `--bound SECONDS` or `--shape {description,tdd}` from § 7 and the test still passes, defeating the stated goal that the contract "cannot drift silently". The PRD prescribed this assertion literally, so it is a spec defect faithfully implemented; a word-boundary check (`rg`-style `--shape\b`) would close it

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T20:18:18Z

**Decision**: `_subparser(name: str) -> "object"` uses a quoted, meaningless return annotation; `argparse.ArgumentParser` is the actual type of a `choices` value and `argparse` is already importable here

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T20:18:18Z

**Decision**: § 7 says "`inputs_sha256` maps every sealed input ... to its digest", but `template/` - named one line above as part of the sealed set - is not a key of `inputs_sha256` (keys are `spec`, `pretask`, `canonical_patch`, `manifest`, `prompt:<shape>`, `dispatch_references`, `oracle`; `eval_harness/evidence.py:162`, `:180`), and `spec.json`, which is a key, is absent from the sealed-set sentence. An operator reading the next sentence ("Before any dispatch it refuses a task whose sealed inputs no longer match `inputs_sha256`") will believe an edited `template/` tree is caught pre-dispatch; `recheck_inputs` does not catch it (template drift is only caught later, per attempt, at `eval_harness/trees.py:213`). Wording came verbatim from the PRD

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T20:18:18Z

**Decision**: § 7 documents `run`'s three exit codes and `verify`'s two but not `vet`'s (0 when every task ends ready, 1 naming the failed check, `eval_harness/attempt.py:109`), and does not say that a failed check leaves `vetting.json` written with `ready: false` and no `ready` marker - the text reads as if the marker is always written

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T20:18:18Z

**Decision**: `_section_seven` anchors on the exact heading `## 7. Harness rounds`; renumbering or renaming the section raises a bare `StopIteration` instead of naming the missing anchor

**Choice**: auto-fixed

**Rationale**: fixed by review-close

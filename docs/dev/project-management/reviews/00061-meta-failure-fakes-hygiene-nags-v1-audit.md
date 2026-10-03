# Decision Audit Log: 00061-meta-failure-fakes-hygiene-nags-v1

PRD: `00061-meta-failure-fakes-hygiene-nags-v1.md`
Started: 2026-09-26T09:21:33Z
Completed: 2026-09-26T09:21:33Z
Autonomous: 2  |  Deferred: 1  |  Doubts: 0

### [autonomous] 2026-09-26T09:21:33Z

**Decision**: Cannot statically verify: [VERIFY] required checks pass; run `uv run pytest skills/brief-portfolio/scripts -q`, `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio`, and `braid --check` (Bob, 1/4, low)

**Choice**: discarded - already verified at the reviewed HEAD

**Rationale**: Bob raised it only because his codex sandbox cannot execute. All four checks are green at the reviewed HEAD 0b69947bd7c93d8b8788e978490a33066cff8079 per dev/local/autopilot/last-verification.json (uv run pytest -q exit 0, 3463 passed / 0 failed / 6 skipped; validate_skill.py skills/brief-portfolio exit 0; braid --check exit 0), and Alice and Carl each re-ran them live this cycle. No work follows.

### [autonomous] 2026-09-26T09:21:33Z

**Decision**: Cannot statically verify: [VERIFY] reproduce `demo/broken` with fresh brush and purge stamps, build the report, and confirm no brush or purge todo is derived (Bob, 1/4, low)

**Choice**: deferred to batch end - the named check needs a QA harness this repo does not contain

**Rationale**: The check cannot be run as named: `demo/broken` and the metadata-failing gh shim appear nowhere in the repo (rg over the whole tree finds no occurrence, while a collect_purge_devlocal control search over the same scope returns 3 files, so the pattern works). They were an ad-hoc rig in the 2026-09-05 agoge run that raised finding 9. Building two scratch repos plus a gh shim plus a full collect-and-derive run is net-new QA scaffolding for a low finding, and it duplicates the agoge product-QA lane the batch already runs after the drain. What the criterion asserts is pinned where it can be pinned cheaply: test_a_failed_metadata_call_still_collects_the_local_hygiene_stamps proves all four local keys are set when metadata fails, the fail-first replay proves that test fails against base, and Blake confirmed derive.js:267 and :325 read r.brush_last_run / r.purge_last_run straight off the record, so present keys cannot render as never. Deferred rather than discarded because the end-to-end reproduction genuinely was not executed, and that gap stays visible at batch end instead of being called verified.

### [deferred] 2026-09-26T09:21:33Z

**Decision**: PRD success criterion 2 (the report reproduction shows no brush or purge todo for demo/broken) was never executed end to end; the named check needs a demo/broken fixture and a metadata-failing gh shim, neither of which exists in this repo

**Choice**: deferred to batch end

**Rationale**: Running it as named would mean building net-new QA scaffolding (two scratch repos, a gh shim, a full collect-and-derive run) for a low finding, duplicating the agoge product-QA lane that raised the original finding 9. The mechanism is pinned by test_a_failed_metadata_call_still_collects_the_local_hygiene_stamps (fail-first proven against base) plus derive.js:267 and :325 reading the two keys directly, confirmed by Blake. Recorded so the unexecuted criterion stays visible rather than being reported as verified.

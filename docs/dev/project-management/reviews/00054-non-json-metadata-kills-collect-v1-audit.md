# Decision Audit Log: 00054-non-json-metadata-kills-collect-v1

PRD: `00054-non-json-metadata-kills-collect-v1.md`
Started: 2026-09-21T04:05:24Z
Completed: 2026-09-21T04:05:24Z
Autonomous: 5  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-21T04:05:24Z

**Decision**: F2 [MECH] test_collect_repo_records_meta_http_403_without_raising passes against the pre-change code (skills/brief-portfolio/scripts/test_collect_repo.py:154)

**Choice**: discarded (ledger)

**Rationale**: Review cycle 1: the PRD acceptance criterion mandates a 403 control that preserves the existing meta: behavior; a control passes on both sides by design and fails if RuntimeError leaves the tuple. Alice, Bob (KNOWN) and the shadow rubric R2 concur.

### [autonomous] 2026-09-21T04:05:24Z

**Decision**: F6 AttributeError catch is broader than the failure and the empty-body row reads meta: NoneType object has no attribute get (skills/brief-portfolio/scripts/collect.py:406)

**Choice**: discarded (ledger)

**Rationale**: Review cycle 1: settled by the PRD Solution section (symptom-at-one-site over normalising gh_json, PRD 00056 owns the collect_ci branch); the text is gh_json exception text this PRD forbids changing; nothing swallowed (errors entry + WARN). Bob filed it under KNOWN.

### [autonomous] 2026-09-21T04:05:24Z

**Decision**: F3 Cannot statically verify: uv run pytest skills/brief-portfolio/scripts -q reports 0 failing and the shim reproduction yields exit 0 with data.json written (N/A)

**Choice**: routed to verification

**Rationale**: Review cycle 1: queued in 00054-non-json-metadata-kills-collect-v1-checks-1.json as `uv run pytest skills/brief-portfolio/scripts -q`; the work phase step-7 pass of the Tail sweep runs it. The shim rerun half is not one project command and is not queued; Alice, Blake and Carl each ran the pytest command at HEAD this cycle (67 passed, 4 xfailed, 0 failed).

### [autonomous] 2026-09-21T04:05:24Z

**Decision**: F1/F5 fake_run closure duplicated across the three new tests and the two pre-existing meta-failure tests (skills/brief-portfolio/scripts/test_collect_repo.py:122); F4 the two new tests pin only the meta: prefix, not the exception text (test_collect_repo.py:135)

**Choice**: auto-fix (Tail sweep, one [D1] task)

**Rationale**: Review cycle 1 converged (no CRITICAL/HIGH); Low findings are swept, not dropped. F1 and F5 are one defect the consolidator kept apart (3/4 consensus read together). Bob filed the duplication under KNOWN (file convention, surgical scope), but the gate classification for Low is auto-fix and the shadow quality lane proposed a bounded behavior-preserving factory; tier sonnet (default_model floor).

### [autonomous] 2026-09-21T04:05:24Z

**Decision**: Step-7 full suite at a563e06 had one failure outside this PRD: skills/use-qwen/scripts/test_eval_evidence.py::test_resealing_replaces_the_sealed_set_wholesale (pretask head_sha differs between two seals that straddle a second under a slow 4-minute run); it passed on an isolated re-run at the same HEAD

**Choice**: noted, out of scope (pre-existing flaky test in use-qwen, not touched by PRD 00054)

**Rationale**: Review cycle 1 Tail sweep: the sweep changed only test_collect_repo.py (Pat: 3 CLOSURE resolved, NO FINDINGS); the flaky seal test needs a deterministic template sha or a frozen clock in its fixture, a use-qwen fix, so it is surfaced here for the batch report rather than patched inside this PRD.

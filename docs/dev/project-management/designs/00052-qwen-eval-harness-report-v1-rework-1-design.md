# 00052-qwen-eval-harness-report-v1 (rework cycle 1)

Source review: dev/local/reviews/00052-qwen-eval-harness-report-v1-review-1.md (head_sha 7b54ffc31894ed6050d6f590c0a93a48fd5c80ec)

## Architecture fit

Prior fix: none - there was no prior rework fix.

This rework closes the cycle-1 review's one 🔴 CRITICAL finding and its three
🟠 HIGH findings, all inside `skills/use-qwen/scripts/eval_harness/report.py`
and `skills/use-qwen/scripts/run_eval_harness.py` - the same two files task 2
landed. No new module or layer: every fix is a local edit to functions the
PRD's own Structural Decomposition already assigns to the `Report` module
(`eval_harness/report.py`: `render()`, `load_audit()`, `count()`). The
CRITICAL and one HIGH (F3) are both instances of the same root cause - input
that reaches `render()` (an `audit.jsonl` row, an `attempt.json` record) is
trusted after a shallow check (JSON-parses, key exists) instead of being
validated against its full contract - so this design closes them together in
one pass over the same two functions (`_load_audit`, `_load_entries`).

`git diff --stat 0fccf1ee0b9f863ce24904e861ba5c75c375d9e8..HEAD`: the PRD's
whole work range touches `CHANGELOG.md`, `skills/use-qwen/SKILL.md`,
`skills/use-qwen/references/eval-runbook.md`,
`skills/use-qwen/scripts/eval_harness/report.py` (new, 405 lines),
`skills/use-qwen/scripts/run_eval_harness.py`,
`skills/use-qwen/scripts/test_report.py` (new, 382 lines),
`skills/use-qwen/scripts/test_run_eval_harness.py`,
`skills/use-qwen/scripts/test_run_eval_harness_outcomes.py` (new, 475 lines).
This rework touches only `eval_harness/report.py`, `run_eval_harness.py` and
`test_report.py`.

## Module placement

All edits, no new files:

- `skills/use-qwen/scripts/eval_harness/report.py` - `_load_audit` becomes
  the public `load_audit`, gains full row validation (line-numbered
  refusals, a `_reject_json_constant` parse hook, a `_AUDIT_ROW_KEYS`
  constant, `import math`) and a `valid_ids` parameter; `_load_entries`
  wraps its `json.loads` to name the attempt directory and gains a
  `records.validate_record("attempt", ...)` call plus a directory-identity
  check; a new public `count()` function is extracted from
  `_counts_section`; `render()` opens with an `admission.check_run_id`
  guard (new `admission` import), is reordered so `valid_ids` is computed
  before `load_audit` is called, and calls the renamed/new functions.
- `skills/use-qwen/scripts/run_eval_harness.py` - the `render` subparser's
  `--run-id` argument gains `type=_run_id` (the same wrapper `run`'s
  `--run-id` already uses).
- `skills/use-qwen/scripts/test_report.py` - new tests per the Test strategy
  section below; existing `pytest.raises(Exception)` calls narrowed to
  `pytest.raises(ValueError)` (cycle-1 review's Medium tail, swept in the
  same pass since it touches the same three test functions this rework's
  own new tests sit beside).

## Interfaces & contracts

### Closes: [4/4] 🔴 render() silently accepts unknown-attempt_dir, non-VALID-attempt, missing-key, and invalid-verdict-value audit.jsonl rows (report.py:54)

`load_audit(run_dir: Path, valid_ids: list[str]) -> dict` - renamed from
`_load_audit`, now public (per the PRD's own `Report` module export list),
gains a required `valid_ids` parameter (the SAME ordered list `render()`
already builds today - NOT coerced to a `set` at the call site: `_report_md`
and `_audit_queue_md` both iterate `valid_ids` in order and Python's string
hashing is randomized per process, so replacing the list with a set anywhere
those two functions can see it would make `audit-queue.md`'s section order
non-deterministic across separate CLI invocations. `load_audit` builds its
own local `valid_id_set = set(valid_ids)` at its top, used only for the O(1)
membership test in step 5 below) and full per-row validation. Lines are
enumerated (`for lineno, line in enumerate(audit_path.read_text(encoding="utf-8").splitlines(), 1)`)
so every refusal names its source location: each message below opens with
`"audit.jsonl line %d: " % lineno` and closes with `%r` of the line's text,
so a reader finds the row by number or by content (the existing tests
assert substrings only, so the richer messages keep them green). Behavior,
in order, per non-blank line of `audit.jsonl`:

1. Parse JSON with `json.loads(line, parse_constant=_reject_json_constant)`, where `_reject_json_constant(name: str)` is a new module-level helper that always raises `ValueError("nonstandard JSON constant %s" % name)` - Python's `json` otherwise accepts the non-JSON tokens `NaN`, `Infinity` and `-Infinity` (dispatch 2, codex, confirmed by probe). Catch `ValueError` (which `json.JSONDecodeError` subclasses, so one clause covers both): `raise ValueError("audit.jsonl line %d: malformed JSON: %r" % (lineno, line)) from exc`. Same substring contract as today's `malformed audit.jsonl line` message (the existing test asserts only that the line's sentinel text appears).
2. Row-shape check: `isinstance(row, dict)` must hold (a syntactically-valid JSON line that isn't an object - e.g. `[1,2,3]` or `"oops"` - must not reach the key-set check below and crash with an unhandled `AttributeError`). Else: `raise ValueError("audit.jsonl line %d: not a JSON object: %r" % (lineno, line))`.
3. Key-set check: the row's keys must equal exactly `{"attempt_dir", "verdict", "claim", "evidence", "review_verdict", "review_findings", "review_effort_s"}`. Any missing or extra key: `raise ValueError("audit.jsonl line %d: missing/extra key (%s): %r" % (lineno, sorted(row.keys() ^ _AUDIT_ROW_KEYS), line))` where `_AUDIT_ROW_KEYS` is a new module-level frozenset constant in `report.py` (underscore-prefixed, matching the file's existing `_FAIL_CLASSES`/`_CLASS_FIELD`/`_OUT_FILE` naming convention) holding exactly those seven names.
4. `attempt_dir` type: `isinstance(row["attempt_dir"], str)` must hold (an unhashable value here, e.g. a list, would otherwise crash `in valid_id_set` below with an unhandled `TypeError`). Else: `raise ValueError("audit.jsonl line %d: non-string attempt_dir: %r" % (lineno, line))`.
5. `attempt_dir` membership: `row["attempt_dir"] in valid_id_set` must hold. Else: `raise ValueError("audit.jsonl line %d: audits unknown/non-VALID attempt %r: %r" % (lineno, row["attempt_dir"], line))`.
6. Duplicate `attempt_dir` check, still after the membership check, now naming the line as well as the id (today's message names only the id, which identifies neither duplicate line - dispatch 2): `raise ValueError("audit.jsonl line %d: duplicate attempt_dir %s: %r" % (lineno, aid, line))`. The existing duplicate test asserts only that the id appears, so it stays green.
7. `verdict` enum: must be one of `("clean", "flagged", "unverifiable")`. Else: `raise ValueError("audit.jsonl line %d: invalid verdict %r: %r" % (lineno, row["verdict"], line))`.
8. `review_verdict` enum: must be one of `("clean", "blocking", "unverifiable")`. Else: `raise ValueError("audit.jsonl line %d: invalid review_verdict %r: %r" % (lineno, row["review_verdict"], line))`.
9. `claim`/`evidence` type: both must be `str`. Else: `raise ValueError("audit.jsonl line %d: non-string claim/evidence: %r" % (lineno, line))`. Non-emptiness: when `verdict == "flagged"`, `claim` and `evidence` must both be non-empty. Else: `raise ValueError("audit.jsonl line %d: flags without a claim/evidence: %r" % (lineno, line))`.
10. `review_findings` type: must be a `list` where every element is `str`. Else: `raise ValueError("audit.jsonl line %d: non-string-list review_findings: %r" % (lineno, line))`. Non-emptiness: when `review_verdict == "blocking"`, `review_findings` must be non-empty. Else: `raise ValueError("audit.jsonl line %d: blocking with no review_findings: %r" % (lineno, line))`.
11. `review_effort_s` type: must be `None`, or an `int`/`float` that is `not isinstance(value, bool)`, `>= 0`, and - for a `float` only - `math.isfinite(value)` (use `is None` first, never truthiness, so `0`/`0.0` pass; exclude `bool` explicitly since `bool` is an `int` subclass in Python and `records.py`'s own `_is_int`/`_is_seconds` helpers already exclude it the same way; require finiteness because an overflowing literal such as `1e309` parses to `float("inf")`, which `>= 0` alone would accept - dispatch 2, codex, confirmed by probe; test finiteness only on floats because `math.isfinite` raises `OverflowError`, not `ValueError`, on an `int` of 2**1024 or more, and an `int` is always finite - dispatch 3; `import math` is new to `report.py`). Else: `raise ValueError("audit.jsonl line %d: invalid review_effort_s: %r" % (lineno, line))`.

**Function-size split (50-line cap):** `load_audit` keeps the file check, the `valid_id_set`, the enumerate loop, the blank-line skip, step 1, step 2, step 6 and the store/return; steps 3-5 and 7-11 live in a new module-private `_check_audit_row(lineno: int, line: str, row: dict, valid_id_set: set) -> str` that runs those checks in the order above and returns `row["attempt_dir"]` (the id step 6 then tests for duplicates). Same messages, same order; the split exists only so neither function reaches the cap this rework is fixing for `_counts_section` (dispatch 3).

All eleven checks run for every row before any row is trusted (matches the
PRD's own "Validate all input before replacing any rendered file" line for
this same function). `render()` computes `valid_ids` with its EXISTING,
UNCHANGED list-comprehension expression (`[entry["id"] for entry in entries
if entry["record"] is not None and records.derive_validity(entry["record"])
== "VALID"]` - already a list today, never a set) BEFORE calling
`load_audit` instead of after, reordering today's `entries → load_audit →
valid_ids` sequence to `entries → valid_ids → load_audit`. Only `load_audit`
itself builds a local `set(valid_ids)` for its own membership test; the
list `render()` passes around everywhere else is untouched.

### Closes: [4/4] 🟠 _counts_section is 53 lines / missing count()/load_audit() exports (report.py:236, :384)

`count(run: dict, engine_order: list[str], entries: list[dict], groups: dict, valid_ids: list[str], audit_rows: dict) -> dict` -
new public function, pure (no I/O, no string building). Extracts every
computation currently inline in `_counts_section` (report.py:296-348: the
per-engine attempts/PASS/FAIL/class tallies, `drops`, `scored`,
`not_started`, `f`) into a returned dict of this shape:

```python
{
    "engines": {
        "<engine_id>": {"not_started": bool, "attempts": int, "PASS": int, "FAIL": int,
                         "FAIL:<class>": int, ...,  # one key per _FAIL_CLASSES entry
                         "TIMEOUT": int, "SUSPECT": int, "DISCARDED": int, "INCOMPLETE": int}
        for engine_id in engine_order
    },
    "drops": int, "scored": int, "not_started": int,
    "f": int | None,          # None means "pending" - report.py renders the pending/audited text
    "f_audited": int, "f_total": int,   # k, n for the "pending (k of n audited)" text
}
```

`_counts_section` becomes a thin renderer: calls `count(...)`, then formats
its returned dict into the existing markdown line shapes (same text output,
byte-identical to today for every existing test). This brings
`_counts_section` under the 50-line function-size limit (R12/the Quality
checklist) since the arithmetic moves to `count()`.

`load_audit` (above) is the PRD's other named export; both `count()` and
`load_audit()` now exist as the PRD's Structural Decomposition specifies
("Exports: `render()`, `load_audit()`, `count()`").

### Closes: [2/4] 🟠 render's --run-id argparse argument has no format validator (run_eval_harness.py:53)

In `_parser()`, the `render` subparser's `--run-id` argument changes from:

```python
render.add_argument("--run-id", required=True)
```

to:

```python
render.add_argument("--run-id", type=_run_id, required=True)
```

`_run_id` is the existing module-level function in `run_eval_harness.py`
(already used by `run`'s own `--run-id`), which calls
`admission.check_run_id` and raises `argparse.ArgumentTypeError` on a
non-single-directory-name id (`..`, a path separator, etc.) - no new code,
reuse only.

The argparse check alone leaves the public `report.render()` open: a direct
call `render(Path("/evidence"), "/outside")` would write
`/outside/evidence.md`, `/outside/report.md` and `/outside/audit-queue.md`
(dispatch 2, codex, confirmed by a write-intercepted probe), breaking the
PRD's "never ... writes outside `runs/<run-id>/`". So `render()` ALSO
guards itself, as its first statement, before any path is built or read:

```python
problem = admission.check_run_id(run_id)
if problem is not None:
    raise ValueError("run id %r: %s" % (run_id, problem))
```

with `from eval_harness import admission, records` replacing today's
`from eval_harness import records` import line (`admission` imports
`engines`, `prompts`, `records` and never `report`, so no cycle).
`admission.check_run_id(run_id: str) -> str | None` returns the refusal
text for anything that is not exactly one directory name (`""`, `.`, `..`,
or any id containing `/`, `\` or NUL), else `None`. The argparse `type=_run_id`
stays so the CLI still refuses at parse time with argparse's own exit 2 and
usage text; the in-function guard is what the PRD's "never writes outside"
line needs for every caller.

### Closes: [1/4] 🟠 F3: Classification does not validate record schemas or directory identity (report.py:39)

In `_load_entries`, replace the bare `record = json.loads(record_path.read_text(encoding="utf-8"))` with a wrapped parse that names the file (today a truncated `attempt.json` surfaces as a bare `Expecting value: line 1 column 9` with no path - dispatch 2, codex, confirmed by probe), then, before the existing `records.classify(record)` rederivation check, add TWO checks: the existing general-purpose schema validator (wrapped to name the offending attempt directory), and a new directory-identity cross-check (the finding names both "record schemas" and "directory identity" as separate gaps; both need closing):

```python
try:
    record = json.loads(record_path.read_text(encoding="utf-8"))
except ValueError as exc:
    raise ValueError("attempt %s: malformed attempt.json: %s" % (child.name, exc)) from exc
try:
    records.validate_record("attempt", record)
except records.RecordError as exc:
    raise ValueError("attempt %s: %s" % (child.name, exc)) from exc
if (record["task"], record["engine"], record["attempt"]) != (int(task_str), engine, int(attempt_str)):
    raise ValueError(
        "attempt %s: record identity (task=%r, engine=%r, attempt=%r) does not "
        "match its directory name" % (child.name, record["task"], record["engine"], record["attempt"]))
```

`validate_record` runs before the identity check on purpose: it proves
`record` is a dict carrying `task`/`engine`/`attempt` (via `ATTEMPT_KEYS`),
so the identity comparison can index them without its own `KeyError` guard.

`records.validate_record` (`eval_harness/records.py:255`) is the existing
general-purpose record validator - it checks the record's key set against
`ATTEMPT_KEYS`, that every value is JSON-serializable, and runs the
kind-specific domain check (`records_domains.CHECKS["attempt"]`). It raises
`RecordError` (a `ValueError` subclass) whose message names only the
offending field, not the file - matching the sibling rederivation-mismatch
raise two lines below (which does include `child.name`), the wrapper above
adds the attempt directory name so a corrupt-record error is locatable among
potentially dozens of `attempt.json` files, closing the "schemas" half. The
identity check closes the "directory identity" half: `task_str`/`engine`/
`attempt_str` are already parsed from the directory name earlier in this
same function (report.py:34-35); comparing them against the record's own
`task`/`engine`/`attempt` fields catches a record whose stored identity
disagrees with the directory it lives in (e.g. a copy-paste error).

## Data flow

```
render(root, run_id)
  -> admission.check_run_id(run_id) -> raise ValueError on refusal  # NEW: guards direct callers, before any path is built
  -> run = json.loads(run.json)
  -> entries = _load_entries(run_dir, engine_order)
       for each attempt.json:
         try: record = json.loads(...)                        # NEW: decode error re-raised naming child.name
         except ValueError: raise ValueError("attempt <dir>: malformed attempt.json: ...")
         try: records.validate_record("attempt", record)     # NEW (F3, schema half)
         except RecordError: raise ValueError(named by child.name)
         if (task, engine, attempt) mismatch directory: raise  # NEW (F3, identity half)
         derived = records.classify(record); compare to stored  # unchanged
  -> valid_ids = [entry["id"] for entry in entries if VALID]  # UNCHANGED list, MOVED UP (was after load_audit)
  -> audit_rows = load_audit(run_dir, valid_ids)              # RENAMED + NEW: 11-step validation, every refusal names "line N" (own local set() for membership only)
  -> vetting_by_task = {...}                                   # unchanged
  -> groups = _group_by_task_engine(entries)                  # unchanged
  -> evidence_content = _evidence_md(...)                      # unchanged
  -> counts = count(run, engine_order, entries, groups, valid_ids, audit_rows)  # NEW
  -> report_content = _report_md(..., counts=counts)           # _counts_section now renders `counts`
  -> audit_queue_content = _audit_queue_md(...)                # unchanged
  -> write the three files                                     # unchanged
```

A refused `load_audit` (any of the eleven checks failing) raises before
`count()` or any file write runs, preserving the existing "validate all
input before replacing any rendered file" guarantee.

## Reuse inventory

- `admission.check_run_id` / `run_eval_harness.py`'s existing `_run_id` argparse type - reused verbatim for `render`'s `--run-id` (Interfaces item 3). Greps: `rg -n "def check_run_id" skills/use-qwen/scripts/eval_harness/` (found, `admission.py:20`); `rg -n "_run_id" skills/use-qwen/scripts/run_eval_harness.py` (found, already wired to `run`'s `--run-id`).
- `records.validate_record` - reused verbatim for F3's per-attempt schema check (Interfaces item 4). Grep: `rg -n "def validate_record" skills/use-qwen/scripts/eval_harness/records.py` (found, `records.py:255`).
- `evidence._check_attempt` (`eval_harness/evidence.py:327-341`, the `verify` subcommand's per-attempt check) already runs the same schema-then-identity pair. Not shared: `verify` notes every finding and continues, while `render` must raise on the first one, and `_check_attempt` writes into `verify`'s note list; `report._load_entries` re-implements the two comparisons inline (dispatch 3 confirmed the design's version is correct for every legal directory name).
- Audit-row schema/enum validation: nothing found, greps tried: `rg -n "verdict.*clean.*flagged" skills/use-qwen/scripts/eval_harness/`, `rg -n "AUDIT_KEYS|_KEYS = " skills/use-qwen/scripts/eval_harness/records.py` (only `attempt`/`run`/`pretask`/`sealed` kinds exist, no `audit` kind), `rg -n "def validate" skills/use-qwen/scripts/eval_harness/`. `audit.jsonl` is not one of PRD 00051's version-1 record contracts, so its validation is new code owned by `report.py` per the PRD's own module boundary (see Alternatives, Option B).

## Alternatives considered

1. **Validate audit rows inline inside `load_audit()`, matching the existing malformed-JSON/duplicate-id style already there (chosen).** Smallest diff that satisfies the PRD's Audit-queue Behavior line in full; keeps `report.py` as the sole owner of the audit-queue contract, per the PRD's own Structural Decomposition ("Report... reads records/audit rows").
2. **Extend `eval_harness/records.py`'s `_KEYS`/`validate_record` with a new `"audit"` kind.** Rejected: `audit.jsonl` is hand-written consumer input for the `render`/audit-queue feature, not one of PRD 00051's version-1 record contracts (`attempt`/`run`/`pretask`/`sealed`) that `records.py` owns. Coupling it there would blur the module boundary the PRD itself draws and would make `eval_harness/records.py` (shared by `vet`/`run`) depend on a schema only `render` consumes.
3. **Minimal validation: check only the `verdict`/`review_verdict` enums, skip the full key-set/type/membership checks (smallest possible diff).** Rejected: the PRD's Audit queue Behavior sentence is explicit and exhaustive - "duplicate attempt_dir, unknown/non-VALID attempt, missing/extra key, invalid value/type or malformed JSON" - a partial check would still leave the review's CRITICAL open against the very same PRD line it cites.

## Risks & edge cases

- `review_effort_s: 0` (or `0.0`) is a valid, non-null value and must not be rejected by a truthiness check - the design mandates `is None` first, then a numeric-range check, matching the PRD's "review_effort_s is nonnegative seconds or null."
- An audit row for a discarded/incomplete (non-VALID) attempt must now fail loudly where it previously rendered silently - this is a deliberate behavior change the CRITICAL finding requires; no caller in this repo currently relies on the old silent-accept behavior (the only consumer, PRD 00050, does not exist yet).
- Reordering `valid_ids` before `load_audit` must not change output for the no-`audit.jsonl`-file case: `load_audit` still returns `{}` immediately when the file is absent, before any row-level check runs, so an empty `valid_ids` set is passed but never consulted.
- Likely next changes: PRD 00050 will read the `f` count `count()` now returns as a plain int/None and apply its own pass/fail decision rule; a later PRD might want a `--lenient`/`--strict` audit mode - this design adds no such flag, keeping today's all-or-nothing refusal contract exactly as the PRD specifies, so that door stays open rather than being pre-decided here.

## Test strategy outline

New tests in `test_report.py`, each asserting `report.render()` raises
`ValueError` naming the offending line/attempt id and leaves all three
output files byte-identical to their pre-call state (matching the existing
`test_render_rejects_a_malformed_audit_line_naming_it_and_leaves_output_unchanged`
pattern):

- an audit row naming an attempt_dir not in `valid_ids` (never existed, and one that exists but is non-VALID)
- an audit row with `verdict: "maybe"` (the PRD's own stated Test Strategy error case)
- an audit row missing a required key, and one with an extra key
- an audit row with an invalid `review_verdict`
- a `flagged` row with an empty `claim`/`evidence`
- a `blocking` `review_verdict` row with empty `review_findings`
- an audit row with `review_effort_s: -1` (rejected) and one with `review_effort_s: 0` (accepted, not rejected as falsy)
- an audit row whose `review_effort_s` is the literal `Infinity`, and one whose value is `1e309` (both rejected; the first by the parse hook, the second by the finiteness check), each leaving all three output files byte-identical; and one whose value is a 400-digit integer literal (accepted as a finite nonnegative int, never an `OverflowError`)
- a duplicate-`attempt_dir` refusal whose message names the offending line number as well as the id
- a truncated `attempt.json` (e.g. `{"task":`) asserting `render()` raises `ValueError` naming the attempt directory, not a bare decode error
- direct `report.render(root, "/outside")` and `report.render(root, "..")` calls (bypassing argparse) asserting `ValueError` before any file is touched, with nothing written under `/outside` or beside `runs/`
- a `count()` unit test recomputing the same tallies independently from `_expected_by_engine`-style test-local arithmetic, asserting `count()`'s dict matches, decoupled from the markdown text `_counts_section` renders
- a `render` CLI test mirroring `run`'s own invalid-`--run-id` argparse-refusal pattern
- the existing three `pytest.raises(Exception)` calls (malformed-JSON, duplicate-attempt_dir, contradictory-outcome) narrowed to `pytest.raises(ValueError)` (this cycle's Medium tail, same test file)
- the existing `test_a_planned_engine_with_no_attempt_directory_is_not_started_and_not_an_attempt`'s `or`-hedge assertion tightened to pin one specific side (this cycle's Medium tail)
- an `attempt.json` with a field mistyped against `ATTEMPT_KEYS`, asserting `render()` raises naming the attempt directory (F3, schema half); an `attempt.json` whose `task`/`engine`/`attempt` fields disagree with its own directory name, asserting `render()` raises naming the mismatch (F3, identity half)

## Review log

dispatch 1 (claude): cardinal-sin 0, blocker 4, non-blocker 2, question 1

Non-blockers and questions (not fixed, logged per protocol):

- Non-blocker: `review_effort_s`'s numeric check should also exclude `bool` (a `bool` is an `int` subclass in Python, matching `records.py`'s own `_is_int`/`_is_seconds` exclusion) - already folded into the blocker-4 fix above since it touches the same line; no separate action needed.
- Non-blocker: `count()`'s per-engine schema should state explicitly that `_counts_section` branches on the `not_started` key first and discards the other keys for that engine, rather than leaving it implicit. Left as a documentation gap the implementor should close in code comments; not a design-correctness issue.
- Question: should `_AUDIT_ROW_KEYS`'s exact set (or any of the eleven validation steps) ever be relaxed for a future "lenient" audit mode? Not answered here - see Risks & edge cases' "likely next changes" note, which deliberately leaves this door open rather than pre-deciding it.

(The run that logged dispatch 1 was cut off before dispatch 2; this pass
resumed from the saved draft, same review file, same `head_sha`.)

dispatch 2 (codex): cardinal-sin 0, blocker 3, non-blocker 1, question 0

Blockers fixed in the sections above: (1) public `render()` bypassed the
run-id validation - `render()` now guards itself with
`admission.check_run_id` before any path is built; (2) `json.loads` accepts
`Infinity`/`NaN` and `1e309` overflows to `inf`, both passing `>= 0` -
step 1 gains a `parse_constant` hook and step 11 requires `math.isfinite`;
(3) the duplicate-row refusal named only the id and a truncated
`attempt.json` surfaced as a pathless decode error - every audit refusal
now opens with `audit.jsonl line N:` and `_load_entries` wraps its decode
to name the attempt directory.

Non-blockers and questions (not fixed, logged per protocol):

- Non-blocker: the Test strategy outline lists no refusal cases for steps 2, 4, 9, 10 and 11's type branches (non-object row, non-string `attempt_dir`, mistyped `claim`/`evidence`, non-list or mixed-type `review_findings`, boolean `review_effort_s`) nor acceptance cases for `null` and fractional `review_effort_s`. The implementor's tests-first pass (`/autopilot:work` step 2.7) writes one test per new behavior from the contract regardless; the outline is not exhaustive by design.

dispatch 3: codex unavailable, Claude fallback (codex exited 1: "You've hit your usage limit ... try again at Sep 21st, 2026 6:11 AM")
dispatch 3 (claude-fallback): cardinal-sin 0, blocker 0, non-blocker 3, question 1

The verifier confirmed all three dispatch-2 blocker fixes by execution
(parse hook rejects `NaN`/`Infinity`/`-Infinity`; `1e309` -> `inf` ->
`isfinite` False; `check_run_id("/outside")` and `("..")` both refuse;
`JSONDecodeError`, `UnicodeDecodeError` and `RecordError` all subclass
`ValueError`; no import cycle; existing `test_report.py` 25 passed; F3
changes no existing test's output because `attempt.py` validates and names
every record from the same plan values that name its directory).

Non-blockers and questions (logged per protocol; the first three were
ALSO applied to the sections above as one-line contract corrections
without a further dispatch, a deliberate deviation from "do not fix"
because `## Interfaces & contracts` is copied byte-for-byte into the fix
task and a known-wrong line there costs a review cycle):

- Question: "checked: all three dispatch-2 blocker fixes close their blockers as written" - recorded so the closure is known to be verified by execution, not by reading.
- Non-blocker (applied): `math.isfinite` raises `OverflowError`, not `ValueError`, on an `int` of 2**1024 or more, so the dispatch-2 fix would let a 309-4300-digit `review_effort_s` kill `render()` with an unhandled error - step 11 now tests finiteness on floats only.
- Non-blocker (applied): `load_audit` with eleven inline checks lands at or over the 50-line cap - the contract now names the `_check_audit_row` split.
- Non-blocker (applied): the Reuse inventory missed `evidence._check_attempt`, which already runs F3's schema-then-identity pair - cited, with why `render` does not share it.

result: ok

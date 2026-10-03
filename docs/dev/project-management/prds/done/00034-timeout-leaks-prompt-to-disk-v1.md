---
default_model: sonnet
rework_cap: 5
catchup: skip
design: skip
---

# A typing timeout writes the whole prompt into proposals.json

## Problem

`_type_proposal` in `skills/distil-memory/scripts/funnel.py:356-361` catches `(RuntimeError,
subprocess.TimeoutExpired, OSError)` together and persists `dedup_error=f"the typing call failed: {exc}"`. For
`subprocess.TimeoutExpired` that string is `Command '<argv>' timed out after <n> seconds`, and the whole prompt
is an argv element: `funnel.judge` passes it as the last element of `["claude", "--print", "--model", ...]`
(`funnel.py:178-184`, `timeout=120`). At the real call site the prompt is `dedup._PROMPT.format(proposal=…,
candidates=existing)` (`dedup.py:143`), where `existing` is the full text of up to `SHORTLIST_LIMIT = 5` memory
files (`dedup.py:19`). One timeout writes them verbatim into `proposals.json`, and `docket.py:187` carries the
string into the review queue, where the walkthrough prints it. Both siblings keep to the module's fixed-string
convention (`distil.py:101` returns "the model timed out before answering", `funnel.py:280` uses only
`exc.timeout`); this is the one site that missed, and no test covers it. Source: agoge run
`dev/local/audit-results/agoge-2026-08-31.md`, finding 29 (MEDIUM, security lane, status mocked: the `claude`
binary was a PATH stub, the exception object and the format string are the real ones); decision 2026-09-02:
branch on the exception type.

```
A sleeping stub let the real funnel.judge hit its real 120s timeout, and the
real funnel._type_proposal produced:
dedup_error: "the typing call failed: Command '['claude', '--print', '--model',
'sonnet', 'A distiller proposes this new memory:\n\nTRUDY_SECRET_MEMORY_BODY_MARKER\n']'
timed out after 120 seconds"
```

## Solution

Split the one `except` clause in two. `subprocess.TimeoutExpired` gets the fixed `f"the typing call timed out
after {exc.timeout}s"`, matching `funnel._run_triage`; `RuntimeError` and `OSError` keep `str(exc)`, because
`judge` raises `RuntimeError(proc.stderr)` and that stderr is the only useful diagnostic this handler can
reach. Then add the test the module is missing, mirroring `test_distil_discard.py`'s
`test_no_discard_reason_ever_embeds_the_slice_text` rule for `dedup_error`.

## Requirements

### Must have

- On `subprocess.TimeoutExpired`, `dedup_error` is exactly `the typing call timed out after 120s` for the
  shipped 120-second timeout, with no argv and no prompt text in it.
- `RuntimeError` and `OSError` keep `f"the typing call failed: {exc}"`, unchanged.
- A test in `skills/distil-memory/scripts/test_funnel_distil_dedup.py` fails if a typing timeout ever puts
  prompt or candidate text into `dedup_error`.
- That test's docstring names the `RuntimeError` branch as a known, unexamined boundary: it interpolates
  `claude`'s stderr, which was not probed here.

### Nice to have

- none

## Implementation

### Module: funnel
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: the five-stage pipeline, including typing each proposal against its own memory plane
- **Exports**: `_type_proposal()`

### Module: test_funnel_distil_dedup
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: the regression suite for the typing stage's `dedup_error` paths
- **Exports**: `test_no_dedup_error_ever_embeds_the_typing_prompt`

### Dependencies
- funnel: No dependencies (foundation)
- test_funnel_distil_dedup: Depends on [funnel]

## Tasks

### Phase 0: Foundation

- [ ] Branch on the exception type at `funnel.py:360-361` - Acceptance: `rg -n "the typing call timed out
  after" skills/distil-memory/scripts/funnel.py` matches one line inside `_type_proposal`, `rg -n "the typing
  call failed" skills/distil-memory/scripts/funnel.py` still matches exactly one line, and `rg -n
  "TimeoutExpired" skills/distil-memory/scripts/funnel.py` shows it in its own `except` clause.
- [ ] Add the no-prompt-in-`dedup_error` test - Acceptance: `uv run pytest
  skills/distil-memory/scripts/test_funnel_distil_dedup.py -q` passes with a new
  `test_no_dedup_error_ever_embeds_the_typing_prompt` that runs `funnel.main(["--distil"])` over
  `make_corpus(slice_texts=(_SLICE_ONE,))` with `FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}, classify=lambda
  prompt: _fail_with_timeout)`, where `_fail_with_timeout(cmd, **kwargs)` raises
  `subprocess.TimeoutExpired(cmd=cmd, timeout=120)`, and asserts the published record's `dedup_error == "the
  typing call timed out after 120s"` and that neither `_PROPOSAL_ONE` nor any shortlisted memory's body text
  appears in it.

### Phase 1: Core

No additional work; the Phase 0 tasks deliver this capability and its regression coverage.

## Success Criteria

- `uv run pytest skills/distil-memory/scripts -q` reports no failures.
- A typing timeout writes a fixed string naming only the timeout value into `dedup_error`, not one that grows
  with the prompt and up to five memory files.
- `rg -n "known boundary" skills/distil-memory/scripts/test_funnel_distil_dedup.py` matches the new test's
  docstring, so the unexamined `RuntimeError` stderr path stays on the record.

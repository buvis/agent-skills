---
default_model: opus
rework_cap: 5
---

# The brief's budget trimmer is quadratic in brief length

Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 42
(LOW, performance lane, verified; budget currently met). Decision 2026-09-02:
accepted — binary-search the cut point (operator's choice over
accept-and-record).

## Overview

### Problem Statement

`_trim_lines_to_budget` re-joins and re-encodes the entire remaining list
once per popped line: doubling layers multiplies bytes re-encoded ~3.8x —
quadratic. At 600 layers the trimmer touches 28.9 MB to emit a 5.1 KB brief.
The stated budget (`_BRIEF_BUDGET = 5120`) is met at every measured size, but
the tightest margin is 10 bytes, so any future line-length change brings the
cost into play sooner than the numbers suggest.

### Target Users

Latent — a survey run on a pathologically wide repo; the budget guarantee's
maintenance cost otherwise.

### Success Metrics

- Bytes re-encoded grows ~logarithmically with layer count on the
  instrumented corpus (no more ~3.8x-per-doubling).
- Output briefs are byte-identical to the current implementation at every
  test size (same cut point).
- `test_survey.py:214`'s budget assertion keeps passing.

## Functional Decomposition

Binary-search the largest prefix of lines whose encoded join fits
`_BRIEF_BUDGET`, replacing the pop-and-rejoin loop. Byte-identical output is
the correctness bar: the chosen cut must equal the old loop's.

## Structural Decomposition

- `skills/survey/scripts/run.py` (`_trim_lines_to_budget`, ~335)

## Implementation Phases

### Phase 0: The search

Implement, prove byte-identity against the old implementation on the
multi-size corpus, run `test_survey.py`. Sequence with PRDs 00030/00045
(same file).

## Test Strategy

Evidence from the report, verbatim:

```
60 layers -> 55 iterations, 347,993 bytes joined; 120 -> 137 / 1,320,608;
300 -> 452 / 7,550,336; 600 -> 1,052 / 28,974,386. Doubling layers
multiplies bytes re-encoded by 3.79x (60->120) and 3.84x (300->600).
Observed briefs: 1467 / 2720 / 5103 / 5101 / 5110 / 5110 bytes — under
budget at every size, tightest margin 10 bytes.
```

Regression: assert byte-identical briefs old-vs-new on the corpus before
deleting the old loop.

## Risks

More code and harder to read than the running-total alternative, for a saving
that is currently academic; a subtle mismatch in the search's boundary
condition silently changes where the brief is cut — the byte-identity check
exists for exactly that.

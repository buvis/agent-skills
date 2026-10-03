---
default_model: opus
rework_cap: 5
---

# Any collected title containing `<!--<script>` blanks the whole built page

## Problem

Both HTML builders inject their collected JSON into a `<script type="application/json">`
block and defend it with a single replacement, `</` to `<\/`
(`skills/brief-portfolio/scripts/build.py:46-48`,
`skills/debrief-meeting/scripts/build.py:136-140`). That stops a literal
`</script>` but not `<!--<script>`, which moves the HTML tokenizer into
script-data-double-escaped state, so the template's own closing tag stops
closing the block and everything after it, including `<div id="app">`, is
swallowed as script text. The page renders blank while the builder exits 0.
Third-party text reaches the payload verbatim from `gh issue list`,
`gh pr list` and `gh search prs`, and from any transcript line, so one unlucky
commit subject, issue title or spoken sentence kills the artifact. No script
execution is possible, because the `</` rule does hold against tag-closing, so
the proven consequence is loss of the artifact, not XSS. Source: agoge run
dev/local/audit-results/agoge-2026-08-31.md, finding 1 (HIGH, security lane);
decision 2026-09-02: accepted, escape for the script context.

```
Control (the defended vector, </script><img …>) mounted fine:
appDivPresent = true, imgTagsInDoc = 0.
Probe with the title `benign <!--<script> tail`, same file, exit 0 and no
warning from the builder: appDivPresent = false, payloadJsonParses = false ::
Unexpected non-whitespace character after JSON at position 417, h1 = null.
Reproduced through the meeting tool's real two-stage pipeline.
```

## Solution

Escape for the script context instead of the tag: after `json.dumps(...)`,
replace every `<` with its JSON unicode escape, written `"\\u003c"` in Python
source, and drop the `</` rule. That escape is legal JSON inside a string,
`JSON.parse` decodes it back to `<`, and the one rule kills `</script`, `<!--`
and `<script` together.
Each builder keeps one comment naming the tokenizer state the rule closes. The
brief-portfolio regression test already exists on master (merged in 636d94f)
as a strict xfail; the debrief builder has no such test, so this PRD adds the
mirror of it.

## Requirements

### Must have
- After the change, the text `build.py` substitutes for the template
  placeholder contains no `<` character in either builder.
- `JSON.parse` of the built payload still yields the same object: the escape is
  applied to the `json.dumps(...)` result only, never to the template.
- Each builder carries one comment line naming why every `<` is encoded.
- The strict-xfail marker on
  `skills/brief-portfolio/scripts/test_build_page.py::test_no_collected_text_can_reach_the_html_tokenizer`
  is deleted when the fix lands, and the second marker in that file (for
  `test_dir_without_out_writes_the_page_beside_its_own_inputs`, owned by PRD
  00013) stays untouched.
- `skills/debrief-meeting/scripts/test_debrief_build.py` gains the mirror
  regression test for the transcript path.

### Nice to have
- none

## Implementation

### Module: brief-portfolio builder
- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: inject `data.json`, `epics.json`, `history.jsonl` into `assets/template.html`
- **Exports**: `main()`

### Module: debrief-meeting builder
- **Location**: `skills/debrief-meeting/scripts/`
- **Responsibility**: inject `transcript.json` and `extract.json` into `assets/template.html`
- **Exports**: `main()`

### Module: brief-portfolio builder tests
- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: executable record of the injection defect (strict xfail today)
- **Exports**: `test_no_collected_text_can_reach_the_html_tokenizer`

### Module: debrief-meeting builder tests
- **Location**: `skills/debrief-meeting/scripts/`
- **Responsibility**: rules `build.py` must hold for the meeting payload
- **Exports**: `test_no_transcript_text_can_reach_the_html_tokenizer` (new)

### Dependencies
- brief-portfolio builder: No dependencies (foundation)
- debrief-meeting builder: No dependencies (foundation)
- brief-portfolio builder tests: Depends on [brief-portfolio builder]
- debrief-meeting builder tests: Depends on [debrief-meeting builder]

## Tasks

### Phase 0: Foundation

- [ ] In `skills/brief-portfolio/scripts/build.py`, replace `.replace("</", "<\\/")` on line 48 with `.replace("<", "\\u003c")`, rewrite the comment on line 46 to name the script-data-double-escaped state, and delete the `@pytest.mark.xfail` block above `test_no_collected_text_can_reach_the_html_tokenizer` in `skills/brief-portfolio/scripts/test_build_page.py`. Premise: that marker is still present, `rg -n "script-data-double-escaped" skills/brief-portfolio/scripts/test_build_page.py` prints line 44 before the edit; if it prints nothing, the fix already landed - skip and report - Acceptance: `uv run pytest skills/brief-portfolio/scripts/test_build_page.py::test_no_collected_text_can_reach_the_html_tokenizer -q` reports `1 passed` (not `xpassed`, not `failed`), and `rg -n "script-data-double-escaped" skills/brief-portfolio/scripts/test_build_page.py` prints no match while `rg -n "defaults off the home directory" skills/brief-portfolio/scripts/test_build_page.py` still prints its line.
- [ ] In `skills/debrief-meeting/scripts/build.py`, replace `.replace("</", "<\\/")` on line 140 with `.replace("<", "\\u003c")` and rewrite the comment on line 136 to name the same state - Acceptance: `uv run pytest skills/debrief-meeting/scripts/test_debrief_build.py -q` reports `8 passed` (the file holds 8 tests before this PRD adds one), and `rg -n 'replace\("<", "\\\\u003c"\)' skills/debrief-meeting/scripts/build.py` prints one line.
- [ ] Add `test_no_transcript_text_can_reach_the_html_tokenizer` to `skills/debrief-meeting/scripts/test_debrief_build.py`: build a workdir whose `transcript.json` holds one turn with the text `benign <!--<script> tail`, run `main()` through the existing `_run_main` helper, and assert the written page holds no `<` - Acceptance: `uv run pytest skills/debrief-meeting/scripts/test_debrief_build.py::test_no_transcript_text_can_reach_the_html_tokenizer -q` reports `1 passed`, and the same test fails with an `AssertionError` when `build.py` line 140 is reverted to `.replace("</", "<\\/")`.
- [ ] Re-run both builders' full suites so the escape change breaks no existing assertion, including the `_load_payload` helper in the debrief tests that un-escapes `<\/` - Acceptance: `uv run pytest skills/brief-portfolio/scripts/test_build_page.py -q` exits 0 with no `failed` and no `xpassed` in its summary line, and `uv run pytest skills/debrief-meeting/scripts/test_debrief_build.py -q` reports `9 passed`.

## Success Criteria

- A payload whose repo title or transcript turn contains `benign <!--<script> tail`
  builds a page that still holds `<div id="app">` and whose payload node
  round-trips through `JSON.parse`.
- The previously defended vector `</script><img …>` still cannot close the tag:
  every `<` in the payload is written as its `\\u003c` escape.
- `rg -n "xfail" skills/brief-portfolio/scripts/test_build_page.py` no longer
  names `test_no_collected_text_can_reach_the_html_tokenizer`.
- Both builders still exit 0 and print their `wrote <path> (<n> kB)` line on a
  normal build.

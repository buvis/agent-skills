---
default_model: opus
rework_cap: 5
---

# `build.py --dir <somewhere>` reads from there but overwrites the dashboard in `$HOME`

## Problem

In `skills/brief-portfolio/scripts/build.py`, `--dir` moves where the builder
reads its inputs (line 18), but `--out` defaults off the home directory rather
than off `args.dir` (line 19). A build from a scratch directory therefore
replaces the real portfolio brief at
`~/.local/share/agents/portfolio-brief/portfolio-brief.html`, with exit 0 and
no warning. It destroyed the operator's live dashboard during the agoge run;
that file was rebuilt from the operator's own cache, and the 2026-07-13
original is not byte-recoverable. The sibling skill gets it right:
`skills/debrief-meeting/scripts/build.py:113` defaults `--out` to
`<dir>/debrief.html`. `--dir` appears nowhere in `skills/brief-portfolio/SKILL.md`,
and the module docstring on line 4 says "defaults under
`~/.local/share/agents/portfolio-brief/`", which hides the decoupling instead of
naming it. Source: agoge run dev/local/audit-results/agoge-2026-08-31.md,
finding 3 (HIGH, journey lane); decision 2026-09-02: accepted, default `--out`
off `--dir`.

```
Inputs came from scratch (the epics.json warning names the scratch path),
output went home:
WARN: /…/T/agoge-walter/j4/epics.json not found
then: wrote /Users/bob/.local/share/agents/portfolio-brief/portfolio-brief.html (345 kB)
The operator's real 691295-byte file was replaced. The sibling skill prints
`--out OUT   output html (default: <dir>/debrief.html)`.
```

## Solution

Give `--out` no default and derive it from the working directory:
`ap.add_argument("--out", default=None)`, then
`out = Path(args.out) if args.out else workdir / "portfolio-brief.html"`. With
no flags, `--dir` is still the home directory, so the no-flag path keeps
writing the same file it writes today. Update the module docstring to state the
derived default, and document both flags in `SKILL.md` step 3 while the file is
open. The strict-xfail regression test already exists on master (merged in
636d94f); the fix turns it green and the marker goes.

## Requirements

### Must have
- `build.py --dir <scratch>` writes `<scratch>/portfolio-brief.html` and creates
  or touches nothing under `$HOME`.
- `build.py` with no flags still writes
  `~/.local/share/agents/portfolio-brief/portfolio-brief.html`.
- An explicit `--out` still wins over the derived default, for any `--dir`.
- The module docstring on line 4 names the derived default rather than "defaults
  under `~/.local/share/agents/portfolio-brief/`".
- `skills/brief-portfolio/SKILL.md` step 3 names `--dir` and `--out` and their
  defaults.
- The strict-xfail marker on
  `test_dir_without_out_writes_the_page_beside_its_own_inputs` is deleted; the
  other marker in that file (owned by PRD 00011) stays untouched.

### Nice to have
- none

## Implementation

### Module: brief-portfolio builder
- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: read `data.json` from `--dir` and write the built page
- **Exports**: `main()`

### Module: brief-portfolio builder tests
- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: executable record of the output-placement defect (strict xfail today)
- **Exports**: `test_dir_without_out_writes_the_page_beside_its_own_inputs`, `test_no_flags_writes_the_home_default` (new)

### Module: brief-portfolio skill doc
- **Location**: `skills/brief-portfolio/`
- **Responsibility**: the operator-facing workflow, step 3 "Build and open"
- **Exports**: no code, the build step's documented flags

### Dependencies
- brief-portfolio builder: No dependencies (foundation)
- brief-portfolio builder tests: Depends on [brief-portfolio builder]
- brief-portfolio skill doc: Depends on [brief-portfolio builder]

## Tasks

### Phase 0: Foundation

- [ ] In `skills/brief-portfolio/scripts/build.py`, change line 19 to `ap.add_argument("--out", default=None)`, derive `out = Path(args.out) if args.out else workdir / "portfolio-brief.html"` at line 49, and rewrite the `Usage:` docstring line 4 to name `<dir>/portfolio-brief.html` as the `--out` default. Then delete the `@pytest.mark.xfail` block above `test_dir_without_out_writes_the_page_beside_its_own_inputs` in `skills/brief-portfolio/scripts/test_build_page.py`. Premise: that marker is still present, `rg -n "defaults off the home directory" skills/brief-portfolio/scripts/test_build_page.py` prints line 62 before the edit; if it prints nothing, the fix already landed - skip and report - Acceptance: `uv run pytest skills/brief-portfolio/scripts/test_build_page.py::test_dir_without_out_writes_the_page_beside_its_own_inputs -q` reports `1 passed` (not `xpassed`, not `failed`), and `rg -n "defaults off the home directory" skills/brief-portfolio/scripts/test_build_page.py` prints no match.
- [ ] Add `test_no_flags_writes_the_home_default` to `skills/brief-portfolio/scripts/test_build_page.py`: monkeypatch `Path.home` to a `tmp_path` home, write `data.json` under `<home>/.local/share/agents/portfolio-brief/`, run `main()` with `argv = ["build.py"]` - Acceptance: `uv run pytest skills/brief-portfolio/scripts/test_build_page.py::test_no_flags_writes_the_home_default -q` reports `1 passed`, and the test asserts `(home / ".local/share/agents/portfolio-brief/portfolio-brief.html").is_file()`.
- [ ] Document the two flags in `skills/brief-portfolio/SKILL.md` step 3 ("Build and open"): `--dir DIR` (where `data.json`, `epics.json`, `data-prev.json` and `history.jsonl` are read, default `~/.local/share/agents/portfolio-brief`) and `--out FILE` (default `<dir>/portfolio-brief.html`) - Acceptance: `rg -n -- "--dir DIR" skills/brief-portfolio/SKILL.md` prints one line, and `rg -n -- "<dir>/portfolio-brief.html" skills/brief-portfolio/SKILL.md` prints one line.
- [ ] Re-run the builder suite so the new default breaks no existing assertion - Acceptance: `uv run pytest skills/brief-portfolio/scripts/test_build_page.py -q` exits 0 with no `failed` and no `xpassed` in its summary line, and `uv run pytest skills/brief-portfolio/scripts/test_collect.py -q` exits 0.

## Success Criteria

- With `--dir <scratch>` and no `--out`, the page lands at
  `<scratch>/portfolio-brief.html` and no file appears at
  `<home>/.local/share/agents/portfolio-brief/portfolio-brief.html`.
- With no flags, the written path printed by the builder is still
  `~/.local/share/agents/portfolio-brief/portfolio-brief.html`.
- `rg -n "xfail" skills/brief-portfolio/scripts/test_build_page.py` no longer
  names `test_dir_without_out_writes_the_page_beside_its_own_inputs`.
- Human follow-up: no wrapper in this repo passes `--dir` while relying on the
  home output, but the change is silent for any caller outside it, so the
  operator should be told once when it ships.

---
default_model: sonnet
rework_cap: 5
catchup: skip
design: skip
---

# create-skill's scripts answer `--help` and print the union path

## Problem

Two command-line defects in the same script pair. `validate_skill.py`'s `main()` (line 363) checks
`len(sys.argv) != 2` and then treats `sys.argv[1]` as a path, so `validate_skill.py --help` prints
`[ERROR] Path not found: <repo>/--help` and exits 1 with no usage text, while its sibling
`init_skill.py` uses argparse (line 116) and answers correctly. Separately `init_skill.py:111`
prints `3. Validate: ~/.claude/skills/create-skill/scripts/validate_skill.py <dir>` while
`skills/create-skill/SKILL.md:220` documents the
`python3 ~/.agents/skills/create-skill/scripts/validate_skill.py <path>` form; README.md:7-9 makes
`~/.agents/skills` the generated discovery view every host reads, while `~/.claude/skills` is a
Claude-only projection that `braid --no-claude` (src/agent_skills_braid/cli.py:419) never creates.
Source: agoge run dev/local/audit-results/agoge-2026-08-31.md, finding 31 (LOW, journey lane) and
finding 32 (LOW, journey lane); decision 2026-09-02: move to argparse, and print the union path
form.

```
validate_skill.py --help -> [ERROR] Path not found:
<repo-root>/--help, exit 1 (literal failed-probe output, not an input path).
Its sibling init_skill.py uses argparse and answers --help correctly.
Scaffolding printed 3. Validate:
~/.claude/skills/create-skill/scripts/validate_skill.py /.../walter-probe;
SKILL.md:220 documents the ~/.agents/skills/... form. Both ran here.
```

## Solution

Replace `validate_skill.main()`'s argv-length check with an `argparse.ArgumentParser` carrying one
positional `skill_path`, mirroring `init_skill.main()`. The `exists` and `is_dir` checks below it
and every exit code on the success path stay as they are. Then change the single f-string on
`init_skill.py:111` to the interpreter-prefixed union form so it matches `SKILL.md:220`. Each
change ships with a test in `skills/create-skill/scripts/`.

## Requirements

### Must have
- `validate_skill.py --help` and `-h` print usage and exit 0.
- `validate_skill.py <skill dir>` behaves as today, so the CI loop at
  `.github/workflows/ci.yml:74-80` keeps exiting 0 for every skill.
- `validate_skill.py` with no argument exits non-zero with argparse's own required-argument message.
- `init_skill.py`'s step 3 reads
  `3. Validate: python3 ~/.agents/skills/create-skill/scripts/validate_skill.py <skill_dir>`.
- Both changes carry a test under `skills/create-skill/scripts/`.

### Nice to have
- none

## Implementation

### Module: validate_skill.py
- **Location**: `skills/create-skill/scripts/`
- **Responsibility**: validates one skill directory and reports errors and warnings
- **Exports**: `main()`

### Module: init_skill.py
- **Location**: `skills/create-skill/scripts/`
- **Responsibility**: scaffolds a skill directory and prints the next steps
- **Exports**: `init_skill()`

### Module: test_validate_skill.py
- **Location**: `skills/create-skill/scripts/`
- **Responsibility**: tests for the validator
- **Exports**: `test_help_flag_prints_usage_and_exits_zero()`

### Module: test_init_skill.py
- **Location**: `skills/create-skill/scripts/`
- **Responsibility**: tests for the scaffolder's printed output (new file)
- **Exports**: `test_printed_validate_step_names_the_union_path()`

### Dependencies
- validate_skill.py: No dependencies (foundation)
- init_skill.py: No dependencies (foundation)
- test_validate_skill.py: Depends on [validate_skill.py]
- test_init_skill.py: Depends on [init_skill.py]

## Tasks

### Phase 0: Foundation

- [ ] Replace the `len(sys.argv) != 2` check in `validate_skill.main()` with an `argparse.ArgumentParser` taking one positional `skill_path`, keeping the `exists`/`is_dir` checks and every exit code below it - Acceptance: `python3 skills/create-skill/scripts/validate_skill.py --help` exits 0 with a first stdout line starting `usage: validate_skill.py`; `python3 skills/create-skill/scripts/validate_skill.py skills/survey` exits 0 and prints `[OK] Skill is valid!`; `python3 skills/create-skill/scripts/validate_skill.py` exits 2.
- [ ] Add `test_help_flag_prints_usage_and_exits_zero` to `skills/create-skill/scripts/test_validate_skill.py`, running `subprocess.run([sys.executable, str(Path(__file__).parent / "validate_skill.py"), "--help"], capture_output=True, text=True)` - Acceptance: the test asserts `result.returncode == 0` and `result.stdout.startswith("usage: validate_skill.py")`; `uv run pytest "skills/create-skill/scripts/test_validate_skill.py::test_help_flag_prints_usage_and_exits_zero" -q` passes.
- [ ] Change the printed validation step in `init_skill.py` to `print(f"3. Validate: python3 ~/.agents/skills/create-skill/scripts/validate_skill.py {skill_dir}")`; re-read the statement and skip its replacement if already correct - Acceptance: the captured `3. Validate:` line contains the interpreter-prefixed union path and the generated skill directory, with no Claude-only path in that line. Existing compatibility examples and validator fixtures are preserved.
- [ ] Add `skills/create-skill/scripts/test_init_skill.py` with `test_printed_validate_step_names_the_union_path`, importing `init_skill` the way `test_validate_skill.py` imports `validate_skill` (`sys.path.insert(0, str(Path(__file__).parent))`) and calling `init_skill.init_skill("probe-skill", str(tmp_path), [])` under `capsys` - Acceptance: the test asserts the captured stdout contains `3. Validate: python3 ~/.agents/skills/create-skill/scripts/validate_skill.py` and contains no `~/.claude/skills/`; `uv run pytest "skills/create-skill/scripts/test_init_skill.py::test_printed_validate_step_names_the_union_path" -q` passes.

### Phase 1: Core

No additional work; Phase 0 delivers both CLI corrections and their regressions.

## Success Criteria

- `uv run pytest skills/create-skill/scripts -q` reports 0 failed and 0 errors.
- `python3 skills/create-skill/scripts/validate_skill.py --help` exits 0.
- `python3 skills/create-skill/scripts/validate_skill.py skills/survey/` and
  `python3 skills/create-skill/scripts/validate_skill.py skills/sweep-fix/` both exit 0, so the
  trailing-slash argument shape the CI loop passes still resolves.
- The scaffolder's captured `3. Validate:` line names only the interpreter-prefixed union validator
  and the created skill directory; compatibility literals in source and tests remain supported.

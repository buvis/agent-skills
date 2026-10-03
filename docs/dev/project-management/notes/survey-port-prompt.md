# Prompt: make `survey` portable and publish it

Paste everything below the line into a fresh session opened in
`~/git/src/github.com/buvis/agent-skills`.

---

Make the `survey` skill portable, then publish it to
`~/git/src/github.com/buvis/agent-skills` the way the skills already there were
published. `survey` currently lives at `~/.claude/skills/survey/` as a real
directory and runs on Claude Code only.

Read `AGENTS.md` in the agent-skills repo first. It is the working contract for
that repo and it overrides anything below that contradicts it.

## Why this is not a path rewrite

`survey`'s own frontmatter says `Porting: no - vendor or replace that library
first`. The dependency it means is one import:

- `~/.claude/skills/survey/scripts/run.py:7` inserts `~/.claude/hooks` on
  `sys.path`
- `run.py:8` then does `from _lib_cartographer import try_import_tree_sitter`
- the symbol is used twice: `run.py:161` (get the module) and `run.py:376`
  (set the `degraded` flag when it is None)
- `scripts/test_survey.py:18-19` inserts both `~/.claude/hooks` and the skill's
  own `scripts/` dir on `sys.path`

That is the whole coupling. `try_import_tree_sitter` itself
(`~/.claude/hooks/_lib_cartographer.py:349-373`) is ~25 lines: import
`tree_sitter_language_pack`, cache the result for the process under a lock,
return `None` when it is missing, and emit one `append_audit({"event":
"tree_sitter_missing"})` entry the first time. Only the audit call is
Claude-side; everything else is a generic cached optional import.

**Do not modify `_lib_cartographer.py`.** It is shared infrastructure:
`~/.claude/hooks/cartographer-echo.py`, `strunk-ruling-inject.py` and
`_cartographer_identity.py` import it, and `~/.claude/hooks/tests/` covers it.
The change belongs on the `survey` side.

Decide for yourself whether survey gets its own small helper, vendors the
function, or something better, and say why in one line. Judge it against what
the skill needs, not against what the hook version does.

## The CI problem you must solve, not discover late

`agent-skills` CI runs four jobs: pytest on 3.10 and 3.13, `ruff check`, and a
`shell` job running every `skills/*/scripts/test_*.sh`. `uv run pytest` collects
`tests/` plus every `test_*.py` under `skills/`, so survey's 778-line suite
joins CI the moment you copy it in.

`pyproject.toml` dev dependencies are `pytest`, `pyyaml`, `ruff` — nothing else.
`tree_sitter_language_pack` is NOT among them, and
`test_survey.py:312 test_degraded_not_reported_when_tree_sitter_available` runs
unpatched, asserting the real package is importable. On your machine it passes
because the package happens to be installed; in CI it will not be. Resolve this
deliberately and say which you chose:

- add the dependency (it is large; justify it), or
- make that test skip when the package is absent, or
- restructure so both branches are exercised without the real package.

A test that only passes on one machine is a finding, not a pass.

## Repo rules that will bite you

- **The repo is public.** No personal names, no `/Users/<name>` paths, no
  private project names, in code, comments, fixtures or sample output. Grep for
  them before committing. Every port so far hid at least one.
- **`skills/` is the only directory braid scans.** Anything there is advertised
  to Claude Code, Codex, Copilot and Gemini alike — all four are verified to
  read `~/.agents/skills`. A skill that only works on Claude must not live
  there; `tests/test_skill_placement.py` fails the build if a skill in
  `skills/` declares itself Claude-only.
- **Paths inside a skill** are written `~/.agents/skills/<name>/...`.
  `${CLAUDE_SKILL_DIR}` resolves on Claude Code and nowhere else, so it must not
  survive in the copy. Beware the substitution trap: Claude Code expands that
  placeholder before you read the file, so re-read from disk after edits.
- **The `compatibility:` frontmatter line must be true.** Name anything that
  degrades off Claude Code instead of hiding it; do not claim a dependency is
  gone when it is merely optional.
- **`.braidignore`** holds exactly the 20 compatibility copies whose Claude
  version ships in a plugin. `survey` has no plugin twin, so it gets no entry.

## Traps that cost earlier sessions time

- pytest uses prepend import mode: two test files sharing a **basename** abort
  collection repo-wide. Check `rg --files -g 'test_*.py'` before adding one.
  `--import-mode=importlib` is not the fix — it breaks sibling imports in
  `debrief-meeting` and `review-prd-backlog`.
- `ruff` excludes `skills` and `docs` on purpose (those trees carry illustrative
  code). Do not remove the exclusion. If a formatter rewrites files under
  `skills/` anyway, your loupe plugin is older than v0.2.2 — update it rather
  than committing the churn.
- `sed -i` has no portable spelling (BSD wants a separate suffix argument). Edit
  through a temp file and write back by redirection; `mv` loses the exec bit.
- A script reached through the link farm resolves `../../..` to `~/.agents`, not
  the source repo. Use `cd -P`.
- If a push fails with "communication with agent failed", the 1Password SSH
  agent is locked. Do not work around it: ask the user to push.

## Procedure

1. `rsync -a --exclude __pycache__ ~/.claude/skills/survey/ skills/survey/`,
   then run its tests BEFORE editing anything, so you know the baseline.
2. Remove the Claude coupling. Keep the skill's behaviour identical, including
   the degraded-run reporting when tree-sitter is unavailable.
3. Rewrite `${CLAUDE_SKILL_DIR}` to `~/.agents/skills/survey`, and any
   `~/.claude/skills/<sibling>` reference to `~/.agents/skills/<sibling>`.
4. Replace the `compatibility:` line with an honest portable one.
5. Scrub personal data (see above).
6. Verify, all three:
   - `uv run pytest`
   - `uv run python3 skills/create-skill/scripts/validate_skill.py skills/survey`
   - `~/.agents/bin/braid --check` (braid is not on PATH; zero drift is the bar)
7. Run the skill itself from the link farm, not just its tests: produce a brief
   for a real repo and read it. Tests passing is not evidence the skill works.
8. Untrack the original from the dotfiles bare repo, then delete it:
   `git --git-dir=~/.buvis --work-tree=~ rm -r --cached -- ':(top).claude/skills/survey'`
   then `rm -rf ~/.claude/skills/survey`, then `~/.agents/bin/braid` to lay the
   symlinks, then `braid --check` again.
   The `:(top)` pathspec matters: that repo resolves pathspecs against cwd and
   answers "not tracked" by printing nothing, which has already caused a wrong
   conclusion. Diff the copy against the original before deleting anything.
9. Add a `CHANGELOG.md` entry under `[Unreleased]`, commit in agent-skills and
   in the dotfiles repo, push both, and confirm CI is green.

## Definition of done

`survey` runs on a host with no `~/.claude` directory at all, its tests pass in
CI on 3.10 and 3.13, `braid --check` reports zero drift, and its compatibility
line describes what a reader would actually get on Codex, Copilot or Gemini.

If it turns out `survey` cannot be made portable without faking a dependency or
silently doing less, stop and say so with the specific blocker. A clean refusal
is a legitimate outcome here; a version that quietly degrades is not.

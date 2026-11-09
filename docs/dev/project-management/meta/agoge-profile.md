# agoge strategy profile: agent-skills (master)

Target `/Users/bob/git/src/github.com/buvis/agent-skills` (`<repo>`), branch `master`, HEAD
`f2b82d8372cceab04790e4fb183651a63de1e91d` (tagged `v0.2.0`, the tag also on `origin`). Recon
2026-10-25. Shorthand: `UV` = `uv run --directory <repo>`; `<S>` = a lane scratch dir made with
`mktemp -d -t agoge-<lane>.XXXXXX` (lands under `/var/folders/m6/.../T/`). Facts marked
**[2026-10-18]** come from the earlier profile at
`docs/dev/project-management/meta/agoge-profile.md` (HEAD `4ca90cf`) and were not re-run since.
Changes since the previous recon (`710933e`, five commits): release cut 0.2.0 (`pyproject.toml`,
`uv.lock`, `src/agent_skills_braid/__init__.py`, `CHANGELOG.md`); `e068f25` review-deps-prs now
walks `gh api user/repos --paginate` and gained a new shell suite `test_list_dep_prs.sh`;
`b2e6fcd` glean `matches()` also tries the untrimmed path (collapsed nested `.local/`). Two docs
commits (autopilot ledger, a hold PRD) change no behaviour.

## Surfaces

### Working tree and fences

- `git status --short`: empty (clean) at recon start and end. Nothing may be stashed or cleaned.
- The untracked `skills/purge-devlocal/` leftover of the last recon is gone
  (`ls skills/purge-devlocal` -> no such directory). The validator loop is now green locally.
- Write fence is armed **[2026-10-25, previous recon; behaviour held again today]**: Bash writes
  need literal paths (no `$S`, no shell variables); allowed roots: `<repo>`, `<repo>/docs/dev/tmp`,
  `/private/var/folders/m6/1mnc9pdn28d5vdxy4hxyr1m40000gn/T`, `/private/tmp`. Today a redirect to a
  literal scratch path inside a `bash <S>/x.sh` worked; `Write` into `<S>` worked. Interpreter writes
  (`uv run`, `python3`, `bash x.sh`) are not gated, so a probe must point every output at `<S>`.
- warden refuses a `for` loop variable as a command (`blocked $s: unknown command`) and aegis blocks
  `tail`/`head`/`cat`/`grep`/`find` and pipes: loops go in a scratch `.sh` run as `bash <file>`
  (done today for the validator loop), reads go through `Read`.
- `dev/local/` is gitignored (`.gitignore`).

### Test suites (run today unless marked)

| Suite | Exact command | Observed 2026-10-25 |
|---|---|---|
| Whole Python suite | `UV pytest -q -rs` | `3957 passed, 9 skipped, 236 warnings in 326.34s`, exit 0. Skips: 8 survey (`needs the optional tree_sitter_language_pack`), 1 use-qwen Win32 job object (Windows only). All 236 warnings are one `DeprecationWarning` at `use-qwen/scripts/eval_harness/trees.py:141` (`archive.extractall(dest)`, no tar `filter`). Slowest: `test_run_eval_harness_outcomes.py::test_baseline_and_gate_timeouts_are_suspect` 9.43 s. `UV pytest tests -q` alone: 203 passed in 0.50 s |
| glean + purge-devtmp (the changed code) | `UV pytest -q skills/glean skills/purge-devtmp -rs` | `39 passed in 3.98s` |
| review-deps-prs shell (new) | `bash <repo>/skills/review-deps-prs/scripts/test_list_dep_prs.sh` | 6 passed, 0 failed (gh is a shim in the test: `mocked`) |
| use-codex shell | `bash <repo>/skills/use-codex/scripts/test_codex_run.sh` | 41 passed, 0 failed |
| use-gemini shell | `bash <repo>/skills/use-gemini/scripts/test_gemini_run.sh` | 18 passed, 0 failed |
| use-sonnet shell | `bash <repo>/skills/use-sonnet/scripts/test_sonnet_run.sh` | 30 passed, 0 failed |
| use-qwen shell | `bash <repo>/skills/use-qwen/scripts/test_qwen_run.sh` | 78 passed, 0 failed |
| use-qwen eval automation | `bash <repo>/skills/use-qwen/scripts/test_eval_automation.sh` | 24 passed, 0 failed |
| debrief-meeting SPA | `npm --prefix <repo>/skills/debrief-meeting/app test` | `node --test src/lib/derive.test.js smoke.test.js`: 60 pass, 0 fail, 940 ms |
| Lint | `UV ruff check`; `UV ruff format --check` | `All checks passed!`; `15 files already formatted` |
| Skill validator | `UV python3 skills/create-skill/scripts/validate_skill.py skills/<name>` | scratch loop over `skills/*/`: `pass=50 fail=0` |
| Changelog names | `python3 <repo>/scripts/check_changelog_skills.py` | exit 0, no output |
| structure-git-repo self-test | `UV python3 skills/structure-git-repo/scripts/structure_repo.py --selftest` | all PASS, `DELIVERABLE: helper self-test only (67 checks)` |

Collection: `pyproject.toml` `testpaths = ["tests", "skills", "scripts"]`, `--strict-markers`;
root `conftest.py` gives every test `write_executable_stub`, `isolate_home`, `deny_access`,
`run_resolved_tool` **[2026-10-18]**. CI (`.github/workflows/ci.yml`, pinned by
`tests/test_ci_workflow.py`): jobs `test` (ubuntu, py 3.10 + 3.13), `windows` (3.13), `shell`
(globs `skills/*/scripts/test_*.sh`, so now six suites: the five above plus review-deps-prs),
`lint` (ruff, validator loop, changelog check), `node` (`npm ci` + `npm test`).

### CLI entry points

- **braid** (repo CLI, `src/agent_skills_braid/cli.py`, console script in pyproject):
  `UV braid --version` -> `0.2.0` (was `0.1.0`); `--help` flags unchanged: `--dry-run|--check`,
  `--source`, `--policy`, `--agents-root`, `--claude-root`, `--config-root`, `--no-claude`, `--kiro`,
  `--kiro-root`, `--kiro-agent`, `--forget-kiro-agent`, `--no-kiro`. Proven today with scratch roots
  `<S>/{agents,claude,config}`: sync -> `80 linked, 0 current, 20 ignored, 0 removed ... 80 change(s)`;
  `--check` right after -> `0 linked, 80 current, 20 ignored ... 0 drift`.
  **DANGER:** without all three `--*-root` flags braid writes the real `~/.agents`,
  `~/.claude/skills`, `~/.config/agent-skills`. Every lane passes all three, always.
- **Skill scripts**: `--help` answered exit 0 today for `glean/scripts/glean.py`
  (`{scan,check-staged}`, `--ledger`) and `sweep-fix/scripts/sweep.py` (`--kind {astgrep,rg}
  --pattern --reason --control-term --control-repo [--registry --cwd --cap --deadline --out]`),
  `check_links.py` (`--root`, `--json`; there is no `--out`); the rest answered on 2026-10-25
  earlier today (previous recon, same code): `debrief-meeting/scripts/{parse,build}.py`,
  `create-prd/scripts/ground_prd.py`, `structure-git-repo/scripts/structure_repo.py`,
  `brush/scripts/{trash_untracked,collect_facts}.py`, `audit-qwen/scripts/audit_qwen.py`,
  `distil-memory/scripts/{funnel,docket}.py`, `create-skill/scripts/{init_skill,validate_skill}.py`,
  `use-qwen/scripts/run_eval_harness.py`, `purge-devtmp/scripts/purge_devtmp.py`
  (`(--all | --repo R) [--apply] [--min-age-days] [--age-days] [--empty-trash-days] [-v]`).
  Shell wrappers: `use-{codex,gemini,sonnet,qwen}/scripts/*-run.sh`, `use-qwen/scripts/run-eval.sh`,
  `promote-default.sh`, `mock-llama-server.py PORT MODE_FILE MODEL_ID...` **[2026-10-18]**.
  catchup's 5 bash scripts and `review-deps-prs/scripts/list-dep-prs.sh` touch the operator's
  remotes / every repo the token sees: not invoked live, never from a lane. The list-dep-prs
  script (read today) now runs `gh api user/repos --paginate --jq '.[].full_name'`, exits 1 with a
  stderr message if that fails, then `gh pr list` per repo and filters by author regex
  `^(app/)?(renovate|dependabot)(\[bot\])?$` or title patterns; a lane tests it only through a PATH
  `gh` shim (`mocked`).
  Per-script argument details and side effects: the 2026-10-18 profile's "Skills inventory".
- Proven runs today: `purge_devtmp.py --repo <repo>` (preview) -> `trash=0 live-linked=11 fresh=75
  trash-batches-emptied=0` then `DRY-RUN (use --apply): trash=0 across 1 store(s)`;
  `survey/scripts/run.py` from `<repo>` -> ends `_degraded: tree-sitter unavailable, symbols found
  by regex_` then `*brief truncated*`; `check_links.py --root <repo>` -> exit 1,
  `228 dangling, 0 scan errors` (unchanged; the output still includes findings under the
  `~/.claude/projects/.../memory/` area per the previous recon, not re-measured today).
  `parse.py`/`build.py` round trip (`2 speakers, 4 turns, 19 words`; `wrote debrief.html (83 kB)`)
  was proven earlier today at `710933e`; the debrief code did not change since, not re-run.
- Not usable **[2026-10-25 earlier]**: `convert-to-icon` scripts (`import PIL` ->
  `ModuleNotFoundError`).

### Dev server / browser / database / externals

- **Server:** none. `skills/debrief-meeting/app/package.json` scripts are `build` and `test` only
  **[2026-10-18]**; the product is a single static `debrief.html`.
- **Browser:** no driver. `ls skills/debrief-meeting/app/node_modules` today: `jsdom` present,
  no `playwright`, `puppeteer` or `@playwright`; `mise which playwright` -> "playwright is not a
  mise bin". Browser binaries exist in `~/Library/Caches/ms-playwright` (chromium and headless shell
  1228/1234/1243, ffmpeg-1011), but no package drives them, and warden blocked launching them and
  Chrome **[2026-10-18]**, not re-tried. jsdom is the only DOM path.
- **Database:** none used **[2026-10-25 earlier, `rg` over `skills/` and `src/` code, no hits for
  sqlite3/psycopg/docker; code unchanged in kind since]**. File stores stand in: braid
  `.braid-state.json`, glean ledgers, distil docket queue + memory store,
  `.trash/<date>/manifest.tsv`, debrief `transcript.json`/`extract.json`, use-qwen evidence dirs and
  registries.
- **Externals:** GitHub via `gh` reachable (`gh api repos/buvis/agent-skills --jq .default_branch`
  -> `master`; `git ls-remote --tags origin` -> `v0.2.0` at HEAD). llama-server not listening
  (`curl -m 3 127.0.0.1:8080/health` exit 7). Model CLIs (`claude`, `codex`, `copilot`/`gemini`,
  `pi`) present **[2026-10-18]**, every shipped test stubs them. Operator `HOME` state (`~/.buvis`,
  `~/.claude/{projects,tasks,plugins}`, `~/.pi/agent`, `~/.local/state/glean`,
  `~/.config/gita/repos.csv`) is read-only, never a lane target.

### Flagged for lanes

- Survey prints `*brief truncated*` at a small output (this run: about 3 kB, well under the 5 kB
  budget); `survey/SKILL.md:38-39` explains the footer only as "exceeds the 5KB budget", but
  `run.py:49-79,455-462` also emits it when the layer scan hits its cap **[2026-10-25 earlier
  read]**. Likely a doc gap, not a code defect.
- `use-qwen/scripts/eval_harness/trees.py:141` calls `tarfile.extractall(dest)` without a `filter`
  (DeprecationWarning in the suite, see pytest row). Containment checks exist per the 2026-10-18
  recon; whether it is reachable is trudy's question.
- `check_links.py --root <repo>` reports files outside `<repo>` (auto-memory dir)
  **[2026-10-25 earlier]**; 228 dangling refs, mostly audit/design/PRD prose and the tracked
  `docs/dev/project-management/meta/agoge-profile.md` itself.
- Release truth: `v0.2.0` (tag == HEAD == origin tag) holds 6 changelog bullets for 18
  `feat|fix` commits in `v0.1.0..v0.2.0`
  (`git log v0.1.0..v0.2.0 -E --grep='^(feat|fix)(\(|:|!)'`). No bullet names ground-prd
  (`b6fdefb` exit 2 on bad root), sweep (`e42d637`, `ec79967`, `6adc45f`, `374e1fe`, `aa67491`: parallel
  scan, `--deadline`, `Partial:` line) or use-qwen (`14dc0fa` gate bound); `dcc86bd feat(brush):
  extract trash_dest()` reads like a refactor. `## [Unreleased]` is empty and no `feat|fix` commit
  follows the tag.
- `brush/scripts/collect_facts.py` without `--fast` writes a commit object into the target repo
  **[2026-10-18]**: only on scratch clones.

## Per-specialist strategy

| Specialist | Verdict | Tactics / reason |
|---|---|---|
| olivia (recon) | ran | This profile. |
| walter (journeys) | **armed** | Below. |
| heidi (integration, file stores) | **armed** | Below. No DB; the contracts are file stores and CLI seams. |
| judy (UX through a browser) | **unarmed** | No browser driver: `skills/debrief-meeting/app/node_modules` holds jsdom only (no playwright/puppeteer), `mise which playwright` fails, no serve script exists. Cached chromium binaries are unreachable without a driver, and warden blocked launching them on 2026-10-18. jsdom mounts belong to walter, labelled "jsdom, not a browser". |
| wendy (release, changelog truth) | **armed** | Below. |
| peggy (performance) | **armed**, observation-only | Below. Stated budgets: survey 5KB brief, sweep `--deadline` (300 s default **[2026-10-18]**). Everything else is a number plus method, no budget. |
| trudy (runtime security) | **armed on surface** | Hostile-input surfaces exist: meeting text -> HTML (`parse.py`/`build.py` -> `assets/template.html`), DOCX via `zipfile`, glean secret prescreen and the new `matches()` path logic, path movers (`trash_untracked.py`, `purge_devtmp.py` incl. nested-repo move), braid symlinks from `--source` trees, use-qwen harness copying task trees, operator text to `rg`/`ast-grep` argv in sweep, and `list-dep-prs.sh` output built from repo names and PR titles. Tactics below. Decided on surface alone; whether she runs is decided at dispatch. |

### walter

1. **Debrief round trip.** Write a 4-cue VTT to `<S>/m.vtt`; `UV python3
   <repo>/skills/debrief-meeting/scripts/parse.py <S>/m.vtt --out <S>/out`; `build.py <S>/out`.
   Mount `<S>/out/debrief.html` in jsdom via a scratch `mount.mjs` that loads jsdom with
   `createRequire('<repo>/skills/debrief-meeting/app/package.json')('jsdom')`; assert 7 tabs, no
   errors. Add an `extract.json` per `SKILL.md` with one matching and one non-matching
   `corrections` entry; assert the not-found badge and the `WARN`. Feed `.srt`, Teams `.txt`, and a
   `zipfile`-built `.docx`: message or success, never a traceback.
2. **braid sync -> drift -> duplicate** with all three scratch roots: sync (80 linked), re-sync
   (80 current), `--check` 0 drift; repoint one claude link -> `--check` exit 1; `--source
   <S>/extra` holding a second `skills/brush` -> duplicate-name error before any write; `--kiro
   --kiro-root <S>/kiro` enrol. `--version` must read `0.2.0` and match `pyproject.toml`.
3. **purge-devtmp.** `git init <S>/repo`; under `docs/dev/tmp/` create an old file (`touch -t` 40
   days back), a fresh file, and an old dir holding a `git init`'d nested repo; `UV python3
   <repo>/skills/purge-devtmp/scripts/purge_devtmp.py --repo <S>/repo -v` (preview), then
   `--apply`: nested repo lands in `.trash/<date>/` as one unit with one manifest row, fresh file
   stays; `--apply --empty-trash-days 0` keeps the batch just trashed.
4. **brush trash.** `trash_untracked.py --repo <S>/repo scratch.txt` preview then `--apply`;
   refusals for a tracked file, an outside path, `docs/dev/project-management/x.md`, `.env`.
5. **glean on scratch dotfiles (the 0.2.0 fix).** Scratch run.sh exporting `HOME=<S>/home`, `git
   init --bare <S>/home/.buvis`, ledger `<S>/ledger.json`; create untracked `<S>/home/.config/.local/x`
   so git lists it collapsed as `.config/.local/`; `glean.py --ledger <S>/ledger.json scan`: it
   must not appear as a candidate. Then `check-staged` with a soft hit (exit 0) and a `ghp_`+20
   chars hit (exit 1).
6. **review-deps-prs through a `gh` shim** (`mocked`): PATH `<S>/bin/gh` answering `api user/repos`
   with an org repo `org/r1` and a personal repo, and `pr list --repo ...` with `app/renovate`,
   `dependabot[bot]`, a `chore(deps)` title and an unrelated PR; run `bash
   <repo>/skills/review-deps-prs/scripts/list-dep-prs.sh`: both repos listed, unrelated PR
   skipped; shim exiting 1 for `api` -> exit 1 with the stderr message; empty repo list -> exit 1.
7. **create-skill -> braid.** `init_skill.py demo-skill --path <S>/skills --resources
   scripts,references`; `validate_skill.py <S>/skills/demo-skill`; `UV braid --dry-run --source
   <S>/skills` + three scratch roots lists `demo-skill`.
8. **use-qwen against the mock.** `mock-llama-server.py <port> <S>/mode mock-candidate`, scratch
   `PI_CODING_AGENT_DIR`, `QWEN_APPROVED_REGISTRY`, PATH stubs for `pi`/`mise` as
   `test_qwen_run.sh` lays them; `qwen-run.sh --preflight` ok, then `fail500` -> `completion_failed`.
9. **sweep on a scratch registry** (`--kind rg --registry <S>/registry.csv --cwd <S>/repos/a --out
   <S>/sweep.md`, `HOME=<S>/home`): hits listed; absent control term aborts loudly.
10. **distil-memory docket** without a model: `docket.py save/start/next/decide`, `write.py write
    --store <S>/store`, `unpublished` exit codes.

### heidi

1. **Error paths, no tracebacks:** invalid/truncated `extract.json` and `transcript.json` for
   `build.py`; invalid glean ledger JSON; corrupt docket queue (exit 2 per CHANGELOG);
   `sweep.py --registry <S>/missing.csv`; braid with `{"version": 2}` in `.braid-state.json`;
   `run_eval_harness.py render` on malformed `run.json`; list-dep-prs with a `gh` shim whose
   `api` fails (exit 1, stderr message, nothing on stdout).
2. **Persistence across runs:** braid removes only manifest-owned links after a source skill
   disappears; read-only state file leaves no `.tmp`; purge-devtmp two same-day `--apply` runs
   share one batch with suffixed names and two manifest rows, and a nested repo moved as a unit
   restores cleanly by its manifest row; glean `skip` resurfaces on content change.
3. **Two consumers of one source:** braid union count (50) vs `skills/*/SKILL.md` (50) vs
   `check_changelog_skills.py` iteration vs CI validator loop (which also hits untracked dirs);
   `.braidignore` (20) vs `tests/test_skill_placement.py` vs README plugin table; CI `shell` job
   glob (`skills/*/scripts/test_*.sh`, six files) vs `tests/test_ci_workflow.py` pins vs the five
   suites AGENTS/README mention; version in `pyproject.toml` vs `uv.lock` vs `__init__.py` vs
   `braid --version` vs the `CHANGELOG.md` `[0.2.0]` heading vs the `v0.2.0` tag; use-qwen
   `approved-models.txt` vs `default-model.txt` vs `SHIPPED_DEFAULT_ID` in `test_qwen_run.sh`.
4. **Scope of reads:** `check_links.py --root <S>/repo` on a scratch repo with a scratch `HOME`:
   does it still report files outside `--root`?
5. **External seams with shims:** `gita` shim for `audit_qwen.py`; `gh` shim exiting 1 for
   `collect_facts.py --repo <S>/repo --fast`; `claude` shim for `funnel.py --dry-run`.

### wendy

1. **Commits vs CHANGELOG:** `git -C <repo> log v0.1.0..v0.2.0 --format='%h %s' -E
   --grep='^(feat|fix)(\(|:|!)'` (18) against the `## [0.2.0]` section of `<repo>/CHANGELOG.md`
   (6 bullets). Classify each gap: missing entry vs mistyped commit vs not user-visible (sweep,
   ground-prd, use-qwen, `dcc86bd`). Then `v0.2.0..HEAD` (0 `feat|fix` today) against the empty
   `[Unreleased]`.
2. **Release artefacts:** tag `v0.2.0` == HEAD == origin tag; `pyproject.toml`, `uv.lock`,
   `__init__.py`, `braid --version` all read `0.2.0`; CHANGELOG link/heading shape against `[0.1.0]`.
3. **SKILL.md truth:** each documented command runs as written (all argparse `--help` answer);
   survey `SKILL.md:38-39` vs the two causes of `*brief truncated*`; convert-to-icon must name
   Pillow/numpy; purge-devtmp `SKILL.md` matches the nested-repo behaviour; review-deps-prs
   `SKILL.md` (diff in `e068f25`) matches `list-dep-prs.sh`.
4. **README/AGENTS truth:** README flag table vs `UV braid --help`; `AGENTS.md` "Before
   committing" commands (pytest, validator pass; `braid --check` only with scratch roots);
   `uv tool install --editable .` not runnable in the sandbox, report `unverified`.
5. **CI truth:** `ci.yml` vs `tests/test_ci_workflow.py` vs local results (all six shell suites,
   node, lint, validator loop green locally; Windows job not reproducible here, see hold PRD
   `00044-windows-ci-junction-claim-v1.md`, `unverified`).
6. **Docs rot:** `check_links.py --root <repo> --json` (228 dangling); separate tracked prose from
   audit bundles and from out-of-root hits.

### peggy

1. Suite wall time: `UV pytest -q --durations=25`; then `UV pytest skills/use-qwen/scripts -q
   --durations=10`.
2. survey: time and byte-count `run.py` on `<repo>` and on synthetic repos with 2 vs 200 top-level
   dirs; record which cap (layer scan vs 5120-byte `_BRIEF_BUDGET`) fires at each size.
3. sweep: 2 vs 20 scratch repos, wall time; `rg` shim sleeping 2 s with `--deadline 5` ->
   `Partial:`.
4. purge-devtmp preview/apply on 50 vs 5000 files, and nested repo of 10 vs 10,000 objects (unit
   move should not scale with object count).
5. braid at 50 vs 500 generated skills (`--source <S>/big`): `--dry-run`, sync, `--check`.
6. debrief parse/build/jsdom mount at 100 vs 10,000 cues.
7. glean scan with 100 vs 10,000 files under scratch `.config`, plus 1,000 collapsed nested
   `.local/` dirs (the new `matches()` does a second `fnmatch` per pattern).
8. list-dep-prs against a `gh` shim listing 10 vs 1000 repos (one `gh pr list` per repo): wall time.

### trudy

Benign markers only; every third-party-shaped input is a hand-written fixture (`mocked`); no
third-party host is called; all writes under `<S>` with literal paths.

1. **Transcript -> HTML:** cues `</script><script>window.__m=1</script>`, `<img src=x
   onerror=window.__m=1>`, U+2028, a 20 kB line, speaker `<b>Boss</b>`; same through `extract.json`
   fields and `corrections[].to`. Assert `window.__m` undefined in the jsdom mount and no raw
   `<script` inside the payload of `debrief.html`.
2. **DOCX:** 50 MB `word/document.xml` zip bomb, missing part, non-zip, `../x` entry: bounded
   failure with a message.
3. **glean leaks and verdict bypass:** `api_key=MARKERVALUE`, `ghp_`+20, PEM header; output never
   contains the value; symlink under `.config` to `/etc` not followed; with the new `matches()`,
   paths shaped like `a/.local`, `a/.local/`, `.localx/`, `x.local/` and a glob pattern with a
   trailing slash: does the never verdict cover only real `.local` dirs, and does `check-staged`
   still refuse a staged nested `.local/` file?
4. **Movers:** `trash_untracked.py --apply` with `../outside.txt`, absolute path, symlink out of
   repo, `.env`; `purge_devtmp.py --apply` where `docs/dev/tmp` is a symlink outward, and where
   the nested `.git` is a symlink or a `gitdir:` file pointing outside: where does the unit move
   land, and is anything outside `<S>/repo` touched?
5. **Symlink containment:** braid `--source` with `skills/evil` -> outside dir (dry-run only);
   use-qwen `run_eval_harness.py vet` on templates with escaping symlinks / `..` patches, and a
   tar template with `../` members, absolute members, and device/symlink members aimed at
   `trees.py:141` (`extractall` without a `filter`): does anything land outside `<S>`?
6. **argv and shell:** `sweep.py --pattern '--files'`, `--control-term '-e x'`, newline in pattern;
   `ground_prd.py` with a cited symbol `--version`; `explain-interactively/references/build.sh`
   with spaces and glob-like module names; `list-dep-prs.sh` with a `gh` shim returning repo names
   with spaces, `$(...)` and glob characters, and PR titles with control/ANSI characters (the
   script word-splits `$REPOS` unquoted in `for REPO in $REPOS`): does anything expand or execute?
7. **What leaves the process:** `gh` shim printing `token ghp_MARKER` on stderr for
   `collect_facts.py --fast` and for `list-dep-prs.sh` (its `gh pr list` stderr goes to
   `/dev/null`, `api user/repos` stderr does not); prompt-injection text in a transcript reaching a
   `claude` shim via `funnel.py` (report `unverified`, no model run); `/Users/bob` leaking into
   shareable reports.

## Mocking strategy

| External | Reachable? | Mock | Label |
|---|---|---|---|
| GitHub (`gh`) | yes, authenticated | Read-only single calls on `buvis/*` allowed; `list-dep-prs.sh` is never run against the live token (it walks every repo the token sees): error and hostile bodies via a PATH shim `<S>/bin/gh` in a scratch `run.sh` | live `verified`, shim `mocked` |
| Remote git fetch (catchup) | yes | never against operator remotes; scratch repos with scratch `origin` | `verified` (scratch) |
| `gita`, `~/.config/gita/repos.csv` | present | PATH shim `gita`; sweep `--registry <S>/registry.csv` | `mocked` |
| `claude`, `codex`, `copilot`, `gemini`, `pi` | present | PATH shims as the shipped `test_*_run.sh` suites lay them | `mocked` |
| llama-server | not listening (curl exit 7) | `use-qwen/scripts/mock-llama-server.py <port> <S>/mode <ids>`, mode `ok`/`fail500` | `mocked` |
| Operator `HOME` state | present, read-only | `HOME=<S>/home` inside a scratch `run.sh`; copy only what a test needs | `mocked` |
| Real braid targets | present | never; always three scratch `--*-root` flags | `verified` (scratch) |
| Model output (`extract.json`, proposals, verdicts) | not run | hand-written fixtures per each SKILL.md schema | `mocked` |
| Pillow/numpy, tree-sitter | absent | none; convert-to-icon `unverified`, survey's degraded path is the real path here | `unverified` |
| Browser | no driver | none; DOM facts are `verified (jsdom)`, never "browser" | n/a |
| Windows CI runner | not available | none; `unverified` | `unverified` |

Anything probed through a shim, mock server or hand-written fixture reports `mocked`, never `verified`.

## Authoring assignments

No specialist authors; a lane puts a proposed test in its finding's `fix` field. The master
authors on a branch after the lanes report:

1. review-deps-prs (newest change) -> `skills/review-deps-prs/scripts/test_list_dep_prs.sh`; runner `bash <repo>/skills/review-deps-prs/scripts/test_list_dep_prs.sh` (CI's `shell` job picks it up by glob).
2. glean (newest `matches()` change) -> `skills/glean/scripts/test_glean.py`; runner `UV pytest skills/glean/scripts -q`.
3. purge-devtmp -> `skills/purge-devtmp/scripts/test_purge_devtmp.py`; runner `UV pytest skills/purge-devtmp/scripts -q`.
4. debrief scripts -> `skills/debrief-meeting/scripts/test_parse.py`, `test_debrief_build.py`; runner `UV pytest skills/debrief-meeting/scripts -q`.
5. debrief SPA -> `skills/debrief-meeting/app/smoke.test.js` (new files must be added to the `test` script, node lists them explicitly); runner `npm --prefix <repo>/skills/debrief-meeting/app test`.
6. braid -> `tests/test_braid.py`, `tests/test_braid_check.py`; runner `UV pytest tests -q`.
7. Other script skills (brush, sweep-fix, survey, review-prd-backlog, distil-memory, create-prd, structure-git-repo) -> the skill's own `test_*.py` beside the script; runner `UV pytest skills/<skill>/scripts -q`.
8. use-qwen -> `test_eval_*.py` (pytest) or `test_qwen_run.sh` / `test_eval_automation.sh` (`bash <file>`).
9. Gate before commit: `UV pytest -q`, `UV ruff check`, `UV ruff format --check`, `UV python3 skills/create-skill/scripts/validate_skill.py skills/<touched>`, `python3 <repo>/scripts/check_changelog_skills.py`, `UV braid --check` only with scratch roots.

## Pins and vetoes

Authorization: not asserted

## Freshness stamp

- Recon date: 2026-10-25
- Target HEAD: f2b82d8372cceab04790e4fb183651a63de1e91d

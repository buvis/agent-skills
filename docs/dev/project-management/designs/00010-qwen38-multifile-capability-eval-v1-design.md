# Design: 00010 Qwen3.8 Multi-File Capability Eval vs. Sonnet

PRD: `dev/local/prds/wip/00010-qwen38-multifile-capability-eval-v1.md`.
This is an EVAL PRD: one documentation change, then an operator procedure
that produces gitignored evidence, a report, and a mechanical decision written
back into prose. Nothing here is shipped code and, per the PRD's "no new
modules, scripts, or skills", nothing here is a new script either: every step
is a single existing command (git, cp, tar, mise, uv/cargo/npm, the two
dispatch helpers, GNU `timeout`), recorded verbatim. The design's job is to
pin that procedure precisely enough that an unattended session executes it
without inventing steps, and to name every artifact path and command line so
the evidence cannot be fabricated after the fact.

## Architecture fit

- Layer: `skills/use-qwen/` (portable skill; `SKILL.md`, `references/`,
  `scripts/`). Capsule § Component Boundaries: `approved-models.txt` is the
  machine-read trust list; the trust SCOPE (single-file-only vs multi-file)
  lives only in `SKILL.md` § Model Selection prose. This PRD edits the scope
  prose and the runbook, touches no shipped script.
- Evidence layer: `dev/local/tmp/00010-multifile-eval/` (gitignored, 7-day GC
  while the PRD is in `wip/`) for working artifacts;
  `dev/local/audit-results/` (curated, never trashed) for the report plus a
  full copy of the evidence directory.
- Execution layer: SEALED trees under `/tmp/qwen-eval-00010/` - plain
  directories extracted with `git archive`, with their own single-commit git
  history whose commit (`PRETASK_SHA`) is the pre-task state. One TEMPLATE
  tree per task (warmed up, never dispatched into), and one APFS clone
  (`cp -Rc`, copy-on-write, instant) per engine per attempt. Not git
  worktrees: a worktree shares the source repo's object store, so `git diff
  HEAD` / `git log -p` inside it shows the engine the exact answer. `/tmp` is
  inside the unattended write fence.
- Process bounds: every dispatch and every gate runs under GNU `timeout -k`
  (`/opt/homebrew/opt/coreutils/bin/timeout`, on PATH as `timeout`), which
  puts the command in its own process group and signals the whole group on
  expiry, so a hung `pi` or `claude --print` grandchild dies with its parent.
- External dependencies already in place: llama.cpp on `:8002` serving
  `unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL` under pi provider `llamacpp8002`
  (verified live at selection, `~/.pi/agent/models.json` lists exactly that
  id for that provider); `sonnet-run.sh` and `detect_usage_limit.py` in the
  autopilot plugin (`~/.claude/plugins/cache/buvis-plugins/autopilot/0.3.0/`).
- Machine rule this PRD does NOT own: plan-tasks' qwen-eligibility
  classifier (`docs/plugin-skills/plan-tasks/SKILL.md:327`) routes
  `files_touched <= 3` backend tasks to qwen and lives in the autopilot
  plugin repo, outside this batch's write fence. This PRD records a MEASURED
  scope (its stated deliverable) and says in the same sentence that routing
  does not yet enforce it; the alignment is a recorded deferred decision
  (C10, § Risks).

## Module placement

Edits to existing files (committed):

- `skills/use-qwen/references/eval-runbook.md` - insert a new section
  `## 6. Isolation-safety checklist` between `## 5. On pass: append to the
  registry` and `## Scope of approval`. Phase 0.
- `skills/use-qwen/SKILL.md` - § Model Selection, the bullet at line 69
  ("The eval was deliberately single-file per task ... multi-file work remains
  unproven"): replaced by the measured outcome (Phase 3). The Default bullet
  (line 66) is untouched.
- `docs/plugin-skills/work/references/qwen-integration.md` - § "Under-coverage
  on multi-file tasks" (lines 130-134): the `**Fix**:` paragraph is REPLACED
  (not appended to) by outcome-consistent text (Phase 3, C10). Documentation
  copy; its plugin twin is out of scope (§ Risks).
- `CHANGELOG.md` - one `### Changed` bullet under `[Unreleased]`, scope
  `use-qwen` (Phase 3; the SKILL.md scope edit is the user-visible change).
  The Phase 0 runbook addendum is docs and needs no entry.

New files (gitignored evidence, not committed). No scripts:

```
dev/local/tmp/00010-multifile-eval/
  candidates.md                 # stage A survey: >=10 prospects, fixed schema
  manifest.tsv                  # exactly 6 lines: <prompt-file>\t<verify-cmd>
  tasks/<n>-<slug>.prompt.txt   # verbatim original task + relative Required-files list (immutable)
  tasks/<n>-<slug>.vetting.md   # stage B: kind, Required files + roles, ancillary, shas, history, necessity, interface
  tasks/<n>-<slug>.reverse.patch # the task's hunks on Required files, reversed
  tasks/<n>-<slug>.canonical/<relpath>  # today's copy of each Required test file
  tasks/alt<j>-<slug>.*         # the same set for each fully vetted alternate (j = 1, 2)
  runs/<n>-<engine>-a<k>.out.txt      # helper -o transcript (pi / claude --print output)
  runs/<n>-<engine>-a<k>.wrapper.txt  # copy of the Bash tool's captured output for the dispatch (identity line, timeout marker)
  runs/<n>-<engine>-a<k>.validity.txt # VALID | DISCARDED:<reason>
  runs/<n>-<engine>-a<k>.status.txt   # git diff --name-status PRETASK_SHA, right after dispatch
  runs/<n>-<engine>-a<k>.diff.patch   # git diff --binary PRETASK_SHA, right after dispatch
  runs/<n>-<engine>-a<k>.<step>.txt   # copied gate output; <step> in baseline | own | gate | ablate
  runs/<n>-<engine>-a<k>.<step>.rc    # one line: `gate exit code: <rc>` for that step
  evidence.md                   # combined evidence log (run-eval.sh section shape)
  audit.md                      # false-claim audit, one row per attempt transcript
```

`<n>` is 1-6, `<slug>` kebab-case, `<engine>` is `qwen` or `sonnet`, `<k>`
is the per-engine attempt number starting at 1.

New files (curated, not committed, never GC'd), Phase 3:

- `dev/local/audit-results/qwen38-vs-sonnet-multifile-<YYYY-MM-DD>.md` - the
  comparative report.
- `dev/local/audit-results/qwen38-vs-sonnet-multifile-<YYYY-MM-DD>-bundle/` -
  a verbatim `cp -R` of the whole evidence directory (prompts, vetting,
  patches, transcripts, status, diffs, every gate output), so the report's
  evidence outlives the 7-day GC of `dev/local/tmp/`.

Sealed trees: `/tmp/qwen-eval-00010/<n>-<slug>-tpl/` (template) and
`/tmp/qwen-eval-00010/<n>-<slug>-<engine>-a<k>/` (one per engine per
attempt), left in place at the end (`/tmp` is OS-managed; `rm` is
warden-gated and the report names the paths). A tree whose dispatch was
interrupted is never touched again; the retry is a fresh clone.

## Interfaces & contracts

### C1. Runbook addendum (Phase 0) - exact text

Insert verbatim into `skills/use-qwen/references/eval-runbook.md` after the
`## 5. On pass: append to the registry` section and before `## Scope of
approval`:

```markdown
## 6. Isolation-safety checklist

Walk this list every time you prepare or re-run a task. Each item is a bug that
actually corrupted an eval run (2026-08-31): none is hypothetical, and none is
cheap to detect after the fact.

1. **Never reuse a tree whose dispatch was interrupted, and re-verify
   pre-task state before every re-dispatch.** A killed run can leave the
   target file(s) partly or fully fixed, and a child process (`pi`, `claude
   --print`) can outlive the kill and keep editing. Run every dispatch under
   a process-group timeout (GNU `timeout -k <grace> <limit> <command>`), so a
   hung run dies whole; confirm nothing from that tree survives (`pgrep -lf
   <tree-path>` prints nothing); then build a fresh tree for the retry and
   leave the old one alone. Before dispatching into ANY tree, fresh or not,
   run the task's gate against it and confirm it still fails; never score a
   dispatch made onto a tree that passed its gate beforehand.
2. **Before reverting a file to its pre-task state, check the file's later
   history at line level.** First `git log --oneline --no-patch <commit>..HEAD
   -- <path>`. Empty: no later commit touched the file, and a whole-file
   checkout of `<commit>^ -- <path>` is safe. Non-empty: a whole-file checkout
   is NEVER safe (it erases every later commit, on any line). For a file the
   task ADDED, non-empty disqualifies the task outright: the pre-task state
   is "absent" and no revert can both delete the file and keep the later
   work. For a file the task CHANGED, take the line span where the task's
   hunks sit at HEAD (from `git blame`, or the `+` side of `git diff
   <commit>^ HEAD -- <path>`) and run `git log --oneline --no-patch
   -L<start>,<end>:<path> <commit>..HEAD`. Do not use `-G`/`-S` pickaxe: it
   misses in-body edits. Empty: the later changes are disjoint, so revert
   with the task's own hunks reversed (`git diff <commit> <commit>^ --
   <path>` as a patch), which leaves the later work in place. Non-empty:
   write a surgical, text-level reverse patch of just the task's hunks by
   hand (and save it before dispatch), or disqualify the task. Apply this to
   EVERY file you intend to revert; a file left at today's state needs no
   check.
3. **Never run two test or build invocations concurrently against the same
   tree.** Dispatch one engine, run its gate to completion, restore
   pre-task state, then start the next engine. Shared build dirs and
   file-locking test suites deadlock or cross-contaminate under concurrent
   runs; the symptom is a hang, not an error.

For a multi-file task, items 1 and 2 apply per touched file, and the
pre-task state is the whole set reverted together.
```

Constraints on the edit: keep the existing numbering (`## 1.` .. `## 5.`),
add `## 6.` only, leave `## Scope of approval` last. Validate with
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen`
and `braid --check`.

### C2. Candidate funnel and eligibility (Phase 1)

Terms: the task commit(s) change a set of files. Partition it into
**Required files** (each with a role `impl` | `test` | `caller`; the files
the engine must edit and the eval scores) and **Ancillary files** (changelog,
docs, comments-only or metadata edits in the same commit; kept at today's
state, never reverted, never scored, never counted as stray, and therefore
exempt from history vetting - the incident that vetting prevents cannot
happen to a file nobody reverts). A change that no test-time gate can
observe - a `#[cfg(test)]` visibility move, a re-export reshuffle, a
comment - is a metadata edit and therefore Ancillary even when it sits in a
source file (build-time clarification, batch 202609012242: measured on the
reindex task's `app_contract/mod.rs`). A file that is neither (a real code
change the gate does not need) disqualifies the candidate: the required set
must be exactly the set the gate needs.

**Stage A - survey (`candidates.md`, >= 10 prospects).** From the
`dev/local/prds/done/*.md` ledgers of the gita-registered repos, record per
prospect, in this fixed schema: repo; ledger line (verbatim); `<commit>` (or
`<first>..<last>`); candidate Required files with roles; Ancillary files;
kind (`impl+test` | `impl+caller`); gate command; file-level history per
Required file (`git log --oneline --no-patch <commit>..HEAD -- <path>`,
output or `empty`); a one-line verdict `promising` | `rejected: <why>`.
Stage A checks `single_unit`, `test_gated`, `backend`, `multi_file` (shape
only) and the file-level half of `clean_history`.

**Stage B - full vetting (6 selected + up to 2 alternates).** Each gets the
complete C3 artifact set and passes every condition below. Substitution
(C4) draws ONLY from fully vetted alternates; when none is left the eval
runs with the vetted set it has and the report states the shortfall (C9
step 2 then decides).

A candidate is eligible when ALL hold:

- `single_unit`: one task line in a `dev/local/prds/done/*.md` ledger,
  implemented in one commit `<commit>` or one contiguous run
  `<first>..<last>` by the same task (then `<commit>^` below reads
  `<first>^` and `<commit>` reads `<last>`).
- `test_gated`: a shell command exists whose exit code proves pass/fail,
  runnable from outside the tree (`uv --directory <tree> run ...`,
  `cargo test --manifest-path <tree>/Cargo.toml ...`, `npm --prefix <tree>
  test`, `bats <tree>/...`); this is the **raw test command**.
- `backend`: no UI or visual judgment.
- `reverifiable`: the raw test command PASSES today at the source repo's
  `HEAD` (`<base-sha>`, recorded in `vetting.md`), and the source working
  tree is clean at that moment (`git status --porcelain` empty), run once
  per repo before any tree is built.
- `multi_file`: >= 2 Required files, and the kind is `impl+test` (>= 1
  `impl` plus >= 1 `test` file the same task ADDED or CHANGED) or
  `impl+caller` (>= 1 `impl` plus >= 1 `caller` file the same task changed).
- `clean_history`: for EVERY Required file, the checklist item 2 procedure
  yields `whole-file` (empty file-level history), `hunk-reverse` (later
  commits, all disjoint from the task's lines), or `surgical` (overlap, a
  hand-written reverse patch); `disqualified` otherwise, and always for a
  task-ADDED file with any later history. `git apply --check
  <reverse.patch>` on the extracted `<base-sha>` tree (C4 prep step 4) is a
  syntax/context check only: a rejected hunk means the patch is wrong for
  today's tree; a clean apply does not replace the line-history judgment.
- `necessity` (build-time correction, batch 202609012242: applies to
  Required files with role `impl` or `caller` ONLY - a `test` file's
  load-bearing property is enforced at scoring by `dropped`, `own` and
  `ablate` (C5/C6), and a test file whose task diff only ADDS cases passes
  trivially when it alone is held back, which says nothing about the task;
  measured on tasks 3, 4 and 6 before the correction): in the template tree
  (HEAD = `PRETASK_SHA`), for each Required `impl`/`caller` file `f`:
  `git -C <tpl> apply -R --exclude=<f> <reverse.patch>`
  (restore every Required file except `f` to today's state), run the raw
  test command (NOT the canonical gate: no canonical copy happens here),
  record its exit code and its first failure line, then `git -C <tpl> reset
  --hard <PRETASK_SHA>` and `git -C <tpl> clean -ffdxq -e target -e .venv -e
  node_modules`. Every recorded exit code must be non-zero AND the first
  failure line must be a test-framework failure (an assertion, a compile
  error, a missing test file the task ADDED) rather than a harness error
  (`command not found`, `No such file or directory` on a tool, a syntax
  error in the command). A zero exit for any `f` disqualifies: the task is
  single-file equivalent - with one build-time refinement (batch
  202609012242, measured on the reindex task's `ffi/mod.rs`, `ddb.udl` and
  `ddb-cli/src/commands/crud.rs`): a zero exit on a real code change the raw
  test command structurally cannot observe (a file in a package outside the
  gate's `-p` filter, a file no cargo/pytest target reads, a re-export whose
  only consumers lie outside the gate's test modules) is recorded as
  `gate-invisible (<why>)`, not as a disqualification, PROVIDED at least two
  `impl`/`caller` Required files record `holds`. Gate-invisible files stay
  Required (reverted in the template, listed in the prompt, so the pre-task
  tree stays self-consistent) and are scored only by `dropped` (untouched or
  no-op) and `stray` in C8, never by the gate; the report discloses the
  holds / gate-invisible split per task. Fewer than two `holds` files still
  disqualifies.
- `interface_pinned`: every public symbol, path, flag, and error string the
  canonical test files bind to is named verbatim in the prompt text (the
  ledger line plus its acceptance bullets, plus the prompt's `Names the
  acceptance gate binds to` block - C3 - which lists exactly the identifiers,
  signatures with parameter order, literals, constant names and values the
  canonical tests bind to and the pre-task tree does not already contain).
  Otherwise disqualify: the engine would be graded against a test it could
  not have satisfied by reading the task. The pin list goes in `vetting.md`
  and is identical for both engines. (Refinement recorded at build time,
  batch 202609012242: read literally - ledger line only - the condition
  disqualified every prospect surveyed, because real autopilot tasks reach an
  implementor with a Contract naming exact symbols and a bare ledger line
  under-specifies relative to that mix.)

Sample composition: the 6 in `manifest.tsv` include >= 3 `impl+test` and
>= 1 `impl+caller`, across >= 2 repos and >= 2 languages. Tasks used in the
2026-08-31 single-file round are excluded.

### C3. Per-task artifact set (Phase 1)

`tasks/<n>-<slug>.prompt.txt` (one per task, immutable across engines and
attempts):

```
<verbatim original task line from the done-PRD ledger, including its
acceptance sub-bullets>

You are working in the repository root: the current working directory.
Files to edit (paths relative to it):
- <required-relpath-1>
- <required-relpath-2>
- ... one line per Required file

Names the acceptance gate binds to (use these exact identifiers, signatures,
literals and values):
- <one line per identifier, signature with parameter order, error string,
  constant name and value, or literal the canonical tests bind to that the
  pre-task tree does not already contain; or "none - every name the gate
  binds to already exists in the tree">

Edit only inside this repository. Do not commit.
```

The prompt lists every Required file (the original task ledger did too); it
does not say which is impl and which is test, and it does not simplify the
wording; the pins block names shapes, never implementation or test bodies
(see `interface_pinned` in C2 for why it exists). Relative paths and
"current working directory" keep the prompt valid for every engine tree; the
evidence records the absolute tree path. A `raw test command` may be an
`&&`-chain of tree-relative segments (module-absence checks, `rg` absence
checks, the test run) when the ledger's acceptance is itself such a
conjunction; the executor runs each segment as its own Bash call and the
gate exit code is the first non-zero one.

`tasks/<n>-<slug>.vetting.md` records, in this order: `Kind: impl+test |
impl+caller`; repo path; `<commit>` (or `<first>..<last>`), its parent,
`<base-sha>`; the raw test command and its exit code at `<base-sha>` (must
be 0) with the working-tree-clean check; `Required files:` one line per file
`<relpath> (<role>)`; `Ancillary files:` list or `none`; per Required file:
the history commands run, their output (or `empty`), the verdict
(`whole-file` | `hunk-reverse` | `surgical` | `disqualified`); `Pretask:
<PRETASK_SHA>` (filled at prep); `Necessity:` one line per Required file
`<relpath>: exit <rc>, first failure: <line>`; the pinned interface list;
the canonical test files copied.

`tasks/<n>-<slug>.reverse.patch`: for `whole-file` and `hunk-reverse`
verdicts the output of
`git -C <src> diff <commit> <commit>^ --output=<abs>/tasks/<n>-<slug>.reverse.patch -- <required-paths>`
(Required files only; a file the task ADDED becomes a deletion); for a
`surgical` verdict the hand-written reverse of only the task's hunks, saved
before any tree is built.

`tasks/<n>-<slug>.canonical/<relpath>`: `cp <src>/<relpath>
<abs>/tasks/<n>-<slug>.canonical/<relpath>` for each Required `test` file
the task added or changed, taken while the source tree is verified clean at
`<base-sha>` (today's version, so the gate runs the test as it exists at
HEAD, not the `<commit>`-era one).

`manifest.tsv` line format (the `run-eval.sh` contract, exactly 6 lines):

```
<abs>/tasks/<n>-<slug>.prompt.txt	<raw test command, tree-relative form>
```

The verify column is the raw test command as it reads from a tree root
(e.g. `uv run pytest tests/test_x.py -q`); the executor prefixes the engine
tree with `--directory` / `--manifest-path` / `--prefix` at run time and
copies the canonical tests in first (C5). The manifest is the PRD-mandated
record; it is not fed to `run-eval.sh`.

### C4. Tree prep, preflight, dispatch, validity, retry (Phase 2)

All commands are single Bash tool calls; long ones (`>` a few minutes) run
as background Bash with the harness completion notification as the wait.
Output capture never uses a shell redirect: a command's output is captured
by the Bash tool into its task output file, which is then `cp`'d into
`runs/`; exit codes are recorded in `.rc` files written with the Write
tool; git writes files itself via `--output=`.

**Template prep**, once per task (and per alternate), from the repo root:

1. `mkdir -p /tmp/qwen-eval-00010/<n>-<slug>-tpl`
2. `git -C <src> archive --output=/tmp/qwen-eval-00010/<n>-<slug>.tar <base-sha>`
3. `tar -xf /tmp/qwen-eval-00010/<n>-<slug>.tar -C /tmp/qwen-eval-00010/<n>-<slug>-tpl`
4. `git -C <tpl> apply --check <abs>/tasks/<n>-<slug>.reverse.patch` (a
   failure here means the patch is wrong for today's tree: fix the patch or
   disqualify; never force)
5. `git -C <tpl> apply <abs>/tasks/<n>-<slug>.reverse.patch`
6. `git -C <tpl> init -q`
7. `git -C <tpl> add -A`
8. `git -C <tpl> -c user.name=eval -c user.email=eval@localhost commit -qm "pre-task: <base-sha> minus <commit>"`
9. `git -C <tpl> rev-parse HEAD` -> `PRETASK_SHA`, written to `vetting.md`
   (`Pretask:` line)
10. `mise trust <tpl>/<config>` for each of `.mise.toml`, `mise.toml`,
    `.tool-versions` that exists (check with `ls`)
11. `mise env -C <tpl> -s bash` must exit 0
12. Dependency warmup the repo needs: `uv --directory <tpl> sync`,
    `cargo build --manifest-path <tpl>/Cargo.toml --tests`,
    `npm --prefix <tpl> ci` (background, `timeout -k 60 1800 ...`)
13. The C2 `necessity` runs, in `<tpl>`, each raw test command under
    `timeout -k 30 1800`
14. `git -C <tpl> status --porcelain` must print nothing and
    `git -C <tpl> rev-parse HEAD` must equal `PRETASK_SHA` (the template is
    clean and never dispatched into)

Steps 10-14's outputs go under `## Setup` in `evidence.md` and the report.
A prep that fails at any step disqualifies the task; substitute a vetted
alternate (renumber nothing: the alternate takes the vacated `<n>` in the
manifest and its artifacts are copied to `tasks/<n>-<slug>.*`).

**Preflight**, once before any dispatch; its stdout line is copied verbatim
into `evidence.md`'s first line:

```
~/.agents/skills/use-qwen/scripts/qwen-run.sh --approved-only -P llamacpp8002 --preflight
```

Expected: exit 0 and the line
`preflight: healthy (provider 'llamacpp8002', model 'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL')`.
Any other exit: Phase 2 stops and reports; nothing is dispatched; nothing
starts a server.

**Engine tree**, per task, per engine, per attempt:
`cp -Rc /tmp/qwen-eval-00010/<n>-<slug>-tpl /tmp/qwen-eval-00010/<n>-<slug>-<engine>-a<k>`
(APFS clone: instant, copy-on-write, includes the warmed caches; each engine
and each attempt gets its own caches, nothing crosses). Refuse if the target
exists.

**Dispatch command lines** (recorded verbatim in `evidence.md`; the Bash
tool's cwd is set to the engine tree by a bare `cd <tree>` call first, then
reset with `cd <repo-root>` after, because `pi` and `claude --print` operate
on their cwd):

```
timeout -k 60 3600 ~/.agents/skills/use-qwen/scripts/qwen-run.sh --approved-only -P llamacpp8002 -m unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL -f <abs>/tasks/<n>-<slug>.prompt.txt -o <abs>/runs/<n>-qwen-a<k>.out.txt
timeout -k 60 3600 ~/.agents/skills/use-sonnet/scripts/sonnet-run.sh -y -m sonnet -d /tmp/qwen-eval-00010/<n>-<slug>-sonnet-a<k> -f <abs>/tasks/<n>-<slug>.prompt.txt -o <abs>/runs/<n>-sonnet-a<k>.out.txt

(Engine budget amendment, user decision 2026-09-03: the dispatch bound was
`timeout -k 60 2400` (40 min) for eval task 1, both engines, and for eval
task 2 qwen attempts 1-3 and Sonnet attempt 1. Qwen exceeded it twice on
task 2 while its pi session logs show the full suite green and mypy clean at
38.6 min, the time going to 3-7 min thinking phases per turn at the server's
default xhigh reasoning effort; the user raised the bound to `timeout -k 60
3600` (60 min) for every remaining dispatch of both engines and ordered a
qwen rerun of task 2 (attempt 4). Reasoning effort is unchanged so the engine
stays comparable with the 2026-08-31 qualification. Attempts under the old
bound keep their DISCARDED:timeout records; the effective result stays the
first VALID attempt.)

(Build-time amendment, batch 202609012242: the Sonnet helper path is the
repo copy, not the autopilot plugin cache copy. Both `pi` and `claude --print`
reject a positional prompt that starts with `-`, which every eval prompt does
because it opens with the ledger line `- [ ] ...`; the repo copies of
`qwen-run.sh` (df551fc) and `sonnet-run.sh` (13d68a8) route such prompts over
stdin, byte-verbatim, and the plugin twin of `sonnet-run.sh` still carries the
defect. A DISCARDED attempt in which the engine never started - the CLI
rejected argv, or the helper died before exec - is a harness fault recorded in
the block, not an engine attempt, and does not consume the C4 retry budget.)
```

Both run as background Bash. `-o` captures the `pi` / `claude --print`
child (`2>&1 | tee`) into `out.txt`; `qwen-run.sh` prints its identity line
`Using provider 'llamacpp8002' model 'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL'`
to its OWN stderr before that tee, so it is absent from `out.txt` and
present in the Bash tool's captured output, which is `cp`'d to
`runs/<n>-<engine>-a<k>.wrapper.txt` on completion. Passing `-m` with `-P`
also makes `qwen-run.sh` refuse (exit 1, `model_id_missing`) when `:8002`
does not serve that exact id, so exit 0 is itself identity evidence.

**Validity** (`runs/<n>-<engine>-a<k>.validity.txt`, written with the Write
tool): `VALID` requires all of: exit code 0 (from the tool result; 124/137
means `timeout` fired); for qwen `rg -F "Using provider 'llamacpp8002' model
'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL'" runs/<n>-qwen-a<k>.wrapper.txt`
exits 0; for Sonnet `python3 <autopilot-plugin-root>/skills/run-autopilot/scripts/detect_usage_limit.py --log runs/<n>-sonnet-a<k>.out.txt`
exits NON-zero (exit 0 means a usage-limit banner was found). Anything else
is `DISCARDED:<reason>` with `<reason>` in `exit-<rc>` | `timeout` |
`identity` | `usage-limit`, and NO gate runs on that attempt.

**Quiescence after a timeout**: `pgrep -lf /tmp/qwen-eval-00010/<n>-<slug>-<engine>-a<k>`
must print nothing (GNU `timeout -k` killed the process group). If it
prints anything, stop Phase 2 and report the surviving pids: the bound
failed and nothing may be dispatched until it is understood.

**Retry**, at most ONCE per task per engine, only after a `DISCARDED`
attempt, and always on a fresh clone `-a<k+1>` (the interrupted tree is
never touched again): `DISCARDED:usage-limit` stops Phase 2 until the reset
epoch the marker names (no retry before it); for qwen re-run the preflight
first and stop Phase 2 if it fails. The OTHER engine's result on its own
tree is unaffected. A second `DISCARDED` marks the task `SUSPECT` for that
engine. Per engine, the **effective result** is the first `VALID` attempt;
attempts are immutable and each keeps its own `-a<k>` files.

### C5. Per-task, per-engine sequence (Phase 2)

For `n` in 1..6, for engine in (`qwen`, `sonnet`), strictly serial, on that
engine's own tree `<tree>` = `/tmp/qwen-eval-00010/<n>-<slug>-<engine>-a<k>`.
**Build-time amendment (batch 202609012242):** `git reset --hard`, `git
clean`, `git checkout -- .`, `rm` and `pkill` are never used - on this host
warden prompts for them, and a background subagent blocked on a prompt is
indistinguishable from a hang (two dispatches were lost that way). `RESET`
therefore means **a fresh clone**: `cp -Rpc /tmp/qwen-eval-00010/<n>-<slug>-tpl
<new-dir>` (APFS copy-on-write, instant, mtimes preserved so build caches stay
valid), where `<new-dir>` is the stage-suffixed name given below; the previous
directory is left in place. `RECON` means `RESET` into a new directory then
`git -C <new-dir> apply <abs>/runs/<n>-<engine>-a<k>.diff.patch`. The template
is never mutated. `GATE(<step>)` means: run the raw test command against the
stage directory under `timeout -k 30 1800` as background Bash, `cp` the
captured output to `runs/<n>-<engine>-a<k>.<step>.txt`, write
`runs/<n>-<engine>-a<k>.<step>.rc` with `gate exit code: <rc>`. Stage
directories: `<n>-<slug>-<engine>-a<k>-baseline`, `<n>-<slug>-<engine>-a<k>`
(the dispatch tree), `<n>-<slug>-<engine>-a<k>-own`, `<n>-<slug>-<engine>-a<k>-gate`,
`<n>-<slug>-<engine>-a<k>-ablate`. The same rule applies to C2 `necessity`
(one clone per Required file, `<n>-<slug>-tpl-necessity-<i>`, forward-apply
with `git apply -R --exclude=<f>`, run, leave) - the template stays clean by
construction and C4 step 14 verifies it. **Every clone is followed by
`mise trust <new-dir>/.mise.toml`** (second amendment, measured on eval task
1: mise records trust per config-file path, so a clone at a new path is
untrusted and both `qwen-run.sh` and `sonnet-run.sh` exit 1 silently at their
`set -e` `mise env` PATH step, before `pi` / `claude` starts - no identity
line, no `out.txt`; C4 prep step 10 trusted only the template). A dispatch
is preceded by `mise env -C <tree> -s bash` exiting 0. Original text
follows; read `RESET`/`RECON` as defined here:

1. Clone the engine tree (C4). `git -C <tree> status --porcelain` must print
   nothing and `git -C <tree> rev-parse HEAD` must equal `PRETASK_SHA`.
2. Baseline: `cp <abs>/tasks/<n>-<slug>.canonical/<test-relpath>
   <tree>/<test-relpath>` for each canonical test file (none for
   `impl+caller` with a pre-existing test), then `GATE(baseline)`. The exit
   code MUST be non-zero and the first failure line MUST be a test-framework
   failure (recorded in the evidence block as `expected-failure evidence`).
   Exit 0 means the pre-task state is not pre-task: stop, re-check
   `reverse.patch` against `vetting.md`, rebuild the template, re-clone; if
   it still passes, disqualify and substitute (C4). (Checklist item 1.)
3. `RESET` (the baseline copied canonical files in; the engine must start
   from the true pre-task state). `git -C <tree> status --porcelain` empty.
4. Dispatch (C4): `cd <tree>`, the dispatch command line in the background,
   `cd <repo-root>`. On completion `cp` the tool's captured output to
   `wrapper.txt`, decide validity, write `validity.txt`. `DISCARDED` ->
   record the C6 block with no gate lines, apply the C4 retry rule, and do
   not touch this tree again.
5. Snapshot, BEFORE any gate (the canonical gate overwrites the engine's
   test files): `git -C <tree> add -N .`;
   `git -C <tree> diff --name-status --output=<abs>/runs/<n>-<engine>-a<k>.status.txt <PRETASK_SHA>`;
   `git -C <tree> diff --binary --output=<abs>/runs/<n>-<engine>-a<k>.diff.patch <PRETASK_SHA>`;
   `git -C <tree> rev-parse HEAD` (recorded as `HEAD after dispatch`; moved
   means the engine committed - the diffs above are against `PRETASK_SHA`
   so the measurement is unaffected); `git -C <tree> reset -q`.
6. Gates. Each starts from a reconstruction of the engine's result so no
   gate sees another gate's leftovers: `RECON` = `RESET` then
   `git -C <tree> apply <abs>/runs/<n>-<engine>-a<k>.diff.patch`.
   - `impl+test` only: `RECON`, `GATE(own)` - the engine's tests as left,
     against the engine's impl.
   - `RECON`, copy canonical test files as in step 2, `GATE(gate)` - today's
     tests against the engine's impl; the real gate.
   - `impl+test` only: `RESET`, then
     `git -C <tree> apply --include=<test-relpath> <abs>/runs/<n>-<engine>-a<k>.diff.patch`
     (one `--include` per Required test file: the engine's tests back onto
     the pre-task impl), `GATE(ablate)` - MUST be non-zero with a
     test-framework failure, or the engine's tests are vacuous. (The
     matching impl ablation for `impl+test` is the baseline itself; for
     `impl+caller` the C2 `necessity` check already proved each file
     load-bearing, so a no-op edit shows as a gate FAIL and is classified
     by C8 step 1's whitespace-insensitive diff.)
7. Append the task/engine/attempt block to `evidence.md` (C6).

Never start engine B's step 1 before engine A's step 7 for the same task
(engines have separate trees, but the llama.cpp server and the machine are
shared, and the PRD forbids concurrent gates). Never run two gates at once
anywhere (checklist item 3). A gate that hits its 30-minute `timeout` is
recorded as `gate: timeout` and the engine result becomes `SUSPECT (gate
timeout)` - an infrastructure outcome, not a model FAIL.

### C6. Evidence block shape (`evidence.md`)

First line: the verbatim preflight line from C4. Second block: `## Setup`
with, per task: template path, `PRETASK_SHA`, the `mise trust` / `mise env`
outcomes, the warmup command and exit code, the `Necessity:` lines. Then
per task, per engine, per attempt (the `run-eval.sh` section shape, extended
with the fields the PRD requires):

```markdown
## Task <n>: <abs>/tasks/<n>-<slug>.prompt.txt

Repo: <repo> | Kind: impl+test | impl+caller
Required files: <relpath> (<role>), ... | Ancillary: <list or none>
Template: /tmp/qwen-eval-00010/<n>-<slug>-tpl (base <base-sha>, task <commit>, pretask <PRETASK_SHA>)
Verify: `<raw test command, tree-relative>` after copying canonical: <list or none>

### <engine> attempt <k>

Tree: /tmp/qwen-eval-00010/<n>-<slug>-<engine>-a<k>
Dispatch: `<exact command line from C4, including timeout>`
Engine identity: `<the Using provider ... line from wrapper.txt | sonnet-run.sh -y -m sonnet>`
Captured output: <abs>/runs/<n>-<engine>-a<k>.out.txt (<bytes> bytes); wrapper: ...wrapper.txt (<bytes> bytes)
Dispatch exit code: <rc> | Dispatch validity: VALID | DISCARDED:<reason>
HEAD after dispatch: unchanged | moved to <sha> (engine committed)
Baseline gate exit code: <rc != 0> (runs/<n>-<engine>-a<k>.baseline.txt); expected-failure evidence: `<first failure line>`
Files changed by engine: <paths from status.txt> | dropped: <see C8 step 1, or none> | stray: <changed paths outside Required + Ancillary, or none>
Own tests exit code: <rc> | n/a          (impl+test only)
Gate exit code: <rc> -> PASS | FAIL
Ablation exit code: <rc != 0> | n/a; expected-failure evidence: `<first failure line>`   (impl+test only)
Result: PASS | FAIL:<class> | SUSPECT (<why>) | DISCARDED:<reason>

<details><summary>engine output</summary> ... verbatim runs/<n>-<engine>-a<k>.out.txt ... </details>
<details><summary>gate output</summary> ... verbatim runs/<n>-<engine>-a<k>.gate.txt, then the .rc line ... </details>
```

`stray` is read straight off `status.txt` (a diff against `PRETASK_SHA`): a
changed path outside Required and Ancillary. `dropped` is defined in C8
step 1. `Result` is `PASS` only when the dispatch is `VALID`, the canonical
gate exit code is 0, `dropped` is `none`, `stray` is `none`, and (for
`impl+test`) the own-tests exit code is 0 and the ablation exit code is
non-zero with test-framework evidence. Anything else with a `VALID`
dispatch and no gate timeout is `FAIL:<class>` (C8). A block for a
`DISCARDED` attempt carries no gate lines.

### C7. False-claim audit (`audit.md`)

One row per attempt transcript (>= 12; every `runs/*.out.txt`, discarded
attempts included): the file cited by path; verdict `clean` | `flagged` |
`unverifiable`; when flagged, the quoted claim and the real gate output line
or `status.txt` line it contradicts. A claim is false when the transcript
asserts a test ran or passed, or a file was edited, and the gate or the
snapshot shows it did not. For qwen, narrated tool use without real tool
calls (a `thought`/`<channel|>` block, a fabricated `$ pytest` run) also
counts as flagged. Sonnet's `claude --print` output is the final message
only: a Sonnet claim about its OWN command execution that the external gate
neither confirms nor contradicts is `unverifiable` (reported, never counted
as false); a Sonnet claim contradicted by gate or snapshot is `flagged`.
Only `flagged` qwen rows on `VALID` attempts feed C9 step 1; flags on
discarded attempts are listed separately in the report.

(Build-time amendment, batch 202609012242: `pi` in print mode emits only
its final message, so `runs/<n>-qwen-a<k>.out.txt` is not a transcript. pi
persists every session as JSONL under `~/.pi/agent/sessions/<cwd-key>/`;
the orchestrator copied each qwen attempt's log into the evidence dir as
`runs/<n>-qwen-a<k>.session.jsonl` (task 1 a1 has none, pi never started).
The qwen audit reads the final message plus the session log, which shows
every real tool call, so narrated tool use is checked directly rather than
inferred. Sonnet stays final-message-only with the `unverifiable` rule. The
attempt count came to 18 `out.txt` files.)

### C8. Failure classification (Phase 3) - decision procedure

Applied to each `FAIL` engine result (a `VALID` dispatch, no gate timeout,
that did not meet the C6 PASS definition), in this order, first match wins:

1. `dropped-a-file`: some Required file is (a) absent from `status.txt`
   (untouched, or never created for a task-ADDED file), annotated
   `(untouched)`; or (b) present but
   `git -C <tree> diff --ignore-all-space --ignore-blank-lines <PRETASK_SHA> -- <relpath>`
   is empty after `RECON`, annotated `(no-op edit)`; or (c) present with a
   diff the auditor reads as comment-only, annotated `(comment-only)` with
   the hunk cited. Regardless of the gate outcome.
2. `cross-file-confusion`: no dropped file, but `stray` is not `none` (the
   engine edited a file outside Required + Ancillary), or `diff.patch` shows
   the correlated logic duplicated into a Required file of the wrong role
   instead of split by role (cite the hunk; roles come from `vetting.md`).
3. `unrelated-logic-error`: every Required file changed, no stray files, and
   the canonical gate failed, the own-tests run failed, or the ablation
   passed. Annotate `(interface)` when the first error in `gate.txt` is an
   import, name-resolution, signature, or compile error against a pinned
   symbol; `(vacuous-tests)` when only the ablation condition failed. The
   annotations keep the PRD's three classes and make a vetting miss visible
   rather than counting it as a model logic bug.

Gate timeouts and dispatch discards are not FAILs and are not classified;
they are `SUSPECT` / `DISCARDED` and handled by C9 step 2.

### C9. Decision rule (Phase 3) - as recorded in the PRD, evaluated in order

Inputs: the 6 task blocks (C6, effective per-engine results), `audit.md`.

Precompute BEFORE evaluating any branch, and use these numbers in every
C10 text regardless of which branch stops the evaluation:

- `excluded` = tasks whose canonical gate failed for BOTH engines, plus
  tasks with a `DISCARDED`/`SUSPECT` effective result for either engine.
- `<s>` = 6 - |excluded| (scored tasks); `<p_qwen>`, `<p_sonnet>` = PASS
  counts over scored tasks; `<f>` = `flagged` qwen rows on `VALID` attempts
  (over all tasks).
- `drops` = qwen `dropped-a-file` results over every task with a `VALID`
  qwen effective attempt, excluded tasks included (the drop is the signal
  this PRD exists to observe; missing evidence is never read as a drop).

1. `<f>` > 0 -> `single-file-only`. Stop.
2. Name every task in `excluded` as `suspect` in the report. `<s>` < 5 ->
   `single-file-only`. Stop.
3. `drops` = 0 AND qwen `FAIL` count over scored tasks <= 1 ->
   `full multi-file`. Stop.
4. EVERY `impl+test` task in the manifest (excluded ones included) has a
   qwen effective result of `PASS` and a `clean` audit row -> `impl+test
   pairs only`. Stop. (The PRD says "every impl+test-pair task passed
   cleanly"; an excluded, suspect, discarded, dropped, or flagged
   `impl+test` task did not, so it blocks this branch. The manifest
   guarantees >= 3 such tasks.)
5. Otherwise -> `single-file-only`.

Sonnet's score is reported as context and feeds only step 2.

### C10. Scope prose edits (Phase 3) - exact replacement text

`skills/use-qwen/SKILL.md` line 69 bullet is replaced by ONE of:

- `single-file-only`:
  `- This is a local model - capable for well-scoped work, not a confirmed frontier replacement. Multi-file eval <date> (6 tasks vs Sonnet; local report \`dev/local/audit-results/qwen38-vs-sonnet-multifile-<date>.md\`): <score>, rule branch (<k>) -> **measured \`--approved-only\` trust scope: single-file-only**. Not yet enforced: autopilot's plan-time qwen routing (\`qwen_eligible\`, <= 3 files) still admits 2-3-file tasks until the alignment follow-up lands. **Always keep code review on**, and verify against a real test gate - never against its self-report.`
- `full multi-file`:
  `- Multi-file eval <date> (6 tasks vs Sonnet; local report \`dev/local/audit-results/qwen38-vs-sonnet-multifile-<date>.md\`): <score>, zero dropped files, rule branch (3) -> **measured \`--approved-only\` trust scope: multi-file tasks**. Autopilot's plan-time qwen routing (\`qwen_eligible\`, <= 3 files) is unchanged until the alignment follow-up lands. Still a local model: **always keep code review on**, and verify against a real test gate - never against its self-report.`
- `impl+test pairs only`:
  `- Multi-file eval <date> (6 tasks vs Sonnet; local report \`dev/local/audit-results/qwen38-vs-sonnet-multifile-<date>.md\`): <score>, rule branch (4) -> **measured \`--approved-only\` trust scope: implementation+test pairs only**; wider multi-file work stays unproven. Not yet enforced: autopilot's plan-time qwen routing (\`qwen_eligible\`, <= 3 files) does not distinguish pair shapes until the alignment follow-up lands. **Always keep code review on**, and verify against a real test gate - never against its self-report.`

`<score>` is `qwen <p_qwen>/<s> (<f> false claims), sonnet <p_sonnet>/<s>`
from the C9 precomputation. The report path is a local (gitignored) path by
the PRD's own placement; the prose says "local report" so a public reader
knows it is not shipped.

`docs/plugin-skills/work/references/qwen-integration.md` § "Under-coverage on
multi-file tasks": REPLACE the existing `**Fix**:` paragraph (line 134) with:
`**Measured** <date> on Qwen3.8 over 6 multi-file tasks: <drops> dropped-a-file failures; measured \`--approved-only\` trust scope: <outcome> (local report under \`dev/local/audit-results/\`). Routing still relies on \`state.tasks[i].qwen_eligible\` (\`<= 3\`-file backend tasks, PRD 00032/00019) and the step-5.5 per-task test gate, which escalates a failed qwen attempt to Claude Sonnet; aligning that threshold with the measured scope is a pending autopilot follow-up.`

`skills/use-qwen/references/eval-runbook.md` § 1: ONLY when the outcome is
not `single-file-only`, append to the eligibility bullet:
`(The single-file bar is for qualification; the multi-file trust scope was measured separately - see SKILL.md § Model Selection.)`

`CHANGELOG.md` `### Changed`:
`- **use-qwen**: record Qwen3.8's measured multi-file trust scope (<outcome>) in the Model Selection guidance, backed by a 6-task comparison against Sonnet.`

Phase 3 also appends to `state.deferred_decisions` one entry
`{"issue": "align autopilot qwen_eligible file threshold with measured scope <outcome>", "severity": "medium", "reason": "classifier lives in the autopilot plugin, outside this PRD and this batch's write fence", "status": "pending"}`
so the batch-end walkthrough surfaces the enforcement gap.

### C11. Report shape (Phase 3)

`dev/local/audit-results/qwen38-vs-sonnet-multifile-<date>.md` sections, in
order: `# Qwen3.8 vs Sonnet: multi-file eval <date>`; `## Setup` (preflight
line, per-task template/pretask/mise/warmup/necessity, manifest path, every
tree path); `## Scores` (table: task, kind, repo, qwen effective result,
sonnet effective result, attempts per engine, excluded flag); `## False-claim
audit` (counts per engine incl. `unverifiable`, the `audit.md` rows
inlined); `## Failure classification` (one row per FAIL: engine, task, class
+ annotation, one-line evidence citing the file); `## Decision` (the
precomputed numbers, rule branch fired, outcome, the exact SKILL.md text
applied, the deferred classifier-alignment entry); `## Decision packets`
(standing findings-walkthrough shape, one packet per overturnable call: the
outcome itself, each exclusion, each `flagged` verdict, and the
classifier-alignment follow-up). Beside it, the `-bundle/` copy of the
whole evidence directory.

## Data flow

1. Phase 0 edits the runbook; nothing else reads it programmatically.
2. Phase 1 reads `dev/local/prds/done/*.md` ledgers across the gita repos
   (`gita ll` lists them; the 2026-08-31 round used agent-skills, gems, ddb,
   claude-warden, claude-git-ferry, claude-aegis) and each repo's `git log`.
   Output: `candidates.md` (stage A) -> 6 selected + alternates (stage B)
   -> `tasks/*` (prompt, vetting, reverse.patch, canonical/), `manifest.tsv`.
3. Phase 2 preps one template per task (archive, apply, init, mise, warmup,
   necessity), runs the preflight, then the C5 loop per task per engine on
   cloned trees. Data flows baseline -> reset -> dispatch -> validity ->
   snapshot -> gates, each captured to its own attempt-suffixed `runs/`
   file, then summarised into `evidence.md` with the transcripts embedded;
   `audit.md` is written by reading every `runs/*.out.txt` against its
   `gate.txt` and `status.txt`.
4. Phase 3 reads `evidence.md` + `audit.md`, applies C8 then C9, writes the
   report, copies the evidence directory to the `-bundle/`, then applies C10
   to the three prose files, the CHANGELOG, and `deferred_decisions`. Trees
   stay under `/tmp/qwen-eval-00010/` (OS-managed; the report names the
   paths; no `rm -rf`, which warden gates unattended).

## Reuse inventory

- `skills/use-qwen/scripts/qwen-run.sh` - dispatch, `-P`/`-m`/`-f`/`-o`,
  `--preflight`, `--approved-only`; prints `Using provider ...` to stderr at
  `:453` BEFORE `run_cmd` (`:475-481`), so `-o` misses it and the Bash
  tool's captured output (`wrapper.txt`) is where it lands; the preflight
  line at `:464` goes to stdout; with `-P` + `-m` the post-resolution gate
  (`:432-452`) refuses an unserved id, so exit 0 proves identity.
- `<autopilot-plugin-root>/skills/use-sonnet/scripts/sonnet-run.sh` -
  `-y -m sonnet -d DIR -f FILE -o FILE`; `claude --print` in cwd; final
  message only.
- `<autopilot-plugin-root>/skills/run-autopilot/scripts/detect_usage_limit.py`
  - `--log <file>` exits 0 on a usage-limit marker; discards a rate-limited
  Sonnet attempt instead of scoring it.
- GNU coreutils `timeout` (`/opt/homebrew/opt/coreutils/bin/timeout`) - own
  process group + `-k` hard kill: the whole-tree bound for dispatches and
  gates; `pgrep -lf <tree>` confirms quiescence.
- `git archive --output`, `git apply` (`--check`, `--include`, `--exclude`,
  `-R`), `git init`, `git diff --output --name-status/--binary <sha>`,
  `git diff --ignore-all-space` - stdlib git covers the sealed tree, the
  necessity checks, the snapshot, the reconstruction, the ablation, and the
  no-op-edit test; `cp -Rc` (APFS clone) covers per-engine trees; no helper
  needed.
- `skills/use-qwen/scripts/run-eval.sh` - NOT run (it dispatches qwen only
  and cannot revert between engines), but its manifest format
  (`<prompt-file>\t<verify-cmd>`, exactly 6 lines) and its evidence section
  shape (`## Task n`, `Verify:`, `Gate exit code: rc -> PASS|FAIL`, two
  `<details>` blocks) are reused so the log reads like every prior eval log.
- `skills/use-qwen/scripts/promote-default.sh` - NOT run (no promotion); its
  fact-only-bullet-then-hand-rationale pattern is what C10 follows, and
  `:134` rewrites only the `- **Default:` line, so C10's edited bullet
  survives a future promotion.
- `skills/use-qwen/references/eval-runbook.md` § 1-5 - the structure the
  addendum extends; § 2's provider-pin rule is why every dispatch carries
  `-P llamacpp8002`.
- Prior prompt files
  (`/private/tmp/claude-501/-Users-bob/fc24b46e-.../scratchpad/eval-prompts/task*.txt`,
  still on disk) - the prompt shape C3 generalises (task line + file list).
- `dev/local/audit-results/qwen-eval-unsloth-Qwen3.8-27B-GGUF-UD-Q6_K_XL-2026-08-31.md`
  - the precedent report; its task-1/task-3 transcripts are the contamination
  examples behind checklist item 1.
- `~/.claude/rules-library/rationalizations.md` synonym sets were used for the
  sweep. Greps tried: `worktree` (hits only in unrelated skills: brief-portfolio,
  brush, sweep-fix tests - none is a worktree helper), `mise trust` (no hits
  in skills), `git log.*-L|--pickaxe|-G` (no hits; pattern proven with
  `git log`, 9 hits), `sonnet-run` under `dev/local` (only the PRD, the
  capsule, and the backlog review - no prior Sonnet evidence log exists, so
  the Sonnet half of this eval has no precedent file to copy), `single-file`
  (the three scope-prose sites named in § Module placement). Nothing found
  for: a revert-between-engines driver, a tree-prep helper, or a
  multi-engine evidence log - and per the PRD none is written.

## Alternatives considered

1. **Smallest diff: reuse `run-eval.sh` twice** (once per engine) with a
   6-line manifest whose verify command does revert + gate. Rejected: the
   script dispatches only `qwen-run.sh` (no engine switch), reverts nothing
   between tasks, and its verify command runs AFTER dispatch, so the
   baseline-must-fail check has no place to live. Extending it means editing
   a shipped script, which the PRD forbids.
2. **Shared git worktrees at `HEAD`, one per repo, with per-task revert
   scripts** (the 2026-08-31 shape). Rejected after review: a worktree shares
   the source repo's object store, so `git diff HEAD`, `git log -p`, or `git
   stash` inside it hands the engine the exact answer (Claude Code runs `git
   status`/`git diff` to orient, and `claude --print` hides the tool calls);
   and whole-file `git checkout <commit>^ -- <path>` writes the index, so
   after task 1 the tree's "clean" state is no longer `HEAD` and task 2 starts
   dirty. Both defects were invisible in the single-file round and would have
   invalidated this one.
3. **Sealed trees driven by three throwaway scripts** (`prep.sh`,
   `gate.sh`, `dispatch.sh` under the evidence directory). Rejected after
   two rival-model reviews read them against the PRD's "no new dispatch
   tooling" and "No new modules, scripts, or skills": the wrapper also hid
   the real helper command lines behind its own, and `set -u` scripting let
   a harness failure (`cp`, `git checkout`) masquerade as a test failure.
   Everything the scripts did is expressible as single existing commands,
   so the scripts bought nothing but a constraint violation.
4. **Chosen: sealed template tree per task + APFS-cloned tree per engine
   per attempt, every step a single existing command** (C4/C5). The
   template's commit is the pre-task state by construction, so `RESET` is
   `reset --hard <sha>` + `clean -ffdx` with three cache exemptions, the
   snapshot is `diff --name-status <sha>`, clones give each engine and each
   attempt private caches, and there is no history to leak. GNU `timeout -k`
   bounds every dispatch and gate as a process group. Over option 1 this
   buys: a baseline gate before each engine, snapshot-before-gate so file
   coverage is measured independently of the gate, reverts written down as
   a patch before dispatch (checklist item 2, syntax-checked by `git apply
   --check`), a validity verdict per dispatch, reconstruction before every
   gate, and the own / canonical / ablate triple plus the necessity check
   that together make a one-file solution with a no-op or vacuous second
   edit fail. Cost: one cold warmup per task template (`cargo build --tests`
   on a Rust repo can be 5-10 minutes; clones are free), up to three gate
   runs per engine turn on `impl+test` tasks, and more Bash tool calls per
   step than a script would need; accepted, the PRD budgets hours and the
   Rust tasks are a minority.
5. **Trees at the task's parent commit** (`git archive <commit>^`) instead of
   `<base-sha>` + reverse patch. Pre-task state is exact by construction and
   no history vetting is needed. Rejected: the PRD requires the gate to be
   re-verifiable TODAY, and a parent-commit tree runs the gate against a
   months-old tree (old deps, old lockfiles), which is exactly the
   "single-file-equivalent" trap in reverse: the engine works in a codebase
   that no longer exists. Noted as the cheaper design if a future round drops
   the re-verifiable-today requirement.

Gate design decision worth stating: for `impl+test` tasks the canonical gate
restores today's test file (from `<base-sha>`) before running, so a vacuous
model-written test cannot pass the gate; the model's own test is then run
as-is (`own`) and against the pre-task impl (`ablate`, must fail), so a
whitespace, tautological, or unchanged test cannot count as "touched the
test file". PASS therefore means: valid dispatch, canonical gate passes, no
Required file dropped (including no-op edits), no stray file, own tests
pass, ablation fails (C6). The PRD's phrase "the gate cannot pass with only
one of them reverted-and-fixed" is enforced twice: at vetting by the
`necessity` check on the task itself, and at scoring by the C6 definition.
The price is `interface_pinned` (C2): the canonical test binds to names the
engine must be able to learn from the prompt.

## Risks & edge cases

- **Scope prose vs machine routing disagree.** plan-tasks routes
  `files_touched <= 3` backend tasks to qwen (`qwen_eligible`), in the
  autopilot plugin, outside this repo and this batch's write fence. Every
  C10 outcome text therefore says "measured" and "not yet enforced" in the
  same sentence, the qwen-integration paragraph is replaced so no shipped
  prose contradicts the measurement, and a `deferred_decisions` entry is
  recorded. Next change #1: an autopilot PRD aligning `qwen_eligible`'s
  file threshold (or pair-shape awareness) with the measured scope. This
  design boxes nothing in: the scope text names the outcome and the
  evidence path, which is all that PRD needs.
- **Candidate scarcity.** Multi-file tasks with clean line-level history, a
  necessity-checked required set, AND a prompt that pins the canonical
  test's interface may be rarer than 10 across the portfolio. Mitigation is
  the two-stage funnel with vetted alternates; if fewer than 6 survive stage
  B, the eval runs with what it has, the report states the shortfall, and
  C9 step 2 (`<s>` < 5) decides - do not lower the bar to `impl +
  pre-existing test` or drop `interface_pinned`.
- **Long dispatches vs the 10-minute Bash ceiling.** Multi-file agentic runs
  and Rust gates exceed 600000 ms. Dispatches and gates run in the background
  under GNU `timeout -k` (40 / 30 minutes) with the completion notification
  as the wait. A timed-out dispatch is DISCARDED, its tree abandoned, and
  quiescence is checked with `pgrep` before anything else runs.
- **Server death mid-run.** The preflight passes at Phase 2 start; a crash
  later shows as `DISCARDED:exit-*` or `:timeout`. The retry rule re-runs
  the preflight first and stops Phase 2 if it fails, naming the restart in
  the evidence (`start_qwen` / LlamaBarn on :8002). Nothing in this PRD
  starts a server.
- **Nested `claude --print` under a Claude Code session.** `sonnet-run.sh`
  runs the `claude` CLI with `bypassPermissions`; the user's global hooks
  (warden, aegis, the write fence) apply to that nested session. `/tmp` is
  inside the fence, so tree edits are allowed; a denied edit is invisible in
  the final-message transcript and surfaces only as a dropped file or gate
  FAIL, which the audit row must consider before calling it a model failure.
- **Canonical-test restore masks a dropped or vacuous test.** Handled by
  snapshotting BEFORE any gate, reconstructing before EACH gate, and the
  `own`/`ablate` runs. Reversing snapshot and gate would make every
  `impl+test` task look complete.
- **Engine commits or stages.** Snapshot and reset key on `PRETASK_SHA`,
  never on `HEAD`; a moved HEAD is recorded. `git add -N` makes new files
  visible to `diff` and is undone with `git reset -q` right after.
- **Harness failure read as a test failure.** Every setup step is its own
  command with its own exit code, and every expected-failure run (baseline,
  necessity, ablation) must show a test-framework failure line, recorded in
  the evidence; a `command not found` or missing-tool line invalidates the
  run, it does not satisfy it.
- **A sealed tree is still one `cd ..` from the source repo.** The prompt
  says "edit only inside this repository" and gives no other path; an
  engine that deliberately hunts the source repo would show it in the qwen
  transcript (real tool calls) and nowhere in Sonnet's. Accepted: the
  realistic leak (orientation commands inside the tree) is closed;
  deliberate exfiltration is out of scope.
- **Ancillary files leak the feature description.** A changelog line kept at
  today's state describes the task in one sentence; the prompt already
  carries the full task line, so nothing new leaks.
- **APFS clone assumption.** `cp -Rc` needs APFS (the root volume here is
  APFS). On another filesystem `cp -R` still works, only slower.
- **Cost/time.** 6-8 template warmups, 12+ dispatches, and per engine turn
  one baseline plus one to three gate runs (up to 36 gate runs), all
  serial. Budget several hours; the PRD accepts this.
- Next change #2: a follow-up round that also measures `impl+caller` at
  scale if branch (4) fires. Next change #3: folding the C5 loop into
  `run-eval.sh` as an `--engine` switch once two rounds have run it by
  hand - the artifact layout and evidence shape are what such a script would
  emit. Next change #4: sync the qwen-integration documentation copy's
  plugin twin in the autopilot repo. None is boxed in.

## Test strategy outline

- Phase 0 (docs): `uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen`
  must pass; `braid --check` must pass; `bash skills/use-qwen/scripts/test_qwen_run.sh`
  unchanged (T19 pins the default id, which this PRD does not touch);
  `uv run pytest` unchanged (963 passed / 5 skipped at `e87f23d`). No new
  test file: the addendum is prose and the validator is its gate.
- Phase 1 (artifacts): `candidates.md` lists >= 10 prospects in the stage A
  schema; `manifest.tsv` has exactly 6 non-comment lines and every prompt
  path exists; every selected task and alternate has `vetting.md`,
  `reverse.patch`, and (for `impl+test`) `canonical/`; composition check
  (>= 3 impl+test, >= 1 impl+caller) done by counting the `Kind:` lines in
  `tasks/[1-6]-*.vetting.md`; every `vetting.md` records a raw-test exit
  code 0 at `<base-sha>`, a `Required files:` list with roles, and one
  non-zero `Necessity:` line with a test-framework failure per Required
  file; every prompt lists exactly the Required files.
- Phase 2 (evidence integrity, the checks that cannot be produced after the
  fact): every attempt has `validity.txt`, `out.txt`, and `wrapper.txt`;
  every `VALID` attempt has a `baseline.txt`/`.rc` pair with a non-zero
  code, a `status.txt`, a `diff.patch`, a `gate.txt`/`.rc` pair, and for
  `impl+test` `own` and `ablate` pairs; every qwen `wrapper.txt` marked
  `VALID` contains the exact `Using provider 'llamacpp8002' model
  'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL'` line; `evidence.md` opens with the
  preflight line and its `## Setup` block has one template entry per task;
  `audit.md` has one row per `out.txt`.
- Phase 3: the report's `## Decision` shows the C9 precomputed numbers and
  names a rule branch consistent with them (re-derive by hand); the
  SKILL.md bullet contains the exact report filename and the words
  "measured" and the routing caveat; the qwen-integration paragraph names
  the outcome and no longer carries the old `**Fix**:` text; the runbook § 1
  note is present iff the outcome is not `single-file-only`; the `-bundle/`
  directory exists beside the report and contains `evidence.md`;
  `validate_skill.py skills/use-qwen` and `braid --check` pass again;
  CHANGELOG entry present under `### Changed`; `deferred_decisions` carries
  the classifier-alignment entry.

## Review log

dispatch 1 (claude): cardinal-sin 0, blocker 8, non-blocker 7, question 2

Blockers fixed after dispatch 1: (1) qwen `-o` misses the stderr identity
line -> capture the whole invocation; (2) shared worktree leaks the answer
via git history -> sealed trees; (3) `revert.sh` index/clean defects ->
revert is `reset --hard` + `clean` against a pre-task commit; (4)
`<commit>`-era canonical test -> `canonical/` copies from `<base-sha>`; (5)
impl+test graded against an unseen interface -> `interface_pinned`
eligibility + `(interface)` annotation in C8; (6) snapshot lacked C8 inputs
-> status against the pre-task commit + full `diff.patch`; (7) `mise
trust`/`mise env` missing -> prep steps + `## Setup` evidence; (8) `-L` line
numbers were task-era -> HEAD-side recipe in C1 item 2 and C2.

Non-blockers from dispatch 1 (recorded, not fixed unless noted):
- NB1: Sonnet transcript is the final message only (`sonnet-run.sh:101`);
  tool calls and hook denials are invisible. Possible follow-up: `-S <uuid>`
  per dispatch and copy the session `.jsonl` beside `runs/`. C7 scopes the
  tool-call clause to qwen and adds `unverifiable`; the deeper capture is
  not done.
- NB2: a passing baseline is not always "the revert is wrong". C2 requires
  the gate to pass at `<base-sha>` and the `necessity` check covers this at
  vetting.
- NB3: orphaned `pi`/`claude --print` children. Superseded by dispatch 3's
  cardinal sin (GNU `timeout -k` process-group bound + `pgrep` quiescence).
- NB4: Sonnet usage-limit hits look like a gate FAIL. Resolved by the
  validity contract (`detect_usage_limit.py`).
- NB5: `dev/local/tmp/` evidence is GC'd in 7 days while the report is
  curated. Resolved by the `-bundle/` copy (dispatch 3 NB13).
- NB6: `docs/plugin-skills/work/references/qwen-integration.md` is a
  documentation copy; the plugin twin lives outside this batch's write
  fence. Next change #4.
- NB7: `rm -rf /tmp/qwen-eval-00010` is warden-gated unattended - removed;
  trees are left in place.

Questions from dispatch 1 (recorded; C9 pinned the readings, C3 added
`Kind:` to vetting):
- Q1: C9 inputs. Pinned in the C9 precomputation.
- Q2: Phase 1 composition check counted a `Kind:` field only `evidence.md`
  carried. `vetting.md` now carries it.

dispatch 2 (codex): cardinal-sin 0, blocker 9, non-blocker 4, question 1

Blockers fixed after dispatch 2: (1) no quiescence after an interrupted
dispatch -> attempt trees, never reused (later hardened by dispatch 3); (2)
impl+test gate accepted a one-file solution with a vacuous test edit ->
own / canonical / ablate + vetting-time `necessity`; (3) scored file set
undefined -> `Required files` with roles and `Ancillary files`, used by
prompt, patch, snapshot, classification, and composition; (4) revert kept
ignored cross-run state -> `clean -ffdx` with three named cache exemptions
(later made per-engine by dispatch 3); (5) reset/snapshot trusted a mutable
HEAD -> `PRETASK_SHA`, `reset --hard <sha>`, `diff --name-status/--binary
<sha>`, HEAD movement recorded; (6) PASS ignored stray edits -> PASS
requires `stray: none`; (7) invalid dispatches were gated and retries reused
filenames -> validity contract, no gate on DISCARDED, attempt-suffixed
files, re-preflight before a qwen retry, audit rows per attempt, C9 counts
drops only over valid snapshots; (8) `dispatch.sh` vs "no new dispatch
tooling" -> first argued, then removed by dispatch 3's blocker 2; (9)
trust-scope decision not operationally enforced -> C10 names the unchanged
classifier, REPLACES the qwen-integration fix paragraph, appends a
`deferred_decisions` entry (later reworded to "measured, not yet enforced"
by dispatch 3's blocker 12).

Question from dispatch 2 (fixed as part of the C1 text, since it is shipped
runbook prose): Q3: a task-ADDED file with later history has no stated
verdict -> C1 item 2 and C2 `clean_history` say it disqualifies.

Non-blockers from dispatch 2 (recorded, not fixed unless noted):
- NB8: `git apply --check` is a syntax/context check, not semantic proof.
  Wording corrected in C2.
- NB9: durable SKILL.md prose points at a gitignored report path. C10 labels
  it "local report"; the bundle copy keeps the evidence. A shipped decision
  record under `skills/use-qwen/references/` is not added.
- NB10: cross-file-confusion stays partly a judgment call. C8 step 2
  requires citing the hunk; per-file roles exist in `vetting.md`.
- NB11: Phase 3 test-strategy assertion could not hold for every outcome.
  Corrected to an outcome-specific matrix.

dispatch 3 (codex): cardinal-sin 1, blocker 11, non-blocker 4, question 2

Cardinal sin fixed after dispatch 3: timed-out dispatches left unbounded
child processes -> every dispatch and gate runs under GNU `timeout -k`
(own process group, whole group killed on expiry), quiescence confirmed
with `pgrep -lf <tree>` before anything else runs, Phase 2 stops if
anything survives; C1 item 1 carries the same rule.

Blockers fixed after dispatch 3: (2) `dispatch.sh` was new dispatch tooling
and hid the helper command lines -> all scripts removed; every step is a
single existing command; the recorded dispatch line IS the helper
invocation under `timeout`; (3) interrupted-tree reuse was still allowed in
C1 item 1 -> unconditional "never reuse", plus the gate re-check before any
dispatch; (4) whole-file checkout with disjoint later history still erased
work -> C1 item 2 / C2: whole-file only on empty file-level history,
`hunk-reverse` for disjoint, `surgical` for overlap; (5) ">= 10 eligible"
was circular and substitution undefined -> two-stage funnel (stage A survey
schema, stage B full vetting of 6 + up to 2 alternates; substitution only
from vetted alternates); (6) necessity check restored the test under
examination -> necessity runs the raw test command, never the canonical
copy; (7) harness failures could pass as model evidence -> each setup step
is its own command with its own exit code, and every expected-failure run
must show a test-framework failure line; (8) gate/engine cross-contamination
-> per-engine, per-attempt APFS-cloned trees with private caches, and
`RECON` before every gate; (9) no-op edits satisfied the multi-file
criterion -> `dropped` now includes whitespace-insensitive-empty and
comment-only edits, `necessity` proves each `impl+caller` file
load-bearing, `ablate` catches vacuous tests; (10) contradictory retry
state machine -> per-engine attempts on separate clones, immutable prompt,
effective result = first VALID attempt, the other engine untouched; (11)
branch 4 could fire past an impl+test drop -> branch 4 ranges over EVERY
manifest `impl+test` task, any non-clean one blocks it; (12) recorded scope
read as enforced -> every C10 text says "measured" and "not yet enforced"
in one sentence, plus the deferred decision.

Questions from dispatch 3 (pinned in the text, since both change what a
planner would write): Q4: Ancillary files exempt from history vetting ->
stated in C2 (never reverted, so the incident cannot occur). Q5: score
denominator and `<f>` when branch 1 stops early -> C9 precomputes `<s>`,
`<p_*>`, `<f>`, `drops` before any branch.

Non-blockers from dispatch 3 (recorded, not fixed unless noted):
- NB12: durable evidence bundle incomplete -> Phase 3 copies the whole
  evidence directory to `-bundle/` (applied; one `cp -R`).
- NB13: Sonnet false-run claims unverifiable -> C7 adds the `unverifiable`
  verdict, excluded from counts (applied; one sentence). Session-JSONL
  capture via `-S <uuid>` is not added.
- NB14: timeouts mislabelled as logic errors -> gate timeout is `SUSPECT
  (gate timeout)`, an infrastructure outcome (applied); role-confusion
  judgment remains an annotated, hunk-cited call.
- NB15: `braid --check` omitted -> added to Phase 0 and Phase 3 validation
  (applied; repository rule).


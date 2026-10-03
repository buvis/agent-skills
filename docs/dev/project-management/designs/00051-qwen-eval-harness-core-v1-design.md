# Design: Qwen Eval Harness Core (PRD 00051)

## Architecture fit

The harness lands entirely inside `skills/use-qwen/`, the repo's local-model
dispatch and qualification surface. Three properties of this repo shape every
decision below:

- **Stdlib only.** `pyproject.toml` declares no runtime dependencies; the dev
  group is `pytest`, `pyyaml`, `ruff`. The harness adds none. `urllib.request`
  fetches `/props`, `subprocess` runs everything else, `hashlib` hashes trees.
- **`ruff` excludes `skills/` and `docs/`** (`extend-exclude` in
  `pyproject.toml`), so lint is not a gate here. `uv run pytest` (testpaths
  `tests`, `skills`, `scripts`) plus
  `skills/create-skill/scripts/validate_skill.py` are the whole gate for a
  skill change, and any `test_*.py` added under `skills/` is collected with no
  config change.
- **A repo-root `conftest.py` already supplies host-portability fixtures**
  (`write_executable_stub`, `isolate_home`, `deny_access`, `run_resolved_tool`)
  to every collected test, including `skills/use-qwen/scripts/`. The engine
  adapter tests are built on `write_executable_stub` rather than hand-spelling
  stub paths, because it resolves through `shutil.which` and therefore survives
  Windows `%PATHEXT%` casing.

The harness is an ordinary interpreter script. Warden gates the session's own
Bash line, not the harness's subprocesses, so the harness itself never invokes
`rm`, `git reset --hard` or `git clean`: fresh clones replace resets, and stale
clones are left for an operator to remove.

Line budgets that bind the split below: the autopilot style gate refuses
functions over **50 lines** and files over **800 lines**; the PRD tightens the
package files to **400**. `skills/` sits outside `ruff`, so nothing else
reformats these files.

## Module placement

New files, all under `skills/use-qwen/scripts/`:

| Path | Kind | Purpose |
|---|---|---|
| `run_eval_harness.py` | new | CLI entry: `vet`, `verify` and `run` subcommands |
| `eval_harness/__init__.py` | new | package marker; re-exports nothing |
| `eval_harness/spec.py` | new | spec parsing, validation, path classification |
| `eval_harness/prompts.py` | new | both prompt shapes, dispatch references |
| `eval_harness/runner.py` | new | bounded process-tree execution, reaping, gate lock, failure kinds |
| `eval_harness/win32.py` | new | Job Object and suspended-creation ctypes layer (Windows only) |
| `eval_harness/trees.py` | new | template build, clone, manifest, containment, hash proofs, snapshot |
| `eval_harness/engines.py` | new | qwen/sonnet/cmd adapters, versions, `/props` |
| `eval_harness/events.py` | new | completion, first-edit, usage from session events |
| `eval_harness/gates.py` | new | baseline, `gate`/`own`/`ablate`, candidate observation |
| `eval_harness/evidence.py` | new | seal the vet inputs, `verify` the bundle |
| `eval_harness/attempt.py` | new | `vet`/`run` drivers, per-attempt lifecycle |
| `eval_harness/records.py` | new | exact record key sets, `validate_record`, `derive_validity`, `classify` |
| `eval_harness_fixtures.py` | new | fixture repo builder + argv-recording stub (test-only, importable) |
| `fixtures/fake_engine.py` | new | engine stand-in driven by `FAKE_ENGINE_MODE` |
| `test_run_eval_harness.py` | new | end-to-end `vet`/`run` rounds |
| `test_eval_spec.py` | new | spec + prompt unit suite |
| `test_eval_trees.py` | new | template/clone/snapshot/runner unit suite |
| `test_eval_engines.py` | new | adapter argv, `/props`, event-parsing suite |
| `test_eval_records.py` | new | record contract + `derive_validity` + `classify` suite |
| `test_eval_evidence.py` | new | input sealing, containment, manifest, `verify` |

**The PRD names one test file (`test_run_eval_harness.py`) and one module
split (`spec/trees/engines/attempt`).** The PRD's own Structural Decomposition
grants this phase the split ("the design phase fixes the split, each file <=
400 lines"). Both refinements are that grant exercised: `spec.py` carrying
parsing plus both prompt shapes, and `engines.py` carrying adapters plus event
parsing, each exceed 400; one test file carrying every case above exceeds 800.
Every acceptance command in the PRD is directory-scoped
(`uv run pytest skills/use-qwen/scripts -q`), so the split does not weaken one.
`attempt.py` keeps its PRD name and its lifecycle role; `records.py` is the
"outcome and classification" feature, split out because it is pure and is the
one surface PRD 00052 and PRD 00050 read.

Edits to existing files:

| Path | Edit |
|---|---|
| `skills/use-sonnet/scripts/sonnet-run.sh` | add `-S/--session-id UUID`, appended to `claude --print` in prompt mode only |
| `skills/use-sonnet/scripts/test_sonnet_run.sh` | add the print-mode and resume-mode cases |
| `skills/use-qwen/scripts/mock-llama-server.py` | add a `GET /props` route |
| `CHANGELOG.md` | `### Added` entries for use-qwen and use-sonnet |

**Premise, re-checked 2026-09-07 at HEAD `484ac0d`:**
`skills/use-sonnet/scripts/sonnet-run.sh` IS in this repo (the project capsule
previously recorded it as plugin-only; that was wrong and has been corrected)
and carries no `session-id` option. Control-proved:
`rg -n -e 'session-id' -e '--print' skills/use-sonnet/scripts/sonnet-run.sh`
returns four `--print` lines and zero `session-id` lines, so the empty result
is a real absence and not a broken pattern. The `-S` task is live, not a skip.

`mock-llama-server.py` is shared by `test_qwen_run.sh` (which copies it) and
`test_eval_automation.sh` (which runs it in place). Its current `do_GET` serves
`/v1/models` and 404s everything else, so adding a `/props` branch cannot
change either suite's behaviour: neither requests `/props`.

## Interfaces & contracts

### Import bootstrap

`run_eval_harness.py` is a script, not an installed package. It prepends its
own directory to `sys.path` before importing the package, mirroring the shim
idiom already used by the autopilot CLI's `detect_usage_limit.py`:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_harness import attempt, spec
```

Tests import `eval_harness` and `eval_harness_fixtures` directly: pytest's
prepend import mode already puts `skills/use-qwen/scripts/` on `sys.path`
because that directory holds no `__init__.py`.

### `eval_harness/spec.py`

```python
class SpecError(ValueError):
    """Raised when a spec.json is missing or malformed. str() names the key."""


@dataclass(frozen=True)
class Spec:
    task_id: int
    slug: str
    repo: Path
    first: str
    last: str
    raw_test_cmd: tuple[str, ...]
    task_text: str
    writable: tuple[str, ...] | None
    oracle: tuple[str, ...] | None
    pins: tuple[str, ...]
    warmup: tuple[str, ...]
    kind: str                      # "single-file" | "multi-file"
    architecture: str | None       # tdd only
    invariants: tuple[str, ...]    # tdd only
    read_anchors: tuple[ReadAnchor, ...]   # tdd only
    reading_budget_tokens: int     # 1..100000, default 100000


@dataclass(frozen=True)
class ReadAnchor:
    path: str
    symbol: str
    start_line: int
    end_line: int


def load_spec(spec_dir: Path, shape: str) -> Spec: ...
def classify_paths(changed: list[str], spec: Spec) -> tuple[list[str], list[str]]: ...
def derive_kind(writable: list[str]) -> str: ...
```

- `spec_dir` is `tasks/<n>-<slug>/`; `task_id` is the integer prefix of the
  directory name and `slug` is the remainder after the first `-`.
- `load_spec` raises `SpecError` naming the first offending key. Required for
  both shapes: `repo`, `first`, `last`, `raw_test_cmd`, `task_text`. Required
  additionally when `shape == "tdd"`: `architecture` (non-empty `str`),
  `invariants` (`list[str]`), `read_anchors` (`list` of objects with **exactly**
  the keys `path`, `symbol`, `start_line`, `end_line`; both line numbers
  positive `int`, `end_line >= start_line`).
- `raw_test_cmd` and `warmup` are ordered lists of **non-empty** strings; an
  empty list, a non-list, or a non-string element raises `SpecError`.
  `raw_test_cmd` must be non-empty; `warmup` may be absent (default `()`).
- `reading_budget_tokens` defaults to `100000` and must be an `int` in
  `1..100000` inclusive.
- `kind` is taken from the spec when present and must be `"single-file"` or
  `"multi-file"`; when present it must equal `derive_kind(writable)`
  (`"single-file"` iff exactly one writable path), else `SpecError`. When
  absent it is derived.
- `classify_paths` splits `first^..last` changed paths using the **same
  predicate autopilot's router uses**, reimplemented here (the plugin is not
  importable from this repo — see Reuse inventory). Test-path directory
  segments: `test`, `tests`, `__tests__`, `spec`, `specs`, `fixtures`,
  `__fixtures__`, `__snapshots__`, `testdata`, matched exactly and
  case-sensitively against every segment except the last. Test basenames,
  matched with `fnmatch.fnmatchcase`: `conftest.py`, `test_*.py`, `*_test.py`,
  `*_test.go`, `*_spec.rb`, `*Test.java`, `*Tests.java`, `test_*.sh`,
  `*_test.sh`, and `*.test.<ext>` / `*.spec.<ext>` for
  `js jsx ts tsx mjs cjs`. Test paths become `oracle`, the rest `writable`.
  A `writable` or `oracle` override in the spec replaces that list wholesale.
  Both returned lists are sorted slash-form repo-relative strings.

### `eval_harness/prompts.py`

```python
@dataclass(frozen=True)
class DispatchReference:
    name: str            # e.g. "ivan", "subagent-dispatch"
    version: str
    instructions: str    # verbatim ordered-work / per-surface-verification text


def load_dispatch_references(evidence_dir: Path) -> tuple[DispatchReference, ...]: ...

def render_prompt(spec: Spec, shape: str, writable: list[str], oracle: list[str],
                  references: Sequence[DispatchReference]) -> str: ...
```

`description` shape, in order: `task_text`; the line
`You are working in the repository root: the current working directory. Files to edit:`
followed by the writable list; the pins block (the pins, one per line, or the
single line `none`); the line
`Edit only inside this repository. Do not commit.`

`tdd` shape, in order, mirroring
`<autopilot-plugin-root>/skills/work/references/qwen-integration.md`
§ TDD Implementation Mode: `Failing tests exist at:` plus the oracle paths;
`Make all failing tests pass.`; `Architecture:` plus `spec.architecture`;
`Key invariants:` plus the invariant list; the five rules **verbatim**
(`1. Do NOT modify test files`, `2. Read the tests to understand expected
behavior`, `3. Implement minimal code to pass all tests`, `4. Follow existing
patterns and conventions`, `5. Run tests after implementation to verify`);
`Relevant files:` plus the writable list; `Read-only anchors:` with one line
per anchor as `<path>:<symbol> lines <start>-<end>` (inclusive);
`Reading budget: <N> input tokens.`; and a closing line stating the read
allowlist is the writable paths, the oracle paths and those anchors, to be read
by narrow symbol/range reads with no recursive exploration.
`task_text` and `pins` are **omitted** in `tdd`.

**Dispatch references (blocker fix, dispatch 1).** The PRD requires the tdd
prompt to record the installed Ivan and dispatch-reference versions **and to
incorporate their ordered-work and per-surface-verification instructions**.
Those documents live in the autopilot plugin cache, whose path changes on every
release and which AGENTS.md forbids naming by path — and this repo must stay
runnable where no plugin is installed at all. So the instruction text is
**vendored into the evidence directory by the operator**, never read from a
plugin path:

`<evidence-dir>/dispatch-references.json` is a JSON **array**, order
significant, of objects with exactly
`{"name", "version", "instructions", "provenance"}`, all non-empty strings.
`provenance` records where the operator copied the text from (a path, a URL, a
release tag) so a later reader can tell an installed-version record from an
operator's label. `load_dispatch_references` raises `SpecError` naming the
offending index and key on any deviation. `render_prompt` emits, after the
reading-budget line and in array order, one block per reference:

```
Dispatch reference: <name> <version>
<instructions>
```

Array order is the render order, so the byte-exact prompt assertion has a
defined ordering (a `dict` would not). The versions also land in `run.json`'s
`versions` map as `"<name>"` -> `"<version>"`, alongside `pi` and `claude`.
`description` shape renders no reference block.

**For the `tdd` shape the references are mandatory, not optional** (blocker
fix, dispatch 2). The PRD requires the tdd prompt to *incorporate* the
ordered-work and per-surface-verification instructions; a silently-empty
reference list would render a prompt that omits them while still looking
successful. So `load_dispatch_references` raises `SpecError` when, for
`shape == "tdd"`: the file is absent; the array is empty; it lacks an entry
named `ivan` or one named `subagent-dispatch`; two entries share a `name`; or a
`name` collides with a key `record_versions` already owns (`pi`, `claude`).
`vet` refuses to write `ready` and `run` refuses to dispatch on any of these —
but only when `tdd` is among the shapes being qualified (`vet --shapes`) or run
(`run --shape`). For `description` the file may be absent, and an absent file
yields `()`.

The prompt **never names an engine**: `run` writes one
`<n>-<slug>.prompt.txt` per task and copies its bytes into each attempt
directory, asserting equal SHA256 before dispatch.

`render_prompt` raises `SpecError` when the architecture text or any anchor
contains a solution patch, acceptance prose, or candidate feedback — detected
as: any line beginning `+++ `, `--- `, `@@ `, or `diff --git`, or any line
matching `Acceptance:` / `Acceptance criteria`.

### `eval_harness/runner.py`

```python
@dataclass(frozen=True)
class CommandResult:
    rc: int | None
    timed_out: bool
    first_failure: str | None
    failure_kind: str | None       # "test" | "tool" | "unknown" | None
    wall_s: float | None

    def as_json(self) -> dict: ...


class ProcessTree:
    """Opaque handle to a child and every process it spawns.

    POSIX: a session/process group (`start_new_session=True`).
    Windows: a Job Object the child is assigned to at creation.
    """
    def terminate(self, escalate_after_s: float) -> None: ...
    def survivors(self) -> bool: ...


class OrphanError(RuntimeError):
    """Raised when a command's process tree still has members after cleanup."""


def run_bounded(argv: list[str], cwd: Path, timeout_s: float, *,
                env: dict[str, str] | None = None,
                stdout_path: Path | None = None,
                escalate_after_s: float = 60.0,
                settle_s: float = 5.0) -> tuple[CommandResult, ProcessTree]: ...

def reap(tree: ProcessTree, *, escalate_after_s: float = 60.0,
         settle_s: float = 5.0) -> bool: ...

def run_segments(segments: Sequence[str], cwd: Path, deadline_s: float, *,
                 env: dict[str, str] | None = None) -> CommandResult: ...

def classify_failure(text: str) -> str: ...

@contextmanager
def gate_lock(run_dir: Path, label: str) -> Iterator[None]: ...
```

- `run_bounded` starts the child inside a `ProcessTree` and returns
  `(result, tree)`. **It returns the tree object, not a bare pid**, because the
  orphan question is about the tree and a pid stops answering it the moment the
  direct child exits.
  - **POSIX** — `subprocess.Popen(..., start_new_session=True)`, so every
    descendant inherits the process group id. `terminate` sends `SIGTERM` to the
    group with `os.killpg(pgid, signal.SIGTERM)`, waits `escalate_after_s`, then
    `os.killpg(pgid, signal.SIGKILL)`. `survivors` polls `os.killpg(pgid, 0)`
    for up to `settle_s` and returns `False` as soon as it raises
    `ProcessLookupError` — a grandchild whose parent already exited still
    carries the group id, so it is still seen.
  - **Windows** — a **Job Object**, created through `ctypes` against
    `kernel32` (stdlib; no `pywin32`) and lives in `eval_harness/win32.py`:
    `CreateJobObjectW`, `SetInformationJobObject` with
    `JOBOBJECT_EXTENDED_LIMIT_INFORMATION.BasicLimitInformation.LimitFlags |=
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, then `AssignProcessToJobObject`.
    `terminate` is `TerminateJobObject`, which kills the whole tree at once;
    `survivors` reads
    `QueryInformationJobObject(JobObjectBasicProcessIdList)` and returns `True`
    while any pid remains, polling for up to `settle_s`.
  - **The assignment race is closed by suspended creation** (blocker fix,
    dispatch 2). `AssignProcessToJobObject` on an already-running child leaves a
    window in which the child can spawn a grandchild that never joins the job —
    which is precisely the escape this whole mechanism exists to prevent. So the
    child is created suspended, assigned to the job while it cannot execute, and
    only then resumed. **`subprocess` does not export `CREATE_SUSPENDED`**
    (blocker fix, dispatch 3 — it exports `CREATE_NEW_CONSOLE`,
    `CREATE_NEW_PROCESS_GROUP`, `CREATE_NO_WINDOW`, `DETACHED_PROCESS` and the
    priority classes, and nothing else), so `win32.py` defines
    `CREATE_SUSPENDED = 0x00000004` itself and the numeric value is passed to
    `Popen(creationflags=...)`. `subprocess.Popen` does not hand back the
    initial thread handle either, so `win32.resume_process(pid)` reopens it:
    `CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)` ->
    `Thread32First`/`Thread32Next` filtered on `th32OwnerProcessID == pid` ->
    `OpenThread(THREAD_SUSPEND_RESUME, ...)` -> `ResumeThread`.
  - **Assignment failure halts the run; it is not an attempt-level discard**
    (blocker fix, dispatch 3). If `CreateJobObjectW` or
    `AssignProcessToJobObject` fails (an enclosing job that forbids nesting,
    pre-Windows-8 semantics), the child is killed while still suspended — but
    calling that `DISCARDED:harness` would contradict the record contract two
    ways: the process **was** created, so `launch` is `"started"`, and only
    `"not-started"` may yield `harness`, which is also the one state that
    authorises the retry. Instead this is a run-level halt: `halted.txt` with
    reason `job_assignment_failed`, `run` exits non-zero, no further attempt is
    dispatched. That is the honest response — the harness has just discovered it
    cannot contain any child on this host, which invalidates every subsequent
    attempt, not merely this one. Windows tests cover a child that spawns a
    grandchild immediately and then exits.
  - **Why a job object and not `taskkill /T /F /PID`** (blocker fix, dispatch
    1): `taskkill /T` walks the *live* parent/child links. The PRD's own `hang`
    fixture spawns a child that **outlives its parent**, so by termination time
    the direct child is gone, `taskkill` reports "not found", and a check
    keyed on its exit status would report the tree clean while the orphan runs
    on. A job object is the true Windows analogue of the POSIX process group:
    membership is set at creation and survives the parent's death.
  - `taskkill /T /F /PID` is **not** used at all. It was the dispatch-1 design
    and is wrong for the orphaned-grandchild case (see Alternatives D); job
    creation failing is handled by killing the suspended child, not by falling
    back to a weaker mechanism.
  - **No POSIX-only binary (`killpg`, `pgrep`, `ps`) is required on Windows,
    and no Windows-only binary is required on POSIX.** Both branches are
    stdlib.
- **The containment guarantee is group-scoped, and that limit is stated rather
  than papered over** (blocker fix, dispatch 2). A descendant that deliberately
  calls `setsid` (POSIX) leaves the process group, and no stdlib POSIX
  mechanism short of PID namespaces can hold it; `survivors()` therefore
  answers "no member of this process group remains", not "no process this
  command ever started remains". The fake engine's `hang` mode is specified to
  spawn a grandchild that **outlives its parent without leaving the process
  group** — which is exactly what the PRD asks for ("spawns a child that
  outlives its parent") and is containable. A hypothetical engine that calls
  `setsid` to escape is out of scope for this harness and is recorded here as a
  known limit, not as a defect to discover later.
- `survivors()` returning `True` makes the caller record `HALTED:orphans`
  (see "Where `HALTED:orphans` is written" below). `settle_s` exists so the
  check is not made in the microsecond after the kill, when a doomed process
  has not yet been reaped and a real round would abort spuriously.
- **`reap` runs after EVERY command, not only after a timeout** (blocker fix,
  dispatch 2). A gate command that exits 0 can still leave a background child
  holding a port or a lock, which would then run concurrently with the next
  gate — the exact interference the PRD's "a gate run concurrent with another"
  metric forbids. So `run_bounded` and `run_segments` both call `reap` on every
  path (clean exit, non-zero exit, timeout), and `reap` returns `False` when
  survivors remain. `run_segments` raises `OrphanError` in that case rather
  than returning a result, and **`gate_lock` releases its marker only after
  `reap` has returned `True`** — the lock covers the whole tree's lifetime, not
  just the parent's.
- **`reap` succeeding is the normal case, and `OrphanError` is the rare one**
  (blocker fix, dispatch 3). A leftover child that `SIGKILL`/`TerminateJobObject`
  reaps cleanly is **not** an orphan halt: `reap` kills it, returns `True`, and
  the command's result stands. `OrphanError` fires only when the tree still has
  members *after* the escalation and the settle window — a state no portable
  fixture can produce on demand, so the tests drive it by stubbing
  `ProcessTree.survivors`. The clean-exit-with-leftover-child path is tested
  for what it actually does: the child is reaped, the heartbeat stops, and the
  attempt scores normally with no halt.
- **The bound measures the direct child's lifetime.** `timeout_s` is enforced
  against `Popen.wait`, not against the tree: an engine that exits while a
  descendant lingers has *finished* for timing purposes, and the descendant is
  a reaping question rather than a timeout one. This is why the `hang` fixture
  keeps its **parent** alive past the bound (see `fixtures/fake_engine.py`); a
  parent that returned immediately would score a clean fast run no matter what
  it had spawned.
- `escalate_after_s` defaults to `60.0` per the PRD but is a **parameter**, so
  a test can drive a SIGTERM-ignoring child with a millisecond escalation and
  still assert the two-stage kill inside the 60 s suite budget.
- `gate_lock` is what makes "gates run one at a time" enforced rather than
  asserted (blocker fix, dispatch 1). It creates
  `<run_dir>/.gate-in-flight` with `os.open(path, O_CREAT | O_EXCL | O_WRONLY)`,
  writes `label`, and removes it on exit; an existing marker raises
  `GateConcurrencyError` naming the label already in flight. Every gate
  (`baseline`, `gate`, `own`, `ablate`, and every `vet` check) runs inside it.
  A `cmd:` fixture command can read the marker, so the guarantee is observable
  from inside a gate and therefore testable.
- `run_segments` executes each segment as `bash -lc <segment>` with the segment
  passed as **one argv element** — no segment text is ever interpolated into
  the parent's shell. It stops at the first non-zero segment and returns that
  segment's result. **One deadline covers the whole list**: each segment is
  bounded by the time remaining against `deadline_s`, not by a fresh bound.
- `classify_failure` returns `"tool"` when the text matches a
  tool-error marker (`command not found`, `No such file or directory`,
  `ModuleNotFoundError`, `ImportError`, `ERROR collecting`, `INTERNALERROR`,
  `error: could not`, `is not recognized as an internal or external command`);
  `"test"` when it matches a named test-framework failure marker
  (`FAILED `, `AssertionError`, `assert `, `=== FAILURES ===`, `test result:
  FAILED`, `--- FAIL:`, `not ok `); `"unknown"` otherwise. Tool markers are
  tested **before** test markers, so a collection error never reads as a test
  failure. `first_failure` is the first line matching either marker set, or
  the first non-blank line of the last 40 lines when nothing matches.
- An **unrun** command is represented by `None`, never a `CommandResult` with
  `rc=0`.

### `eval_harness/trees.py`

```python
def build_template(repo: Path, first: str, dest: Path) -> str: ...
def fresh_clone(template: Path, dest: Path) -> Path: ...
def hash_paths(root: Path, paths: Sequence[str]) -> dict[str, str]: ...
def build_manifest(root: Path) -> dict[str, dict]: ...
def head_sha(root: Path) -> str: ...
def prove_state(clone: Path, expected: dict, manifest: dict) -> tuple[str, list[str]]: ...
def contained(root: Path, relpath: str) -> Path: ...
def overlay_oracle(evidence_dir: Path, clone: Path, oracle: Sequence[str]) -> None: ...
def commit_all(clone: Path, message: str) -> str: ...
def snapshot(clone: Path, sealed_sha: str) -> tuple[list[dict], str]: ...
def mise_trust(root: Path) -> None: ...
def apply_patch(clone: Path, patch: Path, *,
                exclude: Sequence[str] = ()) -> CommandResult: ...
```

- `build_template` extracts `git archive <first>^` from `repo` into `dest`,
  then `git init`, `git add -A`, one commit, and returns the commit SHA.
  Every git invocation that writes history passes identity and branch name
  explicitly — `git -c user.name=eval-harness -c user.email=eval-harness@local
  -c init.defaultBranch=main` — because CI runners carry no global git config
  and the harness must not depend on the operator's.
- `fresh_clone` is `shutil.copytree(template, dest, symlinks=True)`. It
  preserves file bytes and symlinks and is the only copy path implemented; see
  Alternatives for the APFS clone that is deliberately not built.
- `hash_paths` returns a map from slash-form relative path to a **lowercase
  sha256 hexdigest**, or the literal string `"absent"` when the path does not
  exist. Directories and symlinks-to-directories hash as `"absent"`; a symlink
  to a file hashes its target's bytes.
- `build_manifest` walks the whole tree except `.git/` and returns a map from
  slash-form relative path to `{"type": "file"|"symlink"|"dir",
  "sha256": <hex>|null, "target": <str>|null, "mode": <int>}` — `sha256` set
  for regular files, `target` for symlinks (the raw link text, unresolved),
  `mode` the executable bit only (`0o755` or `0o644`). It is written to
  `manifest.json`, a **separate file from `pretask.json`**, because the PRD
  fixes `pretask.json`'s key set at exactly `head_sha`, `writable`, `oracle`
  and adding a key there would break PRD 00052's reader.
- `prove_state` returns `("ok", [])` when **all** of: `git status --porcelain`
  is empty; `head_sha(clone)` equals `expected["head_sha"]`; every path in
  `expected["writable"]` and `expected["oracle"]` re-hashes to the recorded
  value; and `build_manifest(clone)` equals `manifest` exactly. Otherwise
  `("PREP_MISMATCH", sorted_differing_paths)`.
  **The manifest comparison is the load-bearing part** (blocker fix, dispatch
  2): `git status --porcelain` does not report `.gitignore`d files, and the two
  path maps cover only the paths the task declares. A stale `.venv`, a
  `__pycache__` from a previous attempt, a `conftest.py` in an undeclared
  directory, or a `pytest.ini` can all change what the gate observes while
  HEAD, porcelain status and both path maps stay identical. The manifest sees
  every one of them.
- `contained(root, relpath)` resolves `relpath` under `root` and raises
  `TreeError` unless the result is inside `root`. It refuses absolute paths,
  `..` traversal, and any path whose resolution crosses a symlink pointing
  outside the tree. **Every write the harness performs goes through it**
  (blocker fix, dispatch 2): `overlay_oracle`'s destinations, `apply_patch`'s
  targets, and the oracle copies `vet` takes. `build_template` and
  `fresh_clone` additionally reject the tree outright when any symlink in it
  has an absolute target or resolves outside the tree, because
  `copytree(symlinks=True)` faithfully reproduces such a link and a later
  write through it would reach the operator's real repository — turning
  "fresh clone per attempt" into shared mutable state across attempts.
  `hash_paths` reads a file symlink's target bytes for the recorded hash, which
  is safe only once containment has been proven, so containment is checked
  first.
- `overlay_oracle` copies `<evidence_dir>/oracle/<relpath>` over
  `<clone>/<relpath>`, creating parents.
- `snapshot` runs, in order, `git add -N .`, `git diff --name-status
  <sealed_sha>`, `git diff --binary <sealed_sha>`, `git reset -q`, and returns
  `(changed, diff_text)`. `changed` is an ordered list of
  `{"status": str, "path": str, "old_path": str | None}`, `old_path` set only
  for renames.
- `mise_trust` runs `mise trust` in `root` when a `.mise.toml`, `mise.toml` or
  `.tool-versions` is present **and** `mise` resolves on PATH. It never raises:
  an absent or failing `mise` is recorded and ignored, so a host without mise
  can still run the suite.
- `apply_patch` runs `git apply --binary <patch>` in `clone` and returns a
  `CommandResult`. `exclude` maps to one `--exclude=<path>` argument per entry,
  which is how "canonical minus that path" is produced for the necessity check:
  the patch is applied whole with that single path excluded, so the tree
  differs from the canonical tree in exactly one file. (The alternative,
  re-checking-out the path from `first^` after a full apply, was rejected: it
  produces the same tree only when the path is not also touched by a rename or
  a mode change in the same patch, and the exclusion form has no such
  precondition.) The `ablate` gate uses the mirror form — apply only the
  candidate's oracle-path hunks — expressed as `apply_patch(clone, diff,
  exclude=writable)`.

### `eval_harness/engines.py`

```python
@dataclass(frozen=True)
class EngineSettings:
    qwen_provider: str | None
    qwen_model: str | None
    sonnet_model: str | None
    usage_limit_cmd: Path | None
    server_reasoning_effort: str | None


def build_argv(engine_id: str, command: str, prompt_file: Path, clone: Path,
               out_file: Path, settings: EngineSettings,
               session_uuid: str) -> list[str]: ...

def dispatch(engine_id: str, command: str, prompt_file: Path, clone: Path,
             attempt_dir: Path, settings: EngineSettings,
             bound_s: float) -> dict: ...

def record_versions(engine_ids: Sequence[str],
                    settings: EngineSettings) -> dict[str, str | None]: ...

def server_root(provider_url: str) -> str: ...
def fetch_server_props(provider_url: str, declared_effort: str | None,
                       timeout_s: float = 10.0) -> dict: ...
```

Exact argv, asserted byte-for-byte by the adapter tests:

- **qwen** — `["bash", "<home>/.agents/skills/use-qwen/scripts/qwen-run.sh",
  "--approved-only", "-P", <provider>, "-m", <model>, "-f", <prompt>,
  "-o", <out>]`, with `PI_CODING_AGENT_SESSION_DIR=<attempt_dir>/pi-sessions`
  added to the child environment. After the run, the newest `*.jsonl` under
  that directory is copied to `<attempt_dir>/session.jsonl`.
- **sonnet** — `["bash", "<home>/.agents/skills/use-sonnet/scripts/sonnet-run.sh",
  "-y", "-m", <model>, "-d", <clone>, "-f", <prompt>, "-o", <out>,
  "-S", <uuid>]` with a freshly generated `uuid4`. The transcript is located
  with `Path(projects_root).rglob(f"{uuid}.jsonl")` — **stdlib, not `rg`**
  (dispatch-1 fix): `rg` is not guaranteed on the Windows runner, and a missing
  `session.jsonl` would silently make `completion` `"unknown"` and score every
  sonnet attempt `DISCARDED:incomplete`. `<projects_root>` defaults to
  `~/.claude/projects` and is overridable for tests.
- **cmd** — `command` of the form `cmd:<path>`. argv is
  `[sys.executable, <path>, <prompt_file>]` when `<path>` ends in `.py`, else
  `[<path>, <prompt_file>]`. Run with `clone` as cwd. Test use only.
  **The fake adapter satisfies the same validity rules through the same
  observable evidence** (blocker fix, dispatch 2) — otherwise its `PASS`
  fixtures would prove nothing about the real path, because `derive_validity`
  would be reading fields no fake ever populates. Its protocol:
  - **identity** — the fake engine writes `Using engine 'cmd:<mode>'` to
    **stderr**, which lands in `wrapper.txt`; the adapter matches that literal,
    the same way the qwen adapter matches `Using provider '<P>' model '<M>'`.
    Identity absent (the `silent-edit` mode) yields `identity: null`.
  - **final message** — the fake writes its final text to **stdout**, captured
    to `out.txt`; `final_message_bytes` counts those bytes.
  - **completion** — the fake writes `<attempt_dir>/session.jsonl` with one
    terminal assistant event carrying `stop_reason: "end_turn"`, the text, a
    timestamp, and a `usage` object; `read_events` parses it exactly as it
    parses a real transcript. The `silent-edit` mode writes an event with
    `stop_reason: "length"`, which must read as `incomplete`.
  - `usage_limit` is `"unchecked"` for `cmd:` engines unless the test passes
    `--usage-limit-cmd`.

`dispatch` returns the `engine_run` block (contract below). Identity evidence:
qwen matches the literal `Using provider '<P>' model '<M>'` in `wrapper.txt`
(emitted by `qwen-run.sh` on stderr); sonnet records the model flag it passed.
`usage_limit` is `"hit"` when `settings.usage_limit_cmd` (or the autopilot
plugin cache copy of `detect_usage_limit.py`) exits **0** for
`--log <out.txt>`, `"clear"` when it exits non-zero, and `"unchecked"` when no
checker is configured or resolvable. (Exit 0 means limit-stuck — the CLI prints
the reset epoch on stdout; its signature is
`detect_usage_limit.py [--log PATH] <cwd> [projects_root]` and `--log` alone is
a valid invocation.)

`server_root` removes exactly one trailing `/v1` path component plus any
trailing slash, preserving any preceding proxy path:
`http://h:8002/v1` -> `http://h:8002`; `http://h/proxy/v1/` -> `http://h/proxy`;
a URL with no trailing `/v1` is returned with only its trailing slash stripped.
`fetch_server_props` requests `<server_root>/props` (never `/v1/props`) with
`urllib.request` and returns the `server` block with **exactly** these keys:
`n_ctx` (from `default_generation_settings.n_ctx`), `model_alias`,
`build_info`, `sampling` (a map with exactly `temperature`, `top_k`, `top_p`,
`min_p` from `default_generation_settings.params`),
`supports_reasoning_effort` (from
`chat_template_caps.supports_reasoning_effort`), `declared_effort` (the
operator's `--server-reasoning-effort` label, **never measured or verified**),
`metadata_error`. Unavailable values are `None`; `metadata_error` is `None` or
a credential-free diagnostic string. No credential ever enters a record or an
argv.

`record_versions` runs `pi --version` only when `"qwen"` is among
`engine_ids`, and `claude --version` only when `"sonnet"` is. A fake-only run
(`cmd:` engines only) records both as `None`, performs **no** network request
and **no** real-engine probe.

### `eval_harness/events.py`

```python
def read_events(session_path: Path | None, out_path: Path) -> dict: ...
```

Returns `{"completion", "final_message_bytes", "first_edit_s", "usage"}`.
`completion` is `"complete"` when a terminal assistant message with non-empty
text is observed; `"incomplete"` when the stream ended with an observed
`length` / `error` / `aborted` stop reason, or is malformed; `"unknown"` when
no completion evidence exists at all. **Missing evidence is never success.**
`first_edit_s` is the elapsed seconds to the first successful write/edit tool
result, or `None`. `usage` has exactly `input_tokens`, `output_tokens`,
`cache_read_tokens`, `cache_write_tokens`, `cost_usd`; token fields are
non-negative integers, `cost_usd` a non-negative number, and any unreported
field stays `None` — never `0`. Usage is aggregated **once per final message
event**, excluding streaming deltas. For qwen, the captured Pi terminal message
is the final text; wrapper diagnostics never count as final text.

### `eval_harness/records.py`

```python
PRETASK_KEYS = ("head_sha", "writable", "oracle")
SEALED_KEYS = ("head_sha", "writable", "oracle")
VETTING_KEYS = ("template_sha", "gate_bound_s", "warmup", "baseline",
                "necessity", "canonical", "inputs_sha256", "shapes", "ready")
COMMAND_RESULT_KEYS = ("rc", "timed_out", "first_failure", "failure_kind", "wall_s")
ENGINE_RUN_KEYS = ("argv", "launch", "exit", "timed_out", "wall_s", "identity",
                   "completion", "final_message_bytes", "usage_limit",
                   "first_edit_s", "usage")
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_tokens",
              "cache_write_tokens", "cost_usd")
GATE_KEYS = ("gate", "own", "ablate")
ATTEMPT_KEYS = ("task", "engine", "attempt", "shape", "clone", "prep", "baseline",
                "engine_run", "validity", "changed", "stray", "oracle_intact",
                "dropped", "gates", "outcome", "class", "started", "finished")
RUN_KEYS = ("schema_version", "run_id", "started", "config", "engines", "tasks",
            "versions", "server")
SERVER_KEYS = ("n_ctx", "model_alias", "build_info", "sampling",
               "supports_reasoning_effort", "declared_effort", "metadata_error")

RECORD_KINDS = ("attempt", "run", "pretask", "sealed", "vetting",
                "command_result", "engine_run", "usage", "server")
REQUIRED_GATES = {"tdd": ("gate",), "description": ("gate", "own", "ablate")}


class RecordError(ValueError):
    """Raised when a record's key set or field domain violates the contract."""


def validate_record(kind: str, record: dict) -> None: ...
def derive_validity(record: dict) -> str: ...
def classify(record: dict) -> tuple[str, str | None]: ...
def is_valid_baseline(baseline: dict | None) -> bool: ...
```

`validate_record` accepts only a `kind` in `RECORD_KINDS` and raises
`RecordError` on any other value, so a typo cannot silently validate nothing.

`validate_record` raises `RecordError` when the top-level key set is not
**exactly** the declared tuple (missing *or* extra), recursing into `prep`,
`baseline`, `engine_run`, `usage` and `gates`. A key is never omitted; unknown
values are `null`. **It also checks each field's type and domain** (blocker
fix, dispatch 2) — an exact key set alone does not stop a writer and a reader
disagreeing about whether `task` is `3` or `"3"`, and PRD 00052 is written
against this table, not against the key names:

| Field | Type and domain |
|---|---|
| `task` | `int`, the numeric spec-directory prefix; matches `run.json`'s `tasks[].id` |
| `engine` | `str`, one of the `run.json` `engines[].id` values (`qwen`, `sonnet`, `cmd1`, `cmd2`) |
| `attempt` | `int`, `1` or `2` |
| `shape` | `str`, `"description"` or `"tdd"` |
| `clone` | `str`, an absolute path in the host's native form |
| `outcome` | `str`, one of `PASS`, `FAIL`, `TIMEOUT`, `SUSPECT`, `DISCARDED` |
| `class` | `str` for `FAIL` (`test-mutation`, `stray-edit`, `no-edit`, `dropped-a-file`, `vacuous-tests`, `logic-error`), else `null` |
| `validity` | `str`, `"VALID"` or `"DISCARDED:<reason>"` from the reason set |
| `started`, `finished` | `str`, UTC ISO 8601 with a `Z` suffix, second precision |
| `changed[]` | objects with exactly `status`, `path` (`str`, slash-form relative), `old_path` (`str` for renames and copies, else `null`) |
| `stray`, `dropped` | sorted `list[str]` of slash-form relative paths, or `null` when unobserved |
| `oracle_intact` | `bool` in tdd **when observed**; `null` in description, and `null` in tdd when the attempt failed before the post-dispatch re-hash |

`changed[].status` is exactly what `git diff --name-status` emits (blocker fix,
dispatch 3 — "a git status letter pair" was wrong twice over: the values are
single letters, and `R`/`C` carry a similarity score): one of
`A C D M R T U X B`, optionally followed by 1-3 digits for `R` and `C`
(`R100`, `C75`). `validate_record` matches `^[ACDMRTUXB][0-9]{0,3}$` and
requires `old_path` to be non-null exactly when the letter is `R` or `C`.
Likewise `oracle_intact` may be `null` in tdd: the dispatch-2 table said `bool`
in tdd unconditionally, which contradicts the nested contract's rule that
unobserved values are `null` and would have made every early-failing tdd
attempt fail validation.

`vetting.json`'s `necessity` is a map from slash-form writable non-test path to
an object with **exactly** `{"result": <command result or null>, "holds":
<bool>}`. `holds` is `true` only when `result` is present, `result["rc"]` is a
non-zero `int`, `result["timed_out"]` is false, and
`result["failure_kind"] == "test"`. `vetting.json`'s `warmup` is a list of
command-result objects in segment order.

Nested contracts, all keys always present:

- `prep`: `{"status", "differing_paths"}`; status `"ok"` or `"PREP_MISMATCH"`;
  `differing_paths` a sorted list of slash-form relative strings.
- Command result: `COMMAND_RESULT_KEYS`. `rc` integer or `None`, `timed_out`
  bool, `first_failure` string or `None`, `failure_kind` one of `"test"`,
  `"tool"`, `"unknown"`, `None`, `wall_s` non-negative number or `None`.
  `gates` has exactly `gate`, `own`, `ablate`, each a command result or `None`.
- `engine_run`: `ENGINE_RUN_KEYS`. `argv` a list of strings; `launch` one of
  `"not-started"`, `"started"`, `"unknown"`; `exit` integer or `None`;
  `identity` a matched model/provider string or `None`; `completion` one of
  `"complete"`, `"incomplete"`, `"unknown"`; `usage_limit` one of `"clear"`,
  `"hit"`, `"unchecked"`. **A no-launch attempt still writes this whole object**
  with null measurements and `launch: "not-started"`.
- `changed`, `stray`, `dropped`, `oracle_intact`: `changed` is an ordered list
  of `{status, path, old_path}`; `stray` and `dropped` are sorted path lists;
  `oracle_intact` is boolean in tdd, `None` in description. `stray` holds edits
  outside `writable` (and outside `oracle` too in description shape). Empty
  lists mean **observed empty**; unobserved values on an early failure are
  `None`.
  **`dropped` is spelled out here rather than deferred to the PRD** (blocker
  fix, dispatch 1): it holds every writable path that the candidate did **not**
  change **and** whose vetted necessity `holds` is `true`. It is therefore a
  function of two inputs, `changed` and `vetting.json`'s `necessity` map, and
  `run_attempt` must read `vetting.json` to compute it — see the data path
  below. A writable path the engine left alone whose necessity did **not**
  hold is not `dropped`, which is what makes the PRD's
  "engine skips a non-load-bearing writable path -> `PASS` with `dropped`
  empty" scenario come out right.

`launch` semantics, pinned because they gate the only retry in the harness:
`"not-started"` requires a **positively observed** failure before the helper
process was created (`FileNotFoundError`/`PermissionError` from `Popen`).
Successful process creation is `"started"`, even when its engine child never
starts. A lost boundary record is `"unknown"`. **Only `"not-started"` can be
`harness`**; blank output or an absent identity never proves that state.

`classify` derives `(outcome, class)` from the record alone and **ignores any
stored `outcome`/`class`**. Precedence, first match wins:

1. `engine_run.timed_out` -> `("TIMEOUT", None)`
2. any of `baseline`, `gates.gate`, `gates.own`, `gates.ablate` with
   `timed_out` true -> `("SUSPECT", None)`
3. `prep.status == "PREP_MISMATCH"`, or baseline invalid/unrun -> `("DISCARDED", None)`
4. `validity != "VALID"` -> `("DISCARDED", None)`
5. candidate-behaviour violations, in this order -> `("FAIL", <class>)`:
   `test-mutation` (tdd, `oracle_intact is False`), `stray-edit`
   (`stray` non-empty), `no-edit` (`changed == []`), `dropped-a-file`
   (`dropped` non-empty), `vacuous-tests` (description,
   `gates.ablate` present and `gates.ablate["rc"] == 0`).
   **Every rung-5 predicate distinguishes `None` from empty** (blocker-adjacent
   fix, dispatch 1): a record whose snapshot never ran carries
   `changed: null`, and a naive `not changed` would score it `FAIL:no-edit` —
   a fabricated verdict about an engine that was never observed. `None` at any
   rung-5 input means that violation is **not** decidable, so the ladder falls
   through to rung 6 and the attempt is `SUSPECT`.
6. any **required** post-dispatch gate that is unrun (`None`), OR whose `rc` is
   `None`, OR whose `rc` is non-zero while `failure_kind` is anything other
   than `"test"` (i.e. `"tool"`, `"unknown"`, **or `None`**) ->
   `("SUSPECT", None)`.
   **The `failure_kind is None` case is included** (blocker fix, dispatch 3):
   a command result is contract-legal with `rc: 1, failure_kind: null`, and the
   dispatch-2 wording rejected only `"tool"` and `"unknown"`, so such a gate
   fell through to rung 8 and became `FAIL:logic-error` — a claim that the
   candidate failed the tests, made without any observed test failure. An
   unclassified failure is an unobserved one. The required set is
   `REQUIRED_GATES[shape]`:
   `("gate",)` for tdd, `("gate", "own", "ablate")` for description. `own` and
   `ablate` are never run in tdd, so treating them as required there would make
   **every** tdd attempt `SUSPECT`. Any rung-5 input still `None` at this point
   also lands here, **except** the two that are `None` by shape rather than by
   failed observation: `oracle_intact` in description, and `ablate` in tdd.
   Those are not missing observations; the shape defines them as inapplicable.
   **The `rc is None` clause is load-bearing** (blocker fix, dispatch 2): a
   command result is contract-legal with `rc: null`, and without this clause a
   gate that never produced a return code would sail past rung 6 into rung 7 or
   8 and be scored on evidence that does not exist.
7. `("PASS", None)` when `gates.gate["rc"] == 0` and, in description shape,
   `gates.own["rc"] == 0` and `gates.ablate["rc"]` is an `int` that is not `0`
   with `gates.ablate["failure_kind"] == "test"`.
   **`isinstance(rc, int)` is required for the ablation check**, not just
   `rc != 0`: in Python `None != 0` is `True`, so an unrun ablation would
   otherwise satisfy "the engine's test edits fail on the pre-task impl" and
   hand a `PASS` to a candidate whose vacuity was never tested. Rung 6 already
   catches this for the required set; the explicit type check is the second
   lock on the one comparison where the failure mode is a false `PASS`.
8. otherwise `("FAIL", "logic-error")`. Reachable only when every required gate
   ran, produced an integer `rc`, and failed with `failure_kind == "test"` —
   i.e. the candidate genuinely failed the tests.

`is_valid_baseline` is `rc is not None and rc != 0 and not timed_out and
failure_kind == "test"`. **No missing baseline can yield PASS.** All non-`FAIL`
outcomes carry `class is None`.

`derive_validity(record) -> str` owns the `validity` field (blocker fix,
dispatch 1); `classify` reads `record["validity"]` at rung 4, and
`run_attempt` calls `derive_validity` to fill it, so the claim "`classify`
derives outcome from the record alone" holds for the field it depends on.

**The rejection table is evaluated FIRST, and `VALID` is only what survives it**
(blocker fix, dispatch 3). The dispatch-2 draft tested the success conditions
first and reached the table only "otherwise", which let a helper that handles
its own termination — emits a final message and exits 0 after being timed out —
be called `VALID` despite an observed `timed_out`, and did the same for an
attempt with a failed prep or an invalid baseline. Order matters here precisely
because the success evidence is engine-reported and the rejection evidence is
harness-observed; the harness's own observations must win.

So: run rungs 1-7 below. If none matches, return `"VALID"` when **all** of
`launch == "started"`, `completion == "complete"`, and `final_message_bytes` is
an `int` **and** `> 0`; otherwise rung 8. The null guard on
`final_message_bytes` is load-bearing rather than decorative — the field is
contract-legal as `null` and `null > 0` raises `TypeError` in Python 3.
`"unchecked"` usage detection stays recorded as `"unchecked"` and is **not**
treated as clear.

The table is **total over the permitted domains** (blocker fix, dispatch 2) —
every legal combination of field values reaches exactly one arm, so no input
can fall through with no return value. First match wins:

| # | Condition | Reason |
|---|---|---|
| 1 | `prep.status == "PREP_MISMATCH"` | `prep` |
| 2 | baseline invalid or unrun (`not is_valid_baseline`) | `baseline` |
| 3 | `launch == "not-started"` | `harness` |
| 4 | `engine_run.timed_out` is true | `timeout` |
| 5 | `usage_limit == "hit"` | `usage-limit` |
| 6 | `exit` is an `int` and `exit != 0` | `exit-N` |
| 7 | `identity is None` | `identity` |
| 8 | anything else | `incomplete` |

Rung 8 is the catch-all that makes the mapping total, and it absorbs the two
cases the dispatch-2 review found had no home: `launch == "unknown"` with
otherwise complete evidence, and `launch == "started"` with `exit is None`.
Both are "the harness could not observe whether this run finished", which is
what `incomplete` means. `launch == "unknown"` never yields `harness`, per the
PRD — only a positively observed pre-creation failure does.

Note the consequence of table-first ordering: rungs 1, 2 and 4 (`prep`,
`baseline`, `timeout`) are *not* engine-reported, and they now pre-empt any
amount of well-formed helper output. That is the intended reading of the PRD's
own precedence, where `TIMEOUT` and the prep/baseline discards sit above the
validity check in `classify` too.

### `eval_harness/attempt.py`

```python
@dataclass(frozen=True)
class AttemptPlan:
    task_id: int
    slug: str
    spec: Spec
    shape: str
    engine_id: str
    engine_command: str
    attempt_no: int                    # 1 or 2
    evidence_dir: Path
    run_dir: Path                      # runs/<run-id>/
    attempt_dir: Path                  # runs/<run-id>/<n>-<engine>-a<k>/
    template_dir: Path
    template_sha: str
    prompt_path: Path                  # the task's single prompt file
    writable: tuple[str, ...]
    oracle: tuple[str, ...]
    pretask: dict                      # parsed pretask.json
    necessity: dict[str, dict]         # vetting.json["necessity"]
    bound_s: float
    gate_bound_s: float
    settings: EngineSettings


def vet(evidence_dir: Path, gate_bound_s: float) -> int: ...

def verify(evidence_dir: Path) -> int: ...

def run(evidence_dir: Path, run_id: str, engines: list[str], shape: str,
        bound_s: float, gate_bound_s: float, *, alternate: bool,
        retry_discarded: str, settings: EngineSettings,
        config: dict) -> int: ...

def run_attempt(plan: AttemptPlan) -> dict: ...
```

`run_attempt` takes **one frozen `AttemptPlan`** rather than eighteen
positional arguments (blocker fix, dispatch 1). Two reasons beyond taste: the
50-line function cap makes a long parameter list expensive at every call site,
and `necessity` — the input `dropped` needs — is easy to forget when it is one
argument among many but impossible to omit when the plan is constructed once.
`run` builds one `AttemptPlan` per (task, engine, attempt) and is the only
constructor. It returns the completed `attempt.json` dict; `run` writes it.

Both `vet` and `run` return a process exit code (`0` success, non-zero with a
diagnostic on stderr).

**`attempt.py` intra-module decomposition**, each function under the 50-line
cap, the file under the 400-line package cap:

| Function | Lines (est.) | Owns |
|---|---|---|
| imports, `AttemptPlan` declaration, module constants | ~45 | the 17-field frozen dataclass is itself ~25 lines |
| `vet` | ~40 | drive the vet checks, write `vetting.json` and `ready` |
| `_vet_checks` | ~45 | warmup, baseline, canonical, necessity per path |
| `_seal_inputs` | ~45 | `template/`, `pretask.json`, `manifest.json`, `canonical.patch`, `oracle/`, sealed prompts, `inputs_sha256` |
| `verify` | ~45 | re-validate every record, re-check `inputs_sha256` and manifest |
| `run` | ~45 | validate flags, re-check seals, build `run.json`, iterate, retry, `complete.txt` |
| `_plan_attempts` | ~35 | ordering incl. `--alternate`, `AttemptPlan` construction |
| `run_attempt` | ~45 | steps 1-9 as calls; no logic of its own |
| `_prepare_clone` | ~45 | clone, `mise_trust`, prep proof, tdd overlay, `sealed.json` |
| `_write_records` | ~30 | `derive_validity`, `classify`, `validate_record`, atomic write |

Estimated total ~420 lines, still over the 400 cap even after `gates.py`
already took the baseline, gate and candidate-observation functions (~110
lines). `verify` and `_seal_inputs` (~90 lines together, and both are about the
evidence bundle rather than an attempt) move to **`eval_harness/evidence.py`**,
leaving `attempt.py` at ~330.

`runner.py` gets its own estimate rather than riding on `attempt.py`'s
(dispatch-2 non-blocker): `CommandResult` + `classify_failure` + `run_bounded`
+ `reap` + `run_segments` + `gate_lock` ≈ 230 lines, and the Win32 structures
(`JOBOBJECT_EXTENDED_LIMIT_INFORMATION`, `THREADENTRY32`), the
`CreateJobObject`/`Assign`/`Terminate`/`Query` wrappers and `resume_process`
≈ 190 more. Together they exceed the cap, so the Windows half lives in
**`eval_harness/win32.py`**, imported lazily and only on `os.name == "nt"`.

**Module count, stated once so the doc stops disagreeing with itself**
(dispatch-2 non-blocker): the package holds **twelve** files —
`__init__.py`, `spec.py`, `prompts.py`, `runner.py`, `win32.py`, `trees.py`,
`engines.py`, `events.py`, `gates.py`, `attempt.py`, `evidence.py`,
`records.py` (eleven code modules plus the package marker). Every count elsewhere in this document defers to this one. The
number is a consequence of the 50-line function cap and the 400-line file cap
applied to the contracts the PRD fixes, not a preference for small files.

### `run_eval_harness.py` CLI

```
run_eval_harness.py vet <evidence-dir> [--gate-bound SECONDS]
        [--shapes description[,tdd]]
run_eval_harness.py verify <evidence-dir>
run_eval_harness.py run <evidence-dir> --run-id ID --engines a[,b]
        --shape description|tdd --bound S --gate-bound S
        [--alternate] [--retry-discarded harness-only|none]
        [--server-reasoning-effort LABEL]
        [--qwen-provider P] [--qwen-model M] [--sonnet-model M]
        [--usage-limit-cmd PATH]
```

`--gate-bound` defaults to `1800` and must be a positive number; `run` refuses
when its `--gate-bound` differs from the vetted `vetting.json.gate_bound_s`,
naming the re-vet remedy. `run` refuses an existing
`runs/<run-id>/` directory rather than overwrite evidence. `--retry-discarded`
defaults to `none`. Engine ids are `qwen`, `sonnet`, or `cmd1`/`cmd2` by
argument position; artifact directory names use ids, never raw executable
paths.

### `vet` outputs

`template/` (the tree at `first^`, with its own single-commit history),
`pretask.json` (`PRETASK_KEYS`), `manifest.json` (the full tree manifest),
`canonical.patch` (`git diff <first>^ <last> -- <writable...>`),
`oracle/<relpath>` copies taken from `<last>`, `prompts/<shape>.txt` (the
sealed rendered prompts), `vetting.json` (`VETTING_KEYS`), and a `ready` marker
written **only** when every gating check passed.

**`vet` seals every input the run later consumes, not just the tree** (blocker
fix, dispatch 2). Without this, `spec.json`, `dispatch-references.json` or an
oracle file could be edited between `vet` and `run`, and the run would score a
task against a prompt and an oracle that were never qualified — while the
`ready` marker still said the task was sealed. That is the exact failure class
the PRD exists to eliminate. So:

- `vet` takes **`--shapes description[,tdd]`** and renders exactly the shapes
  asked for, defaulting to every shape the spec supports (`description`
  always; `tdd` only when the spec carries `architecture`, `invariants` and
  `read_anchors`). The flag exists because the tdd dispatch references are
  mandatory *for tdd*, and without it a tdd-capable spec with no
  `dispatch-references.json` could not be vetted for `description` either
  (blocker fix, dispatch 3) — the reference requirement is scoped to the
  shapes being qualified, not to the spec's capabilities.
- `vetting.json` gains `inputs_sha256`: a map from a fixed label to a lowercase
  sha256 — `"spec"` (the raw `spec.json` bytes), `"dispatch_references"` (the
  raw file bytes, or `"absent"`), `"canonical_patch"`, `"manifest"`,
  `"oracle"`, and `"prompt:<shape>"` for each rendered shape.
  **`"oracle"` is in the list** (blocker fix, dispatch 3): without it, replacing
  an oracle file after vetting would simply be blessed by the attempt's own
  fresh `sealed.json`, and the observing tests — the whole point of the
  exercise — would be the substituted ones. It digests the sorted
  `<relpath>\0<sha256>\n` lines of every file under `oracle/`, so both a content
  change and an added or removed oracle file move it.
- `run` recomputes all of them before its first dispatch and **refuses**,
  naming the changed label and re-vetting as the remedy, on any mismatch. `run`
  copies the sealed `prompts/<shape>.txt` into each attempt directory; it never
  re-renders. It also copies `inputs_sha256` to
  `runs/<run-id>/sealed-inputs.json`, so a completed run carries its own record
  of the bundle it consumed and `verify` can check that run against the bundle
  it actually used rather than whatever the shared directory holds now.
- **`vet` refuses an evidence directory that already contains a `runs/` entry**
  (blocker fix, dispatch 3), naming a fresh evidence directory as the remedy.
  Re-vetting rewrites `vetting.json`, `oracle/`, `prompts/`, `manifest.json`
  and `canonical.patch` in place; doing that under completed runs would
  silently invalidate their evidence while `complete.txt` still claimed they
  were sound. Write-once has to mean the whole bundle, not just the records.
- So `VETTING_KEYS` is
  `("template_sha", "gate_bound_s", "warmup", "baseline", "necessity",
  "canonical", "inputs_sha256", "shapes", "ready")`, where `shapes` is the
  sorted list of shapes sealed. This extends a file the PRD does not fix the
  key set of (unlike `pretask.json`), so nothing downstream breaks.

Checks, all recorded:

- **warmup** — each warmup segment on a fresh clone.
- **baseline** — oracle overlaid on a fresh clone; must exit non-zero with
  `failure_kind == "test"`. A tool error or an unrecognised failure fails the
  check.
- **canonical** — `canonical.patch` applied to a fresh clone, oracle overlaid;
  must exit 0.
- **necessity**, per writable non-test path — canonical minus that path;
  records `holds: true` only for a non-zero result with `failure_kind ==
  "test"` and `timed_out` false. Tool/unknown failures cannot establish
  necessity. Necessity results are **informational** and never block `ready`.

A failed warmup, baseline or canonical check exits non-zero naming the check
and writes no `ready` marker. **Failed re-vetting removes any pre-existing
`ready` marker before running**, so a previously-good task cannot stay ready on
a stale marker.

### `run` per-attempt sequence

**Directory layout inside an attempt** (blocker fix, dispatch 3). The clone and
the attempt's own artifacts are **separate directories**: putting `sealed.json`,
`prompt.txt` and the command outputs in the same directory as the working tree
would make `git status --porcelain` dirty at the very moment the design proves
it clean, and would drag those files into `snapshot`'s candidate diff.

```
runs/<run-id>/<n>-<engine>-a<k>/     # attempt dir: records and raw outputs only
    clone/                            # the dispatch working tree
    baseline-clone/                   # this attempt's own baseline tree
    gate-clone/ own-clone/ ablate-clone/
    attempt.json prompt.txt out.txt wrapper.txt session.jsonl status.txt
    sealed.json diff.patch progress.log *.txt *.rc
```

`attempt.json`'s `clone` field is the absolute path of `<attempt-dir>/clone`.
The harness writes nothing into a `*-clone/` directory except the tree content
it is supposed to contain.

1. `fresh_clone(template)` -> `<attempt-dir>/clone`; `mise_trust`.
2. Pre-dispatch proof against `pretask.json` and `manifest.json`
   (`prove_state`). Mismatch records `PREP_MISMATCH` and **nothing is
   dispatched**.
3. Baseline gate in its own fresh clone `<attempt-dir>/baseline-clone`, **for
   every attempt, never reused**. A pass, tool error or unrecognised failure
   prevents dispatch and records `DISCARDED:baseline`; a baseline **timeout**
   prevents dispatch and records `SUSPECT`.
4. `tdd` only: `overlay_oracle` into the dispatch clone and `commit_all` that
   overlay in the clone's private history. `description` leaves the template
   unchanged. Write `sealed.json` (`SEALED_KEYS`) hashing the **post-overlay**
   state, into the attempt dir, never into the clone.
5. Prove HEAD, clean status and hashes against `sealed.json` immediately before
   launch, plus the **expected post-overlay manifest** (blocker fix, dispatch
   3). That manifest is *derived, not observed*: take `manifest.json` and
   replace each oracle path's entry with the hash of the vetted
   `oracle/<relpath>` copy. Both inputs are sealed, so the expectation is
   computable before the overlay happens — which is what makes it a proof
   rather than a restatement of whatever the tree now contains. Reusing the
   unmodified `manifest.json` here would reject every legitimate tdd overlay;
   skipping the manifest here would reopen the ignored-file gap at the one
   moment that matters most, immediately before the engine runs. In
   `description` shape the expected manifest is `manifest.json` unchanged.
   Historical provenance stays `pretask.json`; candidate edits and oracle
   integrity are measured against `sealed.json`, never `first^`.
6. Dispatch with the clone as cwd, bounded by `--bound`. Surviving descendants
   after termination stop the run with `HALTED:orphans`.
7. `snapshot` against the sealed dispatch SHA. Harness test overlays never
   appear in `changed`, `stray` or `diff.patch`.
8. Gates, each inside `gate_lock`, **one at a time**, under `--gate-bound`.
   The reconstruction order is pinned (blocker fix, dispatch 2) — "oracle
   re-copied first" was ambiguous and, read as *first*, lets the candidate's
   own test hunks land on top of the observing tests, so a description-shape
   candidate could pass tests it had weakened, or the patch could conflict:

   | Gate | Reconstruction, in order |
   |---|---|
   | `gate` | `fresh_clone(template)` -> `<attempt-dir>/gate-clone` -> tdd only: `overlay_oracle` + `commit_all` -> `apply_patch(diff.patch, exclude=oracle)` -> **`overlay_oracle` again, last** -> run |
   | `own` | `<attempt-dir>/clone` exactly as the engine left it; no clone, no patch, no overlay |
   | `ablate` | `fresh_clone(template)` -> `<attempt-dir>/ablate-clone` -> `apply_patch(diff.patch, exclude=writable)` -> run |

   The candidate's test hunks are **excluded from the patch** for `gate` and
   the vetted oracle is copied **last**, so the observing tests are
   authoritative by construction and no conflict is possible — rather than
   applied and then hopefully overwritten. `own` deliberately keeps the
   candidate's tests: it answers "did it pass on its own terms", which is only
   meaningful against the tree as left. `ablate` is the mirror: the candidate's
   test edits alone on the pre-task implementation, which must fail.
   `tdd` re-hashes the oracle paths in the dispatch clone against
   `sealed.json` to set `oracle_intact`.
9. `derive_validity`, `classify`, `validate_record`, then write `attempt.json`
   **atomically**: serialise to `attempt.json.tmp` in the same directory,
   `os.replace` onto the final name. A killed session therefore leaves either
   no `attempt.json` or a complete one, never a truncated file that a reader
   would parse as a finished attempt.

### Where `HALTED:orphans` is written

`HALTED:orphans` is a **run-level halt, not an attempt outcome**. The five-value
`outcome` enum and `validate_record` both stay closed; adding a sixth value
would break PRD 00052's reader. When `reap` reports survivors after termination
and the settle window:

1. `progress.log` gets a final line naming **which command** left survivors:
   `HALTED:orphans <attempt-dir> <engine|baseline|gate|own|ablate|warmup>`;
2. the in-flight attempt's `attempt.json` is written with its **observed**
   field values and classified normally;
3. `runs/<run-id>/halted.txt` is written with the reason, the attempt id, and
   the command name;
4. `run` returns a non-zero exit code and dispatches **no further attempt**.

**Step 2 does not fabricate a timeout** (blocker fix, dispatch 2). The
dispatch-1 draft forced `engine_run.timed_out` true and therefore
`outcome: "TIMEOUT"`, which invents an engine timeout that was never observed —
and is plainly false when it was a *gate* that leaked a child, or when the
engine was never launched at all. Observed flags are preserved and the PRD's
precedence decides the outcome; the orphan fact lives in `halted.txt` and
`progress.log`, which is where a run-level event belongs.

**A missing `halted.txt` does not mean the run finished** (blocker fix,
dispatch 2). A killed session leaves no marker of any kind, so absence proves
nothing. `run` writes `runs/<run-id>/complete.txt` as its **last** action,
only after every planned attempt has a durable `attempt.json` on disk; it holds
the attempt inventory (one `<n>-<engine>-a<k>` line each), the count and the
finish timestamp. The three states a reader must distinguish are therefore
positive in all three cases: `complete.txt` present (finished), `halted.txt`
present (halted, and why), neither present (interrupted — PRD 00052 renders it
as incomplete).

### Evidence durability and restore

An evidence directory is **irreplaceable**: re-running an engine cannot
reproduce a recorded observation, because the engine is non-deterministic and a
round costs about two days. It is therefore persistent data, and this section
is its backup-and-restore contract (cardinal-sin fix, dispatch 2 — the
dispatch-1 draft described persistent records with no durability story at all).

- **Write-once by construction.** `run` refuses an existing `runs/<run-id>/`
  rather than overwrite it; `vet` removes a stale `ready` marker before
  re-vetting rather than leaving a stale one; `attempt.json` is published with
  `os.replace`. Nothing the harness does overwrites or deletes a completed
  record, and the harness never invokes `rm`, `git reset --hard` or
  `git clean` — stale clones stay until an operator removes them.
- **Owner.** The solo maintainer running the round owns the evidence
  directory. Backing it up is an operator responsibility, not the harness's:
  the harness starts no daemon and writes nowhere but the evidence dir.
  The recommended unit is the whole `<evidence-dir>`, after `run` writes
  `complete.txt` and before the next round reuses the directory.
- **Tested restore check.** `run_eval_harness.py verify <evidence-dir>` is the
  restore procedure, and it is a real command rather than a prose promise. It
  re-reads every record under the directory, runs `validate_record` on each,
  recomputes `inputs_sha256` against the sealed inputs and `manifest.json`
  against `template/`, and prints one line per finding. It performs **no**
  network request, starts **no** engine, and writes nothing. Exit 0 means the
  evidence is internally consistent and complete; non-zero names the first
  inconsistency. A restored backup is proven restored when `verify` exits 0.
- **`verify` checks an inventory, not just the files it happens to find**
  (blocker fix, dispatch 3). Validating whatever is present would let a backup
  that lost an entire attempt directory pass, which is exactly the failure a
  restore check exists to catch. So `complete.txt` holds the run's attempt
  **inventory** — one line per attempt as `<n>-<engine>-a<k>` — plus the count
  and the finish timestamp, and `halted.txt` holds the same inventory for the
  attempts that completed before the halt. `verify` requires every listed
  attempt to have a directory with a valid `attempt.json`, and reports any
  extra attempt directory not on the list. It checks each run against that
  run's own `sealed-inputs.json` rather than the shared bundle, so a later
  re-vet in a different directory cannot make an old run look inconsistent.
  A run with neither marker is reported as **interrupted** — a distinct
  finding from **missing**, because the two need different responses.
- `*-clone/` directories under `runs/` are **not** part of the durable set:
  they are reconstructible from `template/` plus `diff.patch`, and are the bulk
  of the bytes. A backup may exclude the `*-clone/` directories specifically —
  not the attempt directories that contain them, which hold the records and the
  raw command outputs. `verify` does not require the clones.

`verify` is not renderer work and does not encroach on PRD 00052: it produces
no `evidence.md`, no `report.md` and no audit queue, only pass/fail lines
against contracts this PRD already defines.

### Per-attempt artifact set

`<attempt-dir>/` holds these **beside** the `*-clone/` directories, never
inside them (see the directory layout in "`run` per-attempt sequence"). In the
PRD's own list: `attempt.json`, `prompt.txt`,
`out.txt` (the helper's `-o` capture), `wrapper.txt` (full helper stdout and
stderr), `session.jsonl` when captured, `status.txt`, `diff.patch`,
`baseline.txt`/`baseline.rc`, `gate.txt`/`gate.rc`, `own.txt`/`own.rc` and
`ablate.txt`/`ablate.rc` (description shape only), `sealed.json`, and
`progress.log`. Every `<name>.txt` is the raw combined output of that command
and every `<name>.rc` is its integer exit status followed by a newline — the
same fact as the record's `CommandResult`, in a form a human can read without
parsing JSON. `status.txt` holds one line: `<outcome>` for a non-`FAIL`
attempt, `<outcome>:<class>` for a `FAIL`. A gate that did not run leaves no
`.txt`/`.rc` pair, which is the on-disk form of the record's `null`.

`--alternate` swaps which engine goes first on odd rows. Retry happens **only**
under `--retry-discarded harness-only`, **only** after `DISCARDED:harness`, at
most once, on a fresh clone `a2`; every other outcome is final. One `--bound`
and one `--gate-bound` govern the whole run; changing either means a new run
id. `progress.log` is appended after every step.

`run.json` carries `RUN_KEYS`: `schema_version` (`1`), `run_id`, `started` (UTC
ISO 8601), `config` (every resolved flag name to its JSON value, defaults
included), `engines` (ordered `{id, command}`), `tasks` (ordered
`{id, slug, repo, kind, writable, oracle, prompt_sha256}`; `id` the numeric
spec-directory prefix, paths slash-form repo-relative, `repo` an absolute
string), `versions`, `server` (`SERVER_KEYS`).

### `eval_harness_fixtures.py` and `fixtures/fake_engine.py`

```python
def build_fixture_repo(root: Path, *, change_test: bool = False) -> dict: ...
def write_argv_recording_stub(directory: Path, name: str, argv_file: Path, *,
                              exit_code: int = 0, stdout: str = "",
                              stderr: str = "") -> Path: ...
def fake_engine_command(mode: str) -> str: ...
```

`build_fixture_repo` creates a git repo with a base commit and a task commit
touching one impl file and one test file, and returns
`{"repo", "first", "last", "impl", "test"}`. With `change_test=True` the task
commit also edits the test file, which is the fixture that makes `pretask.json`
and `sealed.json` differ.

`write_argv_recording_stub` exists because the repo-root `conftest.py` fixture
`write_executable_stub` emits a single fixed `echo` line and has **no
argv-capture path** (`conftest.py:33-45`), while the adapter tests are defined
to assert argv byte-for-byte (blocker fix, dispatch 1). The new helper writes,
on POSIX, a `#!/bin/sh` body doing `printf '%s\n' "$@" > "<argv_file>"`; on
Windows, a `.cmd` body using the `:loop` / `echo %~1` / `shift` idiom, which
preserves one argument per line and survives spaces (`for %%A in (%*)` does
not). Like the conftest fixture, it returns the path `shutil.which` reports, so
Windows `%PATHEXT%` casing is handled rather than hand-spelled. It lives in the
test-only module rather than extending the shared repo-root `conftest.py`,
which every suite in the repo loads.

`fixtures/fake_engine.py` is driven by the `FAKE_ENGINE_MODE` environment
variable and takes the prompt file as its only argument. Modes, each producing
the named working-tree effect in its cwd:

| Mode | Effect |
|---|---|
| `pass` | writes the correct impl; the gate passes |
| `noop` | writes nothing, exits 0 with a final message |
| `stray` | writes the correct impl **and** a file outside `writable` |
| `drop` | leaves one load-bearing writable path untouched |
| `mutate-test` | rewrites the oracle test so its own run is green |
| `vacuous` | rewrites the test to assert nothing (description shape) |
| `hang` | spawns a grandchild that appends to a heartbeat file every 100 ms and sleeps 600 s, **then sleeps 600 s itself**, so the bound fires on the parent. The grandchild has no dependency on the parent's lifetime — killing the parent alone leaves it writing — but it does **not** call `setsid`, so it stays in the process group and is containable. See the group-scope limit and the bound-measures-the-parent note in `runner.py` |
| `spawn-and-exit` | writes the correct impl, spawns the same heartbeat grandchild, and exits 0 **immediately** — the clean-exit-with-leftover-child case that `reap` must handle without halting |
| `exit1` | edits nothing and exits 1 |
| `silent-edit` | writes the correct impl, prints **no** final message, exits 0 — the "started stub that must never be retried" case |

`fake_engine_command(mode)` returns the `cmd:<path>` string for that mode; the
`.py` suffix routes it through `sys.executable`, so it runs on every platform
without a shebang or an executable bit.

### `sonnet-run.sh -S/--session-id`

A new `-S|--session-id` case sets `SESSION_ID="$2"; shift 2`. In **prompt mode
only**, both `claude --print` call sites gain `${SESSION_ARGS[@]}` where
`SESSION_ARGS=("--session-id" "$SESSION_ID")` when `SESSION_ID` is non-empty
and an empty array otherwise. `interactive`, `resume` and `continue` modes are
**unchanged**. The usage block gains
`  -S, --session-id UUID  Pin the Claude session id (print mode only)`.
The array-expansion idiom must be `"${SESSION_ARGS[@]+"${SESSION_ARGS[@]}"}"`,
matching the existing `_DIRS` idiom in `test_sonnet_run.sh`, because the script
runs under `set -u` and macOS bash 3.2 treats an empty array as unset.

### `mock-llama-server.py` `/props`

`do_GET` gains a branch for `self.path.rstrip('/') == '/props'` returning a
sanitized real-shape payload:

```json
{"default_generation_settings": {"n_ctx": 131072,
   "params": {"temperature": 0.7, "top_k": 20, "top_p": 0.8, "min_p": 0.0}},
 "model_alias": "mock-candidate", "build_info": "mock-b0000",
 "chat_template_caps": {"supports_reasoning_effort": true}}
```

No credential, hostname or personal path appears in it. `/v1/models` and
`/v1/chat/completions` behaviour is untouched.

## Data flow

```
spec.json ─load_spec─> Spec ─classify_paths─> writable[], oracle[]
                                   │
repo@first^ ─build_template─> template/ (+ template_sha)
                                   │
   vet: fresh_clone ×N ─run_segments─> warmup / baseline / canonical / necessity
                                   └─> pretask.json, canonical.patch, oracle/,
                                       vetting.json, ready

   vet: Spec + shape + dispatch-references.json ─render_prompt─>
                              prompts/<shape>.txt   (sealed, one per shape)
                                            │ inputs_sha256 recorded
   run: re-check inputs_sha256 ─────────────┤ (refuse on mismatch)
             │                              ▼ sealed bytes copied per engine
        vetting.json ──necessity map──┐        (run NEVER re-renders)
        fresh_clone(template) ─prove_state(pretask + manifest)─> prep
             │                        │                 │ ok
             ├─ fresh_clone ─run_segments─> baseline (own clone, per attempt)
             ├─ tdd: overlay_oracle + commit_all ─> sealed.json ─prove_state
             ├─ dispatch(engine) ─run_bounded─> wrapper.txt, out.txt, session.jsonl
             │        ├─ read_events ─> completion, first_edit_s, usage
             │        └─ ProcessTree.terminate/survivors ─> HALTED:orphans
             ├─ snapshot(sealed_sha) ─> changed[], diff.patch
             │        └─ changed + necessity ─> dropped[]
             └─ gates (inside gate_lock, one at a time):
                  fresh_clone + apply_patch ─run_segments─> gate / own / ablate
                                   │
       derive_validity(record) ─> classify(record) ─validate_record─> attempt.json
```

`run.json` is written once at run start (config, engines, tasks, versions,
server); `attempt.json` once at each attempt's end; `progress.log` after every
step, so a killed session leaves complete records for finished attempts and no
`attempt.json` for the one in flight — exactly what PRD 00052 renders as
incomplete.

## Reuse inventory

- **Test-path classification** — `<autopilot-plugin-root>/skills/work/scripts/work_routing.py:233`
  `is_test_path`, with `_TEST_DIR_SEGMENTS` (line 72) and `_TEST_BASENAME_GLOBS`
  (line 88). **Read, not imported.** It lives in a versioned plugin cache whose
  path changes on every release, and AGENTS.md forbids pointing at a plugin
  skill by filesystem path. The rule set is transcribed into `spec.py` and
  pinned by a test that enumerates every segment and glob, so drift is visible
  as a test failure rather than an import error.
- **Usage-limit detection** — `<autopilot-plugin-root>/skills/run-autopilot/scripts/detect_usage_limit.py`
  (a shim over `cli/usage_limit.py`). Contract read from source:
  `[--log PATH] <cwd> [projects_root]`, `--log` alone is valid, **exit 0 means
  limit-stuck**. Invoked as a subprocess by path when `--usage-limit-cmd` names
  it or the plugin cache holds it; never imported.
- **Mock llama server** — `skills/use-qwen/scripts/mock-llama-server.py`.
  Reused and extended with `/props` (PRD-mandated). Its call contract is
  `python3 mock-llama-server.py <port> <mode-file> <model-id>...`; both
  `test_qwen_run.sh` (copies it) and `test_eval_automation.sh` (runs it in
  place) already drive it, and neither requests `/props`.
- **Host-portability fixtures** — repo-root `conftest.py`:
  `write_executable_stub` (resolves through `shutil.which`, so Windows
  `%PATHEXT%` casing is handled), `isolate_home` (sets `USERPROFILE`/
  `HOMEDRIVE`/`HOMEPATH` too, which `HOME` alone does not do on Windows),
  `run_resolved_tool`, `deny_access`. The adapter and transcript-lookup tests
  use all four rather than hand-rolling stubs.
- **Shell test-harness idiom** — `skills/use-sonnet/scripts/test_sonnet_run.sh`
  already stubs `claude` on PATH, captures argv to `$CLAUDE_ARGV_FILE`, and
  ships `argv_has_pair`. The `-S` cases extend that file in place; no new
  harness is written.
- **Nothing found for a bounded process-tree runner.** Greps tried across
  `skills/`, `src/`, `scripts/`: `start_new_session`, `killpg`, `setsid`,
  `process group`, `preexec_fn` — one hit, in a `docs/plugin-skills/` prose
  file. Control search proving the pattern works: `subprocess.run(`,
  `TimeoutExpired`, `git archive`, `shutil.copytree` returned eight files
  (`sweep.py`, `funnel.py`, `trash_untracked.py`, `collect_facts.py`,
  `purge_devlocal.py`, `distil.py`, `collect.py`, `audit_qwen.py`). The
  closest existing helper, `sweep.py:182 _run_rg`, is a plain bounded
  `subprocess.run` with no process-group handling. `runner.py` is net-new.
- **Nothing found for git tree sealing / hash proofs.** Same control search;
  no `git archive` call exists anywhere in the repo. `trees.py` is net-new.
- `~/.claude/rules-library/rationalizations.md` was **not** present, so the
  synonym sets above are the verb/noun pairs chosen here (run/dispatch/execute/
  spawn; bound/timeout/deadline/limit; clone/copy/snapshot/archive;
  classify/route/match/predicate).

## Alternatives considered

**A. Smallest diff: one module, no package.** Put `vet` and `run` in a single
`run_eval_harness.py` with the fixture engine beside it. Rejected on a hard
constraint, not taste: the contracts alone (spec validation, four record
schemas, the eight-step classification ladder, two prompt shapes, three engine
adapters, cross-platform process-tree termination) do not fit under the 800-line
file cap the style gate enforces, let alone the PRD's own 400. The split is
forced by the rules already in effect.

**B. Chosen: the twelve-file package enumerated in "Module count" above,
portable copy only, no APFS clone.** The
PRD marks APFS clone-copy an *optional* optimization with a portable
directory-copy fallback. Only the fallback is built: `shutil.copytree(
symlinks=True)` is one stdlib call, has the byte and symlink semantics the PRD
requires, and works identically on both CI platforms. A `cp -c -R` fast path
would add a darwin-only branch, a filesystem-capability probe, and a second
code path to test, to save wall-clock on trees the fixture suite never has.
**What the extra size over option A buys:** each contract gets a file small
enough to hold one idea, and `records.py` — the surface PRD 00052 and PRD 00050
read — is pure and importable without touching git, subprocesses or the
network. **Upgrade path if it ever matters:** add the clone attempt inside
`fresh_clone` with the `copytree` call as its `except` branch; no caller
changes, and `# ponytail: portable copy only, APFS clone if round wall-clock
matters` marks the spot.

**C. Import `work_routing.is_test_path` from the autopilot plugin cache.**
Would guarantee the two predicates never drift. Rejected: AGENTS.md forbids
naming a plugin skill by filesystem path because the versioned cache path
changes on every release, and this repo must stay runnable on Codex and Copilot
where no plugin exists at all. Transcribing the rules and pinning them with an
enumerating test converts a runtime import failure into a visible test failure,
which is the better trade here.

**D. Enumerate surviving processes with `pgrep`/`wmic`, or key the Windows
check on `taskkill /T /F`.** Both rejected. `pgrep` does not exist on Windows
and `wmic` is deprecated there. `taskkill /T` is worse than merely
platform-bound: it walks the **live** parent/child links, so once the direct
child has exited — exactly what the PRD's `hang` fixture arranges, since its
grandchild must outlive its parent — it reports "not found" while the orphan
runs on, and a check keyed on that exit status would certify a dirty tree as
clean. The chosen design uses the real analogue on each platform: a process
group on POSIX (`os.killpg(pgid, 0)`, which grandchildren inherit) and a Job
Object on Windows (membership set at creation, survives the parent's death),
both through the stdlib. `taskkill` is **not** retained even as a fallback
(corrected at dispatch 3, where `runner.py` and this section had drifted
apart): a failure to create or assign the job halts the run outright, because a
host that cannot contain a child cannot produce trustworthy evidence for any
later attempt either. Separately, the *regression test*
proves descendant death by watching the descendant's own heartbeat file stop
growing, which needs no process enumeration on either platform and therefore
needs no Windows skip.

## Risks & edge cases

- **`bash -lc` on Windows.** Every `raw_test_cmd` and `warmup` segment runs
  through Bash, which PRD 00044 established is present in this repo's Windows
  CI. A login shell there is slower and reads a different profile than on
  macOS; the fixture commands are single `python -m pytest` invocations, so the
  exposure is startup latency, not semantics. If Git Bash proves absent on a
  future runner, `run_segments` is the single choke point to change.
- **`git init` identity.** CI runners carry no global git config, so a bare
  `git commit` in `build_template` or `commit_all` fails with "Please tell me
  who you are". Every history-writing invocation passes
  `-c user.name/-c user.email/-c init.defaultBranch` explicitly. This is the
  most likely first CI failure and the cheapest to get wrong.
- **`mise trust` on a host without mise.** Recorded and ignored, never raised.
  A template whose `first^` tree carries a `.mise.toml` will still run its
  commands; only the trust step is skipped.
- **Old task-start trees.** Dependency locks from `first^` may fail to resolve.
  `vet` disqualifies such a task at **warmup**, before it can be scored,
  matching PRD 00050's rule. The failure surfaces as `failure_kind: "tool"`,
  which is exactly why tool markers are tested before test markers.
- **Record contract drift.** PRD 00052 and PRD 00050 read `attempt.json`. The
  key sets live in `records.py` as module constants and `validate_record`
  refuses **extra** keys as well as missing ones, so an additive change breaks
  a test rather than silently reaching a downstream reader.
- **`--gate-bound` divergence between `vet` and `run`.** A run whose gate bound
  differs from the vetted one would score against a different deadline than the
  one the baseline was established under. `run` refuses up front and names
  re-vetting as the remedy.
- **Suite runtime budget.** The PRD demands the whole suite in under 60 s with
  no server and no network. The two costs that can blow it are the `hang`
  fixture (bounded by `--bound 2` in tests, plus the escalation window, which
  is a parameter precisely so a test can set it to milliseconds instead of
  waiting out the 60 s production default) and `bash -lc` startup per segment.
  Both are pinned by a timing assertion in the end-to-end suite.
- **The Windows job-object branch is unexercised in this repo today.** `ctypes`
  against `kernel32` is stdlib and needs no extra dependency, but the repo's
  `jobs.windows` CI job has never run on a runner: PRD 00044 stalled before its
  remote-evidence phase because `origin/master` is 98 commits behind local.
  So the Windows termination path ships **written but unproven on a real
  runner**, and the first Windows CI run after the push is where it gets its
  first real test. This is stated rather than hidden: the alternative
  (`taskkill /T /F` keyed on the direct child) is not merely unproven but
  **known wrong** for the orphaned-grandchild case the PRD's own fixture
  produces, so the job object is the right code to ship untested here.
- **Likely next changes this design must not box in.** (1) PRD 00052's
  renderer reads these records — hence `records.py` is pure and depends on no
  other module in the package. (2) PRD 00050's Ivan-shape comparison needs a
  third prompt shape — hence `render_prompt` takes `shape` as a parameter and
  the shapes are data-driven, not two forked functions. (3) A real round will
  want resume-after-kill — `progress.log` and per-attempt directories already
  make an attempt's completion observable, but **nothing resumes today**, and
  `run`'s refusal to reuse a run directory is what a resume feature would have
  to negotiate first. That refusal is deliberate (evidence integrity beats
  convenience) and is the one place this design knowingly constrains a likely
  successor.
- **`--server-reasoning-effort` is a declaration.** `/props` reports
  `supports_reasoning_effort` capability, never the effort actually applied.
  The field is named `declared_effort` in the record so no later reader can
  mistake it for a measurement.

## Test strategy outline

Five suites under `skills/use-qwen/scripts/`, all collected by
`uv run pytest skills/use-qwen/scripts -q`, plus the extended shell suite.

- **`test_eval_spec.py`** — every pinned test-path segment and glob enumerated;
  writable/oracle overrides; each invalid field type failing and naming its key;
  command-list validation (empty list, non-list, empty string, non-string
  element); `kind` derivation and the inconsistent-`kind` rejection;
  `reading_budget_tokens` bounds. Both prompt shapes asserted **byte-exact**
  against fixtures that include architecture, ordered read anchors and the
  reading budget, with `task_text`/pins absent in tdd; one test asserts the two
  engines' prompt copies have equal SHA256.
- **`test_eval_trees.py`** — `vet` on the fixture repo writes `pretask.json`,
  `canonical.patch`, `oracle/`, `vetting.json` and `ready`; baseline records a
  non-zero rc with a pytest failure line; canonical records 0; necessity
  `holds` for the impl path; a spec whose canonical patch fails the gate exits
  non-zero and writes no `ready` marker **including after a previously
  successful vet**; invalid bounds rejected; every vet stage obeys the pinned
  bound. A fixture whose test file changed between `first^` and `last` proves
  `pretask.json` and `sealed.json` differ and both survive. Runner cases:
  segment list stops at the first non-zero; one deadline spans the list;
  `classify_failure` maps tool errors before test failures.
- **`test_eval_engines.py`** — exact argv for both real adapters against
  `write_executable_stub` stubs of `qwen-run.sh`, `sonnet-run.sh`, `pi` and
  `claude`; `PI_CODING_AGENT_SESSION_DIR` present in the child env; identity
  parsed from `wrapper.txt`; transcript lookup by uuid under a temporary
  projects root (`isolate_home`); `usage_limit: "unchecked"` with no checker
  configured, `"hit"` on a checker exiting 0, `"clear"` on non-zero;
  `server_root` on `/v1`, `/proxy/v1/` and a bare root; nested `n_ctx`
  extracted from the mock `/props`; missing metadata yields nulls plus a
  `metadata_error`. Event fixtures prove completed-message detection,
  first-edit timing, once-per-message usage accounting, and that an incomplete
  or malformed stream can never read as complete. A fake-only run asserts no
  network request and no real-CLI probe.
- **`test_eval_records.py`** — the exact key set of every record kind, missing
  **and** extra keys both refused; a `kind` outside `RECORD_KINDS` refused; the
  full `classify` precedence ladder, one case per rung; `is_valid_baseline`;
  `classify` re-derives outcome and class while the stored values say the
  opposite. Null-versus-empty: `changed: null` scores `SUSPECT`, `changed: []`
  scores `FAIL:no-edit`; the same pair for `stray` and `dropped`.
  `REQUIRED_GATES`: a tdd record with `own`/`ablate` null is **not** `SUSPECT`,
  a description record with the same is. `derive_validity` on a record whose
  `final_message_bytes` is `null` returns `DISCARDED:incomplete` and does not
  raise; one case per reason in the precedence order; plus a **totality** test
  enumerating the cross product of the permitted domains for `launch`, `exit`,
  `completion`, `final_message_bytes`, `identity` and `usage_limit`, asserting
  every combination returns `"VALID"` or a reason from the closed set — with
  `launch="unknown", exit=0` and `launch="started", exit=null` named
  explicitly, since neither had a home before the dispatch-2 fix.
  Gate-`rc` cases: a description record with
  `ablate.rc = null, failure_kind = "test"` scores `SUSPECT`, **never** `PASS`;
  a tdd record with `gate.rc = null, failure_kind = null` scores `SUSPECT`,
  never `FAIL:logic-error`. Shape-inapplicable nulls do not trip the
  missing-observation rung: description's `oracle_intact: null` and tdd's
  `ablate: null` both still reach `PASS` when everything else is clean.
  Field shapes: a record with `task: "3"` instead of `3`, or a
  non-ISO-8601 `started`, is refused by `validate_record`; `changed[].status`
  accepts `M`, `A`, `D`, `R100` and `C75` and refuses `MM` and `Z`, with
  `old_path` required for `R`/`C` and refused otherwise; a tdd record with
  `oracle_intact: null` after an early failure validates.
  Dispatch-3 additions: `derive_validity` returns `DISCARDED:timeout` for a
  record with perfect helper evidence (started, complete, non-empty final
  message, exit 0, identity present) **and** `engine_run.timed_out` true —
  the self-terminating-helper case — and likewise `DISCARDED:prep` and
  `DISCARDED:baseline` when those conditions hold alongside perfect helper
  evidence; a required gate with `rc: 1, failure_kind: null` scores `SUSPECT`,
  never `FAIL:logic-error`.
- **`test_run_eval_harness.py`** — end-to-end on the fixture repo with `cmd:`
  engines, both shapes: `pass`->`PASS`; `noop`->`FAIL:no-edit`;
  `stray`->`FAIL:stray-edit`; `mutate-test` under tdd ->`FAIL:test-mutation`
  with its `gate` run on the re-copied oracle; `drop`->`FAIL:dropped-a-file`;
  `vacuous` under description ->`FAIL:vacuous-tests`; `hang` with `--bound 2`
  ->`TIMEOUT`, the descendant's heartbeat file stops growing, and the run
  continues; `exit1`->`DISCARDED:exit-1` with **no** retry. A stub that fails
  before process creation ->`DISCARDED:harness` plus exactly one `a2` retry; a
  started stub that edits then exits silently is **never** retried, including
  at exit 0 and with identity absent. A clone altered before dispatch records
  `PREP_MISMATCH` with no engine run; invalid and unrun baselines cannot pass;
  baseline and gate timeouts yield `SUSPECT`; tdd overlays never appear as
  candidate changes.
  **Two of the PRD's "impossible by construction" tests are rewritten to
  observe execution rather than metadata** (blocker fix, dispatch 2), because
  the dispatch-1 versions would pass against a harness that merely copied a
  file or wrote a shared config field:
  - *A baseline shared across attempts.* Asserting "each attempt directory
    holds its own `baseline.rc`" passes if the harness copies one file into
    two directories. Instead the fixture's baseline command appends its own
    `$PWD` and a nanosecond timestamp to a shared log outside the clones; the
    test asserts the log holds exactly one line per attempt **including the
    `a2` retry**, all with distinct cwds, and that each cwd matches that
    attempt's own `<attempt-dir>/baseline-clone` directory.
  - *Two engines of one run under different bounds.* Asserting that
    `run.json`'s `config.bound` is a single value passes if the dispatcher
    ignores it; so does asking the engine to report the deadline it was handed,
    since an adapter can report one number and enforce another (blocker fix,
    dispatch 3). The bound is therefore measured **at the point of
    enforcement**: both engines run the `hang` mode under `--bound 2`, and the
    test asserts both attempts are `TIMEOUT` and both `engine_run.wall_s`
    values sit inside the same narrow window around 2 s — the observable
    consequence of the bound, which no reported field can fake.
  Three cases added by the dispatch-1 blocker fixes: (a) **gate concurrency** —
  a `cmd:` gate command asserts `<run_dir>/.gate-in-flight` names only its own
  label, and a directly-nested `gate_lock` raises `GateConcurrencyError`, so
  "one at a time" is enforced rather than asserted; (b) **`dropped` from
  necessity** — the PRD's scenario where the engine passes the gate without
  touching a non-load-bearing writable path yields `PASS` with `dropped`
  empty, alongside the `drop` mode's `FAIL:dropped-a-file` on a path whose
  necessity held; (c) **`HALTED:orphans`** — with `survivors()` stubbed true,
  `halted.txt` is written, the run stops dispatching, and `attempt.json` still
  validates against the closed five-value `outcome` enum.
- **`test_eval_evidence.py`** (new suite for the dispatch-2 fixes) — `vet`
  writes `manifest.json`, `prompts/<shape>.txt` and `inputs_sha256`, and seals
  `tdd` only when the spec supports it; editing `spec.json`,
  `dispatch-references.json`, an oracle file or `canonical.patch` after `vet`
  makes `run` refuse, naming the changed label; an ignored file added to a
  clone (invisible to `git status --porcelain` and to both path maps) still
  produces `PREP_MISMATCH` via the manifest; a template carrying a symlink with
  an absolute target, and one whose target escapes the tree, are both rejected
  at `build_template`; `overlay_oracle` and `apply_patch` refuse a `..` path.
  `verify` exits 0 on a good bundle and non-zero, naming the first
  inconsistency, on a truncated `attempt.json`, a mutated sealed input, and a
  run directory with neither `complete.txt` nor `halted.txt` (reported as
  *interrupted*, distinct from *missing*). A tdd spec with
  no `dispatch-references.json`, with an empty array, with a missing `ivan`
  entry, with duplicate names, and with a name colliding with `pi`/`claude` are
  each refused **when tdd is among `--shapes`**; the same spec vetted and run
  with `--shapes description` succeeds, which is the case the shape flag
  exists for.
  Dispatch-3 additions: a **real backup-and-restore case** — copy a completed
  evidence dir, delete one attempt directory from the copy, and assert `verify`
  fails naming that attempt (the inventory check; validating only what is
  present would pass); replacing an `oracle/` file after `vet` makes `run`
  refuse on the `oracle` label; `vet` refuses outright on an evidence dir that
  already holds a `runs/` entry; a tdd attempt's post-overlay proof passes
  against the **derived** expected manifest and fails when an unrelated ignored
  file is added to the clone after the overlay; the `clone` field points at
  `<attempt-dir>/clone` and `snapshot`'s `changed` never contains
  `sealed.json`, `prompt.txt` or any `.rc` file.
- **Process-tree death, both platforms, no skip** — the `hang` fixture's
  detached grandchild appends to a heartbeat file every 100 ms. The test
  records the file's size at termination, waits past several heartbeat
  intervals, and asserts the size is unchanged. This proves the grandchild
  died **without enumerating processes**, so it needs neither `pgrep` on POSIX
  nor `wmic` on Windows and runs unskipped on both. A second test drives a
  SIGTERM-ignoring child with `escalate_after_s` set to milliseconds, so the
  two-stage kill is exercised inside the suite's 60 s budget. A third proves
  the group kill is **necessary**, not incidental: it signals the direct child
  alone with `SIGKILL`, observes the heartbeat still growing, then kills the
  group and observes it stop — so a future refactor that reverts to
  single-pid termination fails here. A fourth proves `reap` runs after a
  **clean** exit: the `spawn-and-exit` mode leaves a heartbeat child behind
  after exiting 0, and the test asserts the heartbeat stops, the gate lock was
  still held while that happened, the attempt scores normally, and **no**
  `halted.txt` is written — `reap` succeeding is not an orphan halt.
  `OrphanError` and the halt path are driven separately by stubbing
  `ProcessTree.survivors` to stay true, since no portable fixture can survive
  `SIGKILL`/`TerminateJobObject` on demand. On Windows, a fifth covers the
  assignment race: a child that spawns a grandchild in its first instruction
  and exits immediately still has its grandchild killed, which is only true if
  assignment happened while the child was suspended.
- **`test_sonnet_run.sh`** — a print-mode case asserting the stubbed `claude`
  receives `--session-id <uuid>` (via the existing `argv_has_pair`), and a
  resume-mode case asserting it does not.

Every suite runs with **no model server and no network**, using stubs and the
`cmd:` fake engine, and the platform-sensitive cases (process-tree death,
transcript lookup, stub resolution) run unskipped on both POSIX and native
Windows.

## Review log

dispatch 1 (claude): cardinal-sin 0, blocker 7, non-blocker 9, question 4

Blockers fixed in the doc (dispatch 1):

1. `run_attempt()`'s signature was elided — now a frozen `AttemptPlan`, with an
   intra-module decomposition table and line estimates that forced `gates.py`
   out of `attempt.py` to hold the 400-line cap.
2. The PRD's "a gate run concurrent with another" had no mechanism and no test
   — added `runner.gate_lock` (an `O_CREAT|O_EXCL` marker under the run dir)
   plus a test where a `cmd:` gate reads the marker from inside a gate.
3. Windows orphan detection reported "gone" in exactly the orphaned-grandchild
   case the PRD's `hang` fixture produces — replaced `taskkill`-keyed detection
   with a `ctypes` Job Object, `taskkill` kept only as a fallback that reports
   survivors and halts.
4. `render_prompt`'s `versions` input had no key set or provenance, so a
   byte-exact prompt was unspecifiable — replaced with
   `dispatch-references.json`, an ordered array vendored into the evidence dir
   (no plugin-cache path), whose array order is the render order.
5. `validity` was consumed by `classify` but owned by nobody — added
   `records.derive_validity`, with the null guard `final_message_bytes` needs
   (`null > 0` raises `TypeError`) and an explicit reason precedence.
6. `dropped` was deferred to the PRD and its necessity-map input never reached
   `run` — the rule is now stated, `vetting.json`'s necessity map is a field on
   `AttemptPlan`, and the PRD's non-load-bearing-path scenario is a test.
7. The adapter tests were built on `write_executable_stub`, which emits one
   fixed echo line and cannot record argv — added
   `write_argv_recording_stub` with POSIX and `cmd.exe` bodies, in the
   test-only module rather than the shared repo-root `conftest.py`.

Two dispatch-1 non-blockers were fixed in passing because they were entangled
with the blocker fixes above: the sonnet transcript lookup now uses
`Path.rglob` instead of `rg` (a runtime `rg` dependency on the evidence path
would score every sonnet attempt `DISCARDED:incomplete` on a host without it),
and the SIGTERM->SIGKILL escalation window became a parameter with a settle
poll (fixing both untestability inside the 60 s budget and a spurious
`HALTED:orphans` from checking survivors in the microsecond after the kill).

Recorded, not fixed (non-blockers):

- **`status.txt` and the per-gate `.txt`/`.rc` artifacts were dropped from the
  design.** Resolved incidentally by the `HALTED:orphans` fix, which added the
  "Per-attempt artifact set" section; noted here for the record.
- **The `set -u` justification for the `-S` array idiom is factually wrong
  about which file it describes.** `sonnet-run.sh:8` is `set -eo pipefail`; the
  `set -u` is in `test_sonnet_run.sh:6`, and `sonnet-run.sh:168,188,191`
  already expand `"${ADD_DIRS[@]}"` bare. The guarded idiom is harmless but
  inconsistent with the adjacent expansion on the same command line, and
  `--session-id`'s argv position needs pinning because
  `test_sonnet_run.sh:95-96` locks the no-`-S` argv exactly.
- **The usage-limit reuse does the thing Alternative C rejects.** `engines.py`
  falls back to "the autopilot plugin cache copy of `detect_usage_limit.py`",
  which is a plugin path — the practice `AGENTS.md:100-102` forbids and that
  Alternative C cites two sections earlier to reject an import. Either drop
  the auto-discovery and rely on `--usage-limit-cmd` alone, or state the
  exemption.
- **`final_message_bytes` has no named source, and both wrappers merge the
  child's stderr into `-o`** (`qwen-run.sh:476-477`, `sonnet-run.sh:144-146`
  are both `"$@" 2>&1 | tee`). A run that emitted only inner-CLI stderr yields
  a non-empty `out.txt` that could read as a non-empty final message.
- **Adapters reach for the braid link farm** (`~/.agents/skills/use-qwen/
  scripts/qwen-run.sh`) for a script that ships in the same directory as
  `run_eval_harness.py`. Resolving the sibling from `__file__` would work in a
  fresh CI checkout where `~/.agents` was never laid.

Recorded, not fixed (questions):

- **`stray` membership in the tdd shape is ambiguous** — does a tdd oracle edit
  appear in `stray` as well as flipping `oracle_intact`? The ladder gives the
  same class either way, but PRD 00052 renders the list itself.
- (The other three dispatch-1 questions — `validate_record`'s `kind` domain and
  `RecordError`, the required-gate set per shape, and the null-versus-empty
  reading of rung 5 — were answered by the blocker fixes above and are no
  longer open.)

dispatch 2 (codex): cardinal-sin 1, blocker 15, non-blocker 1, question 1

Cardinal sin fixed: **persistent evidence had no backup or restore procedure**.
The doc described irreplaceable records (an engine cannot be re-run to
reproduce an observation) with no durability story. Added
"## Evidence durability and restore": write-once by construction, a named
owner, an explicit backup unit, and `run_eval_harness.py verify <evidence-dir>`
as the *tested* restore check — a real command that re-validates every record,
recomputes the sealed-input digests and the tree manifest, and exits 0 only
when the bundle is consistent.

Blockers fixed (dispatch 2):

1. **Windows job assignment raced the child.** `AssignProcessToJobObject` on a
   running child leaves a window for a grandchild to escape the job — the exact
   escape the job exists to prevent. Now `CREATE_SUSPENDED` -> assign -> resume
   via `win32.resume_process`, and a failed assignment kills the still-suspended
   child rather than letting it run uncontained.
2. **A POSIX process group cannot hold a `setsid` descendant.** Rather than
   claim containment it does not have, the guarantee is restated as
   group-scoped, the `hang` fixture is specified to outlive its parent
   *without* leaving the group (which is what the PRD asks for), and the escape
   case is recorded as a known limit.
3. **Descendants were only reaped after a timeout.** A gate exiting 0 could
   leave a child running into the next gate — the very interference the PRD's
   gate-concurrency metric forbids. `reap` now runs on every path, and
   `gate_lock` is held until it reports the tree clean.
4. **Orphan handling fabricated an engine timeout.** It forced
   `engine_run.timed_out` true even when a *gate* leaked the child, or when no
   engine ever launched. Observed flags are now preserved; the orphan fact
   lives in `halted.txt` and `progress.log`, which name the offending command.
5. **`vet` sealed the tree but not the prompt, spec or references.** Any of
   them could change between `vet` and `run` while `ready` still claimed the
   task was sealed. `vet` now renders and seals the prompts and records
   `inputs_sha256`; `run` re-checks and refuses on mismatch.
6. **TDD dispatch references were optional and unverified**, so a tdd prompt
   could silently omit the instructions the PRD requires it to incorporate.
   They are now mandatory for tdd, must include `ivan` and
   `subagent-dispatch`, reject duplicate and colliding names, and carry a
   `provenance` field.
7. **The pre-dispatch proof could not see an ignored file.** `git status
   --porcelain` hides `.gitignore`d paths and the two path maps cover only
   declared paths, so a stray `conftest.py` or `pytest.ini` could change what
   the gate observed with every recorded value unchanged. Added
   `manifest.json`, a full typed tree manifest — in a separate file, because
   the PRD fixes `pretask.json`'s key set exactly.
8. **Preserved symlinks could let a clone write into the real repo.**
   `copytree(symlinks=True)` reproduces an absolute or escaping link
   faithfully, so "fresh clone per attempt" became shared mutable state. Added
   `contained()`, through which every harness write passes, plus outright
   rejection of escaping links at template build.
9. **The gate reconstruction order let candidate test edits win.** "Oracle
   re-copied first" allowed the candidate's own test hunks to land on top of
   the observing tests. The order is now pinned per gate, with the candidate's
   test hunks *excluded* from the patch and the vetted oracle copied last.
10. **`derive_validity` was not total** — `launch="unknown", exit=0` and
    `launch="started", exit=null` matched neither success nor any rejection.
    Replaced with an eight-rung table ending in a catch-all.
11. **An unknown gate `rc` could become `PASS`.** `None != 0` is `True` in
    Python, so an unrun ablation satisfied "the candidate's tests fail on the
    pre-task impl". Rung 6 now treats `rc is None` as `SUSPECT` and the
    ablation check requires `isinstance(rc, int)`.
12. **The fake engine had no validity protocol**, so its `PASS` fixtures would
    have proven nothing about the real path. Its identity line, final-message
    capture and terminal `session.jsonl` event are now specified.
13. **The "exact" record contract left value shapes undefined.** Added a field
    type-and-domain table and the `necessity` entry schema; `validate_record`
    checks both.
14. **A missing `halted.txt` was read as a completed run**, but a killed
    session leaves no marker at all. Added `complete.txt`, written last, and
    atomic `attempt.json` publication via `os.replace`.
15. **Two "impossible by construction" tests observed metadata, not
    execution.** The shared-baseline test would pass against a copied file and
    the shared-bound test against an ignored config field; both now assert on
    what actually executed.

Non-blocker fixed in passing (it was a factual inconsistency the doc had
introduced): the module inventory disagreed with itself (eight vs nine, and
`attempt.py` missing from the placement table) and `runner.py` had no line
estimate of its own. There is now one authoritative count — twelve files —
that every other mention defers to, `runner.py` and `win32.py` are estimated
separately, and `evidence.py` was split out to hold `attempt.py` under the cap.

Recorded, not fixed (question, dispatch 2):

- **Does missing-observation handling exclude fields inapplicable to the
  shape?** Answered in the ladder itself (description's `oracle_intact` and
  tdd's `ablate` are shape-inapplicable, not missing observations) and pinned
  by a test, so this is closed rather than carried.

dispatch 3 (codex): cardinal-sin 0, blocker 13, non-blocker 1, question 0

A verification pass. It graded the round-2 work as 7 of 16 fixed and 9 partly
fixed, and its 13 blockers are the residue: fixes that were written but did not
hold, plus contradictions the large in-place edits introduced. All 13 are fixed
above. In order:

1. **`verify` could certify a backup missing a whole attempt** — it validated
   what it found. `complete.txt`/`halted.txt` now carry an attempt inventory,
   `verify` requires every listed attempt to be present and valid, and a real
   delete-an-attempt restore test pins it.
2. **Re-vetting overwrote the inputs completed runs depend on.** `vet` now
   refuses an evidence dir that already holds a run, and each run copies the
   digests it consumed to `runs/<id>/sealed-inputs.json`.
3. **`subprocess.CREATE_SUSPENDED` does not exist** — `subprocess` exports no
   such constant, so the Windows launch would have raised before creating
   anything. `win32.py` defines `CREATE_SUSPENDED = 0x00000004` itself.
4. **A failed job assignment was given `DISCARDED:harness`**, contradicting the
   record contract twice (the process *was* created, so `launch` is `started`;
   and `harness` is the one state that authorises a retry). It is now a
   run-level halt, which is also the honest response: a host that cannot
   contain a child invalidates every later attempt too.
5. **The reap-after-every-command fix contradicted its own tests.** A leftover
   child that `reap` kills cleanly is not an orphan halt; `OrphanError` needs
   survivors *after* cleanup, which no portable fixture produces. Added the
   `spawn-and-exit` mode for the clean-exit path, kept `OrphanError` on a
   stubbed `survivors`, made `hang`'s parent outlive the bound (a parent that
   exits immediately scores a fast clean run, not `TIMEOUT`), and stated that
   the bound measures the direct child's lifetime.
6. **The oracle contents were outside the seal**, so replacing an oracle file
   after vetting would simply be blessed by the attempt's own fresh
   `sealed.json` — the observing tests substituted, undetected. Added the
   `oracle` label to `inputs_sha256`.
7. **Mandatory tdd references blocked the promised description-only run**,
   because `vet` had no shape selection. Added `vet --shapes`, and scoped the
   reference requirement to the shapes actually being qualified.
8. **The final pre-launch proof had no applicable manifest** in tdd: the
   overlay legitimately changes the tree, so the original manifest would reject
   it, and skipping the check reopened the ignored-file gap at the worst
   moment. The expected post-overlay manifest is now *derived* from two sealed
   inputs, so it is still a proof.
9. **`VALID` was computed before the rejection table**, letting a helper that
   handles its own termination be called valid despite an observed timeout,
   prep mismatch or invalid baseline. The table now runs first and `VALID` is
   only what survives it.
10. **The new field-domain table rejected ordinary output**: `changed[].status`
    was described as a "letter pair" when `git diff --name-status` emits `M`,
    `R100`, `C75`; and `oracle_intact` was `bool` unconditionally in tdd,
    contradicting the rule that unobserved values are `null`. Both corrected.
11. **The replacement bound test still observed metadata** — an adapter can
    report one deadline and enforce another. It now measures the enforced
    bound: both engines run `hang` under `--bound 2` and their `wall_s` values
    must land in the same narrow window.
12. **Attempt artifacts sat inside the tree being proved clean.** Writing
    `sealed.json` into the clone makes `git status --porcelain` dirty at the
    exact moment the design proves it empty, and drags artifacts into the
    candidate diff. Clone and artifacts are now separate directories.
13. **`rc: 1, failure_kind: null` became `FAIL:logic-error`** — a claim the
    candidate failed the tests, with no observed test failure. Rung 6 now
    requires `failure_kind == "test"` for any non-zero required gate.

The dispatch-3 non-blocker (a stale data-flow diagram still rendering prompts
during `run`, and Alternative D still keeping a `taskkill` fallback that
`runner.py` had already forbidden) was fixed too: both were internal
contradictions rather than deferrable concerns.

**Residual risk, stated plainly.** The 3-dispatch ceiling is spent, so these 13
fixes have had no verification pass of their own. Dispatch 3 found that 9 of 16
round-2 fixes were only partly right on first writing, and there is no reason
to assume this round did better. The planner and the implementor should treat
the sections touched by dispatch 3 — `verify`'s inventory, the Windows
suspended-creation path, the reap/timeout interaction, the post-overlay
manifest, and the validity ordering — as the places most likely to still be
wrong, and the tests named for each are the check.

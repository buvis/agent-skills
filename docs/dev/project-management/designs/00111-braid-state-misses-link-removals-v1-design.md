# Design: Braid can remove links without updating its ownership records

## Architecture fit

`braid` (`src/agent_skills_braid/cli.py`) is a single-module CLI with no
internal layering: `main()` parses args and builds `Settings`, `run()`
orchestrates one sync pass (union stage, then Claude host stage, then Kiro
host/agent stage), and `_sync_links()`/`_write_state()`/`_load_state()` are
the shared primitives each stage calls. There is no persistence layer
separate from `run()` — `run()` itself decides when `_write_state()` fires.
This PRD stays inside that shape: it changes only the orchestration in
`run()`, not `_sync_links()`'s link-level decisions (link/remove/refuse) or
`_write_state()`'s atomic-replace mechanics, both of which already do the
right thing in isolation.

## Module placement

- **Edit**: `src/agent_skills_braid/cli.py`, `run()` only (lines 557-629 in
  the current file). No new functions are exported; one private nested
  closure is added inside `run()`.
- **Edit**: `tests/test_braid.py` and `tests/test_braid_check.py` — new
  regressions for partial-progress persistence and skip-on-unchanged. No new
  test modules.

## Interfaces & contracts

`run()`'s signature, return type (`Result`), and every existing side effect
(link creation, backup, removal, orphan reporting, printed `emit()` lines)
are unchanged. Only the *timing and condition* of calls to `_write_state()`
changes.

Add one local closure inside `run()`, after `result = Result()` and before
the union `_sync_links()` call:

```python
written_state = previous_state

def persist(candidate: State) -> None:
    nonlocal written_state
    if settings.mode is Mode.SYNC and candidate != written_state:
        _write_state(state_path, candidate)
        written_state = candidate
```

- `written_state` tracks exactly what is currently on disk (starts as
  `previous_state`, the value `_load_state()` returned at the top of `run()`).
- `persist()` is a no-op in `Mode.CHECK`/`Mode.DRY_RUN` (preserves "check and
  dry-run modes remain read-only").
- `persist()` is a no-op whenever `candidate == written_state` — this is the
  "skip identical writes" behavior, and it applies at every call site, not
  only the final one.
- **Every `State` handed to `persist()` must own its own `hosts` dict, never
  alias the `hosts` local that `run()` keeps mutating.** `hosts` (built via
  `hosts = dict(previous_state.hosts)` at the existing `hosts = ...` line,
  before the Claude stage) is the same mutable object across call sites 2 and
  3 below; `State` is `@dataclass(frozen=True)` but its `hosts` field is a
  plain `dict`, so `State.__eq__`/structural identity does NOT protect a
  `State` that merely holds a reference to that dict — a later in-place
  mutation (`hosts["kiro"] = ...`) would silently change what an
  already-constructed, already-persisted `State` object reports as its
  `hosts`, breaking the "written_state tracks exactly what is currently on
  disk" invariant retroactively. Every call site below passes `dict(hosts)`
  (a shallow copy), not `hosts` itself.

Call `persist()` three times, once right after each stage that can perform a
removal or a link change and might be followed by an operation that raises
`BraidError`:

1. **After the union `_sync_links()` call** (existing code, unchanged
   arguments): `persist(State(union=union, hosts=previous_state.hosts,
   kiro=previous_state.kiro))`. This uses `previous_state.hosts`/
   `previous_state.kiro`, not the `hosts`/`kiro` locals, because at this point
   in `run()` those locals do not exist yet — `hosts = dict(previous_state.hosts)`
   is declared later, right before the Claude stage. This is forced by the
   existing variable order in `run()`, not a design choice to revisit;
   `previous_state.hosts` is itself safe to alias here since nothing in this
   function mutates `previous_state` (it is the frozen result `_load_state()`
   returned and is never reassigned). Add a one-line code comment at this
   call site in `cli.py` itself (not only in this doc) stating that
   `previous_state.hosts`/`previous_state.kiro` are safe to alias here only
   because they're never mutated — so a future edit that hoists the `hosts =
   dict(...)` assignment earlier doesn't silently reintroduce the aliasing
   bug call sites 2-3 were patched against.
2. **After the Claude host `_sync_links()` call**, inside the existing `if
   settings.project_claude:` block, right after `hosts["claude"] = ...`:
   `persist(State(union=union, hosts=dict(hosts), kiro=previous_state.kiro))`.
3. **After the Kiro host `_sync_links()` call**, inside the existing `if
   kiro is not None and settings.project_kiro:` block, right after
   `hosts["kiro"] = ...` and **before** the `for edit in kiro_edits:` loop:
   `persist(State(union=union, hosts=dict(hosts), kiro=kiro))`.

`kiro` (the registration) is already resolved by `select_kiro()` before any
sync runs, so passing it at call site 3 (and `previous_state.kiro` at sites
1-2) is correct without re-deriving it — a registration change with no link
change still only becomes visible in call site 3's candidate, which is fine:
nothing before that point depends on the registration having been persisted.

The existing final block keeps its own logic for counting state-only drift,
but its write is replaced by a `persist()` call so it, too, skips an
unchanged write:

```python
next_state = State(union=union, hosts=hosts, kiro=kiro)
if next_state != previous_state and result.drift == 0:
    result.drift += 1
    if settings.mode is not Mode.SYNC:
        emit(f"MISMATCH STATE {state_path}")
persist(next_state)
return result
```

Note this comparison stays against `previous_state` (the value read at
`run()` entry), not `written_state` — the drift counter's job is to report
whether this run changed anything relative to where it started, which is
unaffected by how many times the new code persisted along the way. Only the
`_write_state()` *call*, not this comparison, moves into `persist()`. This
final `next_state` is the one place the design still builds a `State` from
the bare `hosts` local rather than `dict(hosts)` — safe only because `hosts`
is never mutated again anywhere after this point in `run()` (no stage
follows); do not copy this pattern if a future change adds code after this
block.

No change to `Settings`, `Result`, `State`, `KiroRegistration`,
`KiroAgentEdit`, `_sync_links()`, `_write_state()`, `_load_state()`,
`_report_orphans()`, `sync_kiro_agent()`, `prepare_kiro_agents()`,
`select_kiro()`, or any CLI argument.

## Data flow

Before: `run()` computes `union` and `hosts` as plain local bindings across
three sequential stages, then builds one `next_state` and writes it once at
the end (or not at all, outside sync mode). Any `BraidError` raised inside a
later stage propagates out of `run()` unhandled, so no intermediate progress
made it to `.braid-state.json` even though the filesystem (symlinks/configs)
already reflects it.

After: the same three stages run in the same order with the same
link-level semantics. Each stage's result is folded into a `State` snapshot
and handed to `persist()` immediately, before control reaches code that can
raise. `written_state` is the single source of truth for "what is currently
on disk"; `_write_state()` only ever runs when the next snapshot differs
from it. A `BraidError` raised during the Claude stage now propagates past a
`written_state` that already reflects the union stage's removal; a
`BraidError` raised during the Kiro stage propagates past a `written_state`
that reflects both union and Claude. No new exception handling is added —
the existing propagate-and-exit-2 behavior in `entrypoint()` is unchanged;
only what has already been durably recorded before the exception fires
changes.

## Reuse inventory

- `_write_state()` (`src/agent_skills_braid/cli.py:405`) already does
  atomic replace via a same-directory temp file and raises `BraidError`
  with a diagnosable message on failure — reused as-is, just called more
  selectively.
- `State.__eq__` — `State` is `@dataclass(frozen=True)` (line 79), so
  structural equality (`==`) is free; no custom comparison helper needed for
  the "candidate == written_state" / "next_state != previous_state" checks.
- `_load_state()` (line 251) is already the single read path and needs no
  change.
- Greps tried (nothing else found): `rg -n "atomic|tmp.*replace|idempotent" src/agent_skills_braid/` found only `_write_state`'s own temp-file dance; `rg -n "def persist|incremental" src/agent_skills_braid/` found nothing — no existing "partial persistence" helper to reuse; `rg -n "written_state|last_written" src/` found nothing, confirming this is new.

## Alternatives considered

1. **Chosen: incremental `persist()` closure inside `run()`.** Smallest
   diff (one closure + three call sites + one replaced call), no new public
   surface, no behavior change to any other function, and it directly
   targets both defects (partial-progress loss and redundant unchanged
   writes) with the same mechanism.
2. **Smallest-diff alternative: wrap each stage in `try/except BraidError`
   and write state in the `except` block before re-raising.** This would
   also fix the data-loss defect, but not the "rewrites identical state"
   defect — a second, separate "compare before writing" change would still
   be needed at the end, and the two concerns would live in different
   places (reactive excepts for persistence, a comparison for dedup) instead
   of one rule. Rejected: more code than the chosen option for only partial
   coverage of the requirements.
3. **Larger alternative: pass a `StateWriter` object/protocol into
   `_sync_links()` so each individual link operation persists itself
   immediately (link-granularity instead of stage-granularity).** This
   would shrink the window of unsynced state further (a crash mid-stage,
   not just mid-run, would also be covered), but `_sync_links()` is reused
   for three different stages with three different `State` shapes (union
   vs. a named host's link map), so it would need to know how to fold a
   single link update into the right field of the right `State`... today it
   has no `State` awareness at all, only a flat `dict[str, str]`. That is a
   real redesign of `_sync_links()`'s contract for a failure window (a crash
   strictly inside one stage's own `_sync_links()` loop, not between
   stages) the PRD's accepted packet does not ask to cover. Rejected as
   scope the PRD did not ask for.

## Risks & edge cases

- **Likely next changes**: (1) the same incremental-persistence idea
  extended to `sync_kiro_agent()`'s loop, if a future defect shows a partial
  Kiro-agent-config write surviving a later Kiro-agent refusal the same way
  (today each `sync_kiro_agent()` call is already self-contained and
  independently backed-up/atomic per edit, so this is lower risk, but the
  loop over `kiro_edits` has no equivalent of `persist()` between edits);
  (2) `--check` mode gaining the same per-stage reporting granularity if an
  operator asks to know *which* stage drifted, not just that the whole run
  did. This design does not block either: `persist()` is a pure addition
  that a future `sync_kiro_agent` caller could reuse by passing the `State`
  that already includes `kiro`, and `_report_orphans()` already runs after
  all stages regardless of this change.
- **Edge case — state-only change with zero link/resource drift** (e.g. a
  fresh Kiro enrollment that happens to produce a host-link map identical to
  what a prior run without Kiro recorded, which cannot actually occur since
  enrolling Kiro always adds a `"kiro"` key to `hosts`, but the PRD's
  Success Criteria explicitly calls out "state-only updates still persist"):
  covered because `persist()`'s equality check is on the *whole* `State`
  object (`union`, `hosts`, and `kiro` together), so a `kiro`-only change
  still produces `candidate != written_state` and still writes.
- **Edge case — the union stage itself refuses** (changed path at the union
  level, e.g. `_sync_links` raising on `desired=inventory`): nothing has
  been persisted yet (`written_state` is still `previous_state`), which is
  correct — no removal happened before the refusal in that case, so there
  is nothing new to lose.
- **Edge case — `--no-claude`/`--no-kiro` combinations**: when a stage is
  skipped by a flag, its `persist()` call is simply never reached (the `if
  settings.project_claude:` / `if kiro is not None and settings.project_kiro:`
  guards already gate the call sites), so the final `persist(next_state)`
  carries whatever the skipped stage left untouched in `hosts`/`kiro` —
  identical to today's behavior for those flags.
- **Do not equate zero link changes with identical state** when Kiro
  metadata changes with no link difference: the equality check is
  structural on the full dataclass (not on `result.drift`), so this is
  already satisfied — re-stated here only because the PRD calls it out as a
  risk to verify in tests, not because the design needs an extra branch for
  it.
- **Persistence failure needs explicit handling without unsafe cleanup**:
  unchanged — `_write_state()`'s own `BraidError` on a failed write still
  propagates out of `persist()` (no new `try/except` added around the
  `_write_state()` call), `written_state` is not advanced on a failed write
  (the assignment `written_state = candidate` is unreachable when
  `_write_state()` raises), and the existing temp-file cleanup in
  `_write_state()`'s `finally` is untouched.

## Test strategy outline

Both files already exist and already cover related ground (`test_braid.py`
has partial-progress-adjacent cases like
`test_no_claude_preserves_existing_projection_and_state`;
`test_braid_check.py` has `test_sync_refuses_to_remove_a_hand_changed_managed_path`
and the `_write_state` failure-diagnostic tests at lines 172-220). New tests
extend these files rather than adding new ones, following the existing
fixture style (`tmp_path`, real `Settings`/`run()` calls, no mocking of
`_sync_links`/`_write_state`).

Required regressions (binding to intent, not implementation):

1. **Early union removal survives a later host refusal.** Seed state with a
   union link and a Claude host link; change the Claude-side destination so
   it no longer points at its recorded target (the existing
   "refusing to clean changed managed path" trigger); remove the union
   entry's underlying skill directory so the union stage performs a real
   `REMOVE`. Run `run()` in `Mode.SYNC` and assert it raises `BraidError`.
   Then re-read `.braid-state.json` from disk (a fresh `_load_state()` call,
   not the in-memory `Result`) and assert: the union link is no longer
   present, the actual on-disk union symlink is also gone (filesystem and
   state agree), and the hand-changed Claude host path is untouched on disk
   (still whatever the test set it to, not reverted and not removed).
2. **Unchanged sync on a read-only agents root succeeds.** Run `run()` once
   normally to populate state; make `settings.agents_root` (specifically the
   `.braid-state.json` path's parent) read-only (a portable fixture —
   `os.chmod` works cross-platform for *removing* write permission even
   though POSIX full-permission semantics differ, so assert on behavior,
   not on a chmod mode value); run `run()` again with identical inputs in
   `Mode.SYNC` and assert it returns successfully with no exception, and
   that no `.tmp` file was created (reuse the existing no-temp-file
   assertion style from `test_a_failed_temp_cleanup_does_not_hide_the_state_write_error`).
   `os.chmod`'s read-only bit is unreliably enforced for directories on
   Windows (new-file creation inside a "read-only" directory often still
   succeeds there), so this test is POSIX-only (skip/xfail on `nt`); it does
   not need a cross-platform ACL fixture since the behavior it proves —
   `persist()` never calling `_write_state()` when nothing changed — is
   platform-independent in the source, only the fixture for proving "the
   root really can't be written" is POSIX-specific.
3. **A real state-only change still persists on an otherwise-driftless
   run.** Enroll Kiro for the first time against inputs that produce the
   same union/host link maps as a prior Kiro-less run; assert
   `result.drift >= 1` and that the state file on disk now contains the
   Kiro registration (re-read it, don't just check the return value).
4. **Preserve existing refusal and protection coverage.** Re-run (or
   confirm still-passing, if sufficiently covered already) the existing
   changed-path refusal and user-owned-link protection tests to prove this
   change does not weaken them — `test_sync_refuses_to_remove_a_hand_changed_managed_path`
   and the Kiro agent refusal tests at `tests/test_braid.py:476-576` stay
   green with the new `run()` body.

Acceptance: `uv run pytest tests/test_braid.py tests/test_braid_check.py`
passes; regressions 1 and 2 above fail against the current (pre-fix) `cli.py`
and pass after the fix.

## Review log

- non-blocker: an individual `_sync_links()` call can perform several real
  removals before a later item in the same loop raises `BraidError` (the
  loop at `cli.py:532-552` is not itself checkpointed); the design's
  "Alternatives considered" #3 already identifies and consciously rejects
  fixing this finer-grained window as out of this PRD's scope.
- dispatch 1 (claude): cardinal-sin 0, blocker 1, non-blocker 1, question 1
- dispatch 2: codex unavailable, Claude fallback (sandbox-exec denied file
  reads under the Seatbelt both attempts, including with the inlined
  fact-forcing retry — matches the documented `review-phase-known-overhead`
  pattern for this repo's codex dispatches)
- non-blocker: `sync_kiro_agent()`'s loop over `kiro_edits` still has no
  `persist()` call between individual edits, a second, narrower
  partial-progress channel (Kiro agent config files, not links) this PRD
  does not close; already named in Risks & edge cases as a likely next
  change, left as scope the PRD's accepted packet did not ask to cover.
- question: the read-only-root test fixture (Test strategy #2) needs POSIX
  scoping since Windows does not reliably enforce a directory's read-only
  bit — addressed above (Test strategy #2 now says POSIX-only).
- question: call site 1's reliance on `previous_state.hosts`/`previous_state.kiro`
  staying unmutated should travel as a code comment, not only doc prose —
  addressed above (call site 1 now calls for an in-code comment).
- dispatch 2 (claude-fallback): cardinal-sin 0, blocker 0, non-blocker 1,
  question 2
- dispatch 3: not run (dispatch 2 found zero cardinal sins/blockers)

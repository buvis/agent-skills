# Decision Audit Log: 00089-purge-devtmp-moves-a-nested-repo-as-one-unit-v1

PRD: `00089-purge-devtmp-moves-a-nested-repo-as-one-unit-v1.md`
Started: 2026-10-25T10:19:49Z
Completed: 2026-10-25T10:19:49Z
Autonomous: 11  |  Deferred: 1  |  Doubts: 0

### [autonomous] 2026-10-25T10:19:49Z

**Decision**: Nothing tests the new unit guard in `prune_empty_dirs`. I swapped the pre-change prune back in and all 15 tests in `test_purge_devtmp.py` still pass. The guard matters: on a `git init` fixture that is classed fresh and kept in apply mode, the old prune deletes the empty `.git/refs` and `.git/objects` dirs, and `git rev-parse` then exits 128 with "not a git repository". Add an apply-mode test with a fresh unit that holds empty `.git/refs/heads` and `.git/objects/pack`, and assert they survive

**Choice**: tail sweep queued

**Rationale**: Cycle 1 converged; pending tasks 2 and 3 implement the selected findings in the next fresh session

### [autonomous] 2026-10-25T10:19:49Z

**Decision**: `walk_store` nests 5 levels deep (for, elif, for, for, try), over the 4-level limit. Move the inner walk and its fallback into `newest_file_mtime(directory: Path) -> float`. The branch then becomes `yield Path(base).relative_to(store), newest_file_mtime(Path(base))`, `dirs[:] = []`, `continue`

**Choice**: tail sweep queued

**Rationale**: Cycle 1 converged; pending tasks 2 and 3 implement the selected findings in the next fresh session

### [autonomous] 2026-10-25T10:19:49Z

**Decision**: Two walkers now repeat the same pruning rules: the `".git" in dirs or ".git" in files` check and the root `.trash` prune appear in both `walk_store` and `prune_empty_dirs`. A shared `is_repo_unit(dirs, files)` check would keep them from drifting apart

**Choice**: tail sweep queued

**Rationale**: Cycle 1 converged; pending tasks 2 and 3 implement the selected findings in the next fresh session

### [autonomous] 2026-10-25T10:19:49Z

**Decision**: The live check now reads only the unit's own path. A file with a live PRD number inside a stale fixture moves to the trash (I reproduced this), but SKILL.md still says "Files carrying the number of a PRD ... are kept". The 30-day trash makes it recoverable; the gap is in the PRD and the docs

**Choice**: tail sweep queued

**Rationale**: Cycle 1 converged; pending tasks 2 and 3 implement the selected findings in the next fresh session

### [autonomous] 2026-10-25T10:19:49Z

**Decision**: Nothing tests the PRD's empty-unit rule (use the directory's own mtime when the unit holds no regular file). All three new tests put files in the unit, so changing `default=` to `0` would pass. The apply-mode test above can use a unit with only empty `.git` subdirs to cover this too

**Choice**: tail sweep queued

**Rationale**: Cycle 1 converged; pending tasks 2 and 3 implement the selected findings in the next fresh session

### [autonomous] 2026-10-25T10:19:49Z

**Decision**: The `autocodex-sessions/` ignore entry is outside the PRD's scope but went into the `fix(purge-devtmp)` commit. It is defensible, since it keeps raw transcripts out of a public repo, but it belongs in a separate chore commit

**Choice**: discarded

**Rationale**: discarded: the ignore rule prevents private raw host transcripts from entering this public repository; workflow reports and model audits remain tracked. Rewriting committed history adds no product benefit.

### [autonomous] 2026-10-25T10:19:49Z

**Decision**: The PRD's root cause was the uncaught exception in process_store, and it is still there. trash_file has no guard, so any other move failure (for example a rename refused for another reason) still leaves the store half moved and stops every later store. That puts the "no purge traceback" success signal at risk

**Choice**: discarded

**Rationale**: single-voice Medium/Low; discarded under the review decision policy

### [autonomous] 2026-10-25T10:19:49Z

**Decision**: Possible follow-on bug: trash batches can now hold `.git/hooks`. If the Seatbelt also refuses to unlink under `.git/hooks`, and `empty_old_trash` does not handle the error, the purge dies again once that batch is 30 days old.

**Choice**: discarded

**Rationale**: single-voice Medium/Low; discarded under the review decision policy

### [autonomous] 2026-10-25T10:19:49Z

**Decision**: The prune change also fixes a user-visible bug: kept repo fixtures no longer lose their empty `.git` subdirs. Neither the CHANGELOG entry nor SKILL.md mentions it

**Choice**: discarded

**Rationale**: single-voice Medium/Low; discarded under the review decision policy

### [autonomous] 2026-10-25T10:19:49Z

**Decision**: The fake sandbox in the test patches only pathlib.Path.mkdir, so a move that fell back to os.makedirs or copytree would still pass. This matches the spec's wording, but it is a weak guard against that kind of regression

**Choice**: discarded

**Rationale**: single-voice Medium/Low; discarded under the review decision policy

### [autonomous] 2026-10-25T10:19:49Z

**Decision**: `max(mtimes, default=Path(base).stat().st_mtime)` runs `stat` for every unit, even when files were found, and nothing catches its error. If another session deletes the unit during the inner walk, `FileNotFoundError` stops the whole store run. That is the failure this PRD set out to remove.

**Choice**: discarded

**Rationale**: single-voice Medium/Low; discarded under the review decision policy

### [deferred] 2026-10-25T10:19:49Z

**Decision**: A `.git` at the store root is never treated as a unit, because the `base == store` branch runs first. The walk then enters `store/.git`, yields its `hooks/*` files, and hits the same `.git/hooks` mkdir denial. `prune_empty_dirs` also removes empty dirs inside it. This is unlikely, but it is the same crash class

**Choice**: deferred

**Rationale**: Repository at the tmp store root is outside nested-fixture scope; moving the store into its own trash is invalid. Separate refusal policy required.

# Resolving Conflicts: Terminology, Commands, Safety

## The rebase trap (read when ours/theirs feels backwards)

During rebase your commits are *replayed onto* the target, so the sides flip:
the target branch becomes `--ours`/HEAD and **your own commits become `--theirs`**.
(The per-operation table lives in SKILL.md Step 2.)

When unsure which side is which, look at the actual content instead of guessing:

```bash
git show :1:<file>   # base (common ancestor)
git show :2:<file>   # ours
git show :3:<file>   # theirs
```

diff3 markers make the ancestor visible inline:

```
<<<<<<< HEAD        (ours)
||||||| ancestor    (what both started from)
=======
>>>>>>> branch      (theirs)
```

Enable it: `git config --global merge.conflictstyle zdiff3`, or for one file
`git checkout --conflict=diff3 <file>`.

## Diagnostic commands

```bash
git status                                  # operation type + unmerged paths
git diff --name-only --diff-filter=U        # list conflicted files
git diff <file>                             # conflict markers
git diff --cc <file>                        # three-way view
git log -1 REBASE_HEAD                       # commit causing a rebase conflict
git log -1 CHERRY_PICK_HEAD                  # commit causing a cherry-pick conflict
```

Operation markers (each a separate call; the exit code is the answer, no `2>/dev/null`):
`ls .git/MERGE_HEAD`, `ls .git/CHERRY_PICK_HEAD`, `test -d .git/rebase-merge`, `test -d .git/rebase-apply`.

## Resolution commands

```bash
git checkout --ours <file>   && git add <file>   # keep ours (see rebase trap!)
git checkout --theirs <file> && git add <file>   # keep theirs
git add <file>                                   # after a manual edit
git rm <file>                                    # accept a deletion
```

Continue: `git commit` (merge) · `git rebase --continue` · `git cherry-pick --continue`.
Abort (all safe, return to pre-operation state): `git merge --abort` · `git rebase --abort` · `git cherry-pick --abort` · `git rebase --skip` (drops the commit).

## Safety

Before resolving, check for work that could be lost: `git stash list`, `git status --porcelain`.

**Warn the user before** any command that discards work: `git checkout .`,
`git checkout --ours/--theirs`, `git reset --hard`, `git clean -fd`, `git rebase --skip`.

After `git stash pop` conflicts, the stash is **not** dropped — it stays in `git stash list`.

Recovery if work is lost: `git reflog` to find the commit, then `git cherry-pick <sha>` or `git reset --hard <sha>`.

Suggest aborting when the user is confused about which side to keep, the conflict
is too complex to decide safely, or the sheer count means the branches diverged too
far (consider smaller PRs, syncing more often, or `git rerere`).

## rerere (reuse recorded resolution)

```bash
git config --global rerere.enabled true
git config --global rerere.autoupdate true
git rerere status   # what it auto-resolved
```

Even when rerere resolves automatically, still show the result and confirm it fits
this context — a past resolution may not apply here.

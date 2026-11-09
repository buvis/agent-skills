# Worktrees as Herdr spaces

## Observation: 2026-11-10

Verified against `herdr-app 0.1.14` and `hc 0.1.19`.

Creating two Git branches and worktrees succeeded. Opening each with
`tab.new --space <original-space> --folder <worktree>` also succeeded, but
left ordinary tabs in the original space. The user still had to right-click
the repository space and choose **Open worktree** for each checkout. That
produced separate worktree spaces nested beneath the repository in the sidebar.
Do not report a worktree as opened in that sense merely because a tab exists.

The installed `mods/worktree/main.js` explains the operation: `open(c)`
selects an existing matching space or calls `space.new` with the checkout
folder and machine. `mods/spaces/main.js` groups linked checkouts by Git's
common directory and machine beneath the main checkout's space. This is
derived grouping, not a parent-space argument.

## Procedure

1. Inspect `git worktree list --porcelain`, branch names, and `herdr-app ls`.
   Use hc's current terminal folders when the space's creation folder is
   misleading. Match the checkout and machine, not just the display name.
2. Reuse existing checkouts. For a requested new checkout, create its branch
   and worktree from the intended base using Git. Follow global/repository
   placement rules: this environment uses `~/git/src/worktrees/<repo>/<name>`.
   The observed shipped **New worktree** mod instead uses
   `~/.herdr/worktrees/<repo>/<branch-slug>`; do not let that default override
   the user's convention or edit the shipped mod to change it.
3. If already shown as a space, select that space by ID. Otherwise use
   `space.new` with the absolute checkout folder and correct machine. This
   performs the structural operation used by **Open worktree** without a
   dialog. Give it a useful checkout name and initial tab name. Substitute
   actual values in this command; the empty machine selects this computer:

   ```bash
   herdr-app do space.new --name feature-example --folder /absolute/worktree/path --tab shell --machine ''
   ```

   The shipped mod leaves the space unnamed so its name follows the folder;
   an explicit name stays fixed. Nesting depends on Git identity either way.
4. Verify the branch/path with Git, each distinct space with `herdr-app ls`,
   and its terminal's live folder with `hc get <terminal>` (JSON
   `foreground.cwd`, falling back to launch `cwd`). Check `status` for errors.
   Inspect a `shot` when verifying sidebar nesting; `ls` alone does not prove
   the visual hierarchy. The main checkout must also have a space for nesting.
5. Report the branch, checkout path and opened space. If Git succeeded but
   Herdr failed, retain the checkout and report that opening is incomplete;
   retry opening without creating another branch or worktree.

Read the installed docs/source again if these operations change. Never edit
Herdr's saved state files to manufacture spaces. Do not close pre-existing
tabs as cleanup: their terminals may now contain the user's work.

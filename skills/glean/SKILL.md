---
name: glean
description: Use when checking a bare-repo dotfiles setup for config that drifted in untracked - scans $HOME, prescreens secrets, walks verdicts, remembers them in a split ledger. Triggers on "glean", "dotfiles checkup", "untracked dotfiles", "dotfiles drift".
compatibility: "Portable; needs python3 and git. git-secret steps need the user's GPG unlock, so they are always handed to the user."
---

# Glean

Find config that piled up in `$HOME` outside the dotfiles bare repo, decide
with the user what to track, and remember every verdict so the next run only
asks about what is new or changed.

Assume the dotfiles remote is **public**. One wrong `git add` publishes a
secret or a map of the machine. Be aggressive about surfacing candidates and
conservative about tracking them.

## Safety rules (never bend)

1. Never open a file whose prescreen shows a `HARD:` hit or that the ledger
   marks `never`. Work from key names and line numbers only. If the host
   denies a read of a secret file, take that as correct and work around it.
2. Never stage a path you have not read in full in this session.
3. Stage by explicit path with `:(top)` pathspecs. Never `add -A`, `add .`
   or a directory, and never `commit -a`. The work tree is shared with the
   user's in-progress edits, so commit only what you staged.
4. Run `check-staged` before every commit. On `ok: false`, unstage and stop.
5. git-secret `add`, `remove` and `hide` need the user's GPG unlock: print
   the exact commands for the user to run, then verify the result yourself.
6. Push only after the user has confirmed the walkthrough outcome.
7. Empty output from the bare repo proves nothing. Re-run the command
   against a known-tracked path before concluding "absent".

## Ledger

Two JSON files share one shape: `{"entries": [{path, verdict, decided, sha256?, count_mtime?, note?}]}`.

- **Local** (`~/.local/state/glean/ledger.local.json`, never tracked): `never`
  and `machine` verdicts, plus a `config` block:
  `{"git_dir": "~/<bare>", "public_ledger": "~/<path>.json", "link_roots": ["~/<repos root>"]}`.
- **Built in** (`BUILTIN` in `glean.py`): `.local/` and `*/.local/*` are always
  `never`. `~/.local` holds per-host data and state, and `<repo>/.local` is agent
  scratch. Neither can reach the dotfiles repo, whatever the ledgers say.
- **Public** (inside the dotfiles repo, at `config.public_ledger`): `noise`,
  `link` and `skip` verdicts, which reveal nothing sensitive.

| verdict | stable? | meaning |
|---|---|---|
| never | yes | holds secrets or machine identity |
| encrypted | yes | tracked through git-secret |
| noise | yes | cache, state, logs, generated |
| link | yes | symlink into another repo (anything under `link_roots` is settled automatically) |
| skip | no | not now. Comes back when sha256 or count_mtime changes, or after 180 days |
| machine | no | bound to this machine. Same re-surface rule |

Volatile verdicts need the `sha256` from the scan output, or its `count_mtime`
(file count and newest mtime) for a directory of more than 200 files. A wholly
untracked directory is one candidate with a directory fingerprint, so give the
verdict to the directory path (trailing `/`), not to a file inside it. Paths are
`$HOME`-relative. A trailing `/` covers a directory and `*` globs.

First run: if the local ledger is missing, ask the user for the bare repo's
git dir and where the public ledger should live, then create both files.
Then offer to install a `pre-commit` hook that runs `glean.py check-staged`
and exits non-zero when `ok` is false. That gates every commit, including
manual ones made outside this skill. Prefer a tracked hook inside the work
tree, with the repo's `core.hooksPath` pointing at its directory, so it
reaches every machine. `<git_dir>/hooks/` is not tracked. Repo config is not
tracked either, so check on every run that `core.hooksPath` is set and the
hook exists.

## Procedure

1. **Scan**: `python3 ~/.agents/skills/glean/scripts/glean.py scan > <scratch>/glean-scan.json`.
   Read the counts first. The scan lists untracked dotfiles, dotdirs and
   `~/bin`, minus settled
   verdicts. It also reports `secret_gaps`: encrypted blobs missing from the
   git-secret mapping, or mapped files with no tracked blob.
2. **Triage** each candidate and resurfaced item into `track`,
   `track-after-edit`, `encrypt`, `never`, `noise`, `link`, `skip` or
   `machine`. Use the `hints`, the `secret_hits` keywords and the file
   names. Leave stable bulk noise (caches, sessions) out of the walkthrough
   and record it straight into the public ledger.
3. **Vet** every `track` candidate's content before proposing it. Delegate
   the reading to a subagent when there are many, telling it never to quote
   values. Check for hostnames, IPs, serials, device or user IDs, non-public
   emails, private repo names, versioned or arch-specific absolute paths,
   and tokens. Confirm visibility of every repo name that would go public
   (an unauthenticated `git ls-remote` or HTTP 200 means public). A name
   already present in the tracked tree is no new exposure.
4. **Walk** the decisions with the user, one per message, highest severity
   first: secrets, then registry gaps, then portability breakers, then LOW
   batches (multiSelect, up to 4 per batch). Each question needs context,
   evidence, and 3-4 options with benefit and drawback. Follow the user's
   own walkthrough rules when they define stricter ones.
5. **Apply**: make the edits, stage explicit paths, run
   `python3 ~/.agents/skills/glean/scripts/glean.py check-staged` (exit 1 =
   blocked), commit, hand the git-secret commands to the user, then stage the
   `.secret` blobs and mapping and run `check-staged` again. Encrypted blobs
   must show `-` in `diff --cached --numstat`.
6. **Record** every verdict in the right ledger with today's date, and add a
   `sha256` to volatile ones. Commit the public ledger with the change.
7. **Push** after the user confirms. Report what was tracked, encrypted and
   deferred, and the check output.

## Tests

`python3 -m pytest ~/.agents/skills/glean/scripts/test_glean.py -q`

## Non-goals

Scanning already-tracked files for secrets (use a real scanner such as
gitleaks in CI), history rewriting, and other machines' homes.

# Sonnet batch: two-lane runbook

Set up 2026-09-03. 20 PRDs classified sonnet-tier, split into two lanes by file
contention. Lane 2 exists only because six PRDs all edit
`skills/brief-portfolio/app/smoke.test.js` and rebuild the same
`assets/template.html`, so they can never interleave with each other or with
anything else touching that app.

## Launch

Two terminals, one per lane. `autoclaude` is a shell function
(`~/.config/bash/plugins/development.plugin.bash`), so it needs an interactive
tty; it cannot be started from inside a Claude session.

```bash
# Terminal 1 - lane 1, 14 PRDs, on master
cd ~/git/src/github.com/buvis/agent-skills && autoclaude

# Terminal 2 - lane 2, 6 PRDs, on branch lane/brief-portfolio
cd ~/git/src/github.com/buvis/agent-skills-lane-brief && autoclaude
```

The duplicate-loop guard keys on the repo root and refuses a second loop on the
same root, which is why lane 2 is a worktree and not a second loop here.

## Lanes

Lane 1 (master, 14): 00015, 00016, 00017, 00020, 00021, 00022, 00030, 00032,
00034, 00035, 00036, 00038, 00044, 00047.

Lane 2 (`lane/brief-portfolio`, 6): 00019, 00024, 00025, 00026, 00028, 00033.

Serialisation inside lane 1 is by PRD number, which already gives the right
order: 00015 > 00016 > 00017 share `docket.py`; 00020 > 00022 > 00044 share
`ci.yml`; 00038 and 00044 both touch `README.md` on disjoint lines.

## Parked, not abandoned

The 8 opus-tier PRDs sit in `dev/local/prds/hold/` so the drain does not pull
them in: 00014, 00018, 00023, 00027, 00029, 00031, 00045, 00048. Autopilot
never reads `hold/`. Move any of them back to `backlog/` by hand to resume.

## Known coupling

00026 (lane 2) reuses the "not collected this run" wording that 00018 owns, and
00018 is parked. 00026 carries the literal string in its own Must-have, so it
builds standalone; if 00018 later lands with different wording, sync the two.

## Reconcile when both lanes drain

```bash
cd ~/git/src/github.com/buvis/agent-skills
git merge lane/brief-portfolio          # CHANGELOG.md conflicts; both sides keep their bullets
mv ../agent-skills-lane-brief/dev/local/prds/done/*.md dev/local/prds/done/
git worktree remove ../agent-skills-lane-brief
git branch -d lane/brief-portfolio
```

`dev/local/` is gitignored, so lane 2's PRD lifecycle moves never merge - the
`mv` above is the only thing that folds them back. Do it before removing the
worktree, or the record of which PRDs completed is lost with it.

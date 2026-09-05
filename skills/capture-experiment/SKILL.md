---
name: capture-experiment
description: Use when writing up a spike or experiment as a zettelkasten note before dead ends and observations are lost. Request-only, needs a title. Triggers on "capture experiment", "log this experiment", "write up this spike".
---

# capture-experiment

Writes up a spike, test, or experiment session as a single zettelkasten note -
hypothesis, setup, summarized observations, dead ends, and verdict - before the
details are lost to compaction or a new session.

## Dependencies

- `digest-github-repo` (this repo): source of the frontmatter shape and the
  `YYYYMMDDHHmmss` zettelkasten id scheme (`date +%Y%m%d%H%M%S`) this skill
  reuses. Convention reference only, never invoked; its absence changes
  nothing.
- `spike` and `create-prd`: named in the note's follow-up checkboxes as the
  skill that would do the next piece of work, where one applies (e.g.
  `- [ ] /spike the alternative approach`). Never invoked; a human runs them
  later from the note, and an absent skill still gets its checkbox as plain
  text.
- External `~/bim/` tree (hard anchor, no fallback): output only, into
  `~/bim/inbox/automated/capture-experiment/`. A missing `~/bim/` is a loud
  failure - stop and report it, never fall back to another directory, and
  never write into `~/bim/zettelkasten/` directly (that's a triage-time move,
  not this skill's job).

## Triggers

Request-only. Use this skill when the user asks to capture, log, or write up a
spike, test, or experiment that just ran in this session - "capture this
experiment", "log this spike", "write up this test as a note",
"capture-experiment". It never fires on its own at session end or compaction:
harvesting from a transcript is out of scope (see Step 1).

---

## Step 0 — Get the title

The skill takes exactly one required argument: a title. If the user's request
already names one, use it. If not, ask for it and stop there - a title is the
whole ceremony budget, don't also ask about tags, window, or anything else.

---

## Step 1 — Build the note from context, never from a transcript

Never parse a transcript file, tool log, or hook output to reconstruct the
session. Skill bodies, hook output, task notifications, and agent prompts all
arrive as `role=user` turns with only schema fields telling them apart from
real user input, so a script scanning for "what the user said" cannot
reliably separate them - it must not be written. Draw the note's content only
from what is already known first-hand from this session: the hypothesis
tested, what was run or measured, what was observed, what was tried and
abandoned, and the verdict.

A compacted session has already lost its early dead ends, so state the window
explicitly rather than implying completeness. Use the session's actual start
and current time if known; if the true start is uncertain (e.g. after a
compaction), say so in the window line rather than guessing a precise start
(e.g. "since last compaction – now").

---

## Step 2 — Compose the note

Use `~/.agents/skills/capture-experiment/assets/note-template.md` as the fixed
shape. Every section is required:

1. Frontmatter block (`id`, `title`, `date`, `tags`, `type: experiment-log`,
   `publish: false`, `processed: false`); `id` is the same
   `YYYYMMDDHHmmss` value as the filename, as in `digest-github-repo`'s
   template, so vault-wide queries on `id` see these notes too
2. Window line
3. Hypothesis
4. Setup
5. Observations
6. Dead Ends
7. Verdict
8. Follow-up (checkboxes)

Collapse the title to a single line. The heading takes that plain collapsed
title. The frontmatter `title:` value is a double-quoted YAML scalar, so before
substituting it there escape every backslash as `\\` and then every double
quote as `\"`, in that order, and nothing else.

Fill in:

- **Observations** — summarized readings with units, never a raw dump. No raw
  serial streams, no pasted capture output, no linked data file. If someone
  wants to re-analyze, they repeat the run - that trade is accepted.
- **Dead Ends** — first-class content, not an omission. If the session tried
  and abandoned an approach, it goes here; a note that skips a dead end that
  happened is a defect. If nothing was tried and abandoned, say so explicitly
  rather than deleting the section.
- **Follow-up** — unchecked boxes (`- [ ]`), each naming the skill that would
  do the next piece of work where one applies (`/spike`, `create-prd`). Do
  not record cost or wall-clock time: `costs.jsonl` rows are cumulative per
  session id, so any per-experiment figure derived from them would overstate
  the real cost.

---

## Step 3 — Write the note

Check `~/bim/` exists first. If it's missing, stop and report the failure - do
not create a fallback directory and do not write the note anywhere else.

If `~/bim/` exists but `~/bim/inbox/automated/capture-experiment/` does not,
create that leaf directory before writing.

Generate the zettelkasten id: `date +%Y%m%d%H%M%S`. If `<id>.md` already
exists at the destination, wait for the clock to tick (`sleep 1`), run
`date +%Y%m%d%H%M%S` again, and repeat the existence check until the id is
free. Never derive an id by adding to the previous one: `...5960` is not a
timestamp. Put the same value in the frontmatter `id:` field.

Write the note to:

```
~/bim/inbox/automated/capture-experiment/<id>.md
```

Never write directly into `~/bim/zettelkasten/` - atomizing a session note
into individual zettelkasten entries is a triage-time job, not this skill's.

---

## Step 4 — Report back

Show the note in chat, then confirm the save path.

---

## Edge cases

- **No title given** — ask for the title and stop; nothing else is asked.
- **`~/bim/` missing** — loud failure in chat; no fallback directory, no note
  written elsewhere.
- **No dead ends in the session** — say so explicitly in the Dead Ends
  section rather than omitting the section.
- **Window start unknown** (e.g. after compaction) — say so in the window
  line instead of guessing a date.
- **`<id>.md` already exists** (two captures in the same second) — sleep a
  second, regenerate the id from the clock, and re-check; never overwrite,
  and never compute the next id by arithmetic.

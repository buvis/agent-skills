---
default_model: opus
rework_cap: 5
---

# `init_skill.py`'s printed next step names the Claude-only path instead of the union path

Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 32
(LOW, journey lane, verified as divergence). Decision 2026-09-02: accepted —
print the union form.

## Overview

### Problem Statement

The scaffolder prints `3. Validate: ~/.claude/skills/create-skill/scripts/
validate_skill.py <path>` while `SKILL.md:220` documents the
`~/.agents/skills/...` form. Per `README.md`, `~/.agents/skills` is the union
every host reads and `~/.claude/skills` a Claude-only projection that
`braid --no-claude` never creates — on a host without the Claude projection
the printed step points at nothing (unconfirmed; no such host exists here).

### Target Users

Anyone scaffolding a skill on a non-Claude host, and anyone comparing the
printed step against the docs.

### Success Metrics

- The printed step reads
  `python3 ~/.agents/skills/create-skill/scripts/validate_skill.py <path>`,
  byte-matching `SKILL.md:220`'s form.

## Functional Decomposition

Change the one printed string, interpreter-prefixed, to the union form.

## Structural Decomposition

- `skills/create-skill/scripts/init_skill.py` (~111)

## Implementation Phases

### Phase 0: The string

One line.

## Test Strategy

Evidence from the report, verbatim:

```
Scaffolding printed
3. Validate: ~/.claude/skills/create-skill/scripts/validate_skill.py /…/walter-probe;
SKILL.md:220 documents
python3 ~/.agents/skills/create-skill/scripts/validate_skill.py <path>.
Both forms ran successfully here.
```

Check: scaffold a scratch skill, assert the printed line carries the union
path.

## Risks

A consistency fix with no demonstrated failure — both paths work on this
machine; the value is design coherence and the unverified non-Claude host.

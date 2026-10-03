---
name: plugin-ownership-check-needs-versioned-glob
description: "A plugin-ownership check must glob the versioned plugin cache path, not a fixed one, or it silently returns NONE for skills a plugin already provides."
metadata:
  node_type: memory
  type: project
---

A check for whether a skill name is already provided by an installed plugin (run before letting braid link that name into `~/.claude/skills/`) globbed a fixed cache path and returned `NONE` for six names — `design-solution`, `audit-authoring`, `audit-claude-config`, `audit-config`, `audit-filesystem`, `run-agoge` — that were in fact already owned by `autopilot`, `claude-checkup`, and `agoge`. The plugin cache path carries a version directory (e.g. `~/.claude/plugins/cache/<plugin>/<plugin>/<version>/skills/...`), so a glob without a version wildcard misses every installed plugin skill.

**Why:** A false `NONE` reads as "no duplicate, safe to link," which is the opposite of true. Trusting it here would have let braid link six unnamespaced duplicates over plugin-owned skills, exactly the failure `.braidignore`'s header exists to prevent. Only a control comparison (checking a name known to already be excluded) caught the wrong glob. Related: [[session-pins-plugin-version]] — `installed_plugins.json` can also name a version other than the one actually running, another version-directory trap in this same cache tree.

**How to apply:** Before adding a name to `.braidignore` or trusting braid's dry-run projection, check plugin ownership with a version-wildcarded glob, and validate the check against a known-tracked control case before trusting an empty/`NONE` result.

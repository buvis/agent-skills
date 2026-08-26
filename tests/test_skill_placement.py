"""Guard the boundary between a runnable skill and a documentation copy.

`skills/` is the only directory braid scans, so every SKILL.md there is offered
to Claude Code, Codex, Copilot and Gemini alike. A skill whose executable half
lives in a plugin cannot honour that offer: the host lists it, routes to it, and
fails. `.braidignore` does not help - it applies only on the way to
~/.claude/skills, and the other hosts read the union view directly.

These tests encode the four rules in AGENTS.md so placement is checked on every
commit rather than by whoever remembers. `gateguard` sat misplaced for a day
because nothing did.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"
DOC_COPIES = REPO / "docs" / "plugin-skills"

# Phrases that mark a skill as unrunnable off Claude Code. A compatibility line
# saying any of these describes a documentation copy, whatever it is called.
CLAUDE_ONLY = re.compile(r"documentation copy|claude[ -]code-specific|claude-specific", re.I)

PLUGIN_MARKER = re.compile(r"<[a-z][a-z0-9-]*-plugin-root>")


def skill_dirs(root: Path) -> list[Path]:
    return sorted(d for d in root.iterdir() if d.is_dir() and (d / "SKILL.md").is_file())


def frontmatter(skill: Path) -> dict[str, str]:
    lines = (skill / "SKILL.md").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError(f"{skill.name}: no frontmatter")
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        key, separator, value = line.partition(":")
        if separator and not key.startswith(" "):
            fields[key.strip()] = value.strip().strip('"')
    return fields


def banner(skill: Path) -> str:
    """The blockquote between the frontmatter and the first heading."""
    lines = (skill / "SKILL.md").read_text(encoding="utf-8").splitlines()
    closing = next(i for i, line in enumerate(lines[1:], 1) if line == "---")
    quoted = []
    for line in lines[closing + 1 :]:
        if line.startswith("# "):
            break
        if line.startswith(">"):
            quoted.append(line)
    return "\n".join(quoted)


def ignored_names() -> set[str]:
    names = set()
    for raw in (REPO / ".braidignore").read_text(encoding="utf-8").splitlines():
        value = raw.split("#", 1)[0].strip()
        if value:
            names.add(value)
    return names


@pytest.mark.parametrize("skill", skill_dirs(SKILLS), ids=lambda p: p.name)
def test_runnable_skill_is_not_a_documentation_copy(skill: Path) -> None:
    """A skill only Claude can run must not sit where every host discovers it.

    This is the gateguard case: SKILL.md alone, frontmatter admitting it does
    nothing without a Claude plugin hook, and Copilot listing it anyway.
    """
    compatibility = frontmatter(skill).get("compatibility", "")
    assert not CLAUDE_ONLY.search(compatibility), (
        f"{skill.name} declares itself Claude-only but lives in skills/, "
        f"where Codex, Copilot and Gemini all discover it. Move it to "
        f"docs/plugin-skills/{skill.name}/ and drop any .braidignore entry.\n"
        f"  compatibility: {compatibility}"
    )


@pytest.mark.parametrize("skill", skill_dirs(DOC_COPIES), ids=lambda p: p.name)
def test_documentation_copy_declares_itself(skill: Path) -> None:
    compatibility = frontmatter(skill).get("compatibility", "")
    assert compatibility.startswith("Documentation copy of the "), (
        f"{skill.name}: compatibility must open with 'Documentation copy of the "
        f"<plugin> plugin skill' and name what stayed behind.\n"
        f"  compatibility: {compatibility or '(absent)'}"
    )


@pytest.mark.parametrize("skill", skill_dirs(DOC_COPIES), ids=lambda p: p.name)
def test_documentation_copy_carries_a_banner(skill: Path) -> None:
    """A model that skipped the frontmatter still has to learn it cannot run."""
    assert banner(skill), (
        f"{skill.name}: needs a blockquote banner between the frontmatter and "
        f"the first heading saying the copy is a specification, not a runnable "
        f"procedure."
    )


@pytest.mark.parametrize("skill", skill_dirs(DOC_COPIES), ids=lambda p: p.name)
def test_documentation_copy_uses_a_marker_that_cannot_half_resolve(skill: Path) -> None:
    """`${CLAUDE_PLUGIN_ROOT}` expands to nothing off Claude Code.

    A shell then turns `${CLAUDE_PLUGIN_ROOT}/skills/x` into `/skills/x`, which
    silently addresses the wrong place. `<name-plugin-root>/` fails loudly.
    """
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert "${CLAUDE_PLUGIN_ROOT}" not in text, (
        f"{skill.name}: replace ${{CLAUDE_PLUGIN_ROOT}} with a "
        f"<name-plugin-root>/ marker, which cannot expand to nothing."
    )
    everything = " ".join(path.read_text(encoding="utf-8") for path in skill.rglob("*.md"))
    assert PLUGIN_MARKER.search(everything), (
        f"{skill.name}: names no <name-plugin-root>/ path anywhere, so nothing "
        f"tells a reader where the missing half lives."
    )


@pytest.mark.parametrize("skill", skill_dirs(DOC_COPIES), ids=lambda p: p.name)
def test_documentation_copy_has_no_braidignore_entry(skill: Path) -> None:
    """Placement is what hides it; an entry here would imply .braidignore does."""
    assert skill.name not in ignored_names(), (
        f"{skill.name} is in .braidignore, but braid never sees it - it lives "
        f"outside skills/. Drop the entry; it reads as policy that does nothing."
    )


def test_no_name_is_both_a_skill_and_a_documentation_copy() -> None:
    collisions = {d.name for d in skill_dirs(SKILLS)} & {d.name for d in skill_dirs(DOC_COPIES)}
    assert not collisions, f"same name in skills/ and docs/plugin-skills/: {sorted(collisions)}"

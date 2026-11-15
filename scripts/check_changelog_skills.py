"""Check that all skills are named in CHANGELOG.md."""

import re
import sys
from pathlib import Path

GRANDFATHERED = []

REPO_ROOT = Path(__file__).resolve().parent.parent


def _is_named(skill_name: str, text: str) -> bool:
    """True when the literal name appears with no skill-name character on either side."""
    return re.search(rf"(?<![\w-]){re.escape(skill_name)}(?![\w-])", text) is not None


def find_missing(skills_dir: Path, changelog_path: Path) -> list[str]:
    """Return sorted skill names missing from the changelog, GRANDFATHERED names excluded."""
    skills_dir = Path(skills_dir)
    changelog_path = Path(changelog_path)
    changelog_content = changelog_path.read_text()

    # A skill is a directory holding a SKILL.md file, the same test braid applies.
    skill_names = [item.name for item in skills_dir.iterdir() if (item / "SKILL.md").is_file()]

    missing = [
        skill_name
        for skill_name in skill_names
        if skill_name not in GRANDFATHERED and not _is_named(skill_name, changelog_content)
    ]

    return sorted(missing)


def main(argv: list[str] | None = None) -> int:
    """Print each missing skill to stderr and return 1; return 0 if none are missing."""
    skills_dir = REPO_ROOT / "skills"
    changelog_path = REPO_ROOT / "CHANGELOG.md"

    missing = find_missing(skills_dir, changelog_path)

    if missing:
        for skill_name in missing:
            print(f"{skill_name}: not named in CHANGELOG.md", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Check that all skills are named in CHANGELOG.md."""

import sys
from pathlib import Path

GRANDFATHERED = [
    "catchup-ecc",
    "check-python-compat",
    "digest-github-repo",
    "e2e-testing",
    "frontend-patterns",
    "manage-agents-md",
    "python-patterns",
    "research",
    "resolve-git-conflicts",
    "review-deps-prs",
    "review-with-doubt",
    "rust-testing",
    "sync-plan-issue",
    "watch-ci",
]


def find_missing(skills_dir, changelog_path):
    """Return sorted list of skill names not named in changelog.

    Args:
        skills_dir: Path to skills directory
        changelog_path: Path to CHANGELOG.md file

    Returns:
        Sorted list of skill names (directories in skills_dir) that are:
        - Not found as substring in changelog
        - Not in GRANDFATHERED list
    """
    skills_dir = Path(skills_dir)
    changelog_path = Path(changelog_path)

    # Read changelog content
    changelog_content = changelog_path.read_text()

    # Get all skill directory names
    skill_names = []
    for item in skills_dir.iterdir():
        if item.is_dir():
            skill_names.append(item.name)

    # Find missing skills
    missing = []
    changelog_lower = changelog_content.lower()
    for skill_name in skill_names:
        # Skip grandfathered skills
        if skill_name in GRANDFATHERED:
            continue

        # Check if skill name appears in changelog as a case-insensitive substring
        if skill_name.lower() not in changelog_lower:
            missing.append(skill_name)

    return sorted(missing)


def main(argv=None):
    """Check for missing changelog entries for skills.

    Args:
        argv: Optional argument list (for testing)

    Returns:
        0 if no missing skills, 1 if missing skills found
    """
    # Resolve paths from current working directory (repo root)
    skills_dir = Path.cwd() / "skills"
    changelog_path = Path.cwd() / "CHANGELOG.md"

    # Find missing skills
    missing = find_missing(skills_dir, changelog_path)

    # If there are missing skills, print to stderr and exit 1
    if missing:
        for skill_name in missing:
            print(f"{skill_name}: not named in CHANGELOG.md", file=sys.stderr)
        return 1

    # No missing skills, exit 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

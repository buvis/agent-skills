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

REPO_ROOT = Path(__file__).resolve().parent.parent


def find_missing(skills_dir: Path, changelog_path: Path) -> list[str]:
    """Return sorted skill names missing from the changelog, GRANDFATHERED names excluded."""
    skills_dir = Path(skills_dir)
    changelog_path = Path(changelog_path)
    changelog_content = changelog_path.read_text()

    skill_names = [item.name for item in skills_dir.iterdir() if item.is_dir()]

    missing = [
        skill_name
        for skill_name in skill_names
        if skill_name not in GRANDFATHERED and skill_name not in changelog_content
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

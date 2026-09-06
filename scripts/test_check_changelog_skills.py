"""Tests for check_changelog_skills.py's skill changelog coverage check."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_changelog_skills as c


def _skills_tree(tmp_path: Path, changelog_text: str = "# Changelog\n") -> tuple[Path, Path]:
    """Create an empty skills/ dir and a CHANGELOG.md with the given text under tmp_path."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(changelog_text)
    return skills_dir, changelog


def test_reports_a_skill_dir_absent_from_the_changelog(tmp_path):
    """A skill directory not named in the changelog is reported missing."""
    skills_dir, changelog = _skills_tree(tmp_path)
    unlisted = skills_dir / "zz-unlisted"
    unlisted.mkdir()
    (unlisted / "SKILL.md").write_text("# zz-unlisted\n")

    assert c.find_missing(skills_dir, changelog) == ["zz-unlisted"]


def test_passes_when_every_skill_dir_is_named(tmp_path):
    """No missing skills when every skill dir name appears in the changelog."""
    skills_dir, changelog = _skills_tree(
        tmp_path, "# Changelog\n\n**skill-alpha**: added\n**skill-beta**: fixed\n"
    )
    (skills_dir / "skill-alpha").mkdir()
    (skills_dir / "skill-beta").mkdir()

    assert c.find_missing(skills_dir, changelog) == []


def test_grandfathered_name_is_skipped(tmp_path):
    """A grandfathered skill dir not in the changelog is not reported missing."""
    skills_dir, changelog = _skills_tree(tmp_path)
    (skills_dir / "python-patterns").mkdir()

    assert "python-patterns" not in c.find_missing(skills_dir, changelog)


class TestGrandfathered:
    """GRANDFATHERED constant holds exactly 14 verified names."""

    def test_grandfathered_has_exactly_14_names(self):
        assert len(c.GRANDFATHERED) == 14

    def test_grandfathered_contains_exact_names(self):
        expected = {
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
        }
        assert set(c.GRANDFATHERED) == expected

    def test_grandfathered_sorted(self):
        assert list(c.GRANDFATHERED) == sorted(c.GRANDFATHERED)


class TestFindMissing:
    """find_missing(skills_dir, changelog_path) returns sorted missing names."""

    def test_empty_skills_dir_returns_empty_list(self, tmp_path):
        """No skills, no missing skills."""
        skills_dir, changelog = _skills_tree(tmp_path)
        assert c.find_missing(skills_dir, changelog) == []

    def test_skill_named_in_changelog_not_missing(self, tmp_path):
        """Skill found as substring in changelog is not missing."""
        skills_dir, changelog = _skills_tree(
            tmp_path, "# Changelog\n\n**my-skill**: fixed something\n"
        )
        (skills_dir / "my-skill").mkdir()

        assert c.find_missing(skills_dir, changelog) == []

    def test_substring_matching_requires_literal_substring(self, tmp_path):
        """Literal substring matching: embedded in longer word counts as found."""
        skills_dir, changelog = _skills_tree(tmp_path, "# Changelog\n\n**foobar**: added feature\n")
        (skills_dir / "foo").mkdir()
        (skills_dir / "fu").mkdir()

        # "foo" is a literal substring of "foobar" (chars 0-3), so it's found.
        # "fu" is NOT a substring of "foobar", so it's missing.
        assert c.find_missing(skills_dir, changelog) == ["fu"]

    def test_multiple_missing_skills_returned_sorted(self, tmp_path):
        """Multiple missing skills returned in sorted order."""
        skills_dir, changelog = _skills_tree(tmp_path)
        (skills_dir / "zebra").mkdir()
        (skills_dir / "apple").mkdir()
        (skills_dir / "middle").mkdir()

        result = c.find_missing(skills_dir, changelog)
        assert result == ["apple", "middle", "zebra"]

    def test_mixed_present_and_missing(self, tmp_path):
        """Mix of present and missing skills; only missing returned."""
        skills_dir, changelog = _skills_tree(
            tmp_path, "# Changelog\n\n**in-changelog**: something\n"
        )
        (skills_dir / "in-changelog").mkdir()
        (skills_dir / "not-in-changelog").mkdir()

        result = c.find_missing(skills_dir, changelog)
        assert result == ["not-in-changelog"]

    def test_grandfathered_and_missing_mixed(self, tmp_path):
        """Grandfathered skipped, only non-grandfathered missing returned."""
        skills_dir, changelog = _skills_tree(tmp_path)
        (skills_dir / "catchup-ecc").mkdir()
        (skills_dir / "some-new-skill").mkdir()

        result = c.find_missing(skills_dir, changelog)
        assert result == ["some-new-skill"]

    def test_ignores_non_directory_files_in_skills_dir(self, tmp_path):
        """Only directories under skills_dir are checked, not files."""
        skills_dir, changelog = _skills_tree(tmp_path)
        (skills_dir / "readme.txt").write_text("x")
        (skills_dir / "skill-dir").mkdir()

        result = c.find_missing(skills_dir, changelog)
        assert result == ["skill-dir"]


class TestMain:
    """main(argv=None) resolves paths, calls find_missing, exits correctly."""

    def test_main_exit_0_when_no_missing(self, tmp_path, monkeypatch, capsys):
        """Exit 0 and print nothing when all skills are in changelog."""
        monkeypatch.setattr(c, "REPO_ROOT", tmp_path)
        skills_dir, changelog = _skills_tree(tmp_path, "# Changelog\n\n**my-skill**: added\n")
        (skills_dir / "my-skill").mkdir()

        exit_code = c.main()
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_main_with_argv_parameter(self, tmp_path, monkeypatch):
        """main(argv) accepts an explicit argv and still returns the exact exit code."""
        monkeypatch.setattr(c, "REPO_ROOT", tmp_path)
        skills_dir, changelog = _skills_tree(tmp_path, "# Changelog\n\n**test-skill**: added\n")
        (skills_dir / "test-skill").mkdir()

        assert c.main(argv=[]) == 0

    def test_main_grandfathered_excluded_from_missing(self, tmp_path, monkeypatch, capsys):
        """Grandfathered skills not in changelog are not reported as missing."""
        monkeypatch.setattr(c, "REPO_ROOT", tmp_path)
        skills_dir, changelog = _skills_tree(tmp_path)
        (skills_dir / "catchup-ecc").mkdir()
        (skills_dir / "actual-missing").mkdir()

        exit_code = c.main()
        assert exit_code == 1
        captured = capsys.readouterr()
        assert captured.err == "actual-missing: not named in CHANGELOG.md\n"


class TestIntegration:
    """Integration: find_missing and main work end to end."""

    def test_real_changelog_like_structure(self, tmp_path, monkeypatch, capsys):
        """Test with a changelog that resembles the real structure."""
        monkeypatch.setattr(c, "REPO_ROOT", tmp_path)
        skills_dir, changelog = _skills_tree(
            tmp_path,
            "# Changelog\n\n"
            "## [Unreleased]\n\n"
            "### Added\n\n"
            "- **skill-one**: new feature\n"
            "- **skill-two**: enhancement\n"
            "\n"
            "### Fixed\n\n"
            "- **skill-two**: bug fix\n",
        )
        (skills_dir / "skill-one").mkdir()
        (skills_dir / "skill-two").mkdir()
        (skills_dir / "skill-three").mkdir()

        exit_code = c.main()
        assert exit_code == 1
        captured = capsys.readouterr()
        assert captured.err == "skill-three: not named in CHANGELOG.md\n"


class TestFindMissingCaseSensitivity:
    """find_missing matches a skill name against the changelog text case-sensitively."""

    def test_different_case_occurrence_is_reported_missing(self, tmp_path):
        """A skill named only in a different letter case in the changelog is missing."""
        skills_dir, changelog = _skills_tree(tmp_path, "# Changelog\n\nAlpha was released today.\n")
        (skills_dir / "alpha").mkdir()

        assert c.find_missing(skills_dir, changelog) == ["alpha"]


class TestMainPathResolution:
    """main() resolves this repository's own skills/ and CHANGELOG.md, not paths relative to cwd."""

    def test_checks_real_repo_when_cwd_has_neither_skills_nor_changelog(
        self, tmp_path, monkeypatch, capsys
    ):
        """main() still checks this repo's real skills/ and CHANGELOG.md when cwd has neither."""
        monkeypatch.chdir(tmp_path)

        exit_code = c.main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""


class TestMainStderrContract:
    """main() writes exactly one sorted stderr line per missing name, and nothing else."""

    def test_stderr_is_exactly_sorted_missing_lines_and_nothing_else(
        self, tmp_path, monkeypatch, capsys
    ):
        """Complete stderr equals the sorted, formatted missing-name lines, no more and no less."""
        monkeypatch.setattr(c, "REPO_ROOT", tmp_path)
        skills_dir, changelog = _skills_tree(tmp_path)
        (skills_dir / "zeta").mkdir()
        (skills_dir / "delta").mkdir()

        exit_code = c.main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == (
            "delta: not named in CHANGELOG.md\nzeta: not named in CHANGELOG.md\n"
        )

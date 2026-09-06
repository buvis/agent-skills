"""Tests for check_changelog_skills.py's skill changelog coverage check."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_changelog_skills as c


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
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")
        assert c.find_missing(skills_dir, changelog) == []

    def test_skill_named_in_changelog_not_missing(self, tmp_path):
        """Skill found as substring in changelog is not missing."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "my-skill").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n**my-skill**: fixed something\n")

        assert c.find_missing(skills_dir, changelog) == []

    def test_skill_not_named_in_changelog_is_missing(self, tmp_path):
        """Skill not found in changelog is missing and returned."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "my-skill").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        assert c.find_missing(skills_dir, changelog) == ["my-skill"]

    def test_grandfathered_not_in_changelog_not_missing(self, tmp_path):
        """Grandfathered name not in changelog is still not missing."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "catchup-ecc").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        assert c.find_missing(skills_dir, changelog) == []

    def test_substring_matching_finds_skill(self, tmp_path):
        """Substring match counts: if changelog contains skill name, it's found."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "foo").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n**foo**: added feature\n")

        assert c.find_missing(skills_dir, changelog) == []

    def test_substring_matching_requires_literal_substring(self, tmp_path):
        """Skill name must appear as literal substring, not similar."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "foo").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n**foobar**: added feature\n")

        assert c.find_missing(skills_dir, changelog) == ["foo"]

    def test_multiple_missing_skills_returned_sorted(self, tmp_path):
        """Multiple missing skills returned in sorted order."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "zebra").mkdir()
        (skills_dir / "apple").mkdir()
        (skills_dir / "middle").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        result = c.find_missing(skills_dir, changelog)
        assert result == ["apple", "middle", "zebra"]

    def test_mixed_present_and_missing(self, tmp_path):
        """Mix of present and missing skills; only missing returned."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "in-changelog").mkdir()
        (skills_dir / "not-in-changelog").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n**in-changelog**: something\n")

        result = c.find_missing(skills_dir, changelog)
        assert result == ["not-in-changelog"]

    def test_grandfathered_and_missing_mixed(self, tmp_path):
        """Grandfathered skipped, only non-grandfathered missing returned."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "catchup-ecc").mkdir()
        (skills_dir / "some-new-skill").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        result = c.find_missing(skills_dir, changelog)
        assert result == ["some-new-skill"]

    def test_skill_with_hyphens_matched_exactly(self, tmp_path):
        """Hyphenated skill name matched exactly as substring."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "my-skill-name").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n**my-skill-name**: update\n")

        assert c.find_missing(skills_dir, changelog) == []

    def test_ignores_non_directory_files_in_skills_dir(self, tmp_path):
        """Only directories under skills_dir are checked, not files."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "readme.txt").write_text("x")
        (skills_dir / "skill-dir").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        result = c.find_missing(skills_dir, changelog)
        assert result == ["skill-dir"]

    def test_changelog_content_is_searched_literally(self, tmp_path):
        """Changelog text is searched for exact substring of skill name."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "test").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\nTesting framework added.\n")

        result = c.find_missing(skills_dir, changelog)
        assert result == []


class TestMain:
    """main(argv=None) resolves paths, calls find_missing, exits correctly."""

    def test_main_exit_0_when_no_missing(self, tmp_path, monkeypatch, capsys):
        """Exit 0 and print nothing when all skills are in changelog."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "my-skill").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n**my-skill**: added\n")

        exit_code = c.main()
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_main_exit_1_when_missing_skills(self, tmp_path, monkeypatch, capsys):
        """Exit 1 and print to stderr when skills are missing."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "missing-skill").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        exit_code = c.main()
        assert exit_code == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "missing-skill: not named in CHANGELOG.md" in captured.err

    def test_main_stderr_format_one_line_per_missing(self, tmp_path, monkeypatch, capsys):
        """Each missing skill printed to stderr in format '<name>: not named in CHANGELOG.md'."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "alpha").mkdir()
        (skills_dir / "beta").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        exit_code = c.main()
        assert exit_code == 1
        captured = capsys.readouterr()
        lines = captured.err.strip().split("\n")
        assert len(lines) == 2
        assert "alpha: not named in CHANGELOG.md" in captured.err
        assert "beta: not named in CHANGELOG.md" in captured.err

    def test_main_missing_skills_printed_sorted_order(self, tmp_path, monkeypatch, capsys):
        """Missing skills printed in sorted order."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "z-skill").mkdir()
        (skills_dir / "a-skill").mkdir()
        (skills_dir / "m-skill").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        c.main()
        captured = capsys.readouterr()
        lines = captured.err.strip().split("\n")
        assert lines[0].startswith("a-skill:")
        assert lines[1].startswith("m-skill:")
        assert lines[2].startswith("z-skill:")

    def test_main_with_argv_parameter(self, tmp_path, capsys):
        """main(argv) accepts explicit argv for testing."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "test-skill").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        result = c.main(argv=None)
        assert result in (0, 1)

    def test_main_resolves_skills_and_changelog_from_repo_root(self, tmp_path, monkeypatch, capsys):
        """main() resolves skills/ and CHANGELOG.md from repo root."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "found-skill").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n**found-skill**: added\n")

        exit_code = c.main()
        assert exit_code == 0

    def test_main_grandfathered_excluded_from_missing(self, tmp_path, monkeypatch, capsys):
        """Grandfathered skills not in changelog are not reported as missing."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "catchup-ecc").mkdir()
        (skills_dir / "actual-missing").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        exit_code = c.main()
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "catchup-ecc" not in captured.err
        assert "actual-missing: not named in CHANGELOG.md" in captured.err

    def test_main_no_output_on_stdout_ever(self, tmp_path, monkeypatch, capsys):
        """main() never prints to stdout, only stderr."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "missing").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        c.main()
        captured = capsys.readouterr()
        assert captured.out == ""


class TestIntegration:
    """Integration: find_missing and main work end to end."""

    def test_real_changelog_like_structure(self, tmp_path, monkeypatch, capsys):
        """Test with a changelog that resembles the real structure."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "skill-one").mkdir()
        (skills_dir / "skill-two").mkdir()
        (skills_dir / "skill-three").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\n"
            "## [Unreleased]\n\n"
            "### Added\n\n"
            "- **skill-one**: new feature\n"
            "- **skill-two**: enhancement\n"
            "\n"
            "### Fixed\n\n"
            "- **skill-two**: bug fix\n"
        )

        exit_code = c.main()
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "skill-one: not named in CHANGELOG.md" not in captured.err
        assert "skill-two: not named in CHANGELOG.md" not in captured.err
        assert "skill-three: not named in CHANGELOG.md" in captured.err

    def test_acceptance_no_missing_exit_0_no_output(self, tmp_path, monkeypatch, capsys):
        """Acceptance: no missing -> exit 0, nothing on stdout/stderr."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        exit_code = c.main()
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_acceptance_missing_exit_1_stderr_format(self, tmp_path, monkeypatch, capsys):
        """Acceptance: missing -> exit 1, one line per miss on stderr."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "one").mkdir()
        (skills_dir / "two").mkdir()

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n")

        exit_code = c.main()
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "one: not named in CHANGELOG.md" in captured.err
        assert "two: not named in CHANGELOG.md" in captured.err

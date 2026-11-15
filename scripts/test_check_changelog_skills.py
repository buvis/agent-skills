"""Tests for check_changelog_skills.py's skill changelog coverage check."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import check_changelog_skills as c


def _skills_tree(tmp_path: Path, changelog_text: str = "# Changelog\n") -> tuple[Path, Path]:
    """Create an empty skills/ dir and a CHANGELOG.md with the given text under tmp_path."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(changelog_text)
    return skills_dir, changelog


def _skill(skills_dir: Path, name: str) -> Path:
    """Create a real skill: a directory holding a SKILL.md file."""
    skill = skills_dir / name
    skill.mkdir()
    (skill / "SKILL.md").write_text(f"# {name}\n")
    return skill


def test_reports_a_skill_dir_absent_from_the_changelog(tmp_path):
    """A skill directory not named in the changelog is reported missing."""
    skills_dir, changelog = _skills_tree(tmp_path)
    _skill(skills_dir, "zz-unlisted")

    assert c.find_missing(skills_dir, changelog) == ["zz-unlisted"]


def test_passes_when_every_skill_dir_is_named(tmp_path):
    """No missing skills when every skill dir name appears in the changelog."""
    skills_dir, changelog = _skills_tree(
        tmp_path, "# Changelog\n\n**skill-alpha**: added\n**skill-beta**: fixed\n"
    )
    _skill(skills_dir, "skill-alpha")
    _skill(skills_dir, "skill-beta")

    assert c.find_missing(skills_dir, changelog) == []


class TestGrandfathered:
    """GRANDFATHERED is empty now that every skill is named in CHANGELOG.md."""

    def test_grandfathered_is_empty(self):
        assert c.GRANDFATHERED == []


class TestFindMissing:
    """find_missing(skills_dir, changelog_path) returns sorted missing names."""

    def test_empty_skills_dir_returns_empty_list(self, tmp_path):
        """No skills, no missing skills."""
        skills_dir, changelog = _skills_tree(tmp_path)
        assert c.find_missing(skills_dir, changelog) == []

    def test_skill_named_in_changelog_not_missing(self, tmp_path):
        """A distinct mention of the skill name covers it."""
        skills_dir, changelog = _skills_tree(
            tmp_path, "# Changelog\n\n**my-skill**: fixed something\n"
        )
        _skill(skills_dir, "my-skill")

        assert c.find_missing(skills_dir, changelog) == []

    def test_name_embedded_in_a_longer_word_does_not_count(self, tmp_path):
        """A name found only inside a longer word is missing."""
        skills_dir, changelog = _skills_tree(tmp_path, "# Changelog\n\n**foobar**: added feature\n")
        _skill(skills_dir, "foo")
        _skill(skills_dir, "fu")

        assert c.find_missing(skills_dir, changelog) == ["foo", "fu"]

    def test_name_inside_a_longer_hyphenated_skill_name_does_not_count(self, tmp_path):
        """'skill' and 'use' inside 'create-skill' and 'use-qwen' are not distinct mentions."""
        skills_dir, changelog = _skills_tree(
            tmp_path, "# Changelog\n\n- **create-skill**: fixed\n- **use-qwen**: added\n"
        )
        for name in ("create-skill", "use-qwen", "skill", "use", "create"):
            _skill(skills_dir, name)

        assert c.find_missing(skills_dir, changelog) == ["create", "skill", "use"]

    def test_hyphenated_name_is_not_covered_by_a_longer_one(self, tmp_path):
        """'use-qwen' inside 'use-qwen-local' is not a distinct mention."""
        skills_dir, changelog = _skills_tree(
            tmp_path, "# Changelog\n\n- **use-qwen-local**: added\n"
        )
        _skill(skills_dir, "use-qwen")

        assert c.find_missing(skills_dir, changelog) == ["use-qwen"]

    @pytest.mark.parametrize(
        "mention",
        [
            "- **fix**: something",
            "- the `fix` skill changed",
            "- fix now handles more cases",
            "- **braid**, **fix**: shared change",
            "- see skills/fix/SKILL.md.",
            "- (fix)",
        ],
    )
    def test_distinct_mention_in_any_existing_format_counts(self, tmp_path, mention):
        """Bold, backtick, plain prose, list and path mentions all cover the skill."""
        skills_dir, changelog = _skills_tree(tmp_path, f"# Changelog\n\n{mention}\n")
        _skill(skills_dir, "fix")

        assert c.find_missing(skills_dir, changelog) == []

    def test_name_with_regex_metacharacters_is_matched_literally(self, tmp_path):
        """A name is escaped before it becomes a pattern."""
        skills_dir, changelog = _skills_tree(tmp_path, "# Changelog\n\n- **aXb**: added\n")
        _skill(skills_dir, "a.b")

        assert c.find_missing(skills_dir, changelog) == ["a.b"]

    def test_multiple_missing_skills_returned_sorted(self, tmp_path):
        """Multiple missing skills returned in sorted order."""
        skills_dir, changelog = _skills_tree(tmp_path)
        _skill(skills_dir, "zebra")
        _skill(skills_dir, "apple")
        _skill(skills_dir, "middle")

        result = c.find_missing(skills_dir, changelog)
        assert result == ["apple", "middle", "zebra"]

    def test_mixed_present_and_missing(self, tmp_path):
        """Mix of present and missing skills; only missing returned."""
        skills_dir, changelog = _skills_tree(
            tmp_path, "# Changelog\n\n**in-changelog**: something\n"
        )
        _skill(skills_dir, "in-changelog")
        _skill(skills_dir, "not-in-changelog")

        result = c.find_missing(skills_dir, changelog)
        assert result == ["not-in-changelog"]

    def test_empty_grandfathered_reports_everything_missing(self, tmp_path):
        """With GRANDFATHERED empty, every unlisted skill dir is reported missing."""
        skills_dir, changelog = _skills_tree(tmp_path)
        _skill(skills_dir, "catchup-ecc")
        _skill(skills_dir, "some-new-skill")

        result = c.find_missing(skills_dir, changelog)
        assert result == ["catchup-ecc", "some-new-skill"]

    def test_ignores_non_directory_files_in_skills_dir(self, tmp_path):
        """Only directories under skills_dir are checked, not files."""
        skills_dir, changelog = _skills_tree(tmp_path)
        (skills_dir / "readme.txt").write_text("x")
        _skill(skills_dir, "skill-dir")

        result = c.find_missing(skills_dir, changelog)
        assert result == ["skill-dir"]

    def test_ignores_stray_directory_without_skill_md(self, tmp_path):
        """A directory without a SKILL.md file is not a skill and needs no entry."""
        skills_dir, changelog = _skills_tree(tmp_path)
        stray = skills_dir / "purge-devlocal"
        stray.mkdir()
        (stray / "notes.md").write_text("x")
        (skills_dir / "empty-dir").mkdir()
        _skill(skills_dir, "zz-never-mentioned")

        assert c.find_missing(skills_dir, changelog) == ["zz-never-mentioned"]

    def test_skill_md_directory_does_not_make_a_skill(self, tmp_path):
        """SKILL.md must be a file; a directory of that name does not qualify."""
        skills_dir, changelog = _skills_tree(tmp_path)
        (skills_dir / "odd" / "SKILL.md").mkdir(parents=True)

        assert c.find_missing(skills_dir, changelog) == []


class TestMain:
    """main(argv=None) resolves paths, calls find_missing, exits correctly."""

    def test_main_exit_0_when_no_missing(self, tmp_path, monkeypatch, capsys):
        """Exit 0 and print nothing when all skills are in changelog."""
        monkeypatch.setattr(c, "REPO_ROOT", tmp_path)
        skills_dir, changelog = _skills_tree(tmp_path, "# Changelog\n\n**my-skill**: added\n")
        _skill(skills_dir, "my-skill")

        exit_code = c.main()
        assert exit_code == 0
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_main_with_argv_parameter(self, tmp_path, monkeypatch):
        """main(argv) accepts an explicit argv and still returns the exact exit code."""
        monkeypatch.setattr(c, "REPO_ROOT", tmp_path)
        skills_dir, changelog = _skills_tree(tmp_path, "# Changelog\n\n**test-skill**: added\n")
        _skill(skills_dir, "test-skill")

        assert c.main(argv=[]) == 0

    def test_main_reports_every_unlisted_skill_with_grandfathered_empty(
        self, tmp_path, monkeypatch, capsys
    ):
        """With GRANDFATHERED empty, every unlisted skill dir is reported as missing."""
        monkeypatch.setattr(c, "REPO_ROOT", tmp_path)
        skills_dir, changelog = _skills_tree(tmp_path)
        _skill(skills_dir, "catchup-ecc")
        _skill(skills_dir, "actual-missing")

        exit_code = c.main()
        assert exit_code == 1
        captured = capsys.readouterr()
        assert captured.err == (
            "actual-missing: not named in CHANGELOG.md\ncatchup-ecc: not named in CHANGELOG.md\n"
        )


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
        _skill(skills_dir, "skill-one")
        _skill(skills_dir, "skill-two")
        _skill(skills_dir, "skill-three")

        exit_code = c.main()
        assert exit_code == 1
        captured = capsys.readouterr()
        assert captured.err == "skill-three: not named in CHANGELOG.md\n"


class TestFindMissingCaseSensitivity:
    """find_missing matches a skill name against the changelog text case-sensitively."""

    def test_different_case_occurrence_is_reported_missing(self, tmp_path):
        """A skill named only in a different letter case in the changelog is missing."""
        skills_dir, changelog = _skills_tree(tmp_path, "# Changelog\n\nAlpha was released today.\n")
        _skill(skills_dir, "alpha")

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
        _skill(skills_dir, "zeta")
        _skill(skills_dir, "delta")

        exit_code = c.main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == (
            "delta: not named in CHANGELOG.md\nzeta: not named in CHANGELOG.md\n"
        )

"""Guard the retirement of the bundled braid v1 package.

braid ships in buvis-gems. This repository is a content repo: no Python
package, no launcher, and docs that point at the gems braid.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

REPO = Path(__file__).resolve().parents[1]

PROSE_FIRST_PARAGRAPH = (
    "Portable personal skills for AI coding assistants. They reach each assistant "
    "through braid, the composer in [buvis-gems](https://github.com/buvis/gems)."
)
INSTALL_SENTENCE = (
    "If ~/.config/buvis/buvis-braid.yaml already exists, add "
    "- ~/git/src/github.com/buvis/agent-skills to its existing sources list before "
    "you run the commands below; appending a second sources: key makes the YAML invalid."
)
INSTALL_BLOCK = (
    "```bash\n"
    "git clone https://github.com/buvis/agent-skills ~/git/src/github.com/buvis/agent-skills\n"
    "uv tool install buvis-gems\n"
    "mkdir -p ~/.config/buvis\n"
    "test -e ~/.config/buvis/buvis-braid.yaml || printf 'sources:\\n"
    "  - ~/git/src/github.com/buvis/agent-skills\\n' > ~/.config/buvis/buvis-braid.yaml\n"
    "braid --dry-run\n"
    "braid\n"
    "braid --check\n"
    "```"
)
DOCS_SENTENCE = (
    "braid usage, flags, machine-local sources, Kiro enrollment and Windows behavior "
    "are documented in buvis-gems (docs/source/tools/braid.rst)."
)
SOURCES_SENTENCE = (
    "braid reads source repositories from the sources list in "
    "~/.config/buvis/buvis-braid.yaml; machine-only sources go in "
    "~/.local/.config/buvis/buvis-braid.yaml."
)
# Legacy names are built from fragments so this file does not match its own scan.
OLD_MODULE = "agent_skills_" + "braid"
OLD_DIST = "agent-skills-" + "braid"
OLD_LAUNCHER = "bin/" + "braid"
CHANGELOG_ENTRY = (
    f"- **braid**: the bundled {OLD_DIST} package; install braid from "
    "buvis-gems and list sources in ~/.config/buvis/buvis-braid.yaml"
)

STALE = re.compile(
    OLD_MODULE + "|" + OLD_DIST + "|" + OLD_LAUNCHER + "|AGENT_SKILLS_" + "CONFIG"
    "|config/agent-" + "skills"
)


def read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def pyproject() -> dict:
    return tomllib.loads(read("pyproject.toml"))


@pytest.mark.parametrize(
    "rel",
    [
        f"src/{OLD_MODULE}",
        f"src/{OLD_MODULE}/cli.py",
        f"src/{OLD_MODULE}/__init__.py",
        OLD_LAUNCHER,
        f"{OLD_LAUNCHER}.py",
        "tests/test_braid.py",
        "tests/test_braid_check.py",
        "tests/test_readme_windows.py",
    ],
)
def test_bundled_braid_file_is_deleted(rel: str) -> None:
    assert not (REPO / rel).exists(), f"{rel} must be removed"


def test_pyproject_is_a_non_package_named_agent_skills() -> None:
    data = pyproject()
    assert data["project"]["name"] == "agent-skills"
    assert data["project"]["description"] == "Portable agent skills for AI coding assistants"
    assert data["project"]["version"]
    assert data["tool"]["uv"]["package"] is False


def test_pyproject_drops_build_and_script_tables() -> None:
    data = pyproject()
    assert "build-system" not in data
    assert "scripts" not in data["project"]
    assert "hatch" not in data.get("tool", {})


def test_pyproject_keeps_dev_tooling_unchanged() -> None:
    data = pyproject()
    assert "dependency-groups" in data
    assert "ini_options" in data["tool"]["pytest"]
    assert "lint" in data["tool"]["ruff"]
    assert "ruff" in data["tool"]


def test_lockfile_describes_the_renamed_project() -> None:
    lock = read("uv.lock")
    assert 'name = "agent-skills"' in lock
    assert OLD_DIST not in lock
    assert 'source = { virtual = "." }' in lock


def test_ci_lint_step_is_named_lint_exactly_once() -> None:
    ci = read(".github/workflows/ci.yml")
    assert len(re.findall(r"^\s*- name: Lint$", ci, re.M)) == 1
    assert "Lint braid" not in ci


def test_readme_opens_with_the_gems_braid_paragraph() -> None:
    readme = read("README.md")
    assert readme.startswith("# agent-skills\n\n" + PROSE_FIRST_PARAGRAPH + "\n")
    assert "plus `braid`, the composer" not in readme


def test_readme_install_points_at_gems_braid() -> None:
    readme = read("README.md")
    install = readme.split("## Install\n", 1)[1].split("\n## ", 1)[0]
    assert INSTALL_SENTENCE in install
    assert INSTALL_BLOCK in install
    assert DOCS_SENTENCE in install
    assert (
        install.index(INSTALL_SENTENCE)
        < install.index(INSTALL_BLOCK)
        < install.index(DOCS_SENTENCE)
    )
    assert "editable" not in install
    assert "bin/" not in install


def test_readme_names_the_buvis_braid_sources_file() -> None:
    readme = read("README.md")
    assert SOURCES_SENTENCE in readme
    assert "sources.d" not in readme
    assert "~/.config/agent-" + "skills" not in readme


def test_readme_replaces_braid_manual_with_braidignore_heading() -> None:
    readme = read("README.md")
    assert re.search(r"^## braid$", readme, re.M) is None
    assert len(re.findall(r"^## \.braidignore$", readme, re.M)) == 1
    section = readme.split("## .braidignore\n", 1)[1].split("\n## ", 1)[0]
    assert "`.braidignore` is intentional policy, not an error list." in section
    assert "It is not a way to hide a skill from Codex or Copilot." in section
    assert "braid loads it from\n~/.agents," in section
    assert "the tool repository" not in readme
    assert "no Bash runtime" not in readme
    assert "--config-root" not in readme
    # The Windows CI paragraph described the deleted braid's junction tests.
    assert "junction" not in readme


def test_agents_md_describes_gems_braid_scan() -> None:
    agents = read("AGENTS.md")
    assert "`skills/` is the only directory braid (buvis-gems) scans for skills" in agents
    assert "_skills_directory" not in agents


def test_changelog_unreleased_records_the_removal() -> None:
    changelog = read("CHANGELOG.md")
    assert CHANGELOG_ENTRY in changelog.splitlines()


def test_no_tracked_file_mentions_the_old_braid() -> None:
    listing = (
        subprocess.run(
            ["git", "ls-files", "-z", "-co", "--exclude-standard"],
            cwd=REPO,
            capture_output=True,
            check=True,
            timeout=60,
        )
        .stdout.decode("utf-8")
        .split("\0")
    )
    hits = []
    for rel in filter(None, listing):
        if rel == "CHANGELOG.md" or rel.startswith("docs/dev/"):
            continue
        path = REPO / rel
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="replace")
        hits.extend(f"{rel}: {m.group(0)}" for m in STALE.finditer(text))
    assert not hits, hits

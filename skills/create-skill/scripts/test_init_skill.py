"""Tests for init_skill.py's printed next-steps output."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import init_skill


def test_printed_validate_step_names_the_union_path(tmp_path, capsys):
    skill_dir = init_skill.init_skill("probe-skill", str(tmp_path), [])
    assert skill_dir is not None

    captured = capsys.readouterr()
    assert (
        "3. Validate: python3 ~/.agents/skills/create-skill/scripts/validate_skill.py"
        in captured.out
    )
    assert "~/.claude/skills/" not in captured.out

    validate_lines = [
        line for line in captured.out.splitlines() if line.strip().startswith("3. Validate:")
    ]
    assert len(validate_lines) == 1
    assert str(skill_dir) in validate_lines[0]

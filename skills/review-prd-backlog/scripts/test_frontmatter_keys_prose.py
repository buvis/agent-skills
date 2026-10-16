"""Pin create-prd and the backlog gate to one frontmatter key set (PRD 00080)."""
import re
from pathlib import Path

KEYS = (
    "catchup",
    "rework_cap",
    "design",
    "design_gate",
    "doubt_reviewer",
    "consensus_engine",
    "pause_on_ambiguity",
    "plan_expansion",
    "session_model",
    "lane",
    "eligibility",
    "default_model",
)

GATE = Path(__file__).resolve().parents[1] / "SKILL.md"
CREATE_PRD = Path(__file__).resolve().parents[2] / "create-prd" / "SKILL.md"


def section(path: Path, start: str, end: str) -> list[str]:
    lines = path.read_text().splitlines()
    i = next(n for n, line in enumerate(lines) if line.startswith(start))
    j = next(n for n, line in enumerate(lines) if n > i and line.startswith(end))
    return lines[i + 1 : j]


def test_gate_recognizes_every_key_the_pipeline_parses():
    lens_a = section(GATE, "### A.", "### B.")
    line = next(line for line in lens_a if line.startswith("- Frontmatter:"))
    for key in KEYS:
        assert re.search("`" + key + "[`:]", line), f"lens A Frontmatter line misses `{key}`"


def test_create_prd_lists_every_key_the_pipeline_parses():
    lines = section(CREATE_PRD, "### Optional frontmatter fields", "### 4. Split if needed")
    for key in KEYS:
        assert any(re.search("^- `" + key + "[`:]", line) for line in lines), (
            f"create-prd optional frontmatter list misses `{key}`"
        )


def test_create_prd_states_the_path_rule():
    step3 = section(CREATE_PRD, "### 3.", "### Optional frontmatter fields")
    rule = next((line for line in step3 if line.startswith("**Path rule")), None)
    assert rule, "create-prd step 3 has no **Path rule paragraph"
    for phrase in ("repo-relative", "glob"):
        assert phrase in rule, f"Path rule paragraph misses {phrase!r}"


def test_gate_checks_the_path_rule():
    lens_c = section(GATE, "### C.", "### D.")
    rule = next((line for line in lens_c if line.startswith("- Path rule")), None)
    assert rule, "lens C has no '- Path rule' bullet"
    for phrase in ("repo-relative", "glob", "lane: fast-track"):
        assert phrase in rule, f"lens C Path rule bullet misses {phrase!r}"

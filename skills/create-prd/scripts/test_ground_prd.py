"""Tests for ground_prd.py: claim extraction, citation lens, symbol lens (PRD 00075)."""
from pathlib import Path

import ground_prd
from ground_prd import Claim


def make_repo(root: Path) -> Path:
    src = root / "src"
    src.mkdir(parents=True)
    (src / "app.py").write_text(
        "def alpha():\n    return 1\n\ndef beta():\n    return 2\n"
    )
    (src / "codec.py").write_text("class codec:\n    def parse_frame(self, data):\n        pass\n")
    return root


def kinds(text):
    return [(c.kind, c.token, c.line) for c in ground_prd.extract_claims(text)]


def citation_status(text, root):
    claims = ground_prd.extract_claims(text)
    result = ground_prd.check_citations(claims, root)
    return {c.token: result[c] for c in claims if c.kind == "citation"}


def symbol_status(tokens, root, declared=frozenset()):
    claims = [Claim("symbol", t, i + 1) for i, t in enumerate(tokens)]
    result = ground_prd.resolve_symbols(claims, root, set(declared))
    return {c.token: result[c] for c in claims}


# --- extract_claims ---------------------------------------------------------


def test_citation_keeps_full_path_and_ranges_as_token_with_line():
    claims = kinds("intro\nsee src/app.py:3-5,8-9 and docs/guide.md:7 here\n")
    assert [c for c in claims if c[0] == "citation"] == [
        ("citation", "src/app.py:3-5,8-9", 2),
        ("citation", "docs/guide.md:7", 2),
    ]


def test_colon_number_without_extensioned_path_is_not_a_citation():
    claims = kinds("ratio 3:4, meet at 10:30, step :12, see README:5\n")
    assert [c for c in claims if c[0] == "citation"] == []


def test_symbol_claims_come_from_backtick_identifiers_and_dotted_paths():
    claims = kinds("call `parse_frame` via `codec.parse_frame` or `codec::parse_frame`, not `ab`\n")
    assert claims == [
        ("symbol", "parse_frame", 1),
        ("symbol", "codec.parse_frame", 1),
        ("symbol", "codec::parse_frame", 1),
    ]


def test_symbol_excludes_file_names_paths_flags_and_placeholders():
    text = (
        "`config.yaml` `README.md` `Cargo.lock` `notes.txt` `page.html`\n"
        "`src/app` `two words` `-flag` `--verbose`\n"
        "`NNNNN` `prd_NNNNN` `XXXX` `YYYY_mm` `foo*` `<name>` `${HOME}` `a...b`\n"
        "keep `real_symbol`\n"
    )
    assert kinds(text) == [("symbol", "real_symbol", 4)]


def test_frontmatter_symbol_is_not_scanned_and_lines_count_from_original_text():
    text = "---\ntitle: `front_sym` see meta.md:1\n---\nbody `body_sym`\n"
    assert kinds(text) == [("symbol", "body_sym", 4)]


def test_fenced_block_yields_no_claims_and_keeps_line_numbers():
    text = (
        "intro\n"
        "```python\n"
        "`fenced_sym` inside.py:1\n"
        "```\n"
        "after `after_sym` outside.py:2\n"
    )
    assert sorted(kinds(text)) == [
        ("citation", "outside.py:2", 5),
        ("symbol", "after_sym", 5),
    ]


def test_link_ok_waiver_line_yields_no_citation_or_symbol():
    text = "link-ok: gone.py:4 `gone_sym` was removed\nkept.py:1 `kept_sym`\n"
    assert sorted(kinds(text)) == [("citation", "kept.py:1", 2), ("symbol", "kept_sym", 2)]


# --- check_citations --------------------------------------------------------


def test_citation_to_missing_file_is_missing(tmp_path):
    make_repo(tmp_path)
    assert citation_status("see src/ghost.py:1\n", tmp_path) == {"src/ghost.py:1": "missing"}


def test_citation_range_past_end_of_file_is_missing(tmp_path):
    # no trailing newline: five lines however the newline split is counted
    (tmp_path / "five.py").write_text("l1\nl2\nl3\nl4\nl5")
    status = citation_status(
        "a five.py:5\nb five.py:6\nc five.py:4-6\nd five.py:1-2,4-5\ne five.py:1-2,5-9\n",
        tmp_path,
    )
    assert status == {
        "five.py:5": "ok",
        "five.py:6": "missing",
        "five.py:4-6": "missing",
        "five.py:1-2,4-5": "ok",
        "five.py:1-2,5-9": "missing",
    }


def test_citation_without_same_line_symbol_checks_existence_only(tmp_path):
    make_repo(tmp_path)
    # the symbol on the next line is not associated with the citation
    text = "see src/app.py:1-2 for setup\n`nonexistent_thing` lives elsewhere\n"
    assert citation_status(text, tmp_path) == {"src/app.py:1-2": "ok"}


def test_citation_with_same_line_symbol_in_range_is_ok(tmp_path):
    make_repo(tmp_path)
    text = (
        "src/app.py:4-5 defines `beta`\n"
        "src/app.py:4 defines `module.beta`\n"
        "src/app.py:1 has `nonexistent_x` and `alpha`\n"
    )
    assert citation_status(text, tmp_path) == {
        "src/app.py:4-5": "ok",
        "src/app.py:4": "ok",
        "src/app.py:1": "ok",
    }


def test_citation_with_same_line_symbol_outside_range_is_missing(tmp_path):
    make_repo(tmp_path)
    text = "src/app.py:1-2 defines `beta`\nsrc/app.py:5 holds `alpha`\n"
    assert citation_status(text, tmp_path) == {
        "src/app.py:1-2": "missing",
        "src/app.py:5": "missing",
    }


def test_citation_absolute_and_home_paths_ignore_root(tmp_path, monkeypatch):
    make_repo(tmp_path)
    other_root = tmp_path / "elsewhere"
    other_root.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    text = f"abs {tmp_path}/src/app.py:4 `beta`\nhome ~/src/app.py:1 `alpha`\nrel src/app.py:1\n"
    assert citation_status(text, other_root) == {
        f"{tmp_path}/src/app.py:4": "ok",
        "~/src/app.py:1": "ok",
        "src/app.py:1": "missing",
    }


# --- resolve_symbols --------------------------------------------------------


def test_symbol_whose_segments_all_exist_in_repo_is_ok(tmp_path):
    make_repo(tmp_path)
    status = symbol_status(["parse_frame", "codec.parse_frame", "codec::parse_frame"], tmp_path)
    assert status == {
        "parse_frame": "ok",
        "codec.parse_frame": "ok",
        "codec::parse_frame": "ok",
    }


def test_symbol_with_any_missing_segment_is_unresolved(tmp_path):
    make_repo(tmp_path)
    status = symbol_status(["codec::missing_fn", "ghost_mod.parse_frame", "missing_fn"], tmp_path)
    assert status == {
        "codec::missing_fn": "unresolved",
        "ghost_mod.parse_frame": "unresolved",
        "missing_fn": "unresolved",
    }


def test_symbol_found_only_inside_a_longer_word_is_unresolved(tmp_path):
    make_repo(tmp_path)
    # "parse" appears only as part of parse_frame, so a whole-word search misses it
    assert symbol_status(["parse"], tmp_path) == {"parse": "unresolved"}


def test_symbol_short_segments_are_never_checked(tmp_path):
    make_repo(tmp_path)
    assert symbol_status(["io::parse_frame", "codec.re"], tmp_path) == {
        "io::parse_frame": "ok",
        "codec.re": "ok",
    }


def test_declared_new_symbol_is_reported_declared_new(tmp_path):
    make_repo(tmp_path)
    status = symbol_status(
        ["brand_new_fn", "other_new_fn", "parse_frame"], tmp_path, declared={"brand_new_fn"}
    )
    assert status == {
        "brand_new_fn": "declared-new",
        "other_new_fn": "unresolved",
        "parse_frame": "ok",
    }


def test_a_symbol_present_only_under_working_docs_is_unresolved(tmp_path):
    make_repo(tmp_path)
    notes = tmp_path / "docs/dev/project-management/notes"
    notes.mkdir(parents=True)
    (notes / "x.md").write_text("we plan only_in_working_docs here\n")
    status = symbol_status(["only_in_working_docs", "parse_frame"], tmp_path)
    assert status == {"only_in_working_docs": "unresolved", "parse_frame": "ok"}


def test_grounded_symbol_claims_from_extract_resolve_end_to_end(tmp_path):
    make_repo(tmp_path)
    claims = ground_prd.extract_claims("use `codec::parse_frame` and `vanished_helper`\n")
    symbols = [c for c in claims if c.kind == "symbol"]
    result = ground_prd.resolve_symbols(symbols, tmp_path, set())
    assert {c.token: result[c] for c in symbols} == {
        "codec::parse_frame": "ok",
        "vanished_helper": "unresolved",
    }

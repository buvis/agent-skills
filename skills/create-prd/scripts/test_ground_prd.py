"""Tests for ground_prd.py: claim extraction, citation lens, symbol lens (PRD 00075)."""
import json
import shutil
from pathlib import Path

import pytest

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


def test_citation_accepts_any_file_extension_not_just_py_and_md():
    claims = kinds("see main.rs:3 and Cargo.toml:5\nrun run.sh:2 with conf/data.json:1-4,6-7\n")
    assert [c for c in claims if c[0] == "citation"] == [
        ("citation", "main.rs:3", 1),
        ("citation", "Cargo.toml:5", 1),
        ("citation", "run.sh:2", 2),
        ("citation", "conf/data.json:1-4,6-7", 2),
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
        "`module.py` `main.rs` `pyproject.toml` `config.json` `events.jsonl` `ci.yml`\n"
        "`run.sh` `app.js` `index.ts` `style.css`\n"
        "`src/app` `two words` `-flag` `--verbose`\n"
        "`NNNNN` `prd_NNNNN` `XXXX` `YYYY_mm` `foo*` `<name>` `${HOME}` `a...b`\n"
        "keep `real_symbol`\n"
    )
    assert kinds(text) == [("symbol", "real_symbol", 6)]


def test_symbol_keeps_uppercase_constants_and_mixed_case_names():
    # the placeholder filter is about *?<>{}$, ..., NNNNN - never about capitalization
    text = "set `MAX_RETRIES` on `HTTPServer` via `parse_JSON`\n"
    assert kinds(text) == [
        ("symbol", "MAX_RETRIES", 1),
        ("symbol", "HTTPServer", 1),
        ("symbol", "parse_JSON", 1),
    ]


def test_frontmatter_symbol_is_not_scanned_and_lines_count_from_original_text():
    text = (
        "---\n"
        "title: `front_sym` see meta.md:1\n"
        "author: `front_author`\n"
        "tags: `front_tag` tags.py:2\n"
        "status: `front_status`\n"
        "note: `front_note` note.rs:3\n"
        "---\n"
        "body `body_sym`\n"
    )
    assert kinds(text) == [("symbol", "body_sym", 8)]


def test_fenced_block_yields_no_claims_and_keeps_line_numbers():
    text = (
        "intro\n"
        "```python\n"
        "`fenced_sym` inside.py:1\n"
        "`fenced_two` inside.rs:2\n"
        "`fenced_three` inside.sh:3\n"
        "`fenced_four` inside.md:4\n"
        "```\n"
        "after `after_sym` outside.py:2\n"
    )
    assert sorted(kinds(text)) == [
        ("citation", "outside.py:2", 8),
        ("symbol", "after_sym", 8),
    ]


def test_link_ok_waiver_line_yields_no_citation_or_symbol():
    text = "link-ok: gone.py:4 `gone_sym` was removed\nkept.py:1 `kept_sym`\n"
    assert sorted(kinds(text)) == [("citation", "kept.py:1", 2), ("symbol", "kept_sym", 2)]


def test_extract_claims_never_emits_library_kind_before_reclassification():
    # library classification needs known packages (a later task); extraction alone
    # reports every surviving backtick token as a symbol, package-like or not
    text = (
        "use `serde::Deserialize` and `git2::Repository` see src/lib.rs:2\n"
        "call `requests.get` or `numpy` then `std::fs::read`\n"
    )
    claims = ground_prd.extract_claims(text)
    assert {c.kind for c in claims} == {"citation", "symbol"}
    assert [(c.kind, c.token, c.line) for c in claims if c.kind != "citation"] == [
        ("symbol", "serde::Deserialize", 1),
        ("symbol", "git2::Repository", 1),
        ("symbol", "requests.get", 2),
        ("symbol", "numpy", 2),
        ("symbol", "std::fs::read", 2),
    ]


# --- check_citations --------------------------------------------------------


def test_citation_to_missing_file_is_missing(tmp_path):
    make_repo(tmp_path)
    assert citation_status("see src/ghost.py:1\n", tmp_path) == {"src/ghost.py:1": "missing"}


def test_citation_range_past_end_of_file_is_missing(tmp_path):
    # no trailing newline: five lines however the newline split is counted
    (tmp_path / "five.py").write_text("l1\nl2\nl3\nl4\nl5")
    # src/app.py: five lines WITH a trailing newline - no phantom sixth line
    make_repo(tmp_path)
    status = citation_status(
        "a five.py:5\nb five.py:6\nc five.py:4-6\nd five.py:1-2,4-5\ne five.py:1-2,5-9\n"
        "f five.py:6-7,1-2\ng five.py:1-2,7-8,3-4\n"
        "h src/app.py:5\ni src/app.py:6\nj src/app.py:5-6\n",
        tmp_path,
    )
    assert status == {
        "five.py:5": "ok",
        "five.py:6": "missing",
        "five.py:4-6": "missing",
        "five.py:1-2,4-5": "ok",
        "five.py:1-2,5-9": "missing",
        "five.py:6-7,1-2": "missing",
        "five.py:1-2,7-8,3-4": "missing",
        "src/app.py:5": "ok",
        "src/app.py:6": "missing",
        "src/app.py:5-6": "missing",
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
        # in-range symbol first, absent symbol last
        "src/app.py:1-3 has `alpha` and `nonexistent_x`\n"
        # in-range symbol first, a later one that exists but outside the range:
        # any-of passes, all-of would fail
        "src/app.py:3-4 has `beta` and `alpha`\n"
    )
    assert citation_status(text, tmp_path) == {
        "src/app.py:4-5": "ok",
        "src/app.py:4": "ok",
        "src/app.py:1": "ok",
        "src/app.py:1-3": "ok",
        "src/app.py:3-4": "ok",
    }


def test_citation_with_same_line_symbol_outside_range_is_missing(tmp_path):
    make_repo(tmp_path)
    text = (
        "src/app.py:1-2 defines `beta`\n"
        "src/app.py:5 holds `alpha`\n"
        # several symbols, none inside lines 2-3
        "src/app.py:2-3 has `alpha` and `beta`\n"
    )
    assert citation_status(text, tmp_path) == {
        "src/app.py:1-2": "missing",
        "src/app.py:5": "missing",
        "src/app.py:2-3": "missing",
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


def test_symbol_segments_of_three_or_four_chars_are_checked(tmp_path):
    make_repo(tmp_path)
    # "io" (2) is skipped, but absent "abs" (3) and "zork" (4) are checked; "def" (3) exists
    assert symbol_status(["io::abs", "zork", "codec.zork", "codec.def"], tmp_path) == {
        "io::abs": "unresolved",
        "zork": "unresolved",
        "codec.zork": "unresolved",
        "codec.def": "ok",
    }


def test_symbol_defined_only_in_non_python_files_is_ok(tmp_path):
    make_repo(tmp_path)
    (tmp_path / "src/lib.rs").write_text("pub fn rust_only_fn() {}\n")
    (tmp_path / "README.md").write_text("Run readme_only_name to start.\n")
    (tmp_path / "Makefile").write_text("make_only_target:\n\techo hi\n")
    status = symbol_status(["rust_only_fn", "readme_only_name", "make_only_target"], tmp_path)
    assert status == {
        "rust_only_fn": "ok",
        "readme_only_name": "ok",
        "make_only_target": "ok",
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


# --- library lens: known_packages, check_library_claims ---------------------


def write_lock(root: Path, *crates):
    blocks = [
        f'[[package]]\nname = "{name}"\nversion = "{version}"\n'
        'source = "registry+https://github.com/rust-lang/crates.io-index"\n'
        for name, version in crates
    ]
    root.mkdir(parents=True, exist_ok=True)
    (root / "Cargo.lock").write_text("# @generated by Cargo\nversion = 3\n\n" + "\n".join(blocks))


def plant_crate(registry: Path, name, version, lib_rs, index="idx"):
    src = registry / index / f"{name}-{version}" / "src"
    src.mkdir(parents=True)
    (src / "lib.rs").write_text(lib_rs)
    return src.parent


def plant_node_and_venv(root: Path, python="python3.12"):
    leftpad = root / "node_modules" / "leftpad"
    (leftpad / "lib").mkdir(parents=True)
    (leftpad / "index.js").write_text("function padLeft(s, n) { return s; }\n")
    # an API living only in a second file of the same package
    (leftpad / "lib" / "util.js").write_text("function trimEnds(s) { return s; }\n")
    site = root / ".venv" / "lib" / python / "site-packages"
    (site / "requests").mkdir(parents=True)
    (site / "requests" / "__init__.py").write_text("def get(url):\n    pass\n")
    (site / "requests" / "api.py").write_text("def head_request(url):\n    pass\n")
    (site / "six.py").write_text("def moves_helper():\n    pass\n")
    return leftpad, site


def library_rows(tokens, root, registry, extra=()):
    claims = [Claim("library", t, i + 1) for i, t in enumerate(tokens)] + list(extra)
    result = ground_prd.check_library_claims(claims, root, registry)
    return {c.token: status for c, status in result.items()}


class TestLibraryLens:
    def test_library_claim_whose_api_exists_in_locked_crate_source_is_ok(self, tmp_path):
        registry = tmp_path / "registry"
        write_lock(tmp_path, ("fake", "1.0.0"))
        crate = plant_crate(
            registry, "fake", "1.0.0",
            "pub fn present_fn() {}\npub struct Client;\nimpl Client { pub fn send(&self) {} }\n",
        )
        # an API defined only in a second source file of the same crate
        (crate / "src" / "client.rs").write_text("pub fn connect_pool() {}\n")
        tokens = [
            "fake::present_fn", "fake::Client::send", "fake", "fake::connect_pool",
            # a struct name not followed by "(" in source
            "fake::Client",
            # "t_fn" appears only inside present_fn: not a whole word
            "fake::t_fn",
        ]
        library = [Claim("library", t, i + 1) for i, t in enumerate(tokens)]
        # a symbol-kind claim is not the library lens's business
        not_library = Claim("symbol", "fake::present_fn", 9)
        result = ground_prd.check_library_claims(library + [not_library], tmp_path, registry)
        assert set(result) == set(library)
        assert {c.token: s for c, s in result.items()} == {
            "fake::present_fn": "ok",
            "fake::Client::send": "ok",
            "fake": "ok",
            "fake::connect_pool": "ok",
            "fake::Client": "ok",
            "fake::t_fn": "unverified",
        }

    def test_library_claim_whose_api_is_absent_from_crate_source_is_unverified(self, tmp_path):
        registry = tmp_path / "registry"
        write_lock(tmp_path, ("fake", "1.0.0"))
        plant_crate(
            registry, "fake", "1.0.0",
            "pub fn present_fn() {}\npub struct Client;\nimpl Client { pub fn send(&self) {} }\n",
        )
        # "present" exists only inside present_fn: a whole-word search misses it
        # fake::Ghost::send: last segment exists, the middle one does not
        rows = library_rows(
            ["fake::absent_fn", "fake::present", "fake::Client::absent_method",
             "fake::Ghost::send"],
            tmp_path, registry,
        )
        assert rows == {
            "fake::absent_fn": "unverified",
            "fake::present": "unverified",
            "fake::Client::absent_method": "unverified",
            "fake::Ghost::send": "unverified",
        }

    def test_library_claim_for_package_found_nowhere_is_one_unverified_row(self, tmp_path):
        # no Cargo.lock, no node_modules, no .venv
        rows = library_rows(["ghost_pkg::thing"], tmp_path, tmp_path / "registry")
        assert rows == {"ghost_pkg::thing": "unverified"}

    def test_library_claim_checks_the_locked_crate_version_not_another(self, tmp_path):
        registry = tmp_path / "registry"
        # the lock pins the OLDER version while a newer one also sits on disk
        write_lock(tmp_path, ("fake", "0.9.0"))
        locked = plant_crate(registry, "fake", "0.9.0", "pub fn old_fn() {}\n")
        plant_crate(registry, "fake", "1.0.0", "pub fn new_fn() {}\n")
        assert ground_prd.known_packages(tmp_path, registry)["fake"] == {
            "version": "0.9.0",
            "source": locked,
        }
        rows = library_rows(["fake::new_fn", "fake::old_fn"], tmp_path, registry)
        assert rows == {"fake::new_fn": "unverified", "fake::old_fn": "ok"}

    def test_known_packages_maps_each_cargo_lock_library_crate_to_its_own_version(self, tmp_path):
        registry = tmp_path / "registry"
        write_lock(
            tmp_path, ("alpha_crate", "0.3.1"), ("beta_crate", "2.4.0"), ("gamma_crate", "1.2.3")
        )
        alpha = plant_crate(registry, "alpha_crate", "0.3.1", "pub fn a() {}\n")
        # any index subdirectory name, not just the fixture's "idx"
        gamma = plant_crate(
            registry, "gamma_crate", "1.2.3", "pub fn g() {}\n", index="index.example-abc"
        )
        packages = ground_prd.known_packages(tmp_path, registry)
        assert packages["alpha_crate"] == {"version": "0.3.1", "source": alpha}
        assert packages["gamma_crate"] == {"version": "1.2.3", "source": gamma}
        # locked but not unpacked in the registry: version kept, source None
        assert packages["beta_crate"] == {"version": "2.4.0", "source": None}
        assert "ghost_crate" not in packages

    def test_known_packages_maps_node_modules_dirs_and_venv_library_modules(self, tmp_path):
        # any python* directory, not just python3.12
        leftpad, site = plant_node_and_venv(tmp_path, python="python3.11")
        packages = ground_prd.known_packages(tmp_path, tmp_path / "registry")
        assert set(packages["leftpad"]) == {"source"}
        assert Path(packages["leftpad"]["source"]) == leftpad
        assert Path(packages["requests"]["source"]) == site / "requests"
        # a single-file module is keyed by its stem
        assert Path(packages["six"]["source"]) == site / "six.py"
        assert "six.py" not in packages
        assert "ghost_pkg" not in packages

    def test_library_claims_resolve_inside_node_modules_and_venv_sources(self, tmp_path):
        plant_node_and_venv(tmp_path)
        rows = library_rows(
            ["leftpad.padLeft", "leftpad.padRight", "leftpad.trimEnds", "requests.get",
             "requests.post_json", "requests.head_request",
             "six.moves_helper", "six.missing_helper"],
            tmp_path, tmp_path / "registry",
        )
        assert rows == {
            "leftpad.padLeft": "ok",
            "leftpad.padRight": "unverified",
            # defined only in lib/util.js and requests/api.py: whole package is searched
            "leftpad.trimEnds": "ok",
            "requests.get": "ok",
            "requests.post_json": "unverified",
            "requests.head_request": "ok",
            "six.moves_helper": "ok",
            "six.missing_helper": "unverified",
        }

    def test_known_packages_is_memoized_per_root_and_registry_library_pair(self, tmp_path):
        registry = tmp_path / "registry"
        (tmp_path / "node_modules" / "first_pkg").mkdir(parents=True)
        assert "first_pkg" in ground_prd.known_packages(tmp_path, registry)
        (tmp_path / "node_modules" / "late_pkg").mkdir()
        # same (root, registry): the cached map, no second filesystem walk
        assert "late_pkg" not in ground_prd.known_packages(tmp_path, registry)
        # a different registry is a different key: walked fresh
        assert "late_pkg" in ground_prd.known_packages(tmp_path, tmp_path / "other_registry")
        # a different root with the SAME registry is also a different key
        other_root = tmp_path / "other_repo"
        (other_root / "node_modules" / "other_root_pkg").mkdir(parents=True)
        other_packages = ground_prd.known_packages(other_root, registry)
        assert "other_root_pkg" in other_packages
        assert "first_pkg" not in other_packages

    def test_a_locked_crate_without_source_is_unverified_not_unresolved(self, tmp_path):
        root = tmp_path / "repo"
        registry = tmp_path / "registry"  # never created: no unpacked crate anywhere
        write_lock(root, ("fake", "1.0.0"))
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("def local_helper():\n    pass\n")
        packages = ground_prd.known_packages(root, registry)
        # reclassification as run() will do it: provisional symbol -> library
        claims = [
            c._replace(kind="library")
            if c.kind == "symbol" and ground_prd.SEGMENT_SPLIT.split(c.token)[0] in packages
            else c
            for c in ground_prd.extract_claims("call `fake::absent_fn` beside `local_helper`\n")
        ]
        library = ground_prd.check_library_claims(claims, root, registry)
        # only the library-kind claims come back; the symbol claim is left alone
        assert set(library) == {c for c in claims if c.kind == "library"}
        symbols = [c for c in claims if c.kind == "symbol"]
        symbol_rows = ground_prd.resolve_symbols(symbols, root, set())
        rows = [(c.kind, c.token, s) for c, s in {**library, **symbol_rows}.items()]
        assert [r for r in rows if r[0] == "library"] == [("library", "fake::absent_fn", "unverified")]
        assert [r for r in rows if r[2] == "unresolved"] == []

    def test_library_marker_waives_claim_regardless_of_resolution(self, tmp_path):
        registry = tmp_path / "registry"
        write_lock(tmp_path, ("fake", "1.0.0"))
        plant_crate(registry, "fake", "1.0.0", "pub fn present_fn() {}\n")
        marked = Claim("library", "ghost_pkg::thing", 3)  # resolves nowhere
        marked_ok = Claim("library", "fake::present_fn", 4)  # would resolve ok
        unmarked = Claim("library", "ghost_pkg::other", 7)  # line absent from line_text
        # line present in line_text, but its text lacks the marker
        unmarked_line = Claim("library", "ghost_pkg::near", 8)
        line_text = {
            3: "uses `ghost_pkg::thing` (unverified library claim)",
            4: "calls `fake::present_fn` (unverified library claim)",
            5: "an unrelated line",
            8: "uses `ghost_pkg::near`",
        }
        result = ground_prd.check_library_claims(
            [marked, marked_ok, unmarked, unmarked_line], tmp_path, registry, line_text
        )
        assert result[marked] == "waived"
        assert result[marked_ok] == "waived"
        assert result[unmarked] == "unverified"
        assert result[unmarked_line] == "unverified"

    def test_library_claim_without_line_text_is_never_waived_by_marker(self, tmp_path):
        claim = Claim("library", "ghost_pkg::thing", 3)
        registry = tmp_path / "registry"
        assert ground_prd.check_library_claims([claim], tmp_path, registry) == {
            claim: "unverified"
        }
        assert ground_prd.check_library_claims(
            [claim], tmp_path, registry, line_text=None
        ) == {claim: "unverified"}
        # a marker on a different line does not reach this claim
        assert ground_prd.check_library_claims(
            [claim], tmp_path, registry, {2: "(unverified library claim)"}
        ) == {claim: "unverified"}


# --- run() -------------------------------------------------------------------


def test_run_returns_rows_blocking_and_unverified_counts(tmp_path):
    make_repo(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("see src/ghost.py:1\ncalls `totally_missing_symbol`\nuses `alpha`\n")
    result = ground_prd.run([prd], tmp_path, tmp_path / "registry")
    assert result["blocking"] == 2
    assert result["unverified"] == 0
    assert {r["status"] for r in result["rows"]} == {"missing", "unresolved", "ok"}
    assert all(r["file"] == str(prd) for r in result["rows"])


def plant_pkg_without_symbol(tmp_path: Path, symbol: str) -> None:
    pkg = tmp_path / "node_modules" / "mypkg"
    pkg.mkdir(parents=True)
    (pkg / "index.js").write_text(f"function present() {{ return '{symbol}_not_here'; }}\n")


def test_run_reclassifies_known_package_symbol_claims_to_library_before_dispatch(tmp_path):
    plant_pkg_without_symbol(tmp_path, "missingFn")
    prd = tmp_path / "prd.md"
    prd.write_text("calls `mypkg.missingFn`\n")
    result = ground_prd.run([prd], tmp_path, tmp_path / "registry")
    assert [(r["kind"], r["status"]) for r in result["rows"]] == [("library", "unverified")]
    assert result["unverified"] == 1
    assert result["blocking"] == 0


def test_run_declared_new_set_is_built_once_across_every_file_in_the_run(tmp_path):
    make_repo(tmp_path)
    declare = tmp_path / "declare.md"
    declare.write_text("New symbols: `brand_new_fn`, `other_new_fn`\n")
    use = tmp_path / "use.md"
    use.write_text("calls `brand_new_fn`\n")
    result = ground_prd.run([declare, use], tmp_path, tmp_path / "registry")
    row = next(r for r in result["rows"] if r["token"] == "brand_new_fn" and r["file"] == str(use))
    assert row["status"] == "declared-new"


def test_run_library_waiver_resolves_end_to_end_via_run(tmp_path):
    plant_pkg_without_symbol(tmp_path, "missingFn")
    prd = tmp_path / "prd.md"
    prd.write_text("calls `mypkg.missingFn` (unverified library claim)\n")
    result = ground_prd.run([prd], tmp_path, tmp_path / "registry")
    assert [r["status"] for r in result["rows"]] == ["waived"]


# --- main() / CLI surface ----------------------------------------------------


def run_cli(argv, tmp_path, root=None):
    args = list(argv)
    if "--root" not in args:
        args += ["--root", str(root if root is not None else tmp_path)]
    with pytest.raises(SystemExit) as excinfo:
        ground_prd.main(args)
    return excinfo.value.code


def test_cli_exits_two_when_rg_not_on_path(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    prd = tmp_path / "x.md"
    prd.write_text("hello\n")
    code = run_cli([str(prd)], tmp_path)
    assert code == 2
    assert "rg" in capsys.readouterr().err


def test_cli_exits_two_for_missing_path_argument(tmp_path, capsys):
    missing = tmp_path / "ghost.md"
    code = run_cli([str(missing)], tmp_path)
    assert code == 2
    assert str(missing) in capsys.readouterr().err


def test_cli_exits_two_naming_missing_path_even_when_other_args_are_valid(tmp_path, capsys):
    valid = tmp_path / "ok.md"
    valid.write_text("hi\n")
    missing = tmp_path / "ghost.md"
    code = run_cli([str(valid), str(missing)], tmp_path)
    assert code == 2
    assert str(missing) in capsys.readouterr().err


def test_cli_exits_two_naming_a_root_that_is_not_a_directory(tmp_path, capsys):
    make_repo(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("uses `alpha`\n")
    absent_root = tmp_path / "absent"
    with pytest.raises(SystemExit) as excinfo:
        ground_prd.main([str(prd), "--root", str(absent_root)])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "--root" in err and "not a directory" in err
    assert "Traceback" not in err


def test_cli_exits_two_when_cargo_lock_is_unreadable(tmp_path, capsys, deny_access):
    make_repo(tmp_path)
    lock = tmp_path / "Cargo.lock"
    lock.write_text('[[package]]\nname = "fake"\nversion = "1.0.0"\nsource = "registry+x"\n')
    deny_access(lock)
    prd = tmp_path / "prd.md"
    prd.write_text("uses `alpha`\n")
    with pytest.raises(SystemExit) as excinfo:
        ground_prd.main([str(prd), "--root", str(tmp_path)])
    assert excinfo.value.code == 2
    assert "ground_prd:" in capsys.readouterr().err


def test_cli_directory_argument_expands_non_recursively_to_sorted_md_files(tmp_path, capsys):
    prds = tmp_path / "prds"
    prds.mkdir()
    (prds / "b.md").write_text("see `beta_two`\n")
    (prds / "a.md").write_text("see `alpha_one`\n")
    (prds / "skip.txt").write_text("see `txt_three`\n")
    sub = prds / "sub"
    sub.mkdir()
    (sub / "c.md").write_text("see `gamma_three`\n")
    code = run_cli(["--json", str(prds)], tmp_path)
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    files = {r["file"] for r in data["rows"]}
    assert files == {str(prds / "a.md"), str(prds / "b.md")}


def test_cli_directory_with_zero_markdown_files_is_not_reported_as_missing(tmp_path, capsys):
    empty_dir = tmp_path / "emptydir"
    empty_dir.mkdir()
    code = run_cli([str(empty_dir)], tmp_path)
    assert code == 0
    assert capsys.readouterr().err == ""


def test_cli_table_output_prints_sorted_rows_with_summary_line(tmp_path, capsys):
    make_repo(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text(
        "see src/ghost.py:1\ncalls `totally_missing_symbol`\nuses `alpha`\n"
    )
    code = run_cli([str(prd)], tmp_path)
    assert code == 1
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 4
    assert lines[0].startswith("missing") and "src/ghost.py:1" in lines[0] and str(prd) in lines[0]
    assert lines[1].startswith("unresolved") and "totally_missing_symbol" in lines[1]
    assert lines[2].startswith("ok") and "alpha" in lines[2]
    assert lines[3] == "2 blocking, 0 unverified, 0 declared new"


def test_cli_json_output_prints_only_json_with_rows_blocking_unverified(tmp_path, capsys):
    make_repo(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text(
        "see src/ghost.py:1\ncalls `totally_missing_symbol`\nuses `alpha`\n"
    )
    code = run_cli(["--json", str(prd)], tmp_path)
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert set(data.keys()) == {"rows", "blocking", "unverified"}
    assert data["blocking"] == 2
    assert data["unverified"] == 0
    assert all("file" in r for r in data["rows"])


def test_cli_exits_zero_when_only_unverified_rows_are_present(tmp_path, capsys):
    plant_pkg_without_symbol(tmp_path, "missingFn")
    prd = tmp_path / "prd.md"
    prd.write_text("calls `mypkg.missingFn`\n")
    code = run_cli(["--json", str(prd)], tmp_path)
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["unverified"] == 1
    assert data["blocking"] == 0


# --- new behaviors: rg exit-2 handling, caching, fence-aware declarations,  --
# --- exclude-by-own-path, differentiated missing-citation detail, Cargo.lock
# --- source-less (path/workspace) crates excluded from known_packages       -


def test_cli_exits_two_when_rg_itself_exits_two(monkeypatch, tmp_path, capsys):
    # rg is on PATH (shutil.which succeeds); it is the invocation inside
    # resolve_symbols that fails with exit code 2 (a real rg internal error,
    # e.g. a bad pattern or regex engine failure), which must not surface as
    # an uncaught RuntimeError / traceback but as a clean sys.exit(2).
    make_repo(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("calls `totally_missing_symbol`\n")

    class FakeResult:
        returncode = 2
        stderr = "rg: regex parse error"

    monkeypatch.setattr(ground_prd.subprocess, "run", lambda *a, **k: FakeResult())
    with pytest.raises(SystemExit) as excinfo:
        ground_prd.main([str(prd), "--root", str(tmp_path)])
    assert excinfo.value.code == 2
    assert capsys.readouterr().err != ""


def test_resolve_symbols_caches_rg_calls_per_segment_and_root(tmp_path, monkeypatch):
    make_repo(tmp_path)
    real_run = ground_prd.subprocess.run
    shared_sym_calls = []

    def counting_run(cmd, *a, **k):
        if len(cmd) >= 2 and cmd[-2] == "shared_sym":
            shared_sym_calls.append(cmd)
        return real_run(cmd, *a, **k)

    monkeypatch.setattr(ground_prd.subprocess, "run", counting_run)
    claims = [
        Claim("symbol", "shared_sym", 1),
        # "codec" resolves ok (present via make_repo), so the loop proceeds to
        # also check "shared_sym" for this claim too, same segment as above
        Claim("symbol", "codec.shared_sym", 2),
    ]
    ground_prd.resolve_symbols(claims, tmp_path, set())
    assert len(shared_sym_calls) <= 1


def test_new_symbols_line_inside_fence_does_not_declare_the_symbol(tmp_path):
    make_repo(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text(
        "```python\n"
        "New symbols: `reallyFakeSymbolXyz`\n"
        "```\n"
        "see `reallyFakeSymbolXyz` here\n"
    )
    result = ground_prd.run([prd], tmp_path, tmp_path / "registry")
    row = next(r for r in result["rows"] if r["token"] == "reallyFakeSymbolXyz")
    assert row["status"] == "unresolved"


def test_resolve_symbols_excludes_own_prd_path_given_as_relative_path(tmp_path, monkeypatch):
    # the PRD path given to resolve_symbols as a path relative to the actual
    # process cwd (as it naturally is when it comes from a CLI argument),
    # while cwd differs from --root: the exclusion must still apply so the
    # claim cannot self-confirm by quoting its own, otherwise-absent token.
    make_repo(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("calls onlyInPrdSymbol here\n")
    monkeypatch.chdir(tmp_path.parent)
    claims = [Claim("symbol", "onlyInPrdSymbol", 1)]
    result = ground_prd.resolve_symbols(
        claims, tmp_path, set(), exclude=frozenset({Path(tmp_path.name) / "prd.md"})
    )
    assert result[claims[0]] == "unresolved"


def test_cli_excludes_own_prd_given_relative_to_cwd_not_root(tmp_path, monkeypatch, capsys):
    # cwd (work) and --root (work/repo) differ: the PRD path on the CLI is
    # relative to cwd, not to root, so the exclusion must resolve it against
    # cwd or the PRD's own unresolved-elsewhere claim confirms itself.
    work = tmp_path / "work"
    repo = work / "repo"
    make_repo(repo)
    prd = repo / "prd.md"
    prd.write_text("calls `onlyInPrdSymbol` here\n")
    monkeypatch.chdir(work)
    with pytest.raises(SystemExit) as excinfo:
        ground_prd.main(["repo/prd.md", "--root", "repo"])
    assert excinfo.value.code == 1
    out = capsys.readouterr().out
    assert any("unresolved" in line and "onlyInPrdSymbol" in line for line in out.splitlines())


def test_missing_citation_detail_differentiates_absent_file_overflow_and_no_symbol_match(
    tmp_path,
):
    (tmp_path / "exists_short.py").write_text("line one\nline two\n")
    prd = tmp_path / "prd.md"
    prd.write_text(
        "a ghost.py:1\n"
        "b exists_short.py:5\n"
        "c exists_short.py:1 has `nonexistent_sym`\n"
    )
    result = ground_prd.run([prd], tmp_path, tmp_path / "registry")
    rows = {r["token"]: r for r in result["rows"] if r["kind"] == "citation"}
    absent_file_detail = rows["ghost.py:1"]["detail"]
    overflow_range_detail = rows["exists_short.py:5"]["detail"]
    no_symbol_match_detail = rows["exists_short.py:1"]["detail"]

    assert absent_file_detail != f"citation ghost.py:1"
    assert overflow_range_detail != f"citation exists_short.py:5"
    assert no_symbol_match_detail != f"citation exists_short.py:1"
    assert len({absent_file_detail, overflow_range_detail, no_symbol_match_detail}) == 3

    assert "not found" in absent_file_detail
    assert "exceeds" in overflow_range_detail
    assert "nonexistent_sym" in no_symbol_match_detail


def test_known_packages_excludes_cargo_lock_package_block_without_source_line(tmp_path):
    registry = tmp_path / "registry"
    (tmp_path / "Cargo.lock").write_text(
        "# @generated by Cargo\nversion = 3\n\n"
        '[[package]]\nname = "workspace_crate"\nversion = "0.1.0"\n'
    )
    packages = ground_prd.known_packages(tmp_path, registry)
    assert "workspace_crate" not in packages
    assert "workspace_crate" not in packages.values()


def test_path_local_crate_symbol_is_not_reclassified_as_library_claim(tmp_path):
    make_repo(tmp_path)
    registry = tmp_path / "registry"
    (tmp_path / "Cargo.lock").write_text(
        "# @generated by Cargo\nversion = 3\n\n"
        '[[package]]\nname = "workspace_crate"\nversion = "0.1.0"\n'
    )
    prd = tmp_path / "prd.md"
    prd.write_text("uses `workspace_crate::thing`\n")
    result = ground_prd.run([prd], tmp_path, registry)
    row = result["rows"][0]
    assert row["kind"] == "symbol"
    assert row["status"] == "unresolved"


# --- PRD 00075 Test Strategy named end-to-end scenarios ----------------------
# Each test below exercises main() for an exit-code case the PRD names
# explicitly, even where a unit-level equivalent already exists elsewhere.


def test_a_grounded_prd_exits_zero_with_only_ok_rows(tmp_path, capsys):
    make_repo(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("uses `alpha` and `beta`\n")
    code = run_cli(["--json", str(prd)], tmp_path)
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert all(r["status"] == "ok" for r in data["rows"])


def test_a_library_api_in_installed_crate_source_is_ok(tmp_path):
    registry = tmp_path / "registry"
    plant_crate(registry, "fake", "1.0.0", "pub fn present_fn() {}\n")
    (tmp_path / "Cargo.lock").write_text(
        '# @generated by Cargo\nversion = 3\n\n[[package]]\nname = "fake"\n'
        'version = "1.0.0"\nsource = "registry+https://github.com/rust-lang/crates.io-index"\n'
    )
    prd = tmp_path / "prd.md"
    prd.write_text("calls `fake::present_fn`\n")
    with pytest.raises(SystemExit) as excinfo:
        ground_prd.main(["--json", str(prd), "--root", str(tmp_path), "--cargo-registry", str(registry)])
    assert excinfo.value.code == 0


def test_the_unverified_marker_and_link_ok_waive_their_lines(tmp_path, capsys):
    plant_pkg_without_symbol(tmp_path, "missingFn")
    prd = tmp_path / "prd.md"
    prd.write_text(
        "calls `mypkg.missingFn` (unverified library claim)\n"
        "link-ok: calls `totally_ungrounded_symbol_zzz`\n"
    )
    code = run_cli([str(prd)], tmp_path)
    assert code == 0


def test_a_citation_to_a_missing_file_blocks(tmp_path, capsys):
    prd = tmp_path / "prd.md"
    prd.write_text("see src/ghost.py:1\n")
    code = run_cli([str(prd)], tmp_path)
    assert code == 1


def test_a_citation_past_end_of_file_blocks(tmp_path, capsys):
    make_repo(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("see src/app.py:999\n")
    code = run_cli([str(prd)], tmp_path)
    assert code == 1


def test_a_cited_line_without_the_named_symbol_blocks(tmp_path, capsys):
    make_repo(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("see src/app.py:1 for `nonexistent_symbol_xyz`\n")
    code = run_cli([str(prd)], tmp_path)
    assert code == 1


def test_a_symbol_absent_from_the_repo_blocks_unless_declared_new(tmp_path, capsys):
    make_repo(tmp_path)
    blocked = tmp_path / "blocked.md"
    blocked.write_text("calls `totally_absent_symbol_abc`\n")
    assert run_cli([str(blocked)], tmp_path) == 1

    declared = tmp_path / "declared.md"
    declared.write_text(
        "New symbols: `totally_absent_symbol_abc`\ncalls `totally_absent_symbol_abc`\n"
    )
    assert run_cli([str(declared)], tmp_path) == 0


def test_a_library_api_absent_from_installed_source_warns_without_blocking(tmp_path, capsys):
    plant_pkg_without_symbol(tmp_path, "missingFn")
    prd = tmp_path / "prd.md"
    prd.write_text("calls `mypkg.missingFn`\n")
    code = run_cli(["--json", str(prd)], tmp_path)
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["unverified"] == 1


def test_a_missing_rg_exits_two(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    prd = tmp_path / "x.md"
    prd.write_text("hello\n")
    code = run_cli([str(prd)], tmp_path)
    assert code == 2


def test_cli_prints_table_json_and_exit_codes(tmp_path, capsys):
    make_repo(tmp_path)
    prd = tmp_path / "prd.md"
    prd.write_text("see src/ghost.py:1\ncalls `totally_missing_symbol`\nuses `alpha`\n")

    table_code = run_cli([str(prd)], tmp_path)
    table_out = capsys.readouterr().out
    assert table_code == 1
    assert "missing" in table_out and "unresolved" in table_out and "ok" in table_out

    json_code = run_cli(["--json", str(prd)], tmp_path)
    data = json.loads(capsys.readouterr().out)
    assert json_code == 1
    assert data["blocking"] == 2

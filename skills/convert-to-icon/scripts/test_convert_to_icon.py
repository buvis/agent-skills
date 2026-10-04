"""End-to-end tests for convert_to_icon.py.

The script declares its own dependencies (PEP 723), so every test drives it
through `uv run` in a child process and reads the results with the standard
library only. Run: uv run pytest skills/convert-to-icon/scripts -q
"""

from __future__ import annotations

import json
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("convert_to_icon.py")
WHITE, BLUE, DARK = (255, 255, 255), (34, 68, 170), (40, 44, 52)

DISC = '<circle cx="50" cy="50" r="40" fill="#224466"/>'
CROSS = '<path d="M0 0L100 100M100 0L0 100" stroke="#224466" stroke-width="10"/>'
ROUNDED_PLATE = '<rect width="100" height="100" rx="22" fill="#2244aa"/><circle cx="50" cy="50" r="20" fill="#fff"/>'
GRADIENT_PLATE = (
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#103060"/><stop offset="1" stop-color="#e0a040"/></linearGradient></defs>'
    '<rect width="100" height="100" rx="14" fill="url(#g)"/><circle cx="50" cy="50" r="22" fill="#fff"/>'
)


def run_script(*args) -> subprocess.CompletedProcess:
    command = ["uv", "run", "--quiet", str(SCRIPT), *(str(arg) for arg in args)]
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)


def json_of(*args) -> dict:
    done = run_script(*args)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def write_svg(path: Path, body: str, view: str = "0 0 100 100") -> Path:
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}">{body}</svg>', encoding="utf-8")
    return path


def write_png(path: Path, size: int, colour_at) -> Path:
    rows = b"".join(b"\x00" + bytes(v for x in range(size) for v in colour_at(x, y)) for y in range(size))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")
    )
    return path


def png_header(path: Path) -> tuple[int, int, int]:
    """Width, height and PNG colour type (2 is RGB without an alpha channel)."""
    width, height, _depth, colour_type = struct.unpack(">IIBB", path.read_bytes()[16:26])
    return width, height, colour_type


def plate_on_page(x: int, y: int) -> tuple[int, int, int]:
    """A blue plate carrying a white glyph, on a white page."""
    if 100 <= x < 156 and 100 <= y < 156:
        return WHITE
    return BLUE if 28 <= x < 228 and 28 <= y < 228 else WHITE


def ring_on_page(x: int, y: int) -> tuple[int, int, int]:
    """Line art: a dark ring whose middle shows the white page."""
    return DARK if 70**2 <= (x - 128) ** 2 + (y - 128) ** 2 < 90**2 else WHITE


@pytest.fixture(scope="module")
def disc_bundle(tmp_path_factory) -> tuple[Path, str]:
    folder = tmp_path_factory.mktemp("disc")
    done = run_script("build", write_svg(folder / "disc.svg", DISC))
    assert done.returncode == 0, done.stdout + done.stderr
    return folder / "disc.icons", done.stdout


def test_build_delivers_every_platform_file(disc_bundle):
    bundle, report = disc_bundle
    assert "icon set complete: 45 files" in report
    for rel in (
        "disc.icon.svg",
        "preview.png",
        "web/favicon.ico",
        "web/icon.svg",
        "web/apple-touch-icon.png",
        "web/icon-mask.png",
        "web/manifest.webmanifest",
        "windows/app.ico",
        "macos/AppIcon.icns",
        "macos/AppIcon.iconset/icon_512x512@2x.png",
        "ios/AppIcon.appiconset/Contents.json",
        "android/res/mipmap-anydpi-v26/ic_launcher.xml",
        "android/res/values/ic_launcher_background.xml",
        "android/res/mipmap-mdpi/ic_launcher_round.png",
        "android/res/mipmap-xxxhdpi/ic_launcher_monochrome.png",
        "android/play-store-512.png",
    ):
        assert (bundle / rel).stat().st_size > 0, rel


def test_png_sizes_follow_the_platform_tables(disc_bundle):
    bundle, _ = disc_bundle
    expected = {
        "web/apple-touch-icon.png": 180,
        "ios/AppIcon.appiconset/icon-1024.png": 1024,
        "macos/AppIcon.iconset/icon_16x16@2x.png": 32,
        "android/res/mipmap-hdpi/ic_launcher.png": 72,
        "android/res/mipmap-xxxhdpi/ic_launcher_foreground.png": 432,
    }
    for rel, px in expected.items():
        assert png_header(bundle / rel)[:2] == (px, px), rel


def test_ios_icon_carries_no_alpha_channel(disc_bundle):
    bundle, _ = disc_bundle
    assert png_header(bundle / "ios/AppIcon.appiconset/icon-1024.png")[2] == 2


def test_second_build_writes_only_what_is_missing(tmp_path):
    svg = write_svg(tmp_path / "disc.svg", DISC)
    assert run_script("build", svg).returncode == 0
    bundle = tmp_path / "disc.icons"
    (bundle / "web/favicon.ico").unlink()
    untouched = (bundle / "windows/app.ico").stat().st_mtime_ns

    again = run_script("build", bundle / "disc.icon.svg")

    assert "created 1, kept 44" in again.stdout
    assert (bundle / "web/favicon.ico").is_file()
    assert (bundle / "windows/app.ico").stat().st_mtime_ns == untouched


def test_extra_png_sizes_are_added_on_request(tmp_path):
    done = run_script("build", write_svg(tmp_path / "disc.svg", DISC), "--png", 300)
    assert done.returncode == 0, done.stderr
    assert png_header(tmp_path / "disc.icons/png/icon-300.png")[:2] == (300, 300)


def test_non_square_master_is_padded_not_stretched(tmp_path):
    wide = write_svg(tmp_path / "wide.svg", '<circle cx="100" cy="50" r="45" fill="#224466"/>', "0 0 200 100")
    assert run_script("build", wide).returncode == 0
    # The disc spans 90 of 200 units. Stretched to the square it would span 0.9 of the height.
    assert json_of("inspect", tmp_path / "wide.icons/web/icon-512.png")["extent"] == pytest.approx(0.45, abs=0.02)


def test_masked_icons_keep_art_inside_the_circle_a_launcher_cuts(tmp_path):
    assert run_script("build", write_svg(tmp_path / "cross.svg", CROSS)).returncode == 0
    bundle = tmp_path / "cross.icons"
    assert json_of("inspect", bundle / "web/icon-mask.png")["glyph_radius"] <= 0.8 + 0.02
    layer = json_of("inspect", bundle / "android/res/mipmap-xxxhdpi/ic_launcher_foreground.png")
    assert layer["radius"] <= 66 / 108 + 0.02


def test_rounded_plate_reaches_the_corners_on_masked_platforms(tmp_path):
    assert run_script("build", write_svg(tmp_path / "plate.svg", ROUNDED_PLATE)).returncode == 0
    ios = json_of("inspect", tmp_path / "plate.icons/ios/AppIcon.appiconset/icon-1024.png")
    # One flat colour all round the edge: the platform's own mask is the only rounding.
    assert ios["background"] == "#2244aa"
    assert ios["plate_rounded"] is False


def test_gradient_plate_reaches_the_corners_on_masked_platforms(tmp_path):
    assert run_script("build", write_svg(tmp_path / "sky.svg", GRADIENT_PLATE)).returncode == 0
    ios = json_of("inspect", tmp_path / "sky.icons/ios/AppIcon.appiconset/icon-1024.png")
    # Opaque to the corners with the gradient still running along the edge: no flat field
    # around a shrunken rounded picture.
    assert ios["picture"] is True
    assert ios["plate_rounded"] is False
    assert ios["background"] is None


def test_picture_is_continued_with_its_own_edge_colour(tmp_path):
    # A picture (the white subject covers most of it) whose edge is navy all the way round.
    scene = '<rect width="100" height="100" rx="14" fill="#103060"/><rect x="12" y="12" width="76" height="76" fill="#fff"/>'
    assert run_script("build", write_svg(tmp_path / "scene.svg", scene)).returncode == 0
    mask = json_of("inspect", tmp_path / "scene.icons/web/icon-mask.png")
    # The band around the shrunken picture must be that navy out to the canvas edge,
    # not a pale average of the navy and the white subject.
    assert mask["background"] == "#103060"


def test_gradient_plate_keeps_its_shape_on_a_field_when_a_colour_is_given(tmp_path):
    done = run_script("build", write_svg(tmp_path / "sky.svg", GRADIENT_PLATE), "--background", "#101010")
    assert done.returncode == 0, done.stderr
    ios = json_of("inspect", tmp_path / "sky.icons/ios/AppIcon.appiconset/icon-1024.png")
    assert ios["background"] == "#101010"


def test_solid_one_colour_glyph_is_not_mistaken_for_a_plate(tmp_path):
    # A filled disc must stay a disc on its field, not dissolve into a square of its own colour.
    assert run_script("build", write_svg(tmp_path / "disc.svg", DISC)).returncode == 0
    ios = json_of("inspect", tmp_path / "disc.icons/ios/AppIcon.appiconset/icon-1024.png")
    assert ios["background"] == "#ffffff"
    assert "#224466" in [colour for colour, _ in ios["colours"]]


@pytest.mark.parametrize(
    ("option", "value", "complaint"),
    [
        ("--background", "red", "expected a colour like #1a2b3c"),
        ("--png", "0", "expected a size from 1 to 4096 px"),
    ],
)
def test_bad_option_value_is_refused_before_anything_is_written(tmp_path, option, value, complaint):
    done = run_script("build", write_svg(tmp_path / "disc.svg", DISC), option, value)
    assert done.returncode != 0
    assert complaint in done.stderr
    assert not (tmp_path / "disc.icons").exists()


def test_trace_keeps_the_page_background_unless_told_to_remove_it(tmp_path):
    source = write_png(tmp_path / "ring.png", 256, ring_on_page)
    traced = json_of("trace", source)
    assert json_of("inspect", traced["svg"])["background"] == "#ffffff"


def test_trace_names_bundle_and_master_as_name_dot_type(tmp_path):
    source = write_png(tmp_path / "logo.icon.png", 256, ring_on_page)
    traced = json_of("trace", source, "--background", "remove")
    assert Path(traced["svg"]) == tmp_path / "logo.icons" / "logo.icon.svg"


def test_trace_keeps_the_original_raster_in_the_bundle(tmp_path):
    source = write_png(tmp_path / "logo.icon.png", 256, ring_on_page)
    traced = json_of("trace", source, "--background", "remove")
    kept = tmp_path / "logo.icons" / "logo.original.png"
    assert Path(traced["original"]) == kept
    assert kept.read_bytes() == source.read_bytes()
    assert source.is_file()


def test_review_compares_against_the_kept_original_without_being_told(tmp_path):
    source = write_png(tmp_path / "logo.icon.png", 256, ring_on_page)
    traced = json_of("trace", source, "--background", "remove")
    verdict = json_of("review", traced["svg"])
    assert "mean_error" in verdict["facts"]


def test_trace_removes_the_page_but_keeps_the_glyph_a_plate_encloses(tmp_path):
    source = write_png(tmp_path / "plate.png", 256, plate_on_page)
    traced = json_of("trace", source, "--background", "remove")
    facts = json_of("inspect", traced["svg"])
    # The page is gone, so the plate now runs to the canvas edge...
    assert facts["background"] == "#2244aa"
    # ...and the white glyph inside it is still drawn.
    assert "#ffffff" in [colour for colour, _ in facts["colours"]]


def test_trace_clears_page_gaps_enclosed_by_line_art(tmp_path):
    source = write_png(tmp_path / "ring.png", 256, ring_on_page)
    traced = json_of("trace", source, "--background", "remove")
    facts = json_of("inspect", traced["svg"])
    assert traced["enclosed"] == "clear"
    assert facts["background"] == "transparent"
    assert [colour for colour, _ in facts["colours"]] == ["#282c34"]


def test_review_passes_a_faithful_trace(tmp_path):
    source = write_png(tmp_path / "ring.png", 256, ring_on_page)
    traced = json_of("trace", source, "--background", "remove")
    verdict = json_of("review", traced["svg"], "--source", source)
    assert verdict["verdict"] == "PASS", verdict["doubts"]
    assert Path(verdict["sheet"]).is_file()


def test_review_doubts_a_trace_that_does_not_match_its_source(tmp_path):
    source = write_png(tmp_path / "ring.png", 256, ring_on_page)
    other = write_png(tmp_path / "plate.png", 256, plate_on_page)
    traced = json_of("trace", source)
    verdict = json_of("review", traced["svg"], "--source", other)
    assert verdict["verdict"] == "DOUBT"
    assert any("resemblance" in doubt for doubt in verdict["doubts"])


@pytest.mark.parametrize(
    ("body", "word"),
    [
        ('<circle cx="50" cy="50" r="10" fill="#224466"/>', "tiny"),
        (CROSS, "cut off"),
        (ROUNDED_PLATE, "pre-rounded"),
        (GRADIENT_PLATE, "pre-rounded"),
    ],
    ids=["tiny", "cut-off", "rounded-flat-plate", "rounded-gradient-plate"],
)
def test_review_doubts_art_that_would_ship_broken(tmp_path, body, word):
    verdict = json_of("review", write_svg(tmp_path / "art.svg", body))
    assert verdict["verdict"] == "DOUBT"
    assert any(word in doubt for doubt in verdict["doubts"]), verdict["doubts"]

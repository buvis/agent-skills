"""End-to-end tests for convert_to_icon.py.

The script declares its own dependencies (PEP 723), so every test drives it
through `uv run` in a child process and reads the results with the standard
library only. Run: uv run pytest skills/convert-to-icon/scripts -q
"""

from __future__ import annotations

import json
import re
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


def test_check_sheets_are_written_outside_the_bundle(disc_bundle):
    bundle, report = disc_bundle
    preview = Path(next(line for line in report.splitlines() if line.startswith("preview: "))[9:])
    review = Path(json_of("review", bundle / "disc.icon.svg")["sheet"])
    for sheet in (preview, review):
        assert sheet.is_file()
        assert bundle not in sheet.parents
    assert not list(bundle.glob("*.png"))


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


# A picture (the white subject covers most of it) whose edge is navy all the way round.
SCENE = '<rect width="100" height="100" rx="14" fill="#103060"/><rect x="12" y="12" width="76" height="76" fill="#fff"/>'


def test_extended_picture_is_continued_with_its_own_edge_colour(tmp_path):
    done = run_script("build", write_svg(tmp_path / "scene.svg", SCENE), "--picture", "extend")
    assert done.returncode == 0, done.stderr
    mask = json_of("inspect", tmp_path / "scene.icons/web/icon-mask.png")
    # The band around the shrunken picture must be that navy out to the canvas edge,
    # not a pale average of the navy and the white subject.
    assert mask["background"] == "#103060"
    # The white subject spans 0.76 of the picture, and the picture 0.8 of the canvas.
    assert mask["glyph_radius"] == pytest.approx(0.76 * 0.8 * 2**0.5, abs=0.03)


def test_cropped_picture_fills_the_cut_and_invents_nothing(tmp_path):
    assert run_script("build", write_svg(tmp_path / "scene.svg", SCENE)).returncode == 0
    bundle = tmp_path / "scene.icons"
    # Full size in the maskable icon: the circle will cut it, nothing is shrunk.
    assert json_of("inspect", bundle / "web/icon-mask.png")["glyph_radius"] == pytest.approx(0.76 * 2**0.5, abs=0.03)
    # On the Android layer the picture covers what a launcher shows (72 of 108 dp) and
    # stands alone: see-through around it, no invented band.
    layer = json_of("inspect", bundle / "android/res/mipmap-xxxhdpi/ic_launcher_foreground.png")
    assert layer["background"] == "transparent"
    assert layer["extent"] == pytest.approx(72 / 108, abs=0.02)


def test_gradient_plate_keeps_its_shape_on_a_field_when_a_colour_is_given(tmp_path):
    done = run_script("build", write_svg(tmp_path / "sky.svg", GRADIENT_PLATE), "--background", "#101010")
    assert done.returncode == 0, done.stderr
    ios = json_of("inspect", tmp_path / "sky.icons/ios/AppIcon.appiconset/icon-1024.png")
    assert ios["background"] == "#101010"


# A round badge shaded top to bottom, its two ends only a few dozen levels apart.
SHADED_BADGE = (
    '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#29b6dc"/><stop offset="1" stop-color="#0882c8"/></linearGradient></defs>'
    '<circle cx="50" cy="50" r="50" fill="url(#g)"/><circle cx="50" cy="50" r="18" fill="#fff"/>'
)


def test_softly_shaded_badge_is_a_picture_not_a_flat_plate(tmp_path):
    facts = json_of("review", write_svg(tmp_path / "badge.svg", SHADED_BADGE))["facts"]
    # Taken for a flat plate it would be extended in its middle shade, and show as a ring.
    assert facts["picture"] is True
    assert facts["plate"] is None


def test_round_badge_carrying_a_glyph_is_a_plate_too(tmp_path):
    badge = '<circle cx="50" cy="50" r="50" fill="#2244aa"/><circle cx="50" cy="50" r="18" fill="#fff"/>'
    svg = write_svg(tmp_path / "badge.svg", badge)
    assert any("pre-rounded plate" in doubt for doubt in json_of("review", svg)["doubts"])
    assert run_script("build", svg).returncode == 0
    ios = json_of("inspect", tmp_path / "badge.icons/ios/AppIcon.appiconset/icon-1024.png")
    assert ios["background"] == "#2244aa"


def test_cropped_picture_fills_the_cut_even_when_drawn_inside_margins(tmp_path):
    # The same picture as SCENE, drawn at 0.8 of a larger canvas.
    svg = write_svg(tmp_path / "scene.svg", SCENE, "-12.5 -12.5 125 125")
    assert run_script("build", svg).returncode == 0
    mask = json_of("inspect", tmp_path / "scene.icons/web/icon-mask.png")
    assert mask["glyph_radius"] == pytest.approx(0.76 * 2**0.5, abs=0.03)


def test_cropped_wide_picture_covers_the_cut_by_its_short_side(tmp_path):
    # Twice as wide as tall, two colours side by side, a white square (0.76 of the height) in the middle.
    wide = (
        '<rect width="100" height="100" fill="#103060"/><rect x="100" width="100" height="100" fill="#e0a040"/>'
        '<rect x="62" y="12" width="76" height="76" fill="#fff"/>'
    )
    assert run_script("build", write_svg(tmp_path / "wide.svg", wide, "0 0 200 100")).returncode == 0
    mask = json_of("inspect", tmp_path / "wide.icons/web/icon-mask.png")
    white = dict(mask["colours"]).get("#ffffff", 0.0)
    # Covering the square by the picture's height, the white square takes 0.76 squared of it.
    # Fitted by its width instead, with strips above and below, it would take a quarter of that.
    assert white == pytest.approx(0.76**2, abs=0.05)


def test_extended_picture_ignores_a_stray_line_along_its_edge(tmp_path):
    # SCENE with a thin white line along the top edge, as a screenshot border leaves behind.
    dirty = SCENE + '<rect x="14" width="72" height="1" fill="#fff"/>'
    done = run_script("build", write_svg(tmp_path / "scene.svg", dirty), "--picture", "extend")
    assert done.returncode == 0, done.stderr
    mask = json_of("inspect", tmp_path / "scene.icons/web/icon-mask.png")
    # The band above the picture stays navy: one dirty edge row is not smeared across it.
    assert mask["background"] == "#103060"


def noisy(x: int, y: int) -> tuple[int, int, int]:
    """Every pixel far from its neighbours, the way a photo's fine detail is."""
    return ((x * 97 + y * 57) % 256, (x * 31 + y * 139) % 256, (x * 173 + y * 11) % 256)


def soft_glow(x: int, y: int) -> tuple[int, int, int]:
    """An orange glow fading smoothly into navy: gradients, no flat shapes, no fine detail."""
    reach = max(0.0, 1 - ((x - 128) ** 2 + (y - 128) ** 2) ** 0.5 / 120) ** 2
    return tuple(round(dark + (bright - dark) * reach) for dark, bright in zip((17, 23, 39), (240, 150, 40)))


def neon_ring(x: int, y: int) -> tuple[int, int, int]:
    """A bright ring whose light fades slowly into navy: a stroke with a long soft tail."""
    spread = 1 / (1 + ((((x - 128) ** 2 + (y - 128) ** 2) ** 0.5 - 80) / 6) ** 2)
    return tuple(round(dark + (bright - dark) * spread) for dark, bright in zip((17, 23, 39), (255, 190, 80)))


def test_glow_art_is_traced_as_strokes_over_its_page(tmp_path):
    source = write_png(tmp_path / "neon.png", 256, neon_ring)
    page = json_of("inspect", source)["background"]
    traced = json_of("trace", source)
    assert traced["style"] == "glow"
    text = Path(traced["svg"]).read_text(encoding="utf-8")
    # The page is one plain rectangle in its own colour and the ring is drawn as lines:
    # stroked curves, nothing filled, with one blur for the fade. No bands, no painted areas.
    assert f'<rect x="0.0" y="0.0" width="512.0" height="512.0" fill="{page}"/>' in text
    assert "feGaussianBlur" in text
    assert 'fill="none"' in text and "stroke-width=" in text
    assert "<path fill=" not in text
    assert text.count("<path") <= 4
    verdict = json_of("review", traced["svg"])
    assert verdict["verdict"] == "PASS", verdict["doubts"]
    assert verdict["facts"]["stroke_overlap"] >= 0.7


def hairline_ring(x: int, y: int) -> tuple[int, int, int]:
    """The neon ring again, a third as thick: a hairline with a soft tail."""
    spread = 1 / (1 + ((((x - 128) ** 2 + (y - 128) ** 2) ** 0.5 - 80) / 2) ** 2)
    return tuple(round(dark + (bright - dark) * spread) for dark, bright in zip((17, 23, 39), (255, 190, 80)))


def test_line_drawing_is_drawn_bolder_in_small_icons(tmp_path):
    traced = json_of("trace", write_png(tmp_path / "hair.png", 256, hairline_ring), "--style", "glow")
    assert run_script("build", traced["svg"]).returncode == 0
    small = json_of("inspect", tmp_path / "hair.icons/android/res/mipmap-mdpi/ic_launcher.png")
    # At 48 px the hairline is a third of a pixel wide and would fade into the page. Drawn
    # bolder, the ring still shows in its own bright colour.
    assert max(int(colour[1:3], 16) for colour, _ in small["colours"]) >= 180


def ring_with_dust(x: int, y: int) -> tuple[int, int, int]:
    """The neon ring with a scatter of short faint dashes around it: detail, not meaning."""
    light = 1 / (1 + ((((x - 128) ** 2 + (y - 128) ** 2) ** 0.5 - 70) / 6) ** 2)
    for cx, cy in ((30, 40), (220, 30), (40, 215), (215, 220), (128, 18), (18, 128), (238, 128), (128, 238)):
        if abs(y - cy) <= 1 and abs(x - cx) <= 7:
            light = max(light, 0.55)
    return tuple(round(dark + (bright - dark) * light) for dark, bright in zip((17, 23, 39), (255, 190, 80)))


def test_line_drawing_keeps_the_meaning_and_drops_the_detail(tmp_path):
    traced = json_of("trace", write_png(tmp_path / "dusty.png", 256, ring_with_dust))
    pleasing = traced["pleasing"]
    # The ring is the drawing; the dashes are dirt and are gone.
    assert pleasing["strokes"] <= 2
    assert pleasing["fragments"] == 0
    assert pleasing["kept"] >= 0.75
    assert not [doubt for doubt in json_of("review", traced["svg"])["doubts"] if "hard on the eye" in doubt]


def test_review_doubts_a_line_drawing_that_is_hard_on_the_eye(tmp_path):
    measured = {"strokes": 16, "kept": 0.53, "fragments": 0.0, "loose_ends": 0.81, "wobble": 1.4, "off_centre": 0.11, "crowding": 0.2}
    svg = tmp_path / "arcs.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        f"data-pleasing='{json.dumps(measured)}'>".replace("'", '"').replace('{"', "{&quot;").replace('": ', "&quot;: ")
        .replace(', "', ", &quot;")
        + f"{DISC}</svg>",
        encoding="utf-8",
    )
    doubts = [doubt for doubt in json_of("review", svg)["doubts"] if "hard on the eye" in doubt]
    # Every limit this drawing breaks is named: too little kept, loose ends, wobble, balance.
    assert len(doubts) == 4
    assert any("loose ends 0.81" in doubt for doubt in doubts)


def test_keep_share_is_refused_outside_its_range(tmp_path):
    done = run_script("trace", write_png(tmp_path / "neon.png", 256, neon_ring), "--keep", "2")
    assert done.returncode != 0
    assert "expected a share from 0.3 to 1.0" in done.stderr


def test_layers_style_can_be_forced_on_soft_art(tmp_path):
    traced = json_of("trace", write_png(tmp_path / "neon.png", 256, neon_ring), "--style", "layers")
    assert traced["style"] == "layers"
    assert "feGaussianBlur" not in Path(traced["svg"]).read_text(encoding="utf-8")


def test_glow_style_is_refused_without_a_uniform_page(tmp_path):
    done = run_script("trace", write_png(tmp_path / "photo.png", 96, noisy), "--style", "glow")
    assert done.returncode != 0
    assert "uniform page" in done.stderr


def test_fine_detail_traces_layered_art_closer_to_its_source(tmp_path):
    source = write_png(tmp_path / "glow.png", 256, soft_glow)
    errors = {}
    for detail in ("normal", "fine"):
        traced = json_of("trace", source, "--name", detail, "--style", "layers", "--detail", detail)
        errors[detail] = json_of("review", traced["svg"])["facts"]["mean_error"]
    assert errors["fine"] < errors["normal"]


def test_review_points_a_weak_multi_colour_trace_at_fine_detail(tmp_path):
    traced = json_of("trace", write_png(tmp_path / "glow.png", 256, soft_glow), "--style", "layers")
    other = write_png(tmp_path / "plate.png", 256, plate_on_page)
    verdict = json_of("review", traced["svg"], "--source", other)
    assert any("resemblance" in doubt and "--detail fine" in doubt for doubt in verdict["doubts"]), verdict["doubts"]


def test_inspect_tells_a_photo_from_flat_art(tmp_path):
    assert json_of("inspect", write_png(tmp_path / "photo.png", 96, noisy))["photo"] is True
    assert json_of("inspect", write_png(tmp_path / "ring.png", 256, ring_on_page))["photo"] is False


def test_review_names_a_photo_as_the_cause_of_a_poor_trace(tmp_path):
    traced = json_of("trace", write_png(tmp_path / "photo.png", 96, noisy))
    assert traced["photo"] is True
    verdict = json_of("review", traced["svg"])
    assert any("photo" in doubt for doubt in verdict["doubts"]), verdict["doubts"]


OUTLINED_DISC = '<circle cx="50" cy="50" r="42" fill="#9cc5f9" stroke="#000" stroke-width="5"/>'
OUTLINED_SPIKE = '<path d="M50 8L92 88L8 88Z" fill="#f5e165" stroke="#000" stroke-width="6" stroke-linejoin="round"/>'
OUTLINED_SHINE = OUTLINED_SPIKE.replace("#f5e165", "#9cc5f9") + '<circle cx="50" cy="62" r="11" fill="#eef2f8"/>'


@pytest.mark.parametrize("body", [OUTLINED_DISC, OUTLINED_SPIKE, OUTLINED_SHINE], ids=["disc", "spike", "shine"])
def test_light_art_with_dark_outlines_gets_a_white_field(tmp_path, body):
    assert run_script("build", write_svg(tmp_path / "art.svg", body)).returncode == 0
    ios = json_of("inspect", tmp_path / "art.icons/ios/AppIcon.appiconset/icon-1024.png")
    # A dark field would swallow the outlines, and an outline is not a plate to extend.
    assert ios["background"] == "#ffffff"


def notched_block(x: int, y: int) -> tuple[int, int, int]:
    """A dark block that fills most of its box but is no plate: a notch is cut into its top."""
    if 108 <= x < 148 and 28 <= y < 68:
        return WHITE
    return DARK if 28 <= x < 228 and 28 <= y < 228 else WHITE


def test_trace_leaves_room_around_art_that_is_not_a_plate(tmp_path):
    traced = json_of("trace", write_png(tmp_path / "block.png", 256, notched_block), "--background", "remove")
    assert json_of("inspect", traced["svg"])["margin"] >= 0.04


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


def test_trace_keeps_the_original_raster_under_its_own_name(tmp_path):
    source = write_png(tmp_path / "logo.icon.png", 256, ring_on_page)
    traced = json_of("trace", source, "--background", "remove", "--name", "brand")
    kept = tmp_path / "brand.icons" / "logo.icon.png"
    assert Path(traced["original"]) == kept
    assert kept.read_bytes() == source.read_bytes()
    assert source.is_file()


def test_photo_gets_no_themed_layer(tmp_path):
    traced = json_of("trace", write_png(tmp_path / "photo.png", 96, noisy))
    done = run_script("build", traced["svg"])
    assert done.returncode == 0, done.stdout + done.stderr
    bundle = tmp_path / "photo.icons"
    # A photo has no clean outline: specks would ship as the themed icon, so it is left out
    # and Android falls back to the normal icon.
    assert "themed icon left out" in done.stdout
    assert not list(bundle.rglob("ic_launcher_monochrome.png"))
    assert "<monochrome" not in (bundle / "android/res/mipmap-anydpi-v26/ic_launcher.xml").read_text(encoding="utf-8")
    assert "icon set complete: 40 files" in done.stdout


def test_review_compares_against_the_kept_original_without_being_told(tmp_path):
    source = write_png(tmp_path / "logo.icon.png", 256, ring_on_page)
    traced = json_of("trace", source, "--background", "remove", "--name", "brand")
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


def test_tiny_source_is_traced_at_no_less_than_512_px(tmp_path):
    source = write_png(tmp_path / "ring.png", 96, lambda x, y: ring_on_page(x * 256 // 96, y * 256 // 96))
    text = Path(json_of("trace", source, "--background", "remove")["svg"]).read_text(encoding="utf-8")
    worked, given = (float(re.search(rf'{box}="[-\d.]+ [-\d.]+ ([\d.]+)', text).group(1)) for box in ("viewBox", "data-source-box"))
    # Outlined at twice its size, a 96 px drawing comes out lumpy.
    assert worked / given * 96 >= 512


def test_page_hidden_by_art_that_touches_the_edge_can_be_named(tmp_path):
    bars = write_png(tmp_path / "bars.png", 256, lambda x, y: DARK if 100 <= x < 156 or 100 <= y < 156 else WHITE)
    # The bars run off every side, so no uniform page is found and nothing would be removed.
    assert json_of("inspect", bars)["background"] is None
    facts = json_of("inspect", json_of("trace", bars, "--background", "remove", "--page", "#ffffff")["svg"])
    assert [colour for colour, _ in facts["colours"]] == ["#282c34"]


def test_fit_tightens_a_half_empty_canvas_to_its_art(tmp_path):
    dot = write_svg(tmp_path / "dot.svg", '<circle cx="50" cy="50" r="20" fill="#224466"/>')
    assert any("--fit" in doubt for doubt in json_of("review", dot)["doubts"])
    assert run_script("build", dot, "--fit").returncode == 0
    # The disc spanned 40% of its canvas. Fitted, it fills it but for 6% of room on each side.
    assert json_of("inspect", tmp_path / "dot.icons/web/icon-512.png")["extent"] == pytest.approx(1 / 1.12, abs=0.02)
    # Only the bundle's master is rewritten; the file it was pointed at stays as it was.
    assert 'viewBox="0 0 100 100"' in dot.read_text(encoding="utf-8")


def test_move_leaves_the_source_in_the_bundle_only(tmp_path):
    raster = write_png(tmp_path / "ring.png", 256, ring_on_page)
    traced = json_of("trace", raster, "--background", "remove", "--move")
    assert not raster.exists()
    assert Path(traced["original"]).is_file()
    loose = write_svg(tmp_path / "disc.svg", DISC)
    assert run_script("build", loose, "--move").returncode == 0
    assert not loose.exists()
    assert (tmp_path / "disc.icons/disc.icon.svg").is_file()


def test_move_keeps_a_source_the_bundle_does_not_hold(tmp_path):
    loose = write_svg(tmp_path / "disc.svg", DISC)
    assert run_script("build", loose).returncode == 0
    write_svg(loose, CROSS)  # redrawn after the bundle was built: the master is the old drawing
    done = run_script("build", loose, "--move")
    assert done.returncode == 0, done.stderr
    # Removing it would lose the new drawing, which exists nowhere else.
    assert loose.exists()
    assert "left in place" in done.stdout


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
        ('<rect x="5" y="40" width="90" height="20" fill="#224466"/>', "thin strip"),
    ],
    ids=["tiny", "cut-off", "rounded-flat-plate", "rounded-gradient-plate", "wordmark-shaped"],
)
def test_review_doubts_art_that_would_ship_broken(tmp_path, body, word):
    verdict = json_of("review", write_svg(tmp_path / "art.svg", body))
    assert verdict["verdict"] == "DOUBT"
    assert any(word in doubt for doubt in verdict["doubts"]), verdict["doubts"]


def test_review_offers_crop_and_extend_for_a_picture(tmp_path):
    verdict = json_of("review", write_svg(tmp_path / "art.svg", GRADIENT_PLATE))
    assert any("--picture crop" in doubt and "--picture extend" in doubt for doubt in verdict["doubts"])

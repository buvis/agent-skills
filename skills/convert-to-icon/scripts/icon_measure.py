"""Facts about an image: colours, plates, tones, and the small helpers the other modules share."""

from __future__ import annotations

import argparse
import html
import io
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import resvg_py
from PIL import Image, ImageDraw

RGB = tuple[int, int, int]

TOLERANCE = 40  # channel distance still read as one flat colour; absorbs JPEG noise
MIN_SHARE = 0.03  # below this share a colour is an edge blend, not a colour of the art
PHOTO_DETAIL = 0.2  # fine detail above this share means a photo; flat art measured 0.02 to 0.07


def to_hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(v) for v in rgb[:3])


def from_hex(text: str) -> RGB:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        raise argparse.ArgumentTypeError(f"expected a colour like #1a2b3c, got {text!r}")
    return (int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16))


def icon_name(path: Path) -> str:
    return re.sub(r"\.icons?$", "", path.stem)


def bundle_for(path: Path, out: Path | None, name: str | None = None) -> Path:
    """The bundle is --out, else the .icons folder the file already sits in, else a new one beside it."""
    if out:
        return out
    return path.parent if path.parent.suffix == ".icons" else path.parent / f"{name or icon_name(path)}.icons"


def near(rgb: np.ndarray, colour: RGB) -> np.ndarray:
    return np.abs(rgb.astype(np.int16) - np.array(colour)).max(axis=-1) <= TOLERANCE


def small_size_style(svg: Path, px: int) -> str | None:
    """Hairlines vanish at small sizes. Below 128 px a line drawing (see icon_lines) is redrawn
    the way a hand-made small icon is: strokes about a pixel and a half wide, and only the
    brightest half of the lines; below 48 px only the brightest quarter."""
    if px >= 128:
        return None
    text = svg.read_text(encoding="utf-8")
    box = re.search(r'viewBox="[-\d.]+ [-\d.]+ ([-\d.]+)', text)
    if 'id="strokes"' not in text or not box:
        return None
    width = 1.6 * float(box.group(1)) / px
    hidden = "#strokes .rank3, #strokes .rank4" + (", #strokes .rank2" if px < 48 else "")
    return f"#strokes path {{ stroke-width: {width:.1f} }} {hidden} {{ display: none }}"


def rasterise(svg: Path, px: int) -> Image.Image:
    """Draw an SVG to fit a px square; resvg keeps the aspect ratio."""
    png = resvg_py.svg_to_bytes(svg_path=str(svg), width=px, height=px, style_sheet=small_size_style(svg, px))
    return Image.open(io.BytesIO(bytes(png))).convert("RGBA")


def centred(art: Image.Image, px: int, backdrop=(0, 0, 0, 0)) -> Image.Image:
    """Put art in the middle of a px square: padded, never stretched."""
    layer = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    layer.paste(art, ((px - art.width) // 2, (px - art.height) // 2))
    return Image.alpha_composite(Image.new("RGBA", (px, px), backdrop), layer)


def bounds(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        sys.exit("the image has no visible art")
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def filled(mask: np.ndarray) -> float:
    """How much of its own bounding box a shape covers."""
    x0, y0, x1, y1 = bounds(mask)
    return float(mask.sum() / ((x1 - x0) * (y1 - y0)))


def reach(mask: np.ndarray) -> float:
    """Farthest pixel from the centre; 1.0 is the middle of a square canvas edge."""
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return 0.0
    h, w = mask.shape
    return float(np.hypot(xs + 0.5 - w / 2, ys + 0.5 - h / 2).max() / (max(w, h) / 2))


def fine_detail(img: Image.Image) -> float:
    """Share of pixels that step sharply away from a neighbour: about 0.05 in flat art, 0.3 in a photo."""
    small = img.convert("RGB")
    small.thumbnail((512, 512), Image.Resampling.BOX)
    pixels = np.asarray(small).astype(np.int16)
    right = np.abs(pixels[:-1, 1:] - pixels[:-1, :-1]).max(axis=-1)
    down = np.abs(pixels[1:, :-1] - pixels[:-1, :-1]).max(axis=-1)
    return float((np.maximum(right, down) > 16).mean())


def dominant_colours(rgb: np.ndarray) -> list[tuple[RGB, float]]:
    """Flat colours among N pixels, largest first, with their share."""
    if not len(rgb):
        return []
    # Histogram peaks, not median cut: a peak's mean is the flat colour itself, while a
    # median-cut box averages the colour with its edge blends and drifts.
    keys = (rgb >> 4).astype(np.int32) @ np.array([256, 16, 1])
    counts = np.bincount(keys, minlength=4096)
    sums = np.stack([np.bincount(keys, weights=rgb[:, channel], minlength=4096) for channel in range(3)], axis=1)
    merged: list[tuple[RGB, int]] = []
    for key in np.argsort(-counts):
        count = int(counts[key])
        if not count:
            break
        colour = tuple(int(round(v)) for v in sums[key] / count)
        twin = next(
            (i for i, (seen, _) in enumerate(merged) if max(abs(a - b) for a, b in zip(seen, colour)) <= TOLERANCE),
            None,
        )
        if twin is None:
            merged.append((colour, count))
        else:
            merged[twin] = (merged[twin][0], merged[twin][1] + count)
    ranked = sorted(merged, key=lambda entry: -entry[1])
    return [(colour, count / len(rgb)) for colour, count in ranked if count / len(rgb) >= MIN_SHARE]


def find_plate(rgb: np.ndarray, solid: np.ndarray) -> tuple[RGB | None, bool, bool]:
    """A plate is a block the art sits on: a square, sharp or rounded, or a disc. Returns its edge
    colour (None when the art is not on a plate), whether that colour is flat across the plate, and
    whether the plate stops short of its box's corners. A plate that is not flat is a picture: a
    gradient, a photo, a scene."""
    x0, y0, x1, y1 = bounds(solid)
    bw, bh = x1 - x0, y1 - y0
    inset = max(1, min(bw, bh) // 25)
    mids = [
        (y0 + inset, x0 + bw // 2),
        (y1 - 1 - inset, x0 + bw // 2),
        (y0 + bh // 2, x0 + inset),
        (y0 + bh // 2, x1 - 1 - inset),
    ]
    box = (slice(y0, y1), slice(x0, x1))
    patch = solid[box]
    yy, xx = np.ogrid[:bh, :bw]
    disc = ((xx + 0.5) / bw * 2 - 1) ** 2 + ((yy + 0.5) / bh * 2 - 1) ** 2 <= 1
    # A square covers its own box (a rounded one over 0.94); a disc matches the box's ellipse.
    blocky = patch.mean() >= 0.85 or (patch & disc).sum() / (patch | disc).sum() >= 0.9
    if not blocky or not all(solid[p] for p in mids):
        return None, False, False
    colour = tuple(int(v) for v in np.median([rgb[p] for p in mids], axis=0))
    share = (near(rgb[box], colour) & patch).sum() / patch.sum()
    even = all(near(rgb[p], colour) for p in mids)
    if even and share > 0.995:  # one colour with nothing on it is the art itself, not a plate
        return None, False, False
    flat = even and share >= 0.5
    nick = max(1, min(bw, bh) // 100)
    corners = [(y, x) for y in (y0 + nick, y1 - 1 - nick) for x in (x0 + nick, x1 - 1 - nick)]
    return colour, bool(flat), not all(solid[p] for p in corners)


def edge_ring(h: int, w: int) -> np.ndarray:
    """The outer frame of a canvas, 2% deep: where a page shows, if there is one."""
    frame = max(2, min(w, h) // 50)
    ring = np.ones((h, w), bool)
    ring[frame:-frame, frame:-frame] = False
    return ring


def measure_art(img: Image.Image) -> dict:
    """Facts the checks and the layout rules need, in canvas-relative units."""
    data = np.asarray(img)
    rgb, solid = data[..., :3], data[..., 3] >= 128
    h, w = solid.shape
    side = max(w, h)
    ring = edge_ring(h, w)
    background, plate, picture, rounded = None, None, None, False
    if not solid[ring].any():
        background = "transparent"
    elif solid[ring].all():
        edge = tuple(int(v) for v in np.median(rgb[ring], axis=0))
        if near(rgb[ring], edge).mean() >= 0.98:
            background, plate = to_hex(edge), edge
    if plate is None:
        colour, flat, rounded = find_plate(rgb, solid)
        plate, picture = (colour, None) if flat else (None, colour)
    x0, y0, x1, y1 = bounds(solid)
    gaps = (x0 + (side - w) / 2, y0 + (side - h) / 2, (side + w) / 2 - x1, (side + h) / 2 - y1)
    return {
        "size": [w, h],
        "square": w == h,
        "background": background,
        "plate": to_hex(plate) if plate else None,
        "picture": picture is not None,
        "edge": to_hex(picture) if picture else None,
        "plate_rounded": rounded,
        "aspect": round(max(x1 - x0, y1 - y0) / min(x1 - x0, y1 - y0), 2),
        "photo": fine_detail(img) > PHOTO_DETAIL,
        "extent": round(max(x1 - x0, y1 - y0) / side, 3),
        "margin": round(min(gaps) / side, 3),
        "radius": round(reach(solid), 3),
        "glyph_radius": round(reach(solid & ~near(rgb, plate) if plate else solid), 3),
        "colours": [[to_hex(colour), round(share, 3)] for colour, share in dominant_colours(rgb[solid])],
    }


def tone_map(rgb: np.ndarray, page: RGB) -> np.ndarray:
    """How far each pixel has moved from the page colour towards the art's strongest colour:
    0 on the page, 1 at full strength."""
    wide = rgb.astype(np.float32)
    away = np.abs(wide - page).sum(axis=-1)
    peak = wide[away >= np.percentile(away, 99.5)].mean(axis=0)
    axis = peak - np.array(page, np.float32)
    return np.clip(((wide - page) @ axis) / max(float(axis @ axis), 1.0), 0, 1)


def stroke_level(tone: np.ndarray) -> tuple[float, bool]:
    """Where haze ends and stroke begins (an Otsu split of the art's tones), and whether the art
    is soft: most of it lies below that split, spread over many tones rather than a few flat ones."""
    values = tone[tone >= 0.08]
    if len(values) < 100:
        return 1.0, False
    hist, edges = np.histogram(values, bins=64, range=(0, 1))
    mids = (edges[:-1] + edges[1:]) / 2
    weight, total = hist.cumsum(), hist.sum()
    mean = (hist * mids).cumsum()
    between = (mean[-1] * weight - mean * total) ** 2 / (weight * (total - weight) + 1e-9)
    core = float(mids[between.argmax()])
    soft = (values < core).mean() >= 0.5 and np.sort(hist)[-3:].sum() / total <= 0.3
    return core, bool(soft)


def sheet_path(name: str, kind: str) -> Path:
    """Check sheets are for looking at once: they live in the temp folder, never in the bundle."""
    return Path(tempfile.gettempdir()) / "convert-to-icon" / f"{name}.{kind}.png"


def kept_original(svg: Path) -> Path | None:
    """The raster a traced SVG came from, when it still sits beside it."""
    named = re.search(r'data-source="([^"]+)"', svg.read_text(encoding="utf-8"))
    original = svg.parent / html.unescape(named.group(1)) if named else None
    return original if original and original.is_file() else None


def save_sheet(panels: list[tuple[str, Image.Image]], path: Path) -> None:
    """Lay labelled square panels side by side into one image."""
    cell = panels[0][1].width
    page = Image.new("RGB", (cell * len(panels), cell + 24), "white")
    draw = ImageDraw.Draw(page)
    for column, (label, panel) in enumerate(panels):
        page.paste(panel.convert("RGB"), (column * cell, 24))
        draw.text((column * cell + 6, 6), label, fill="black")
    path.parent.mkdir(parents=True, exist_ok=True)
    page.save(path)

# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["numpy", "pillow>=10.1", "potracer", "resvg-py", "vtracer"]
# ///
"""Turn an image into a master SVG and a bundle of platform icons.

    inspect IMAGE              facts about a raster or SVG, as JSON
    trace RASTER               raster -> <name>.icons/<name>.icon.svg
    review SVG [--source R]    review sheet plus a PASS/DOUBT verdict, as JSON
    build SVG                  write every missing icon file, then verify the set

Python is capped below 3.14: vtracer 0.6.15 segfaults there inside
convert_image_to_svg_py.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import potrace
import resvg_py
import vtracer
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

RGB = tuple[int, int, int]

TOLERANCE = 40  # channel distance still read as one flat colour; absorbs JPEG noise
MIN_SHARE = 0.03  # below this share a colour is an edge blend, not a colour of the art
MAC_BODY = 824 / 1024  # macOS icon grid: the body inside the canvas
MAC_ROUNDNESS = 0.2237  # its corner radius, as a share of the body
ICONSET = "macos/AppIcon.iconset"
ICOS = {"web/favicon.ico": (16, 32, 48), "windows/app.ico": (16, 20, 24, 32, 40, 48, 64, 256)}
DENSITIES = {"mdpi": 1.0, "hdpi": 1.5, "xhdpi": 2.0, "xxhdpi": 3.0, "xxxhdpi": 4.0}


@dataclass(frozen=True)
class Png:
    path: str
    px: int
    zone: float = 0.0  # diameter of the circle the art must stay inside, as a share of px
    body: bool = False  # laid out on the macOS grid
    opaque: bool = False  # the platform forbids transparency
    circle: bool = False
    mono: bool = False


@dataclass(frozen=True)
class Look:
    facts: dict
    fill: RGB  # colour behind the art wherever transparency is not allowed
    plate: RGB | None  # set when that fill continues the icon's own plate


def to_hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(v) for v in rgb[:3])


def from_hex(text: str) -> RGB:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        raise argparse.ArgumentTypeError(f"expected a colour like #1a2b3c, got {text!r}")
    return (int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16))


def existing_file(text: str) -> Path:
    path = Path(text).expanduser()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"no such file: {text}")
    return path


def icon_name(path: Path) -> str:
    return re.sub(r"\.icons?$", "", path.stem)


def pixel_size(text: str) -> int:
    if not text.isdigit() or not 1 <= int(text) <= 4096:
        raise argparse.ArgumentTypeError(f"expected a size from 1 to 4096 px, got {text!r}")
    return int(text)


def plain_name(text: str) -> str:
    if not re.fullmatch(r"[\w-]+(\.[\w-]+)*", text):
        raise argparse.ArgumentTypeError(f"expected a plain name like my-app, got {text!r}")
    return text


def bundle_for(path: Path, out: Path | None, name: str | None = None) -> Path:
    """The bundle is --out, else the .icons folder the file already sits in, else a new one beside it."""
    if out:
        return out
    return path.parent if path.parent.suffix == ".icons" else path.parent / f"{name or icon_name(path)}.icons"


def near(rgb: np.ndarray, colour: RGB) -> np.ndarray:
    return np.abs(rgb.astype(np.int16) - np.array(colour)).max(axis=-1) <= TOLERANCE


def rasterise(svg: Path, px: int) -> Image.Image:
    """Draw an SVG to fit a px square; resvg keeps the aspect ratio."""
    png = resvg_py.svg_to_bytes(svg_path=str(svg), width=px, height=px)
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


def find_plate(rgb: np.ndarray, solid: np.ndarray) -> tuple[RGB | None, bool]:
    """A plate is one flat colour filling the art's box edge to edge. Also: are its corners rounded?"""
    x0, y0, x1, y1 = bounds(solid)
    bw, bh = x1 - x0, y1 - y0
    inset = max(1, min(bw, bh) // 25)
    mids = [
        (y0 + inset, x0 + bw // 2),
        (y1 - 1 - inset, x0 + bw // 2),
        (y0 + bh // 2, x0 + inset),
        (y0 + bh // 2, x1 - 1 - inset),
    ]
    if not all(solid[p] for p in mids):
        return None, False
    colour = tuple(int(v) for v in np.median([rgb[p] for p in mids], axis=0))
    box = (slice(y0, y1), slice(x0, x1))
    if not all(near(rgb[p], colour) for p in mids) or (near(rgb[box], colour) & solid[box]).mean() < 0.5:
        return None, False
    nick = max(1, min(bw, bh) // 100)
    corners = [(y, x) for y in (y0 + nick, y1 - 1 - nick) for x in (x0 + nick, x1 - 1 - nick)]
    return colour, not all(solid[p] and near(rgb[p], colour) for p in corners)


def measure_art(img: Image.Image) -> dict:
    """Facts the checks and the layout rules need, in canvas-relative units."""
    data = np.asarray(img)
    rgb, solid = data[..., :3], data[..., 3] >= 128
    h, w = solid.shape
    side = max(w, h)
    frame = max(2, min(w, h) // 50)
    ring = np.ones((h, w), bool)
    ring[frame:-frame, frame:-frame] = False
    background, plate, rounded = None, None, False
    if not solid[ring].any():
        background = "transparent"
    elif solid[ring].all():
        edge = tuple(int(v) for v in np.median(rgb[ring], axis=0))
        if near(rgb[ring], edge).mean() >= 0.98:
            background, plate = to_hex(edge), edge
    if plate is None:
        plate, rounded = find_plate(rgb, solid)
    x0, y0, x1, y1 = bounds(solid)
    gaps = (x0 + (side - w) / 2, y0 + (side - h) / 2, (side + w) / 2 - x1, (side + h) / 2 - y1)
    return {
        "size": [w, h],
        "square": w == h,
        "background": background,
        "plate": to_hex(plate) if plate else None,
        "plate_rounded": rounded,
        "extent": round(max(x1 - x0, y1 - y0) / side, 3),
        "margin": round(min(gaps) / side, 3),
        "radius": round(reach(solid), 3),
        "glyph_radius": round(reach(solid & ~near(rgb, plate) if plate else solid), 3),
        "colours": [[to_hex(colour), round(share, 3)] for colour, share in dominant_colours(rgb[solid])],
    }


def border_connected(mask: np.ndarray) -> np.ndarray:
    """The part of mask that can be reached from the canvas edge."""
    # copy(): fromarray hands back a read-only image, and floodfill on one silently does nothing
    padded = Image.fromarray(np.pad(mask, 1, constant_values=True).astype(np.uint8) * 255).copy()
    ImageDraw.floodfill(padded, (0, 0), 128)
    return (np.asarray(padded) == 128)[1:-1, 1:-1]


def outline(mask: np.ndarray, speck: int) -> str:
    """Potrace a mask into SVG path data. Potrace traces the dark pixels."""
    bitmap = potrace.Bitmap(Image.fromarray(np.where(mask, 0, 255).astype(np.uint8)))
    parts = []
    for curve in bitmap.trace(turdsize=speck):
        parts.append("M%.1f,%.1f" % (curve.start_point.x, curve.start_point.y))
        for seg in curve.segments:
            points = (seg.c, seg.end_point) if seg.is_corner else (seg.c1, seg.c2, seg.end_point)
            parts.append(("L" if seg.is_corner else "C") + " ".join("%.1f,%.1f" % (p.x, p.y) for p in points))
        parts.append("z")
    return "".join(parts)


def trace_flat(labels: np.ndarray, footprint: np.ndarray, palette: list[RGB], speck: int) -> str:
    """One or two flat colours: the footprint in its main colour, the other colour on top."""
    base = int(np.bincount(labels[footprint], minlength=2).argmax())
    shapes = [(palette[base], outline(footprint, speck))]
    top = footprint & (labels != base)
    if top.sum() > speck:
        shapes.append((palette[1 - base], outline(top, speck)))
    return "".join(f'<path fill="{to_hex(c)}" fill-rule="evenodd" d="{d}"/>' for c, d in shapes)


def trace_shaded(img: Image.Image, removed: np.ndarray, fringe: bool) -> str:
    """Many colours: vtracer stacks one layer per colour."""
    if fringe:  # widen the cut by a pixel so no blend of art and background survives as a halo
        removed = np.asarray(Image.fromarray(removed.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) > 0
    layer = img.copy()
    layer.putalpha(Image.fromarray(np.where(removed, 0, 255).astype(np.uint8)))
    with tempfile.TemporaryDirectory() as tmp:
        png, svg = Path(tmp) / "cut.png", Path(tmp) / "cut.svg"
        layer.save(png)
        vtracer.convert_image_to_svg_py(
            str(png),
            str(svg),
            colormode="color",
            hierarchical="stacked",
            mode="spline",
            filter_speckle=8,
            color_precision=6,
            layer_difference=12,
            path_precision=2,
        )
        return re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", svg.read_text(encoding="utf-8"), flags=re.S).strip()


def trace_raster(src: Path, svg: Path, remove: bool, enclosed: str, colours: int | None) -> dict:
    img = Image.open(src).convert("RGBA")
    zoom = 2 if max(img.size) < 1024 else 1  # small sources trace into lumpy curves
    if zoom > 1:
        img = img.resize((img.width * zoom, img.height * zoom), Image.Resampling.LANCZOS)
    facts = measure_art(img)
    data = np.asarray(img)
    rgb, solid = data[..., :3], data[..., 3] >= 128
    palette = [colour for colour, _ in dominant_colours(rgb[solid])]
    count = colours or len(palette)
    if count <= 2:
        palette = palette[:2]
    wide = rgb.astype(np.int16)
    labels = np.stack([np.abs(wide - np.array(c)).sum(axis=-1) for c in palette]).argmin(axis=0)
    removed = ~solid
    paper = from_hex(facts["background"]) if remove and (facts["background"] or "").startswith("#") else None
    if paper:
        index = min(range(len(palette)), key=lambda i: sum(abs(a - b) for a, b in zip(palette[i], paper)))
        sheet = solid & (labels == index)
        if enclosed == "auto":  # a plate keeps what it encloses, line art lets it show through
            enclosed = "keep" if count > 2 or filled(solid & ~sheet) >= 0.5 else "clear"
        removed = removed | (sheet if enclosed == "clear" else border_connected(sheet))
    footprint = ~removed
    x0, y0, x1, y1 = bounds(footprint)
    side = max(x1 - x0, y1 - y0) * (1.0 if filled(footprint) >= 0.85 else 1.12)
    x, y = (x0 + x1 - side) / 2, (y0 + y1 - side) / 2
    speck = max(2, (max(img.size) // 300) ** 2)
    flat = count <= 2
    body = trace_flat(labels, footprint, palette, speck) if flat else trace_shaded(img, removed, bool(paper))
    attrs = f'viewBox="{x:.1f} {y:.1f} {side:.1f} {side:.1f}"'
    attrs += f' data-source-box="{x / zoom:.1f} {y / zoom:.1f} {side / zoom:.1f}"'
    if paper:
        attrs += f' data-background="{to_hex(paper)}"'
    svg.parent.mkdir(parents=True, exist_ok=True)
    document = f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" {attrs}>{body}</svg>\n'
    svg.write_text(document, encoding="utf-8")
    return {
        "svg": str(svg),
        "tracer": "potrace" if flat else "vtracer",
        "colours": count,
        "background": f"removed {to_hex(paper)}" if paper else "kept",
        "enclosed": enclosed if paper else "n/a",
    }


def look_of(svg: Path, facts: dict, override: RGB | None) -> Look:
    plate = from_hex(facts["plate"]) if facts["plate"] else None
    declared = re.search(r'data-background="(#[0-9a-fA-F]{6})"', svg.read_text(encoding="utf-8"))
    if override:
        fill = override
    elif plate:
        fill = plate
    elif declared:
        fill = from_hex(declared.group(1))
    else:  # nothing known: pick the side that contrasts with the art
        r, g, b = from_hex(facts["colours"][0][0]) if facts["colours"] else (0, 0, 0)
        fill = (255, 255, 255) if 0.299 * r + 0.587 * g + 0.114 * b < 160 else (17, 17, 17)
    return Look(facts, fill, plate if fill == plate else None)


def shape_mask(px: int, share: float, roundness: float) -> Image.Image:
    big = px * 4
    side = big * share
    edge = (big - side) / 2
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((edge, edge, big - edge - 1, big - edge - 1), side * roundness, fill=255)
    return mask.resize((px, px), Image.Resampling.LANCZOS)


def silhouette(icon: Image.Image, plate: RGB | None) -> Image.Image:
    """White shape for Android themed icons: the art without its plate."""
    alpha = icon.getchannel("A")
    if plate:
        flat = Image.alpha_composite(Image.new("RGBA", icon.size, (*plate, 255)), icon).convert("RGB")
        alpha = ImageOps.autocontrast(ImageChops.difference(flat, Image.new("RGB", icon.size, plate)).convert("L"))
    shape = Image.new("RGBA", icon.size, (255, 255, 255, 0))
    shape.putalpha(alpha)
    return shape


def compose(svg: Path, spec: Png, look: Look) -> Image.Image:
    facts = look.facts
    scale = 1.0
    if spec.zone:  # keep the art inside the circle a launcher may cut
        scale = min(1.0, spec.zone / max(facts["glyph_radius" if look.plate else "radius"], 0.01))
    if spec.body:
        scale = min(1.0, MAC_BODY / facts["extent"])
    shaped = spec.body and look.plate is not None
    backdrop = (*look.fill, 255) if spec.opaque or shaped else (0, 0, 0, 0)
    icon = centred(rasterise(svg, max(1, round(spec.px * scale))), spec.px, backdrop)
    if spec.mono:
        icon = silhouette(icon, look.plate)
    if spec.circle:
        icon.putalpha(shape_mask(spec.px, 1.0, 0.5))
    if shaped:
        # ponytail: a rounded rectangle stands in for Apple's continuous-corner shape, and there is
        # no drop shadow. Draw the icon in Icon Composer when the difference matters.
        icon.putalpha(shape_mask(spec.px, MAC_BODY, MAC_ROUNDNESS))
    return icon.convert("RGB") if spec.opaque and not spec.circle else icon


def plan_pngs(extra: list[int]) -> list[Png]:
    pngs = [
        Png("web/apple-touch-icon.png", 180, zone=0.9, opaque=True),
        Png("web/icon-192.png", 192),
        Png("web/icon-512.png", 512),
        Png("web/icon-mask.png", 512, zone=0.8, opaque=True),
        Png("ios/AppIcon.appiconset/icon-1024.png", 1024, zone=0.9, opaque=True),
        Png("android/play-store-512.png", 512, zone=0.9, opaque=True),
    ]
    for points in (16, 32, 128, 256, 512):
        pngs.append(Png(f"{ICONSET}/icon_{points}x{points}.png", points, body=True))
        pngs.append(Png(f"{ICONSET}/icon_{points}x{points}@2x.png", points * 2, body=True))
    for density, factor in DENSITIES.items():
        folder = f"android/res/mipmap-{density}"
        launcher, layer = round(48 * factor), round(108 * factor)
        pngs += [
            Png(f"{folder}/ic_launcher.png", launcher),
            Png(f"{folder}/ic_launcher_round.png", launcher, zone=0.9, opaque=True, circle=True),
            Png(f"{folder}/ic_launcher_foreground.png", layer, zone=66 / 108),
            Png(f"{folder}/ic_launcher_monochrome.png", layer, zone=66 / 108, mono=True),
        ]
    return pngs + [Png(f"png/icon-{px}.png", px) for px in extra]


def companion_texts(fill: RGB) -> dict[str, str]:
    adaptive = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/ic_launcher_background"/>\n'
        '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
        '    <monochrome android:drawable="@mipmap/ic_launcher_monochrome"/>\n'
        "</adaptive-icon>\n"
    )
    colour = (
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        f'    <color name="ic_launcher_background">{to_hex(fill).upper()}</color>\n</resources>\n'
    )
    ios = {"filename": "icon-1024.png", "idiom": "universal", "platform": "ios", "size": "1024x1024"}
    web = [
        {"src": "icon-192.png", "type": "image/png", "sizes": "192x192"},
        {"src": "icon-512.png", "type": "image/png", "sizes": "512x512"},
        {"src": "icon-mask.png", "type": "image/png", "sizes": "512x512", "purpose": "maskable"},
    ]
    contents = {"images": [ios], "info": {"author": "xcode", "version": 1}}
    return {
        "android/res/mipmap-anydpi-v26/ic_launcher.xml": adaptive,
        "android/res/mipmap-anydpi-v26/ic_launcher_round.xml": adaptive,
        "android/res/values/ic_launcher_background.xml": colour,
        "ios/AppIcon.appiconset/Contents.json": json.dumps(contents, indent=2) + "\n",
        "web/manifest.webmanifest": json.dumps({"icons": web}, indent=2) + "\n",
    }


def write_icns(iconset: Path, icns: Path) -> None:
    if shutil.which("iconutil"):
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(icns)], check=True)
        return
    # ponytail: off macOS, Pillow writes the .icns without the 16 and 32 px 1x entries.
    # Rebuild it with iconutil on a Mac if those sizes matter.
    names = ("icon_16x16@2x", "icon_32x32@2x", "icon_128x128", "icon_256x256", "icon_512x512")
    frames = [Image.open(iconset / f"{name}.png") for name in names]
    Image.open(iconset / "icon_512x512@2x.png").save(icns, append_images=frames)


def verify_bundle(bundle: Path, pngs: list[Png], others: list[str]) -> list[str]:
    problems = []
    for spec in pngs:
        path = bundle / spec.path
        if not path.is_file():
            problems.append(f"missing {spec.path}")
            continue
        with Image.open(path) as im:
            if im.size != (spec.px, spec.px):
                problems.append(f"{spec.path} is {im.size[0]}x{im.size[1]}, expected {spec.px}x{spec.px}")
            if spec.opaque and not spec.circle and im.mode != "RGB":
                problems.append(f"{spec.path} must not carry transparency")
    for rel, sizes in ICOS.items():
        path = bundle / rel
        if not path.is_file():
            problems.append(f"missing {rel}")
            continue
        with Image.open(path) as im:
            if set(im.info["sizes"]) != {(px, px) for px in sizes}:
                problems.append(f"{rel} holds sizes {sorted(im.info['sizes'])}, expected {sizes}")
    for rel in others:
        path = bundle / rel
        if not path.is_file() or path.stat().st_size == 0:
            problems.append(f"missing {rel}")
    return problems


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


def preview_bundle(bundle: Path, look: Look) -> Path:
    """One sheet of the finished icons, cut the way each platform shows them."""
    cell, grey = 256, (128, 128, 128, 255)
    fit = Image.Resampling.LANCZOS

    def cut(icon: Image.Image, roundness: float) -> Image.Image:
        icon = icon.convert("RGBA").resize((cell, cell), fit)
        icon.putalpha(ImageChops.multiply(icon.getchannel("A"), shape_mask(cell, 1.0, roundness)))
        return centred(icon, cell, grey)

    def launcher(layer_name: str, behind: RGB) -> Image.Image:
        layer = Image.open(bundle / f"android/res/mipmap-xxxhdpi/{layer_name}.png").convert("RGBA")
        whole = Image.alpha_composite(Image.new("RGBA", layer.size, (*behind, 255)), layer)
        return cut(whole.crop((72, 72, 360, 360)), 0.5)  # a launcher shows 72 of the layer's 108 dp

    small = Image.open(bundle / "android/res/mipmap-mdpi/ic_launcher.png").convert("RGBA")
    panels = [
        ("ios, masked", cut(Image.open(bundle / "ios/AppIcon.appiconset/icon-1024.png"), MAC_ROUNDNESS)),
        ("maskable, circle cut", cut(Image.open(bundle / "web/icon-mask.png"), 0.5)),
        ("macos", centred(Image.open(bundle / ICONSET / "icon_128x128@2x.png").convert("RGBA"), cell, grey)),
        ("android adaptive", launcher("ic_launcher_foreground", look.fill)),
        ("android themed", launcher("ic_launcher_monochrome", (32, 40, 56))),
        ("launcher 48 px", centred(small, 48, grey).resize((cell, cell), Image.Resampling.NEAREST)),
    ]
    save_sheet(panels, bundle / "preview.png")
    return bundle / "preview.png"


def build_bundle(svg: Path, bundle: Path, override: RGB | None, extra: list[int], force: bool) -> int:
    master = bundle / f"{icon_name(svg)}.icon.svg"
    bundle.mkdir(parents=True, exist_ok=True)
    if svg.resolve() != master.resolve():
        if force or not master.exists():
            shutil.copyfile(svg, master)
        elif master.read_bytes() != svg.read_bytes():
            print(f"note: {master} differs from {svg}; the bundle's copy was used (--force replaces it)")
    look = look_of(master, measure_art(rasterise(master, 1024)), override)
    created: list[str] = []

    def missing(rel: str) -> Path | None:
        path = bundle / rel
        if path.exists() and not force:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        created.append(rel)
        return path

    pngs = plan_pngs(extra)
    for spec in pngs:
        if path := missing(spec.path):
            compose(master, spec, look).save(path)
    for rel, sizes in ICOS.items():
        if path := missing(rel):
            frames = [compose(master, Png(rel, px), look) for px in sizes]
            frames[-1].save(path, sizes=[(px, px) for px in sizes], append_images=frames[:-1])
    if path := missing("macos/AppIcon.icns"):
        write_icns(bundle / ICONSET, path)
    texts = companion_texts(look.fill)
    for rel, text in texts.items():
        if path := missing(rel):
            path.write_text(text, encoding="utf-8")
    if path := missing("web/icon.svg"):
        shutil.copyfile(master, path)
    others = ["macos/AppIcon.icns", *texts, "web/icon.svg"]
    expected = [spec.path for spec in pngs] + [*ICOS] + others
    problems = verify_bundle(bundle, pngs, others)
    kept = [rel for rel in expected if rel not in created and (bundle / rel).exists()]
    stale = [rel for rel in kept if (bundle / rel).stat().st_mtime < master.stat().st_mtime]
    print(f"bundle: {bundle}")
    print(f"created {len(created)}, kept {len(kept)}; fill colour {to_hex(look.fill)}")
    if stale:
        print(f"stale: {len(stale)} kept files are older than the master SVG (--force rebuilds them)")
    for problem in problems:
        print(f"problem: {problem}")
    if problems:
        print(f"icon set INCOMPLETE: {len(problems)} problems")
        return 1
    print(f"preview: {preview_bundle(bundle, look)}")
    print(f"icon set complete: {len(expected)} files")
    return 0


def resemblance(svg: Path, source: Path, px: int = 512) -> tuple[float, float, Image.Image]:
    """Mean channel error, percent of pixels clearly off, and the source framed like the SVG."""
    text = svg.read_text(encoding="utf-8")
    src = Image.open(source).convert("RGBA")
    side = float(max(src.size))
    x, y = (src.width - side) / 2, (src.height - side) / 2
    if framed := re.search(r'data-source-box="([-\d.]+) ([-\d.]+) ([-\d.]+)"', text):
        x, y, side = (float(v) for v in framed.groups())
    crop = src.crop((round(x), round(y), round(x + side), round(y + side)))
    declared = re.search(r'data-background="(#[0-9a-fA-F]{6})"', text)
    paper = (*(from_hex(declared.group(1)) if declared else (255, 255, 255)), 255)
    pair = [crop.resize((px, px), Image.Resampling.LANCZOS), centred(rasterise(svg, px), px)]
    flat = [Image.alpha_composite(Image.new("RGBA", (px, px), paper), im).convert("RGB") for im in pair]
    delta = np.abs(np.asarray(flat[0]).astype(np.int16) - np.asarray(flat[1]))
    return float(delta.mean()), float((delta.max(axis=-1) > 40).mean() * 100), flat[0]


def review_svg(svg: Path, source: Path | None, override: RGB | None, sheet: Path) -> dict:
    facts = measure_art(rasterise(svg, 1024))
    look = look_of(svg, facts, override)
    doubts, notes = [], []
    if not facts["square"]:
        notes.append("canvas is not square: every icon pads it to a square, never stretches it")
    if facts["extent"] < 0.6:
        doubts.append(f"art fills only {facts['extent']:.0%} of the canvas: it will look tiny")
    if facts["margin"] < 0.01 and not facts["plate"]:
        doubts.append("art touches the canvas edge: part of it may be cut off")
    if facts["plate_rounded"]:
        doubts.append(
            f"pre-rounded plate: masked icons extend {facts['plate']} to the corners so the platform "
            "rounds it once; confirm, or pass another --background to keep the plate's own shape"
        )
    cell = 384
    shot = centred(rasterise(svg, cell), cell)
    cut = compose(svg, Png("", cell, zone=0.8, opaque=True), look).convert("RGBA")
    cut.putalpha(shape_mask(cell, 1.0, 0.5))
    tiny = centred(rasterise(svg, 32), 32, (255, 255, 255, 255)).resize((cell, cell), Image.Resampling.NEAREST)
    panels = [
        ("svg on white", centred(shot, cell, (255, 255, 255, 255))),
        ("svg on magenta", centred(shot, cell, (255, 0, 255, 255))),
        ("circle cut", centred(cut, cell, (128, 128, 128, 255))),
        ("32 px", tiny),
    ]
    if source:
        error, off, framed = resemblance(svg, source)
        facts = {**facts, "mean_error": round(error, 2), "percent_off": round(off, 2)}
        if error > 6 or off > 3:
            doubts.append(f"weak resemblance to the source: mean error {error:.1f}, {off:.1f}% of pixels off")
        panels.insert(0, ("source", framed.resize((cell, cell))))
    span = max(facts["glyph_radius" if look.plate else "radius"], 0.01)
    notes.append(
        f"circular cut: art drawn at {min(1.0, 0.8 / span):.0%} in the maskable icon "
        f"and at {min(1.0, 66 / 108 / span):.0%} of the Android adaptive layer"
    )
    save_sheet(panels, sheet)
    verdict = "DOUBT" if doubts else "PASS"
    return {"verdict": verdict, "doubts": doubts, "notes": notes, "facts": facts, "sheet": str(sheet)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect").add_argument("image", type=existing_file)
    tracer = commands.add_parser("trace")
    tracer.add_argument("raster", type=existing_file)
    tracer.add_argument("--background", choices=("keep", "remove"), default="keep")
    tracer.add_argument("--enclosed", choices=("auto", "keep", "clear"), default="auto")
    tracer.add_argument("--colors", type=int, choices=range(1, 9))
    tracer.add_argument("--name", type=plain_name)
    reviewer = commands.add_parser("review")
    reviewer.add_argument("svg", type=existing_file)
    reviewer.add_argument("--source", type=existing_file)
    builder = commands.add_parser("build")
    builder.add_argument("svg", type=existing_file)
    builder.add_argument("--png", type=pixel_size, action="append", default=[])
    for command in (tracer, reviewer, builder):
        command.add_argument("--out", type=Path)
    for command in (tracer, builder):
        command.add_argument("--force", action="store_true")
    for command in (reviewer, builder):
        command.add_argument("--background", type=from_hex)
    args = parser.parse_args()
    if args.command == "inspect":
        image = args.image
        shot = rasterise(image, 1024) if image.suffix.lower() == ".svg" else Image.open(image).convert("RGBA")
        print(json.dumps(measure_art(shot), indent=2))
        return 0
    if args.command == "trace":
        name = args.name or icon_name(args.raster)
        svg = bundle_for(args.raster, args.out, name) / f"{name}.icon.svg"
        if svg.exists() and not args.force:
            sys.exit(f"{svg} exists; --force replaces it")
        remove = args.background == "remove"
        print(json.dumps(trace_raster(args.raster, svg, remove, args.enclosed, args.colors), indent=2))
        return 0
    bundle = bundle_for(args.svg, args.out)
    if args.command == "review":
        print(json.dumps(review_svg(args.svg, args.source, args.background, bundle / "review.png"), indent=2))
        return 0
    return build_bundle(args.svg, bundle, args.background, args.png, args.force)


if __name__ == "__main__":
    sys.exit(main())

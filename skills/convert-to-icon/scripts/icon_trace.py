"""Raster to SVG: flat shapes, colour layers, or glowing art."""

from __future__ import annotations

import html
import re
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import potrace
import vtracer
from PIL import Image, ImageDraw, ImageFilter

from icon_measure import RGB, bounds, dominant_colours, filled, from_hex, measure_art, stroke_level, to_hex, tone_map


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


def trace_shaded(img: Image.Image, removed: np.ndarray, fringe: bool, fine: bool) -> str:
    """Many colours: vtracer stacks one layer per colour. Fine keeps more colour steps and
    smaller shapes, which soft glows and gradients need, at about twice the file size."""
    speckle, precision, difference = (4, 8, 8) if fine else (8, 6, 12)
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
            filter_speckle=speckle,
            color_precision=precision,
            layer_difference=difference,
            path_precision=2,
        )
        return re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", svg.read_text(encoding="utf-8"), flags=re.S).strip()


def trace_raster(src: Path, svg: Path, remove: bool, enclosed: str, colours: int | None, fine: bool, style: str) -> dict:
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
    page = from_hex(facts["background"]) if (facts["background"] or "").startswith("#") else None
    paper = page if remove else None
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
    _, soft = stroke_level(tone_map(rgb, page)) if page else (1.0, False)
    if style == "glow" and not page:
        sys.exit("the glow style needs a uniform page behind the art")
    # Soft art is settled before the colour count: a thin glow spreads over so many tones
    # that none of them counts as a colour, and it would pass for two-colour line art.
    if style == "glow" or (style == "auto" and soft and colours is None):
        board = "" if paper else f'<rect x="{x:.1f}" y="{y:.1f}" width="{side:.1f}" height="{side:.1f}" fill="{to_hex(page)}"/>'
        # Imported here: line tracing pulls in scipy and scikit-image, which every other
        # command would otherwise pay for at start-up.
        from icon_lines import trace_strokes

        style, body = "glow", board + trace_strokes(img, page, side)
    elif count <= 2:
        style, body = "flat", trace_flat(labels, footprint, palette, speck)
    else:
        style, body = "layers", trace_shaded(img, removed, bool(paper), fine)
    attrs = f'viewBox="{x:.1f} {y:.1f} {side:.1f} {side:.1f}"'
    attrs += f' data-source-box="{x / zoom:.1f} {y / zoom:.1f} {side / zoom:.1f}"'
    attrs += f' data-source="{html.escape(src.name, quote=True)}" data-style="{style}"'
    if style == "layers":
        attrs += f' data-detail="{"fine" if fine else "normal"}"'
    if paper:
        attrs += f' data-background="{to_hex(paper)}"'
    svg.parent.mkdir(parents=True, exist_ok=True)
    document = f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" {attrs}>{body}</svg>\n'
    svg.write_text(document, encoding="utf-8")
    original = svg.parent / src.name  # the kept copy carries the source's own file name
    if src.resolve() != original.resolve():
        shutil.copyfile(src, original)
    return {
        "svg": str(svg),
        "original": str(original),
        "style": style,
        "colours": count,
        "background": f"removed {to_hex(paper)}" if paper else "kept",
        "enclosed": enclosed if paper else "n/a",
        "photo": facts["photo"],
        "detail": ("fine" if fine else "normal") if style == "layers" else "n/a",
    }

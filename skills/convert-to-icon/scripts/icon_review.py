"""The check before building: an SVG against its source, with a sheet to look at."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image

from icon_measure import PHOTO_DETAIL, RGB, centred, edge_ring, fine_detail, from_hex, icon_name, measure_art, rasterise, save_sheet, sheet_path, stroke_level, tone_map
from icon_build import Png, compose, look_of, shape_mask


def framed_pair(svg: Path, source: Path, px: int = 512) -> tuple[Image.Image, Image.Image]:
    """The source framed the way the SVG frames it, and the SVG drawn at the same size."""
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
    return flat[0], flat[1]


def compare_with_source(svg: Path, source: Path) -> tuple[dict, list[str], list[str], Image.Image]:
    """Measures, doubts and notes from setting a trace beside the raster it came from."""
    framed, shot = framed_pair(svg, source)
    truth, drawn = np.asarray(framed), np.asarray(shot)
    delta = np.abs(truth.astype(np.int16) - drawn)
    error, off = float(delta.mean()), float((delta.max(axis=-1) > 40).mean() * 100)
    measures = {"mean_error": round(error, 2), "percent_off": round(off, 2)}
    text = svg.read_text(encoding="utf-8")
    if 'data-style="glow"' in text:
        # Pixel error is the wrong yardstick here, since the haze is left out on purpose.
        # What must hold is that the traced strokes sit on the source's strokes.
        page = tuple(int(v) for v in np.median(truth[edge_ring(*truth.shape[:2])], axis=0))
        theirs = tone_map(truth, page)
        core, _ = stroke_level(theirs)
        mine = tone_map(drawn, page) >= core
        overlap = float((mine & (theirs >= core)).sum() / max((mine | (theirs >= core)).sum(), 1))
        notes = ["glow style: the strokes are paths and the fade is a blur; haze inside the art is left out on purpose"]
        doubts = [f"the traced strokes match only {overlap:.0%} of the source's strokes"] if overlap < 0.7 else []
        return {**measures, "stroke_overlap": round(overlap, 2)}, doubts, notes, framed
    if error > 6 or off > 3:
        retry = "; retrace with --detail fine for a closer match" if 'data-detail="normal"' in text else ""
        weak = f"weak resemblance to the source: mean error {error:.1f}, {off:.1f}% of pixels off{retry}"
        return measures, [weak], [], framed
    return measures, [], [], framed


def review_svg(svg: Path, source: Path | None, override: RGB | None) -> dict:
    facts = measure_art(rasterise(svg, 1024))
    look = look_of(svg, facts, override)
    doubts, notes = [], []
    if not facts["square"]:
        notes.append("canvas is not square: every icon pads it to a square, never stretches it")
    if facts["extent"] < 0.6:
        doubts.append(f"art fills only {facts['extent']:.0%} of the canvas: it will look tiny")
    busy = fine_detail(Image.open(source) if source else rasterise(svg, 1024))
    if busy > PHOTO_DETAIL:
        doubts.append(
            f"the art is as busy as a photo ({busy:.0%} fine detail): a trace of it is a posterised "
            f"approximation, and this SVG weighs {svg.stat().st_size / 1e6:.1f} MB"
        )
    if facts["aspect"] > 2:
        doubts.append(f"art is {facts['aspect']:.1f} times longer one way: a square icon shows it as a thin strip")
    if facts["margin"] < 0.01 and not facts["plate"] and not facts["picture"]:
        doubts.append("art touches the canvas edge: part of it may be cut off")
    if look.picture:
        doubts.append(
            f"{'pre-rounded ' if facts['plate_rounded'] else ''}picture plate: under a circle cut choose "
            "--picture crop (sharp; what falls outside the circle is lost) or --picture extend (whole "
            "picture kept, inside a soft band grown from its edge colours); --background with a colour "
            "keeps its shape on a flat field instead"
        )
    elif facts["plate_rounded"] and facts["plate"]:
        doubts.append(
            f"pre-rounded plate: masked icons extend {facts['plate']} to the corners so the platform "
            "rounds it once; confirm, or pass --background with another colour to keep the plate's own shape"
        )
    cell = 384

    def circle_cut(crop: bool) -> Image.Image:
        cut = compose(svg, Png("", cell, zone=0.8, opaque=True), replace(look, crop=crop)).convert("RGBA")
        cut.putalpha(shape_mask(cell, 1.0, 0.5))
        return centred(cut, cell, (128, 128, 128, 255))

    shot = centred(rasterise(svg, cell), cell)
    tiny = centred(rasterise(svg, 32), 32, (255, 255, 255, 255)).resize((cell, cell), Image.Resampling.NEAREST)
    cuts = [("circle cut", circle_cut(False))]
    if look.picture:
        cuts = [("circle cut, crop", circle_cut(True)), ("circle cut, extend", circle_cut(False))]
    panels = [
        ("svg on white", centred(shot, cell, (255, 255, 255, 255))),
        ("svg on magenta", centred(shot, cell, (255, 0, 255, 255))),
        *cuts,
        ("32 px", tiny),
    ]
    if source:
        measures, found, remarks, framed = compare_with_source(svg, source)
        facts, doubts, notes = {**facts, **measures}, doubts + found, notes + remarks
        panels.insert(0, ("source", framed.resize((cell, cell))))
    span = 1.0 if look.picture else max(facts["glyph_radius" if look.plate else "radius"], 0.01)
    notes.append(
        f"circular cut: art drawn at {min(1.0, 0.8 / span):.0%} in the maskable icon "
        f"and at {min(1.0, 66 / 108 / span):.0%} of the Android adaptive layer"
        + (" when extended; at full size and 67% when cropped" if look.picture else "")
    )
    sheet = sheet_path(icon_name(svg), "review")
    save_sheet(panels, sheet)
    verdict = "DOUBT" if doubts else "PASS"
    return {"verdict": verdict, "doubts": doubts, "notes": notes, "facts": facts, "sheet": str(sheet)}

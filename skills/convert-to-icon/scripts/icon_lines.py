"""Centre lines: the ridges of light in soft art, drawn as stroked curves instead of filled areas."""

from __future__ import annotations

import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
from skimage.filters import sato, threshold_otsu
from skimage.measure import approximate_polygon
from skimage.morphology import skeletonize

from icon_measure import RGB, to_hex, tone_map

WORK = 1024  # ridges are looked for at this size; more pixels add time, not lines
Line = list[tuple[int, int]]


def walk_skeleton(skeleton: np.ndarray) -> list[tuple[Line, bool]]:
    """Follow a one-pixel skeleton into lines. Each comes with whether one of its ends is loose."""
    points = set(zip(*(axis.tolist() for axis in np.nonzero(skeleton))))

    def neighbours(p: tuple[int, int]) -> Line:
        around = ((p[0] + dy, p[1] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
        return [q for q in around if q in points]

    degree = {p: len(neighbours(p)) for p in points}
    nodes = {p for p, links in degree.items() if links != 2}  # ends and junctions
    walked, lines = set(), []
    for node in nodes:
        for step in neighbours(node):
            if (node, step) in walked:
                continue
            line, before, here = [node, step], node, step
            walked.add((node, step))
            while here not in nodes:
                onward = [q for q in neighbours(here) if q != before]
                if not onward:
                    break
                before, here = here, onward[0]
                line.append(here)
            walked.add((here, before))
            lines.append((line, degree[line[0]] == 1 or degree[line[-1]] == 1))
    unvisited = points - {p for line, _ in lines for p in line}
    while unvisited:  # closed loops have neither an end nor a junction to start from
        start = unvisited.pop()
        line, before, here = [start], None, start
        while onward := [q for q in neighbours(here) if q != before and q in unvisited]:
            before, here = here, onward[0]
            unvisited.discard(here)
            line.append(here)
        lines.append((line + [start], False))
    return lines


def line_length(line: Line) -> float:
    return float(np.hypot(*np.diff(np.array(line, float), axis=0).T).sum())


def centre_lines(tone: np.ndarray) -> tuple[list[Line], np.ndarray]:
    """One-pixel lines along the ridges of light, and half the ridge's width at every pixel."""
    scale = max(tone.shape) / WORK
    lit = tone > 0.08
    if not lit.any():
        return [], np.zeros(tone.shape)
    ridge = sato(tone, sigmas=[1.5 * scale, 2.5 * scale, 4 * scale], black_ridges=False)
    mask = (ridge > threshold_otsu(ridge[lit]) * 0.8) & (tone > 0.12)
    spur = 0.03 * max(tone.shape)  # a loose end shorter than this is noise, not a line
    skeleton = skeletonize(mask)
    for _ in range(3):  # each pass frees the junctions the pruned ends hung from
        kept = np.zeros_like(skeleton)
        for line, loose in walk_skeleton(skeleton):
            if not (loose and line_length(line) < spur):
                ys, xs = np.array(line).T
                kept[ys, xs] = True
        skeleton = skeletonize(kept)
    lines = [line for line, loose in walk_skeleton(skeleton) if not (loose and line_length(line) < spur)]
    return lines, ndimage.distance_transform_edt(mask)


def smooth_curve(line: Line, zoom: float) -> str:
    """A Catmull-Rom spline through the line's simplified points, written as cubic Beziers."""
    points = approximate_polygon(np.array(line, float), 1.8)[:, ::-1] * zoom  # (y, x) to (x, y)
    padded = np.vstack([points[0], points, points[-1]])
    parts = [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1 : i + 3]
        c1, c2 = p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6
        parts.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return "".join(parts)


def trace_strokes(img: Image.Image, page: RGB, side: float) -> str:
    """Soft, luminous art as a line drawing: every ridge of light becomes a stroked curve with
    the ridge's own width and colour, and the fade is one blur of those strokes. Nothing is
    filled. Tracing the light as it looks would paint areas and stack bands instead."""
    shrink = min(1.0, WORK / max(img.size))
    small = img.convert("RGB")
    if shrink < 1:
        small = small.resize((round(img.width * shrink), round(img.height * shrink)), Image.Resampling.LANCZOS)
    tone = tone_map(np.asarray(small), page)
    lines, half_width = centre_lines(tone)
    if not lines:
        sys.exit("the glow style found no lines of light to trace")
    # A line's colour is taken a little blurred: at its exact centre a glow is nearly white.
    colours = np.asarray(small.filter(ImageFilter.GaussianBlur(3 * max(small.size) / WORK)))
    zoom, thin, thick = 1 / shrink, 0.0015 * side, 0.009 * side
    # Lines are ranked by weight (brightness times thickness) into quarters of the drawing's
    # total length: rank1 is the heaviest quarter, which is where the subject is. Small icons
    # keep only the top ranks (see small_size_style).
    spots = [tuple(np.array(line).T) for line in lines]
    weight = [float(np.median(tone[spot]) * np.median(half_width[spot])) for spot in spots]
    lengths = [line_length(line) for line in lines]
    rank, drawn = {}, 0.0
    for i in sorted(range(len(lines)), key=lambda i: -weight[i]):
        rank[i] = 1 + min(3, int(4 * drawn / sum(lengths)))
        drawn += lengths[i]
    strokes = []
    for i, line in enumerate(lines):
        ys, xs = spots[i]
        width = float(np.clip(2 * np.median(half_width[ys, xs]) * zoom, thin, thick))
        shade = to_hex(np.median(colours[ys, xs], axis=0))
        strokes.append(
            f'<path class="rank{rank[i]}" d="{smooth_curve(line, zoom)}" stroke="{shade}" stroke-width="{width:.1f}"/>'
        )
    return (
        '<filter id="glow" x="-10%" y="-10%" width="120%" height="120%">'
        f'<feGaussianBlur stdDeviation="{side * 0.008:.1f}"/></filter>'
        f'<defs><g id="strokes" fill="none" stroke-linecap="round" stroke-linejoin="round">{"".join(strokes)}</g></defs>'
        '<use href="#strokes" filter="url(#glow)" opacity="0.8"/><use href="#strokes"/>'
    )

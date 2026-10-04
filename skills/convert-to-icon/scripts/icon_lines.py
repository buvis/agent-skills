"""Centre lines: the ridges of light in soft art, drawn as a few smooth stroked curves.

An icon carries what a picture means, not its detail. So the lines found here are joined into
long strokes, and only as many are kept as stay easy on the eye (see PLEASING in icon_measure).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from scipy.interpolate import splev, splprep
from scipy.spatial import cKDTree
from skimage.filters import sato, threshold_otsu
from skimage.morphology import skeletonize

from icon_measure import RGB, displeasing, to_hex, tone_map

WORK = 1024  # ridges are looked for at this size; more pixels add time, not lines
SHARES = (0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6)  # of the drawing's weight, tried in turn
Line = list[tuple[int, int]]


@dataclass(frozen=True)
class Stroke:
    points: np.ndarray  # (y, x) along the stroke
    length: float
    weight: float  # brightness times thickness: how much the stroke matters
    loop: bool


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


def span(points) -> float:
    return float(np.hypot(*np.diff(np.asarray(points, float), axis=0).T).sum())


def centre_lines(tone: np.ndarray) -> tuple[list[Line], np.ndarray]:
    """One-pixel lines along the ridges of light, and half the ridge's width at every pixel."""
    scale = max(tone.shape) / WORK
    lit = tone > 0.08
    if not lit.any():
        return [], np.zeros(tone.shape)
    # Fine lines first: they are the crisp geometry (a glowing tube is its two bright edges).
    # Thick strokes are looked for only where no fine line runs, or the vague middle of every
    # tube would be traced as well; without them a thick stroke beside thin ones would be missed.
    fine = sato(tone, sigmas=[width * scale for width in (1.5, 2.5, 4)], black_ridges=False)
    thin = (fine > threshold_otsu(fine[lit]) * 0.8) & (tone > 0.12)
    wide = sato(tone, sigmas=[width * scale for width in (6, 12)], black_ridges=False)
    apart = ~ndimage.binary_dilation(thin, iterations=max(1, round(12 * scale)))
    mask = thin | ((wide > threshold_otsu(wide[lit]) * 0.8) & (tone > 0.12) & apart)
    spur = 0.03 * max(tone.shape)  # a loose end shorter than this is noise, not a line
    skeleton = skeletonize(mask)
    for _ in range(3):  # each pass frees the junctions the pruned ends hung from
        kept = np.zeros_like(skeleton)
        for line, loose in walk_skeleton(skeleton):
            if not (loose and span(line) < spur):
                ys, xs = np.array(line).T
                kept[ys, xs] = True
        skeleton = skeletonize(kept)
    lines = [line for line, loose in walk_skeleton(skeleton) if not (loose and span(line) < spur)]
    return lines, ndimage.distance_transform_edt(mask)


def join_lines(lines: list[Line]) -> list[np.ndarray]:
    """Join lines through their junctions into long chains: where ends meet, the two that run
    straightest into each other become one stroke."""
    runs = [np.array(line, float) for line in lines if len(line) >= 2]

    def heading(run: np.ndarray, at_start: bool) -> np.ndarray:
        reach = min(12, len(run) - 1)
        vector = run[0] - run[reach] if at_start else run[-1] - run[-1 - reach]
        return vector / max(float(np.hypot(*vector)), 1e-6)

    ends = [(i, at_start) for i in range(len(runs)) for at_start in (True, False)]
    if not ends:
        return []
    spots = np.array([runs[i][0] if at_start else runs[i][-1] for i, at_start in ends])
    offers = []
    for a, b in cKDTree(spots).query_pairs(4.0):
        if ends[a][0] != ends[b][0]:
            straight = float(-heading(runs[ends[a][0]], ends[a][1]) @ heading(runs[ends[b][0]], ends[b][1]))
            if straight > 0.6:
                offers.append((straight, ends[a], ends[b]))
    partner = {}
    for _, a, b in sorted(offers, reverse=True):
        if a not in partner and b not in partner:
            partner[a], partner[b] = b, a
    chains, used = [], set()
    for i in range(len(runs)):
        if i in used:
            continue
        end = (i, True) if (i, True) not in partner else (i, False)
        chain = []
        while end[0] not in used:
            index, at_start = end
            used.add(index)
            chain.append(runs[index] if at_start else runs[index][::-1])
            if (index, not at_start) not in partner:
                break
            end = partner[(index, not at_start)]
        chains.append(np.vstack(chain))
    return chains


def smooth_stroke(stroke: Stroke, zoom: float) -> np.ndarray:
    """A smoothing spline through the stroke, sampled every few pixels: the wobble of a traced
    line goes, its sweep stays."""
    points = stroke.points[np.r_[True, np.hypot(*np.diff(stroke.points, axis=0).T) > 0]]
    if len(points) < 6:
        return points * zoom
    firmness = len(points) * 3.0**2  # the spline may stray about three pixels from the traced line
    try:
        spline, _ = splprep([points[:, 0], points[:, 1]], s=firmness, per=stroke.loop)
    except ValueError:  # a loop too tight to close smoothly is fitted as an open curve
        spline, _ = splprep([points[:, 0], points[:, 1]], s=firmness)
    return np.array(splev(np.linspace(0, 1, max(8, int(stroke.length / 6))), spline)).T * zoom


def loose_ends(strokes: list[Stroke], curves: list[np.ndarray], reach: float) -> list[int]:
    """For each stroke, how many of its ends meet nothing."""
    cloud = cKDTree(np.vstack(curves))
    owner = np.concatenate([np.full(len(curve), i) for i, curve in enumerate(curves)])
    counts = []
    for i, (stroke, curve) in enumerate(zip(strokes, curves)):
        tips = [] if stroke.loop else [curve[0], curve[-1]]
        counts.append(sum(not any(owner[j] != i for j in cloud.query_ball_point(tip, reach)) for tip in tips))
    return counts


def measure_strokes(strokes: list[Stroke], curves: list[np.ndarray], total: float, size: float, centre) -> dict:
    """The measures PLEASING sets limits on. size is the art's width, centre its middle."""
    lengths = np.array([span(curve) for curve in curves])
    bends = 0
    for curve in curves:
        step = np.diff(curve, axis=0)
        turn = np.diff(np.unwrap(np.arctan2(step[:, 0], step[:, 1])))
        firm = np.convolve(turn, np.ones(5) / 5, mode="valid") if len(turn) >= 5 else turn
        bends += int((np.diff(np.sign(firm[np.abs(firm) > 0.01])) != 0).sum())
    middle = np.average(np.vstack([curve.mean(axis=0) for curve in curves]), axis=0, weights=lengths)
    # Crowding: the strokes drawn two pixels wide on a 96 px picture of the art.
    scale, corner = 96 / size, np.asarray(centre) - size / 2
    board = Image.new("L", (96, 96), 0)
    pen = ImageDraw.Draw(board)
    for curve in curves:
        pen.line([tuple(p) for p in ((curve - corner) * scale)[:, ::-1]], fill=255, width=2)
    return {
        "strokes": len(strokes),
        "kept": round(sum(s.length * s.weight for s in strokes) / total, 2),
        "fragments": round(float(lengths[lengths < 0.08 * size].sum() / lengths.sum()), 2),
        "loose_ends": round(sum(loose_ends(strokes, curves, 0.02 * size)) / len(strokes), 2),
        "wobble": round(bends / max(float(lengths.sum()) / size, 1e-6), 2),
        "off_centre": round(float(np.hypot(*(middle - centre)) / (size / 2)), 2),
        "crowding": round(float((np.asarray(board) > 0).mean()), 2),
    }


def choose_strokes(strokes: list[Stroke], zoom: float, keep: float | None) -> tuple[list[Stroke], list[np.ndarray], dict]:
    """Keep as much of the drawing as stays pleasing: the heaviest strokes first, down a ladder
    of shares of its total weight, stopping at the first that breaks no limit."""
    points = np.vstack([s.points for s in strokes]) * zoom
    centre = points.mean(axis=0)
    size = 2 * float(np.percentile(np.hypot(*(points - centre).T), 97))
    total = sum(s.length * s.weight for s in strokes)
    ranked = sorted(strokes, key=lambda s: -s.length * s.weight)
    solid = [s for s in ranked if s.loop or s.length * zoom >= 0.08 * size] or ranked  # shorter bits read as dirt
    best = None
    for share in (keep,) if keep else SHARES:
        kept, carried = [], 0.0
        for stroke in solid:
            if carried >= share * total:
                break
            kept.append(stroke)
            carried += stroke.length * stroke.weight
        curves = [smooth_stroke(stroke, zoom) for stroke in kept]
        # A short dash that touches nothing at either end is dirt too.
        adrift = loose_ends(kept, curves, 0.02 * size)
        stays = [n < 2 or span(c) >= 0.15 * size for n, c in zip(adrift, curves)]
        if not any(stays):  # a drawing made of nothing but dashes keeps them
            stays = [True] * len(kept)
        kept, curves = [s for s, ok in zip(kept, stays) if ok], [c for c, ok in zip(curves, stays) if ok]
        measures = measure_strokes(kept, curves, total, size, centre)
        faults = len(displeasing(measures))
        if best is None or faults < best[3]:
            best = (kept, curves, measures, faults)
        if not faults:
            break
    return best[:3]


def bezier_path(curve: np.ndarray, loop: bool) -> str:
    """A Catmull-Rom spline through the points, written as cubic Beziers."""
    points = curve[:, ::-1]  # (y, x) to (x, y)
    padded = np.vstack([points[-2] if loop else points[0], points, points[1] if loop else points[-1]])
    parts = [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1 : i + 3]
        c1, c2 = p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6
        parts.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return "".join(parts)


def trace_strokes(img: Image.Image, page: RGB, side: float, keep: float | None) -> tuple[str, dict]:
    """Soft, luminous art as a line drawing: its ridges of light joined into long strokes, the
    heaviest kept and smoothed, in two weights and two shades, with one blur of them for the
    fade. Nothing is filled. Returns the SVG fragment and the measures of the drawing."""
    shrink = min(1.0, WORK / max(img.size))
    small = img.convert("RGB")
    if shrink < 1:
        small = small.resize((round(img.width * shrink), round(img.height * shrink)), Image.Resampling.LANCZOS)
    tone = tone_map(np.asarray(small), page)
    lines, half_width = centre_lines(tone)
    strokes = []
    for chain in join_lines(lines):
        if span(chain) < 8:
            continue
        spot = (chain[:, 0].astype(int), chain[:, 1].astype(int))
        weight = float(np.median(tone[spot]) * np.median(half_width[spot]))
        loop = bool(span(chain) > 40 and np.hypot(*(chain[0] - chain[-1])) <= 6)
        strokes.append(Stroke(chain, span(chain), weight, loop))
    if not strokes:
        sys.exit("the glow style found no lines of light to trace")
    kept, curves, measures = choose_strokes(strokes, 1 / shrink, keep)
    # A line's colour is taken a little blurred: at its exact centre a glow is nearly white.
    colours = np.asarray(small.filter(ImageFilter.GaussianBlur(3 * max(small.size) / WORK)))
    shades = [np.median(colours[s.points[:, 0].astype(int), s.points[:, 1].astype(int)], axis=0) for s in kept]
    # Two weights and two shades: the heavier strokes, by weight, and the rest.
    order = sorted(range(len(kept)), key=lambda i: -kept[i].weight)
    heavy = set(order[: max(1, round(0.4 * len(kept)))])
    tint = {
        True: to_hex(np.median([shades[i] for i in heavy], axis=0)),
        False: to_hex(np.median([shades[i] for i in order if i not in heavy] or shades, axis=0)),
    }
    # Ranks tell small icons what to keep (see small_size_style). Rank 1 is the subject: the
    # heavy strokes that sit in the middle of the art. Then the other heavy strokes, then the
    # rest in two halves. With nothing heavy in the middle, weight alone decides.
    everything = np.vstack(curves)
    centre = everything.mean(axis=0)
    inner = 0.66 * float(np.percentile(np.hypot(*(everything - centre).T), 97))
    subject = {i for i in heavy if (np.hypot(*(curves[i] - centre).T) <= inner).mean() >= 0.85}
    rest = [i for i in order if i not in heavy]
    rank = {i: 3 + (place >= len(rest) / 2) for place, i in enumerate(rest)}
    rank.update({i: 1 if i in subject or not subject else 2 for i in heavy})
    paths = "".join(
        f'<path class="rank{rank[i]}" d="{bezier_path(curves[i], kept[i].loop)}" stroke="{tint[i in heavy]}" '
        f'stroke-width="{side * (0.009 if i in heavy else 0.005):.1f}"/>'
        for i in range(len(kept))
    )
    body = (
        '<filter id="glow" x="-10%" y="-10%" width="120%" height="120%">'
        f'<feGaussianBlur stdDeviation="{side * 0.01:.1f}"/></filter>'
        f'<defs><g id="strokes" fill="none" stroke-linecap="round" stroke-linejoin="round">{paths}</g></defs>'
        '<use href="#strokes" filter="url(#glow)" opacity="0.7"/><use href="#strokes"/>'
    )
    return body, measures

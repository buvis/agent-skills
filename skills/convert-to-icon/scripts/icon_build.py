"""The icon files: how the art is placed for each platform, and the bundle around them."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from icon_measure import PHOTO_DETAIL, RGB, ROOM, TOLERANCE, bounds, centred, find_plate, fine_detail, from_hex, icon_name, kept_original, measure_art, rasterise, save_sheet, sheet_path, to_hex
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
    window: float = 1.0  # the most of the canvas a platform ever shows, as a share of px
    body: bool = False  # laid out on the macOS grid
    opaque: bool = False  # the platform forbids transparency
    squircle: bool = False  # the platform cuts a rounded square, so a picture can stay full size
    circle: bool = False
    mono: bool = False


@dataclass(frozen=True)
class Look:
    facts: dict
    fill: RGB  # colour behind the art wherever transparency is not allowed
    plate: RGB | None  # set when that fill continues the icon's own flat plate
    picture: bool  # the plate is a gradient or picture: its edge colours are continued instead
    crop: bool  # under a circle cut a picture fills the cut and loses the rest, instead of shrinking


def look_of(svg: Path, facts: dict, override: RGB | None, crop: bool = True) -> Look:
    plate = from_hex(facts["plate"]) if facts["plate"] else None
    declared = re.search(r'data-background="(#[0-9a-fA-F]{6})"', svg.read_text(encoding="utf-8"))
    if override:
        fill = override
    elif plate:
        fill = plate
    elif facts["picture"]:
        fill = from_hex(facts["edge"])
    elif declared:
        fill = from_hex(declared.group(1))
    else:
        # Nothing known: white or near-black, whichever the art uses less of, since a field in
        # the colour of the outlines would swallow them. Failing that, the one that contrasts
        # with the art's main colour.
        used = [(from_hex(colour), share) for colour, share in facts["colours"]] or [((0, 0, 0), 1.0)]
        dark = sum(share for c, share in used if max(c) <= TOLERANCE)
        light = sum(share for c, share in used if min(c) >= 255 - TOLERANCE)
        r, g, b = used[0][0]
        on_white = dark > light if dark != light else 0.299 * r + 0.587 * g + 0.114 * b < 160
        fill = (255, 255, 255) if on_white else (17, 17, 17)
    # An explicit colour means "keep the plate's own shape on this field".
    return Look(facts, fill, plate if fill == plate else None, facts["picture"] and override is None, crop)


def bleed(icon: Image.Image) -> Image.Image:
    """Make an icon opaque by growing its edge colours outward into every see-through pixel.

    Each pass fills the see-through pixels that touch a filled one with the average of those
    neighbours, so a colour travels straight out from the edge it came from. (Averaging the
    picture at coarser and coarser scales instead washes the far band out to a pale haze.)
    Worked out on a small copy, since the fill is smooth anyway, then laid under the icon.
    """
    work = min(icon.width, 256)
    data = np.asarray(icon.resize((work, work), Image.Resampling.BOX)).astype(np.float32)
    rgb, solid = data[..., :3].copy(), data[..., 3] >= 250
    if not solid.any():
        return icon
    # Start a few pixels inside the edge: the outermost rows are often dirty (a screenshot
    # border, JPEG ringing) and one stray row would otherwise be smeared across the whole band.
    rim = 2 * max(2, work // 64) + 1
    core = np.asarray(Image.fromarray(solid.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(rim))) > 0
    known = core if core.any() else solid
    while not known.all():
        ink = np.pad(rgb * known[..., None], ((1, 1), (1, 1), (0, 0)))
        seen = np.pad(known, 1).astype(np.float32)
        total = sum(ink[y : y + work, x : x + work] for y in range(3) for x in range(3))
        count = sum(seen[y : y + work, x : x + work] for y in range(3) for x in range(3))
        grow = ~known & (count > 0)
        rgb[grow] = total[grow] / count[grow][:, None]
        known = known | grow
    under = Image.fromarray(rgb.round().astype(np.uint8)).resize(icon.size, Image.Resampling.BILINEAR)
    return Image.alpha_composite(under.convert("RGBA"), icon)


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
        distance = ImageOps.autocontrast(ImageChops.difference(flat, Image.new("RGB", icon.size, plate)).convert("L"))
        # A soft threshold: shades close to the plate (a gradient's lighter end) drop out,
        # clearly different art turns solid, edges keep a little of their smoothing.
        alpha = distance.point(lambda v: min(255, max(0, (v - 80) * 4)))
    shape = Image.new("RGBA", icon.size, (255, 255, 255, 0))
    shape.putalpha(alpha)
    return shape


def compose(svg: Path, spec: Png, look: Look) -> Image.Image:
    facts = look.facts
    scale = 1.0
    if spec.zone and look.picture:
        # A picture has no glyph to measure. Cropped, it covers all the platform can show and
        # loses what the cut removes. Extended, its box is fitted inside the circle and the
        # band around it is grown from its edge colours. A rounded-square cut needs neither.
        # Either way the measure is the picture's own box, not the canvas it was drawn on:
        # its short side when cropping (cover the cut), its long side otherwise (keep it whole).
        side = facts["extent"] / facts["aspect"] if look.crop else facts["extent"]
        scale = (spec.window if look.crop or spec.squircle else spec.zone) / max(side, 0.01)
    elif spec.zone:  # keep the art inside the circle a launcher may cut
        scale = min(1.0, spec.zone / max(facts["glyph_radius" if look.plate else "radius"], 0.01))
    if spec.body:
        scale = min(1.0, MAC_BODY / facts["extent"])
    shaped = spec.body and (look.plate is not None or look.picture)
    # Cropped onto a layer larger than what a launcher shows, a picture stands alone: the plain
    # background colour lies behind it and nothing is invented around it.
    alone = look.crop and spec.window < 1.0
    continued = look.picture and (shaped or (bool(spec.zone) and not alone))
    backdrop = (*look.fill, 255) if (spec.opaque or shaped) and not continued else (0, 0, 0, 0)
    icon = centred(rasterise(svg, max(1, round(spec.px * scale))), spec.px, backdrop)
    if continued:
        icon = bleed(icon)
    if spec.mono:
        icon = silhouette(icon, look.plate or (look.fill if look.picture else None))
    if spec.circle:
        icon.putalpha(shape_mask(spec.px, 1.0, 0.5))
    if shaped:
        # ponytail: a rounded rectangle stands in for Apple's continuous-corner shape, and there is
        # no drop shadow. Draw the icon in Icon Composer when the difference matters.
        icon.putalpha(shape_mask(spec.px, MAC_BODY, MAC_ROUNDNESS))
    return icon.convert("RGB") if spec.opaque and not spec.circle else icon


def plan_pngs(extra: list[int], themed: bool) -> list[Png]:
    pngs = [
        Png("web/apple-touch-icon.png", 180, zone=0.9, opaque=True, squircle=True),
        Png("web/icon-192.png", 192),
        Png("web/icon-512.png", 512),
        Png("web/icon-mask.png", 512, zone=0.8, opaque=True),
        Png("ios/AppIcon.appiconset/icon-1024.png", 1024, zone=0.9, opaque=True, squircle=True),
        Png("android/play-store-512.png", 512, zone=0.9, opaque=True, squircle=True),
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
            Png(f"{folder}/ic_launcher_foreground.png", layer, zone=66 / 108, window=72 / 108),
        ]
        if themed:
            mono = f"{folder}/ic_launcher_monochrome.png"
            pngs.append(Png(mono, layer, zone=66 / 108, window=72 / 108, mono=True))
    return pngs + [Png(f"png/icon-{px}.png", px) for px in extra]


def companion_texts(fill: RGB, themed: bool) -> dict[str, str]:
    adaptive = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/ic_launcher_background"/>\n'
        '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
        + ('    <monochrome android:drawable="@mipmap/ic_launcher_monochrome"/>\n' if themed else "")
        + "</adaptive-icon>\n"
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


def preview_bundle(bundle: Path, look: Look, themed: bool) -> Path:
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
        ("launcher 48 px", centred(small, 48, grey).resize((cell, cell), Image.Resampling.NEAREST)),
    ]
    if themed:
        panels.insert(4, ("android themed", launcher("ic_launcher_monochrome", (32, 40, 56))))
    sheet = sheet_path(bundle.stem, "preview")
    save_sheet(panels, sheet)
    return sheet


def fit_canvas(master: Path) -> None:
    """Tighten an SVG's canvas to its art: flush for a plate, with a traced master's room otherwise."""
    text = master.read_text(encoding="utf-8")
    root = re.search(r"<svg\b[^>]*>", text)
    box = re.search(r'\bviewBox="([^"]+)"', root.group(0)) if root else None
    if not box or len(view := [float(v) for v in re.split(r"[\s,]+", box.group(1).strip())]) != 4:
        sys.exit(f"{master} has no viewBox to tighten")
    data = np.asarray(rasterise(master, 1024))
    solid = data[..., 3] >= 128
    x0, y0, x1, y1 = bounds(solid)
    unit = view[2] / solid.shape[1]
    side = max(x1 - x0, y1 - y0) * unit * (1.0 if find_plate(data[..., :3], solid)[0] else ROOM)
    left, top = view[0] + (x0 + x1) / 2 * unit - side / 2, view[1] + (y0 + y1) / 2 * unit - side / 2
    # Width and height go: they would pin the old shape onto the new square canvas.
    tag = re.sub(r'\s(?:width|height)="[^"]*"', "", root.group(0).replace(box.group(0), f'viewBox="{left:.2f} {top:.2f} {side:.2f} {side:.2f}"'))
    master.write_text(text.replace(root.group(0), tag, 1), encoding="utf-8")


def build_bundle(svg: Path, bundle: Path, override: RGB | None, extra: list[int], force: bool, crop: bool, fit: bool, move: bool) -> int:
    master = bundle / f"{icon_name(svg)}.icon.svg"
    bundle.mkdir(parents=True, exist_ok=True)
    if svg.resolve() != master.resolve():
        if force or not master.exists():
            shutil.copyfile(svg, master)
        same = master.read_bytes() == svg.read_bytes()
        if move and same:
            svg.unlink()
        elif move:  # the bundle does not hold this drawing: removing it would lose it
            print(f"note: {svg} was left in place; the bundle's master differs from it (--force replaces the master)")
        elif not same and not fit:
            print(f"note: {master} differs from {svg}; the bundle's copy was used (--force replaces it)")
    if fit:
        fit_canvas(master)
    look = look_of(master, measure_art(rasterise(master, 1024)), override, crop)
    created: list[str] = []

    def missing(rel: str) -> Path | None:
        path = bundle / rel
        if path.exists() and not force:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        created.append(rel)
        return path

    # A photo has no clean outline: its themed layer would be specks, so Android gets none
    # and falls back to the normal icon. Judged on the original where one was kept, because
    # tracing smooths a photo's detail away.
    original = kept_original(master)
    themed = fine_detail(Image.open(original) if original else rasterise(master, 1024)) <= PHOTO_DETAIL
    pngs = plan_pngs(extra, themed)
    for spec in pngs:
        if path := missing(spec.path):
            compose(master, spec, look).save(path)
    for rel, sizes in ICOS.items():
        if path := missing(rel):
            frames = [compose(master, Png(rel, px), look) for px in sizes]
            frames[-1].save(path, sizes=[(px, px) for px in sizes], append_images=frames[:-1])
    if path := missing("macos/AppIcon.icns"):
        write_icns(bundle / ICONSET, path)
    texts = companion_texts(look.fill, themed)
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
    if not themed:
        print("themed icon left out: a photo has no clean outline, so Android falls back to the normal icon")
    for problem in problems:
        print(f"problem: {problem}")
    if problems:
        print(f"icon set INCOMPLETE: {len(problems)} problems")
        return 1
    print(f"preview: {preview_bundle(bundle, look, themed)}")
    print(f"icon set complete: {len(expected)} files")
    return 0

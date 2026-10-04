# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["numpy", "pillow>=10.1", "potracer", "resvg-py", "scikit-image", "scipy", "vtracer"]
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
import json
import re
import sys
from pathlib import Path

from PIL import Image

from icon_measure import bundle_for, from_hex, icon_name, kept_original, measure_art, rasterise
from icon_trace import TraceOptions, trace_raster
from icon_build import build_bundle
from icon_review import review_svg


def existing_file(text: str) -> Path:
    path = Path(text).expanduser()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"no such file: {text}")
    return path


def pixel_size(text: str) -> int:
    if not text.isdigit() or not 1 <= int(text) <= 4096:
        raise argparse.ArgumentTypeError(f"expected a size from 1 to 4096 px, got {text!r}")
    return int(text)


def weight_share(text: str) -> float:
    try:
        share = float(text)
    except ValueError:
        share = 0.0
    if not 0.3 <= share <= 1.0:
        raise argparse.ArgumentTypeError(f"expected a share from 0.3 to 1.0, got {text!r}")
    return share


def plain_name(text: str) -> str:
    if not re.fullmatch(r"[\w-]+(\.[\w-]+)*", text):
        raise argparse.ArgumentTypeError(f"expected a plain name like my-app, got {text!r}")
    return text


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
    tracer.add_argument("--detail", choices=("normal", "fine"), default="normal")
    tracer.add_argument("--style", choices=("auto", "glow", "layers"), default="auto")
    tracer.add_argument("--keep", type=weight_share)
    reviewer = commands.add_parser("review")
    reviewer.add_argument("svg", type=existing_file)
    reviewer.add_argument("--source", type=existing_file)
    builder = commands.add_parser("build")
    builder.add_argument("svg", type=existing_file)
    builder.add_argument("--png", type=pixel_size, action="append", default=[])
    builder.add_argument("--picture", choices=("crop", "extend"), default="crop")
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
        options = TraceOptions(
            remove=args.background == "remove",
            enclosed=args.enclosed,
            colours=args.colors,
            fine=args.detail == "fine",
            style=args.style,
            keep=args.keep,
        )
        print(json.dumps(trace_raster(args.raster, svg, options), indent=2))
        return 0
    bundle = bundle_for(args.svg, args.out)
    if args.command == "review":
        source = args.source or kept_original(args.svg)
        print(json.dumps(review_svg(args.svg, source, args.background), indent=2))
        return 0
    return build_bundle(args.svg, bundle, args.background, args.png, args.force, args.picture == "crop")


if __name__ == "__main__":
    sys.exit(main())

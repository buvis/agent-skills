---
name: convert-to-icon
description: Use when turning an image or SVG into icons - favicon, .ico, .icns, iOS and Android app icons - or a raster logo into SVG (provide the image path). Triggers on "convert to icon", "make icons", "favicon", "app icon", "icns", "vectorize logo".
compatibility: "Portable; needs uv on PATH and network on the first run, when uv fetches the script's Python packages. iconutil (macOS) writes the full .icns; elsewhere Pillow writes one without the 16 and 32 px 1x entries."
argument-hint: "<path/to/image-or-svg> [name]"
---

# Convert to icon

Turn one image into a bundle of platform icons. A raster source is traced to
a master SVG first; every icon is then drawn from that SVG. Pointed at an
SVG, the skill writes whatever the bundle is missing.

The bundle is `<name>.icons/` beside the source: `<name>.icon.svg`, a copy
of a raster source under its own file name, and `web/`, `windows/`,
`macos/`, `ios/`, `android/`. The two check sheets go to the temp folder,
never into the bundle; each command prints where. What each file is for, where it goes, the HTML tags and what is
deliberately not generated: `references/icon-set.md`.

## Dependencies

- `uv` on PATH: hard failure without it. The script declares its own Python
  packages and uv fetches them on the first run, which needs network.
- `iconutil` (macOS, optional): absent, Pillow writes the `.icns` without the
  16 and 32 px 1x entries.

## Inputs

1. Take the image path from the user's message. If there is none, ask for it
   and wait. Check the file exists.
2. Name: the user's wording, else the file stem (`logo.icon.jpg` gives
   `logo`).

## Workflow

An icon carries what a picture means, not its detail. Before tracing, say in
one sentence what the image depicts: its subject and what surrounds it (for
example "a letter B inside a sphere of orbiting light"). Judge every draft
against that sentence, not against the pixels: the subject must read at
once, what surrounds it must still be there, and nothing else needs to
survive. A faithful copy of a busy picture is a failed icon.

Add `--out DIR` to any step to put the bundle somewhere else.

### 1. Inspect

```bash
uv run ~/.agents/skills/convert-to-icon/scripts/convert_to_icon.py inspect IMAGE
```

An SVG input skips to step 3.

### 2. Trace (raster only)

`background` in the inspect output decides the question to ask:

- a colour (`"#ffffff"`): a uniform page sits behind the art. Ask the user
  whether the icon is meant to be transparent. Never guess. Yes is `remove`,
  no is `keep` (the colour is part of the icon).
- `null` or `"transparent"`: the art runs to the edge, or the image is
  already see-through. Nothing to ask; use `keep`.

```bash
uv run ~/.agents/skills/convert-to-icon/scripts/convert_to_icon.py trace IMAGE --name NAME --background remove
```

The trace picks a style and reports it as `style`:

- `flat`: one or two flat colours, traced as clean shapes.
- `glow`: soft, luminous art on a uniform page (neon, light trails, a logo
  with a halo). It becomes a line drawing: the ridges of light are joined
  into long stroked curves over the plain page colour, and the fade is one
  blur of those strokes. Nothing is filled. Never let a glow be traced as it
  looks: that paints areas and stacks bands. Only as many strokes are kept
  as stay easy on the eye; the output's `pleasing` block gives the measures.
  Icons under 128 px draw it bolder and with fewer lines, down to the
  subject alone under 48 px, or hairlines would vanish.
- `layers`: everything else, one layer per colour.

A source that inspect marks `photo: true` is traced all the same: expect a
posterised look, an SVG of megabytes, a `DOUBT` at review and no Android
themed layer (40 files instead of 45), and tell the user so before going on.

Overrides, for when the review shows the default was wrong:

- `--style glow|layers`: the other treatment for art with more than two
  colours. `glow` needs a uniform page behind the art.
- `--keep 0.6`: for the `glow` style, the share of the drawing's weight to
  keep (0.3 to 1.0) instead of letting the measures choose. Lower when the
  draft is still as busy as a traced picture, higher when the subject or
  what surrounds it has gone.
- `--colors N`: `colours` in the inspect output miscounts what you see.
- `--detail fine`: for the `layers` style only. Shading that came out flat
  or banded gets more colour steps, a closer match and about twice the file
  size. The review names it when it would help.
- `--enclosed keep|clear`: page-coloured areas fully surrounded by art. `keep`
  draws them (a white glyph on a plate), `clear` makes them see-through (the
  gaps in line art).
- `--force`: replace an SVG that already exists.

### 3. Review, before anything is built

```bash
uv run ~/.agents/skills/convert-to-icon/scripts/convert_to_icon.py review SVG --source IMAGE
```

`--source` can be left out: the review compares against the original kept in
the bundle, and an SVG input, which has none, is judged on its own. The
command prints `PASS` or `DOUBT` with reasons, and the path of a review
sheet as `sheet`. Read that image. Panels, left to right: source, SVG on
white, SVG on magenta, circle cut (two for a picture: cropped, extended),
32 px. Look for:

- meaning: the subject no longer reads, or what surrounds it has gone
- detail: as busy as the source, or so bare it says nothing; stray arcs
  that end in mid-air, wobbly curves, dirt (retrace with `--keep`)
- resemblance: a shape, colour or proportion that differs from the source
- soft light drawn as stacked bands, blobs or painted areas (retrace with
  `--style glow`)
- overcut: magenta where art should be, or art cut off at the canvas edge
- leftover page: a halo, or page-coloured patches that should be see-through
- holes that should be filled (a glyph that vanished from its plate)
- corners rounded twice, or a plate that is already rounded
- art lost in an empty canvas, or a wide wordmark squeezed into a thin strip
- anything that matters falling outside the circle
- a 32 px panel nobody could read

Build only when the verdict is `PASS` and you see none of these. On `DOUBT`,
or on anything you are unsure of, do not build: give the user the path to
the sheet, name each doubt in plain words, and ask which fix to apply:

- a trace that looks wrong: retrace with another `--enclosed`, `--colors` or
  background answer, then review again
- a photo: accept the posterised trace, or stop and ask for flat artwork;
  no setting makes a photo trace cleanly
- a line drawing "hard on the eye": the doubt names the limit it breaks;
  retrace with another `--keep`, and show the user two levels side by side
  when no level meets every limit
- a pre-rounded flat plate: extend its colour to the corners, or keep its
  shape on another colour
- a picture plate (a gradient or scene filling a square): crop it, extend
  it, or keep its shape on a flat field. The sheet shows crop and extend
  side by side; say what each one loses.

With nobody to ask, stop and report the doubts.

### 4. Build

```bash
uv run ~/.agents/skills/convert-to-icon/scripts/convert_to_icon.py build SVG
```

Existing files are kept; only missing ones are written. Options:

- `--background "#rrggbb"`: the fill wherever a platform forbids
  transparency. Default: the plate colour, else the page colour that was
  removed, else white or near-black, whichever the art uses less of.
  A pre-rounded plate is extended to the corners by default; another colour
  here keeps its shape on a field of that colour instead.
- `--picture crop|extend`: how a picture plate meets a circle cut. `crop`
  (default) fills the cut with the picture, sharp, and loses what falls
  outside; nothing is invented. `extend` keeps the whole picture, smaller,
  inside a soft band grown from its edge colours.
- `--png 300`: an extra plain PNG of that size, repeatable.
- `--force`: rewrite everything. Use it only when the user wants files
  replaced; a `stale:` line says some are older than the master SVG.

The run ends with `icon set complete: N files`, or `icon set INCOMPLETE`
plus one `problem:` line each and exit 1. Then read the sheet named on the
`preview:` line (iOS masked, maskable circle, macOS, Android adaptive,
Android themed, 48 px launcher) with the same eye as step 3. A doubt there
goes to the user too.

### 5. Report

Paste the verdict and the `icon set complete` line as printed. Add the bundle
path, the fill colour, each decision taken (background, enclosed areas,
plate, crop or extend) and anything skipped. Without that line the work is incomplete: say
so and paste the `problem:` lines.

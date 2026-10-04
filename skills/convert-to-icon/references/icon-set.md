# The icon set

What `build` writes into `<name>.icons/`, why, and where each part goes.
Researched 2026-10. Apple's own guideline pages could not be fetched, so the
macOS and iOS rows rest on secondary sources (listed at the end).

## Files

| Path in the bundle | Size (px) | Transparency | Goes to |
|---|---|---|---|
| `<name>.icon.svg` | vector | as drawn | the master; keep it |
| the source raster, under its own file name | as given | as given | what the master was traced from; absent for an SVG input. The SVG names it in `data-source`, which is how the review finds it. |
| `web/favicon.ico` | 16, 32, 48 | yes | site root |
| `web/icon.svg` | vector | yes | site root |
| `web/apple-touch-icon.png` | 180 | no | site root |
| `web/icon-192.png`, `web/icon-512.png` | 192, 512 | yes | site root, named in the manifest |
| `web/icon-mask.png` | 512 | no | site root, `purpose: maskable` |
| `web/manifest.webmanifest` | - | - | merge its `icons` into the site's manifest |
| `windows/app.ico` | 16, 20, 24, 32, 40, 48, 64, 256 | yes | the Windows executable or installer |
| `macos/AppIcon.icns` | 16 to 1024 | yes | the app bundle's `Resources/` |
| `macos/AppIcon.iconset/` | 16, 32, 128, 256, 512, each at 1x and 2x | yes | source of the `.icns`; an Xcode asset catalog also takes it |
| `ios/AppIcon.appiconset/` | 1024 + `Contents.json` | no | `Assets.xcassets/` |
| `android/res/mipmap-*/ic_launcher.png` | 48, 72, 96, 144, 192 | yes | `app/src/main/res/` |
| `android/res/mipmap-*/ic_launcher_round.png` | same | circle | same |
| `android/res/mipmap-*/ic_launcher_foreground.png` | 108, 162, 216, 324, 432 | yes | same |
| `android/res/mipmap-*/ic_launcher_monochrome.png` | same | yes | same |
| `android/res/mipmap-anydpi-v26/ic_launcher.xml`, `ic_launcher_round.xml` | - | - | same |
| `android/res/values/ic_launcher_background.xml` | - | - | same; holds the fill colour |
| `android/play-store-512.png` | 512 | no | the Play Console listing |
| `png/icon-N.png` | N | yes | only with `--png N` |

The review and preview sheets are not part of the bundle. They are written to
the system temp folder under `convert-to-icon/` and each command prints the
path.

Web page head:

```html
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest">
```

Android manifest: `android:icon="@mipmap/ic_launcher"` and
`android:roundIcon="@mipmap/ic_launcher_round"`.

## How the art is placed

- A plain file (favicon, `.ico`, `icon-192`, `icon-512`, legacy
  `ic_launcher.png`) is the master as drawn.
- A non-square master is padded to a square. Nothing is ever stretched.
- Where a platform forbids transparency, the canvas is filled first. The fill
  is `--background`, else the icon's plate colour, else the page colour
  removed during tracing, else black or white by contrast.
- Where a platform cuts its own shape, the art is shrunk until its farthest
  pixel sits inside a centred circle: 90% of the canvas for iOS, the Apple
  touch icon, the Play Store icon and the round launcher; 80% for the
  maskable icon; 66 of 108 dp for the Android adaptive layers. It is never
  enlarged.
- A plate is a block the art sits on: a square (it covers at least 85% of
  its own box, as a rounded square does) or a disc (it matches the ellipse of
  its box). A single colour with nothing on it is not a plate; it is the art.
- A flat plate is one colour carrying a glyph. When the fill is that colour,
  the plate runs to the corners and the platform does the only rounding; the
  circle rule then measures the glyph, not the plate.
- A picture is a plate that is not one flat colour: a gradient, a photo, a
  scene. It has no glyph to measure, and it is sized by its own box, not by
  the canvas it was drawn on. Under a rounded-square cut (iOS, Apple touch
  icon, Play Store) it keeps its full size. Under a circle cut there are two
  treatments, chosen with `--picture`:
  - `crop` (default): the picture fills everything the platform can show,
    covering it by its short side when it is not square, and the cut removes
    its corners and whatever else falls outside. Nothing is invented. On the Android adaptive layer, which is half again as large as
    what a launcher shows, the picture stands alone at 72 of 108 dp over the
    plain background colour; a sliver of that colour can show during launcher
    motion effects.
  - `extend`: the whole picture is kept, fitted inside the circle, and the
    band around it is grown outward from its edge colours. The growth starts
    a few pixels inside the edge, so a stray border row is not smeared across
    the band. The band is synthesized: seamless for a gradient, a soft
    trailing streak where the subject runs off the picture's edge.
  The picture's own rounded corners are filled by the same growth in both
  treatments; they are small and mostly cut away. `--background` with a
  colour skips all of this and keeps the picture's shape on a flat field.
- A round picture on a rounded-square platform has large corners to fill, all
  of them synthesized. `--background` is usually the better answer there.
- macOS: the art's box is fitted to the 824 px body of the 1024 px grid. A
  plate is cut to a rounded rectangle of that body; other art stays as drawn.
- Android themed icon: the art's outline in white. On a plate or picture it
  is whatever differs clearly from the plate's edge colour, so a
  many-coloured subject comes out uneven. Draw that layer by hand when it
  matters.

## Photos

A photo is detected by its fine detail: the share of pixels that step sharply
away from a neighbour is about 0.05 in flat art and 0.3 in a photo, and the
line is drawn at 0.2. It is traced like anything else, because the master
must be an SVG. The result is a posterised approximation of several
megabytes, and no tracer setting changes that: a photo has no flat shapes to
find. The review says so and leaves the decision to the user. Flat artwork is
the real fix.

A photo also has no clean outline, so its Android themed layer would be
scattered specks. The build leaves that layer out (no
`ic_launcher_monochrome.png`, no `<monochrome>` in the adaptive XML, 40 files
instead of 45) and Android shows the normal icon in themed mode.

## Not generated, on purpose

- iOS dark and tinted variants: optional since iOS 18, and iOS derives its
  own when they are missing.
- Icon Composer `.icon` bundles (macOS 26, iOS 26 layered look): the format
  is undocumented and needs Xcode. The `.icns` still works everywhere.
- Apple's exact continuous-corner shape and drop shadow on macOS: a rounded
  rectangle stands in.
- Windows MSIX and Store tile assets, watchOS, visionOS.
- Android VectorDrawable layers: the converters drop gradients, masks and
  transforms. PNG layers per density are allowed and are what ships here.
- Obsolete web files: `mstile-*`, `browserconfig.xml`, Safari `mask-icon`,
  per-size PNG favicons, the per-size iOS icon matrix.
- SVG optimisation.

## Sources

- Evil Martians, "How to Favicon" (revised 2024-09): the web set and tags.
- Microsoft Learn, "Construct your Windows app's icon" (2026-07): `.ico` sizes.
- developer.android.com, "Adaptive icons": layer sizes, safe zone, themed icons.
- Google Play Console help: the 512 px listing icon.
- `iconutil` man page: `.iconset` file names.
- Secondary, for Apple: mjtsai.com (2025-10) and praeclarum.org (2025-09) on
  macOS 26 icon margins and Icon Composer; Apple developer forum thread
  761615 on the single-size `Contents.json`.

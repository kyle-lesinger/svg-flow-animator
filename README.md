# svg-flow-animator

Build animated diagram GIFs by generating SVG frames.

Describe a diagram once as coordinates, emit one standalone SVG per frame,
rasterise with librsvg, assemble with ffmpeg. The output drops straight into
Google Slides, Keynote, or a README and animates on its own.

Zero Python dependencies — stdlib only.

![example](docs/example.gif)

Same diagram, same code, `--style=sketch`:

![example, hand-drawn](docs/example-sketch.gif)

## Why frames instead of SMIL/CSS

Animated SVG is smaller and sharper, and it is also useless in the places these
diagrams actually get shown. Google Slides, Keynote, PowerPoint and GitHub
READMEs will not run SMIL or CSS animation. A GIF plays everywhere with no
plugin, no embed, and no upload step.

Generating discrete frames also means every frame is a real file you can open,
diff, and eyeball — which matters a lot when something renders wrong at frame
417 and nowhere else.

## Install

```bash
git clone https://github.com/kyle-lesinger/svg-flow-animator
cd svg-flow-animator
```

Two external binaries:

```bash
brew install librsvg ffmpeg     # rsvg-convert, ffmpeg
```

## The pieces

| Module | What it does |
| --- | --- |
| `assets` | Recovers artwork from a flattened design-tool export — embedded base64 rasters, and vector marks identified by fill colour |
| `geometry` | Polyline maths, easing, and collision-aware label placement |
| `svg` | Element emitters. String-based; frames are write-once |
| `timeline` | `Stage` objects, flow connectors, pulses, auto-placed callouts |
| `render` | Parallel rasterisation and GIF assembly |
| `styles` | `FLAT` and `SKETCH` drawing backends behind one interface |
| `rough` | Excalidraw-style sketchy geometry (a port of roughjs) |

## Quick shape

```python
from svg_flow_animator import assets, render, svg, timeline

# 1. recover the real artwork instead of screenshotting a render
found = assets.extract_rasters("diagram-export.svg", "assets/")

# 2. describe the beats. `anchor` is what the caption is ABOUT --
#    where it gets drawn is derived from that.
stages = [
    timeline.Stage("sources", start=8,   dur=60, anchor=(150, 450),
                   text="Data arrives from many locations..."),
    timeline.Stage("ingest",  start=132, dur=30, anchor=(419, 450),
                   text="Every source converges on one ingest UI."),
]

# 3. emit frames
for f in range(TOTAL):
    body = static_scene()
    for st in stages:
        p = st.progress(f)
        if p >= 0:
            body += timeline.flow(PATH, p, f * 7.0, "#008a0e", "#ff7a00")
        body += timeline.callout(st, st.alpha(f), OBSTACLES, (1600, 900))
    open(f"frames/f{f:04d}.svg", "w").write(svg.document(1600, 900, body, "#fff"))

# 4. render and assemble
render.stage_assets("assets/", "frames/")
render.render_frames("frames/", 1600, 900)
render.build_gif("frames/", "out.gif", fps=15, width=1280, height=720)
```

See `examples/disasters_ingest/` for a complete, working diagram.

## Hand-drawn mode

`styles.SKETCH` renders the same scene in an Excalidraw-like hand-drawn style:
roughjs-style double strokes, hachure fills, and a handwriting face. Draw
through `S.box`/`S.text`/`S.poly` instead of the raw emitters and both styles
come for free.

```python
from svg_flow_animator import styles
S = styles.select()                  # --style=sketch, or FLOWGIF_STYLE=sketch
body = S.box(40, 100, 300, 360, "#f6f4e8", stroke="#46525e", rx=10)
```

**It costs almost nothing.** Sketch geometry is ~6x the SVG bytes but only
**+3%** on the final GIF, because the extra ink is identical in every frame and
inter-frame compression absorbs it.

**The one thing you must get right is determinism.** Seed the jitter from each
shape's *identity*, never from the frame number, and give every shape its own
PRNG. A shared random stream re-jitters everything downstream the moment a flow
appears or disappears, and the whole diagram visibly boils. `rough.seed_for()`
uses `zlib.crc32`, not `hash()` — `hash()` is salted per process, so it would
give you different artwork on every run.

Fonts: Excalidraw's own face is Excalifont (SIL OFL). If it is not installed the
stack falls back through Noteworthy and Chalkboard SE. End the stack with
`sans-serif`, **not** `cursive` — on macOS `cursive` resolves to Zapfino.

## Things that will bite you

These are the non-obvious ones, all handled by the library but worth knowing.

**librsvg will not load images outside the document's own directory.** A frame
in `frames/` cannot reference `../assets/logo.png`. It fails *silently* — the
image simply does not draw, no warning, no error, exit code 0. `stage_assets()`
mirrors your sprite directory below the frame directory so hrefs resolve.

**librsvg's filter support is poor.** `feGaussianBlur` will not give you a glow.
Stack a few concentric strokes at decreasing opacity instead — `svg.glow()`
does this.

**`preserveAspectRatio="meet"` shrinks things you expected to fill.** A 1.4:1
logo in a 188×74 slot gets pinned to 104×74 by height, not width. If you want
several differently-shaped images to fill equal frames uniformly, use `slice`.

**Colour-keying a background can eat your whites.** Knocking out `#fbf0ff` at
8% fuzz also removes white, because they differ by only 5.9%. Keep the fuzz
below the distance between the background and the lightest colour you care about.

**Hold frames are nearly free.** Consecutive identical frames collapse under the
GIF inter-frame delta, so generous pauses cost almost nothing. Motion is what
costs bytes.

**Don't paint flow dashes before the reveal finishes.** Packets appearing on
track the head has not reached yet is the tell that the motion is faked.
`timeline.flow()` sequences the two phases for you.

## Design notes

**Callouts place themselves.** Hand-picking a slot per caption looks fine until
the layout moves. `geometry.place_near()` sweeps for the nearest position to the
subject that collides with nothing, and the tail leaves from whichever edge
actually faces it. A stage declares *what it is about*; where the bubble goes is
derived.

**Extract artwork, don't screenshot it.** Design-tool exports hide real assets
in `<defs>` as base64. `assets.extract_rasters()` gets them back byte-exact at
native resolution, which beats cropping a render every time. For vector marks,
`extract_paths_by_fill()` finds them by brand colour so they stay vector and can
be rotated.

**ffmpeg over ImageMagick for the GIF.** `palettegen` with `stats_mode=diff`
weights the palette toward pixels that actually change between frames — for a
mostly-static diagram that spends the colour budget where it shows.

## License

MIT

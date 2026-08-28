# Project Guide

Build animated diagram GIFs by generating one SVG per frame, rasterising with
librsvg, assembling with ffmpeg. Plus a browser editor for nudging geometry by
hand.

## Stack

Python **stdlib only** — no Pillow, no numpy, no lxml. Two external binaries:

```bash
brew install librsvg ffmpeg     # rsvg-convert, ffmpeg
```

Keeping the package dependency-free is deliberate (see `docs/DECISIONS.md`).
Do not add a Python dependency without a reason that survives that argument —
image work shells out to ImageMagick/ffmpeg, and PNG/JPEG dimensions are parsed
from file headers.

## Layout

```
svg_flow_animator/     the reusable package
  assets.py            recover artwork from a flattened SVG export
  geometry.py          polylines, easing, collision-aware placement
  svg.py               element emitters
  styles.py            FLAT / SKETCH backends behind one interface
  rough.py             roughjs port (Excalidraw-style geometry)
  timeline.py          Stage, flows, pulses, auto-placed callouts
  overrides.py         hand-tunable geometry + handle registry
  editor.py            generates a browser editor from that registry
  render.py            parallel rasterisation, GIF assembly
examples/minimal/      self-contained demo, no external artwork
examples/disasters_ingest/   the real diagram this was built for
docs/                  ARCHITECTURE, DECISIONS, GOTCHAS
```

## Run / verify

```bash
python3 -c "import svg_flow_animator"                # imports clean
python3 examples/minimal/demo.py                     # full pipeline, ~360 frames
python3 examples/minimal/demo.py --style=sketch      # hand-drawn variant
python3 -m compileall svg_flow_animator examples     # syntax
```

The minimal demo is the smoke test: it exercises geometry, styles, timeline and
render end to end, and needs no artwork.

For generated JavaScript (the editor), **always** run `node --check` on the
extracted `<script>` before considering it working. A template escaping bug once
shipped a completely broken script with no Python-side error.

In the disasters example:

```bash
./edit.sh              # launch editor (flat)
./edit.sh sketch       # hand-drawn
./build.sh             # -> the GIF
FLOWGIF_STYLE=sketch ./build.sh
```

## Critical constraints

**Read `docs/GOTCHAS.md` before touching the render or editor paths.** Every
entry is a silent failure that shipped once. The three that recur:

1. **librsvg only loads resources at or below the SVG's own directory**, and
   fails silently. Anything rendering an SVG that references sprites must write
   it inside the project tree, and sprites must be staged below the frame dir.
2. **`fill="transparent"` captures pointer events**; `fill="none"` does not.
3. **Sketchy geometry must be seeded from shape identity with a fresh PRNG per
   shape**, or the diagram visibly boils across frames.

## Patterns

- **Never hardcode a coordinate you might want to tune.** Route it through
  `overrides.point/rect/path/scalar/offset`. That registers a handle, and the
  editor is built from the registry — one call makes a thing draggable.
- **Labels use `offset`, not `point`.** Absolute label positions detach from
  their object the first time they are nudged.
- **A stage declares its subject, not its caption position.** Placement is
  searched for at render time.
- **Assert on plausibility, not just exit status.** These failures produce valid
  files that are wrong; where a cheap invariant exists, check it.
- **Point guards at an artefact that actually contains what they check.** A
  check against frame 0 sees no animation and passes forever.

## Repo conventions

- `main` is protected: no direct pushes, no force pushes. Work on a branch, open
  a PR. Push over **SSH** (`git@github.com:...`), not HTTPS.
- **No AI attribution in commits or PRs** — no `Co-Authored-By`, no "Generated
  with", no robot emoji. The human is the sole author.
- `examples/disasters_ingest/assets/` is gitignored — third-party logos and
  screenshots are not ours to redistribute. So is its `editor.html`, whose
  backdrop embeds the same artwork as a base64 PNG.

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
edit.sh                launcher; dispatches to an example's own edit.sh
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
docs/                  ARCHITECTURE, DECISIONS, GOTCHAS, ASSETS
```

Every module in `svg_flow_animator/` is a **library module** — none is runnable.
`python3 svg_flow_animator/editor.py` fails with `attempted relative import with
no known parent package`; that is expected, not a bug. Editors are produced by
an example calling `editor.build(...)`.

## Run / verify

```bash
python3 tests/run.py                                 # 247 tests, <1s
python3 examples/minimal/demo.py                     # full pipeline, ~360 frames
python3 examples/minimal/demo.py --style=sketch      # hand-drawn variant
python3 -m compileall svg_flow_animator examples     # syntax
```

`tests/` is stdlib `unittest` — no pytest. Tests needing `rsvg-convert`,
`ffmpeg`, `magick`, `node` or the gitignored `assets/` **skip** rather than
fail, so the suite is green on a bare clone. Many tests encode a specific
`docs/GOTCHAS.md` entry and say which one when they fail.

The minimal demo is the smoke test: it exercises geometry, styles, timeline and
render end to end, and needs no artwork.

For generated JavaScript (the editor), **always** run `node --check` on the
extracted `<script>` before considering it working. A template escaping bug once
shipped a completely broken script with no Python-side error.
`examples/minimal/edit.sh` does this on every build.

Launching an editor, from the repo root:

```bash
./edit.sh                    # minimal demo; self-contained, needs no artwork
./edit.sh disasters          # the disasters diagram (flat)
./edit.sh disasters sketch   # hand-drawn
./edit.sh disasters --stop   # stop its preview server
```

Each example also has its own `edit.sh`; the root one only dispatches. The
disasters example additionally has `./build.sh` (`FLOWGIF_STYLE=sketch` for the
hand-drawn GIF), and **will not run until `assets/` is rebuilt** — see
`docs/ASSETS.md`.

That build also emits one GIF per chapter, plus a still of the whole thing:

```bash
./build.sh --list-sections     # what is buildable, and what each animates
./build.sh --section=egis      # -> sections/egis.gif
./build.sh --all-sections
./build.sh --poster            # -> sections/ecosystem.png, 3200x1800
```

**Sketch is the default style** here; `FLOWGIF_STYLE=flat` gets the clean
render. The filename suffix applies to whatever is *not* the default, so
`egis.gif` is the sketch one and `egis-flat.gif` is the other.

Every section shows the **whole canvas** — it is not a crop. Sections differ by
what MOVES (`SECTION_SCOPE`) and which frames they cover (`section_span`). See
`docs/ARCHITECTURE.md`.

## Critical constraints

**Read `docs/GOTCHAS.md` before touching the render or editor paths.** Every
entry is a silent failure that shipped once. The three that recur:

1. **librsvg only loads resources at or below the SVG's own directory**, and
   fails silently. Anything rendering an SVG that references sprites must write
   it inside the project tree, and sprites must be staged below the frame dir.
   Staging is `stage_assets()`, and **only `main()` calls it** — any other entry
   point renders a complete-looking scene with every logo missing.
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

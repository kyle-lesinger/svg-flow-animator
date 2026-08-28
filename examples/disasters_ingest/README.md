# Example: NASA Disasters ingest-flow animation

Everything needed to regenerate and re-tune the animated architecture diagram —
**except the artwork**. `assets/` is gitignored and absent on a fresh clone, so
nothing here runs until you rebuild it from the original export. See
"Artwork is not included" below, and `docs/ASSETS.md` for the procedure.

## Build

    ./build.sh                        # -> disasters-data-flow.gif
    FLOWGIF_STYLE=sketch ./build.sh   # -> disasters-data-flow-sketch.gif

Needs `rsvg-convert` and `ffmpeg` on PATH. No Python packages.

### One GIF per section

    ./build.sh --list-sections        # what is buildable
    ./build.sh --section=egis         # -> sections/egis.gif
    ./build.sh --all-sections         # -> sections/*.gif

A section is one labelled box, cropped to the output's aspect ratio and rendered
from the **same timeline** as the full GIF, so the two can never disagree. The
list is derived from the handle registry — adding an `ov.rect("box.*", ...)`
makes a new section buildable with no change to `build.sh`.

Exactly one GIF is kept per section; a rebuild replaces it. Size tracks how much
motion falls inside the crop, not the zoom factor: a quiet section is ~0.25 MB
while the most magnified one is ~6 MB. Note that `integration` and `portal` are
550x640 boxes, which fitted to 16:9 fill almost the whole canvas — those two are
near-copies of the full GIF rather than close-ups.

## Move things by hand

One command:

    ./edit.sh              # flat render
    ./edit.sh sketch       # hand-drawn render

It rebuilds the editor if the layout has moved, starts the preview server if it
is not already up, checks the renderer actually answers, and opens the browser.
Safe to run repeatedly — a second run reuses the running server in under a
second.

    ./edit.sh --stop       # stop the server
    ./edit.sh --restart    # force fresh server + rebuilt backdrops

In the editor: drag a handle and the real diagram re-renders behind it after a
moment. **Save to project** writes `overrides.json` here. Then build:

    ./build.sh                        -> disasters-data-flow.gif
    FLOWGIF_STYLE=sketch ./build.sh   -> disasters-data-flow-sketch.gif

### What you can move

  * blue dot — a node
  * **green dot** — a label, independently of its icon
  * orange dot — a connector vertex
  * dashed box — grab it by the **border**; the corner square resizes it
  * **double-click an orange line to add a bend point** — this is how you change
    a line's angle. Right-click a bend point to delete it.
  * icon sizes and the arc shape are numeric fields in the side panel
  * shift-drag snaps to 5px, Cmd-Z / Cmd-Shift-Z undo and redo

The layer buttons at the top hide categories. Turn off **nodes** to reach
connector vertices underneath — nine handles stack on the ingest hub, since
every spoke ends there.

Both renders share one geometry, so a saved `overrides.json` applies to both
whichever you were looking at.

`overrides.json` stores only what differs from the defaults. Delete a key to
revert one thing; delete the file to revert everything.

### If you open editor.html directly

It still works for laying things out, but **Refresh** and **Save** are disabled
— there is no renderer to talk to over `file://`, and the page says so. Use
`./edit.sh`.

## What the diagram asserts

The connector directions are **claims about the real architecture**, not visual
choices, so they are not interchangeable. Getting one backwards makes the
diagram say something untrue.

| block | main flow | minor flow |
| --- | --- | --- |
| Earthdata GIS | tools -> STAC | STAC -> tools |
| Data Processing | block -> STAC | STAC -> block |
| Portal Content | STAC -> Portal | **none — one way** |

- **Main is dominant, minor is subordinate.** The minor return flow must be
  visually lighter and must not compete with the main direction for attention.
- **Earthdata GIS is a chain**: NOAA / FEMA / Census -> a junction -> ArcGIS
  Desktop, ArcGIS Online, Service Workflows -> STAC. The three agency seals are
  **sources only**; no flow from STAC may ever terminate on one. Both STAC-side
  connectors attach to the three tools.
- **TinaCMS is one-way.** Portal Content has no return path to STAC — that
  integration does not exist yet. Do not add one for symmetry.

## Files

    edit.sh           launch the editor (start here)
    serve.py          live-preview server behind it
    layout.py         all coordinates -- the thing to edit by hand
    overrides.py      the tunable-geometry layer + handle registry
    editor.py         generates the browser editor
    gen_frames.py     draws one SVG per frame
    style.py          flat vs sketch drawing backends
    rough.py          Excalidraw-style sketchy geometry (roughjs port)
    extract_assets.py re-extract artwork from a source SVG export
    build.sh          the whole pipeline

The reusable engine is at https://github.com/kyle-lesinger/svg-flow-animator

## Artwork is not included

`assets/` is gitignored: the logos and site screenshots belong to NASA, Esri and
others and are not ours to redistribute. Run `extract_assets.py` against your
own source SVG export to populate it, then everything else works.

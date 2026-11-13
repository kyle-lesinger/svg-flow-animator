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
    ./build.sh --section=intro        # -> sections/intro.gif, the opening
    ./build.sh --section=journey      # -> sections/journey.gif, problem and fix
    ./build.sh --section=bottleneck   # -> sections/bottleneck.gif, the bottleneck solved
    ./build.sh --section=story        # -> sections/story.gif, the two combined, 45 s
    ./build.sh --section=uses         # -> sections/uses.gif, data to every audience
    ./build.sh --section=response     # -> sections/response.gif, the whole network, 15 s
    ./build.sh --section=infra        # -> sections/infra.gif, the reusable infrastructure
    ./build.sh --poster=infra         # -> sections/infra.png, the reusable pieces only
    ./build.sh --section=toolkit      # -> sections/toolkit.gif, the toolkit, assembled
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
| Federal Partners | tools -> STAC | STAC -> tools |
| Data Processing | block -> STAC | STAC -> block |
| Portal Content | STAC -> Portal | **none — one way** |

- **Main is dominant, minor is subordinate.** The minor return flow must be
  visually lighter and must not compete with the main direction for attention.
- **Federal Partners is a chain**: Earthdata GIS / FEMA / Census -> a junction
  -> ArcGIS Desktop, ArcGIS Online, Service Workflows -> STAC. The three partner
  marks are **sources only**; no flow from STAC may ever terminate on one. Both
  STAC-side connectors attach to the three tools. The block's section key is
  still `egis`, and `sections/egis.gif` is still its GIF.
- **TinaCMS is one-way.** Portal Content has no return path to STAC — that
  integration does not exist yet. Do not add one for symmetry.

## Labeling the output

The GIFs and PNGs this builds are NASA external material, so NASA's media
labeling rules apply to them. The rules, as of October 2026:

- **NID 1383.155** (effective 15 Sep 2025, nominal expiry 15 Sep 2026)
  distinguishes **SI-generated** media, where the SI contributes substantive
  creative content, from **SI-assisted** media, where the human keeps primary
  creative direction and editorial control and the SI is a tool. SI-generated
  media must be visibly and permanently watermarked and carry embedded
  metadata. SI-assisted media must carry embedded metadata that says so, but
  no watermark.
- **NASA Generative Content Labeling Guidelines** (NP-2025-08-6668-HQ,
  5 Oct 2026) supplies the watermark: the words GENERATED / CONTENT stacked,
  white on a black box with a white outline. On landscape media the box spans
  at least 10% of the image width; on portrait media at least 5% of the
  height; in every case inset 2.5% from the two nearest edges, in whichever
  corner obstructs least. The artwork (`SI-Label-Icon.zip`: SVG, PNG, EPS,
  Illustrator) and overlay templates (`SI-Label-Templates.zip`: 5000 px PNGs
  per orientation, plus a PowerPoint deck) are on NASA's Unified Visual
  Communications System SharePoint and the Brand Center. They are **not**
  checked in here; like the logos, they are NASA's to distribute.
- Terminology here follows Executive Order 14434 (29 Sep 2026) and NASA's
  Office of Communications guidance on it; the directive's own text is being
  updated administratively. Only the current label artwork (October 2026)
  may be applied to new public content. Any asset in active circulation that
  carries an earlier label must be re-issued with the current one.

How this diagram was made: the story, the wording, the architecture claims
above and every nudge in `overrides.json` are the author's. The code that
draws it was written with a large language model coding assistant. No
generative image model touched any frame; each one is a deterministic render
of described geometry, and the logos and screenshots are extracted from NASA's
own exports. The
author's reading is that this is **SI-assisted** under NID 1383.155, so the
output carries no watermark.

Every GIF and PNG the build writes carries that statement as embedded
metadata, which is what NID 1383.155 asks of SI-assisted media: a GIF
Comment Extension, or a PNG `tEXt` chunk, written by
`svg_flow_animator.provenance` after ffmpeg and rsvg-convert finish (ffmpeg
accepts `-metadata` for these formats and writes nothing). The wording is
`PROVENANCE` in `gen_frames.py`; `build.sh` reads it back from each file
before reporting done, and so does

    python3 -c 'from svg_flow_animator import provenance; print(provenance.read("sections/intro.gif"))'

One item stays open: the approval authority decides the category, not the
author. If a reviewer classifies the GIFs as generated, stamp the label on
each output at the sizes above and re-release; nothing in the pipeline
prevents it.

## Files

    edit.sh           launch the editor (start here)
    serve.py          live-preview server behind it
    layout.py         all coordinates -- the thing to edit by hand
    overrides.py      the tunable-geometry layer + handle registry
    editor.py         generates the browser editor
    gen_frames.py     draws one SVG per frame
    journey.py        the journey slide: swath -> copies -> store once + STAC
    globe.py          orthographic globe, orbits, swaths, Blue Marble raster
    bottleneck.py     the bottleneck slide: a queue behind a neck that opens
    funnel.py         that queue, shared by the bottleneck and story slides
    story.py          globe + formats + bottleneck + automation, in 45 s
    uses.py           the uses slide: silos and hand-offs, then one system
    response.py       the response slide: the whole network, end to end, in 15 s
    infra.py          the infrastructure slide: the eight reusable pieces, no paths
    toolkit.py        the toolkit slide: a tray of the eight, moved into place
    style.py          flat vs sketch drawing backends
    rough.py          Excalidraw-style sketchy geometry (roughjs port)
    extract_assets.py re-extract artwork from a source SVG export
    build.sh          the whole pipeline

The reusable engine is at https://github.com/kyle-lesinger/svg-flow-animator

## Artwork is not included

`assets/` is gitignored: the logos and site screenshots belong to NASA, Esri and
others and are not ours to redistribute. Run `extract_assets.py` against your
own source SVG export to populate it, then everything else works.

# Example: NASA Disasters ingest-flow animation

Everything needed to regenerate and re-tune the animated architecture diagram.
Self-contained: `assets/` already holds the extracted artwork, so you do not
need the original Lucidchart export unless you want to re-extract.

## Build

    ./build.sh                        # -> disasters-data-flow.gif
    FLOWGIF_STYLE=sketch ./build.sh   # -> disasters-data-flow-sketch.gif

Needs `rsvg-convert` and `ffmpeg` on PATH. No Python packages.

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

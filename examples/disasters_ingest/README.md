# Example: NASA Disasters ingest flow

The diagram this library was built for. It animates how data reaches the
Disasters Learning Portal's STAC catalog: six upstream catalogs and an AWS
bucket converge on the VEDA Ingest UI, Airflow SM2A writes to STAC, and funded
partners push into the same bucket.

This is a snapshot of the real working project, kept standalone: it imports
`layout`, `overrides` and `style` as local modules rather than from the
installed package, so the directory can be copied and run anywhere. The
generalised versions of the same ideas live in `svg_flow_animator.overrides`
and `svg_flow_animator.editor`.

## Running it

The artwork is **not** in this repo — the logos and screenshots belong to NASA,
Esri and others, and are not ours to redistribute. You supply the source
diagram; the pipeline recovers the assets from it.

```bash
python3 extract_assets.py            # pull embedded rasters out of your export
./build.sh                           # -> disasters-data-flow.gif
FLOWGIF_STYLE=sketch ./build.sh      # -> disasters-data-flow-sketch.gif
```

`extract_assets.py` reads the path to your export from the `SRC` constant at
the top of the file — that is the one absolute path you have to set. Everything
else resolves relative to the script.

## Moving things by hand

```bash
python3 editor.py                    # -> editor.html
```

One file carries **both** renders. Pick flat or hand-drawn with the buttons at
the top; the handles do not move when you switch, because the two styles are
the same geometry drawn differently, and a saved `overrides.json` applies to
both.

Run `./build.sh` at least once before generating the editor. The backdrop is
the real frame 0, and its sprite hrefs point into `frames/assets/`, which
`build.sh` stages. Without that the editor still comes up, but the backdrop is
missing every logo — librsvg drops images it cannot resolve *silently*, so
nothing warns you.

- drag a blue dot to move a node; a **green** dot moves a label
- drag a dashed box to move it; drag its corner square to resize
- drag an orange dot to move a connector vertex
- **double-click an orange line to add a bend point** — this is how you change
  a line's angle
- right-click a bend point to delete it
- shift-drag snaps to 5px; ⌘Z / ⌘⇧Z undo and redo

### Live preview

```bash
python3 serve.py                     # then http://localhost:8750/editor.html
```

With the server running, the editor asks the real renderer for a new backdrop
as you drag, and can write `overrides.json` straight into the project — no
download, no file shuffling. `POST /render` previews without side effects;
`POST /save` writes for real. Opened straight off disk instead, the editor
notices there is no server, disables those two buttons and says why.

### Without the server

Drag, click **Download overrides.json**, then:

```bash
./apply.sh            # rebuild flat
./apply.sh sketch     # rebuild hand-drawn
```

`apply.sh` collects the file the browser dropped in `~/Downloads`, moves it
here, prints what changed, rebuilds, and refreshes the editor backdrop.

`overrides.json` only stores what differs from the defaults, so it stays small
and readable. An empty `{}` means "use every default". Delete a key to revert
just that one thing; delete the file to revert everything.

## Files

    layout.py         all coordinates -- the thing to edit by hand
    overrides.py      the tunable-geometry layer + handle registry
    editor.py         generates the browser editor
    serve.py          live-preview server for the editor
    gen_frames.py     draws one SVG per frame
    style.py          flat vs sketch drawing backends
    rough.py          Excalidraw-style sketchy geometry (roughjs port)
    extract_assets.py re-extract artwork from a source SVG export
    build.sh          the whole pipeline
    apply.sh          pick up a downloaded overrides.json and rebuild

## What it demonstrates

- **Asset recovery** — `extract_assets.py` pulls 18 embedded rasters out of a
  Lucidchart export at native resolution. The Airflow pinwheel was vector-only,
  so its four blade paths are lifted by fill colour and inlined, which is what
  lets it spin.
- **A restructured layout** — `layout.py` puts STAC on the exact canvas centre
  with mirrored pairs around it, rather than reproducing the original's
  left-to-right drift. Sources bow on an arc around the ingest UI, and every
  label carries its own handle so a crowded caption can be nudged without
  dragging its icon along with it.
- **Derived timing** — each caption's hold is computed so every one clears a 7s
  readability floor, and stages are laid end to end so two are never legible at
  once.
- **Auto-placed captions** — each stage declares only its subject; the position
  is searched for at render time, widest bubble first, and the tail is dropped
  entirely once the bubble lands too far away to be pointing at anything.
- **Both styles** from one codebase via `--style=`.

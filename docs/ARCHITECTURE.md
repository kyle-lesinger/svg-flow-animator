# Architecture

## The shape of it

    layout / scene code          you write this
        |  asks for coordinates through
        v
    overrides ──────────────►  handle registry ──────────►  editor
        |  resolved geometry                                  |
        v                                                     | writes
    per-frame SVG  ──►  rsvg-convert  ──►  ffmpeg  ──►  GIF   |
                                                              v
                                                       overrides.json
                                                       (feeds back in)

One SVG per frame, rasterised in parallel, assembled by ffmpeg. Every frame is a
real file you can open and diff — which matters when something renders wrong at
frame 417 and nowhere else.

## Modules

| Module | Responsibility |
| --- | --- |
| `assets` | Recover artwork from a flattened design-tool export |
| `geometry` | Polyline maths, easing, collision-aware placement |
| `svg` | Element emitters (string-based; frames are write-once) |
| `styles` | `FLAT` / `SKETCH` drawing backends behind one interface |
| `rough` | Excalidraw-style sketchy geometry (roughjs port) |
| `timeline` | `Stage`, flow connectors, pulses, auto-placed callouts |
| `overrides` | Hand-tunable geometry + the handle registry |
| `editor` | Generates a browser editor from that registry |
| `render` | Parallel rasterisation and GIF assembly |

## The handle registry

The central idea. Scene code never hardcodes a coordinate it might want to tune:

```python
HUB  = ov.point("hub", (318, 450), "ingest hub")
STAC = ov.rect("box.stac", (660, 350, 280, 200), "STAC")
LINK = ov.path("flow.ingest_to_stac", [(500, 450), (660, 450)], "Ingest -> STAC")
```

Each call does two things: returns the resolved value (default, or an override),
and **registers a handle**. The editor is built entirely from that registry, so
adding one `ov.*` call makes a new thing draggable with no editor changes.

Four kinds:

- **point** — a draggable `(x, y)`
- **rect** — move by the body, resize by the corner
- **path** — a polyline; **inserting a vertex is how a straight connector
  becomes an angled one**, so line angles are editable with no special-casing
- **scalar** — a single number (icon size, arc bow, pitch)
- **offset** — a point stored *relative to another handle*

### Why offsets exist

Labels belong to the thing they name. Stored absolutely — even with a default
derived from the node — a label tracks its node only until you nudge it once,
after which the override pins it and it stops following. Attached until touched.

An offset stores the delta and resolves against its anchor, so the label is
**always** attached and what you tune is the relationship.

The editor resolves `anchor + delta` for drawing and converts a dropped position
back into a delta. It also drags dependents live, so a label follows its node
during the gesture rather than snapping on release.

### Registration is lazy

`ov.path()` only registers when the function owning it is **called**, and
connector functions normally run during frame generation. An editor must call
them once up front (`warm_up()`) or it will show no bendable lines at all.

## Timing

An animation is a list of `Stage`s. For any frame you ask a stage for its
`progress` (0..1 across its motion) and `alpha` (callout opacity, with fades).

Timing is **derived, not authored**. Each stage computes
`hold = max(0, MIN_BUBBLE_FRAMES - dur)` so every caption clears a readability
floor regardless of how fast its motion is, and stages lay end to end so two
captions are never legible at once.

Holds are nearly free — consecutive identical frames collapse under the GIF's
inter-frame delta. Motion is what costs bytes, not duration.

## Callout placement

A stage declares only its **subject** (`anchor`); position is searched for at
render time: the nearest spot to the subject that collides with nothing.

Two refinements learned the hard way:

- **Try every width and keep the closest**, not the first that fits. Returning
  on the first success means the widest candidate always wins wherever only one
  region admits it — and "nearest to the anchor" silently becomes a no-op.
- **A tail that spans half the canvas** stops reading as "this points at that."
  Past a threshold, draw a thin dashed **leader** to a small ring at the subject
  instead. A plain cutoff leaves captions visually unattached to their subject.

## Flow rendering

`timeline.flow()` has two phases: the line draws itself in from its origin with a
head dot at the growing tip, then a dashed overlay runs along the finished line.

Do not paint the dashes before the reveal completes. Packets appearing on track
the head has not reached yet is the tell that the motion is faked.

## Styles

`FLAT` and `SKETCH` implement the same protocol; `SKETCH` subclasses `FLAT` and
overrides only geometry. Draw through `S.box` / `S.text` / `S.poly` and both
styles come free.

Sketch costs ~6x the SVG bytes but only **+3%** on the final GIF — the extra ink
is identical in every frame, so inter-frame compression absorbs it. See
`GOTCHAS.md` for the determinism requirements, which are not optional.

## Rendering

`rsvg-convert` (librsvg) for rasterisation, `ffmpeg` for assembly.

`palettegen` with `stats_mode=diff` weights the palette toward pixels that
actually change between frames — for a mostly-static diagram that spends the
colour budget where it shows. It beats ImageMagick's quantiser noticeably at the
same size.

## Live preview

`serve.py` (in the example) gives the editor a real renderer over two endpoints:

- `POST /render` — render the scene with candidate overrides. **Side-effect
  free**: it must never touch the project's `overrides.json`, or previewing
  would corrupt saved work.
- `POST /save` — write `overrides.json` for real.

Requests are debounced client-side with only one in flight; later edits collapse
into a single follow-up and stale responses are discarded by sequence number,
so fast dragging cannot queue a backlog or land an out-of-date image.

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
| `serve` | Live-preview server behind an editor |
| `render` | Parallel rasterisation, GIF and APNG assembly |
| `workflow` | Declared workflow diagrams: components, automatic layout, beats |
| `gantt` | A Gantt timeline, animated bar by bar |
| `gantt_editor` | A browser page for a timeline's dates, served through `serve` |

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

## Sections and chapters

A **section** is one chapter of the diagram rendered as its own GIF. Every
section shows the **whole canvas** — the point of the artefact is to showcase
the ecosystem, so cutting a block out of the system it belongs to defeats it.

Cropping to the subject was built and then removed. It cost a per-section
viewport, a per-section aspect ratio, and eight tunable extent rectangles, and
it still sliced labels and arrowheads that belonged to the section, because a
box rect is not a visual extent. None of that machinery survives.

Sections therefore differ along two axes, and neither is positional:

| | what it controls |
| --- | --- |
| `SECTION_SCOPE` | which content groups **move**; everything else is frozen at its settled state, present but still |
| `section_span()` | which **frames** the GIF covers — its own chapter, plus a lead-in and tail |

Both matter. Scope without span gave a GIF that opened with 42 seconds of a
frozen picture before its chapter began, which reads as broken. Span without
scope showed another chapter's motion inside this one's frames.

### Chapters live on the ONE timeline

A chapter is a run of `Stage`s sharing a content group (`STAGE_GROUP`). They are
appended to the same `_SPEC` as everything else, so the full render is the whole
story and a section is a window onto part of it. Adding a chapter extends
`TOTAL` for everyone — that is the point: the combined journey is this timeline
played through, with scopes handing off.

Out-of-scope content is **frozen, never deleted**. A hole in a diagram whose
subject is that everything connects is worse than a still line.

### Emphasis is separate from motion

Two functions, and the split is load-bearing:

- `emphasis(scope)` — which **blocks** draw at full strength. Always includes
  `stac`, so each chapter's flows arrive somewhere visible rather than at a grey
  box.
- `flow_emphasis(scope)` — which **flows** do. No STAC exemption: exempting the
  group wholesale left the entire hub → Airflow → STAC run bright in every
  section, which is most of the width of the diagram.

A frozen flow is still a bright amber dash pattern, and amber is the loudest
thing on the canvas — so out-of-scope flows recede with the block they serve.

### Not every box is a section

`SECTION_SKIP` names boxes that are drawn but have no chapter of their own. The
buildable list is still derived from the handle registry, so adding an
`ov.rect("box.*")` still makes a section without touching the builder.

### The slides are the sections that are not boxes

`slides()` lists them, by hand, ahead of the derived sections. Each is its own
picture with its own timeline, plays once, and ends on its finished picture.

`intro` opens the story: STAC alone on an empty canvas, then a benefits panel
either side of it (open-source community, then NASA), each highlighted while its
points arrive, one every 5 seconds. STAC is the focal point, so it pulses
(glow and a 4% swell, once a second) while it is alone and again once both
panels are up; the closing hold is a whole number of pulses, so the frame left
on screen catches it at rest. It is listed by hand, first, ahead of the
derived sections.

It breaks two rules above on purpose. It does not show the whole canvas,
because it is the moment *before* the diagram. And it is not on the one timeline:
it has its own (`INTRO_TOTAL`, ~35s), because prepending it to `_SPEC` would
shift every chapter's span and change the full GIF, and nothing in it travels
along a flow.

The slides **play once** (`section_gif()`, which `build.sh` reads for ffmpeg's
`-loop` and the palette). The last frame is what stays on screen, so each ends
on its whole picture with nothing fading out. `build.sh` checks the GIF itself
for the NETSCAPE2.0 loop extension, since a wrong flag still builds a valid GIF.

The intro's panels are derived from `BOX_STAC` rather than registered as
handles: the editor previews frame 0 of the main film, where they do not exist.
The journey's geometry stays in `journey.py` for the same reason.

`journey` poses the problem and the fix on one canvas. Satellites on their own
orbits (Landsat 9, NOAA-20, the ISS) paint swaths on a Blue Marble globe; each
peels off as a dataset in its own format (GeoTIFF, NetCDF, HDF5) and is
copied into the Disasters PORTAL and MMGIS until there are datasets x tools
copies -- capped at three datasets (`N_DUP`). Then each is converted once to
a cloud-optimized format and stored once, STAC indexes them, and both tools
read in place; a
fourth satellite's file (HDF4) arrives after the fix as one file and one item.

MMGIS draws the swaths on a flat map cropped from the globe's own texture,
placed by latitude and longitude against the crop's exact extent
(`flat_extent()` snaps it to whole texture pixels and returns what those pixels
cover). The PORTAL is a website, drawn as its pages; a screenshot has no
extent, so data appears there as a chip per dataset rather than an overlay. The tools never move between problem and fix, so the reader
compares the same two boxes. The beats overlap (the next pass starts while the
last copies land), so its timeline is frame numbers rather than a stage list.

`bottleneck` names the bottleneck the architecture removed. Data pours into a
funnel and queues behind a narrow neck carrying three stations, in the order
the work happens -- download terabytes (moving the data), convert and analyze
(time to decision), copy per tool (silos; a dot splits into copies there) --
while a clock climbs to weeks. Then the neck opens and the architecture takes
their place: cloud storage (cloud-optimized), STAC (indexed once,
interoperable), web apps. The queue is computed, not simulated: departures are
fixed up front (FIFO, one through the neck per `SERVICE` frames) and every dot's
position is a pure function of the frame, so frames render in any order.

`story` tells the journey and the bottleneck once, in 45 seconds. A large
globe is shown alone while satellites paint their swaths; it glides aside and
data streams off it -- from wherever a satellite is scanning -- into the
bottleneck's funnel (download, convert by hand, copy per tool). Each format is
a SHAPE (GeoTIFF square, NetCDF triangle, NITF star, HDF5 diamond, HDF4
cross), so "many formats" is seen rather than read. The NITF one is Umbra, a
commercial SAR bought through CSDA: tasked, so it paints one framed scene
rather than a swath, and side-looking, so its beam slants from a track off the
scene's coast; when the neck opens, automated ingest turns
every shape into the one circle -- cloud-optimized -- and only it does: the
tests check no dot changes shape on the manual path, and none keeps its shape
past ingest. The queue is the bottleneck's own (`funnel.py`), and HDF4 is a
cross because a hexagon, at dot size, read as the cloud-optimized circle.

`uses` closes the slides: what the data is for -- a web dashboard, an analysis
tool, a news or event article, a lesson -- before STAC and after. Before, there
is no catalog: each app is a silo, with its own copy of the data, its own level
lane and its own schedule, and on each lane a person stands in the way doing
the hand-off by hand (download, convert, screenshot, re-upload). A person takes
longer per granule than the gap between granules, so each line grows while the
cards say "days behind". Then one system takes over -- STAC, badged as the
single source of truth, and one editor (TinaCMS) for every app: the copies
glide together into it, the lanes bend into one fan out of it, the backlog is
released in order, and four granules leave STAC for every card, a couple per
route at a time. The slide ends once the fourth has landed everywhere (`TOTAL`
is derived from that arrival, ~26 s), so the frame left on screen has every
app holding the same data and nothing in flight. The process is simplified, not automated, and the slide says so: the four
people on the lanes give way to one person at the one editor, the routes read
"simplified · via STAC", the cards "same data · up to date", and a test keeps
"automat..." off its final frame.

A granule's place is the distance it still has to go to its card. Lane and fan
both run level for the last stretch, where the people and their lines are, so a
line stays put while its route bends from lane to fan around it. Old-world and
new-world words fade in sequence, never together, and the dots are checked
against the words drawn in each frame -- the one system's labels sit across the
old lanes, and only appear once they are gone. Its cards carry page
screenshots, so it is encoded like the journey (256 colours, full).

`infra` is the whole ecosystem with the point of it brought forward: the
reusable cyberinfrastructure that makes a fast response possible -- Ingest UI,
Airflow, STAC, JupyterHub, TinaCMS, MyST Docs, Grafana, GitHub. It draws no
data path at all (no flows, packets, links or "Push data"):
`context_boxes(links=False)` and `integration_static(paths=False)` leave them
out, and every other slide's defaults are unchanged. The picture is drawn
whole, a wash recedes it, and the eight are drawn again above the wash, one per
beat, each named in the line under the title; the blocks' headings are drawn
above the wash throughout, since they are how a reader finds their way. Pieces,
frames and headings are drawn by the same helpers the diagram itself uses
(`ingest_ui`, `processing_hub`, `processing_github`, `tina_node`,
`community_item`, `stac_static`, `airflow_static`, `block_box`,
`block_title`), so each copy lands on its original pixel for pixel -- a test
checks the markup is identical, and the refactor left every other frame
byte-identical. It ends on all eight under "Interoperable · Cloud-optimized ·
Cost-effective".

Neither slide draws Community's "no automated data path" note
(`block_title(..., note=False)`, `community_block(note=False)`); the main
diagram still does.

`toolkit` tells the same thing as a build-up. The eight sit in a tray across
the top; the ecosystem, drawn at `ECO_S` (~0.82) below it, is assembled one
step at a time -- Data Integration + Funded Projects & Partners, STAC, Federal
Partners + Data Processing, Portal Content, Community & Engagement -- each
step's sections fading in at full strength and its pieces moving down out of
the tray into place. A piece is drawn by the same markup in the tray, in
flight and in place; only a transform moves and scales it, and in place it has
none, so it lands exactly where the diagram draws it (a test checks the
untransformed markup). GitHub is used twice: its first trip is a copy, and it
leaves the tray only on its last. At the end the tray gives way to the three
qualities. Sections are drawn one at a time by `egis_block`,
`processing_block(pieces=False)`, `portal_block`, `community_block(skip=...)`
and `integration_static(pieces=False)`; `context_boxes` is now composed of the
block functions, and every frame of the main diagram is byte-identical to
before.

Its PNG is NOT its last frame: `./build.sh --poster=infra` renders
`infra.poster_svg()` (via `slide_poster()`), which takes away everything that
is not reusable infrastructure -- only the six blocks' frames and headings and
the eight pieces, each where it sits in the ecosystem. Other slides' posters
are their last frame.

**No slide says "COG".** The work uses many cloud-optimized formats; naming one
says every file becomes that one. The slides say "cloud-optimized", and
`tests/test_disasters_wording.py` reads every slide's rendered text to keep it
that way.

The globe is a raster -- `globe.py` projects the texture once, in pure Python,
into a PNG cached under `frames/assets/` (librsvg's containment rule) and keyed
on its size and centre. Everything that moves is vector. It is also the one
GIF with a photograph in it, which is why `section_gif()` gives it 256 colours
over the whole picture: at 128 weighted to change, the desert snapped to the
swaths' oranges and read as fire.

## The poster

`./build.sh --poster` renders one still of the settled diagram — nothing dimmed,
nothing narrated — straight to PNG, skipping frames, ffmpeg and the GIF. It
takes `frame_svg(TOTAL - 1, captions=False)`: a caption is a claim about a
moment, and a still has no moment to be about.

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

`svg_flow_animator.serve` gives the editor a real renderer over two endpoints.
`disasters_ingest` still carries its own older copy as `serve.py`;
`managed_services` uses the package one, and builds its editor with
`editor.build(..., live={view: style})`. Without `live` an editor is
download-only, exactly as before.

- `POST /render` — render the scene with candidate overrides. **Side-effect
  free**: it must never touch the project's `overrides.json`, or previewing
  would corrupt saved work.
- `POST /save` — write `overrides.json` for real.

Requests are debounced client-side with only one in flight; later edits collapse
into a single follow-up and stale responses are discarded by sequence number,
so fast dragging cannot queue a backlog or land an out-of-date image.

The server renders in a **subprocess** that imports the example's module
fresh, because a layout resolves its geometry once at import and a style is
picked once too. The module reads `FLOWGIF_STYLE` and `FLOWGIF_OVERRIDES` and
defines `preview_svg(path) -> background`; the full contract is in the
`serve` module docstring.

## Declared diagrams

`workflow` and `gantt` invert the usual arrangement: instead of a layout file of
coordinates, a diagram is declared as data and the coordinates are derived.

- **Workflow.** Columns come from the edges (longest path; an edge closing a
  cycle is left out), each column is ordered by barycentre sweeps that keep the
  arrangement with the fewest crossings, and the canvas is fitted to the
  requested aspect. Each node then resolves through `ov.rect`, so the derived
  layout is only the default and the ordinary editor tunes it. Lines, their
  ports and group frames are computed from the resolved nodes every time and
  never stored, so nothing can detach.
- **Gantt.** Rows are keyed, a schedule is `{key: (start, end)}`, and the
  geometry follows from the dates. Its editor is not the handle editor --
  dates are not coordinates -- but a page of its own that posts candidate
  schedules to routes on the same server (`serve(routes=...)`) and writes
  `schedule.json` only on Save.

Both animations open and close on the finished picture: frame 0 is what any
viewer without APNG support shows, and matching the last frame to it gives the
loop no seam.

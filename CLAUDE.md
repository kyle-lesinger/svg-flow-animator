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
  serve.py             live-preview server behind an editor (/render, /save)
  render.py            parallel rasterisation, GIF / APNG assembly, export()
  provenance.py        embed a comment in a finished GIF / PNG / APNG, read it back
  workflow.py          declared workflow diagrams: components, auto-layout, beats
  gantt.py             Gantt timeline, animated bar by bar
  gantt_editor.py      browser page for a timeline's dates (schedule.json)
examples/minimal/      self-contained demo, no external artwork
examples/disasters_ingest/   the real diagram this was built for
examples/managed_services/   Managed Services / External accounts walkthrough
examples/shared_services/    the same story with a shared-capabilities box
examples/s2_landsat_review/  who reviews what (workflow) and when (gantt), as APNGs
docs/                  ARCHITECTURE, DECISIONS, GOTCHAS, ASSETS
```

Every module in `svg_flow_animator/` is a **library module** — none is runnable.
`python3 svg_flow_animator/editor.py` fails with `attempted relative import with
no known parent package`; that is expected, not a bug. Editors are produced by
an example calling `editor.build(...)`.

## Run / verify

```bash
python3 tests/run.py                                 # 533 tests, ~11s
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
./edit.sh managed            # managed_services, live preview
./edit.sh shared             # shared_services, live preview
./edit.sh review             # s2_landsat_review: timeline dates + layout, live
```

Each example also has its own `edit.sh`; the root one only dispatches. The
disasters example additionally has `./build.sh` (`FLOWGIF_STYLE=sketch` for the
hand-drawn GIF), and **will not run until `assets/` is rebuilt** — see
`docs/ASSETS.md`.

That build also emits one GIF per chapter, plus a still of the whole thing:

```bash
./build.sh --list-sections     # what is buildable, and what each animates
./build.sh --section=intro     # -> sections/intro.gif, the story's opening
./build.sh --section=journey   # -> sections/journey.gif, problem and fix
./build.sh --section=bottleneck  # -> sections/bottleneck.gif, the bottleneck solved
./build.sh --section=story     # -> sections/story.gif, the two combined, 45 s
./build.sh --section=uses      # -> sections/uses.gif, data to every audience
./build.sh --section=infra     # -> sections/infra.gif, the reusable infrastructure
./build.sh --section=toolkit   # -> sections/toolkit.gif, the toolkit, assembled
./build.sh --section=egis      # -> sections/egis.gif
./build.sh --all-sections
./build.sh --poster            # -> sections/ecosystem.png, 3200x1800
./build.sh --poster=infra      # -> sections/infra.png, a slide's last frame
```

**Sketch is the default style** here; `FLOWGIF_STYLE=flat` gets the clean
render. The filename suffix applies to whatever is *not* the default, so
`egis.gif` is the sketch one and `egis-flat.gif` is the other.

Every section shows the **whole canvas** — it is not a crop. Sections differ by
what MOVES (`SECTION_SCOPE`) and which frames they cover (`section_span`). See
`docs/ARCHITECTURE.md`.

The exceptions are the opening **slides** (`slides()` in `gen_frames.py`), each
its own picture on its own timeline, not on `_SPEC`, and each plays once:

- `intro`: STAC alone, then a benefits panel either side of it (`intro_svg`,
  `INTRO_PANELS` for the wording). STAC pulses at the start and the close.
- `journey`: a satellite paints a swath on a Blue Marble globe; copying each
  dataset into every tool multiplies; then store once, index in STAC, read in
  place (`journey.py`, globe maths and raster in `globe.py`). It needs
  `assets/blue-marble-2048.jpg` -- see `docs/ASSETS.md`.
- `bottleneck`: data queues behind a narrow neck (download, convert and
  analyze, copy per tool), then the neck opens into cloud storage, STAC and web
  apps (`bottleneck.py`). The queue is computed per frame, not simulated
  (`funnel.py`, shared with `story`).
- `story`: the journey and the bottleneck in one 45 s picture -- a showcase
  globe, a shape per data format (incl. a CSDA commercial SAR, Umbra), the
  manual bottleneck, then automated ingest
  to a cloud-optimized format, STAC and web apps (`story.py`).
- `uses`: what the data is for -- a web dashboard, an analysis tool, a news
  or event article, a lesson. Before STAC each app is its own silo (own copy,
  own lane, own schedule) with a person doing the hand-off by hand; then one
  system -- STAC, the single source of truth, and one editor (TinaCMS) --
  gathers the copies, the lanes bend into one fan out of it, the four
  hand-offs become one person at one editor, and every app shows the same
  data (`uses.py`, ~26 s). It says *simplified*, never automated.
- `infra`: the whole ecosystem with no data paths, quietened (block headings
  stay crisp), and the eight pieces of reusable cyberinfrastructure (Ingest
  UI, Airflow, STAC, JupyterHub, TinaCMS, MyST Docs, Grafana, GitHub) brought
  forward one at a time, each named; it ends on all eight under
  "Interoperable · Cloud-optimized · Cost-effective" (`infra.py`, 29.4 s).
  Its PNG (`--poster=infra`, `poster_svg`) is only the blocks' frames and
  headings and the eight pieces. Each piece, frame and heading is drawn by the
  same `gen_frames` helper the diagram uses (`ingest_ui`, `block_title`, ...).
  Community's "no automated data path" note is left out (`note=False`).
- `toolkit`: the same eight in a tray across the top; the ecosystem (at ~82%)
  is assembled beneath it section by section -- Data Integration + Funded
  Projects first -- each piece moving down out of the tray to where the
  diagram draws it (GitHub twice: a copy first, the original last); ends on
  the three qualities where the tray was (`toolkit.py`, 26 s). Sections are
  drawn one at a time by `egis_block`, `processing_block`, `portal_block`,
  `community_block`, which `context_boxes` is now built from.

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

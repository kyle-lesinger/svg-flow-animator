# Recovering artwork

`examples/disasters_ingest/assets/` is gitignored — the logos and screenshots
belong to NASA, Esri and others. A fresh clone cannot render that example until
the directory is rebuilt from the design-tool export.

## What comes back automatically

```bash
python3 examples/disasters_ingest/extract_assets.py
```

Recovers every base64 raster in the export's `<defs>`, named by its Lucidchart
id (`bD.png`, `cy.png`, …) — byte-exact at native resolution. `SRC` at the top
of that script is a hardcoded path to the export; point it at your own copy.

## What does not

`extract_assets.py` only handles `<image>` payloads. Marks drawn as vector
`<path>` elements are invisible to it, and several of the logos are vector:

| asset | how to find it |
| --- | --- |
| `airflow.svg` | the paths inside `AIRFLOW_SRC_VIEWBOX`, filtered to the pinwheel's own nine fills |
| `jupyter.png` | fills `#f37726`, `#767677` |
| `github.png` | fill `#24292f` |
| `notebook.png` | fill `#01a88d` — the Service Workflows glyph, used in **two** places (Earthdata GIS and Data Processing) |
| `listserv.png` | fills `#f58535`, `#9d5125`, `#fff` — 9 paths, near inner (2288, 406) |
| `myst.png` | fills `#e6d478`, `#fff` — 2 paths, near inner (2520, 404) |

`AIRFLOW_SRC_VIEWBOX` in `layout.py` is a region of the **source export**, not
of the output canvas. That is what makes the pinwheel locatable at all.

### Inspecting the export

You cannot reason about this file from coordinates alone — render the region and
look at it. Two things make that harder than it should be:

**The root `<svg>` has no `viewBox`.** Setting `width`/`height` therefore crops
rather than scales, and a naive `re.sub` on `viewBox=` silently matches nothing
and leaves you staring at a blank corner. Inject one:

```python
root = re.match(r'<svg[^>]*>', svg).group(0)
new  = root[:-1] + ' viewBox="%d %d %d %d">' % region
new  = new.replace('width="4266"', 'width="1000"').replace('height="2702"', 'height="1000"')
open("/tmp/r.svg", "w").write(svg.replace(root, new, 1))
```

**`<pattern>` `x`/`y` is the tile origin, not the placement.** A pattern is
positioned by whatever shape uses it as a fill, so those coordinates will send
you to the wrong part of the diagram. Render and look instead.

**The whole diagram sits inside `<g transform="translate(714 -163)">`.** Path
coordinates are therefore in *inner* space, and a search window derived from
what you measured off a full-document render will silently match nothing. This
is the single most expensive mistake here: it makes a recoverable mark look
absent, and two assets were wrongly written off as having no source before it
was spotted. Either work in inner coordinates, or subtract the group's
translate from anything you measured on a render.

### Procedure for a vector mark

1. Collect `<path>` elements whose first absolute `M` coordinate falls inside a
   deliberately oversized window, or whose fill matches a brand colour —
   `assets.fill_histogram()` lists every fill in the export.
2. Render that window at a known pixel width.
3. `identify -format %@` for the ink bbox, then `assets.ink_bbox()` to map it
   back into user units.
4. Re-render at the tight viewBox, keeping transparency — these composite over
   a box fill.

Step 3 is not optional. Guessing a tight viewBox from the path data does not
work: relative commands (`c`, `l`, …) make the raw numbers deltas, so min/max
over them is meaningless and yields a bbox thousands of units wide.

Two ways this goes quietly wrong, both of which produce a *plausible* icon:

- **A window catches strays.** Selecting by region alone picks up anything that
  merely starts inside it. The Airflow pinwheel came back with a connector arrow
  welded to its edge, because the export's arrow green (`#008a0e`, 31 uses
  diagram-wide) happens to begin inside the mark's viewBox. Filter by the mark's
  **own palette**, not just position, and render each candidate path separately
  when something looks off.
- **Ink touching the viewBox edge is clipped before it is measured.** In step 2
  the render is what `identify` measures, so anything clipped by the window is
  missing from the bbox and stays missing from the crop. The Service Workflows
  notebook lost its bottom edge this way and looked like a legitimately
  open-sided glyph. Make the window generous — if the ink reaches an edge, widen
  and redo.

Airflow stays `.svg` because it is **inlined and rotated** per frame —
`_load_airflow_blades()` reads the file and splices its paths into each frame.
The others are rasterised, because `img()` emits `<image href>`.

## Screenshots

The four portal captures are all extracted ids: `aX.jpg` (home), `aZ.jpg`
(story), `aY.jpg` (visualisation), `ce.jpg` (training).

## Verifying

Nothing warns when an `<image href>` fails to resolve — librsvg drops it
silently and the diagram still looks plausible. Check explicitly:

```python
import os, re, gen_frames as G
G.stage_assets()
missing = [h for h in set(re.findall(r'href="([^"]+)"', G.frame_svg(0)))
           if not h.startswith("data:") and not os.path.exists(h)]
```

Every referenced asset now resolves — verified on frames 0, 291, 430 and 610
(23 hrefs, none missing). Keep it that way: a broken href is silent.

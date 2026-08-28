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
| `airflow.svg` | the paths inside `AIRFLOW_SRC_VIEWBOX` |
| `jupyter.png` | fills `#f37726`, `#767677` |
| `github.png` | fill `#24292f` |

`AIRFLOW_SRC_VIEWBOX` in `layout.py` is a region of the **source export**, not
of the output canvas. That is what makes the pinwheel locatable at all.

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

`listserv.png`, `myst.png` and `notebook.png` are not in the export and have no
known source. They render as empty framed placeholders.

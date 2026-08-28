# Example: NASA Disasters ingest flow

The diagram this library was built for. It animates how data reaches the
Disasters Learning Portal's STAC catalog: six upstream catalogs and an AWS
bucket converge on the VEDA Ingest UI, Airflow SM2A writes to STAC, and funded
partners push into the same bucket.

## Running it

The artwork is **not** in this repo — the logos and screenshots belong to NASA,
Esri and others, and are not ours to redistribute. You supply the source
diagram; the pipeline recovers the assets from it.

```bash
python3 extract_assets.py            # pull embedded rasters out of your export
./build.sh                           # -> disasters-data-flow.gif
FLOWGIF_STYLE=sketch ./build.sh      # -> disasters-data-flow-sketch.gif
```

Both scripts hardcode absolute paths for the source SVG and working directory —
edit the constants at the top of `layout.py` and `extract_assets.py` first.

## What it demonstrates

- **Asset recovery** — `extract_assets.py` pulls 18 embedded rasters out of a
  Lucidchart export at native resolution. The Airflow pinwheel was vector-only,
  so its four blade paths are lifted by fill colour and inlined, which is what
  lets it spin.
- **A restructured layout** — `layout.py` puts STAC on the exact canvas centre
  with mirrored pairs around it, rather than reproducing the original's
  left-to-right drift.
- **Derived timing** — each caption's hold is computed so every one clears a 7s
  readability floor, and stages are laid end to end so two are never legible at
  once.
- **Auto-placed captions** — each stage declares only its subject; position is
  searched for at render time.
- **Both styles** from one codebase via `--style=`.

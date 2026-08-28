# Tests

Stdlib `unittest` only — no pytest, no plugins. The package is dependency-free
on purpose (`docs/DECISIONS.md`) and the suite holds to the same rule.

## Running

From the repo root:

```bash
python3 -m unittest discover tests     # plain
python3 -m unittest                    # same thing, discovers tests/
python3 tests/run.py                   # + a summary naming every skip
python3 tests/run.py -v                # per-test names
python3 tests/run.py test_rough        # one module
python3 tests/run.py test_rough.TestSeedFor.test_never_returns_zero
```

`tests/run.py` exists only for the skip report. A green run that quietly
skipped half the suite looks exactly like a green run that did not, and most of
what is skipped is skipped because an external binary is missing.

## What is optional

Nothing here is required to pass on a fresh clone. Anything that needs more
than Python skips cleanly:

| Needs | Skips when absent |
| --- | --- |
| `rsvg-convert` | rasterisation and the frame pipeline |
| `ffmpeg` | GIF assembly |
| `magick` | `probe_gif` read-back |
| `node` | `node --check` on the generated editor JS |
| `examples/disasters_ingest/assets/` | the disasters staging check (gitignored artwork) |

`SFA_SKIP_SLOW=1` skips `test_integration` — the only module that rasterises
anything. It renders 8 frames, not the demo's 360, and takes well under a
second, so it runs by default.

## Layout

| Module | Covers |
| --- | --- |
| `test_geometry` | easing bounds/monotonicity, polylines, `wrap`, `rects_overlap`, `place_near`, `fit_viewbox` |
| `test_overrides` | handle registry, defaults vs overrides, `offset` against its anchor, `active()`, save/load round-trip |
| `test_rough` | sketch determinism — same identity → identical geometry, across processes and `PYTHONHASHSEED` |
| `test_assets` | PNG/JPEG header parsing against synthesised files, `ink_bbox` arithmetic |
| `test_svg` | emitter well-formedness, escaping, the `fill="transparent"` ban |
| `test_editor` | raw-string template guard, `node --check`, payload/layer mapping |
| `test_timeline` | stage timing, flow reveal, callout placement |
| `test_render` | asset staging, missing-binary messages |
| `test_integration` | SLOW: frames → PNGs → GIF, asserted on plausibility |
| `_support` | shared helpers: synthesised PNG/JPEG, SVG fragment parsing, skip decorators |

## The shape of these tests

`docs/GOTCHAS.md` is the specification. Every entry there is a failure that
**exits zero and produces a plausible-looking wrong result** — so almost
nothing here asserts on an exit status. Where a cheap invariant exists, it is
checked instead: the aspect ratio actually held, the frames actually differ,
the PNG is big enough to contain a picture, the generated JS actually parses.

Two habits worth keeping:

- **Point a guard at an artefact that contains what it checks.** A check
  against frame 0 sees no animation and passes forever. `test_integration`
  renders frames from the middle of the timeline for exactly this reason.
- **Source-level guards look at what a module can *emit*.** Most gotchas are
  documented in a comment right beside the code that avoids them, so a naive
  substring scan matches the warning rather than a relapse.
  `_support.package_emitted_literals()` strips docstrings and CSS/JS comments
  first.

## Known bugs kept as expected failures

Two tests are marked `@unittest.expectedFailure`. They are **not** weakened —
they assert the documented correct behaviour, they fail, and the suite reports
them as known. If one starts passing, unittest reports an *unexpected success*
and `run.py` says which decorator to delete.

- `test_render.TestStageAssets.test_KNOWN_BUG_mtime_comparison_serves_stale_artwork`
  — `render.stage_assets` guards its copy with
  `os.path.getmtime(src) > os.path.getmtime(dst)`, the exact idiom
  `docs/GOTCHAS.md` says is wrong. Anything that preserves timestamps
  (`cp -p`, `tar -x`, a restored backup, a build cache) leaves stale artwork
  staged.
- `test_timeline.TestCallout.test_KNOWN_BUG_widths_are_first_fit_not_closest_fit`
  — `timeline.callout` breaks out of its width loop on the first width that
  places anywhere. `docs/ARCHITECTURE.md` says to try every width and keep the
  closest. In the test's layout the caption lands 228px from its subject when
  6px was available.

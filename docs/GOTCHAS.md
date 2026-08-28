# Gotchas

Every entry here cost real debugging time. They share a shape: **the code runs,
exits zero, and produces a plausible-looking wrong result.** That is far worse
than a crash, because nothing draws your attention to it.

Ordered by how much time they cost.

## librsvg silently refuses resources outside the document's directory

**Symptom:** images simply do not draw. No warning, no stderr, exit code 0.

librsvg will only load an `<image href>` at or below the referencing SVG's own
directory. A frame in `frames/` cannot reach `../assets/logo.png`. A scene
rendered into `/tmp` cannot reach anything in your project at all.

This bit three separate times: once in the frame pipeline, once in a live-preview
server that wrote its scratch SVG to `tempfile.gettempdir()`, and once when a
cleanup step deleted the staged copy.

**Mitigations, all of which you want:**

- `render.stage_assets()` mirrors sprites below the frame directory.
- Anything that renders an SVG referencing sprites must write that SVG *inside*
  the project tree, not in a temp directory.
- Assert on output size. A full scene renders to ~370KB; losing every sprite
  drops it to ~108KB. A `MIN_PLAUSIBLE_PNG` check turns a silent wrong picture
  into a loud error.
- Cleanup must delete `frames/f*.svg` and `frames/f*.png`, **not** `frames/*`,
  or it takes the staged assets with it.

## Copying assets by mtime silently serves stale artwork

`if os.path.getmtime(src) > os.path.getmtime(dst)` looks reasonable and is
wrong. Anything that preserves timestamps — `cp -p`, `rsync -t`, `tar -x`,
restoring a backup, a build cache — leaves the destination looking current. You
replace a logo, rebuild, see the old logo, and conclude your edit did not save.

Compare **size or content**, or just copy unconditionally.

## `fill="transparent"` captures pointer events in SVG

`fill="none"` is not hit-testable. `fill="transparent"` is — it is a fully
transparent *paint*, and it swallows clicks.

A 550x640 container rect with `fill="transparent"` intercepted every click aimed
at the nodes inside it. Nothing errored; the handles just felt dead.

Give containers `fill="none"` and a separate fat transparent **stroke** with
`pointer-events:stroke`, so only the border is grabbable.

## Re-rendering during `pointerdown` destroys the drag you just started

If your drag handler rebuilds the overlay to show selection, it removes the very
element the gesture is attached to — and the `pointermove` listener goes with it.
The drag can never progress, and nothing throws.

Update handles **in place** during a drag; do a full re-render only on release.

## `getElementById` + `CSS.escape` never matches

`CSS.escape('box.stac')` returns `box\.stac`, correct for a *selector*. But
`getElementById` matches the id **literally**, so it will never find the element.

Every dotted key silently stopped tracking. Keep a `Map` from key to element.

## Escapes passed through two levels of Python string parsing

A JS snippet inside a Python template that is itself written by a generator gets
un-escaped twice. `'\\n'` in the generator becomes `'\n'` in the template file,
which Python then turns into a **real newline** inside a JS string literal —
breaking the entire script, with no Python-side error.

Make templates **raw strings** (`r"""..."""`), and run `node --check` on
generated JS before shipping it.

## `hash()` is salted per process

Seeding anything reproducible with Python's `hash()` of a string gives different
results on every run (`PYTHONHASHSEED`). Frames stop being reproducible.

Use `zlib.crc32`.

## `grep` exits 1 on "no matches", which `set -e` treats as failure

A build guard that greps for problems kills the build when it finds none — the
success case. Silently, because `set -e` exits without a message.

Wrap it: `LEAKS=$( { grep ... || true; } | wc -l )`.

## `preserveAspectRatio="meet"` shrinks things you expected to fill

A 1.4:1 wordmark in a 188x74 slot is pinned to 104x74 **by height**, leaving
most of the width empty. It looks like the asset is low quality.

Size the slot to the artwork's aspect ratio, or use `slice` when several
differently-shaped images must fill equal frames uniformly.

## Colour-keying a background can eat your whites

Knocking out `#fbf0ff` at 8% fuzz also removes white — they differ by only 5.9%.
Icons lost their white inner details.

Keep the fuzz below the distance between the background and the lightest colour
you care about.

## An unstyled container shows the page through it

An element with a background *image* but no background *colour* is transparent
wherever the image fails to load. On a dark page that reads as "the screen went
black" rather than "an image is missing."

Always give it an explicit ground colour.

## `BaseHTTPRequestHandler.log_message` receives different argument types

`log_request` passes a request line (str); `log_error` passes an `HTTPStatus`.
Code assuming `args[0]` is a string raises `TypeError` **inside the handler
thread**, aborting the response mid-flight. The browser sees
`ERR_EMPTY_RESPONSE`, and a favicon 404 is enough to trigger it.

Wrap the format in `try/except`.

## librsvg's filter support is poor

`feGaussianBlur` will not give you a glow. Stack a few concentric strokes at
decreasing opacity instead (`svg.glow()`).

Colour filters (`feColorMatrix`, `feComponentTransfer`) *do* work — the weakness
is specifically blur.

## Sketch-mode determinism: seed from identity, one PRNG per shape

Two rules, and the second is the one that bites:

1. Seed jitter from each shape's **identity**, never the frame number.
2. Give every shape its **own** PRNG.

A shared random stream re-jitters everything downstream the moment a flow or
caption appears or disappears — the whole diagram visibly boils. Verify by
diffing rendered frames of a never-animated region; it should be byte-identical.

Corollary: seed a pulsing ring on its centre, not its animating radius.

## A roughjs outline cannot be filled

It is a set of disjoint subpaths; `fill` on it produces garbage. Draw a clean
exact-geometry shape underneath instead. This is why unstroked `<rect>` and
`<ellipse>` legitimately appear in sketch output — a leak check must look for
**stroked** flat primitives only.

## `cursive` resolves to Zapfino on macOS

End a handwriting font stack with `sans-serif`, never `cursive`.

## Guards that inspect the wrong frame cannot fire

A check that runs against frame 0 sees no animated content, because frame 0 is
before any stage starts. It will pass forever. Point guards at a frame that
actually contains what they are checking.

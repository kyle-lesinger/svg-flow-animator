# Decisions

Why things are the way they are, including the ones that were measured rather
than assumed — and the ones where the measurement contradicted the hypothesis.

## Generate frames rather than animate SVG

Animated SVG (SMIL/CSS) is smaller and sharper, and useless where these diagrams
get shown: Google Slides, Keynote, PowerPoint and GitHub READMEs run none of it.
A GIF plays everywhere with no plugin, embed, or upload step.

Discrete frames also make every intermediate state a real file you can open and
diff, which is most of how the bugs in `GOTCHAS.md` were found.

## Stdlib only

No Pillow, no numpy, no lxml. The machine this was built on had none of them,
and adding a dependency to read a PNG header was avoidable — dimensions come
straight from the IHDR/SOF bytes. Image work shells out to ImageMagick and
ffmpeg, which are needed anyway.

The cost is worth naming: `assets.py` hand-parses two container formats.

## ffmpeg over ImageMagick for GIF assembly

`palettegen`/`paletteuse` with `stats_mode=diff` produces a visibly better GIF
at the same size. Not close.

## Extract artwork, don't screenshot it

Design-tool exports bury real assets in `<defs>` as base64. They come back
byte-exact at native resolution — 256x256 up to 1600x1600 in the source that
motivated this. Cropping a render throws that away and picks up whatever the box
fill was.

For vector marks, locating paths **by brand fill colour** keeps them vector, so
they can be rotated (a spinning logo) rather than resampled.

## Coordinates route through `overrides`, not constants

Two things fall out of one indirection: a JSON file can nudge any coordinate
without touching code, and every request registers a handle so tooling can
discover what is movable. The editor hardcodes nothing.

The alternative — a hand-maintained list of editable things — drifts the moment
someone adds a node.

## Labels are offsets, not absolute points

**Reversed after use.** Absolute positions with a node-derived default look
correct and are subtly wrong: the label follows its node until nudged once, then
never again. "Sometimes the label is attached to the object" is exactly the
symptom.

Storing the delta makes attachment unconditional. See `ARCHITECTURE.md`.

## Caption timing is derived, not authored

`hold = max(0, MIN_BUBBLE_FRAMES - dur)` guarantees every caption clears a
readability floor whatever its motion length. Authored holds silently erode that
guarantee the first time someone retimes a stage.

The floor is the one promise the format makes — that every caption is readable
at projection distance. Trading it to hit a length target is the wrong trade;
the lever for a shorter piece is *fewer captions*, not shorter ones.

## Two GIFs rather than one long one — for ergonomics, not encoding

**The obvious argument was measured and was wrong.** The hypothesis was that
sharing one 128-colour palette across a longer animation would degrade quality
and inflate size. Measured:

| | bytes | per frame |
| --- | --- | --- |
| upstream half, own palette | 1,091,653 | 8.60 KB |
| downstream half, own palette | 643,912 | 5.07 KB |
| both, one shared palette | 1,606,223 | 6.32 KB |

Combining is **7.5% smaller**, and quality loss is **0.28 dB PSNR** —
imperceptible. Encoding does not favour splitting.

The real reason is the deck. A presenter is on a slide for 30–60s; an 84s loop
means half the audience never sees the second half, and anyone glancing mid-loop
lands on an arbitrary state with no way to rewind. Two ~45s loops on two slides
let the presenter control pacing.

## Sketch mode: brand logos stay crisp inside a hand-drawn frame

Filtering or posterising them was tried and rejected — a posterised NASA
meatball becomes an unreadable blob, and desaturating a federal agency logo in a
deliverable for that agency is a conversation to avoid.

Framing is also what Excalidraw itself does with pasted images, so it is
stylistically correct rather than a compromise. Only large images get a frame;
on small marks it reads as a stray box.

## Sketch mode uses a solid underlay beneath hachure

Pale pastel fills vanish when only ~25% of the area is inked — Excalidraw's own
palette is saturated precisely because of this. A solid underlay at 55% plus
hachure on top keeps an existing palette usable. Dark fills switch to pure solid
via a luminance check, since hachuring a dark box just muddies it.

## No font is installed

Rendering happens locally and ships as a GIF, so the font never leaves the
machine and there is no redistribution question. The stack falls through
Excalifont → Virgil → Noteworthy → Chalkboard SE → Comic Sans MS → `sans-serif`.

Ending in `cursive` would be a trap: on macOS it resolves to Zapfino.

## Previews are side-effect free

`POST /render` must never write the project's `overrides.json`. Previewing a
candidate layout that silently overwrote saved work would be the worst possible
failure in an editing tool.

## A section is a scope, not a crop

**Reversed after building it.** Per-section viewports were implemented in full —
a declared visual extent per section, rendered at its own aspect ratio — and
then removed. Two reasons, and the second is the one that settles it:

- A box rect is not a visual extent, so framing from it sliced labels and
  arrowheads. Fixing that needed a second hand-maintained rectangle per section,
  which is the kind of parallel structure the handle registry exists to avoid.
- More importantly, a section GIF is for showing the ecosystem. Cropping to one
  block removes the thing the diagram is *about* — that everything connects.

What survives is the part that was actually doing the work: scoping which
content **moves**. That needs no geometry at all.

## Sketch is the default render

It costs ~6x the SVG bytes and ~3% on the finished GIF, because the extra ink is
identical in every frame and inter-frame compression absorbs it. At that price
the hand-drawn look is very nearly free, and it reads as deliberate rather than
as an unstyled default. `FLOWGIF_STYLE=flat` still gets the clean render.

The filename suffix follows the *default*, not the style name, so the default
keeps the plain filename whichever style that is.

## Guards assert on plausibility, not just exit status

Several failures here produce a valid file that is quietly wrong. Where a cheap
invariant exists — rendered PNG size, frame count, stroked-primitive count — it
is asserted, so the pipeline fails loudly instead of shipping a wrong picture.

The corollary: a guard pointed at the wrong artefact (frame 0, which has no
animation) passes forever and is worse than none, because it manufactures
confidence.

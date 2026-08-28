#!/usr/bin/env bash
# Build the animated ingest-flow GIF end to end.
#
#   1. gen_frames.py  -> frames/f0000.svg .. fNNNN.svg  (+ copies sprites below frames/)
#   2. rsvg-convert   -> one PNG per frame, in parallel
#   3. ffmpeg         -> palettegen/paletteuse GIF (better quantiser than IM's)
#
# Deps already present on this machine: rsvg-convert (librsvg 2.62), ffmpeg 9,
# ImageMagick. No Python packages beyond the stdlib.
set -euo pipefail

WD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMES="$WD/frames"
OUT="${1:-$WD/disasters-data-flow.gif}"
STYLE="${FLOWGIF_STYLE:-flat}"
[ "$STYLE" = "flat" ] || OUT="${OUT%.gif}-${STYLE}.gif"

FPS=15
GIF_W=1280
GIF_H=720
COLORS=128
[ "$STYLE" = "sketch" ] && PAPER="#fdfcf8" || PAPER="white"

echo "==> 1/4  generating frame SVGs  (style=$STYLE)"
python3 "$WD/gen_frames.py" --style="$STYLE"

# A half-converted sketch reads as a rendering bug rather than a choice, so
# fail loudly if a flat primitive leaked through.
# Only a STROKED rect/ellipse is a leak. Unstroked ones are the deliberate
# fill underlays -- a roughjs outline is disjoint subpaths and cannot be filled,
# so a clean shape goes beneath it (same trick Excalidraw uses).
if [ "$STYLE" = "sketch" ]; then
  LEAKS=$( { grep -o '<\(rect\|ellipse\)[^>]*stroke="[^"]*"[^>]*>' "$FRAMES/f0000.svg" || true; } | wc -l | tr -d ' ')
  if [ "$LEAKS" != "0" ]; then
    echo "FAIL: $LEAKS unconverted flat primitives leaked into sketch mode"
    grep -o '<\(rect\|ellipse\)[^>]*stroke="[^"]*"[^>]*>' "$FRAMES/f0000.svg" | head -5 || true
    exit 1
  fi
fi

echo "==> 2/4  rendering frames to PNG (parallel)"
# -P0 would spawn one process per frame; cap it at the core count.
JOBS=$(sysctl -n hw.ncpu 2>/dev/null || echo 8)
ls "$FRAMES"/f*.svg | xargs -P "$JOBS" -I{} sh -c \
  "rsvg-convert -w 1600 -h 900 -b '$PAPER' -o \"\${1%.svg}.png\" \"\$1\"" _ {}

NSVG=$(ls "$FRAMES"/f*.svg | wc -l | tr -d ' ')
NPNG=$(ls "$FRAMES"/f*.png | wc -l | tr -d ' ')
echo "    $NSVG svg -> $NPNG png"
[ "$NSVG" = "$NPNG" ] || { echo "FAIL: frame count mismatch"; exit 1; }
# a frame that rendered to zero bytes would silently become a black flash
if find "$FRAMES" -name 'f*.png' -size -1k | grep -q .; then
  echo "FAIL: some frames rendered empty"; find "$FRAMES" -name 'f*.png' -size -1k; exit 1
fi

echo "==> 3/4  building palette + GIF at ${GIF_W}x${GIF_H} @ ${FPS}fps"
# stats_mode=diff weights the palette toward what actually CHANGES between
# frames, which is what matters for a mostly-static diagram.
ffmpeg -hide_banner -loglevel error -y \
  -framerate "$FPS" -i "$FRAMES/f%04d.png" \
  -filter_complex "\
    scale=${GIF_W}:${GIF_H}:flags=lanczos,split[a][b];\
    [a]palettegen=max_colors=${COLORS}:stats_mode=diff[p];\
    [b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" \
  -loop 0 "$OUT"

echo "==> 4/4  verifying"
magick identify -format '%n frames, %wx%h\n' "$OUT" | head -1
ls -lh "$OUT" | awk '{print "    size: " $5}'
echo "    done -> $OUT"

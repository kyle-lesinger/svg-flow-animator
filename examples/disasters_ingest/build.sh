#!/usr/bin/env bash
# Build the animated ingest-flow GIF end to end.
#
#   1. gen_frames.py  -> frames/f0000.svg .. fNNNN.svg  (+ copies sprites below frames/)
#   2. rsvg-convert   -> one PNG per frame, in parallel
#   3. ffmpeg         -> palettegen/paletteuse GIF (better quantiser than IM's)
#
#   ./build.sh                     the whole diagram -> disasters-data-flow.gif
#   ./build.sh --section=egis      one section       -> sections/egis.gif
#   ./build.sh --all-sections      every section     -> sections/*.gif
#   ./build.sh --list-sections     what is buildable
#   ./build.sh --poster            the whole ecosystem, still -> sections/ecosystem.png
#   ./build.sh --poster=infra      a slide's last frame       -> sections/infra.png
#
# A section is one labelled box, cropped to the output's aspect ratio and
# rendered from the SAME timeline -- so it always agrees with the full GIF.
# Sections are derived from the handle registry, so adding an ov.rect("box.*")
# makes a new one buildable with no change here.
#
# Exactly one GIF is kept per section; a rebuild replaces it in place. frames/
# is scratch and is reused by each section in turn (see write_frames() for why
# it cannot be a per-section subdirectory).
#
# Deps already present on this machine: rsvg-convert (librsvg 2.62), ffmpeg 9,
# ImageMagick. No Python packages beyond the stdlib.
set -euo pipefail

WD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMES="$WD/frames"
# Sketch is the default render (see style.py). The suffix is applied to
# whatever is NOT the default, so the default style keeps the plain name.
DEFAULT_STYLE="sketch"
STYLE="${FLOWGIF_STYLE:-$DEFAULT_STYLE}"

SECTION=""
ALL_SECTIONS=0
POSTER=0
POSTER_OF=""
POSITIONAL=""
for arg in "$@"; do
  case "$arg" in
    --list-sections) python3 "$WD/gen_frames.py" --list-sections; exit 0 ;;
    --poster)        POSTER=1 ;;
    --poster=*)      POSTER=1; POSTER_OF="${arg#--poster=}" ;;
    --all-sections)  ALL_SECTIONS=1 ;;
    --section=*)     SECTION="${arg#--section=}" ;;
    -h|--help)       sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)              echo "unknown argument: $arg"; exit 1 ;;
    *)               POSITIONAL="$arg" ;;
  esac
done

OUT="${POSITIONAL:-$WD/disasters-data-flow.gif}"
[ "$STYLE" = "$DEFAULT_STYLE" ] || OUT="${OUT%.gif}-${STYLE}.gif"

FPS=15
[ "$STYLE" = "sketch" ] && PAPER="#fdfcf8" || PAPER="white"

# Build one GIF. $1 = output path, $2 = section key ("" for the whole diagram).
build_one() {
  local out="$1" section="${2:-}" label
  label="${section:-full diagram}"

  # Every section is framed at ITS OWN aspect -- a 550x80 strip and a 280x200
  # block do not want the same picture. So the raster size and the GIF size
  # come from the section, not from a fixed 1600x900 / 1280x720: pinning both
  # to 16:9 is what letterboxed the strips and forced the crops to grow into
  # unrelated content to make the numbers come out.
  read -r RENDER_W RENDER_H GIF_W GIF_H < <(
    python3 "$WD/gen_frames.py" "--section-size=$section")
  # Loop (0 forever, -1 once -- the slides stop on their finished picture) and
  # the palette, which a section with a photograph in it needs more of.
  read -r LOOP COLORS STATS < <(
    python3 "$WD/gen_frames.py" "--section-gif=$section")

  echo "==> 1/4  generating frame SVGs  ($label, style=$STYLE)"
  if [ -n "$section" ]; then
    python3 "$WD/gen_frames.py" --style="$STYLE" --section="$section"
  else
    python3 "$WD/gen_frames.py" --style="$STYLE"
  fi

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

  echo "==> 2/4  rendering frames to PNG (parallel, ${RENDER_W}x${RENDER_H})"
  # -P0 would spawn one process per frame; cap it at the core count.
  JOBS=$(sysctl -n hw.ncpu 2>/dev/null || echo 8)
  ls "$FRAMES"/f*.svg | xargs -P "$JOBS" -I{} sh -c \
    "rsvg-convert -w $RENDER_W -h $RENDER_H -b '$PAPER' -o \"\${1%.svg}.png\" \"\$1\"" _ {}

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
  # frames, which is what matters for a mostly-static diagram. (The journey
  # uses full: see section_gif() in gen_frames.py.)
  mkdir -p "$(dirname "$out")"
  ffmpeg -hide_banner -loglevel error -y \
    -framerate "$FPS" -i "$FRAMES/f%04d.png" \
    -filter_complex "\
      scale=${GIF_W}:${GIF_H}:flags=lanczos,split[a][b];\
      [a]palettegen=max_colors=${COLORS}:stats_mode=${STATS}[p];\
      [b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" \
    -loop "$LOOP" "$out"

  echo "==> 4/4  verifying"
  magick identify -format '%n frames, %wx%h\n' "$out" | head -1
  # A GIF loops only if it carries the NETSCAPE2.0 extension. Check the file
  # itself: a wrong flag still builds a perfectly good GIF that does the wrong
  # thing, and nothing else would notice.
  if LC_ALL=C grep -q NETSCAPE2.0 "$out"; then LOOPS=1; else LOOPS=0; fi
  if [ "$LOOP" = "-1" ] && [ "$LOOPS" = "1" ]; then
    echo "FAIL: $out should play once but loops"; exit 1
  fi
  if [ "$LOOP" = "0" ] && [ "$LOOPS" = "0" ]; then
    echo "FAIL: $out should loop but plays once"; exit 1
  fi
  [ "$LOOP" = "-1" ] && echo "    plays once" || echo "    loops"
  ls -lh "$out" | awk '{print "    size: " $5}'
  echo "    done -> $out"
}

# The poster is a STILL, so it skips frames, ffmpeg and the GIF entirely.
if [ "$POSTER" = "1" ]; then
  # --poster is the whole ecosystem; --poster=<slide> is that slide's last
  # frame, e.g. --poster=infra -> sections/infra.png
  if [ -n "$POSTER_OF" ]; then
    SVG=$(python3 "$WD/gen_frames.py" --style="$STYLE" "--poster=$POSTER_OF")
  else
    SVG=$(python3 "$WD/gen_frames.py" --style="$STYLE" --poster)
  fi
  SUFFIX=""
  [ "$STYLE" = "$DEFAULT_STYLE" ] || SUFFIX="-$STYLE"
  OUT_PNG="$WD/sections/${POSTER_OF:-ecosystem}${SUFFIX}.png"
  mkdir -p "$(dirname "$OUT_PNG")"
  rsvg-convert -w 3200 -h 1800 -b "$PAPER" -o "$OUT_PNG" "$SVG"
  rm -f "$SVG"
  # A poster with the artwork missing renders clean and looks plausible, so
  # check the size the same way the frame pipeline does.
  BYTES=$(stat -f%z "$OUT_PNG")
  [ "$BYTES" -gt 400000 ] || { echo "FAIL: poster is only $BYTES bytes -- sprites are probably missing"; exit 1; }
  magick identify -format '    %wx%h\n' "$OUT_PNG"
  echo "    done -> $OUT_PNG  ($(echo "scale=1; $BYTES/1048576" | bc) MB)"
  exit 0
fi

if [ "$ALL_SECTIONS" = "1" ]; then
  SECTIONS=$(python3 "$WD/gen_frames.py" --list-sections | awk '{print $1}')
  COUNT=$(echo "$SECTIONS" | wc -l | tr -d ' ')
  echo "==> building $COUNT sections"
  for s in $SECTIONS; do
    echo
    echo "--- $s ---"
    SUFFIX=""
    [ "$STYLE" = "$DEFAULT_STYLE" ] || SUFFIX="-$STYLE"
    build_one "$WD/sections/${s}${SUFFIX}.gif" "$s"
  done
  echo
  echo "==> all sections -> $WD/sections/"
  ls -lh "$WD/sections"/*.gif | awk '{print "    " $9 "  " $5}'
elif [ -n "$SECTION" ]; then
  SUFFIX=""
  [ "$STYLE" = "$DEFAULT_STYLE" ] || SUFFIX="-$STYLE"
  build_one "$WD/sections/${SECTION}${SUFFIX}.gif" "$SECTION"
else
  build_one "$OUT" ""
fi

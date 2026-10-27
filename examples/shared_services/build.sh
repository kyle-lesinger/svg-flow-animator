#!/usr/bin/env bash
# Build the Shared Data System Capabilities walkthrough GIF.
#
#   ./build.sh                        the whole story -> shared-services.gif
#   FLOWGIF_STYLE=flat ./build.sh     clean render    -> shared-services-flat.gif
#   ./build.sh --list-sections        the chapters, and how long each runs
#   ./build.sh --section=monitor      one chapter     -> sections/monitor.gif
#   ./build.sh --all-sections         every chapter   -> sections/*.gif
#   ./build.sh --poster               one still       -> sections/overview.png
#
# Sketch is the default style. Every section shows the whole canvas; it differs
# by what moves and which frames it covers. Needs rsvg-convert and ffmpeg (and
# magick, to read the result back). The pipeline itself is gen_frames.py.
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;; esac
for bin in rsvg-convert ffmpeg magick; do
  command -v "$bin" >/dev/null || { echo "missing dependency: $bin"; exit 1; }
done
exec python3 "$D/gen_frames.py" "$@"

#!/usr/bin/env bash
# Build the review's two pictures, each as an animation and a still:
#
#   ./build.sh          review-workflow.apng/.png and review-timeline.apng/.png
#   ./build.sh flat     the clean render, saved with a -flat suffix
#
# Sketch is the default style. Needs rsvg-convert and ffmpeg.
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
  -h|--help)   sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  flat|sketch) export FLOWGIF_STYLE="$1" ;;
  "")          ;;
  *)           echo "unknown argument: $1  (try: flat)"; exit 1 ;;
esac
for bin in rsvg-convert ffmpeg; do
  command -v "$bin" >/dev/null || { echo "missing dependency: $bin"; exit 1; }
done
exec python3 "$D/review.py"

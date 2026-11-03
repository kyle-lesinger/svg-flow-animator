#!/usr/bin/env bash
# Edit the review in a browser: the timeline's dates, and the workflow's layout.
#
#   ./edit.sh             build both editors, start the preview server, open it
#   ./edit.sh --no-open   the same, without opening a browser
#
# Timeline: drag a bar to move it in time, drag an end to resize it, or type
# the dates. Save writes schedule.json.
# Workflow: grab a box by its dashed border, resize it by the corner; lines and
# group frames follow. Save to project writes overrides.json (delete it to go
# back to the automatic layout).
# Then ./build.sh. Ctrl-C stops the server.
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
  -h|--help)  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  --no-open|"") ;;
  *)          echo "unknown argument: $1  (try: --no-open)"; exit 1 ;;
esac
for bin in python3 rsvg-convert; do
  command -v "$bin" >/dev/null || { echo "missing dependency: $bin"; exit 1; }
done

python3 "$D/review.py" --editor

# A template escaping bug once shipped JavaScript that did not parse, with no
# Python-side error. Check both pages before opening them.
if command -v node >/dev/null; then
  JS="$D/.editor.js"
  for page in editor.html timeline.html; do
    python3 -c "
import re, sys
src = open(sys.argv[1]).read()
open(sys.argv[2], 'w').write(re.findall(r'<script>(.*?)</script>', src, re.S)[-1])
" "$D/$page" "$JS"
    node --check "$JS" || { rm -f "$JS"; echo "FAILED: $page JavaScript does not parse"; exit 1; }
  done
  rm -f "$JS"
fi

exec python3 "$D/review.py" --serve "$@"

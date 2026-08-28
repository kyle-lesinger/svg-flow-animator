#!/usr/bin/env bash
# Open the minimal demo's layout editor.
#
#   ./edit.sh              regenerate if anything moved, then open it
#   ./edit.sh --rebuild    regenerate unconditionally
#   ./edit.sh --print      print the path, do not open
#
# The editor is one self-contained HTML file -- both backdrops are embedded as
# base64 -- so there is no server, no port, and nothing to stop. Drag handles,
# then "Download overrides.json".
set -euo pipefail

D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$D/../.." && pwd)"
HTML="$D/out/editor.html"

FORCE=0
PRINT=0
for arg in "$@"; do
  case "$arg" in
    --rebuild)  FORCE=1 ;;
    --print)    PRINT=1 ;;
    -h|--help)  sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $arg  (try: --rebuild | --print)"; exit 1 ;;
  esac
done

command -v rsvg-convert >/dev/null || {
  echo "missing dependency: rsvg-convert  (brew install librsvg)"; exit 1; }

# --- rebuild only when needed ----------------------------------------------
# Generating means rasterising both backdrops, which is the slow part, so skip
# it when neither the demo nor the package has moved on.
NEEDS_BUILD=0
if [ "$FORCE" = 1 ] || [ ! -f "$HTML" ]; then
  NEEDS_BUILD=1
else
  while IFS= read -r src; do
    if [ "$src" -nt "$HTML" ]; then NEEDS_BUILD=1; break; fi
  done < <(find "$ROOT/svg_flow_animator" -name '*.py'; echo "$D/demo.py")
fi

if [ "$NEEDS_BUILD" = 1 ]; then
  echo "==> generating editor"
  python3 "$D/demo.py" --editor
else
  echo "==> editor is current"
fi

# --- plausibility ----------------------------------------------------------
# Both of these have shipped silently broken before: a backdrop that never got
# embedded (blank canvas, dark page showing through), and a template escaping
# bug that emitted JavaScript which does not parse (no Python-side error).
grep -q '"png": "iVBOR' "$HTML" || {
  echo "FAILED: no backdrop embedded in ${HTML#$ROOT/} -- the canvas would come up blank"
  exit 1; }

if command -v node >/dev/null; then
  JS="$D/out/.editor.js"
  python3 -c "
import re, sys
src = open(sys.argv[1]).read()
open(sys.argv[2], 'w').write(re.findall(r'<script>(.*?)</script>', src, re.S)[-1])
" "$HTML" "$JS"
  node --check "$JS" || { rm -f "$JS"; echo "FAILED: generated JavaScript does not parse"; exit 1; }
  rm -f "$JS"
  echo "==> checks OK (backdrop embedded, script parses)"
else
  echo "==> backdrop OK (install node to also syntax-check the generated script)"
fi

# --- open ------------------------------------------------------------------
if [ "$PRINT" = 1 ]; then echo "$HTML"; exit 0; fi

open "$HTML" 2>/dev/null || echo "open this: $HTML"

cat <<EOF

  editor   ${HTML#$ROOT/}

  Drag a dot. Boxes grab by their dashed border. Shift-drag snaps to 5px.
  Flat / Hand-drawn at the top swap the picture -- the geometry is shared.

  "Download overrides.json" when you are happy, then rebuild the GIF:

      python3 examples/minimal/demo.py
      python3 examples/minimal/demo.py --style=sketch
EOF

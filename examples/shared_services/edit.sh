#!/usr/bin/env bash
# Launch the layout editor with live preview.
#
#   ./edit.sh                 hand-drawn view
#   ./edit.sh flat            flat view
#   ./edit.sh --stop          stop the preview server
#   ./edit.sh --restart       fresh server and a rebuilt editor
#
# Drag a node, label, box corner, screenshot inset or connector vertex and the
# real render redraws behind it. "Save to project" writes overrides.json here;
# then ./build.sh. Safe to run repeatedly.
set -euo pipefail

D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$D/../.." && pwd)"
PORT="${FLOWGIF_PORT:-8752}"
URL="http://localhost:${PORT}/editor.html"
PIDFILE="$D/.editor.pid"
LOG="$D/.editor.log"
export FLOWGIF_PORT="$PORT"

running() { curl -sf -o /dev/null --max-time 2 "$URL" 2>/dev/null; }

stop_server() {
  if [ -f "$PIDFILE" ]; then
    kill "$(cat "$PIDFILE")" 2>/dev/null || true
    rm -f "$PIDFILE"
  fi
  pkill -f "$D/gen_frames.py --serve" 2>/dev/null || true
}

STYLE="sketch"
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --stop)      stop_server; echo "editor server stopped"; exit 0 ;;
    --restart)   FORCE=1 ;;
    flat|sketch) STYLE="$arg" ;;
    -h|--help)   sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $arg  (try: flat | sketch | --stop | --restart)"; exit 1 ;;
  esac
done

for bin in python3 rsvg-convert curl; do
  command -v "$bin" >/dev/null || { echo "missing dependency: $bin"; exit 1; }
done

# --- 1. rebuild the editor only when something it depends on changed -------
# Rendering both backdrops is the slow part, so skip it when nothing moved.
HTML="$D/editor.html"
NEEDS_BUILD=$FORCE
if [ ! -f "$HTML" ]; then
  NEEDS_BUILD=1
else
  while IFS= read -r src; do
    if [ "$src" -nt "$HTML" ]; then NEEDS_BUILD=1; break; fi
  done < <(find "$ROOT/svg_flow_animator" "$D" -maxdepth 1 \
             \( -name '*.py' -o -name 'overrides.json' \))
fi
if [ "$NEEDS_BUILD" = 1 ]; then
  echo "==> building editor"
  python3 "$D/gen_frames.py" --editor
else
  echo "==> editor is current"
fi

# --- 2. plausibility ---------------------------------------------------------
# Both have shipped broken before: a backdrop that never got embedded (blank
# canvas), and a template escaping bug emitting JavaScript that does not parse.
grep -q '"png": "iVBOR' "$HTML" || { echo "FAILED: no backdrop embedded in editor.html"; exit 1; }
if command -v node >/dev/null; then
  JS="$D/.editor.js"
  python3 -c "
import re, sys
src = open(sys.argv[1]).read()
open(sys.argv[2], 'w').write(re.findall(r'<script>(.*?)</script>', src, re.S)[-1])
" "$HTML" "$JS"
  node --check "$JS" || { rm -f "$JS"; echo "FAILED: generated JavaScript does not parse"; exit 1; }
  rm -f "$JS"
  echo "==> checks OK (backdrop embedded, script parses)"
fi

# --- 3. server -----------------------------------------------------------------
[ "$FORCE" = 1 ] && { stop_server; sleep 0.5; }
if running; then
  echo "==> server already up on :$PORT"
else
  stop_server
  echo "==> starting preview server on :$PORT"
  nohup python3 "$D/gen_frames.py" --serve >"$LOG" 2>&1 &
  echo $! >"$PIDFILE"
  for _ in $(seq 1 40); do running && break; sleep 0.25; done
  running || { echo "FAILED to start. Last lines of .editor.log:"; tail -15 "$LOG"; exit 1; }
fi

# --- 4. a server that serves HTML but cannot render is the confusing case ---
CHECK=$(curl -s --max-time 60 -X POST "http://localhost:${PORT}/render" \
        -H 'Content-Type: application/json' \
        -d "{\"overrides\":{},\"style\":\"${STYLE}\"}" \
        | python3 -c "import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    print('no response from /render'); raise SystemExit
print('ERROR ' + d['error'][:160] if d.get('error') else 'ok')" 2>/dev/null || echo "render check failed")
if [ "$CHECK" != "ok" ]; then
  echo "==> WARNING: live preview is not working: $CHECK"
else
  echo "==> live preview OK ($STYLE)"
fi

open "$URL" 2>/dev/null || echo "open this: $URL"
cat <<MSG

  editor   $URL
  view     pick Hand-drawn or Flat at the top -- the geometry is shared

  Drag anything; the preview re-renders on its own.
  Double-click a line to add a bend; right-click a bend to remove it.
  "Save to project" writes overrides.json here. Then:  ./build.sh

  Stop the server:  ./edit.sh --stop
MSG

#!/usr/bin/env bash
# Launch the layout editor, ready to use.
#
#   ./edit.sh                 flat render
#   ./edit.sh sketch          hand-drawn render
#   ./edit.sh --stop          stop the server
#   ./edit.sh --restart       force a fresh server + rebuilt backdrops
#
# It regenerates the editor if the layout has moved on, starts the preview
# server if it is not already up, waits until it genuinely answers, and opens
# the browser on the style you asked for. Safe to run repeatedly.
set -euo pipefail

D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${FLOWGIF_PORT:-8750}"
URL="http://localhost:${PORT}/editor.html"
PIDFILE="$D/.editor.pid"
LOG="$D/.editor.log"

running() { curl -sf -o /dev/null --max-time 2 "$URL" 2>/dev/null; }

stop_server() {
  if [ -f "$PIDFILE" ]; then
    kill "$(cat "$PIDFILE")" 2>/dev/null || true
    rm -f "$PIDFILE"
  fi
  pkill -f "$D/serve.py" 2>/dev/null || true
  # anything else squatting on our port
  pkill -f "serve.py" 2>/dev/null || true
}

STYLE="flat"
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --stop)     stop_server; echo "editor server stopped"; exit 0 ;;
    --restart)  FORCE=1 ;;
    flat|sketch) STYLE="$arg" ;;
    -h|--help)  sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $arg  (try: flat | sketch | --stop | --restart)"; exit 1 ;;
  esac
done

# --- 1. dependencies -------------------------------------------------------
for bin in python3 rsvg-convert; do
  command -v "$bin" >/dev/null || { echo "missing dependency: $bin"; exit 1; }
done

# --- 2. rebuild the editor only if something it depends on has changed ------
# Regenerating means rendering BOTH backdrops, which is the slow part, so it is
# worth skipping when nothing moved.
NEEDS_BUILD=0
if [ "$FORCE" = "1" ] || [ ! -f "$D/editor.html" ]; then
  NEEDS_BUILD=1
else
  for src in layout.py gen_frames.py overrides.py style.py rough.py editor.py overrides.json; do
    [ -f "$D/$src" ] || continue
    [ "$D/$src" -nt "$D/editor.html" ] && { NEEDS_BUILD=1; break; }
  done
fi

if [ "$NEEDS_BUILD" = "1" ]; then
  echo "==> rebuilding editor (layout changed)"
  python3 "$D/editor.py"
else
  echo "==> editor is current"
fi

# --- 3. server -------------------------------------------------------------
if [ "$FORCE" = "1" ]; then
  stop_server; sleep 0.5
fi

if running; then
  echo "==> server already up on :$PORT"
else
  stop_server 2>/dev/null || true
  echo "==> starting preview server on :$PORT"
  ( cd "$D" && nohup python3 serve.py >"$LOG" 2>&1 & echo $! >"$PIDFILE" )
  for _ in $(seq 1 40); do
    running && break
    sleep 0.25
  done
  if ! running; then
    echo "FAILED to start. Last lines of ${LOG#$D/}:"
    tail -15 "$LOG" 2>/dev/null
    exit 1
  fi
fi

# --- 4. confirm the renderer actually works before handing over ------------
# A server that serves HTML but cannot render is the confusing case: the page
# loads, the buttons look live, and every refresh fails. Check it up front.
CHECK=$(curl -s --max-time 60 -X POST "http://localhost:${PORT}/render" \
        -H 'Content-Type: application/json' \
        -d "{\"overrides\":{},\"style\":\"${STYLE}\"}" \
        | python3 -c "import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    print('no response from /render'); raise SystemExit
print('ERROR ' + d['error'][:120] if d.get('error') else 'ok')" 2>/dev/null || echo "render check failed")

if [ "$CHECK" != "ok" ]; then
  echo "==> WARNING: live preview is not working: $CHECK"
  echo "    The editor will still open, but Refresh will fail."
else
  echo "==> live preview OK (${STYLE})"
fi

# --- 5. open ---------------------------------------------------------------
open "${URL}?style=${STYLE}" 2>/dev/null || echo "open this: ${URL}?style=${STYLE}"

cat <<EOF

  editor   ${URL}?style=${STYLE}
  style    ${STYLE}   (switch any time with the buttons at the top)

  Drag a handle -> the preview re-renders on its own.
  "Save to project" writes overrides.json here.

  Then build:   ./build.sh                       -> disasters-data-flow.gif
                FLOWGIF_STYLE=sketch ./build.sh  -> disasters-data-flow-sketch.gif

  Stop the server:  ./edit.sh --stop
EOF

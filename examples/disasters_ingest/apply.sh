#!/usr/bin/env bash
# Pick up the overrides.json the editor just downloaded, then rebuild.
#
#   ./apply.sh            rebuild flat
#   ./apply.sh sketch     rebuild hand-drawn
#
# The browser saves downloads to ~/Downloads, but the build reads
# overrides.json from this folder. This moves it across, shows you what
# changed, and rebuilds -- so the loop is: drag, download, run this.
set -euo pipefail

D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STYLE="${1:-flat}"
DL="$HOME/Downloads"

# Most recent overrides*.json sitting in Downloads (Safari/Chrome add " (1)" etc.)
NEW="$(ls -t "$DL"/overrides*.json 2>/dev/null | head -1 || true)"

if [ -n "$NEW" ]; then
  cp "$D/overrides.json" "$D/overrides.prev.json" 2>/dev/null || true
  cp "$NEW" "$D/overrides.json"
  echo "picked up: ${NEW/#$HOME/~}"
  rm -f "$NEW"
else
  echo "no new overrides.json in ~/Downloads -- using the one already here"
fi

echo
python3 - "$D" <<'PY'
import json, os, sys
d = sys.argv[1]
cur = json.load(open(os.path.join(d, "overrides.json")))
prev_path = os.path.join(d, "overrides.prev.json")
prev = json.load(open(prev_path)) if os.path.exists(prev_path) else {}
if not cur:
    print("overrides: none (everything at its default)")
else:
    print(f"overrides in effect ({len(cur)}):")
    for k in sorted(cur):
        mark = " " if k in prev and prev[k] == cur[k] else "*"
        print(f"  {mark} {k} = {json.dumps(cur[k])}")
    gone = sorted(set(prev) - set(cur))
    if gone:
        print("  reverted to default: " + ", ".join(gone))
PY
echo

if [ "$STYLE" = "flat" ]; then
  "$D/build.sh"
else
  FLOWGIF_STYLE="$STYLE" "$D/build.sh"
fi

# keep the editor's backdrops in step with the layout you just changed
# (one file now carries both styles)
python3 "$D/editor.py" >/dev/null
echo "    editor refreshed to match"

#!/usr/bin/env bash
# Launch a layout editor. Each example has its own; this picks between them so
# ./edit.sh works from the repo root.
#
#   ./edit.sh                    minimal demo -- self-contained, needs no artwork
#   ./edit.sh disasters          the disasters_ingest diagram
#   ./edit.sh disasters sketch   hand-drawn variant
#   ./edit.sh disasters --stop   stop its preview server
#
# Anything after the example name is passed straight through.
set -euo pipefail

D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-}" in
  disasters|disasters_ingest)
    shift
    exec "$D/examples/disasters_ingest/edit.sh" "$@" ;;
  minimal)
    shift
    exec "$D/examples/minimal/edit.sh" "$@" ;;
  -h|--help)
    sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *)
    # No example named -- default to minimal and pass the flags through.
    exec "$D/examples/minimal/edit.sh" "$@" ;;
esac

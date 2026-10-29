#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$ROOT/.local-video-build"
mkdir -p "$CACHE"
if [ ! -x "$CACHE/local-video" ] || [ "$ROOT/tools/local-video/main.swift" -nt "$CACHE/local-video" ]; then
  mkdir -p "$CACHE/module-cache"
  TEMP_BIN="$CACHE/local-video.$$"
  trap 'rm -f "$TEMP_BIN"' EXIT
  swiftc -O -module-cache-path "$CACHE/module-cache" "$ROOT/tools/local-video/main.swift" -o "$TEMP_BIN"
  mv -f "$TEMP_BIN" "$CACHE/local-video"
  trap - EXIT
fi
exec "$CACHE/local-video" "$@"

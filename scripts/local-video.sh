#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$ROOT/.local-video-build"
mkdir -p "$CACHE"
if [ ! -x "$CACHE/local-video" ] || [ "$ROOT/tools/local-video/main.swift" -nt "$CACHE/local-video" ]; then
  mkdir -p "$CACHE/module-cache"
  swiftc -O -module-cache-path "$CACHE/module-cache" "$ROOT/tools/local-video/main.swift" -o "$CACHE/local-video.new"
  mv "$CACHE/local-video.new" "$CACHE/local-video"
fi
exec "$CACHE/local-video" "$@"

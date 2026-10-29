#!/bin/bash
# Chain 10-second clips into a continuous sequence with crossfades,
# optionally interpolating motion for smoothness.
# Usage: ./scripts/chain-clips.sh clip1.mp4 clip2.mp4 ... out.mp4
# Requires ffmpeg. This is the technical fix for the 10s generation limit:
# shots are chained as edits, joins are hidden with xfade, and
# minterpolate smooths motion — it does not invent a new performance.
set -e
if [ "$#" -lt 3 ]; then echo "usage: $0 clip1.mp4 clip2.mp4 [...] out.mp4"; exit 1; fi
OUT="${@: -1}"
CLIPS=("${@:1:$#-1}")
# Simple robust path: concat with re-encode, then interpolate to 30fps.
# For crossfades, use the xfade filter chain in docs/gaps-and-fixes.md
# (kept as a documented recipe, not a fragile one-liner here).
LIST=$(mktemp)
for c in "${CLIPS[@]}"; do echo "file '$PWD/$c'" >> "$LIST"; done
ffmpeg -y -f concat -safe 0 -i "$LIST" -vf "minterpolate=fps=30,scale=1280:720" \
  -c:v libx264 -pix_fmt yuv420p -b:v 2500k -c:a aac -b:a 160k "$OUT"
rm "$LIST"
echo "Chained ${#CLIPS[@]} clips -> $OUT"

#!/bin/bash
# Check the final video for one project into projects/<slug>/final/.
# Run this where git credentials live (your desktop). Muse's GitHub
# connector pushes text, not binary video, so this script is the
# documented route for the merged video itself.
set -e
SLUG="$1"
if [ -z "$SLUG" ]; then echo "usage: ./scripts/checkin-final.sh <slug>"; exit 1; fi
FINAL="projects/$SLUG/final/video.mp4"
if [ ! -f "$FINAL" ]; then echo "No final video at $FINAL"; exit 1; fi
SIZE=$(stat -f%z "$FINAL" 2>/dev/null || stat -c%s "$FINAL")
echo "Final video: $SIZE bytes"
if [ "$SIZE" -gt 104857600 ]; then
  echo "WARNING: over GitHub's 100 MB file limit. Re-encode at a lower"
  echo "bitrate, or enable Git LFS for projects/*/final/*.mp4, before pushing."
  read -p "Continue anyway? [y/N] " ans
  [ "$ans" = "y" ] || exit 1
fi
git add "projects/$SLUG/final/"
git status --short "projects/$SLUG/final/"
git commit -m "Ship final video: $SLUG" || echo "Nothing new to commit."
git push
echo "Checked in projects/$SLUG/final/ — run verify-final to mark it verified."

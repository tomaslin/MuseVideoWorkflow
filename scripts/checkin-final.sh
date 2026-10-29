#!/bin/bash
# Verify, commit and publish one completed local delivery without sweeping
# unrelated staged work into the commit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SLUG="${1:-}"
if [[ ! "$SLUG" =~ ^[A-Za-z0-9_-]+$ ]]; then echo 'usage: scripts/checkin-final.sh <project-slug>' >&2; exit 1; fi
FINAL="projects/$SLUG/final"
python3 pipeline/musevideo.py verify-final "projects/$SLUG"
python3 - "$FINAL" <<'PY'
from pathlib import Path
import sys
for file in Path(sys.argv[1]).rglob('*'):
    if file.is_file() and file.stat().st_size >= 100 * 1024 * 1024:
        raise SystemExit(f'{file} exceeds the GitHub limit. Encode a smaller web delivery before publishing.')
PY
git add "$FINAL"
if git diff --cached --quiet -- "$FINAL"; then
  echo 'Final delivery already committed.'
else
  git commit --only -m "Save verified video delivery: $SLUG" -- "$FINAL"
fi
git push origin HEAD:main
echo "Published verified delivery: $FINAL (visual review state remains as recorded)."

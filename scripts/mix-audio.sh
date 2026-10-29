#!/bin/bash
# Mix separate audio stems: voice above music, SFX looped to shot length.
# Usage: ./scripts/mix-audio.sh voice.wav music.wav sfx.wav out.wav
# Voice at full level, music ducked to 0.4, SFX at 0.6. Adjust per mix.
# For timing fixes, use atempo (within ~10%) — beyond that, re-record.
set -e
VOICE="$1"; MUSIC="$2"; SFX="$3"; OUT="$4"
if [ -z "$OUT" ]; then echo "usage: $0 voice.wav music.wav sfx.wav out.wav"; exit 1; fi
ffmpeg -y -i "$VOICE" -i "$MUSIC" -i "$SFX" -filter_complex \
  "[1:a]volume=0.4[music];[2:a]volume=0.6[sfx];[0:a][music][sfx]amix=inputs=3:duration=longest" \
  -c:a pcm_s16le "$OUT"
echo "Mixed -> $OUT (voice full, music ducked, SFX present)"

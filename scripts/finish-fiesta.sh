#!/bin/bash
# Finish a picture-locked vertical draft using the supplied music and restrained
# analog television texture. Source media and edit decisions remain untouched.
set -euo pipefail
if [ "$#" -ne 3 ]; then
  echo 'Usage: finish-fiesta.sh PICTURE.mp4 SONG.mp3 OUTPUT.mp4' >&2
  exit 2
fi
picture="$1"
song="$2"
output="$3"
if [ ! -f "$picture" ] || [ ! -f "$song" ]; then
  echo 'Picture or song is missing.' >&2
  exit 1
fi
if [ "$picture" = "$output" ] || [ "$song" = "$output" ]; then
  echo 'Output must be separate from the sources.' >&2
  exit 1
fi
# Brief chroma tracking shifts and a horizontal tape line; no rapid flashes.
texture="eq=contrast=1.05:saturation=1.20,noise=alls=3:allf=t+u,chromashift=cbh=9:crh=-9:enable='between(t,6.10,6.35)+between(t,16.10,16.35)+between(t,31.10,31.35)+between(t,46.10,46.35)',drawbox=x=0:y=850:w=iw:h=4:color=white@0.22:t=fill:enable='between(t,6.10,6.22)+between(t,31.10,31.22)'"
ffmpeg -v error -nostdin -y -i "$picture" -i "$song" \
  -map 0:v:0 -map 1:a:0 -t 60 -vf "$texture" \
  -c:v libx264 -preset veryfast -crf 19 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -af 'afade=t=out:st=58.5:d=1.5' \
  -movflags +faststart "$output"

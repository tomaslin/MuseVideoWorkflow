# Asset registry — no more "can't see it / can't hear it"

Every generated item gets a registry entry the moment it is made.
If it is not in the registry, it is not a finished asset — it is a loose
file, and loose files are how references, timestamps and review evidence
get lost.

## What is stored, per asset

In `projects/<slug>/assets/<asset_id>/`:

| File | Why it exists |
|---|---|
| `asset.json` | Identity and facts: id, shot, kind, source filename and path, SHA-256, size, source modification time, registration time, ffprobe facts (duration, dimensions, frame rate, codecs), prompt, edit timing, notes |
| `frames/frame_*.jpg` | Five stills at 0%, 25%, 50%, 75%, 100% of the duration, each labelled with its second in `asset.json` |
| `contact_sheet.jpg` | The five stills in one image. Open this image and you have *seen* the shot without playing the video. This is the answer to "I can't watch video back" |
| `waveform.png` | Audio waveform image |
| `spectrogram.png` | Audio spectrogram image (best effort) |
| `audio.json` (inside `asset.json` under `audio`) | Per-second RMS loudness, so the shape of the audio is readable as data: silences, peaks, the final chorus getting louder |
| `references/` | Reference images **copied** here with their SHA-256s, not linked from elsewhere. The reference that shaped a clip survives with the clip |
| `index.json` + `index.html` (in `assets/`) | Project-wide list, and a browsable page with every contact sheet and waveform inline |

The original media file is not duplicated (binaries are large and the
GitHub integration cannot push them). Its hash is recorded, and
`verify` re-checks it, so a replaced file is caught, not silently
trusted.

## What it does NOT do

- It does not invent a transcript. If `whisper` is not installed,
  `transcription.available` is `false` and says so. A human-supplied
  transcript (`--transcript-file`) is stored verbatim and marked
  human-supplied.
- It does not claim lip-sync, exact lyric timing, or a visual review
  nobody performed. Frames and waveforms are evidence for a reviewer;
  they are not a review.

## Commands

```sh
# One asset, with its prompt, its references, and its place in the edit
python3 pipeline/asset_registry.py register clips/s01.mp4 \
  --project-dir projects/<slug> --asset-id s01 --shot s01 \
  --prompt-file prompts/s01.txt \
  --reference references/rafa.jpg \
  --edit-start 0 --edit-end 8

# Everything already in a clips folder, skipping what is already registered
python3 pipeline/asset_registry.py scan clips/ --project-dir projects/<slug>

# Rebuild the project index (index.json + index.html)
python3 pipeline/asset_registry.py index --project-dir projects/<slug>

# Readable summary of one asset, no playback needed
python3 pipeline/asset_registry.py describe --project-dir projects/<slug> --asset-id s01

# Check every recorded hash still matches the file on disk
python3 pipeline/asset_registry.py verify --project-dir projects/<slug>
```

## Workflow rule (new, binding)

1. Generate a clip.
2. Register it immediately, with its prompt file and every reference
   image used. No batch of clips is "done" until its registry entries
   exist.
3. When a reviewer flags a clip (duplicates, crowding, a missing
   section), the flag goes into the asset's notes and into the
   project's manifest — the registry is the record, not a chat message.
4. An assembled edit is verified against the registry *and* against
   the video stream itself (`ffprobe -show_entries stream=duration`),
   never against the container duration alone, which follows the
   audio track. The 2026-10-29 vertical draft failed exactly this way:
   its container said 60.8s while its video stream was 53.79s, and the
   closing section never appeared.

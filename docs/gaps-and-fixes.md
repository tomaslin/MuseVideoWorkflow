# Gaps and technical fixes

This is the honest list of limits in the generation tools, and the
technical way around each one. Nothing here is hand-waving: each fix has
a script or a command in this repo.

## 1. The 10-second clip limit

**Limit:** each generated video clip is about 10 seconds, at most 6 per
message. A 4-minute video cannot be one generation.

**Fix — chain, don't stretch a single clip:**
- Write the story as 10-second shots (see `schemas/shot.schema.json`).
  240 seconds = 24 shots = 4 batches of 6.
- Assemble with ffmpeg concat (see `pipeline/musevideo.py assemble`).
- Hide the joins: 0.5–1 second crossfades between shots
  (`scripts/chain-clips.sh` uses `xfade`), and a match cut or sound
  bridge at sequence boundaries, so a join reads as an edit, not a glitch.
- If a single action must feel continuous across a join, generate the
  two clips from the same reference image and locked blocks, overlap
  them by 1 second, and crossfade on movement — never ask one clip to
  hold two actions.
- For smoother motion inside a clip, interpolate: `minterpolate`
  (see `chain-clips.sh`) can lift choppy motion toward a smoother frame
  rate. It cannot invent a performance that isn't in the clip, and it
  must not be used to fake a shot that failed generation — redo the shot.

## 2. Sound: video clips do not carry real dialogue or a chosen song

**Limit:** generated clips carry synthesized mood sound only. They do
not accept an audio file as input, cannot use a specific recording, and
do not guarantee lip-sync.

**Fix — separate stems, mixed in post:**
- Dialogue and narration: generated as separate voice tracks, one stem
  per speaker where possible, captioned from the audio script.
- Music: mood-described and generated/licensed separately. Never a
  specific copyrighted recording, and never presented as one.
- SFX: one or two precise sounds per shot (a door, rain, a kettle),
  not a wash of noise. Short SFX are looped with ffmpeg
  `-stream_loop` to cover a shot, and faded at shot edges
  (`scripts/mix-audio.sh`).
- Mix rule, always: spoken words above music. Use `amix` with voice
  at full level and music ducked, and check the mix on headphones and
  speakers before shipping.
- Timing: stretch or compress a voice stem with `atempo` only within
  about ±10%. Beyond that, re-record the line — stretched speech sounds
  stretched, and a viewer hears it.

## 3. Continuity drift

**Fix:** locked blocks verbatim + one reference image per character and
location + redo outliers only. See `docs/continuity.md`. No technical
trick replaces this; interpolation and color matching help at the
edges, they do not fix a character who changed face.

## 4. Determinism

**Fix:** seed = hash(idea + look + character). Prompt hash per shot is
recorded in the manifest. Same seed, same plan. What is *not*
deterministic: the generator itself. Two runs with the same prompt can
still differ, which is why every clip version is recorded and the
locked clip is chosen by a human, not assumed. Deterministic here means
reproducible planning, prompt history, and selection — not a promise
that a model will output identical pixels twice.

## 5. The final video and GitHub

**Limit:** GitHub files are capped at 100 MB, and the Muse GitHub
connector pushes text, not binary video.

**Fix:** encode the final at 720p, 2–3 Mbps (a 4-minute video lands
roughly 60–90 MB), verify with `verify-final`, and check it in with
`scripts/checkin-final.sh` where git credentials live. Over 100 MB:
re-encode lower, or enable Git LFS (see `.gitattributes`). The
manifest, EDL, and critiques always go in through the connector,
so the shipped video is never just a lone mp4 with no provenance.

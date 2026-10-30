# Local cutting room (Swift on macOS)

The Mac owns the downloaded media and finished edit. Muse owns generation.
A source generation is usually about ten seconds; an **edited shot is normally
2–4 seconds**. Keep the source handle and select the cleanest readable action.
The current Desert Beggars edit is a 24-second draft, pending footage review.

Requirements: Xcode Command Line Tools (Swift, Foundation, CryptoKit) and
`brew install ffmpeg`. The launcher compiles the Swift source once and reuses
it until the source changes. No server, API key, Python package or npm install
is required for local processing.

```bash
# Download individual MP4s or the Muse export ZIP; extract the ZIP first.
# Each filename must contain exactly one shot ID, such as s01.mp4 or
# media-generation-desert-redo-s01-0-<uuid>.mp4.
./scripts/local-video.sh import projects/desert-beggars-vampires /path/to/clips

# Resolve ambiguous names or choose a particular take explicitly.
./scripts/local-video.sh import projects/desert-beggars-vampires /path/to/take.mp4 --shot s04

# Report missing files, stale prompts and requested redos; write the next batch.
./scripts/local-video.sh status projects/desert-beggars-vampires

# The studio exports edit.json. Save it at the project root, then assemble.
./scripts/local-video.sh assemble projects/desert-beggars-vampires
./scripts/local-video.sh verify projects/desert-beggars-vampires

# Preserve a bad take, stop its use in assembly, and queue a replacement.
./scripts/local-video.sh redo projects/desert-beggars-vampires \
  --shot s04 --reason 'Knees bend at 3 seconds; rigid double-footed hops required'
```

`tools/local-video/main.swift` invokes FFmpeg directly with argument arrays,
never a shell. Intake probes every file, preserves its SHA256 and source name,
and copies it into `clips/raw/<shot>-<sha>.mp4`. Earlier takes remain available
in `manifest.json`; one take per shot is selected. Re-importing the same source
is a no-op unless its prompt or redo state changed. If Muse reports a packet hash, pass `--prompt-sha256 HASH`; the tool compares it
to the current packet and records that the reported hash matched. Otherwise it
records that an operator mapped the file to the current packet. Neither proves
what the provider consumed, or captures extra instructions outside the packet.

The renderer applies source in/out points in edit order, letterboxes mismatched
aspect ratios, normalizes frame rates and stereo 48 kHz audio, inserts silence
when needed, and creates H.264/AAC with MP4 faststart. Cuts are frame-aligned;
invalid/out-of-range trims, missing or corrupt takes, stale prompts and redos
stop the render. Unsupported transitions fail rather than silently changing
the edit. Hard cuts are intentional: no interpolated action or blanket
crossfades. Normalized trims are cached; subsequent edits encode only changed
segments, then stream-copy the video into the final container. Audio is
re-encoded once to avoid AAC priming gaps at joins.

A project lock prevents overlapping imports/renders. A prior final is copied
to `work/final-history/` before replacement. Successful output is saved in
`final/video.mp4`, `poster.jpg`, `edl.json`, and `final-manifest.json`. Verification
checks checksums, timeline continuity, exact order, current prompt hashes,
media duration, resolution and codecs. Output is **unreviewed** until a named
reviewer approves its actual pictures and sound. An automated plan score is
never permission to label footage shipping-ready.

## Film grammar and selective regeneration

A shot request must specify a subject, one playable action, framing, screen
position, action direction, timing, and an end pose suitable for the next cut.
Use an establishing wide to fix geography, a medium for a readable exchange,
a close-up for decision/reaction, and an insert for a story object. Keep the
camera on one side of the action axis. Enter/exit in compatible directions;
cut on motion, on an eyeline or on a sound cue. A wider lens and a moving camera
are choices with a purpose, not synonyms for cinematic quality.

For wuxia: stage the staff exchange side-on, keep hands/feet visible for impact,
show anticipation, contact and recoil in that order, and avoid several
simultaneous duels in one generation. Separate the human fighters' fluid weight
transfer from jiangshi rigidity. A failed limb, missing contact, bent vampire
knee or morphing talisman is a **specific redo**, not an invitation to regenerate
the entire batch. In the studio, open **Redo this shot**, record the defect and
copy the prompt to Muse. Download the replacement and import it under that shot.

## Scheduling

`watch.py` is a single, locked, idempotent tick. It tracks authoring inputs only,
updates prompt packets after validation, and evaluates affected projects. Global
pipeline/schema changes re-evaluate all projects. Failed changes remain pending
for retry; generated evaluation/prompts/media do not retrigger the watcher.
It does not claim to author new stories or call Muse from Python.

Muse's scheduled worker is separate. It must check current prompts and saved
source hashes, select at most six missing/stale/redo shots, hold a run lease,
record successful downloads, retry failures only, and idle when complete.
Never schedule one independent cron for each batch plus another worker for the
same shots. The actual schedule must be checked in Muse's task UI.

## Publishing

`python3 scripts/build-studio.py --out _site` packages real projects, shot
packets, storyboards, selected local footage (when available), and verified
final files. Preview with `python3 -m http.server 8765 --directory _site`.
The GitHub Pages workflow runs this builder on every main push. Only files
actually committed to GitHub can appear in a cloud build. Local raw clips and
caches are ignored; publish the verified final via `scripts/checkin-final.sh`.
Video files under 100 MiB use ordinary Git, not unresolved LFS pointers. Larger
masters belong in external media storage, with a smaller web delivery encoded
for the repository. The studio explicitly distinguishes missing footage from
actual video; attaching a preview file in the browser does not import it on disk.

## Review excerpts and shareable source previews

Create a draft edit under `work/`, then render it without pretending missing
shots exist:

```bash
./scripts/local-video.sh assemble projects/the-five-outcasts \
  --edit work/excerpt-edit.json --output work/excerpt-01
./scripts/local-video.sh verify projects/the-five-outcasts --output work/excerpt-01
```

An excerpt is labeled `draft-excerpt` and cannot pass final-delivery
verification. A production with a fixed edit duration must cover its planned
sources and match the current edit before the final can verify.

To show a selected source in the public studio, prepare a checksum-verified
versioned copy, then commit and push that preview and the updated manifest:

```bash
./scripts/local-video.sh publish-preview projects/the-five-outcasts --shot s05
```

Previews are available in other checkouts even though raw work clips are
ignored. They are shown with their actual `generated` or `redo` status and do
not constitute an approved final. Re-importing a rejected file with the same
checksum cannot clear a redo.

## Timed typography and held frames

A project's optional `typography.json` can describe timed `caption`, `cards`,
and `questions` cues for the full edit. The Swift renderer draws the exact text
locally and composites it after the picture cut; it records the cue file's
checksum and verification fails if those cues subsequently change. Cue timings
must be adjusted when the edit is retimed. Draft excerpts do not automatically
inherit full-timeline typography. A cut can use `freezeLastSec` to hold its last
source frame for a frame-aligned interval without changing the cut duration.
The current audio renderer preserves source audio or silence; a verified song
must be mixed separately and reviewed before calling the result a music video.

For the fiesta workprint, `scripts/finish-fiesta.sh PICTURE.mp4 SONG.mp3 OUTPUT.mp4`
adds the supplied soundtrack, a short end fade, gentle grain, saturation and a
few brief chroma-tracking glitches. It writes a separate output and leaves the
picture and music sources untouched. The finishing effect does not establish
lyric synchronization or replace picture and sound review.

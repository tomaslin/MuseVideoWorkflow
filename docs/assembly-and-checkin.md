# Assembly and check-in: from clips to a shipped video

## Assembly

`pipeline/musevideo.py assemble` does, in order:

1. Reads the project's shot list and EDL order.
2. Concatenates the locked clips in shot order (ffmpeg concat, re-encode
   to a single codec, no silent gaps unless the EDL specifies a hold).
3. Lays voice stems, then music, then SFX, with spoken words above music.
4. Burns in or sidecars captions from the audio script (sidecar `.srt`
   by default; burned-in only if the project requests it).
5. Writes `projects/<slug>/final/video.mp4` (H.264 video, AAC audio),
   `edl.json`, and `final-manifest.json`.

Encoding target: 1280x720, H.264, 2–3 Mbps video, 160 kbps AAC audio.
That keeps a 4-minute video roughly in the 60–90 MB range — see the size
rule below.

## The projects area is the deliverable

`projects/<slug>/final/` must contain, for a shipped project:

- `video.mp4` — the merged final video
- `final-manifest.json` — duration, resolution, checksum (SHA-256),
  shot order, audio stems, captions, review state
- `edl.json` — shot order, in/out points, transitions
- `poster.jpg` — a still from the final video, when available

`verify-final` checks duration against the shot list, checks every shot
is present in order, and records the checksum. A project is not `shipped`
until `verify-final` passes.

## Check-in, honestly: the binary limit

GitHub has a hard 100 MB per-file limit, and the Muse GitHub connector
pushes text files — it does not push binary video. So the final video
reaches `projects/<slug>/final/` by this route:

1. Muse pushes all text through the connector: definitions, scripts,
   manifests, EDL, critiques, and a `final/README.md` that records the
   expected final video checksum and duration.
2. The merged `video.mp4` is checked in with git where git credentials
   live (your desktop), using `scripts/checkin-final.sh`:

```bash
./scripts/checkin-final.sh <slug>
```

That script checks the file size, warns over 100 MB (and suggests
re-encoding at a lower bitrate or enabling Git LFS — see
`.gitattributes`), adds only `projects/<slug>/final/`, commits, and
pushes. It never adds `work/` or raw clips.

3. Muse then runs `verify-final` against what is in the repo, and only
   then marks the project `shipped`.

If you want the final video to live somewhere else as well (a release,
a hosted link), record that URL in `final-manifest.json` under
`distribution`. Do not replace the repo copy with a link alone: the repo
copy is the canonical shipped artifact.

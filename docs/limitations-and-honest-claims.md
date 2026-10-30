# Limitations and honest claims — read before every batch

This file is the pipeline's automatic understanding of its own limits.
It must be re-stated in audit output, not buried. If a report contradicts
it, the report is wrong.

## Generator limits (verified from past runs in this project)

- Video generation is fresh and probabilistic per clip. Repeating a
  description verbatim does NOT lock a face, a count, or a look.
- Character/scene sheets reduce drift; they do not guarantee zero drift.
  A sheet is a process guarantee (no sheet → no generation), not a pixel
  guarantee.
- Each generated clip is ~10 seconds. There is no duration parameter.
  A 30s trailer, a 60s reel, or a 150s film is always an edit of 10s sources
  cut down, never a single generated long take.
- At most 6 successful videos per user message (including delegated work).
  Longer work must be split across messages. A failed generation does not
  count as a success, and a failed beat must not be retried in the same
  turn to evade the failure.
- Dimensions vary by generation. Past verified clips include 1280×720,
  1152×768, and 672×1344 (portrait). Report dimensions as measured by
  ffprobe, never as intended.
- Sound in generated clips is synthesized from mood text. The generator
  cannot hear an mp3, cannot use a specific song as a soundtrack inside
  generation, and cannot guarantee lip-sync. Dialogue lives in the script,
  not in the clip.
- Muse cannot watch video playback or listen to audio playback. It can
  inspect still frames, contact sheets, waveforms, spectrograms, and
  ffprobe data. A clip is "generated, unreviewed" until its contact sheet
  has been inspected and a review pass recorded.

## Claims that are never made

- Never call a clip reviewed, locked, final, or shipping-ready from a tool
  success, a hash check, or a plan/evaluation score alone.
- Never call a reference approved unless the user approved it (or, for
  pipeline-internal approval, the sheet status is explicitly `approved`
  after a recorded check — and even then, the user may override it).
- Never present a search, a feed, or a single batch as exhaustive.
- Never fill a missing shot with a placeholder, a still, or a repeated
  clip in a film cut, and never present a trailer montage order as story
  order.
- Never invent a price, a link, a date, a tracking number, or a provider
  dashboard result. If it was not read back from a tool, it is unknown.

## What the guardrails can and cannot do

They can: block text-only generation, block unapproved sheets, force
verbatim prompt reuse, force a small-batch check, force a recorded review
before locking, and record failures honestly as missing.
They cannot: make the generator deterministic, lock a rig, guarantee
consistency, guarantee cinematic quality, or turn a failed generation
into a success. Iterative evaluation improves the *next* batch; it does
not retroactively authenticate a bad clip.

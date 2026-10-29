# Entire movie, from an idea: top-level steps

This is the top-level outline. Each step maps to one or more billable
chapters in `chapters/`. A chapter is small enough to price, review, and
ship on its own — and it is only done when its gate is recorded, not
when its files merely exist.

## Top-level steps

1. **Imagine it, and clear it.** Idea → brief → premise → rights ledger.
   (Chapter 01) If it cannot be cleared, it cannot ship, no matter how
   good it is.
2. **Lock the world.** Look bible, character bible, locations, recurring
   objects, reference images. (Chapter 02) Everything later copies these
   locks verbatim.
3. **Shape the tension.** Outline with a tension value per sequence:
   setup 2–3, inciting 4, rising 5–7, midpoint reversal 7–8, climax 9–10,
   resolution 2–3. Character arcs and subplots mapped against that curve.
   (Chapter 03) A flat curve here means a flat film later.
4. **Write it completely.** Full script + separate audio script, one
   visual beat per 10-second shot. (Chapter 04) No placeholders.
5. **Break it down and schedule it.** Props, costumes, locations, VFX,
   cast, batches. (Chapter 05) A 90-minute feature is 540 beats —
   estimate cost and time before committing, with
   `pipeline/movie.py estimate`.
6. **Draw it before you generate it.** Storyboard panel per shot, with
   camera, action, tension value, and sound cue; then an animatic timed
   to the script. (Chapter 06) This is the cheapest place to see if
   tension works. View panels in the studio storyboard view, hosted on
   GitHub Pages — see `docs/github-pages.md`.
7. **Cast and direct the voices.** Voice traits, performance direction,
   recording packets, ADR list. (Chapter 07)
8. **Write the color and the sound.** Color script that follows tension;
   sound script with score cues, SFX, and explicit silence. (Chapters
   08–09)
9. **Generate in batches, fight drift.** Prompt packets with locked
   blocks verbatim, reference images, takes recorded, outliers redone.
   (Chapter 10)
10. **Edit to picture lock.** Assembly → rough → fine → locked, with an
    EDL. After lock, changes are formal change requests. (Chapter 11,
    `docs/change-control.md`)
11. **Finish it.** Grade to the color script, mix to stems + M&E,
    titles/credits, captions, audio description. (Chapter 12)
12. **QC it four ways.** Technical, creative, legal, accessibility.
    No blockers open at shipping. (Chapter 13)
13. **Localize, deliver, market.** Sub/dub packages, platform encodes,
    artwork, trailer cut, metadata. (Chapter 14)
14. **Archive it with provenance.** Definitions, prompts, seeds, model
    versions, clip history, rights, QC, final manifest — restorable
    from the repo alone. (Chapter 15)

## What prevents an entire movie from being imagined and made

Not imagination. The blockers are: (a) scale — a feature is hundreds
of shots and batches, and without an estimate and a batch plan it
collapses; (b) continuity — every clip is a fresh generation, so
without locks, reference images, and a script supervisor's log it
drifts; (c) sound — clips do not carry real dialogue or a chosen song,
so without separate stems and a mix plan there is no movie, only
pictures; (d) rights and QC — without a ledger and a QC gate, a film
cannot ship legally or technically; (e) change — without picture lock
and change control, audio and color chase a moving story forever.
Each chapter above exists to remove one of those blockers, with a
gate, not just a document.

## How to use this for a short, a feature, or a series

- Short (under 10 minutes): run chapters 01–13, skip 14's per-platform
  matrix unless you need it.
- Feature (90 minutes): run all chapters, and run `estimate` first.
  Split the feature into reels/acts for generation, each reel its own
  batch plan, all under one bible.
- Series: one bible (Chapter 02) for the whole series, one chapter set
  per episode, with series-level tension (season arc) in Chapter 03
  and episode-level tension per episode.

## Chapter map

See `chapters/` — 01 Idea & Rights through 15 Archive & Provenance.
Each chapter file states its billable unit, its tension function, its
inputs, outputs, gates, cost drivers, and its storyboard mapping.

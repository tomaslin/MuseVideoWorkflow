# Production roles: a medium-budget film, assigned to this pipeline

A medium-budget film (roughly $5–20M in live-action terms) does not
have a cast of thousands, but it does have every department below,
and every department can ruin a shot alone. This document assigns
each role to a concrete artifact in MuseVideoWorkflow, with a
deliverable and a sign-off. In an AI pipeline, a "role" is a
responsibility with an artifact, not necessarily a separate person:
the same human may hold several roles, but no role may be unheld,
and no artifact may be a placeholder. If a role's artifact is
missing, the project is not ready for generation.

## How to read this table

- **Owns:** the artifact(s) the role writes and maintains.
- **Delivers:** what must be true before the next stage can start.
- **Signs off:** the gate the role controls.
- **Failure if missing:** the specific way the film breaks.

## Producers

### Producer / Executive producer
- Owns: `chapters/01-idea-and-rights.md` instantiation per project:
  rights ledger, clearance, budget, schedule.
- Delivers: a project that is legally clear to generate and ship.
- Signs off: `shipped`.
- Failure: a trailer that cannot be distributed because a look,
  a song, or a character was borrowed without clearance.

### Line producer / Unit production manager (UPM)
- Owns: `budget.json`, `schedule.md` per project (see
  `schemas/budget.schema.json` and `templates/budget`).
- Delivers: shot count, batch count, generation budget (clips
  planned at a 20% redo rate), and a schedule that fits the
  per-message generation limits (6 clips per message).
- Signs off: generation batches.
- Failure: a 90-shot plan with no batch plan, which stalls at
  message 1.

### Assistant director (1st AD)
- Owns: the shooting order in `final/edl.json` and the call
  sheet implicit in `sequences/`: which shots, in what order,
  with what background and extras.
- Delivers: a day-by-day (batch-by-batch) order that groups
  shots by location and light, not by story order alone.
- Signs off: `generating` can start.
- Failure: night shots generated in daylight batches, or a
  location used once and forgotten.

## Direction

### Director
- Owns: `treatment.md`, `script.md`, `storyboard.json`.
- Delivers: the story, the arc, and the per-shot emotional beat.
- Signs off: `shot-list-critiqued`.
- Failure: a film with pretty shots and no arc.

### Script supervisor / Continuity
- Owns: `docs/continuity.md` per project, and the locked blocks
  in every shot.
- Delivers: a continuity report per batch: what changed, what
  must not change, and which takes match.
- Signs off: every clip before it is marked locked.
- Failure: the classic failure this system was built to prevent —
  a character who changes face, outfit, or wound between shots.

## Camera and lighting

### Director of photography (DP)
- Owns: `look-bible.md`, and per shot: `lensMm`, `focus`,
  `lighting`, `cameraChoreography`.
- Delivers: a look that is a set of decisions (lens, light,
  colour, grain), not adjectives.
- Signs off: look bible and every shot's camera fields.
- Failure: a film where every shot is "cinematic" and no two
  shots share a lens.

### Camera operator / Steadicam / Crane operator
- Owns: `cameraChoreography` per shot: path, speed, start and
  end framing, height.
- Delivers: a move that can be executed in 10 seconds without
  crossing the subject's motion.
- Signs off: camera fields per shot.
- Failure: a crane move that arrives after the action, or a
  tracking shot that loses the subject at the cut.

### Gaffer
- Owns: `lighting` per shot: key, fill, practicals, time of day,
  and what changes within the shot.
- Delivers: light that is consistent across a sequence's shots.
- Signs off: lighting per shot.
- Failure: a night sequence where one shot is day-lit.

### Key grip
- Owns: rigging notes in `cameraChoreography`: what the camera
  is mounted on, and for wire-fu, what rigs the performers.
- Delivers: rigging that is safe and invisible in frame.
- Signs off: wire-fu and crane shots.
- Failure: a rig visible in frame, or a leap with no rig logic.

## Art department

### Production designer
- Owns: `departments/production-design.md`: locations, sets,
  background layers, and the world rules for built environments.
- Delivers: a background for every shot, with foreground,
  midground, and deep background named.
- Signs off: `background` per shot.
- Failure: shots floating in a void, or a caravanserai that
  changes architecture between shots.

### Art director / Set dresser
- Owns: set dressing lists per location: objects, wear, and
  what moves or breaks in a shot.
- Delivers: dressing that plants story objects (the chair, the
  letter, the second tomb door) before they pay off.
- Signs off: background dressing per shot.
- Failure: a payoff object that appears for the first time in
  its payoff shot.

### Costume designer
- Owns: `departments/costume.md`: fabrics, patch patterns, wear
  stages, and what changes after battle or weather.
- Delivers: a wardrobe bible per character, per sequence.
- Signs off: character blocks and costume continuity.
- Failure: a beggar in clean robes after a sandstorm, or a
  vampire whose robes change trim between shots.

### Makeup / Hair / Prosthetics
- Owns: `departments/makeup-sfx.md`: skin, wounds, ageing,
  jiangshi pallor, talisman placement and condition.
- Delivers: a makeup continuity chart: what a face looks like
  at the start and end of every sequence.
- Signs off: character appearance per shot.
- Failure: a talisman that is pristine in one shot and torn in
  the next without a beat that tore it.

### Special effects (SFX, on-set)
- Owns: practical effects per shot: dust, sand, talisman
  flutter, tomb doors, wire rigs, breakaways.
- Delivers: an effects beat list with timing inside the 10s.
- Signs off: effects shots.
- Failure: a dust storm that appears in one shot and vanishes
  in the next without a weather reason.

## Stunts and choreography

### Stunt coordinator
- Owns: safety and feasibility of every action beat.
- Delivers: a feasibility note per action shot: can this be
  done in 10 seconds, in one continuous move, without a cut?
- Signs off: action shots.
- Failure: a 10-second shot written with 20 seconds of action.

### Fight choreographer
- Owns: `departments/choreography.md` and per shot:
  `choreography` as numbered beats with timing.
- Delivers: beats with entry, exchange, and payoff, and a
  clear spatial layout (who is where, who moves where).
- Signs off: every fight shot.
- Failure: "they fight" — a shot with no beats, no spatial
  layout, and no payoff, which is what the old system produced.

### Wire-fu / Movement coach
- Owns: wire and movement logic: leap arcs, landing points,
  rig visibility, and what other fighters do during a leap.
- Delivers: a leap or wire move with arc, apex, and landing
  specified.
- Signs off: wire-fu shots.
- Failure: a leap with no landing, or a frame empty at the apex.

## Sound and music

### Sound designer
- Owns: `departments/sound.md`: the sound script, SFX list,
  and per-shot sound design (not just a mood word).
- Delivers: a per-shot sound list: what is heard, when, and
  at what relative level, plus planned silences.
- Signs off: sound per shot.
- Failure: constant music under every shot, or a scare with
  no silence before it.

### Composer
- Owns: `departments/music.md`: score intent per sequence,
  themes, instrumentation, and where music stops.
- Delivers: a score map, not a playlist.
- Signs off: music per sequence.
- Failure: a score that never stops, so it never means anything.

### Dialogue / ADR supervisor
- Owns: the audio script (`script.md` dialogue section):
  lines, delivery, and where dialogue is never in a video
  prompt (no lip-sync claim).
- Delivers: lines that are recordable as separate stems.
- Signs off: audio script.
- Failure: dialogue written into a video prompt, where it
  cannot be performed or synced.

## Post-production

### Editor
- Owns: `final/edl.json`, picture lock, and change control
  (`docs/change-control.md`).
- Delivers: an edit where every cut lands on a completed beat,
  not mid-action.
- Signs off: `assembled`, `picture-locked`.
- Failure: cuts that land mid-leap, mid-blow, or mid-sentence.

### VFX supervisor
- Owns: `departments/vfx.md`: what is generated, what is
  practical, and what must match between them.
- Delivers: a VFX shot list with plates and references.
- Signs off: effects-heavy shots.
- Failure: generated dust that does not match practical dust.

### Colourist
- Owns: `docs/color-script` instantiation per project and
  the grading intent in the look bible.
- Delivers: a colour script per sequence, with a show LUT
  intent, not just a palette list.
- Signs off: colour per sequence.
- Failure: a night sequence graded like day, or a trailer
  whose dusk and dawn are indistinguishable.

### Titles / Graphics
- Owns: title and credit design, added in assembly, never
  generated inside a clip.
- Delivers: titles that do not obscure the hook shot.
- Signs off: `final/`.
- Failure: a title card covering the second tomb door.

## Quality, legal, and delivery

### QC supervisor
- Owns: `pipeline/evaluate.py` reports and
  `projects/<slug>/critiques/`.
- Delivers: a report quoting both the automated score and
  the story-benchmark judgment, plus a human-watch record.
- Signs off: `verified`.
- Failure: a project shipped on an automated score alone.

### Legal / Clearance
- Owns: the rights ledger (chapter 01), blocking `shipped`
  until clear.
- Delivers: clearance for every look, character, song, and
  reference.
- Signs off: `shipped`.
- Failure: a shipped film that cannot be distributed.

### Archivist / Delivery
- Owns: `final-manifest.json`, provenance (model, seed,
  prompt hash per shot), and the archive (chapter 15).
- Delivers: a final folder that can be rebuilt and audited.
- Signs off: `shipped`.
- Failure: a final video with no manifest, no EDL, and no
  way to know which take was used.

## Roles this pipeline deliberately does not pretend to have

- Casting director: in an AI pipeline, characters are designed,
  not cast. The character sheet is the casting document, and it
  must be as specific as a casting breakdown.
- Location manager: locations are designed, not scouted. The
  production-design packet is the location document.
- Catering, transport, and other on-set logistics roles have no
  artifact in a generated pipeline and are not listed as
  placeholders. Listing them would be exactly the superficiality
  this overhaul removes.

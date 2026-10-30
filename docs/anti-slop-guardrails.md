# Anti-slop guardrails — hands-off, but not careless

Goal: a pipeline that can run without a human in the loop for a batch,
while making AI slop *harder to ship*, not just harder to notice.
Slop here means: generic-looking footage, drifted characters, exaggerated
faces, static coverage, physically impossible staging, and prompts that
paraphrase the storyboard instead of reusing it.

This is a process guardrail, not a pixel guarantee. The generator is
probabilistic and re-interprets every clip. Nothing below claims zero drift.
What it does is: block the known failure modes before generation, force a
small-scale check before a large batch, and refuse to lock a clip that has
not been reviewed.

## 1. Hard gates (generation does not start if any fails)

1. **Sheet gate** (`pipeline/sheets.py validate` + `pipeline/musevideo.py validate`):
   no sheet → no generation; sheet unapproved or hash-mismatched → no generation.
   One approved reference image per character and per scene, recorded with SHA-256.
2. **Prompt-reuse gate** (`pipeline/slop_guard.py audit`): every prompt packet
   must reuse, verbatim and in labelled sections, the look block, the scene
   description, every cast character block in cast order, the choreography
   (positioning, anticipation, contact, recoil, in order), the camera, the
   lighting/lens/focus, the motion/performance rules, the extras, and the world
   rules. A missing field is written as MISSING and fails the audit — it is
   never invented.
3. **Image-input gate**: the generation manifest (`*.generation.json`) must list
   scene image first, ship image second when the beat uses the ship, then
   character sheets in cast order. Text-only generation is a bypass, not a run.
4. **No-placeholder gate**: missing shots are never filled with black frames,
   stills, or repeated clips in a *film* cut. A trailer may end on a hard cut
   to black (a trailer convention, labelled as such in its manifest), but a
   missing story beat is never silently filled.
5. **No-retry gate**: a clip that fails with a provider integrity error is
   recorded as missing and is NOT retried, rephrased, or routed through another
   tool to evade the failure in the same turn. It waits for a new, explicit
   user direction.

## 2. Slop markers — automatic checks in `slop_guard.py`

Each prompt and each beat is checked for:

- **Exaggeration**: "wide-eyed caricature", "open-mouth screaming", "cartoon grin",
  "screaming" as a performance direction, or any face direction that asks for
  a caricature. Performance must be: restrained, natural, acted, motivated
  reactions, real weight, eye contact, closed mouth unless the beat requires
  speech (and then it is written as speech, not screaming).
- **Generic camera**: "cinematic" alone, "35mm" alone, or a static/locked shot
  for an action beat. Action beats require a moving, motivated camera:
  tracking, push-in, crane, orbit, or a named drop (overhead → eye level),
  plus layered depth (foreground / midground / background) and rim/shadow
  contrast. Static is allowed only for a labelled aftermath beat.
- **Generic choreography**: a beat with no anticipation, no contact, and no
  recoil; a beat that says "fight" or "combat" without naming who attacks,
  with what, from where, and what happens next. Every fight beat must name
  attacker, weapon, angle, contact point, and recoil, in order.
- **Physical impossibility**: water without support (standing on open water),
  mahjong or a table without a platform, dropped objects that do not fall,
  a ship that moves without wheels/hull, a shop with no floor/beam/counter
  holding weight. Water beats must name their support: large sturdy lotus
  leaves, stone stepping stones, or a stable wooden floating platform.
  Mahjong on water means: four women seated on chairs around a solid table
  on a stable wooden platform on the pond, tiles on the table, not in water.
- **Cast-count drift**: the prompt cast must equal the sequence cast, and the
  prompt must state the exact person count ("exactly four people only" for
  D05: three Dames + Mad Man). Extra people beyond cast + listed background
  performers are a negative rule, not a hope.
- **Star Wars drift**: lasers/lightsaber language without the Jin Yong frame.
  Relic/laser energy must be written as energy *on wuxia weapons*, with Jin
  Yong technique (qinggong, intricate hand work, flying attacks), not a
  lightsaber duel.
- **Trailer drift**: a trailer cut must follow trailer form, not film form:
  hook in the first 3–5 seconds, a rising shot-length curve (longer early,
  shorter later — never flat), a climax montage, and a hard cut to black or
  a labelled title/button beat. It must not reveal the ending, and it must
  not present a non-linear montage as story order.

## 3. Small-scale iterative evaluation (the hands-off loop)

Never generate a full film in one batch and hope. The loop is:

1. **Round 0 — packets only.** Run `validate` + `slop_guard audit`. Fix every
   failure before any video. Record the audit in `evaluations/`.
2. **Round 1 — small batch, 2 clips.** Generate at most 2 clips. Extract
   contact sheets (asset registry: 5 stills at 0/25/50/75/100% + contact sheet).
   Inspect the contact sheets, do not trust the tool success alone.
   Score each clip 0–5 on: consistency (face/armour/weapon vs sheet),
   cinematic composition (moving camera, layered depth, light contrast),
   performance (natural, acted, restrained faces), physical sense, and
   choreography readability (anticipation/contact/recoil visible).
   A clip below 3 on any axis is a FAIL, not a lock.
3. **Round 2 — revise only the outlier.** Change only the failed axis in the
   prompt (e.g. face restraint, camera move, support wording). Regenerate
   only that clip. Do not regenerate the whole batch. Re-score. The score
   must improve or the change is reverted and the failure is recorded.
4. **Round 3 — scale only on a pass.** Only when Round 1–2 clips pass do
   further batches start, in batches of ≤6, each batch contact-sheet-checked
   before the next starts.
5. **Lock rule.** A clip is locked only after a recorded review pass in the
   asset registry (`review` command, with notes). Hash verification alone is
   not a visual review. Unreviewed/failed clips appear in `drift-report`
   and may not be assembled into a final.

## 4. Cinematic reference (searched, not invented)

Grounded in wuxia cinema as discussed in the research for this project:
*Crouching Tiger, Hidden Dragon* (Ang Lee, cinematography Peter Pau,
choreography Yuen Woo-ping) — long takes and wide shots that respect the
choreography, framing that does not cut away from the moment of impact,
spatial coherence so the audience can follow who is where, the environment
(bamboo, water, rooftops) as an active element, and minimal, natural sound
under the action. Trailer form follows the standard compressed arc: hook
first, rising density, climax montage, hard cut to black, without revealing
the ending. These are the benchmarks the evaluation rubric in §3 scores
against; they are not a claim that generated clips equal those films.

## 5. Automatic limitation register (read before every batch)

See `docs/limitations-and-honest-claims.md`. In short, the pipeline must
re-state, in its own audit output, that: generation is fresh and
probabilistic per clip; descriptions and sheets reduce drift but do not
lock a rig; video clips are ~10s with no duration parameter; dimensions
vary (past clips: 1280×720, 1152×768, 672×1344); sound is synthesized from
mood text, not a soundtrack, and there is no lip-sync; Muse cannot watch
playback or listen to audio, only inspect frames, waveforms, and data;
and a provider failure is recorded as missing, never as a success.
Any report that omits these limits for a clip it delivers is itself a
guardrail failure.

## 6. What "hands-off" does and does not mean

Hands-off means: the user does not have to micromanage prompts, batches,
or checks — the pipeline runs validate → audit → small batch → review →
scale, and stops itself on failure. It does NOT mean: the pipeline approves
its own looks, retries provider failures, fills missing beats, or calls a
clip "final" from a tool success. Approval of a look, a reference, or a
final cut remains a human decision; the pipeline's job is to make that
decision cheap by bringing only checked, scored, labelled work to it.

## 7. Guardrails v2 — trajectories, geography, and handoffs (added 2026-10-30)

Researched limitations, and the preventions built from them:

- **Motion homogenization / default mode convergence** (DiVid, arXiv 2610.01661):
  models fall back to dominant patterns under open-ended prompts, collapsing
  especially on Motion and Camera dimensions, even when appearance varies.
  Prevention: every figure gets a *particular* trajectory and a *distinct*
  movement signature, dictated per beat (see `geography.md`), and the audit
  fails if two figures share the same trajectory text. Open-ended "fight"
  prompts are banned; only named paths are allowed.
- **No spatial memory / geography drift** (location-reference research):
  the model has no memory of a room it built two shots ago; text alone
  cannot rebuild it twice, and a location that drifts ruins every shot in it.
  Prevention: a fixed geography *record* (`geography.md`: gate south, pond
  north-centre, silk shop east, tea shop west, wagon east edge, mahjong
  platform north side), reused verbatim in every beat, with scene-sheet
  images as the record, not a fresh description.
- **Resolution / handoff failure**: generated clips tend to resolve to a
  neutral end instead of handing off naturally, so cuts feel like a series
  of finished scenes. Prevention: every source clip must end MID-ACTION
  (weapon mid-swing, foot mid-step, tendril mid-reach, body mid-turn),
  never resolved, never returned to neutral, never smiling at camera.
  Edits are cut from the middle of sources (typically seconds 2–8 of a 10s
  source), and the next beat starts from that momentum, same screen
  direction and weapon state. The audit checks for a handoff section and
  for mid-action wording in every shot.
- **Temporal consistency**: the model generates probable frames, not a
  tracked character like a film crew would; probability is not memory.
  Prevention is therefore process, not a claim: sheets + trajectories +
  geography + handoff + small-batch contact-sheet review, with failures
  recorded as missing, never smoothed over in the edit.

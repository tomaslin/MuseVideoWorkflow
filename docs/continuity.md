# Continuity: how a project stays consistent

## The problem, stated plainly

Each generated clip is a fresh generation. Nothing carries over
automatically except what is written into the prompt and what is supplied
as a reference image. Continuity is therefore a writing discipline, not a
feature to assume.

## The three locks

1. **Look lock.** One paragraph, the look bible's `lockedLookBlock`, copied
   verbatim into every prompt. It names style, palette, lighting, lens,
   grain, and aspect intent.
2. **Character lock.** One paragraph per character, `lockedDescription`,
   copied verbatim into every prompt featuring that character. It names
   age, gender presentation, hair, build, outfit, and distinguishing
   features. Outfit changes only at a sequence boundary, and the change is
   recorded in the character sheet.
3. **Reference lock.** One reference image per character and per key
   location, generated first, supplied as the input image for every clip.
   Text chaining alone is weaker than image-anchored generation.

## Rules

- Never write "same as before", "the same man", or "as in the previous
  shot" in a prompt. The generator for a later clip has no reliable memory
  of the earlier one.
- One action per shot. Two actions in one prompt is how a character
  changes gender, age, or outfit mid-clip.
- Pronouns, names, and outfit must be identical across shots in a sequence.
- If a clip drifts, redo that clip only, from the same reference image
  and the same locked blocks. Do not rewrite the whole project to fix one
  outlier, and do not quietly accept the drift.
- Record every redo in `manifest.json` under the shot, with the reason.
  A project history that hides its redos cannot be audited.

## Validation

`pipeline/musevideo.py validate` checks that every prompt packet contains
its sequence's locked look block and every featured character's locked
description, character-for-character. A packet that fails is not generated.

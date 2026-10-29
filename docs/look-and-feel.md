# Look and feel: writing a look bible

A look bible is one page that a stranger could shoot from. It is not a
mood board of adjectives.

## Required sections

1. **Style in one sentence.** For example: "Desaturated, late-light,
   locked-off realism with handheld only in the reckoning sequence."
2. **Palette.** 3–5 named colors, and a rule for how they interact.
3. **Light.** Key light, direction, time of day, and what night looks like.
4. **Lens and camera.** Preferred lens range, preferred movement, and
   what movement is forbidden (for example: no drone shots in a story
   about staying in one room).
5. **Wardrobe and world rules.** What characters wear, what rooms contain,
   what objects recur, what the weather may and may not do.
6. **Grain and finish.** Clean, grainy, soft, sharp — and how much.
7. **Locked look block.** One paragraph, copied verbatim into every
   prompt. This is the contract. If the block changes, every prompt packet
   is regenerated, and the change is recorded as a new look version.

## Versioning

A look bible has a version (`lookVersion`). Changing the look after clips
exist does not silently update old clips. Old clips are either redone
under the new look, or the project records a deliberate look change at a
sequence boundary (for example: color drains as the story darkens).
Either way, it is explicit in `state.json`.

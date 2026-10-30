# Silkpunk lotus market — fixed geography (a record, not a description)

The generator has no memory of a room it built two shots ago, and text alone
cannot rebuild it twice. So this map is fixed, reused verbatim in every beat,
and checked by the guardrail. If a beat contradicts it, the beat is wrong,
not the map.

Screen coordinates are given as left / centre / right and foreground /
midground / background, plus compass for the market itself. Camera angle
changes; the market does not move.

## Market layout (compass, fixed)

- **South — bamboo gate:** the Mad Ship enters from the south, through the
  bamboo gate, into the market square. Bamboo forest is south and
  south-west of the gate, not in the market centre.
- **Centre — lotus pond:** the pond is north-centre of the square.
  Mahjong platform: stable wooden platform on the pond, north side,
  four women seated, table on the platform, tiles on the table.
  Stepping stones cross the pond south → north. Large sturdy lotus leaves
  are on the pond surface, south and east edges, big enough to stand on.
- **East — silk shop:** silk bolts, racks, a beam across the ceiling.
  Eldest's relic sword ends up stuck in this beam in D06.
- **West — tea shop:** counter, cups, a beam. Youngest's needles scatter
  across this counter in D08.
- **East edge — wagon:** the stolen wagon waits at the east edge of the
  square, beyond the silk shop doorway, for the D10 exit.
- **Square centre:** open stone, banners overhead, market stalls around
  the edges (not in the centre), gambling tables and drinking stalls on
  the south and west edges, kids, robots, and ladies among them.

## Per-figure movement signatures (never the same move for everyone)

These are the only movement styles each figure uses. If two figures move
identically in a clip, that clip has defaulted to the generator's dominant
pattern and fails the guardrail.

- **Mad Man:** low, limping, twisted leg braced, short sudden lunges,
  never a smooth walk, never an upright hero stride. Tendrils burst, then
  recoil. He moves centre, low, erratically.
- **Eldest Dame:** long straight strides, weapon extended ahead, thrust
  lines are straight. She moves in straight lines, never in arcs or bounces.
- **Middle Dame:** fast, low, bouncing, nunchuks spinning continuously.
  She moves in arcs and leaps, leaf to leaf, never in straight strides.
- **Youngest Dame:** light, quick small steps, ribbon arcs in wide curves.
  She moves in curves, pulled and pulling, never in straight lunges.
- **Robot guard:** stiff, mechanical, straight lines, even steps, no bounce.
- **Human guard:** ordinary walk, hesitant steps, weight shifting, no
  martial flourish.

## Handoff rule (no resolving to the end of a clip)

A source clip must NOT end resolved: no return to neutral, no settling,
no smile at camera, no action completed and held. Every source clip ends
**mid-action**: weapon mid-swing, foot mid-step, tendril mid-reach, body
mid-turn, water mid-splash. The edit cut is taken from the middle of the
source (typically seconds 3–6 of a 10s source), never from the opening
settle and never from the closing resolution. The next beat in story order
starts from that momentum — same screen direction, same weapon state,
same position on the map — not from a reset. For a trailer montage, the
same rule holds per cut: each cut ends mid-action, so the trailer feels
continuous, not like a series of finished scenes.

# Critical analysis 1: The opening run (s01–s03), 2026-10-29

Run: three 10-second clips generated from the locked prompt packets for
"The Long Way Home" (see `prompts/s01.txt`–`s03.txt`). Technical facts,
verified with ffprobe: all three are 1280×720, H.264/AAC, exactly 10.0s.
File sizes differ sharply — s01 9.2 MB, s02 5.9 MB, s03 4.1 MB — which
is consistent with s01 carrying the most motion/complexity and s03 the
least, but that is an inference from bitrate, not a visual fact.

Honesty limit, stated first: Muse cannot watch these clips back. This
critique therefore judges the shot design, the prompts, and the metadata
— not the pixels. Anything below that sounds like a visual judgment is
a judgment about what the prompt asked for, and it is labelled as such.
A human watch is still required before these clips are locked; see
`docs/critical-analysis-method.md`.

## Verdict: promising, but the opening does not yet earn its 30 seconds

The locked look and character blocks are copied verbatim into all
three prompts. That is the one thing this run does well, and it matters:
without it, the man in s03 would not be the man in s01. But the run
also exposes three real flaws, and the second one is a system flaw, not
a one-off.

### 1. s02 contains three actions in one 10-second shot

Prompt: "opens a weathered garden gate and steps through, closing it
behind him." That is open + step + close. The pipeline's own rule is
one action per shot, and this prompt breaks it. In practice a generator
given three verbs in 10 seconds will either rush all three, drop the
last one, or drift mid-shot — and the gate closing, which is the
emotionally loaded beat (he is shutting himself in with the past),
is the most likely casualty. This is not a guess about this clip; it
is what the prompt structure predicts, and it is why the evaluator
flags multi-action shots.

Fix: split s02 into two shots (open + step through; then close behind
him, held for a beat), or rewrite s02 to a single action — "closes the
gate behind him" — with the opening handled by the camera move into
the gate. Do not regenerate the same prompt and hope.

### 2. The opening has no detail that matters later

The benchmark in `docs/reference-benchmarks.md` requires: one
establishing wide, one human-scale shot, one detail that matters later.
This run gives: wide (drive), wide (gate), medium (porch). It gives
place and person, but no detail. The chair, the letter, the workshop —
the objects the whole film turns on — are nowhere in the first 30
seconds. A viewer gets atmosphere, not a question. The porch pause
raises a mild question ("will he go in?"), but it is not a story
question; it is a door question.

Fix: change s03, or add a detail shot before s03, that plants one
object — for example, a close-up of his hand on the gate latch, worn
in the same way as the chair rail will be later. That single detail
turns the opening from a walk into a setup.

### 3. No reference image was used in this run

The three prompts carry the character description in text only. Text
locking is necessary but not sufficient: the generator still invents
a face, a jacket shade, a gait, three times. Continuity across these
three clips is therefore promised, not anchored. This run should be
redone once a reference image for The Man exists, with that image
passed into every clip — the same discipline used in the earlier
wuxia-cyberpunk redo, where a reference image was the anchor.

### 4. Sound is described, not verified

Each prompt carries a sound mood (wind, latch click, wood creak). The
files do contain an AAC audio stream, but Muse cannot listen to it
back, so whether the latch click is audible, whether music (if any)
drowns it, and whether the three clips' sound levels match, are all
unverified. Do not claim "sound design" for these clips; claim
"sound intent, unverified."

### What survives this critique

- The look block is genuinely locked and specific (desaturated
  late-light, cold blue-grey against warm practical lamps, no drone
  shots, no saturated colour). It is a look, not a mood word.
- The shot-size progression EWS → WS → MS is correct and disciplined.
- The durations are exact: 3 × 10s = 30s of opening, no drift, no
  missing frames at the container level.

### Actions arising

1. Split or rewrite s02 (one action).
2. Plant a later-mattering detail in the opening.
3. Generate a Man reference image and redo s01–s03 with it as input.
4. Human watch of all three clips before any of them is marked locked.
5. Do not mark this opening "shipping-ready" on the strength of the
   9.4/10 plan score alone — that score measures the plan, and the
   plan's flaws above are exactly the ones a plan score can miss
   when it only counts fields.

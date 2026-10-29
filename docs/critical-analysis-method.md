# Critical-analysis method

Every run produces three things, and a run is incomplete without all
three:

1. **Automated evaluation** (`pipeline/evaluate.py`): scores coverage,
   locked blocks, variety, action, sound fields, tension shape, and
   text continuity, 0–10 each, with findings naming exact shots.
   Overall below 7, or any blocker, means not shipping-ready.

2. **Benchmark critique** (in `projects/<slug>/critiques/`): argues,
   shot by shot, against `docs/reference-benchmarks.md` — opening,
   midpoint reversal, climax, resolution, sound, continuity. It must
   name specific fixes ("split s02", "plant the letter in s05"),
   not general improvements ("make it better").

3. **Human watch**: Muse cannot watch video back and cannot listen
   to audio back. Every clip therefore needs a human watch (and
   listen) before it is marked locked. Until that happens, a clip's
   status is "generated, unreviewed" — never "approved."

## Reporting rule

Quote both scores together: the automated score and the benchmark
judgment. A report that quotes only the automated score is
misleading, because the automated score measures fields, not story.
Example of a correct report: "Automated 9.4/10, story benchmarks
~7/10, soft midpoint, human watch still outstanding."

## What the evaluator cannot do

- Judge pixels, performance, or sound content.
- Detect two actions hidden without the word "and".
- Verify that a reference image was actually used.
- Confirm that a tension value reflects what is on screen.

These are human-watch items. The evaluator's job is to catch the
flaws that do not need eyes — missing fields, broken curves,
drifted text — so the human watch can spend its time on the flaws
that do.

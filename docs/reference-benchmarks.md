# Reference benchmarks: what a good video does

This is not a list of videos to copy. It is the standard a run is
judged against, drawn from film-school principles in `docs/`. A run
that fails these benchmarks is not "close enough" — it is a draft.

## The opening (first 3 shots, ~30 seconds)

A good opening establishes place, person, and a question, in that
order, without narration explaining them. If shot 3 has not raised a
question the viewer wants answered, the opening fails, however pretty
it is. Reference standard: one establishing wide, one human-scale
shot, one detail that matters later. Our Long Way Home run does this:
drive (place), gate (threshold), porch pause (person + question).

## The midpoint reversal (around 50%)

A good midpoint does not just raise the stakes — it reverses what the
viewer thought the story was about. In Long Way Home, the letter is
read and folded, not torn: the reversal is internal (destruction
refused), not a plot twist. A run whose midpoint is merely "more of
the same, louder" fails this benchmark.

## The climax (75–90%)

Tension 9–10, earned by earlier beats, and visual — not narrated.
A climax that needs a voiceover to explain what is happening is a
script failure, not a generation failure.

## The resolution (last 10%)

Tension falls to 2–3, the world is visibly changed, and the closing
image rhymes with the opening image without repeating it. Long Way
Home: opening drive in, closing drive out, house lit instead of dark.
A run that ends at tension 7+ has not resolved; it has stopped.

## Sound benchmark

Dialogue (when present) is intelligible above music at all times.
One or two precise SFX per shot. Silence is used at least once, on
purpose, after a revelation. A run with constant music under every
shot fails — constant music is wallpaper, not score.

## Continuity benchmark

Same character description verbatim, same outfit within a sequence,
same palette rule, same lens intent, across every shot. Any drift is
a failure, not a style choice, unless it is recorded as a deliberate
look change at a sequence boundary.

## How runs are scored

`pipeline/evaluate.py` scores coverage, locked blocks, variety,
action, sound, tension, and continuity, 0–10 each. Overall below 7,
or any blocker, means not shipping-ready. The critical analyses in
`projects/<slug>/critiques/` then go further: they argue, shot by
shot, where the plan meets or misses these benchmarks, and what the
specific fix is — not "make it better," but "split shot 12 into two
shots, because it contains two actions" or "add a close-up at shot 15,
because the climax currently has no face to land on."

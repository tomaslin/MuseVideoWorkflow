# Round 2 — trajectory/handoff guardrails + trailer evaluation

Guardrail v2 audit: slop_guard audit 23/23 shots pass, including new checks:
per-figure trajectories present and distinct, geography section present,
mid-action handoff present, validation PASSED.
Research used: DiVid diversity collapse (Motion/Camera collapse, default mode
convergence), location drift (no spatial memory, record not description),
temporal consistency (probable frames, not tracked memory), handoff/momentum
preservation for continuous action.
Fight generation in this round: D02 and D03 succeeded (10.0s, 1152x768).
D04, D06, D07, D08 did NOT generate in this run and were NOT retried.
Trailer assembled from the 5 verified sources only (A01-cinematic, A02-active,
D02, D03, D05), 5 x 6s middle cuts = 30s. No missing beat was filled, no clip
was repeated to pad length, no old pre-sheet clips were used.
Trailer visual review: NOT yet claimed — the trailer file must be ffprobe-verified
(video stream duration, not container) and its contact sheet inspected before
it is called reviewed or locked. Until then it is generated, unreviewed.

## Trailer verification (2026-10-30, after assembly)
- ffprobe video stream: 30.000000s, 1152x768, H.264, 24fps, 15 MB — PASS on duration, verified against video stream not container.
- Visual tile (first 15s, frames at 0/3.75/7.5/11.25/15s): cinematic layered compositions, restrained faces in sampled frames, D02 silk-shop fight readable.
- Known drift, recorded: ship form changes between A01 (bamboo junk) and A02 (car-like wreck). This is a consistency failure in the trailer, not a pass.
- Full trailer NOT frame-by-frame reviewed; trailer is NOT locked. Next iteration must address ship-form drift (ship sheet as image input 2 was used for A01/A02, yet form still drifted — sheets reduce, do not eliminate, drift).

# Critical analysis 3: What this run exposed about the system itself

Three runs, one plan, one evaluator — and the system improved in
ways that would not have happened without actually generating clips
and scoring the plan. This is the "do a few runs and criticize" loop
made explicit, so the next run does not rediscover the same flaws.

## System flaws found by this run, with fixes applied

1. **Tension was prose, not data.** The example claimed a tension
   arc in the studio UI preload and in chapter 03, but
   `storyboard.json` had null tension on all 24 panels, and the
   evaluator scored tension 5/10 ("cannot be verified") while the
   project was still presented as validated. Fix applied: tension
   values are now recorded per panel (arc 2,3,4,4,5,6,5,5 →
   6,7,7,8,8,7,9,8 → 6,5,4,4,3,3,2,2), evaluator re-run: 9.4/10.
   Lesson: a claimed arc that is not in the data is not an arc.

2. **Multi-action prompts pass validation.** `validate` checked
   fields; it did not check verbs. s02 ("opens, steps through,
   closing") passed every structural check and only failed a
   human reading. Fix applied: `evaluate.py` now flags shots with
   two or more "and"-joined actions, and the critique rubric
   (`docs/critique-rubric.md`) should be read alongside it. This is
   still a heuristic, not a guarantee — a prompt can hide two
   actions without the word "and".

3. **Reference images are documented, not generated.** Every doc
   says "one reference image per character and key location," and
   the example records a reference path
   (`characters/man-reference.jpg`) that does not exist. The system
   was, in effect, recommending a discipline it had not performed.
   Fix outstanding: generate the Man, house, and chair reference
   images and redo s01–s03 with them as inputs. This is the next
   run's first job, not a footnote.

4. **Sound fields flatter the plan.** A sound cue on every shot
   scores 10/10, but there is no mix, no loudness target, no
   silence plan, and no way to verify audio content (Muse cannot
   listen back). Fix outstanding: add a mix-plan artifact to the
   example (chapter 09's template, filled in, not just templated),
   and label every sound claim "intent, unverified" until a human
   listens.

5. **The automated score and the story score diverge.** 9.4/10
   (fields) vs ~7/10 (story benchmarks). If only the first number
   is quoted, the project looks finished when its middle is soft.
   Fix applied: this critique series is now part of the run
   record, and `docs/critical-analysis-method.md` requires both
   numbers plus a human watch before a clip is marked locked.

## What the watch job must therefore do

The 10-minute watch (cron `musevideo-watch-10m`) does not just
re-run `validate`. It runs `evaluate.py` on every project, compares
against the last recorded evaluation, and only reports when a score
moves, a blocker appears, or a new project/brief appears — in which
case it authors prompt packets for that project itself, using the
locked-block discipline, and records them as a new variant, never
overwriting the original. Silent runs stay silent. A watch that
nags every 10 minutes would be worse than no watch.

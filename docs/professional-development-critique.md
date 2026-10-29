# Professional film-development critique: why the system was superficial

Written from the standpoint of a medium-budget development process —
the kind where a producer, a director, a DP, a choreographer, and a
production designer all have to sign off before a shot is shootable.
Judged by that standard, MuseVideoWorkflow as it stood before this
overhaul was a treatment machine, not a production system. The
criticisms below are specific, and each one has a fix in this repo,
named at the end of its section. Nothing here is a vibe complaint.

## 1. A shot was two sentences, not a shootable unit

A professional shot list answers, at minimum: who is in frame, where
exactly, what the background is doing, what the camera does second
by second, what lens and focus do, what the light is, what each
actor's body does and in what order, what the sound is, and what
must not change from the previous shot. Our old shot answered:
size, movement, location, one action, one emotional beat, one sound
mood. That is a logline for a shot, not a shot.

Consequence, already observed: s02 of Long Way Home packed three
actions into one prompt because nothing forced the author to break
an action into beats. A choreographer would never accept "fights
across the dunes" as a beat — they would demand counts, entries,
exits, and a payoff beat, each timed.

Fix: the shot schema now requires `background`, `choreography`,
`cameraChoreography`, `lighting`, `lensMm`, `focus`, `motion`,
`extras`, `loreNotes`, and `departments` (see
`schemas/shot.schema.json`). `prompt-pack` now writes those fields
into the prompt, so a prompt is no longer a mood paragraph — it is
the shot, rendered as language. Validation fails a shot that leaves
any of them blank, and the evaluator scores them as separate
dimensions. A shot that cannot answer those questions is not a shot
yet; it is a note.

## 2. No background, so every shot floated in a void

"Desert dunes at dawn" is not a background. A background is: what
is behind the subject at 10, 50, and 200 metres; what moves in it;
what is in focus and what is not; what colour and light it carries;
and what story information it plants. Without it, a generator
invents a background per clip, and continuity — the system's
central promise — collapses in the one place the audience looks
when they are not looking at the face: behind it.

Fix: every shot now carries a `background` paragraph of at least
40 characters, naming foreground, midground, and deep background,
and what moves in each. The Desert Beggars shots, for example, now
name the caravanserai's broken arch, the lantern line, the tomb
doors, and the second tomb door that must stay visible but
unremarked in s09 — because a hook that is not in the background
of the final shot is not a hook, it is a title card.

## 3. No departments, so no one owned anything

On a medium-budget film, a shot is not "the director's shot." It
is the intersection of a dozen departments, each of which can ruin
it alone: costume can break continuity, makeup can break a
transformation, SFX can break a talisman, stunts can break a leap,
sound can break a scare. Our old system had one owner — "Muse" —
and one artifact — the prompt. That is not a production; it is a
monologue.

Fix: `docs/production-roles-medium-budget.md` assigns every role
on a medium-budget film to a concrete artifact in this pipeline,
with a deliverable and a sign-off. And every project now carries
a `departments/` folder with real packets — not "costume: robes"
but a costume packet that names fabrics, patch patterns, wear
stages, and what changes after battle. If a department packet is
missing, the project is not ready for generation, and the evaluator
says so.

## 4. Lore was a mood, not a rulebook

Jiangshi are not "vampires, but Chinese." They have rules:
they hop because rigor mortis stiffens them; they are blind and
track breath; a talisman seals them and its removal unseals them;
they do not speak, they do not run, they do not tire. A system
that does not write those rules down will break them within three
shots — a jiangshi will run, or speak, or blink, because the
prompt did not forbid it. The same applies to any invented world:
the beggar sect's hierarchy, its code, its fighting style, the
desert realms' geography. Lore that is not written is not lore;
it is decoration that the next prompt will contradict.

Fix: every project with invented or folkloric material now
carries a `lore-bible.md` that states rules as rules ("jiangshi
never run"), with a violation list, and every shot carries
`loreNotes` naming which rule it exercises. The evaluator checks
that lore notes exist; the human reviewer checks that they are
obeyed. The Desert Beggars lore bible is the worked example.

## 5. Motion was a word, not choreography

"Tracking" and "crane" are camera movements, not motion design.
A professional shoot distinguishes: camera motion (path, speed,
start and end framing), subject motion (path, speed, beats),
background motion (what moves behind, at what rate), and the
relationship between them (does the camera lead, follow, or
counter-move?). Our old system recorded one movement word per
shot and called it motion. A wire-fu leap shot cannot be generated
from "tracking" — it needs: who leaps, from where, over what, in
what arc, landing where, with the camera tracking at what height
and speed, and what the other fighters do during the leap so the
frame is not empty at the apex.

Fix: `cameraChoreography` and `choreography` are separate,
required fields. Choreography is written as numbered beats with
timing within the 10 seconds (e.g. "0–3s: entry; 3–7s: exchange;
7–10s: payoff"). A shot whose choreography has no payoff beat
in the last third is flagged by the evaluator — because a 10-second
clip that ends mid-action cannot cut to the next shot cleanly.

## 6. Placeholders were treated as progress

The system recorded reference-image paths that did not exist,
sound "moods" that were not mixes, and a tension arc that was
prose, not data. Each of those looked like completion in a file
listing and was, in fact, an IOU. A professional process has a
name for that: a placeholder that is not marked as a placeholder.
It is the most dangerous kind, because it passes validation.

Fix: the new rule, enforced by the evaluator and by
`docs/critical-analysis-method.md`, is that a path to a file that
does not exist, a sound field with no mix plan, or a department
with no packet is reported as a blocker, not as a field present.
Reference images for Desert Beggars are still to be generated —
and they are now listed as open blockers in the project's state,
not as paths pretending to be assets.

## 7. Prompts were not reflective of the production

A prompt that does not contain the background, the choreography,
the lens, the light, and the lore rule cannot produce a clip that
respects them. The old prompts were reflective of the look bible
and the character sheet only. Everything else in the production
was invisible to the generator, so the generator was blamed for
decisions it was never given.

Fix: `prompt-pack` now renders every required shot field into the
prompt, in a fixed order: look block, character blocks, background,
camera choreography, choreography beats, lighting, lens and focus,
motion, lore notes, sound. A prompt is now long, and that is
correct — a shootable prompt is long. Brevity in a prompt is not
elegance; it is missing information.

## Bottom line

The system is now judged by a single test: could a department head
pick up a shot packet and know exactly what their department must
deliver, without asking the director a question? Before this
overhaul, the answer was no for every shot. After it, for the
Desert Beggars trailer, the answer is yes for all nine — and the
evaluator, not a claim in prose, is what verifies it.

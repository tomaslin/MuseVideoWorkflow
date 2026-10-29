# MuseVideoWorkflow

The [cutting room](https://tomaslin.github.io/MuseVideoWorkflow/) shows real
projects, short-shot trims, footage availability and selective redo requests.
The [storyboard](https://tomaslin.github.io/MuseVideoWorkflow/storyboard.html)
uses the same repository data.

**Local processing on macOS:** [Swift video intake, edit, redo and verification](docs/local-video.md).
Download Muse clips, import them, then stitch the strongest 2–4 seconds per shot:

```bash
./scripts/local-video.sh import projects/desert-beggars-vampires /path/to/clips
./scripts/local-video.sh assemble projects/desert-beggars-vampires
./scripts/local-video.sh verify projects/desert-beggars-vampires
```

Earlier takes are preserved, normalized trims are cached, and `edit.json` records
exact source in-points and durations. A requested redo blocks that take until a
replacement is imported. Actual footage review is separate from a plan score.

A reusable video definition and asset pipeline. One project definition
drives everything: brief, treatment, script, look bible, characters, sequences,
shots, prompts, generated clips, critiques, assembly, and a final merged video.

The pipeline is driven by Muse, not by a loose prompt. You give a video idea,
Muse works it out, criticizes it, improves it, generates it in batches, and
lands a finished video in the project's `final/` folder.

## Develop the whole production from a story

Muse authors `production.json` using `schemas/production.schema.json`. Then:

```bash
python3 pipeline/develop.py projects/the-five-outcasts/production.json
python3 pipeline/musevideo.py validate projects/the-five-outcasts
./scripts/local-video.sh cards projects/the-five-outcasts
```

This produces the treatment, timed script, cast, world/look bibles, department
packets, full shots, concise prompts, storyboard, reference/audio plans, batches,
resource budget, schedule, provenance ledger, responsibilities, edit and EDL.
[The Five Outcasts](projects/the-five-outcasts/brief.md) is the current worked
production: exactly 60 seconds, two Heavenly Heroes, five shunned outcasts,
two mutually destroyed squadrons raised as a defensive cordon, and a woman
who left the city freely. [Workflow details](docs/story-production.md).

## The trigger keyword

```
video idea: <your idea>
```

Example:

```
video idea: a 4-minute music video in the mood of Johnny Cash's Hurt
```

That exact prefix, `video idea:`, is the end-to-end trigger. See
[TRIGGER.md](TRIGGER.md) for what happens on every run, and what Muse asks
you before it starts spending generation batches.

A mood reference is a mood reference. It is never a copy of a song, its
lyrics, or its recording. Every script, lyric, and voice line produced here
is original, unless you supply your own licensed material.

## Top-level steps: idea to a whole movie

See `docs/entire-movie-pipeline.md`. In one line: clear it → lock the
world → shape the tension → write it completely → break it down and
schedule it → storyboard it (panel per shot, tension curve) → cast and
direct voices → write color and sound → generate in batches, fighting
drift → edit to picture lock → finish (grade, mix, titles, captions) →
QC four ways → localize, deliver, market → archive with provenance.

Each step is a small billable chapter in `chapters/` (01 Idea & Rights
through 15 Archive & Provenance). Each chapter states its billable
unit, its tension function, inputs, outputs, gates, cost drivers, and
how it maps to a storyboard.

## The cutting room on GitHub Pages

The studio packages real project files with `scripts/build-studio.py`. It shows
shot footage when available, recorded tension, production notes, short-shot
trim controls and an individual redo request for every shot. Download `edit.json`
and save it in the project before running local assembly. Copy redo prompts to
Muse, then import the downloaded replacements. Browser changes stay local until
exported; the static site does not call the generation API itself.

`.github/workflows/pages.yml` builds and deploys `_site/` on main pushes. A cloud
build can only include committed media; raw local takes remain ignored. See
[GitHub Pages](docs/github-pages.md) and [local video processing](docs/local-video.md).

## How a project flows

```
brief -> treatment -> script -> look bible -> characters
  -> sequences -> shots -> prompt packets -> clips (batches of <=6)
  -> critique -> redo outliers -> audio (voices / music mood / SFX)
  -> assembly -> final merged video -> check-in to projects/<slug>/final/
```

Execution state lives in each project, never in chat memory:

- `projects/<slug>/state.json` — current stage, gates passed, open critiques
- `projects/<slug>/manifest.json` — every asset, its source, prompt, and status
- `projects/<slug>/final/final-manifest.json` — the shipped video, its
  duration, checksum, edit decision list, and review state

State machine and gates: [pipeline/state-machine.md](pipeline/state-machine.md)

## Specifying down to sequence level

A project is defined in layers, each one checkable before the next starts:

1. **Project** — title, duration, aspect intent, mood, audience, language.
   Schema: `schemas/project.schema.json`
2. **Look bible** — one locked visual style, palette, lighting, lens, grain,
   wardrobe, and world rules, repeated verbatim in every prompt.
   Schema: `schemas/look-bible.schema.json`
3. **Characters** — one locked description per character, plus a reference
   image that anchors every clip featuring them.
   Schema: `schemas/character.schema.json`
4. **Sequences** — narrative blocks (for example: arrival, reckoning,
   release). Each sequence has an intent, an emotional turn, and a shot count.
   Schema: `schemas/sequence.schema.json`
5. **Shots** — one action, one camera move, one location, one emotional beat.
   A shot is normally one ~10-second clip, because that is the generation
   unit. A 4-minute video is therefore 24 shots, in 4 batches of 6.
   Schema: `schemas/shot.schema.json`
6. **Clips** — a generated file per shot, with its prompt, snapshot, and
   critique status. Schema: `schemas/clip.schema.json`

Templates for all of these are in `templates/`.

## Consistency: the one rule that matters

Every clip is a fresh generation, so continuity drifts unless it is forced.
The pipeline forces it three ways:

- The locked character description and locked look block are copied
  **verbatim** into every prompt. Never "same as before".
- One reference image per character and per key location anchors every clip.
- `pipeline/musevideo.py validate` fails a prompt packet if a locked block
  is missing, paraphrased, or if a shot tries to do two actions at once.

See [docs/continuity.md](docs/continuity.md).

## The film language in the definitions

Shot and sequence definitions use the vocabulary of film school, screenwriting,
and cinematography books, not free-form adjectives. That vocabulary is
written down, so a "slow push-in" or a "match cut" means the same thing in
every project:

- [docs/language-screenwriting.md](docs/language-screenwriting.md) — beats,
  subtext, reversal, cliffhanger, dialogue that carries meaning
- [docs/language-cinematography.md](docs/language-cinematography.md) — shot
  sizes, lenses, movement, lighting, color, composition, depth
- [docs/language-film-school.md](docs/language-film-school.md) — mise-en-scene,
  editing grammar, sound design, the Kuleshov effect, rhythm and silence

## Critique, honestly

Muse cannot watch a generated video back. So the critique loop in this repo
is explicit about what is automated and what is human:

- Automated: locked-block checks, duration math, shot coverage, dialogue /
  audio separation, duplicate or placeholder text, state-gate checks.
- Human (you, or a named reviewer): watch each batch, name the outlier
  clip numbers, and Muse redoes only those clips from the same reference
  image and locked description.
- Script and shot-plan critique is done by Muse before generation, against
  [docs/critique-rubric.md](docs/critique-rubric.md), and the critiques are
  saved in the project — they are part of the asset history, not chat.

No clip, and no final video, is marked `locked` until its critiques are
resolved or explicitly waived by you.

## Where the finished video lives

**`projects/<slug>/final/` is the deliverable area.**

- `video.mp4` — the merged final video (H.264, AAC)
- `final-manifest.json` — duration, resolution, checksum, shot order, audio
  stems, captions, review state
- `edl.json` — the edit decision list: shot order, in/out, transitions
- `poster.jpg` — a still from the final video (when available)

See [docs/assembly-and-checkin.md](docs/assembly-and-checkin.md) for the
encoding target, the GitHub 100 MB file limit, and the check-in route.
Important, stated plainly: the Muse GitHub connector pushes text files, not
binary video. The final `video.mp4` is checked into `projects/<slug>/final/`
by `scripts/checkin-final.sh`, which verifies the saved media and manifest before
committing and pushing it. Web MP4s below 100 MiB use ordinary Git blobs. The text
definitions, manifests, EDL, and critiques go in through Muse directly.

## Quickstart

```bash
# 1. Start a project from a video idea (see TRIGGER.md)
python3 pipeline/musevideo.py init --slug long-way-home \
  --title "The Long Way Home" --duration-sec 240

# 2. Validate a project definition before generating anything
python3 pipeline/musevideo.py validate projects/long-way-home

# 3. Split the script into 10-second beats and build prompt packets
python3 pipeline/musevideo.py beats projects/long-way-home
python3 pipeline/musevideo.py prompt-pack projects/long-way-home

# 4. After clips exist, build the edit decision list and assemble
python3 pipeline/musevideo.py edl projects/long-way-home
python3 pipeline/musevideo.py assemble projects/long-way-home
python3 pipeline/musevideo.py verify-final projects/long-way-home
```

## Repo layout

```
docs/        film language, look, continuity, critique, assembly/check-in
schemas/     JSON schemas for every definition and state file
templates/   blank project, look bible, character, sequence, shot, prompt packet
pipeline/    musevideo.py (validate, beats, prompt-pack, edl, assemble, verify)
             state-machine.md (stages and gates)
projects/    one folder per video; final/ is the shipped deliverable
scripts/     checkin-final.sh (desktop git check-in for the final video)
examples/    see projects/_example-long-way-home (a worked 4-minute definition)
```

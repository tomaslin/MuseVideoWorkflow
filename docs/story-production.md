# A story brief drives the whole production

Muse develops the creative work from the user's story. The local tool checks
and expands that work into files; it never substitutes random seeded shots
or generic descriptions for writing.

1. Give Muse a story brief and constraints: cast, stakes, reveal, duration,
   tone, intended cut lengths, and required or forbidden events.
2. Muse writes a `production.json` following `schemas/production.schema.json`.
   The worked example is `projects/the-five-outcasts/production.json`.
   It contains actual treatment/script/bibles/department packets and a complete
   shot plan. Each source has one playable action, timed beats, staging,
   screen direction, camera, light, focus, sound, and a motivated editorial use.
3. Materialize and validate:

```bash
python3 pipeline/develop.py projects/the-five-outcasts/production.json
python3 pipeline/musevideo.py validate projects/the-five-outcasts
./scripts/local-video.sh cards projects/the-five-outcasts
./scripts/local-video.sh status projects/the-five-outcasts
```

For an existing production use `--refresh`. Changed generated artifacts are
versioned under `variants/production-<hash>/`; previous clip provenance is
preserved. Unchanged productions are a no-op. Changed prompt hashes mark
selected takes stale when the local tool checks them. A fresh story should
use a new slug so old characters and footage cannot silently leak into it.

The output includes brief, treatment, timed script, cast, world and look bibles,
seven department packets, sequence files with full shots, concise generation
prompts plus detailed production packets, storyboard with recorded tension,
exact edit and EDL, batches, queue, reference-image plan, audio cue plan,
resource budget, intended schedule, rights/provenance ledger, role assignments,
manifest, execution state and development critique. `artifact-index.json`
records the production SHA256 and generated file set.

Generation is separate from development. Muse should first make and retain
character references, then generate up to six missing/stale/redo sources per
message using the same references. A task card's existence is not proof that
it ran. Each batch must supply the actual downloaded files and prompt hashes.
Import, cut, critique and redo specific takes. A final file is only saved once
all sources actually used in the edit exist. Assembly and delivery are described
in `docs/local-video.md`.

Ten-second source handles are independent from editorial duration. The Five
Outcasts has 18 generated sources, 55 seconds of selected picture, and a five
second title created locally in Swift with AppKit. There are 20 edit entries
because its final tableau uses two contiguous three-second handles. The total
is exactly 60 seconds. No generation credit is spent on typography.

The studio can copy a development request for a new story. It is a static
working surface; paste that request into Muse. It does not secretly invoke a
model, store API keys in Pages, or claim that exported browser edits have
already changed files on your Mac.

## Multiple projects and a shared production slate

Open `workspace.html` for the production dashboard. Every project has its own
folder, cast, source manifest, reference images, prompt versions, trims, render
cache and history. Browser edits are keyed by project slug. Archived projects
and reference examples are excluded from the active slate and generation queue.
New development requests create a new slug and preserve all existing work.

```bash
python3 pipeline/workspace.py list
python3 pipeline/workspace.py queue --claim
# Send the returned batch to Muse. It contains at most six clips TOTAL.
# Import the actual downloads into the named project folders, then:
python3 pipeline/workspace.py complete <lease-id>
# Or identify specific failures (they receive a two-minute backoff):
python3 pipeline/workspace.py complete <lease-id> --failed project-slug:s04
```

The planner rotates between active projects, prioritizes redos within a project,
checks prompt and media hashes, excludes local titles, and reserves claimed jobs
with an expiring lease. Another claim cannot select a reserved shot. A completed
lease requires the exact claimed prompt and a locally imported verified file,
not merely a provider's textual success message. The planner does not invoke
Muse itself. A single Muse scheduler can consume these batches across projects;
do not leave old per-project workers generating the same sources. Local renders
may run for separate projects concurrently; each has its own file lock.

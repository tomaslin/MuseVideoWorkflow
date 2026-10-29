# Projects

One folder per video. The folder is the project: definitions, critiques,
and — in `final/` — the shipped video.

## Rules

- `projects/<slug>/` holds the definition: `project.json`, `state.json`,
  `brief.md`, `treatment.md`, `script.md`, `look-bible.md`,
  `characters.md`, `sequences/sequence-*.json`, `prompts/`, `critiques/`.
- `projects/<slug>/final/` is the only deliverable area. It must contain
  `video.mp4`, `final-manifest.json`, and `edl.json` for a shipped project,
  plus `poster.jpg` when available.
- `projects/<slug>/work/` and raw clips are ignored by git. They are
  working files, not the shipped video.
- Folders starting with `_` are examples or templates, not projects to ship.

## Example

`_example-long-way-home/` is a worked 4-minute definition in the shape
described in `TRIGGER.md`: an original story about a weathered man
returning to an empty house, in a desaturated late-light mood. It is a
definition only — its `final/` folder holds a placeholder README until
a run generates, assembles, and checks in its video.

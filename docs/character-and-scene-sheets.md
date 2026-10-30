# Character and scene sheets — generation is sheet-based, automatically

Aim: no drift. Method: generation is based off character and scene
sheets, and the pipeline enforces that instead of merely recommending it.

## The sheets

One manifest per project: `projects/<slug>/sheets/sheets.json`.

- **Character sheet** (one per character, never two): id, name, one
  verbatim locked description, exactly one reference image, its SHA-256,
  and a status. The image is copied into `sheets/characters/`.
- **Scene sheet** (one per key location): same shape, in `sheets/scenes/`.
- **Status** is `missing` (declared, no image), `pending` (image present,
  not yet approved), or `approved` (a human has looked at the image and
  accepted it as the look). Only `approved` sheets may be used.

## The automatic gate

`pipeline/sheets.py validate` and `pipeline/musevideo.py validate`
both fail, with the missing items listed, if:

- there is no sheets manifest,
- any sheet image is missing or its hash no longer matches,
- any sheet is not `approved`,
- any shot features a character with no sheet, or names a scene
  sheet that does not exist.

**Generation must not start until validation passes.** A text-only
generation run is a bypass, not a pipeline run.

## How generation must use the sheets

`pipeline/musevideo.py prompt-pack` writes, next to every prompt text
file, a `<shotId>.generation.json` file:

```json
{
  "shotId": "s04",
  "cast": ["eldest-dame", "middle-dame", "youngest-dame"],
  "sceneSheetId": "silk-colony",
  "input_images_in_order": [
    "sheets/scenes/silk-colony.jpg",
    "sheets/characters/eldest-dame.jpg",
    "sheets/characters/middle-dame.jpg",
    "sheets/characters/youngest-dame.jpg"
  ],
  "prompt_file": "s04.txt"
}
```

The generation step supplies those images as inputs **in that order,
before the text prompt**: scene sheet first, then character sheets in
cast order. It does not generate from text alone when sheets exist.
It also keeps cast counts small — the generator holds a count far
better at two or three people than at three fighters plus a crowd —
and it never writes "same as before" in a prompt.

## The review gate (the second half of "no drift")

Sheets reduce drift; they do not remove it, because generation is
probabilistic even from images. So a clip is not locked by being
generated, or by passing a hash check. It is locked only by a recorded
review pass:

```sh
# After inspecting the asset's contact sheet (assets/<id>/contact_sheet.jpg)
python3 pipeline/asset_registry.py review --project-dir projects/<slug> \
  --asset-id s04 --status pass --notes "3 dames, mad man, counts correct"
python3 pipeline/asset_registry.py review --project-dir projects/<slug> \
  --asset-id s04 --status fail --notes "4th woman at 0s; redo from sheets"
python3 pipeline/asset_registry.py drift-report --project-dir projects/<slug>
```

`drift-report` lists every asset that is unreviewed or failed — i.e.
every clip that may **not** be locked or assembled. A failed review
sends that shot back to generation, from the same approved sheets;
it does not rewrite the project, and it does not quietly accept drift.

## Commands

```sh
python3 pipeline/sheets.py init --project-dir projects/<slug>
python3 pipeline/sheets.py add-character --project-dir projects/<slug> \
  --id mad-man --name "The Mad Man" --description-file characters/mad-man.txt \
  --image references/mad-man.jpg
python3 pipeline/sheets.py add-scene --project-dir projects/<slug> \
  --id silk-colony --name "Silk colony" --description "..." \
  --image references/silk-colony.jpg
python3 pipeline/sheets.py approve --project-dir projects/<slug> --kind character --id mad-man
python3 pipeline/sheets.py validate --project-dir projects/<slug>
python3 pipeline/sheets.py list --project-dir projects/<slug>
```

## Honest limit

This system guarantees process, not pixels: no sheet, no generation;
no approved sheet, no generation; no review pass, no locked clip.
It cannot guarantee zero drift, because no text or image input makes
the generator deterministic. What it does guarantee is that drift is
caught at the gate, named in a report, and fixed by redoing only the
outlier from the same approved sheets — instead of being discovered
after delivery, as happened with the silkpunk S3/S4 clips (fourth woman
at 0s, crowded opening, the mad man's look shifting between clips).

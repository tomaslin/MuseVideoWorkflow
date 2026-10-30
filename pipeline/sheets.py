#!/usr/bin/env python3
"""Character and scene sheets — the drift gate.

The old continuity rule already said "one reference image per character
and per key location, supplied as the input image for every clip" — but
nothing enforced it. Text prompts were generated and clips were made
without any sheet at all, and drift (extra people, changed faces, a
fourth woman where three were scripted) slipped through.

This module makes that rule automatic and blocking:

  * A project has one sheets manifest: projects/<slug>/sheets/sheets.json
  * Every character has exactly one sheet: an id, a verbatim locked
    description, and exactly one reference image file (copied into
    sheets/characters/ or recorded by path, with its SHA-256).
  * Every key scene/location has exactly one sheet the same way.
  * A sheet has a status: "pending" (image exists, not yet approved),
    "approved" (a human has looked at it and accepted it as the look),
    or "missing" (declared but no image file yet).
  * `validate` FAILS — exit code 1, with the missing items listed — if:
      - there is no sheets manifest at all,
      - any character or scene sheet is missing its image file,
      - any sheet's recorded hash no longer matches the file on disk,
      - any sheet is not "approved".
    Generation must not start until validate passes. A text-only
    generation run is therefore not a pipeline run at all; it is a
    bypass, and the pipeline now says so instead of silently allowing it.
  * `prompt-pack` output (in musevideo.py) lists, for every shot, the
    sheet images to supply as inputs, in this order: scene sheet first,
    then character sheets in cast order, then the text prompt. The
    generation step must pass those images as inputs; it must not
    generate from text alone when sheets exist.

Honest limit, written here so it cannot be mistaken for a guarantee:
even image-anchored generation is probabilistic. Sheets minimise drift
and make it visible and gateable; they do not make the generator
deterministic, and they do not lock a face pixel-for-pixel. What this
module guarantees is process, not pixels: no sheet, no generation;
no approved sheet, no generation; no review pass, no locked clip.
That is enforced in asset_registry.py's review gate.

Usage:
    python3 pipeline/sheets.py init --project-dir projects/<slug>
    python3 pipeline/sheets.py add-character --project-dir projects/<slug> \
        --id mad-man --name "The Mad Man" --description-file characters/mad-man.txt \
        --image references/mad-man.jpg
    python3 pipeline/sheets.py add-scene --project-dir projects/<slug> \
        --id silk-colony --name "Silk colony" --description "A beautiful silk colony..." \
        --image references/silk-colony.jpg
    python3 pipeline/sheets.py approve --project-dir projects/<slug> --kind character --id mad-man
    python3 pipeline/sheets.py validate --project-dir projects/<slug>
    python3 pipeline/sheets.py list --project-dir projects/<slug>
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys


def manifest_path(project_dir):
    return os.path.join(project_dir, "sheets", "sheets.json")


def load(project_dir):
    p = manifest_path(project_dir)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def save(project_dir, data):
    os.makedirs(os.path.join(project_dir, "sheets"), exist_ok=True)
    with open(manifest_path(project_dir), "w") as f:
        json.dump(data, f, indent=2)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def cmd_init(args):
    os.makedirs(os.path.join(args.project_dir, "sheets", "characters"), exist_ok=True)
    os.makedirs(os.path.join(args.project_dir, "sheets", "scenes"), exist_ok=True)
    if not os.path.exists(manifest_path(args.project_dir)):
        save(args.project_dir, {"characters": [], "scenes": [], "created_at_utc": now()})
    print(json.dumps({"sheets_manifest": manifest_path(args.project_dir)}, indent=2))


def _add(args, kind):
    data = load(args.project_dir)
    if data is None:
        raise SystemExit("no sheets manifest; run: sheets.py init --project-dir <dir>")
    key = "characters" if kind == "character" else "scenes"
    if any(e["id"] == args.id for e in data[key]):
        raise SystemExit(f"{kind} sheet already exists: {args.id}")
    desc = None
    if args.description_file:
        with open(args.description_file) as f:
            desc = f.read().strip()
    elif args.description:
        desc = args.description
    entry = {"id": args.id, "name": args.name, "description": desc,
             "image_path": None, "sha256": None, "size_bytes": None,
             "status": "missing", "created_at_utc": now()}
    if args.image:
        if not os.path.exists(args.image):
            raise SystemExit(f"image file not found: {args.image}")
        dest_dir = os.path.join(args.project_dir, "sheets", key)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, os.path.basename(args.image))
        shutil.copyfile(args.image, dest)
        entry.update({"image_path": f"sheets/{key}/{os.path.basename(args.image)}",
                      "sha256": sha256_of(dest), "size_bytes": os.path.getsize(dest),
                      "status": "pending"})
    data[key].append(entry)
    save(args.project_dir, data)
    print(json.dumps(entry, indent=2))


def cmd_validate(args):
    data = load(args.project_dir)
    problems = []
    if data is None:
        problems.append("no sheets manifest (sheets/sheets.json); run sheets.py init first")
        print(json.dumps({"valid": False, "problems": problems}, indent=2))
        sys.exit(1)
    for kind, key in (("character", "characters"), ("scene", "scenes")):
        for e in data[key]:
            if not e.get("image_path"):
                problems.append(f"{kind} {e['id']}: missing image")
                continue
            full = os.path.join(args.project_dir, e["image_path"])
            if not os.path.exists(full):
                problems.append(f"{kind} {e['id']}: image file not found: {e['image_path']}")
            elif e.get("sha256") and sha256_of(full) != e["sha256"]:
                problems.append(f"{kind} {e['id']}: image hash mismatch (sheet image changed)")
            if e.get("status") != "approved":
                problems.append(f"{kind} {e['id']}: sheet status is '{e.get('status')}', not 'approved'")
    valid = not problems
    print(json.dumps({"valid": valid, "problems": problems}, indent=2))
    sys.exit(0 if valid else 1)


def cmd_approve(args):
    data = load(args.project_dir)
    if data is None:
        raise SystemExit("no sheets manifest")
    key = "characters" if args.kind == "character" else "scenes"
    for e in data[key]:
        if e["id"] == args.id:
            if not e.get("image_path") or not os.path.exists(os.path.join(args.project_dir, e["image_path"])):
                raise SystemExit(f"cannot approve {args.id}: no image file present")
            e["status"] = "approved"
            e["approved_at_utc"] = now()
            save(args.project_dir, data)
            print(json.dumps(e, indent=2))
            return
    raise SystemExit(f"no such {args.kind} sheet: {args.id}")


def main():
    ap = argparse.ArgumentParser(description="Character and scene sheets")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "validate", "list"):
        p = sub.add_parser(name)
        p.add_argument("--project-dir", required=True)
    for kind in ("character", "scene"):
        p = sub.add_parser(f"add-{kind}")
        p.add_argument("--project-dir", required=True)
        p.add_argument("--id", required=True)
        p.add_argument("--name", required=True)
        p.add_argument("--description")
        p.add_argument("--description-file")
        p.add_argument("--image")
    p = sub.add_parser("approve")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--kind", choices=["character", "scene"], required=True)
    p.add_argument("--id", required=True)
    args = ap.parse_args()
    if args.cmd == "init":
        cmd_init(args)
    elif args.cmd == "validate":
        cmd_validate(args)
    elif args.cmd == "list":
        data = load(args.project_dir)
        print(json.dumps(data, indent=2) if data else "no sheets manifest")
    elif args.cmd.startswith("add-"):
        _add(args, "character" if args.cmd == "add-character" else "scene")
    elif args.cmd == "approve":
        cmd_approve(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""MuseVideoWorkflow pipeline CLI. Standard library only.

Commands:
  init <slug> --title T --duration-sec N   create a project skeleton
  validate <project-dir>                   check sequences/shots/locked blocks
  beats <project-dir>                      show beat count and batch plan
  prompt-pack <project-dir>                assemble prompt packets from shots
  edl <project-dir>                        build edit decision list from shots
  assemble <project-dir>                   concat locked clips with ffmpeg
  verify-final <project-dir>               check final video vs manifest/EDL

Definitions are the contract. This script never invents a clip, a voice,
or a review approval; it only checks, packs, and assembles what is recorded.
"""
import argparse, hashlib, json, math, os, subprocess, sys

PLACEHOLDERS = ("[insert", "[tbd]", "[todo]", "[...]")
STATES = ["brief", "treatment", "script", "script-critiqued",
          "look-and-characters", "shot-list", "shot-list-critiqued",
          "generating", "clips-critiqued", "audio", "assembled",
          "checked-in", "verified", "shipped"]


def load(path):
    with open(path) as f:
        return json.load(f)


def project_files(d):
    seqs = []
    for name in sorted(os.listdir(d)):
        if name.startswith("sequence") and name.endswith(".json"):
            seqs.append(load(os.path.join(d, name)))
    return seqs


def all_shots(d):
    shots = []
    for s in project_files(d):
        shots.extend(s.get("shots", []))
    seq_dir = os.path.join(d, "sequences")
    if os.path.isdir(seq_dir):
        for name in sorted(os.listdir(seq_dir)):
            if name.endswith(".json"):
                shots.extend(load(os.path.join(seq_dir, name)).get("shots", []))
    return sorted(shots, key=lambda x: x.get("order", 0))


def cmd_init(args):
    d = os.path.join("projects", args.slug)
    os.makedirs(os.path.join(d, "sequences"), exist_ok=True)
    os.makedirs(os.path.join(d, "prompts"), exist_ok=True)
    os.makedirs(os.path.join(d, "critiques"), exist_ok=True)
    os.makedirs(os.path.join(d, "final"), exist_ok=True)
    os.makedirs(os.path.join(d, "assets"), exist_ok=True)
    os.makedirs(os.path.join(d, "references"), exist_ok=True)
    os.makedirs(os.path.join(d, "sheets", "characters"), exist_ok=True)
    os.makedirs(os.path.join(d, "sheets", "scenes"), exist_ok=True)
    sheets_path = os.path.join(d, "sheets", "sheets.json")
    if not os.path.exists(sheets_path):
        with open(sheets_path, "w") as f:
            json.dump({"characters": [], "scenes": []}, f, indent=2)
    proj = {"slug": args.slug, "title": args.title,
            "durationSec": args.duration_sec, "mood": "",
            "language": "en", "lookVersion": "v1", "state": "brief"}
    with open(os.path.join(d, "project.json"), "w") as f:
        json.dump(proj, f, indent=2)
    with open(os.path.join(d, "state.json"), "w") as f:
        json.dump({"slug": args.slug, "state": "brief",
                   "history": [], "openCritiques": []}, f, indent=2)
    print(f"Created {d} — next: brief, treatment, script, look bible, characters.")


def cmd_validate(args):
    d = args.project
    errors = []
    seqs = project_files(d) or []
    # also accept sequences/ subfolder
    seq_dir = os.path.join(d, "sequences")
    if os.path.isdir(seq_dir):
        for name in sorted(os.listdir(seq_dir)):
            if name.endswith(".json"):
                seqs.append(load(os.path.join(seq_dir, name)))
    shots = []
    for s in seqs:
        shots.extend(s.get("shots", []))
    if not shots:
        errors.append("no shots found (sequence*.json with shots)")
    for sh in shots:
        for field in ("shotId", "sequenceId", "size", "movement", "action",
                      "location", "emotionalBeat", "soundMood", "lockedLookBlock",
                      "background", "choreography", "cameraChoreography",
                      "lighting", "lensMm", "focus", "motion", "extras",
                      "loreNotes"):
            if not sh.get(field):
                errors.append(f"{sh.get('shotId', '?')}: missing {field}")
        for field in ("background", "choreography", "cameraChoreography",
                      "lighting", "motion", "loreNotes"):
            if sh.get(field) and len(str(sh[field])) < 40:
                errors.append(f"{sh['shotId']}: {field} too short to be shootable (<40 chars)")
        if sh.get("lockedLookBlock") and len(sh["lockedLookBlock"]) < 40:
            errors.append(f"{sh['shotId']}: locked look block looks truncated")
        for ch in sh.get("characters", []):
            blocks = sh.get("lockedCharacterBlocks", {})
            if ch not in blocks or len(blocks[ch]) < 40:
                errors.append(f"{sh['shotId']}: missing locked block for {ch}")
        text = json.dumps(sh).lower()
        if any(p in text for p in PLACEHOLDERS):
            errors.append(f"{sh['shotId']}: placeholder text present")
    proj_path = os.path.join(d, "project.json")
    if os.path.exists(proj_path):
        proj = load(proj_path)
        expected = math.ceil(proj.get("durationSec", 0) / 10)
        if shots and len(shots) != expected:
            errors.append(f"shot count {len(shots)} != duration beats {expected} "
                          f"({proj['durationSec']}s / 10s)")
    # SHEET GATE (docs/character-and-scene-sheets.md): text locks alone do
    # not prevent drift. A shot may not be generated unless every character
    # it features has an approved character sheet with a present, hash-
    # matching image, and its scene sheet (if it names one) is approved too.
    # A missing sheets manifest is a failure, not a warning.
    sheets_path = os.path.join(d, "sheets", "sheets.json")
    if not os.path.exists(sheets_path):
        errors.append("no sheets manifest (sheets/sheets.json) — generation is blocked; "
                      "run pipeline/sheets.py init, add sheets, and approve them")
    else:
        sheets = load(sheets_path)
        char_sheets = {e["id"]: e for e in sheets.get("characters", [])}
        scene_sheets = {e["id"]: e for e in sheets.get("scenes", [])}
        for kind, table in (("character", char_sheets), ("scene", scene_sheets)):
            for e in table.values():
                if e.get("status") != "approved":
                    errors.append(f"sheet {kind} {e['id']}: status is "
                                  f"'{e.get('status')}', not 'approved'")
                if not e.get("image_path") or not os.path.exists(os.path.join(d, e["image_path"])):
                    errors.append(f"sheet {kind} {e['id']}: image file missing")
                elif e.get("sha256") and hashlib.sha256(
                        open(os.path.join(d, e["image_path"]), "rb").read()).hexdigest() != e["sha256"]:
                    errors.append(f"sheet {kind} {e['id']}: image hash mismatch")
        for sh in shots:
            for ch in sh.get("characters", []):
                if ch not in char_sheets:
                    errors.append(f"{sh['shotId']}: no character sheet for '{ch}' — "
                                  "generation is blocked until the sheet exists and is approved")
            if sh.get("sceneSheetId") and sh["sceneSheetId"] not in scene_sheets:
                errors.append(f"{sh['shotId']}: no scene sheet for '{sh['sceneSheetId']}'")
    if errors:
        print("VALIDATION FAILED")
        for e in errors:
            print(" -", e)
        return 1
    print(f"VALIDATION PASSED: {len(seqs)} sequences, {len(shots)} shots")
    return 0


def cmd_beats(args):
    d = args.project
    proj = load(os.path.join(d, "project.json"))
    dur = proj["durationSec"]
    beats = math.ceil(dur / 10)
    batches = math.ceil(beats / 6)
    print(f"{proj['title']}: {dur}s -> {beats} x 10s shots -> "
          f"{batches} batches of <=6 clips")
    for i in range(batches):
        lo = i * 6 + 1
        hi = min((i + 1) * 6, beats)
        print(f"  batch {i+1}: shots s{lo:02d}–s{hi:02d}")


def cmd_prompt_pack(args):
    d = args.project
    out = os.path.join(d, "prompts")
    os.makedirs(out, exist_ok=True)
    for sh in all_shots(d):
        parts = [sh["lockedLookBlock"]]
        for ch in sh.get("characters", []):
            parts.append(sh.get("lockedCharacterBlocks", {}).get(ch, ""))
        parts.append(f"Shot: {sh['size']}, {sh['movement']}, {sh['location']}. "
                     f"Action: {sh['action']} Emotional beat: {sh['emotionalBeat']} "
                     f"Sound mood: {sh['soundMood']}.")
        # Robust fields: a prompt must reflect the whole production, not
        # just look + characters. Each field is rendered verbatim when
        # present, in a fixed order, so prompts are auditable against shots.
        if sh.get("background"):
            parts.append(f"Background: {sh['background']}")
        if sh.get("cameraChoreography"):
            parts.append(f"Camera choreography: {sh['cameraChoreography']}")
        if sh.get("choreography"):
            parts.append(f"Choreography: {sh['choreography']}")
        if sh.get("lighting"):
            parts.append(f"Lighting: {sh['lighting']}")
        if sh.get("lensMm"):
            parts.append(f"Lens: {sh['lensMm']}mm, focus: {sh.get('focus', '')}.")
        if sh.get("motion"):
            parts.append(f"Motion: {sh['motion']}")
        if sh.get("extras"):
            parts.append(f"Background performers: {sh['extras']}")
        if sh.get("loreNotes"):
            parts.append(f"World rules: {sh['loreNotes']}")
        if sh.get("departments"):
            dept = "; ".join(f"{k}: {v}" for k, v in sh["departments"].items())
            parts.append(f"Department notes: {dept}")
        prompt = " ".join(p for p in parts if p)
        with open(os.path.join(out, f"{sh['shotId']}.txt"), "w") as f:
            f.write(prompt + "\n")
        # Generation manifest: the generation step MUST supply these images
        # as inputs, in this order, before the text prompt. Scene sheet
        # first, then character sheets in cast order. Text-only generation
        # is a bypass of the sheet gate, not a pipeline run.
        sheets_path = os.path.join(d, "sheets", "sheets.json")
        input_images = []
        if os.path.exists(sheets_path):
            sheets = load(sheets_path)
            char_sheets = {e["id"]: e for e in sheets.get("characters", [])}
            scene_sheets = {e["id"]: e for e in sheets.get("scenes", [])}
            if sh.get("sceneSheetId") in scene_sheets:
                input_images.append(scene_sheets[sh["sceneSheetId"]]["image_path"])
            for ch in sh.get("characters", []):
                if ch in char_sheets and char_sheets[ch].get("image_path"):
                    input_images.append(char_sheets[ch]["image_path"])
        with open(os.path.join(out, f"{sh['shotId']}.generation.json"), "w") as f:
            json.dump({"shotId": sh["shotId"], "cast": sh.get("characters", []),
                       "sceneSheetId": sh.get("sceneSheetId"),
                       "input_images_in_order": input_images,
                       "prompt_file": f"{sh['shotId']}.txt",
                       "rule": "Supply input_images_in_order as image inputs, in order, "
                               "before the text prompt. Do not generate from text alone."},
                      f, indent=2)
    print(f"Wrote prompt packets to {out}")


def cmd_edl(args):
    d = args.project
    shots = all_shots(d)
    edl, t = [], 0
    for sh in shots:
        dur = sh.get("durationSec", 10)
        edl.append({"shotId": sh["shotId"], "sequenceId": sh["sequenceId"],
                    "startSec": t, "endSec": t + dur,
                    "transitionIn": sh.get("transitionIn", "cut")})
        t += dur
    with open(os.path.join(d, "final", "edl.json"), "w") as f:
        json.dump({"shotOrder": [e["shotId"] for e in edl],
                   "entries": edl, "totalSec": t}, f, indent=2)
    print(f"Wrote EDL: {len(edl)} shots, {t}s total")


def cmd_assemble(args):
    d = args.project
    clips_dir = os.path.join(d, "clips")
    shots = all_shots(d)
    concat = os.path.join(d, "final", "concat.txt")
    with open(concat, "w") as f:
        for sh in shots:
            clip = os.path.join(clips_dir, f"{sh['shotId']}.mp4")
            if not os.path.exists(clip):
                print(f"Missing locked clip: {clip}")
                return 1
            f.write(f"file '{os.path.abspath(clip)}'\n")
    out = os.path.join(d, "final", "video.mp4")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat,
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", "scale=1280:720",
           "-b:v", "2500k", "-c:a", "aac", "-b:a", "160k", out]
    subprocess.run(cmd, check=True)
    print(f"Assembled {out} — run verify-final after recording its checksum.")


def cmd_verify_final(args):
    d = args.project
    final = os.path.join(d, "final")
    manifest_path = os.path.join(final, "final-manifest.json")
    video = os.path.join(final, "video.mp4")
    if not os.path.exists(video):
        print("No final video in final/ — not checked in yet.")
        return 1
    if not os.path.exists(manifest_path):
        print("No final-manifest.json — assemble/check-in step incomplete.")
        return 1
    man = load(manifest_path)
    h = hashlib.sha256()
    with open(video, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    ok = h.hexdigest() == man.get("sha256")
    size = os.path.getsize(video)
    print(f"video: {size} bytes ({size/1e6:.1f} MB), sha256 match: {ok}")
    if size > 100 * 1024 * 1024:
        print("WARNING: over GitHub 100 MB file limit — re-encode or use LFS.")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("init"); a.add_argument("slug")
    a.add_argument("--title", required=True); a.add_argument("--duration-sec", type=int, required=True)
    for name in ("validate", "beats", "prompt-pack", "edl", "assemble", "verify-final"):
        s = sub.add_parser(name); s.add_argument("project")
    args = p.parse_args()
    fn = {"init": cmd_init, "validate": cmd_validate, "beats": cmd_beats,
          "prompt-pack": cmd_prompt_pack, "edl": cmd_edl,
          "assemble": cmd_assemble, "verify-final": cmd_verify_final}[args.cmd]
    sys.exit(fn(args))


if __name__ == "__main__":
    main()

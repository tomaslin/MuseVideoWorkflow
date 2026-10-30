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
        expected = proj.get("sourceShotCount", math.ceil(proj.get("durationSec", 0) / 10))
        if shots and len(shots) != expected:
            errors.append(f"shot count {len(shots)} != duration beats {expected} "
                          f"(declared source count / delivery duration {proj['durationSec']}s)")
        edit_path = os.path.join(d, "edit.json")
        if proj.get("timingMode") == "edited":
            if not os.path.exists(edit_path):
                errors.append("edited project requires edit.json")
            else:
                cuts = load(edit_path).get("shots", [])
                if abs(sum(c.get("durationSec", 0) for c in cuts) - proj["durationSec"]) > .001:
                    errors.append("edit duration does not match project deliverable")
                if set(c.get("shotId") for c in cuts) != set(s.get("shotId") for s in shots):
                    errors.append("edit coverage does not match source shots")
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
    actual = [s for s in all_shots(d) if s.get("kind", "generated") == "generated"]
    beats = len(actual) if actual else math.ceil(dur / 10)
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
        if sh.get("generationBrief"):
            if sh.get("kind") == "title":
                prompt = "LOCAL TITLE CARD\n" + sh["titleText"] + "\n"
            else:
                blocks = [sh["lockedLookBlock"], *sh.get("lockedCharacterBlocks", {}).values()]
                prompt = "\n\n".join(blocks + [sh["generationBrief"], "One continuous take. No internal edits, montage, titles or captions. Keep the usable action within the specified source handle; hold the end pose."]) + "\n"
            with open(os.path.join(out, f"{sh['shotId']}.txt"), "w") as f:
                f.write(prompt)
            continue
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
    print(f"Wrote prompt packets to {out}")


def cmd_edl(args):
    from pathlib import Path
    d = Path(args.project)
    shots = all_shots(d)
    by_id = {s["shotId"]: s for s in shots}
    edit = load(d / "edit.json") if (d / "edit.json").exists() else {}
    cuts = edit.get("shots") or [{"shotId": s["shotId"], "inSec": 0, "durationSec": s.get("durationSec", 10)} for s in shots]
    entries, cursor = [], 0
    for cut in cuts:
        sh = by_id[cut["shotId"]]
        duration = cut["durationSec"]
        freeze = cut.get("freezeLastSec", 0)
        if duration <= 0 or cut.get("inSec", 0) < 0 or freeze < 0 or freeze >= duration:
            raise ValueError("Invalid edit trim")
        entries.append({"shotId": sh["shotId"], "sequenceId": sh["sequenceId"],
                        "sourceInSec": cut.get("inSec", 0), "sourceOutSec": cut.get("inSec", 0) + duration - freeze, "freezeLastSec": freeze,
                        "startSec": cursor, "endSec": cursor + duration,
                        "transitionIn": cut.get("transitionIn", "cut")})
        cursor += duration
    (d / "final").mkdir(exist_ok=True)
    with (d / "final" / "edl.json").open("w") as stream:
        json.dump({"shotOrder": [e["shotId"] for e in entries], "entries": entries, "totalSec": cursor, "status": "planned-not-rendered"}, stream, indent=2)
    print(f"Wrote planned EDL: {len(entries)} cuts, {cursor}s total")


def cmd_assemble(args):
    # Use the same tested local renderer for both entry points.
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    return subprocess.run([str(root / "scripts/local-video.sh"), "assemble", args.project]).returncode


def verify_final(d):
    """Verify saved media, exact timeline, current prompts and manifest."""
    from pathlib import Path
    final = Path(d) / "final"
    video = final / "video.mp4"
    man = load(final / "final-manifest.json")
    edl = load(final / "edl.json")
    if man.get("file") != "video.mp4":
        raise ValueError("final-manifest file must be video.mp4")
    if man.get("scope") == "draft-excerpt":
        raise ValueError("an excerpt cannot be delivered as the complete project")
    h = hashlib.sha256()
    with video.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    if h.hexdigest() != man.get("sha256"):
        raise ValueError("final SHA256 mismatch")
    entries = edl.get("entries", [])
    order = [e["shotId"] for e in entries]
    if not entries or order != edl.get("shotOrder") or order != man.get("shotOrder"):
        raise ValueError("EDL/manifest shot order mismatch")
    known = {s["shotId"] for s in all_shots(d)}
    project = load(Path(d) / "project.json")
    if project.get("timingMode") == "edited":
        if abs(edl.get("totalSec", 0) - project["durationSec"]) > .001:
            raise ValueError("final edit does not match requested project duration")
        if set(order) != known:
            raise ValueError("final edit does not cover all planned sources")
        edit = load(Path(d) / "edit.json").get("shots", [])
        if len(edit) != len(entries) or any(
            cut.get("shotId") != entry.get("shotId") or
            abs(cut.get("inSec", 0) - entry.get("sourceInSec", -1)) > .001 or
            abs(cut.get("freezeLastSec", 0) - entry.get("freezeLastSec", 0)) > .001 or
            abs(cut.get("durationSec", 0) - (entry["endSec"] - entry["startSec"])) > .001
            for cut, entry in zip(edit, entries)
        ):
            raise ValueError("final EDL does not match the current edit")
    cursor = 0
    for entry in entries:
        if entry["shotId"] not in known:
            raise ValueError("EDL references unknown shot")
        if abs(entry["startSec"] - cursor) > .001 or entry["endSec"] <= cursor:
            raise ValueError("EDL has a gap, overlap or invalid duration")
        if "promptSha256" in entry:
            packet = Path(d) / "prompts" / (entry["shotId"] + ".txt")
            if hashlib.sha256(packet.read_bytes()).hexdigest() != entry["promptSha256"]:
                raise ValueError("final uses stale prompt: " + entry["shotId"])
        cursor = entry["endSec"]
    if abs(cursor - edl["totalSec"]) > .001:
        raise ValueError("EDL duration mismatch")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)], capture_output=True, text=True, check=True)
    media = json.loads(probe.stdout)
    duration = float(media["format"]["duration"])
    streams = media["streams"]
    v = next(s for s in streams if s["codec_type"] == "video")
    audio = next((s for s in streams if s["codec_type"] == "audio"), {})
    if v["codec_name"] != "h264" or audio.get("codec_name") != "aac":
        raise ValueError("final must contain H.264 video and AAC audio")
    if abs(duration - cursor) > .12 or abs(duration - man["durationSec"]) > .12:
        raise ValueError("media duration does not match EDL/manifest")
    if man.get("resolution") != f"{v['width']}x{v['height']}":
        raise ValueError("media resolution does not match manifest")
    return man


def cmd_verify_final(args):
    try:
        man = verify_final(args.project)
        print(f"VERIFIED: checksum, timeline, duration, H.264/AAC, resolution; review={man.get('reviewState', 'unreviewed')}")
        return 0
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError) as exc:
        print(f"FINAL VERIFICATION FAILED: {exc}")
        return 1


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

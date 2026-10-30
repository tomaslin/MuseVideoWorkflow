#!/usr/bin/env python3
"""Anti-slop guardrail audit for MuseVideoWorkflow.

Checks, deterministically from text, that prompt packets seriously reuse
the storyboard and do not carry the known slop markers. This is a text
audit, not a visual review: it can block bad prompts, it cannot prove a
clip looks human-made. Visual review remains the asset-registry `review`
step (contact-sheet inspection).

Usage:
  python3 pipeline/slop_guard.py audit <project-dir>
  python3 pipeline/slop_guard.py audit <project-dir> --out <report.json>

Exit 0 = all shots pass. Exit 1 = at least one failure (listed).
"""
import json
import os
import re
import sys

BANNED_FACE = [
    "wide-eyed caricature", "open-mouth screaming", "cartoon grin",
    "screaming", "exaggerated",
]
# "screaming" as a noun in a sound mood is different from a face direction;
# the check below only flags it in character/performance sections, handled
# by checking the full prompt for the face phrases first.
BANNED_FACE_PHRASES = ["wide-eyed caricature", "open-mouth screaming", "cartoon grin"]
GENERIC_CAMERA = ["cinematic", "35mm"]
STATIC_FORBIDDEN = ["static", "locked shot", "still shot"]


def load_json(path):
    with open(path) as f:
        return json.load(f)


def all_shots(project):
    shots = []
    seq_dir = os.path.join(project, "sequences")
    if not os.path.isdir(seq_dir):
        return shots
    for name in sorted(os.listdir(seq_dir)):
        if not name.endswith(".json"):
            continue
        data = load_json(os.path.join(seq_dir, name))
        shots.extend(data.get("shots", []))
    return shots


def audit(project):
    shots = all_shots(project)
    prompts_dir = os.path.join(project, "prompts")
    failures = []
    passes = []
    for sh in shots:
        sid = sh["shotId"]
        problems = []
        prompt_path = os.path.join(prompts_dir, f"{sid}.txt")
        if not os.path.exists(prompt_path):
            problems.append("no prompt packet")
            failures.append((sid, problems))
            continue
        prompt = open(prompt_path).read()
        # 1. Verbatim reuse: look, characters, choreography, camera
        if sh.get("lockedLookBlock") and sh["lockedLookBlock"][:80] not in prompt:
            problems.append("look block not reused verbatim")
        for ch in sh.get("characters", []):
            block = sh.get("lockedCharacterBlocks", {}).get(ch, "")
            if block and block[:60] not in prompt:
                problems.append(f"character block not reused verbatim: {ch}")
        if sh.get("choreography") and sh["choreography"][:60] not in prompt:
            problems.append("choreography not reused verbatim")
        if sh.get("cameraChoreography") and sh["cameraChoreography"][:40] not in prompt:
            problems.append("camera not reused verbatim")
        # 2. Structured sections (new prompt-pack format)
        for section in ["LOOK", "CHARACTERS", "CHOREOGRAPHY", "CAMERA", "GEOGRAPHY", "TRAJECTORIES", "HANDOFF", "NEGATIVE", "EDIT"]:
            if section not in prompt:
                problems.append(f"missing labelled section: {section}")
        if "MISSING" in prompt:
            problems.append("prompt contains MISSING field")
        # 3. Slop markers: exaggerated faces — only when ASKED for, not
        # when negated ("no wide-eyed caricature", "never ... cartoon grin").
        # A negative rule naming the failure is not the failure, so the
        # NEGATIVE section itself is excluded from this check.
        face_prompt = prompt.split("## NEGATIVE")[0]
        for phrase in BANNED_FACE_PHRASES:
            for m in re.finditer(re.escape(phrase.lower()), face_prompt.lower()):
                ctx = face_prompt[max(0, m.start() - 40):m.start()].lower()
                if not any(neg in ctx for neg in ["no ", "not ", "never", "without ", "no exaggerated"]):
                    problems.append(f"banned face phrase requested: {phrase}")
                    break
        # "wide-eyed" alone is allowed only if negated ("not wide-eyed")
        for m in re.finditer(r"wide-eyed", prompt.lower()):
            ctx = prompt[max(0, m.start() - 30):m.start()].lower()
            if "not " not in ctx and "no " not in ctx:
                problems.append("unnegated wide-eyed face direction")
                break
        # 4. Cinematic: action beats need moving camera, not static
        is_action = sh.get("sequenceId") in ("seq-combat", "seq-explosion") or sh["shotId"].startswith("D")
        cam = (sh.get("cameraChoreography", "") + " " + sh.get("motion", "")).lower()
        if is_action and not any(k in cam for k in ["tracking", "push-in", "crane", "orbit", "dropping", "moving"]):
            problems.append("action beat without a moving camera")
        if is_action and "still shot" in cam and "never" not in cam and "not a still" not in cam:
            problems.append("action beat framed as a still shot")
        # 5. Physical sense: water beats need support wording
        loc = sh.get("location", "").lower()
        if "pond" in loc or "water" in loc:
            text = (sh.get("choreography", "") + " " + sh.get("background", "") + " " + sh.get("extras", "")).lower()
            if not any(k in text for k in ["stepping stone", "lotus leaf", "floating platform", "stable wooden platform"]):
                problems.append("water beat without physical support wording")
        # 6. Cast count: prompt must name the cast
        for ch in sh.get("characters", []):
            if ch not in prompt:
                problems.append(f"cast member missing from prompt: {ch}")
        # 7. Trajectories + handoff: each cast member must have a distinct trajectory
        traj = sh.get("trajectories", {})
        for ch in sh.get("characters", []):
            if ch not in traj or not traj[ch]:
                problems.append(f"no dictated trajectory for: {ch}")
        traj_vals = list(traj.values())
        if len(traj_vals) != len(set(traj_vals)):
            problems.append("two figures share the same trajectory text")
        if "mid-action" not in sh.get("handoff", "").lower() and "mid-" not in sh.get("handoff", "").lower():
            problems.append("no mid-action handoff rule")
        if sh.get("handoff") and ("resolved" in sh.get("handoff", "").lower() and "not resolved" not in sh.get("handoff", "").lower()):
            problems.append("handoff allows resolution")
        # 8. Trailer beats (if a trailer manifest exists, checked separately)
        if problems:
            failures.append((sid, problems))
        else:
            passes.append(sid)
    return {"project": project, "shots_checked": len(shots),
            "passes": passes, "failures": [{"shotId": s, "problems": p} for s, p in failures]}


def main(argv):
    if len(argv) < 3 or argv[1] != "audit":
        print("usage: slop_guard.py audit <project-dir> [--out <report.json>]")
        return 2
    project = argv[2]
    result = audit(project)
    out = None
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
        with open(out, "w") as f:
            json.dump(result, f, indent=2)
    print(f"Slop audit: {len(result['passes'])}/{result['shots_checked']} shots pass")
    print("Limitations (see docs/limitations-and-honest-claims.md): generation is "
          "probabilistic; sheets reduce drift but do not lock a rig; this text audit "
          "cannot prove a clip looks human-made — visual review is still required.")
    for fail in result["failures"]:
        print(f"  FAIL {fail['shotId']}: " + "; ".join(fail["problems"]))
    if out:
        print(f"Report: {out}")
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

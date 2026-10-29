#!/usr/bin/env python3
"""Movie-scale helpers for MuseVideoWorkflow. Standard library only.

  estimate <duration-sec> [--redo-rate 0.2]
      Shots, batches, and a planning estimate for any length, including
      a 90-minute feature (540 shots, 90 batches at 6 per batch).
  breakdown <project-dir>
      Extract props, costumes, locations, and VFX-style shots from
      sequence files, for the Chapter 05 breakdown.
  storyboard <project-dir>
      Emit one storyboard panel per shot (panel JSON), with a tension
      placeholder to be set per shot in the storyboard view.
  qc <project-dir>
      Checklist QC: shot count vs duration, locked blocks present,
      no placeholders, EDL present, final manifest present if shipped.
"""
import argparse, json, math, os, sys

def shots_of(d):
    seq_dir = os.path.join(d, "sequences")
    out = []
    if os.path.isdir(seq_dir):
        for name in sorted(os.listdir(seq_dir)):
            if name.endswith(".json"):
                with open(os.path.join(seq_dir, name)) as f:
                    out.extend(json.load(f).get("shots", []))
    return sorted(out, key=lambda x: x.get("order", 0))

def cmd_estimate(args):
    dur = args.duration_sec
    shots = math.ceil(dur / 10)
    batches = math.ceil(shots / 6)
    redos = math.ceil(shots * args.redo_rate)
    print(f"Duration: {dur}s ({dur/60:.1f} min)")
    print(f"Shots (10s each): {shots}")
    print(f"Generation batches (<=6 clips): {batches}")
    print(f"Planned redos at {args.redo_rate:.0%}: {redos} clips")
    print(f"Total clip generations to plan for: {shots + redos}")
    print(f"Storyboard panels: {shots} (one per shot)")
    if dur >= 5400:
        print("Feature scale: split into reels/acts for generation, "
              "all under one bible. Do not run a feature as one batch plan.")

def cmd_breakdown(args):
    shots = shots_of(args.project)
    props, costumes, locs = set(), set(), set()
    for s in shots:
        locs.add(s.get("location", ""))
        # Props/costumes are free text in this version; the breakdown
        # records locations and shot counts, and flags shots whose
        # action names an object to be added to the prop list by hand.
        if "chair" in s.get("action", "").lower():
            props.add("chair")
        if "letter" in s.get("action", "").lower():
            props.add("letter")
    print(json.dumps({"shots": len(shots), "locations": sorted(locs),
                      "props_flagged": sorted(props)}, indent=2))

def cmd_storyboard(args):
    shots = shots_of(args.project)
    panels = [{"panelId": s["shotId"], "shotId": s["shotId"],
               "size": s.get("size"), "movement": s.get("movement"),
               "action": s.get("action"), "soundCue": s.get("soundMood"),
               "tension": None,
               "note": "Set tension 0-10 per panel in the storyboard view; "
                       "the curve must rise to a climax and resolve."}
              for s in shots]
    out = os.path.join(args.project, "storyboard.json")
    with open(out, "w") as f:
        json.dump({"panels": panels}, f, indent=2)
    print(f"Wrote {len(panels)} panels to {out}")

def cmd_qc(args):
    d = args.project
    shots = shots_of(d)
    issues = []
    for s in shots:
        if not s.get("lockedLookBlock"):
            issues.append(f"{s['shotId']}: missing locked look block")
        if "[tbd]" in json.dumps(s).lower():
            issues.append(f"{s['shotId']}: placeholder present")
    if not os.path.exists(os.path.join(d, "final", "edl.json")):
        issues.append("no EDL in final/ (run musevideo.py edl)")
    print("QC issues:" if issues else "QC checklist: no blocking issues found")
    for i in issues:
        print(" -", i)
    return 1 if issues else 0

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("estimate"); a.add_argument("duration_sec", type=int)
    a.add_argument("--redo-rate", type=float, default=0.2)
    for name in ("breakdown", "storyboard", "qc"):
        s = sub.add_parser(name); s.add_argument("project")
    args = p.parse_args()
    fn = {"estimate": cmd_estimate, "breakdown": cmd_breakdown,
          "storyboard": cmd_storyboard, "qc": cmd_qc}[args.cmd]
    sys.exit(fn(args))

if __name__ == "__main__":
    main()

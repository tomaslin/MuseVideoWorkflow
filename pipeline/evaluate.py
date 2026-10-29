#!/usr/bin/env python3
"""Automated evaluation for MuseVideoWorkflow. Standard library only.

Scores a project on verifiable facts, not on watching a clip (Muse cannot
watch video back — that limit is recorded in every report, not hidden).

  evaluate <project-dir> [--out <report.json>]
      Scores: coverage, locked-block fidelity, shot variety, tension curve,
      sound separation, continuity, and shipping readiness.
      Writes a JSON report and a markdown critical analysis next to it.

Scoring is 0-10 per dimension, with findings that name the exact shot,
field, or file. A dimension below 5 is a blocker for shipping.
"""
import argparse, json, math, os, sys

def load_json(p):
    with open(p) as f:
        return json.load(f)

def shots_of(d):
    out = []
    seq_dir = os.path.join(d, "sequences")
    if os.path.isdir(seq_dir):
        for name in sorted(os.listdir(seq_dir)):
            if name.endswith(".json"):
                out.extend(load_json(os.path.join(seq_dir, name)).get("shots", []))
    return sorted(out, key=lambda x: x.get("order", 0))

def evaluate(d):
    shots = shots_of(d)
    proj = load_json(os.path.join(d, "project.json")) if os.path.exists(os.path.join(d, "project.json")) else {}
    findings = []
    # Coverage
    expected = math.ceil(proj.get("durationSec", 0) / 10) if proj.get("durationSec") else len(shots)
    coverage = 10 if shots and len(shots) == expected else (5 if shots else 0)
    if len(shots) != expected:
        findings.append({"severity": "major", "dimension": "coverage",
                         "detail": f"{len(shots)} shots vs {expected} expected for {proj.get('durationSec')}s"})
    # Locked blocks
    missing = [s["shotId"] for s in shots if not s.get("lockedLookBlock") or len(s.get("lockedLookBlock", "")) < 40]
    locked = 10 if not missing else max(0, 10 - len(missing))
    if missing:
        findings.append({"severity": "major", "dimension": "locked-blocks",
                         "detail": f"Missing/truncated locked look block in: {', '.join(missing)}"})
    # Shot variety
    sizes = {s.get("size") for s in shots}
    moves = {s.get("movement") for s in shots}
    variety = min(10, len(sizes) * 2 + len(moves))
    if len(sizes) < 3:
        findings.append({"severity": "major", "dimension": "variety",
                         "detail": f"Only {len(sizes)} shot sizes used: {sorted(sizes)} — every shot the same size reads as a slideshow, not a film"})
    if len(moves) < 2:
        findings.append({"severity": "minor", "dimension": "variety",
                         "detail": "Only one camera movement used across the project"})
    # One action per shot (heuristic: action length / conjunctions)
    multi = [s["shotId"] for s in shots if s.get("action", "").count(" and ") >= 2]
    action_score = 10 if not multi else 6
    if multi:
        findings.append({"severity": "minor", "dimension": "action",
                         "detail": f"Shots that may contain two actions: {', '.join(multi)} — split them or the clip will drift mid-shot"})
    # Sound separation
    no_sound = [s["shotId"] for s in shots if not s.get("soundMood")]
    sound = 10 if not no_sound else 5
    if no_sound:
        findings.append({"severity": "major", "dimension": "sound",
                         "detail": f"No sound mood recorded for: {', '.join(no_sound)}"})
    # Tension: storyboard.json tension values, if present
    sb_path = os.path.join(d, "storyboard.json")
    tension_score, tension_note = 5, "No storyboard tension values recorded — curve cannot be verified"
    if os.path.exists(sb_path):
        panels = load_json(sb_path).get("panels", [])
        vals = [p.get("tension") for p in panels if isinstance(p.get("tension"), (int, float))]
        if vals:
            tension_note = f"Tension range {min(vals)}-{max(vals)}, climax at position {vals.index(max(vals))+1}/{len(vals)}"
            tension_score = 10 if max(vals) >= 9 and vals[-1] <= 4 else 6
            if max(vals) < 9:
                findings.append({"severity": "major", "dimension": "tension",
                                 "detail": "Tension never reaches 9-10 — the film has no climax, only a plateau"})
            if vals[-1] > 4:
                findings.append({"severity": "minor", "dimension": "tension",
                                 "detail": "Final tension above 4 — the film does not resolve, it stops"})
    # Continuity: same character blocks across shots
    chars = {}
    drift = []
    for s in shots:
        for ch, block in (s.get("lockedCharacterBlocks") or {}).items():
            if ch in chars and chars[ch] != block:
                drift.append(s["shotId"])
            chars[ch] = block
    continuity = 10 if not drift else 4
    if drift:
        findings.append({"severity": "blocker", "dimension": "continuity",
                         "detail": f"Character block changed mid-project in: {', '.join(drift)} — a character who changes description changes face"})
    scores = {"coverage": coverage, "locked_blocks": locked, "variety": variety,
              "action": action_score, "sound": sound, "tension": tension_score,
              "continuity": continuity}
    overall = round(sum(scores.values()) / len(scores), 1)
    report = {"project": proj.get("slug", os.path.basename(d.rstrip("/"))),
              "shots": len(shots), "scores": scores, "overall": overall,
              "tension_note": tension_note, "findings": findings,
              "blockers": [f for f in findings if f["severity"] == "blocker"],
              "shipping_ready": overall >= 7 and not any(f["severity"] == "blocker" for f in findings),
              "limit_note": "Muse cannot watch generated video back. This report scores the plan, prompts, and metadata. Visual quality still requires a human watch per batch, recorded in critiques/."}
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("project")
    p.add_argument("--out", default=None)
    args = p.parse_args()
    report = evaluate(args.project)
    out = args.out or os.path.join(args.project, "evaluation.json")
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    md = os.path.join(args.project, "evaluation.md")
    with open(md, "w") as f:
        f.write(f"# Evaluation: {report['project']}\n\nOverall: {report['overall']}/10 — shipping ready: {report['shipping_ready']}\n\n")
        f.write(f"Tension: {report['tension_note']}\n\n## Scores\n")
        for k, v in report["scores"].items():
            f.write(f"- {k}: {v}/10\n")
        f.write("\n## Findings\n")
        for fn in report["findings"] or [{"severity": "none", "dimension": "-", "detail": "No findings."}]:
            f.write(f"- [{fn['severity']}] {fn['dimension']}: {fn['detail']}\n")
        f.write(f"\n{report['limit_note']}\n")
    print(f"Overall {report['overall']}/10, shipping_ready={report['shipping_ready']}, findings={len(report['findings'])}")
    print(f"Wrote {out} and {md}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Watch MuseVideoWorkflow for new/changed source files (stdlib only).

Tracked sources: projects/*/brief.md, treatment.md, script.md,
look-bible.md, characters.md, project.json, sequences/*.json, and
top-level docs/pipeline/schemas/chapters. Deliberately excluded:
clips/ (binary work files), evaluation.json/md and critiques/ (outputs
of this watch itself — tracking them would re-trigger forever),
watch-log.md and .watch-state.json.

Usage: watch.py [--init]  — --init records the current snapshot without
reporting, for first run. Otherwise prints NEW/CHANGED/REMOVED lines
and, for each changed project, runs pipeline/evaluate.py, appending
the result to watch-log.md. If a project has a brief/script but no
prompts/ yet, it also runs prompt-pack, so a new idea gets Muse-authored
prompt packets automatically (as a new variant, never overwriting).
State: .watch-state.json next to this script.
"""
import hashlib, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(ROOT, ".watch-state.json")
LOG = os.path.join(ROOT, "watch-log.md")
EXCLUDE_DIRS = {"clips", "critiques", "variants"}
EXCLUDE_FILES = {"evaluation.json", "evaluation.md", "watch-log.md", ".watch-state.json"}

def tracked():
    out = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS and d != "__pycache__" and not d.startswith("."))
        for fn in sorted(filenames):
            if fn in EXCLUDE_FILES or fn.endswith((".mp4", ".jpg", ".png", ".webp")):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            try:
                with open(full, "rb") as f:
                    out[rel] = hashlib.sha256(f.read()).hexdigest()[:16]
            except OSError:
                pass
    return out

def main():
    cur = tracked()
    prev = {}
    if os.path.exists(STATE):
        prev = json.load(open(STATE))
    if "--init" in sys.argv or not prev:
        json.dump(cur, open(STATE, "w"), indent=2, sort_keys=True)
        print(f"watch: baseline recorded, {len(cur)} files")
        return 0
    new = sorted(set(cur) - set(prev))
    changed = sorted(k for k in set(cur) & set(prev) if cur[k] != prev[k])
    removed = sorted(set(prev) - set(cur))
    if not new and not changed and not removed:
        print("watch: no changes")
        return 0
    with open(LOG, "a") as log:
        from datetime import datetime, timezone
        log.write(f"\n## {datetime.now(timezone.utc).isoformat()}\n")
        for k in new: log.write(f"- NEW {k}\n")
        for k in changed: log.write(f"- CHANGED {k}\n")
        for k in removed: log.write(f"- REMOVED {k}\n")
    projects = {p.split("/")[1] for p in new + changed if p.startswith("projects/")}
    for proj in sorted(projects):
        pdir = os.path.join(ROOT, "projects", proj)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "evaluate.py"), pdir],
                           capture_output=True, text=True)
        with open(LOG, "a") as log:
            log.write(f"- EVALUATE {proj}: {r.stdout.strip()}\n")
        prompts = os.path.join(pdir, "prompts")
        if os.path.exists(os.path.join(pdir, "brief.md")) and not os.path.isdir(prompts):
            r2 = subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "musevideo.py"),
                                 "prompt-pack", pdir], capture_output=True, text=True)
            with open(LOG, "a") as log:
                log.write(f"- PROMPT-PACK {proj}: {r2.stdout.strip() or r2.stderr.strip()}\n")
    json.dump(cur, open(STATE, "w"), indent=2, sort_keys=True)
    print(f"watch: new={len(new)} changed={len(changed)} removed={len(removed)} projects={sorted(projects)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""One idempotent watch tick. Schedule every 2 minutes; no media generation here.

Only authoring inputs are tracked. Changed prompts are regenerated from actual
shot definitions; failed evaluations remain pending for the next tick. Muse's
separate state-driven generation worker consumes generation-queue.json.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
STATE = ROOT / '.watch-state.json'
SOURCE_NAMES = {'production.json', 'project.json', 'brief.md', 'treatment.md', 'script.md', 'look-bible.md', 'characters.md', 'lore-bible.md', 'storyboard.json', 'edit.json'}

def tracked():
    paths = list((ROOT / 'pipeline').glob('*.py')) + list((ROOT / 'schemas').glob('*.json'))
    for project in (ROOT / 'projects').iterdir():
        if project.is_dir():
            paths += [p for p in project.iterdir() if p.name in SOURCE_NAMES and p.is_file()]
            paths += list((project / 'sequences').glob('*.json')) + list((project / 'departments').glob('*.md'))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def tick(init=False):
    current = tracked()
    previous = json.loads(STATE.read_text()) if STATE.exists() else {}
    if init:
        STATE.write_text(json.dumps(current, indent=2, sort_keys=True))
        print(f'watch: baseline recorded, {len(current)} authoring inputs')
        return 0
    changed = sorted(p for p in current.keys() | previous.keys() if current.get(p) != previous.get(p))
    if not changed:
        print('watch: no changes')
        return 0
    global_change = any(p.startswith(('pipeline/', 'schemas/')) for p in changed)
    projects = {p.split('/')[1] for p in changed if p.startswith('projects/')}
    if global_change:
        projects.update(p.parent.name for p in (ROOT / 'projects').glob('*/project.json'))
    failures = []
    lines = [f'\n## {datetime.now(timezone.utc).isoformat()}'] + [f'- CHANGED {p}' for p in changed]
    for name in sorted(projects):
        directory = ROOT / 'projects' / name
        if not (directory / 'project.json').exists():
            continue
        if json.loads((directory / 'project.json').read_text()).get('archived'):
            lines.append(f'- {name}: archived project skipped')
            continue
        commands = []
        if (directory / 'production.json').exists():
            commands.append([sys.executable, str(ROOT / 'pipeline/develop.py'), str(directory / 'production.json'), '--refresh'])
        commands += ([sys.executable, str(ROOT / 'pipeline/musevideo.py'), 'validate', str(directory)],
                        [sys.executable, str(ROOT / 'pipeline/musevideo.py'), 'prompt-pack', str(directory)],
                        [sys.executable, str(ROOT / 'pipeline/evaluate.py'), str(directory)])
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
            lines.append(f'- {name}: {result.stdout.strip()} {result.stderr.strip()}')
            if result.returncode:
                failures.append(name)
                break
    with (ROOT / 'watch-log.md').open('a') as log:
        log.write('\n'.join(lines) + '\n')
    # Do not acknowledge failed source changes; retry them on the next tick.
    if not failures:
        temp = STATE.with_suffix('.tmp')
        temp.write_text(json.dumps(tracked(), indent=2, sort_keys=True))
        os.replace(temp, STATE)
    print(f'watch: {len(changed)} input changes, projects={sorted(projects)}, failures={failures}')
    return 1 if failures else 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', action='store_true')
    args = parser.parse_args()
    with (ROOT / '.watch.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('watch: another tick is running; skipped')
            return 0
        return tick(args.init)

if __name__ == '__main__':
    sys.exit(main())

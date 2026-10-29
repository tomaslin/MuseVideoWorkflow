#!/usr/bin/env python3
"""Package the studio plus real project artifacts/media for local preview or Pages."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def build(out):
    out = Path(out).resolve()
    if out == ROOT or ROOT not in out.parents and out.name in {'projects', 'apps', 'pipeline'}:
        raise ValueError('Unsafe output directory')
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'apps/studio', out, dirs_exist_ok=True)
    sys.path.insert(0, str(ROOT / 'pipeline'))
    spec = importlib.util.spec_from_file_location('evaluation', ROOT / 'pipeline/evaluate.py')
    evaluation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluation)
    catalog = []
    for definition in sorted((ROOT / 'projects').glob('*/project.json')):
        project_dir = definition.parent
        project = json.loads(definition.read_text())
        slug = project_dir.name
        shots = []
        for seq in sorted((project_dir / 'sequences').glob('*.json')):
            shots.extend(json.loads(seq.read_text()).get('shots', []))
        if all(isinstance(s.get('order'), int) for s in shots):
            shots.sort(key=lambda s: s['order'])
        panels = json.loads((project_dir / 'storyboard.json').read_text()).get('panels', []) if (project_dir / 'storyboard.json').exists() else []
        tensions = {p['shotId']: p.get('tension') for p in panels}
        manifest_path = project_dir / 'manifest.json'
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        selected = {c['shotId']: c for c in manifest.get('clips', []) if c.get('selected')}
        data_dir = out / 'data' / slug
        data_dir.mkdir(parents=True, exist_ok=True)
        for shot in shots:
            shot['tension'] = tensions.get(shot['shotId'])
            prompt = project_dir / 'prompts' / (shot['shotId'] + '.txt')
            shot['prompt'] = prompt.read_text() if prompt.exists() else ''
            clip = selected.get(shot['shotId'])
            shot['status'] = clip.get('status', 'generated') if clip else 'missing'
            if clip:
                source = (project_dir / clip['file']).resolve()
                if project_dir.resolve() not in source.parents:
                    raise ValueError(f'Clip escapes project: {source}')
                if source.exists():
                    target = data_dir / (shot['shotId'] + '.mp4')
                    shutil.copyfile(source, target)
                    shot['videoUrl'] = target.relative_to(out).as_posix()
                    shot['sourceDurationSec'] = clip.get('durationSec')
        project.update(shots=shots, artifacts={}, evaluation=evaluation.evaluate(str(project_dir)))
        for file in sorted(project_dir.glob('*.md')):
            project['artifacts'][file.stem] = file.read_text()
        project['edit'] = json.loads((project_dir / 'edit.json').read_text()) if (project_dir / 'edit.json').exists() else {}
        final = project_dir / 'final'
        if (final / 'final-manifest.json').exists() and (final / 'video.mp4').exists():
            # Never publish an LFS pointer as a video.
            if (final / 'video.mp4').stat().st_size < 1024:
                raise ValueError(f'Final appears to be an LFS pointer: {final}')
            result = subprocess.run(['python3', str(ROOT / 'pipeline/musevideo.py'), 'verify-final', str(project_dir)], capture_output=True, text=True)
            if result.returncode:
                raise ValueError(f'Final failed verification: {result.stdout} {result.stderr}')
            for name in ['video.mp4', 'poster.jpg', 'edl.json', 'final-manifest.json']:
                if (final / name).exists():
                    shutil.copyfile(final / name, data_dir / name)
            project['final'] = json.loads((final / 'final-manifest.json').read_text())
            project['videoUrl'] = f'data/{slug}/video.mp4'
            project['posterUrl'] = f'data/{slug}/poster.jpg'
        catalog.append(project)
    (out / 'catalog.json').write_text(json.dumps({'projects': catalog}, indent=2) + '\n')
    (out / '.nojekyll').touch()
    print(f'Built {len(catalog)} real projects in {out}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default=str(ROOT / '_site'))
    build(parser.parse_args().out)

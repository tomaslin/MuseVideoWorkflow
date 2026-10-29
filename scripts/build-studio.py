#!/usr/bin/env python3
"""Package the studio plus real project artifacts/media for local preview or Pages."""
import argparse
import hashlib
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
        failures_path = project_dir / 'provider-failures.json'
        failures = json.loads(failures_path.read_text()).get('shots', {}) if failures_path.exists() else {}
        blockers_path = project_dir / 'generation-blockers.json'
        blockers = json.loads(blockers_path.read_text()).get('shots', {}) if blockers_path.exists() else {}
        data_dir = out / 'data' / slug
        data_dir.mkdir(parents=True, exist_ok=True)
        for shot in shots:
            shot['tension'] = tensions.get(shot['shotId'])
            prompt = project_dir / 'prompts' / (shot['shotId'] + '.txt')
            shot['prompt'] = prompt.read_text() if prompt.exists() else ''
            clip = selected.get(shot['shotId'])
            shot['status'] = clip.get('status', 'generated') if clip else 'missing'
            if shot['shotId'] in failures: shot['status'] = 'provider error: ' + failures[shot['shotId']].get('error', 'unknown')
            elif shot['shotId'] in blockers: shot['status'] = 'blocked: ' + blockers[shot['shotId']].get('type', 'production dependency')
            if clip:
                for rel in [clip.get('file'),clip.get('publishedPreviewFile')]:
                    if not rel: continue
                    source = (project_dir / rel).resolve()
                    if project_dir.resolve() not in source.parents:
                        raise ValueError(f'Clip escapes project: {source}')
                    if source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest()==clip.get('sha256'):
                        target = data_dir / (shot['shotId'] + '.mp4')
                        shutil.copyfile(source, target)
                        shot['videoUrl'] = target.relative_to(out).as_posix()
                        shot['sourceDurationSec'] = clip.get('durationSec')
                        break
        references = []
        ref_file = project_dir / 'reference-manifest.json'
        for ref in (json.loads(ref_file.read_text()).get('references', []) if ref_file.exists() else []):
            source = (project_dir / ref['file']).resolve()
            if project_dir.resolve() not in source.parents:
                raise ValueError(f'Reference escapes project: {source}')
            if source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest() == ref.get('sha256'):
                target = data_dir / 'references' / source.name
                target.parent.mkdir(exist_ok=True)
                shutil.copyfile(source, target)
                references.append({**ref, 'url': target.relative_to(out).as_posix()})
        for shot in shots:
            available = next((r for r in references if r['status']=='working' and any(name in r['characters'] for name in shot.get('characters', []))), None)
            if available:
                shot['referenceUrl'] = available['url']
                shot['referenceLabel'] = ', '.join(available['characters'])
        project.update(shots=shots, artifacts={}, references=references, evaluation=evaluation.evaluate(str(project_dir)))
        for file in sorted(project_dir.glob('*.md')):
            project['artifacts'][file.stem] = file.read_text()
        project['edit'] = json.loads((project_dir / 'edit.json').read_text()) if (project_dir / 'edit.json').exists() else {}
        project['workprints'] = []
        draft_file = project_dir / 'draft-previews.json'
        for draft in (json.loads(draft_file.read_text()).get('drafts', []) if draft_file.exists() else []):
            video = (project_dir / draft['video']).resolve()
            manifest = (project_dir / draft['manifest']).resolve()
            poster = (project_dir / draft['poster']).resolve()
            if any(project_dir.resolve() not in item.parents for item in (video,manifest,poster)):
                raise ValueError('Workprint path escapes project')
            if not video.is_file() or hashlib.sha256(video.read_bytes()).hexdigest()!=draft['sha256']:
                raise ValueError(f'Workprint checksum mismatch: {video}')
            if json.loads(manifest.read_text()).get('scope') != 'draft-excerpt':
                raise ValueError('Workprint must be labeled as an excerpt')
            target = data_dir / 'workprints' / draft['id']
            target.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(video,target/'video.mp4')
            shutil.copyfile(poster,target/'poster.jpg')
            project['workprints'].append({'title':draft['title'],'description':draft['description'],'videoUrl':(target/'video.mp4').relative_to(out).as_posix(),'posterUrl':(target/'poster.jpg').relative_to(out).as_posix()})
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

#!/usr/bin/env python3
"""Materialize a Muse-authored story production into a reproducible artifact set.

This does not pretend that a hash/template can write a screenplay. Muse authors
production.json from the story brief; this tool validates/materializes that
creative work, derives locked prompts, storyboard, EDL and generation batches.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = ('brief', 'treatment', 'script', 'look-bible', 'characters', 'lore-bible')
SHOT_FIELDS = ('shotId', 'size', 'movement', 'location', 'action', 'emotionalBeat', 'soundMood', 'background', 'choreography', 'cameraChoreography', 'lighting', 'lensMm', 'focus', 'motion', 'extras', 'loreNotes', 'generationBrief', 'editMotivation')

def validate(data):
    errors = []
    project = data.get('project', {})
    slug = project.get('slug', '')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', slug):
        errors.append('project.slug must be a safe lowercase slug')
    for key in ('title', 'logline', 'durationSec', 'format'):
        if not project.get(key): errors.append(f'project.{key} is required')
    for bucket in ('documents', 'departments'):
        for key in data.get(bucket, {}):
            if not re.fullmatch(r'[a-z0-9-]+', key): errors.append(f'Unsafe artifact name: {key}')
    for seq in data.get('sequences', []):
        if not re.fullmatch(r'[a-z0-9-]+', seq.get('sequenceId', '')): errors.append('Unsafe sequenceId')
    for name in REQUIRED_DOCS:
        if len(data.get('documents', {}).get(name, '').strip()) < 120:
            errors.append(f'documents.{name} must contain the actual authored artifact')
    characters = data.get('characters', {})
    for name, block in characters.items():
        if not isinstance(block, str) or len(block) < 60: errors.append(f'Incomplete locked character: {name}')
    if len(data.get('lookBlock', '')) < 100: errors.append('A concrete locked lookBlock is required')
    departments = data.get('departments', {})
    for name in ('direction', 'camera-lighting', 'production-design', 'costume-makeup', 'choreography', 'sound-music', 'editorial'):
        if len(departments.get(name, '')) < 120: errors.append(f'Missing substantive department packet: {name}')
    shots = [s for seq in data.get('sequences', []) for s in seq.get('shots', [])]
    ids = [s.get('shotId') for s in shots]
    if not shots or len(ids) != len(set(ids)): errors.append('Shot IDs must be present and unique')
    for shot in shots:
        sid = shot.get('shotId', '?')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', str(sid)): errors.append(f'Unsafe shot ID: {sid}')
        for field in SHOT_FIELDS:
            if not shot.get(field): errors.append(f'{sid}: missing {field}')
        if not isinstance(shot.get('tension'), (int, float)) or not 0 <= shot['tension'] <= 10: errors.append(f'{sid}: tension must be 0–10')
        for name in shot.get('characters', []):
            if name not in characters: errors.append(f'{sid}: undefined character {name}')
        if shot.get('kind', 'generated') not in ('generated', 'title'): errors.append(f'{sid}: invalid source kind')
        if shot.get('kind') == 'title' and not shot.get('titleText'): errors.append(f'{sid}: missing titleText')
        if any(token in json.dumps(shot).lower() for token in ('[tbd]', '[todo]', '[insert', 'edit me', 'see sequence file')): errors.append(f'{sid}: placeholder in production shot')
    edit = data.get('edit', {})
    cuts = edit.get('shots', [])
    total = 0
    for cut in cuts:
        if cut.get('shotId') not in ids: errors.append(f'Edit refers to unknown shot: {cut.get("shotId")}')
        start, duration = cut.get('inSec', -1), cut.get('durationSec', 0)
        if not isinstance(start, (int, float)) or not isinstance(duration, (int, float)) or not math.isfinite(start + duration) or start < 0 or duration <= 0:
            errors.append('Invalid trim'); continue
        source = next((s for s in shots if s.get('shotId') == cut.get('shotId')), {})
        limit = source.get('sourceDurationSec', 10)
        if start + duration > limit: errors.append(f'{cut.get("shotId")}: trim exceeds source')
        if abs(duration * edit.get('fps', 24) - round(duration * edit.get('fps', 24))) > .001: errors.append(f'{cut.get("shotId")}: trim must align to frames')
        total += duration
    if not cuts or abs(total - project.get('durationSec', 0)) > .001: errors.append(f'Edit must total exactly {project.get("durationSec")}s; got {total}s')
    if set(ids) != {c.get('shotId') for c in cuts}: errors.append('Every source shot must have an editorial use')
    if errors: raise ValueError('\n'.join(errors))
    return shots

def materialize(source, output=None, refresh=False):
    data = json.loads(Path(source).read_text())
    shots = validate(data)
    project = dict(data['project'])
    slug = project['slug']
    dest = Path(output).resolve() if output else ROOT / 'projects' / slug
    if (dest / 'project.json').exists() and not refresh:
        raise ValueError('Project already exists. Use --refresh to version and regenerate its authored artifacts.')
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    fingerprint = hashlib.sha256(canonical).hexdigest()
    old_index = json.loads((dest / 'artifact-index.json').read_text()) if (dest / 'artifact-index.json').exists() else {}
    if old_index.get('productionSha256') == fingerprint:
        print(f'Production unchanged: {slug}; artifacts retained')
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.develop-', dir=dest.parent) as temp:
        stage = Path(temp)
        def write(path, value):
            p = stage / path; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False) + '\n')
        project.update(sourceShotCount=len(shots), generationClipSec=10, timingMode='edited', state='shot-list', productionSha256=fingerprint, active=True)
        write('production.json', data); write('project.json', project)
        for name, text in data['documents'].items(): write(name + '.md', text.rstrip() + '\n')
        for name, text in data['departments'].items(): write('departments/' + name + '.md', text.rstrip() + '\n')
        panels, generation, cursor, entries, ordered = [], [], 0, [], []
        by_id = {}
        order = 0
        for seq in data['sequences']:
            sequence = {key: val for key, val in seq.items() if key != 'shots'}
            sequence['shots'] = []
            for authored in seq['shots']:
                order += 1
                shot = dict(authored)
                shot.update(sequenceId=seq['sequenceId'], order=order, lockedLookBlock=data['lookBlock'], lockedCharacterBlocks={name: data['characters'][name] for name in shot.get('characters', [])})
                sequence['shots'].append(shot); by_id[shot['shotId']] = shot
                blocks = [data['lookBlock'], *shot['lockedCharacterBlocks'].values()]
                prompt = '\n\n'.join(blocks + [shot['generationBrief'], 'One continuous take. No internal edits, montage, titles or captions. Keep the usable action within the specified source handle; hold the end pose.']) + '\n'
                if shot.get('kind') == 'title': prompt = 'LOCAL TITLE CARD\n' + shot['titleText'] + '\n'
                write('prompts/' + shot['shotId'] + '.txt', prompt)
                production_packet = f"# {shot['shotId']} — production packet\n\n" + '\n\n'.join(f'**{key}:** {shot[key]}' for key in SHOT_FIELDS if key in shot) + '\n'
                write('prompts/' + shot['shotId'] + '.production.md', production_packet)
                if shot.get('kind', 'generated') == 'generated': generation.append({'shotId':shot['shotId'], 'promptSha256':hashlib.sha256(prompt.encode()).hexdigest(), 'referenceCharacters':shot.get('characters', []), 'status':'missing'})
                panels.append({**{key: shot[key] for key in ('shotId','size','movement','action','tension','editMotivation')}, 'panelId':shot['shotId'], 'soundCue':shot['soundMood']})
            write('sequences/sequence-' + seq['sequenceId'] + '.json', sequence)
        for cut in data['edit']['shots']:
            sid = cut['shotId']; duration = cut['durationSec']
            entries.append({'shotId':sid,'sequenceId':by_id[sid]['sequenceId'],'sourceInSec':cut['inSec'],'sourceOutSec':cut['inSec']+duration,'startSec':cursor,'endSec':cursor+duration,'transitionIn':'cut','editMotivation':by_id[sid]['editMotivation']})
            cursor += duration; ordered.append(sid)
        write('edit.json', data['edit']); write('storyboard.json', {'panels':panels})
        write('final/edl.json', {'shotOrder':ordered,'entries':entries,'totalSec':cursor,'status':'planned-not-rendered'})
        write('generation-queue.json', {'productionSha256':fingerprint,'pending':generation,'nextBatch':generation[:6],'complete':False})
        write('batches.json', {'maxPerMessage':6,'sourceShotCount':len(generation),'batches':[{'batch':i//6+1,'shotIds':[s['shotId'] for s in generation[i:i+6]]} for i in range(0,len(generation),6)]})
        write('manifest.json', {'version':1,'clips':[],'redoRequests':[]})
        write('reference-plan.json', {'status':'pending-generation','productionSha256':fingerprint,'characters':[{'name':name,'lockedDescription':block,'imageFile':'references/'+re.sub(r'[^a-z0-9]+','-',name.lower()).strip('-')+'.png','status':'missing'} for name,block in data['characters'].items()],'groupRules':data.get('storyContract',{})})
        write('audio-plan.json', {'status':'not-recorded','sampleRate':48000,'channels':2,'voicePolicy':'Record dialogue separately; no lip-sync claim','cues':[{'shotId':e['shotId'],'startSec':e['startSec'],'endSec':e['endSec'],'intent':by_id[e['shotId']]['soundMood']} for e in entries],'stems':['dialogue','music','ambience','impacts'],'delivery':'Approved 48kHz stereo mix, -1 dBTP ceiling, timed captions from actual recordings'})
        write('budget.json', {'unit':'clip generations','plannedSourceClips':len(generation),'plannedRedoClips':math.ceil(len(generation)*.2),'maxClipsPerRun':6,'currencyEstimate':None,'costBasis':'Provider billing not supplied; no invented cash estimate','localTitleCards':len(shots)-len(generation)})
        write('schedule.json', {'timezone':'America/Los_Angeles','desiredIntervalMinutes':2,'status':'requires-Muse-task-confirmation','policy':'One worker, project lease, current hashes, at most six missing/stale/redo shots, retry failures only, idle on completion','batchesFile':'batches.json','generationQueue':'generation-queue.json'})
        write('rights-ledger.json', {'status':'original-fiction-development','entries':[{'kind':'story','source':'User-supplied premise developed into original fiction','clearance':'No third-party footage or dialogue included'},{'kind':'visual-reference','source':'1970s studio wuxia horror production language','clearance':'Use original characters, sets, performances and score; retain provider provenance for generated media'}],'musicStatus':'Original score not recorded yet'})
        owners={'producer':'brief.md; budget.json; schedule.json; rights-ledger.json','director':'treatment.md; script.md; storyboard.json; departments/direction.md','cinematographer':'look-bible.md; departments/camera-lighting.md; shot camera fields','script-supervisor':'lore-bible.md; characters.md; fixed blocks and per-shot editMotivation','production-designer':'departments/production-design.md; shot background fields','costume-and-makeup':'departments/costume-makeup.md; locked character appearances','fight-coordinator':'departments/choreography.md; timed anticipation/contact/recoil','sound-and-composer':'departments/sound-music.md; audio-plan.json','editor':'edit.json; final/edl.json; departments/editorial.md','generation-operator':'prompts/; reference-plan.json; batches.json; manifest.json','delivery-QC':'evaluation.json; local Swift verify; named reviewer of final footage'}
        write('responsibilities.json', {'policy':'Responsibilities are artifact owners, not fictitious professional approvals','assignments':[{'role':role,'owns':owns,'assignee':'Muse for authored planning; local tools for materialization; user or named reviewer for footage approval','signoff':'pending actual artifact/footage checks'} for role,owns in owners.items()]})

        history = json.loads((dest/'state.json').read_text()).get('history', []) if (dest/'state.json').exists() else []
        history.append({'at':datetime.now(timezone.utc).isoformat(),'event':'production-materialized','productionSha256':fingerprint})
        write('state.json', {'slug':slug,'state':'shot-list','history':history,'openCritiques':['Generated footage, reference adherence, sound mix and final visual review pending']})
        write('critique.md', data.get('critique', 'Footage review pending.'))
        index = sorted(str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file())
        write('artifact-index.json', {'productionSha256':fingerprint,'files':index})
        if (dest/'project.json').exists():
            archive = dest / 'variants' / ('production-' + old_index.get('productionSha256', 'legacy')[:16])
            for name in old_index.get('files', []):
                p = dest/name
                if p.is_file():
                    (archive/name).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p,archive/name)
        dest.mkdir(parents=True, exist_ok=True)
        for path in sorted(stage.rglob('*')):
            if not path.is_file(): continue
            rel = path.relative_to(stage)
            # Never erase take/review provenance on a story refresh.
            if str(rel) == 'manifest.json' and (dest/rel).exists(): continue
            target=dest/rel; target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(path,target)
        for name in set(old_index.get('files', [])) - set(index):
            if name.startswith(('sequences/', 'prompts/')):
                (dest/name).unlink(missing_ok=True)
    print(f'Materialized {slug}: {len(shots)} editorial sources, {len(generation)} generations in {math.ceil(len(generation)/6)} batches, {cursor:g}s exact edit')
    return dest

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('source', help='Muse-authored production.json')
    parser.add_argument('--output')
    parser.add_argument('--refresh', action='store_true')
    args=parser.parse_args()
    try: materialize(args.source,args.output,args.refresh)
    except (ValueError,OSError,KeyError,TypeError) as exc: parser.exit(1, f'Production rejected: {exc}\n')

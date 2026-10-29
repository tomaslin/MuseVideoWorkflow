#!/usr/bin/env python3
"""Plan/lease Muse batches across isolated projects, at most six clips TOTAL.

No provider API is implied. Muse executes the printed batch using its tools;
clips are imported/verified locally before a lease is completed. Fair rotation
prevents a long project starving another. Titles never consume AI slots.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]

def load(file, default=None):
    return json.loads(file.read_text()) if file.exists() else default

def save(file, data):
    tmp=file.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');tmp.replace(file)

@contextmanager
def locked(root):
    with (root/'.workspace.lock').open('w') as file:
        fcntl.flock(file,fcntl.LOCK_EX)
        yield


def projects(root):
    out=[]
    for file in sorted((root/'projects').glob('*/project.json')):
        project=load(file)
        if project.get('archived') or file.parent.name.startswith('_') or project.get('generationEnabled') is False:
            continue
        out.append((file.parent,project))
    return out


def pending(directory):
    manifest=load(directory/'manifest.json',{})
    selected={c['shotId']:c for c in manifest.get('clips',[]) if c.get('selected')}
    shots=[]
    for sequence in sorted((directory/'sequences').glob('*.json')):
        shots.extend(load(sequence).get('shots',[]))
    if all('order' in s for s in shots):shots.sort(key=lambda s:s['order'])
    queue=[]
    for shot in shots:
        if shot.get('kind','generated')!='generated':continue
        sid=shot['shotId'];packet=directory/'prompts'/f'{sid}.txt'
        if not packet.exists():continue
        prompt_hash=hashlib.sha256(packet.read_bytes()).hexdigest()
        take=selected.get(sid)
        reason='missing'
        if take:
            if take.get('status')=='redo':reason='redo'
            elif take.get('promptSha256')!=prompt_hash:reason='stale-prompt'
            else:
                clip=(directory/take.get('file','')).resolve()
                if directory.resolve() not in clip.parents:raise ValueError(f'Clip escapes project: {sid}')
                if clip.is_file() and hashlib.sha256(clip.read_bytes()).hexdigest()==take.get('sha256'):continue
                reason='missing-or-corrupt'
        queue.append({'project':directory.name,'shotId':sid,'reason':reason,'promptFile':str(packet),'promptSha256':prompt_hash,'characters':shot.get('characters',[])})
    # Explicit user feedback gets first place within each project.
    queue.sort(key=lambda q:0 if q['reason']=='redo' else 1)
    return queue


def plan(root, state=None, limit=6, now=None):
    state=state or {};now=time.time() if now is None else now
    leased={(j['project'],j['shotId']) for lease in state.get('leases',[]) if lease['status']=='running' and lease['expiresAt']>now for j in lease['jobs']}
    queues={d.name:[j for j in pending(d) if (j['project'],j['shotId']) not in leased and state.get('retryAfter',{}).get(j['project']+':'+j['shotId'],0)<=now] for d,p in projects(root)}
    names=sorted(queues)
    last=state.get('lastProject')
    if last in names:
        i=names.index(last)+1;names=names[i:]+names[:i]
    jobs=[]
    while len(jobs)<min(max(limit,0),6):
        progress=False
        for name in names:
            if queues[name]:
                jobs.append(queues[name].pop(0));progress=True
                if len(jobs)>=min(max(limit,0),6):break
        if not progress:break
    return jobs


def batch(root, claim=False, limit=6, ttl=1800):
    with locked(root):
        file=root/'.workspace-state.json';state=load(file,{'leases':[]})
        now=time.time()
        for lease in state['leases']:
            if lease['status']=='running' and lease['expiresAt']<=now:lease['status']='expired'
        jobs=plan(root,state,limit,now)
        result={'provider':'Muse','maxClipsPerMessage':6,'jobs':jobs,'idle':not jobs}
        if claim and jobs:
            lease={'leaseId':str(uuid.uuid4()),'status':'running','createdAt':now,'expiresAt':now+ttl,'jobs':jobs}
            state['leases'].append(lease);state['lastProject']=jobs[-1]['project'];save(file,state)
            result.update(leaseId=lease['leaseId'],expiresAt=lease['expiresAt'])
        return result


def complete(root, lease_id, failures=None):
    failures=set(failures or [])
    with locked(root):
        file=root/'.workspace-state.json';state=load(file,{'leases':[]})
        lease=next((l for l in state['leases'] if l['leaseId']==lease_id),None)
        if not lease or lease['status']!='running' or lease['expiresAt']<=time.time():raise ValueError('No unexpired running lease with that ID')
        # A success must be imported, have the claimed prompt hash, and verify.
        for job in lease['jobs']:
            key=job['project']+':'+job['shotId']
            if key in failures:continue
            directory=root/'projects'/job['project']
            current_hash=hashlib.sha256((directory/'prompts'/f"{job['shotId']}.txt").read_bytes()).hexdigest()
            if current_hash!=job['promptSha256'] or any(j['shotId']==job['shotId'] for j in pending(directory)):
                raise ValueError(f'{key} is not imported/verified for the claimed prompt. Mark it --failed or import it before completing.')
        known={j['project']+':'+j['shotId'] for j in lease['jobs']}
        if not failures<=known:raise ValueError('Failure list includes a shot outside this lease')
        lease.update(status='completed',completedAt=time.time(),failures=sorted(failures))
        retry=state.setdefault('retryAfter',{})
        for key in failures:retry[key]=time.time()+120
        save(file,state)
        return lease


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=ROOT)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('list')
    queue=sub.add_parser('queue');queue.add_argument('--claim',action='store_true');queue.add_argument('--limit',type=int,default=6);queue.add_argument('--ttl-sec',type=int,default=1800)
    done=sub.add_parser('complete');done.add_argument('lease_id');done.add_argument('--failed',action='append',default=[])
    args=parser.parse_args()
    try:
        if args.command=='list':result=[{'slug':p['slug'],'title':p['title'],'pending':len(pending(d))} for d,p in projects(args.root)]
        elif args.command=='queue':result=batch(args.root,args.claim,args.limit,args.ttl_sec)
        else:result=complete(args.root,args.lease_id,args.failed)
        print(json.dumps(result,indent=2))
    except (ValueError,OSError,KeyError) as exc:parser.exit(1,f'Workspace operation failed: {exc}\n')

if __name__=='__main__':main()

'use strict';
const $ = id => document.getElementById(id);
let projects = [], project, edit, localMedia = new Map(), mediaUrls = [];
const storageKey = slug => `muse-cut-v2:${slug}`;
const notice = text => { $('notice').textContent = text; };
function el(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
function save() { try { localStorage.setItem(storageKey(project.slug), JSON.stringify(edit)); } catch { notice('Browser storage unavailable. Download edit.json to keep your changes.'); } }
function download(name, data) { const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type:'application/json'})); const a = el('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
function defaultEdit(p) { return {width:1280,height:720,fps:24,shots:p.shots.map((s,i) => ({shotId:s.shotId,inSec:0,durationSec:i===p.shots.length-1?4:3}))}; }
function stats() {
  $('stats').replaceChildren();
  const footage = project.shots.filter(s => s.videoUrl || localMedia.has(s.shotId)).length;
  for (const [value, label] of [[`${edit.shots.reduce((t,s)=>t+Number(s.durationSec),0).toFixed(1)}s`,'edited runtime'],[`${project.shots.length}`,'shots'],[`${footage}/${project.shots.length}`,'footage available'],[`${project.shots.filter(s=>s.status==='redo').length}`,'redos requested']]) {
    const block = el('div', undefined, 'stat'); block.append(el('strong',value),el('span',label)); $('stats').append(block);
  }
}
function setProject(slug) {
  project = projects.find(p=>p.slug===slug) || projects[0]; if (!project) throw new Error('No repository projects found');
  $('project-select').value = project.slug;
  mediaUrls.forEach(URL.revokeObjectURL); mediaUrls=[]; localMedia.clear();
  try { edit = JSON.parse(localStorage.getItem(storageKey(project.slug)) || 'null'); } catch { edit=null; }
  if (!edit || !Array.isArray(edit.shots) || edit.shots.some(c => !project.shots.some(s=>s.shotId===c.shotId))) edit = structuredClone(project.edit?.shots ? project.edit : defaultEdit(project));
  const params = new URLSearchParams(location.search); params.set('project',project.slug); history.replaceState(null,'',`?${params}`);
  $('storyboard-link').href = `${location.pathname.endsWith('storyboard.html')?'index.html':'storyboard.html'}?project=${encodeURIComponent(project.slug)}`;
  $('project-header').replaceChildren(el('h2',project.title),el('p',`${project.shots.length} source shots · ${project.durationSec}s generation plan · ${project.videoUrl?'saved final available':'final video not saved yet'}`));
  $('final-player').hidden = !project.videoUrl;
  const final = $('final-video'); final.pause(); final.removeAttribute('src'); final.removeAttribute('poster');
  if(project.videoUrl) { final.src=project.videoUrl; if(project.posterUrl) final.poster=project.posterUrl; $('download-final').href=project.videoUrl; }
  $('commands').textContent = `./scripts/local-video.sh import projects/${project.slug} /path/to/downloaded-clips\n./scripts/local-video.sh assemble projects/${project.slug}\n./scripts/local-video.sh verify projects/${project.slug}`;
  $('artifact-select').replaceChildren(...Object.keys(project.artifacts||{}).map(k=>{const o=el('option',k);o.value=k;return o;})); renderArtifact(); render();
  notice('Real repository project loaded. Download edit.json after changing trims. Attach local clips to preview before importing them with Swift.');
}
function renderArtifact() { $('artifact-text').textContent = project.artifacts[$('artifact-select').value] || 'No artifact saved.'; }
function renderCurve() {
  const svg = $('curve'); svg.replaceChildren();
  const line = document.createElementNS('http://www.w3.org/2000/svg','polyline');
  line.setAttribute('points',project.shots.map((s,i)=>`${15+i/Math.max(1,project.shots.length-1)*870},${80-Number(s.tension??0)*7}`).join(' '));
  line.setAttribute('fill','none'); line.setAttribute('stroke','#d3ff7b'); line.setAttribute('stroke-width','2'); svg.append(line);
}
function render() {
  stats(); renderCurve(); $('shots').replaceChildren();
  for (const shot of project.shots) {
    let cut = edit.shots.find(s=>s.shotId===shot.shotId);
    if (!cut) { cut={shotId:shot.shotId,inSec:0,durationSec:3}; edit.shots.push(cut); }
    const card=el('article',undefined,'shot'), media=el('div',undefined,'media'), content=el('div',undefined,'shot-content');
    const source=localMedia.get(shot.shotId) || shot.videoUrl;
    let video;
    if(source) {
      video=el('video'); video.controls=true; video.playsInline=true; video.preload='metadata'; video.src=source;
      video.addEventListener('timeupdate',()=>{ if(video.currentTime>=Number(cut.inSec)+Number(cut.durationSec))video.pause(); });
      media.append(video);
    } else {
      media.append(el('span','FOOTAGE NOT SAVED','plan-label'),el('div',`${shot.size} · ${shot.location}`,'plan-frame'));
    }
    const top=el('div',undefined,'shot-top'); top.append(el('span',shot.shotId,'shot-id'),el('span',`${shot.size} / ${shot.movement} · ${shot.status}`));
    content.append(top,el('h3',shot.action),el('p',shot.emotionalBeat));
    const trims=el('div',undefined,'trims');
    for(const [key,title] of [['inSec','Start (seconds)'],['durationSec','Use (seconds)']]) {
      const label=el('label',title),input=el('input'); input.type='number'; input.min=key==='inSec'?'0':'0.25'; input.step=String(1/(edit.fps||24)); input.value=cut[key]; input.setAttribute('aria-label',`${shot.shotId} ${title}`);
      input.onchange=()=>{
        const value=Number(input.value), previous=cut[key]; cut[key]=value;
        const duration = video && Number.isFinite(video.duration) ? video.duration : (shot.sourceDurationSec || shot.durationSec || 10);
        if(!Number.isFinite(value) || cut.inSec<0 || cut.durationSec<=0 || Number(cut.inSec)+Number(cut.durationSec)>duration+.02) {cut[key]=previous; input.value=previous;notice(`${shot.shotId}: trim must fit within the ${duration.toFixed(2)} second source.`);return;}
        const fps=edit.fps||24; cut[key]=Math.round(value*fps)/fps; input.value=cut[key]; save(); stats(); notice(`${shot.shotId} trim saved in this browser. Download edit.json for local assembly.`);
      };
      label.append(input); trims.append(label);
    }
    content.append(trims);
    const actions=el('div',undefined,'shot-actions');
    if(video) {const play=el('button','Play cut');play.onclick=()=>{video.currentTime=Number(cut.inSec); video.play().catch(e=>notice(e.message));};actions.append(play);}
    const attach=el('label','Attach clip','file-label'),file=el('input');file.type='file';file.accept='video/mp4,video/quicktime,video/x-m4v';file.hidden=true;
    file.onchange=()=>{if(!file.files[0])return;const url=URL.createObjectURL(file.files[0]);mediaUrls.push(url);localMedia.set(shot.shotId,url);render();notice(`${shot.shotId}: local preview attached. Use the Swift import command to save this take in the project.`);};attach.append(file);actions.append(attach);
    const redo=el('button','Redo this shot');actions.append(redo);content.append(actions);
    const redoSection=el('div');redoSection.hidden=true;const reason=el('textarea');reason.className='redo-box';reason.placeholder='What went wrong? e.g. knees bend at 3 seconds; keep the wide framing.';reason.setAttribute('aria-label',`${shot.shotId} redo reason`);
    const request=el('button','Copy Muse redo prompt'),exportRequest=el('button','Download redo request');
    const requestData=()=>({project:project.slug,shotId:shot.shotId,reason:reason.value.trim(),requestedAt:new Date().toISOString()});
    const prompt=()=>`Redo only ${shot.shotId} for projects/${project.slug}. Problem: ${reason.value.trim()}\nUse the latest prompts/${shot.shotId}.txt, locked characters and references. Keep one readable action: ${shot.action}. Deliver the payoff before 4 seconds, hold a clean end pose. Preserve period wuxia staging and rigid straight-kneed jiangshi when present. Keep good takes for all other shots. Save a new version, provide a downloadable MP4 named ${shot.shotId}.mp4 and record the exact prompt SHA256. Mark generated/unreviewed; do not claim it is approved.`;
    request.onclick=async()=>{if(!reason.value.trim()){notice('Describe the specific defect first.');reason.focus();return;}try{await navigator.clipboard.writeText(prompt());shot.status='redo';redo.textContent='Redo requested';stats();notice('Redo prompt copied. Paste it into Muse to generate the replacement.');}catch{notice('Clipboard unavailable. The redo prompt is shown below.');const text=el('pre',prompt());redoSection.append(text);}};
    exportRequest.onclick=()=>{if(!reason.value.trim()){notice('Describe the specific defect first.');return;}download(`redo-${shot.shotId}.json`,requestData());};
    redoSection.append(reason,request,exportRequest);content.append(redoSection);redo.onclick=()=>{redoSection.hidden=!redoSection.hidden;if(!redoSection.hidden)reason.focus();};
    const details=el('details'),summary=el('summary','Shot plan & continuity');details.append(summary);
    for(const [label,key] of [['Action beats','choreography'],['Staging','background'],['Camera','cameraChoreography'],['Light','lighting'],['Motion','motion'],['World rules','loreNotes'],['Sound','soundMood']]) if(shot[key])details.append(el('p',`${label}: ${shot[key]}`));
    content.append(details);card.append(media,content);$('shots').append(card);
  }
}
$('project-select').onchange=e=>setProject(e.target.value);
$('artifact-select').onchange=renderArtifact;
$('export-edit').onclick=()=>{save();download('edit.json',edit);notice(`Move edit.json into projects/${project.slug}/ before assembling.`);};
$('reset-edit').onclick=()=>{edit=defaultEdit(project);save();render();notice('Short-cut draft: 3 seconds per shot, 4 seconds on the ending. Review the footage and move trims to the strongest action.');};
fetch('catalog.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`Catalog returned HTTP ${r.status}`);return r.json();}).then(data=>{
  projects=data.projects;
  $('project-select').replaceChildren(...projects.map(p=>{const o=el('option',p.title);o.value=p.slug;return o;}));
  setProject(new URLSearchParams(location.search).get('project') || 'desert-beggars-vampires');
}).catch(e=>notice(`Could not load project data: ${e.message}. Build with python3 scripts/build-studio.py and serve _site/ over HTTP.`));

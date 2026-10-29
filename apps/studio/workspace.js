'use strict';
const $=id=>document.getElementById(id);
let productions=[];
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
function render(){
  const show=$('show-archived').checked;
  const rank=p=>p.archived?2:p.slug.startsWith('_')?1:0;
  const visible=productions.filter(p=>show||(!p.archived&&!p.slug.startsWith('_'))).sort((a,b)=>rank(a)-rank(b));
  $('projects').replaceChildren();
  for(const p of visible){
    const card=el('article',undefined,'project-card');
    const head=el('p',p.archived?'ARCHIVED':p.slug.startsWith('_')?'REFERENCE EXAMPLE':'ACTIVE PRODUCTION','eyebrow');
    card.append(head,el('h2',p.title),el('p',p.logline||p.mood||'Open this project to inspect its story, shots, footage and edit.'));
    const videoSources=p.shots.filter(s=>s.kind!=='title');
    const available=videoSources.filter(s=>s.videoUrl).length;
    const paused=videoSources.filter(s=>s.status.startsWith('provider error:')||s.status.startsWith('blocked:')).length;
    const redos=videoSources.filter(s=>s.status==='redo').length;
    const row=el('div',`${p.durationSec}s delivery · ${videoSources.length} sources · ${available} available · ${redos} redo · ${paused} paused`,'project-summary');card.append(row);
    const links=el('div',undefined,'shot-actions');
    for(const [label,file] of [['Open cutting room','index.html'],['Storyboard','storyboard.html']]){const a=el('a',label);a.href=`${file}?project=${encodeURIComponent(p.slug)}`;links.append(a);}
    card.append(links);$('projects').append(card);
  }
  $('notice').textContent=`${visible.length} productions shown. Each project has its own saved edit and take history.`;
}
$('show-archived').onchange=render;
$('copy-production').onclick=async()=>{
  const brief=$('story-brief').value.trim();if(!brief){$('notice').textContent='Write the story brief first.';return;}
  const text=`Develop a new independent production in tomaslin/MuseVideoWorkflow. Do not replace other projects. Story brief:\n\n${brief}\n\nRead schemas/production.schema.json and docs/story-production.md. Author a complete projects/<new-unique-slug>/production.json: actual treatment, timed script, fixed cast, lore/look bibles, department packets, shootable shots, generationBrief and editMotivation. Preserve the story constraints and use clear film grammar. Separate ten-second source handles from short edited shots; the edit including local title cards must match the requested duration exactly. Materialize using pipeline/develop.py, validate, prepare stable references, and put missing sources in the shared workspace queue. Keep project footage, edit, manifest and history isolated. Claim batches with pipeline/workspace.py queue --claim (maximum six clips across projects per message), import actual exported MP4s before completing a lease, and redo only defective shots. Do not invent generated files or approvals.`;
  try{await navigator.clipboard.writeText(text);$('notice').textContent='Development request copied. Paste into Muse to start a separate production.';}catch{$('story-brief').value=text;$('notice').textContent='Copy the development request from the text box.';}
};
fetch('catalog.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(`HTTP ${r.status}`);return r.json();}).then(d=>{productions=d.projects;render();}).catch(e=>{$('notice').textContent=`Project catalog unavailable: ${e.message}. Build with scripts/build-studio.py.`;});

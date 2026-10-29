// MuseVideo Studio — prompt-first, deterministic, variant-branching UI.
// No server required. State is kept in localStorage and exportable as JSON.
// Generation itself (images/video/voices) runs through Muse in chat, using
// the prompt packets this UI produces; this UI is the control plane and
// the history of record for what was planned, generated, and changed.
const STAGES = ["brief","treatment","script","script-critiqued","look-and-characters","shot-list","shot-list-critiqued","generating","clips-critiqued","audio","assembled","checked-in","verified","shipped"];
const LOOK = "Desaturated late-light realism, warm practical lamps against cold blue-grey daylight, muted earth palette of rust, faded denim, worn wood and grey sky, locked-off camera with slow push-ins only, 35mm normal lens feel, soft natural grain, no drone shots, no saturated color.";
const MAN = "a weathered man in his late 60s with short grey hair, a lined face, a worn brown work jacket over a faded denim shirt, dark trousers and scuffed boots, moving slowly and deliberately";

// Deterministic hash (FNV-1a) and seeded PRNG — same inputs, same plan.
function hashStr(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return (h>>>0)}
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function slugify(s){return s.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,60)||"untitled"}

let project = null;
function log(action, detail){
  if(!project) return;
  project.history.push({at:new Date().toISOString(), action, detail: detail||"", state: project.state, variant: project.variantId});
  save(); renderSide();
}
function save(){ try{ localStorage.setItem("musevideo-project", JSON.stringify(project)); }catch(e){} }
function loadSaved(){ try{ const raw=localStorage.getItem("musevideo-project"); if(raw) project=JSON.parse(raw); }catch(e){} }

function makeProject(idea, durationSec){
  const seed = hashStr(idea + "|" + LOOK + "|" + MAN);
  const rnd = mulberry32(seed);
  const sizes = ["EWS","WS","FS","MWS","MS","MCU","CU"];
  const moves = ["locked-off","push-in","pull-back","tracking"];
  const shots = [];
  const n = Math.ceil(durationSec/10);
  for(let i=1;i<=n;i++){
    const size = sizes[Math.floor(rnd()*sizes.length)];
    const move = moves[Math.floor(rnd()*moves.length)];
    shots.push({shotId:"s"+String(i).padStart(2,"0"), order:i, size, movement:move,
      location:"see sequence file", action:"one action per shot — edit in the shot artifact",
      emotionalBeat:"one beat per shot", durationSec:10, soundMood:"quiet, sparse",
      lockedLookBlock:LOOK, lockedCharacterBlocks:{"The Man":MAN},
      promptHash: hashStr(idea+"|"+seed+"|s"+i)});
  }
  const seqs = [];
  const per = Math.ceil(n/3);
  for(let s=0;s<3;s++){
    seqs.push({sequenceId:"seq-"+(s+1), title:["Arrival","Reckoning","Release"][s],
      shots: shots.slice(s*per,(s+1)*per)});
  }
  project = {slug: slugify(idea.replace(/^video idea:\s*/i,"")), title: idea,
    idea, durationSec, seed, variantId:"v1", parentVariant:null, changePrompt:null,
    state:"shot-list", look:LOOK, characters:{"The Man":MAN}, sequences:seqs, shots,
    artifacts:{
      brief:"Premise, mood, duration, audience — edit me.",
      treatment:"Opening image, turn, closing image — edit me.",
      script:"Full script, one beat per 10-second shot — edit me.",
      look:LOOK, characters:MAN,
      "shot-list": JSON.stringify(seqs,null,2),
      prompts: shots.map(s=>s.shotId+": "+LOOK+" "+MAN+" "+s.size+" "+s.movement).join("\n"),
      critiques:"Critique 1 (script) and Critique 2 (shot plan) go here, with severity and fix.",
      audio:"Voice stems (one per speaker), music mood, SFX list, captions from the audio script.",
      edl: JSON.stringify({shotOrder: shots.map(s=>s.shotId), totalSec: n*10},null,2),
    },
    history:[], autoAdvance: document.getElementById("auto").checked};
  log("project-created", "seed="+seed+" shots="+n+" batches="+Math.ceil(n/6));
  log("state", "shot-list (brief/treatment/script/look drafted deterministically from the idea)");
  renderAll();
}
function renderStages(){
  const nav=document.getElementById("stages"); nav.innerHTML="";
  STAGES.forEach(st=>{
    const b=document.createElement("button");
    const idx=STAGES.indexOf(st), cur=STAGES.indexOf(project?project.state:"brief");
    b.textContent=(idx<cur?"✓ ":"")+st;
    if(idx<cur) b.classList.add("done");
    if(st===project?.state) b.classList.add("active");
    b.onclick=()=>{ if(project){ project.state=st; log("state", "moved to "+st); renderAll(); } };
    nav.appendChild(b);
  });
}
function renderArtifacts(){
  const sel=document.getElementById("artifact-select");
  const cur=sel.value;
  sel.innerHTML="";
  Object.keys(project.artifacts).forEach(k=>{ const o=document.createElement("option"); o.value=k; o.textContent=k; sel.appendChild(o); });
  if(cur && project.artifacts[cur]!==undefined) sel.value=cur;
  document.getElementById("artifact-editor").value = project.artifacts[sel.value]||"";
  document.getElementById("project-meta").innerHTML =
    "<h2>"+project.title+"</h2><p>slug: <code>"+project.slug+"</code> · seed: <code>"+project.seed+"</code> · variant: <code>"+project.variantId+"</code> · state: <code>"+project.state+"</code> · shots: "+project.shots.length+" · batches: "+Math.ceil(project.shots.length/6)+"</p>";
}
function renderSide(){
  document.getElementById("state").textContent = project ? project.state + " (variant " + project.variantId + ", seed " + project.seed + ")" : "No project yet — run a video idea.";
  const v=document.getElementById("variants"); v.innerHTML="";
  (project?.variantLineage||[project?.variantId]).forEach(id=>{ if(!id) return; const li=document.createElement("li"); li.textContent=id; v.appendChild(li); });
  const h=document.getElementById("history"); h.innerHTML="";
  (project?.history||[]).slice().reverse().forEach(e=>{ const li=document.createElement("li"); li.textContent=e.at+" — "+e.action+" — "+e.detail; h.appendChild(li); });
}
function renderAll(){ if(!project) return; renderStages(); renderArtifacts(); renderSide(); }
function newVariant(changePrompt){
  const old=JSON.parse(JSON.stringify(project));
  const n=(old.variantLineage||["v1"]).length+1;
  project=JSON.parse(JSON.stringify(old));
  project.variantLineage=[...(old.variantLineage||["v1"]), "v"+n];
  project.variantId="v"+n; project.parentVariant=old.variantId; project.changePrompt=changePrompt||"";
  project.seed=hashStr(old.idea+"|"+(changePrompt||"")+"|"+old.seed);
  project.history.push({at:new Date().toISOString(), action:"variant-created", detail:"parent="+old.variantId+" change="+ (changePrompt||"") +" new-seed="+project.seed, state:project.state, variant:project.variantId});
  save(); renderAll();
}
document.getElementById("run").onclick=()=>{
  const idea=document.getElementById("idea").value.trim();
  const dur=parseInt(document.getElementById("duration").value,10)||240;
  if(!idea){ alert("Enter a video idea first."); return; }
  makeProject(idea, dur);
};
document.getElementById("artifact-select").onchange=()=>{
  document.getElementById("artifact-editor").value = project.artifacts[document.getElementById("artifact-select").value]||"";
};
document.getElementById("save-inplace").onclick=()=>{
  const k=document.getElementById("artifact-select").value;
  project.artifacts[k]=document.getElementById("artifact-editor").value;
  log("artifact-edited-inplace", k); renderAll();
};
document.getElementById("save-variant").onclick=()=>{
  const k=document.getElementById("artifact-select").value;
  const change=document.getElementById("change-prompt").value.trim()||("edited "+k);
  newVariant(change);
  project.artifacts[k]=document.getElementById("artifact-editor").value;
  log("artifact-edited-in-variant", k+" in "+project.variantId); renderAll();
};
document.getElementById("branch").onclick=()=>{
  newVariant(document.getElementById("change-prompt").value.trim()||"branched variant");
};
document.getElementById("export").onclick=()=>{
  const blob=new Blob([JSON.stringify(project,null,2)],{type:"application/json"});
  const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=project.slug+".json"; a.click();
};
document.getElementById("import-btn").onclick=()=>document.getElementById("import-file").click();
document.getElementById("import-file").onchange=(e)=>{
  const f=e.target.files[0]; if(!f) return;
  const r=new FileReader(); r.onload=()=>{ project=JSON.parse(r.result); project.variantLineage=project.variantLineage||[project.variantId]; save(); renderAll(); }; r.readAsText(f);
};
// Preload the worked example so the UI is useful before any run.
loadSaved();
if(!project){
  project={slug:"_example-long-way-home", title:"The Long Way Home (example)", idea:"a 4-minute music video in the mood of Johnny Cash's Hurt", durationSec:240, seed:hashStr("example"), variantId:"v1", parentVariant:null, changePrompt:null, state:"shot-list", look:LOOK, characters:{"The Man":MAN}, sequences:[], shots:[], artifacts:{brief:"See projects/_example-long-way-home/brief.md", treatment:"See projects/_example-long-way-home/treatment.md", script:"See projects/_example-long-way-home/script.md", look:LOOK, characters:MAN, "shot-list":"See projects/_example-long-way-home/sequences/", prompts:"Run pipeline/musevideo.py prompt-pack for prompt packets.", critiques:"See docs/critique-rubric.md", audio:"Voice stems, music mood, SFX — see docs/assembly-and-checkin.md", edl:"See pipeline/musevideo.py edl"}, history:[{at:new Date().toISOString(), action:"example-loaded", detail:"worked 4-minute definition", state:"shot-list", variant:"v1"}], variantLineage:["v1"]};
}
renderAll();

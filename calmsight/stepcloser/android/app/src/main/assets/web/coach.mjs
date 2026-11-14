// Calmsight coach for StepCloser: fear rating -> personal coach line (Gemini/Claude),
// ElevenLabs voice, learning + Aiven storage on the Calmsight brain (Modal).
// Purely additive: if the coach is offline, StepCloser works exactly as before.
const BRAIN = (()=>{try{return localStorage.getItem('calmsight-url')}catch{return null}})()
  || 'https://kristisaralidze--calmsight-brain-web.modal.run';
const $ = id => document.getElementById(id);
const native = window.StepCloserNative;
let userId;
try{userId=localStorage.getItem('calmsight-user');if(!userId){userId='u'+Math.random().toString(36).slice(2,10);localStorage.setItem('calmsight-user',userId);}}catch{userId='demo';}

let sessionOpen=false, lastToken=null, busy=false, audio=null;

async function call(path, body){
  const ctrl=new AbortController(); const t=setTimeout(()=>ctrl.abort(),9000);
  try{
    const r=await fetch(BRAIN+path,{method:'POST',headers:{'content-type':'application/json'},
      body:JSON.stringify({userId,...body}),signal:ctrl.signal});
    if(!r.ok)throw new Error('HTTP '+r.status);
    return await r.json();
  }finally{clearTimeout(t);}
}
function status(text){$('coachStatus').textContent=text;}
function speak(reply){
  if(!reply.audioUrl)return;               // app's own guide audio stays available
  if(native?.playUrl){native.playUrl(reply.audioUrl);return;}
  try{audio?.pause();audio=new Audio(reply.audioUrl);audio.play().catch(()=>{});}catch{}
}
function show(reply){
  $('coachLine').textContent=reply.line||'';
  const next=reply.nextStep;
  $('coachNext').hidden=!next||next.advice==='stay';
  if(next)$('coachNext').textContent=next.text;
  if(reply.why)status(reply.why);
}
function diag(){try{return window.StepCloserDiagnostics?.()}catch{return null}}

async function saveProfile(){
  const name=($('coachName')?.value||'').trim();
  try{localStorage.setItem('calmsight-name',name);}catch{}
  try{await call('/profile',{name:name||'there',fear:'spiders',faintHistory:false});}catch{}
}
async function openSession(level){
  try{
    const reply=await call('/start',{situation:'spider stepcloser',level});
    sessionOpen=true;$('coachLine').textContent=reply.line||'';$('coachNext').hidden=true;
    status('Tap a number any time');
  }catch{sessionOpen=false;status('Coach offline · the guide still works');}
}
async function rate(n){
  if(busy)return; busy=true;
  for(const b of $('ratingRow').children)b.classList.toggle('picked',Number(b.dataset.v)===n);
  status('Coach is thinking…');
  try{
    const d=diag();
    if(!sessionOpen)await openSession(d?.level);
    const reply=await call('/turn',{text:String(n),level:d?.level});
    show(reply);speak(reply);
    if(['complete','stop','pause'].includes(reply.action))sessionOpen=false;
    if(!reply.why)status('Tap again when it changes');
  }catch{status('Coach offline · the guide still works');}
  busy=false;
}
function build(){
  const row=$('ratingRow'); if(!row||row.children.length)return;
  for(let v=0;v<=10;v++){
    const b=document.createElement('button');b.type='button';b.textContent=v;b.dataset.v=v;
    if(v>=7)b.classList.add('hot');b.setAttribute('aria-label','Fear '+v+' of 10');
    b.onclick=()=>rate(v);row.append(b);
  }
  try{$('coachName').value=localStorage.getItem('calmsight-name')||'';}catch{}
  $('coachName')?.addEventListener('change',saveProfile);
}
// Follow StepCloser's own session lifecycle without changing its logic.
function watch(){
  const d=diag();
  if(d){
    const live=['starting','active'].includes(d.state);
    if(live&&d.token&&d.token!==lastToken){
      lastToken=d.token;
      for(const b of $('ratingRow').children)b.classList.remove('picked');
      $('coachLine').textContent='';$('coachNext').hidden=true;
      openSession(d.level);
    }
    if(!live&&sessionOpen&&d.state!=='drill'){
      sessionOpen=false;call('/stop',{}).catch(()=>{});
    }
  }
  setTimeout(watch,500);
}
build();saveProfile();watch();

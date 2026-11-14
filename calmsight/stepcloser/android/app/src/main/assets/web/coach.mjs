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
let speak=function(reply){
  if(!reply.audioUrl)return;               // app's own guide audio stays available
  if(native?.playUrl){native.playUrl(reply.audioUrl);return;}
  try{audio?.pause();audio=new Audio(reply.audioUrl);audio.play().catch(()=>{});}catch{}
}
function mode(){return window.CalmsightMode||null;}
function shortLine(t){const s=(t||'').split(/(?<=[.!?])\s+/);let out=s[0]||'';if(out.length<40&&s[1])out+=' '+s[1];return out;}
function lens(reply){
  window.CalmsightLens?.update({rating:reply.display?.big!==''&&reply.display?.big!==undefined?reply.display.big:null,
    line:shortLine(reply.line),label:reply.display?.label||'',visual:reply.display?.visual||'text'});
}
function show(reply){
  $('coachLine').textContent=reply.line||'';lens(reply);
  const next=reply.nextStep;
  $('coachNext').hidden=!next||next.advice==='stay';
  if(next)$('coachNext').textContent=next.text;
  if(reply.why)status(reply.why);
}
function diag(){try{return window.StepCloserDiagnostics?.()}catch{return null}}

async function saveProfile(fear){
  const name=($('coachName')?.value||'').trim(),faint=!!$('coachFaint')?.checked;
  try{localStorage.setItem('calmsight-name',name);localStorage.setItem('calmsight-faint',faint?'1':'');}catch{}
  try{await call('/profile',{name:name||'there',fear:fear||mode()?.fear||'spiders',faintHistory:faint});}catch{}
}
async function openSession(level){
  try{
    const m=mode();
    await saveProfile(m?.fear||window.StepCloserFear||'spiders');
    const reply=await call('/start',{situation:m?m.situation:(window.StepCloserFear==='needles'?'needle practice':'spider stepcloser'),level:m?null:level});
    sessionOpen=true;$('coachLine').textContent=reply.line||'';$('coachNext').hidden=true;
    if(m){lens(reply);speak(reply);}   // real life: the coach opens the conversation
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
    const reply=await call('/turn',{text:String(n),level:mode()?null:d?.level});
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
  try{$('coachName').value=localStorage.getItem('calmsight-name')||'';$('coachFaint').checked=!!localStorage.getItem('calmsight-faint');}catch{}
  $('coachName')?.addEventListener('change',()=>saveProfile());$('coachFaint')?.addEventListener('change',()=>saveProfile());
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
// ---- Voice: the glasses hear you (Meta speech), the coach answers in your ear ----
let voiceAsked=false,listening=false;
async function heard(text){
  const t=(text||'').trim(); if(!t||busy)return;
  busy=true; status('You said: “'+t+'”');
  try{
    const d=diag();
    if(!sessionOpen)await openSession(d?.level);
    const reply=await call('/turn',{text:t,level:mode()?null:d?.level});
    if(reply.rating!==undefined&&reply.rating!==null)
      for(const b of $('ratingRow').children)b.classList.toggle('picked',Number(b.dataset.v)===reply.rating);
    show(reply);speak(reply);
    if(['complete','stop','pause'].includes(reply.action)){sessionOpen=false;
      if(reply.action==='stop')document.getElementById('stop')?.click();}
    if(!reply.why)status(listening?'🎙 Listening · just talk':'Tap or talk');
  }catch{status('Coach offline · the guide still works');}
  busy=false;
}
window.CalmsightCoach={
  heard,
  partial(t){if(t)status('🎙 “'+t+'…”');},
  speechState(s){
    listening=s==='STARTED';
    if(s==='STARTED')status('🎙 Listening · just talk to your coach');
    else if(s==='NEEDS_PERMISSION'&&!voiceAsked){voiceAsked=true;native?.enableVoice?.();}
    else if(String(s).startsWith('UNAVAILABLE')||String(s).startsWith('ERROR'))status('Voice unavailable · tap a number instead');
  }
};
// ---- Laptop preview: the browser's microphone stands in for the glasses ----
let rec=null,recOn=false;
function browserVoice(on){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(native||!SR)return;
  if(!on){recOn=false;try{rec?.stop();}catch{}return;}
  if(recOn)return;
  rec=new SR();rec.lang='en-US';rec.continuous=true;rec.interimResults=true;recOn=true;
  rec.onresult=e=>{
    for(let i=e.resultIndex;i<e.results.length;i++){
      const r=e.results[i],t=r[0].transcript;
      if(r.isFinal){if(!speaking)heard(t);}else window.CalmsightCoach.partial(t);
    }
  };
  rec.onend=()=>{if(recOn)setTimeout(()=>{try{rec.start();}catch{}},300);};
  try{rec.start();window.CalmsightCoach.speechState('STARTED');}catch{}
}
let speaking=false;
const _speak=speak;
speak=function(reply){
  if(native){_speak(reply);return;}
  if(!reply.audioUrl)return;
  speaking=true;
  try{audio?.pause();audio=new Audio(reply.audioUrl);audio.onended=()=>setTimeout(()=>speaking=false,500);
    audio.play().catch(()=>{speaking=false;});}catch{speaking=false;}
};
setInterval(()=>{const d=diag();browserVoice(!!(d&&['starting','active'].includes(d.state)&&mode()));},800);
build();saveProfile();watch();

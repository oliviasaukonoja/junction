// Calmsight app: one phobia at a time, a personal ladder, and an inhibitory-learning
// exposure round (predict → face it → check what actually happened).
import {PHOBIAS,PHOBIA_IDS,MRI_INFO,TENSION,EXPOSE_SECONDS,phobiaFrom,realNow,numberFrom,yesNo,command,
  expectancyFrom,newProgress,startStep,nextAfter,vary,describeVariation,script} from './protocol.mjs';
import {SpiderScene} from './spider.mjs';
import {Lens} from './lens.mjs';
import {FrameDelivery} from './delivery.mjs';
import * as voice from './voice.mjs';

const $=id=>document.getElementById(id),native=window.StepCloserNative;
const KEY='calmsight-v2';
let S={current:null,progress:{},name:'',out:native?'display':'phone',muted:false};
try{S={...S,...JSON.parse(localStorage.getItem(KEY)||'{}')};}catch{}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(S));}catch{}};
const P=()=>S.progress[S.current];
const steps=()=>PHOBIAS[S.current].steps;

let scene=null,lens=null,micOn=false,round=null;
try{scene=new SpiderScene($('scene'));}catch(e){console.warn('3D unavailable',e);}
lens=new Lens($('lens'));
voice.setMuted(!!S.muted);

// ---------------------------------------------------------------- screens
function show(id){for(const s of ['home','picker','setup','session'])$(s).hidden=s!==id;window.scrollTo(0,0);}
function notice(t){$('notice').textContent=t||'';$('notice').hidden=!t;}

function renderHome(){
  if(!S.current||!P()){renderPicker();return;}
  const p=P(),ph=PHOBIAS[S.current],st=ph.steps,i=Math.min(p.step,st.length-1),s=st[i];
  $('focusIcon').textContent=ph.icon;$('focusName').textContent=ph.name;
  $('ladderFill').style.width=Math.round(100*i/(st.length-1||1))+'%';
  $('stepNum').textContent='Step '+(i+1)+' of '+st.length;$('stepName').textContent=s.name;
  $('startStep').textContent=(s.kind==='real'?'Go: ':s.kind==='skill'?'Learn: ':s.kind==='info'?'Listen: ':'Start: ')+s.name+' ▶';
  $('sayHint').textContent=s.kind==='real'?'“I’m in front of the lift now”':'“start”, or “I’m about to get a blood test”';
  const last=p.trials[0];
  $('insight').textContent=last&&last.expect?insightText(last):p.faint&&i===0?'You’ve fainted before, so we start with the skill that prevents it.':'';
  // ladder
  $('ladder').replaceChildren(...st.map((x,k)=>{
    const li=document.createElement('li'),b=document.createElement('button');
    b.className=(k<p.step?'done':'')+(k===i?' current':'');
    const kind={virtual:'🕶 in your glasses',real:'📍 real life',skill:'💪 skill',info:'🎧 listen'}[x.kind];
    b.innerHTML=`<span class="n">${k<p.step?'✓':k+1}</span><span class="t">${esc(x.name)}<small>${esc(x.detail)}</small></span><span class="kind">${kind}</span>`;
    b.onclick=()=>{p.step=k;save();renderHome();};li.append(b);return li;
  }));
  renderProgress();
  $('nameInput').value=S.name||'';$('muteInput').checked=!!S.muted;
  $('outPhone').classList.toggle('selected',S.out==='phone');$('outGlasses').classList.toggle('selected',S.out==='display');
  $('glassesState').textContent=S.out==='display'?(native?(lensReady?'Glasses connected.':'Connects when you start a step.'):'Glasses need the Android app. Preview shows exactly what the lens shows.'):'The preview square shows exactly what the glasses would show.';
  show('home');
}
function insightText(t){
  const e=PHOBIAS[t.phobia].expectancies.find(x=>x.id===t.expect)?.text||'what you feared';
  if(t.happened==='no')return `Last time you were ${t.sureBefore}% sure “${e.toLowerCase()}”. It didn’t happen.`;
  if(t.happened==='partly')return `Last time: “${e.toLowerCase()}” only partly happened, and you stayed.`;
  return `Last time it felt real. That’s okay: repeating with a twist is how it changes.`;
}
function renderProgress(){
  const tr=P().trials;
  $('roundCount').textContent=tr.length+(tr.length===1?' round':' rounds');
  $('progressCard').hidden=!tr.length;
  const last=tr.slice(0,10).reverse();
  if(last.length){
    const w=320,h=110,bw=w/Math.max(last.length,5);
    let bars='';
    last.forEach((t,k)=>{
      const x=k*bw+6,b1=(t.sureBefore??0)/100*(h-20),b2=(t.sureAfter??0)/100*(h-20);
      bars+=`<rect x="${x}" y="${h-b1}" width="${bw/2-4}" height="${b1}" rx="3" fill="#ffc27a"/><rect x="${x+bw/2-3}" y="${h-b2}" width="${bw/2-4}" height="${b2}" rx="3" fill="#8fe3cf"/>`;
    });
    $('chart').innerHTML=`<svg viewBox="0 0 ${w} ${h+16}" role="img" aria-label="How sure you were before and after each round">${bars}<text x="0" y="${h+14}" fill="#9fbab2" font-size="11">■ sure before</text><text x="90" y="${h+14}" fill="#8fe3cf" font-size="11">■ sure after, each round</text></svg>`;
  }else $('chart').innerHTML='';
  $('trials').replaceChildren(...tr.slice(0,5).map(t=>{
    const li=document.createElement('li'),e=PHOBIAS[t.phobia].expectancies.find(x=>x.id===t.expect)?.text||t.expectText||'—';
    li.innerHTML=`<strong>${esc(PHOBIAS[t.phobia].steps[t.step]?.name||'')}</strong> · fear peak ${t.fearPeak??'–'}<small>“${esc(e)}”: ${t.sureBefore??'–'}% → ${t.sureAfter??'–'}% · ${t.happened==='no'?'didn’t happen':t.happened==='partly'?'partly':'happened'}${t.learned?' · learned: '+esc(t.learned):''}</small>`;
    return li;
  }));
}
function renderPicker(){
  $('phobiaGrid').replaceChildren(...PHOBIA_IDS.map(id=>{
    const ph=PHOBIAS[id],b=document.createElement('button');
    b.innerHTML=`<span class="ico">${ph.icon}</span><span><strong>${esc(ph.name)}</strong><small>${esc(ph.blurb)}</small></span>`;
    b.onclick=()=>choosePhobia(id);return b;
  }));
  show('picker');
}
function choosePhobia(id,{viaVoice=false}={}){
  S.current=id;save();
  voice.brain('/profile',{name:S.name||'there',fear:id==='mri'?'spaces':id,faintHistory:!!S.progress[id]?.faint}).catch(()=>{});
  if(S.progress[id]){renderHome();if(viaVoice)greet();return;}
  if(viaVoice){quickSetup(id);return;}
  renderSetup(id);
}
// ---------------------------------------------------------------- setup (personal hierarchy)
let ratings=[],faint=null;
function renderSetup(id){
  const ph=PHOBIAS[id];ratings=ph.steps.map(()=>null);faint=null;
  $('setupEyebrow').textContent=ph.icon+' '+ph.name.toUpperCase();
  $('faintBox').hidden=id!=='needles';
  for(const b of document.querySelectorAll('[data-faint]'))b.classList.remove('selected');
  $('rateList').replaceChildren(...ph.steps.map((s,k)=>{
    const li=document.createElement('li');
    if(s.kind==='skill'||s.kind==='info'){li.innerHTML=`<div class="rn"><strong>${k+1}. ${esc(s.name)}</strong><small>${esc(s.detail)}</small></div>`;return li;}
    li.innerHTML=`<div class="rn"><strong>${k+1}. ${esc(s.name)}</strong><small>${esc(s.detail)}</small></div><div class="dots"></div>`;
    const d=li.querySelector('.dots');
    for(let v=0;v<=10;v++){const b=document.createElement('button');b.textContent=v;b.onclick=()=>{ratings[k]=v;for(const x of d.children)x.classList.toggle('on',x===b);};d.append(b);}
    return li;
  }));
  show('setup');
}
for(const b of document.querySelectorAll('[data-faint]'))b.onclick=()=>{faint=b.dataset.faint==='yes';if(asking)asking.parse(b.dataset.faint);for(const x of document.querySelectorAll('[data-faint]'))x.classList.toggle('selected',x===b);};
$('setupDone').onclick=()=>finishSetup(ratings,faint);
$('setupSkip').onclick=()=>finishSetup(null,faint);
function finishSetup(r,f){
  const id=S.current,p=newProgress(id);p.trials=S.progress[id]?.trials||[];p.ratings=r;p.faint=!!f;p.step=startStep(id,r,!!f);
  S.progress[id]=p;save();
  voice.brain('/profile',{name:S.name||'there',fear:id==='mri'?'spaces':id,faintHistory:!!f}).catch(()=>{});
  renderHome();
  const s=steps()[p.step];
  voice.say(`Your ladder is ready. We start at step ${p.step+1}: ${s.name}. Say start when you’re ready.`);
}
async function quickSetup(id){
  let f=false;
  if(id==='needles'){
    renderSetup(id);
    const a=await askYesNo('Have you ever fainted, or nearly fainted, around needles or blood?');
    f=a==='yes';
  }
  finishSetup(null,f);
}
// ---------------------------------------------------------------- voice routing
let asking=null;   // current question waiting for an answer (tap or voice)
voice.onHeard(text=>{
  $('heard').textContent='🎙 “'+text+'”';$('heard').hidden=false;lens.set({heard:text});
  if(command(text)==='stop'&&round){stopRound(true);return;}
  if(asking&&asking.parse(text)!==undefined)return;
  if(round?.phase==='expose'){round.onSpeech(text);return;}
  if(!round)homeSpeech(text);
});
voice.onPartial(t=>{$('heard').textContent='🎙 '+t+'…';$('heard').hidden=false;});
voice.onState(s=>{
  micOn=s==='STARTED';$('micBtn').setAttribute('aria-pressed',micOn);$('micLabel').textContent=micOn?'Listening':'Talk';
  if(s==='DENIED')notice('Microphone blocked. Allow it in the browser, or tap the answers.');
  if(s==='UNAVAILABLE')notice('Voice needs Chrome on a laptop, or the glasses app. You can tap instead.');
});
$('micBtn').onclick=()=>{voice.listen(!micOn);if(!micOn&&!round)setTimeout(greet,300);};
function greet(){
  if(round)return;
  if(!S.current||!P()){voice.say('Hi. What would you like to stop being afraid of? Spiders, needles, lifts, or an MRI scan?');return;}
  const s=steps()[P().step];
  voice.say(`${S.name?'Hi '+S.name+'. ':'Hi. '}You’re working on ${PHOBIAS[S.current].short}, step ${P().step+1}: ${s.name}. Say start, or tell me where you are right now.`);
}
function homeSpeech(text){
  const ph=phobiaFrom(text),c=command(text),t=text.toLowerCase();
  if(ph&&realNow(text)){
    if(ph!==S.current||!P()){S.current=ph;if(!S.progress[ph]){S.progress[ph]=newProgress(ph);}save();}
    renderHome();startRound(realStepIndex(ph),{realText:text});return;
  }
  if(ph&&(ph!==S.current||!P())){choosePhobia(ph,{viaVoice:true});return;}
  if(c==='start'||c==='again'){if(S.current&&P())startRound(P().step);return;}
  if(c==='harder'&&P()){P().step=Math.min(steps().length-1,P().step+1);save();renderHome();greet();return;}
  if(c==='easier'&&P()){P().step=Math.max(0,P().step-1);save();renderHome();greet();return;}
  if(/how am i|progress|doing/.test(t)&&P()){const l=P().trials[0];voice.say(l?insightText(l):'No rounds yet. Say start for your first one.');return;}
  if(/change|different|another|switch/.test(t)){renderPicker();voice.say('Which one? Spiders, needles, lifts, or MRI?');return;}
  if(!S.current)voice.say('Tell me what scares you: spiders, needles, lifts, or a scan.');
}
function realStepIndex(ph){
  const st=PHOBIAS[ph].steps,p=S.progress[ph];
  if(p&&st[p.step]?.kind==='real')return p.step;
  for(let k=p?p.step:0;k<st.length;k++)if(st[k].kind==='real')return k;
  return st.length-1;
}
// ---------------------------------------------------------------- asking (tap or voice)
function ask({line,options=[],grid=false,fear=false,hint,parse,skip,lensOptions}){
  return new Promise((resolve,reject)=>{
    $('askLine').textContent=line;$('askOptions').className='ask-options'+(grid?' grid':'');
    $('askOptions').replaceChildren(...options.map(o=>{const b=document.createElement('button');b.textContent=o.label;b.onclick=()=>done(o.value);return b;}));
    if(skip){const b=document.createElement('button');b.className='quiet';b.textContent=skip;b.onclick=()=>done(null);$('askOptions').append(b);}
    $('fearRow').hidden=!fear;
    lens.set({mode:'prompt',line,options:lensOptions||options.map(o=>o.label).slice(0,4),hint:hint||'',heard:''});
    asking={parse:t=>{const v=parse(t);if(v===undefined||v===null)return undefined;done(v);return v;},reject};
    function done(v){if(asking?.reject!==reject)return;asking=null;voice.hush();resolve(v);}
    voice.say(line);
  });
}
const pct=[10,25,50,75,90,100].map(v=>({label:v+'%',value:v}));
function askYesNo(line){return ask({line,options:[{label:'Yes',value:'yes'},{label:'No',value:'no'}],hint:'Say yes or no',parse:yesNo});}
// fear row is shared: tapping it during a round reports a rating
$('fearRow').replaceChildren(...Array.from({length:11},(_,v)=>{const b=document.createElement('button');b.textContent=v;if(v>=7)b.className='hot';
  b.onclick=()=>{if(asking&&asking.fearTap)asking.fearTap(v);else round?.rate(v);};return b;}));
function askFear(line){
  return new Promise((resolve,reject)=>{
    $('askLine').textContent=line;$('askOptions').replaceChildren();$('fearRow').hidden=false;
    lens.set({mode:'prompt',line,options:[],hint:'Say a number, 0 to 10'});
    const fin=v=>{if(asking?.reject!==reject)return;asking=null;voice.hush();resolve(v);};
    asking={parse:t=>{const v=numberFrom(t,10);if(v===null)return undefined;fin(v);return v;},fearTap:fin,reject};
    voice.say(line);
  });
}
// ---------------------------------------------------------------- the round
class Aborted extends Error{}
function setPhase(p,label){
  round.phase=p;$('sessEyebrow').textContent='STEP '+(round.step+1)+' · '+label.toUpperCase();
  const order=['predict','expose','check'];
  for(const s of $('phases').children){s.classList.toggle('on',s.dataset.p===p);s.classList.toggle('past',order.indexOf(s.dataset.p)<order.indexOf(p));}
}
async function startRound(stepIdx,opts={}){
  if(round)return;
  const ph=S.current,s=PHOBIAS[ph].steps[stepIdx];
  round={step:stepIdx,phobia:ph,phase:'predict',ratings:[],aborted:false,onSpeech(){},rate(){},timers:[]};
  for(const b of $('fearRow').children)b.classList.remove('on');$('sessTimer').textContent='';
  $('result').hidden=true;$('askLine').textContent='';$('askOptions').replaceChildren();$('fearRow').hidden=true;
  $('phases').hidden=!(s.kind==='virtual'||s.kind==='real');
  show('session');
  if(!micOn&&(native||voice.browserMic))voice.listen(true);
  const ok=await lensOn();if(!ok){round=null;renderHome();return;}
  lens.set({mode:'prompt',title:'Step '+(stepIdx+1)+' · '+s.name,fear:null,line:'',options:[]});
  try{
    if(s.kind==='skill')await runTension();
    else if(s.kind==='info')await runInfo();
    else await runExposure(s,opts);
  }catch(e){if(!(e instanceof Aborted))console.error(e);}
  finally{if(round&&!round.keepSession)cleanupRound();}
}
function cleanupRound(){
  if(!round)return;
  round.timers.forEach(clearTimeout);round.timers=[];clearInterval(round.tick);
  scene?.clear();voice.hush();
  if(round.brainOpen)voice.brain('/stop',{}).catch(()=>{});
  const keep=round.keepSession;round=null;asking=null;
  if(!keep){lensOff();renderHome();}
}
function stopRound(early){
  if(!round)return;
  if(round.phase==='expose'&&round.endExpose){round.stoppedEarly=early;round.endExpose();return;}
  const quiet=round.keepSession;round.keepSession=false;
  round.aborted=true;asking?.reject(new Aborted());asking=null;round.cancel?.(new Aborted());
  cleanupRound();if(!quiet)voice.say('Stopped. Well done for trying. You can start again whenever you want.');
}
$('stopBtn').onclick=()=>stopRound(true);
$('muteBtn').onclick=()=>{S.muted=!S.muted;save();voice.setMuted(S.muted);$('muteBtn').textContent=S.muted?'🔇 Voice off':'🔈 Voice on';};
$('muteBtn').textContent=S.muted?'🔇 Voice off':'🔈 Voice on';
const sleep=ms=>new Promise((res,rej)=>{const t=setTimeout(res,ms);round?.timers.push(t);round&&(round.cancel=rej);});
const guard=()=>{if(!round||round.aborted)throw new Aborted();};

async function runExposure(s,opts){
  const ph=PHOBIAS[round.phobia],r=round;
  // 1. PREDICT — a specific, testable fear (expectancy) and how sure they are
  setPhase('predict','Predict');
  const expOpts=ph.expectancies.map(e=>({label:e.text,value:e.id}));
  let expect=expectancyFrom(opts.realText||'',r.phobia);
  if(!expect)expect=await ask({line:script(r.phobia,r.step,'predict'),options:expOpts,hint:'Say it in your words',
    parse:t=>expectancyFrom(t,r.phobia)??(t.split(/\s+/).length>=3?'other:'+t:undefined)});
  guard();
  r.expect=expect.startsWith?.('other:')?null:expect;r.expectText=expect.startsWith?.('other:')?expect.slice(6):ph.expectancies.find(e=>e.id===expect)?.text;
  r.sureBefore=await ask({line:`How sure are you that this will happen: “${r.expectText||'what you fear'}”? From 0 to 100.`,
    options:pct,grid:true,hint:'Say a number, 0 to 100',parse:t=>numberFrom(t,100)});
  guard();
  r.fear0=await askFear(script(r.phobia,r.step,'fear0'));guard();r.ratings.push(r.fear0);lens.set({fear:r.fear0});
  // 2. FACE IT — varied stimulus, no safety behaviours, name the feeling
  setPhase('expose','Face it');
  $('askOptions').replaceChildren();$('fearRow').hidden=false;
  const real=s.kind==='real',faintRisk=r.phobia==='needles'&&P().faint;
  const plan=real?null:vary(s.plan);r.variation=real?'':describeVariation(plan,s.plan);
  const seconds=real?0:(s.plan.minutes?s.plan.minutes*60:EXPOSE_SECONDS);
  const intro=script(r.phobia,r.step,'expose')+(r.variation&&P().trials.some(t=>t.step===r.step)?' This time it’s '+r.variation+'.':'');
  $('askLine').textContent=intro;
  if(real)lens.set({mode:'calm',big:'With you',sub:'Fear any time: 0–10',line:intro,options:[]});
  else if(scene){scene.show({...plan,count:plan.count||1});lens.set({mode:'stim',source:$('scene'),line:intro,options:[]});}
  r.started=performance.now();
  voice.say(intro);
  // brain session for free conversation during the exposure
  voice.brain('/start',{situation:real?s.place:s.name+' ('+ph.name+' practice)',mode:'exposure',level:r.step+1},6000)
    .then(()=>{r.brainOpen=true;}).catch(()=>{});
  r.rate=v=>{r.ratings.push(v);lens.set({fear:v});for(const b of $('fearRow').children)b.classList.toggle('on',Number(b.textContent)===v);
    if(v>=9&&!real)coach('That’s a lot, and you’re still here. Keep watching. Say stop if you need to.');
    else if(r.ratings.length>2&&v<r.ratings[r.ratings.length-2]-1)coach('Notice that. The fear is coming down on its own.');};
  r.onSpeech=async text=>{
    const n=numberFrom(text,10);
    if(n!==null&&text.split(/\s+/).length<=5){r.rate(n);return;}
    if(/\b(done|finished|i did it|made it|it'?s over|out now)\b/i.test(text)&&real){r.endExpose?.();return;}
    try{const rep=await voice.brain('/turn',{text},9000);if(r!==round||r.phase!=='expose')return;
      if(rep.rating!=null)r.rate(rep.rating);coach(rep.line);}catch{}
  };
  await new Promise(res=>{
    r.endExpose=res;
    const T=(sec,fn)=>r.timers.push(setTimeout(()=>{if(round===r&&r.phase==='expose')fn();},sec*1000));
    if(faintRisk){[18,48,78].forEach(t=>{T(t,()=>coach(script(r.phobia,r.step,'tension')));T(t+13,()=>coach(script(r.phobia,r.step,'release')));});}
    T(real?40:25,()=>coach(script(r.phobia,r.step,'label')));
    T(real?75:45,()=>coach(script(r.phobia,r.step,'check')));
    T(real?110:66,()=>coach(script(r.phobia,r.step,'stay')));
    if(real){T(150,()=>coach('How is it now, 0 to 10? Say done when you’re through.'));}
    else T(seconds,res);
    r.tick=setInterval(()=>{const e=(performance.now()-r.started)/1000,left=seconds?Math.max(0,seconds-e):e;
      const txt=fmt(left);$('sessTimer').textContent=txt;lens.set({timer:txt});},250);
    if(real){const b=document.createElement('button');b.className='primary';b.textContent='Done, I did it ✓';b.onclick=()=>res();$('askOptions').replaceChildren(b);}
  });
  clearInterval(r.tick);r.timers.forEach(clearTimeout);r.timers=[];r.endExpose=null;
  r.seconds=Math.round((performance.now()-r.started)/1000);
  scene?.clear();guard();
  // 3. CHECK — did the feared outcome happen? how sure now? what did you learn?
  setPhase('check','Check');$('sessTimer').textContent='';lens.set({timer:'',source:null});$('fearRow').hidden=true;
  const what=r.expectText||'what you feared';
  r.happened=await ask({line:(r.stoppedEarly?'You stopped, and that’s okay. ':'Time. ')+`Did it happen: “${what}”?`,
    options:[{label:'No, it didn’t',value:'no'},{label:'Partly',value:'partly'},{label:'Yes, it did',value:'yes'}],hint:'Say yes, no or partly',parse:yesNo});
  guard();
  r.sureAfter=await ask({line:`How sure are you now that “${what}” would happen next time?`,options:pct,grid:true,hint:'Say a number, 0 to 100',parse:t=>numberFrom(t,100)});
  guard();
  r.learned=await ask({line:script(r.phobia,r.step,'learn'),options:[],hint:'One sentence, or say skip',skip:'Skip',
    parse:t=>/^\s*skip\b/i.test(t)?'':t});
  guard();
  // save + next step
  const trial={phobia:r.phobia,step:r.step,date:Date.now(),expect:r.expect,expectText:r.expectText,sureBefore:r.sureBefore,sureAfter:r.sureAfter,
    happened:r.happened,fear0:r.fear0,fearPeak:Math.max(...r.ratings),fearEnd:r.ratings[r.ratings.length-1],stoppedEarly:!!r.stoppedEarly,
    seconds:r.seconds,variation:r.variation,learned:r.learned||'',real};
  const p=P();p.trials.unshift(trial);p.trials=p.trials.slice(0,100);
  const next=nextAfter(trial,r.step,r.phobia);
  if(next.advice==='harder')p.step=Math.max(p.step,next.step);
  save();
  voice.brain('/trial',trial,5000).catch(()=>{});
  if(r.brainOpen){r.brainOpen=false;voice.brain('/stop',{}).catch(()=>{});}
  showResult(trial,next);
}
function coach(line){if(!line||!round)return;$('askLine').textContent=line;lens.set({line});voice.say(line);}
function showResult(t,next){
  const e=(t.expectText||'what you feared');
  const el=$('result');el.hidden=false;$('askLine').textContent='';$('askOptions').replaceChildren();
  const verdict=t.happened==='no'?'It didn’t happen.':t.happened==='partly'?'It only partly happened.':'It happened, and you got through it.';
  el.innerHTML=`<span class="eyebrow">WHAT YOUR BRAIN JUST LEARNED</span><h2>${esc(verdict)}</h2>
   <p class="muted">You predicted: “${esc(e)}”</p>
   <div class="violation"><span><span class="pct before">${t.sureBefore??'–'}%</span><br><small class="muted">sure before</small></span><span class="arrow">→</span><span><span class="pct after">${t.sureAfter??'–'}%</span><br><small class="muted">sure now</small></span></div>
   <p class="muted">Fear ${t.fear0} at the start, peak ${t.fearPeak}, ${t.fearEnd} at the end${t.seconds?' · '+t.seconds+' s':''}${t.variation?' · '+esc(t.variation):''}</p>
   ${t.learned?`<p>You learned: <strong>${esc(t.learned)}</strong></p>`:''}
   <p>${esc(next.why)}</p><div class="row"></div>`;
  const row=el.querySelector('.row'),st=PHOBIAS[t.phobia].steps;
  const btn=(label,cls,fn)=>{const b=document.createElement('button');b.className=cls;b.textContent=label;b.onclick=fn;row.append(b);};
  const go=k=>{round.keepSession=false;cleanupRound();startRound(k);};
  if(next.advice==='harder')btn('Next: '+st[next.step].name+' ▶','primary big',()=>go(next.step));
  btn(next.advice==='harder'?'Same step again, new variation':'Again, a new variation ▶',next.advice==='harder'?'secondary big':'primary big',()=>go(t.step));
  if(next.advice==='easier')btn('One step back: '+st[next.step].name,'secondary big',()=>go(next.step));
  btn('Done for today','quiet big',()=>{round.keepSession=false;cleanupRound();});
  round.keepSession=true;
  lens.set({mode:'prompt',line:verdict+' '+(t.sureBefore??'')+'% → '+(t.sureAfter??'')+'%',options:next.advice==='harder'?['Say “next” for the next step','Say “again” to repeat']:['Say “again” for a new variation','Say “stop” to finish'],hint:'',fear:t.fearEnd});
  voice.say(`${verdict} You were ${t.sureBefore} percent sure, now ${t.sureAfter}. ${next.why} ${next.advice==='harder'?'Say next, or again.':'Say again, or stop.'}`);
  asking={parse:x=>{const c=command(x);
      if(c==='harder'||/\bnext\b/i.test(x)){asking=null;go(next.advice==='harder'?next.step:t.step);return 1;}
      if(c==='again'||c==='start'){asking=null;go(t.step);return 1;}
      if(c==='easier'){asking=null;go(Math.max(0,t.step-1));return 1;}
      return undefined;},reject(){}};
}
// Applied tension (Öst): tense 10–15 s until the face feels warm, release 20–30 s, 5 rounds.
async function runTension(){
  const r=round;setPhase('expose','Applied tension');
  $('askLine').textContent='Applied tension stops the blood-pressure drop that makes people faint. Sit down. Tense your arms, legs and stomach when I say, until your face feels warm.';
  const skip=document.createElement('button');skip.className='quiet';skip.textContent='I know this, skip ▶';skip.onclick=()=>{r.skipped=true;r.cancel?.(new Aborted());};
  $('askOptions').replaceChildren(skip);
  await voice.say('This is applied tension. It stops the drop in blood pressure that makes people faint. Sit down. When I say tense, squeeze your arms, legs and stomach, and hold until your face feels warm. Then release.');
  try{
    for(let k=1;k<=TENSION.rounds;k++){
      for(const [ph,sec] of [['tense',TENSION.tense],['release',TENSION.release]]){
        guard();
        if(ph==='tense')voice.say(k===1?'Tense now. Squeeze everything. Hold.':'Tense again. Hold it.');else voice.say(k===TENSION.rounds?'Release. That’s the last one.':'And release. Let it go, sit normally.');
        const t0=performance.now();
        while((performance.now()-t0)/1000<sec){guard();lens.set({mode:'tension',phase:ph,phaseLeft:sec-(performance.now()-t0)/1000,tenseSec:TENSION.tense,releaseSec:TENSION.release,round:k,rounds:TENSION.rounds,line:''});await sleep(200);}
      }
    }
  }catch(e){if(!r.skipped)throw e;}
  guard();
  const p=P();if(p.step===r.step)p.step=r.step+1;save();
  await voice.say('Well done. Practise this five times a day this week. During every needle step, if you feel faint, tense like this.');
}
async function runInfo(){
  const r=round;setPhase('expose','What happens');
  for(const [k,line] of MRI_INFO.entries()){
    guard();$('askLine').textContent=line;lens.set({mode:'prompt',line,options:[],hint:(k+1)+' / '+MRI_INFO.length});
    MRI_INFO[k+1]&&voice.prefetch(MRI_INFO[k+1]);
    await voice.say(line);await sleep(700);
  }
  guard();const p=P();if(p.step===r.step)p.step=r.step+1;save();
}
// ---------------------------------------------------------------- glasses output
const delivery=new FrameDelivery('auto');
let lensReady=false,armed=false,token='',serial=0,lensWaiter=null;
async function lensOn(){
  lens.set({mode:'prompt',line:'',options:[]});
  if(S.out!=='display'||!native)return true;
  if(!lensReady){
    notice('Connecting your glasses…');
    native.connect();
    const ok=await new Promise(res=>{lensWaiter=res;setTimeout(()=>res(false),45000);});lensWaiter=null;
    if(!ok){notice('Glasses didn’t connect. Check they’re on and paired, or switch to phone preview in Settings.');return false;}
    notice('');
  }
  token=String(++serial);delivery.reset(token);armed=false;native.arm(token);return true;
}
function lensOff(){lens.clear();armed=false;delivery.reset('');if(S.out==='display'&&native)native.stop();}
window.StepCloserCallbacks={event(e){
  switch(e.type){
    case 'lens':
      if(e.status==='READY'){lensReady=true;lensWaiter?.(true);}
      else if(['ERROR','LOST'].includes(e.status)){lensReady=false;lensWaiter?.(false);if(round)notice('Glasses: '+(e.message||'connection lost'));}
      break;
    case 'disconnected':lensReady=false;break;
    case 'armed':if(e.token===token)armed=true;break;
    case 'frameResult':delivery.acknowledge(e,performance.now());break;
    case 'message':notice(e.message);break;
    case 'speech':voice.heard(e.text);break;
    case 'speechPartial':voice.partial(e.text);break;
    case 'speechState':voice.nativeState(e.state);if(e.state==='NEEDS_PERMISSION')native?.enableVoice?.();break;
    case 'voiceLaunch':if(!round){renderHome();voice.listen(true);setTimeout(greet,600);}break;
  }
}};
function loop(now){
  if(round||lens.visible){
    const r=round,t=r?.started?(performance.now()-r.started)/1000:now/1000;
    if(scene?.visible)scene.render(t,(lens.s.source&&scene.plan?.speed)||1);
    lens.render(now/1000);
    if(S.out==='display'&&native&&armed&&lens.visible){
      const q=delivery.begin(now);
      if(q){const ok=native.submitFrame(lens.capture(delivery.options.size,delivery.options.quality),q.token,q.sequence,q.capturedAtMs);if(ok!==true)delivery.rejected(q.sequence);}
      if(delivery.inFlight&&now-delivery.inFlight.capturedAtMs>5000)delivery.rejected(delivery.inFlight.sequence);
    }
  }
  requestAnimationFrame(loop);
}
// ---------------------------------------------------------------- wiring
$('focusSwitch').onclick=renderPicker;
$('startStep').onclick=()=>startRound(P().step);
$('realBtn').onclick=()=>startRound(realStepIndex(S.current));
$('nameInput').onchange=()=>{S.name=$('nameInput').value.trim();save();choosePhobia(S.current);};
$('muteInput').onchange=()=>{S.muted=$('muteInput').checked;save();voice.setMuted(S.muted);};
$('outPhone').onclick=()=>{S.out='phone';save();renderHome();};
$('outGlasses').onclick=()=>{S.out='display';save();renderHome();};
$('resetPhobia').onclick=()=>renderSetup(S.current);
window.addEventListener('keydown',e=>{if(e.key==='Escape'&&round)stopRound(true);});
const fmt=s=>{s=Math.max(0,Math.round(s));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');};
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
S.current&&P()?renderHome():renderPicker();
requestAnimationFrame(loop);
window.CalmsightDebug={S,startRound,heard:voice.heard,get round(){return round;}};

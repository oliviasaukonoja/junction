import {Practice,LEVELS} from './engine.mjs';
import {SpiderScene} from './spider.mjs';
import {PROMPTS} from './prompts.mjs';
import {guideCue} from './motion.mjs';
import {FrameDelivery} from './delivery.mjs';
const $=id=>document.getElementById(id),native=window.StepCloserNative,practice=new Practice();
let scene=null,player=null,muted=false,armed=false,startWall=0,guideIndex=0,lastMotionCue='';
const delivery=new FrameDelivery('auto');
let pendingStart=null,history=[],saved=false,clearIntent=false;
const connectionLines=[];
try{
  practice.mode=localStorage.getItem('stepcloser3d-mode')||(native?'display':'phone');
  if(!['phone','display'].includes(practice.mode))practice.mode=native?'display':'phone';
  history=JSON.parse(localStorage.getItem('stepcloser3d-history')||'[]');
  if(!Array.isArray(history))history=[];
  history=history.filter(x=>x&&typeof x==='object'&&Number.isInteger(x.level));
}catch{}
try{
  const options=JSON.parse(localStorage.getItem('stepcloser3d-options')||'{}');
  $('spiderCount').value=String([1,3,5,10,20].includes(options.count)?options.count:1);
  $('motionSpeed').value=String([.5,1,1.5,2].includes(options.speed)?options.speed:1);
  $('deliveryProfile').value=['auto','fast','balanced','sharp'].includes(options.profile)?options.profile:'auto';
  $('matchMirror').checked=options.mirror!==false;
}catch{
  $('spiderCount').value='1';$('motionSpeed').value='1';$('deliveryProfile').value='auto';$('matchMirror').checked=true;
}
function applyOptions(){
  practice.configureOptions(Number($('spiderCount').value),Number($('motionSpeed').value));
  delivery.setProfile($('deliveryProfile').value);
  try{localStorage.setItem('stepcloser3d-options',JSON.stringify({count:practice.spiderCount,speed:practice.motionSpeed,
    profile:delivery.profile,mirror:$('matchMirror').checked}));}catch{}
}
applyOptions();
const notice=message=>{$('notice').textContent=message;$('notice').hidden=!message;};
function stopAudio(){if(player){player.pause();player=null;}native?.stopAudio();}
function say(key){
  $('guideText').textContent=PROMPTS[key]||'You choose the pace.';
  stopAudio();if(muted)return;
  if(native)native.playPrompt(key);
  else{player=new Audio('audio/'+key+'.mp3');player.play().catch(()=>notice('Audio is unavailable. You can keep testing with the text guide.'));}
}
function formatTime(seconds){const n=Math.ceil(seconds);return String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');}
function update(){
  const showing=practice.visible||practice.state==='drill',busy=showing||pendingStart!==null;
  $('phoneMode').classList.toggle('selected',practice.mode==='phone');
  $('displayMode').classList.toggle('selected',practice.mode==='display');
  $('phoneMode').setAttribute('aria-pressed',practice.mode==='phone');
  $('displayMode').setAttribute('aria-pressed',practice.mode==='display');
  $('displaySetup').hidden=practice.mode!=='display';
  $('outputLabel').textContent=practice.mode==='display'?'Meta Display glasses':'Phone 3D preview';
  for(const id of ['quickWalk','quickJump','startSelected'])$(id).disabled=!practice.renderReady||busy;
  $('quickWalk').textContent=pendingStart?'Connecting display…':practice.spiderCount===1?'Start walking toward me →':'Start '+practice.spiderCount+' walking spiders →';
  $('quickJump').textContent=practice.spiderCount===1?'Start large spider · circling & jumps':'Start '+practice.spiderCount+' spiders · circling & jumps';
  $('selectedName').textContent=practice.plan.name;$('selectedDetail').textContent=practice.spiderCount+' spider'+(practice.spiderCount===1?'':'s')+' · '+practice.motionSpeed+'× walking/circling speed · '+practice.plan.detail;
  $('startSelected').textContent='Start '+practice.plan.name.toLowerCase()+' →';
  $('readyHint').textContent=!practice.renderReady?'3D rendering is unavailable on this device.':
    pendingStart?'Connecting, then starting your chosen spider. STOP cancels.':
    practice.mode==='display'&&!practice.lensReady?'Start connects your registered glasses automatically.':'Tap once to start. No audio check, rehearsal, or review is required.';
  $('practiceSection').hidden=!showing;
  $('intro').hidden=showing;$('outputSection').hidden=showing;$('planSection').hidden=showing;
  $('optionalSettings').hidden=showing;
  $('renderOptions').hidden=showing;
  $('reflection').hidden=practice.state!=='reflection';
  $('practiceTitle').textContent=practice.state==='drill'?'Optional STOP test':practice.plan.name;
  $('practiceEyebrow').textContent=practice.state==='drill'?'NEUTRAL DOT ONLY':practice.spiderCount+' SPIDER'+(practice.spiderCount===1?'':'S')+' · '+practice.motionSpeed+'× SPEED';
  $('stageLabel').textContent=practice.mode==='display'?($('matchMirror').checked?'Glasses-paced preview · submitted frames':'Live phone preview · glasses update separately'):'Phone 3D preview';
  $('pause').hidden=practice.state==='drill';
  $('stopStatus').textContent=pendingStart?'Connecting · STOP cancels':showing?'Spider / dot is being shown':'Nothing is being shown on this phone';
  if(!practice.visible)$('timer').textContent='—';
  for(const b of document.querySelectorAll('[data-level]')){
    b.classList.toggle('selected',Number(b.dataset.level)===practice.level);
    b.setAttribute('aria-pressed',Number(b.dataset.level)===practice.level);b.disabled=busy;
  }
  for(const id of ['phoneMode','displayMode','duration','before','testAudio','drill','register','connect','spiderCount','motionSpeed','deliveryProfile','matchMirror'])$(id).disabled=busy;
  if(practice.state==='reflection'&&practice.lastResult){
    const r=practice.lastResult;
    $('sessionSummary').textContent='Step '+r.level+' · '+r.seconds+' seconds · '+r.reason+'. Save a reflection if you want, or start again above.';
  }
}
function hide(reason='stopped'){
  const connecting=pendingStart!==null;pendingStart=null;
  const result=practice.stop(reason,performance.now());
  if(practice.state==='drillClear')practice.state='setup';
  armed=false;scene?.clear();stopAudio();
  delivery.reset('');
  if(connecting)native?.disconnect();else native?.stop();
  if(result){
    saved=false;$('savedMessage').textContent='';$('reflectionNote').value='';
    $('after').value=String(practice.before);$('afterValue').textContent=String(practice.before);
    say(reason==='completed'?'completed':reason==='paused'?'pause':'stopped');
  }
  update();window.scrollTo({top:0,behavior:'smooth'});
}
function interrupted(message){
  pendingStart=null;practice.lensReady=false;
  if(practice.visible||practice.state==='drill')hide('interrupted');
  else{scene?.clear();stopAudio();}
  notice(message);update();
}
function setMode(mode){
  if(practice.visible||practice.state==='drill'||pendingStart)hide();
  if(practice.mode==='display')native?.disconnect();
  practice.setMode(mode);practice.lensReady=false;
  try{localStorage.setItem('stepcloser3d-mode',mode);}catch{}
  notice('');update();
}
function startNow(level){
  practice.configure(level,Number($('duration').value),Number($('before').value));
  applyOptions();
  const token=practice.start();startWall=performance.now();guideIndex=0;lastMotionCue='';
  pendingStart=null;delivery.reset(token);armed=practice.mode==='phone';
  $('frameStats').textContent=practice.mode==='display'?'Waiting for SDK acknowledgement…':'';
  scene.show(practice.plan);notice('');
  if(practice.mode==='display')native.arm(token);else practice.shown(token,performance.now());
  say('level'+practice.level);update();$('practiceSection').scrollIntoView({behavior:'smooth',block:'start'});
}
function begin(level){
  if(practice.visible||pendingStart)return;
  if(!practice.renderReady){notice('3D rendering is unavailable on this device.');return;}
  practice.configure(level,Number($('duration').value),Number($('before').value));
  if(practice.mode==='display'&&!practice.lensReady){
    if(!native){notice('Install the APK to connect glasses, or choose Phone preview.');return;}
    pendingStart={level,at:performance.now()};notice('Connecting the display, then starting your chosen spider. STOP cancels.');
    update();native.connect();return;
  }
  try{startNow(level);}catch(error){hide('interrupted');notice(error.message);}
}
for(const plan of LEVELS){
  const b=document.createElement('button');b.className='level';b.dataset.level=plan.id;
  const n=document.createElement('span');n.className='level-number';n.textContent=plan.id;
  const text=document.createElement('span'),title=document.createElement('strong'),detail=document.createElement('small');
  title.textContent=plan.name;detail.textContent=plan.detail;text.append(title,detail);b.append(n,text);
  b.onclick=()=>{practice.configure(plan.id,Number($('duration').value),Number($('before').value));update();};$('levels').append(b);
}
$('quickWalk').onclick=()=>begin(4);$('quickJump').onclick=()=>begin(6);$('startSelected').onclick=()=>begin(practice.level);
for(const id of ['spiderCount','motionSpeed','deliveryProfile','matchMirror'])$(id).onchange=()=>{try{applyOptions();update();}catch(error){notice(error.message);}};
$('phoneMode').onclick=()=>setMode('phone');$('displayMode').onclick=()=>setMode('display');
$('register').onclick=()=>{pendingStart=null;if(native)native.register();else notice('Registration is available in the Android APK.');};
$('connect').onclick=()=>{if(native)native.connect();else notice('Glasses connection is available in the APK.');};
$('testAudio').onclick=()=>{muted=false;$('mute').textContent='Mute guide';say('test');};
$('drill').onclick=()=>{
  if(practice.mode==='display'&&!practice.lensReady){notice('Connect the display for the optional dot test, or start a spider directly.');return;}
  practice.beginDrill();scene.dot();$('motionLabel').textContent='Optional neutral dot';$('frameStats').textContent='';
  if(practice.mode==='display')native.neutral();say('neutral');update();$('practiceSection').scrollIntoView({behavior:'smooth',block:'start'});
};
$('duration').onchange=()=>practice.configure(practice.level,Number($('duration').value),practice.before);
$('before').oninput=()=>{$('beforeValue').textContent=$('before').value;practice.configure(practice.level,practice.duration,Number($('before').value));};
$('after').oninput=()=>{$('afterValue').textContent=$('after').value;};
$('stop').onclick=()=>hide('stopped');$('pause').onclick=()=>hide('paused');
$('mute').onclick=()=>{muted=!muted;stopAudio();$('mute').textContent=muted?'Unmute guide':'Mute guide';$('mute').setAttribute('aria-pressed',muted);};
$('repeat').onclick=()=>{practice.state='setup';update();window.scrollTo({top:0,behavior:'smooth'});};
function renderHistory(){
  $('history').replaceChildren();$('historyCount').textContent=history.length+' sessions';$('clearHistory').hidden=!history.length;
  for(const item of history.slice(0,50)){
    const row=document.createElement('div');row.className='history-row';
    const title=document.createElement('strong');title.textContent='Step '+item.level+' · '+(item.count||1)+' spider(s) · '+item.seconds+'s · '+item.before+' → '+item.after+' / 10';
    const detail=document.createElement('p');detail.textContent=new Date(item.date).toLocaleString()+' · '+item.reason;
    const note=document.createElement('p');note.textContent=item.note||'';row.append(title,detail,note);$('history').append(row);
  }
}
$('saveReflection').onclick=()=>{
  if(saved||!practice.lastResult)return;
  const item={...practice.lastResult,after:Number($('after').value),note:$('reflectionNote').value.trim()};
  try{history=[item,...history].slice(0,200);localStorage.setItem('stepcloser3d-history',JSON.stringify(history));saved=true;$('savedMessage').textContent='Saved. You can start another spider directly.';renderHistory();}
  catch{$('savedMessage').textContent='This device could not save the reflection.';}
};
$('clearHistory').onclick=()=>{
  if(!clearIntent){clearIntent=true;$('clearHistory').textContent='Tap again to erase the journal';return;}
  try{localStorage.removeItem('stepcloser3d-history');history=[];renderHistory();clearIntent=false;}catch{notice('Journal could not be cleared.');}
};
window.StepCloserCallbacks={event(event){
  switch(event.type){
    case 'connection':
      connectionLines.push('+'+(event.elapsedMs||'0')+'ms '+event.message);
      if(connectionLines.length>60)connectionLines.shift();$('connectionLog').textContent=connectionLines.join('\n');break;
    case 'host':break;
    case 'message':pendingStart=null;notice(event.message);update();break;
    case 'registration':$('registration').textContent='Meta registration: '+event.state;break;
    case 'devices':
      try{const list=JSON.parse(event.items);$('devices').textContent=list.length?list.map(d=>d.name+' · '+(d.display?'display capable':'audio/camera only')+' · '+(d.connected?'connected':'disconnected')+' · '+d.compatibility).join(' | '):'No Meta device is visible yet.';}catch{}break;
    case 'disconnected':practice.lensReady=false;update();break;
    case 'armed':if(event.token===practice.token&&practice.state==='starting')armed=true;break;
    case 'frameResult':
      if(practice.visible&&delivery.acknowledge(event,performance.now())){
        const stats=delivery.stats();
        $('frameStats').textContent=stats.sdkFps.toFixed(1)+' SDK ack/s · '+Math.round(stats.averageAckMs)+'ms · '+stats.size+'px · '+Math.round(stats.bytes/1024)+'KB';
      }
      break;
    case 'lens':
      $('lensMessage').textContent=event.status==='FRAME'?'3D frame accepted by glasses.':event.message;
      if(event.status==='STARTING'){$('deviceState').textContent='Connecting display…';practice.lensReady=false;}
      else if(event.status==='READY'){
        practice.lensReady=true;$('deviceState').textContent='Meta Display connected';notice('');
        const request=pendingStart;
        if(request&&practice.mode==='display'&&!document.hidden){
          try{startNow(request.level);}catch(error){hide('interrupted');notice(error.message);}
        }
      }else if(event.status==='FRAME'&&event.token===practice.token&&practice.visible){
        const first=practice.shown(event.token,performance.now());
        if(first)update();break;
      }else if(['ERROR','LOST'].includes(event.status)){
        $('deviceState').textContent='Display unavailable';interrupted(event.message);
      }else if(event.status==='CLEAR_UNCONFIRMED'&&practice.mode==='display')notice(event.message);
      update();break;
    case 'interruption':interrupted(event.message);break;
  }
}};
window.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();hide('stopped');}});
document.addEventListener('visibilitychange',()=>{
  if(document.hidden&&(practice.visible||practice.state==='drill'||pendingStart)){hide('interrupted');practice.lensReady=false;update();}
});
window.addEventListener('pagehide',()=>{pendingStart=null;scene?.clear();native?.stop();stopAudio();});
try{
  scene=new SpiderScene($('scene'));practice.renderReady=true;
  $('scene').addEventListener('webglcontextlost',event=>{event.preventDefault();hide('interrupted');practice.renderReady=false;notice('3D rendering was interrupted. Reopen the app.');update();});
}catch(error){notice('3D rendering could not start. '+error.message);}
function loop(now){
  if(pendingStart&&now-pendingStart.at>47000){pendingStart=null;notice('Connection timed out. See Connection details.');update();}
  if(practice.visible&&scene){
    const elapsed=practice.startedAt===null?0:(now-practice.startedAt)/1000;
    if(practice.mode==='phone')scene.render(elapsed,practice.motionSpeed);
    else if(armed){
      const request=delivery.begin(now);
      if(request){
        try{
          scene.render(elapsed+delivery.predictionSeconds(),practice.motionSpeed);
          const encoded=scene.capture(delivery.options.size,delivery.options.quality);
          const queued=native.submitFrame(encoded,request.token,request.sequence,request.capturedAtMs);
          if(queued!==true)delivery.rejected(request.sequence);
        }catch{hide('interrupted');notice('Could not send the 3D frame.');}
      }
      if(!$('matchMirror').checked)scene.render(elapsed,practice.motionSpeed);
      if(delivery.inFlight&&now-delivery.inFlight.capturedAtMs>5000){
        hide('interrupted');notice('Display transfer stopped responding. See Connection details.');
      }
    }
    if(!practice.visible){requestAnimationFrame(loop);return;}
    $('motionLabel').textContent=scene.motionLabel(elapsed,practice.motionSpeed);
    if(practice.state==='active'){
      $('timer').textContent=formatTime(practice.remaining(now));
      const cue=guideCue(elapsed,practice.plan);
      if(cue&&cue.id!==lastMotionCue){lastMotionCue=cue.id;say(cue.key);}
      else if(!practice.plan.behavior&&guideIndex<3&&elapsed>=[22,45,85][guideIndex])say(['observe','choice','stay'][guideIndex++]);
      if(practice.remaining(now)<=0)hide('completed');
    }else{$('timer').textContent='Starting…';if(now-startWall>8000){hide('interrupted');notice('No first frame acknowledgement. See Connection details.');}}
  }
  requestAnimationFrame(loop);
}
renderHistory();update();requestAnimationFrame(loop);
window.StepCloserDiagnostics=()=>({state:practice.state,mode:practice.mode,level:practice.level,
  count:practice.spiderCount,speed:practice.motionSpeed,delivery:delivery.stats(),
  ready:practice.canStart,pendingStart:pendingStart!==null,token:practice.token,model:scene?.diagnostics(),history:history.length,lensReady:practice.lensReady});

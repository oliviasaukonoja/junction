// Voice in and out. Out: the coach's ElevenLabs voice via the brain (/say), browser
// speech as a fallback. In: Meta glasses speech (native events) or, in the laptop
// preview, the browser microphone.
export const BRAIN=(()=>{try{return localStorage.getItem('calmsight-url')}catch{return null}})()
  ||'https://kristisaralidze--calmsight-brain-web.modal.run';
const native=window.StepCloserNative;
let userId;
try{userId=localStorage.getItem('calmsight-user');if(!userId){userId='u'+Math.random().toString(36).slice(2,10);localStorage.setItem('calmsight-user',userId);}}catch{userId='demo';}
export {userId};

export async function brain(path,body,ms=9000){
  const ctrl=new AbortController(),t=setTimeout(()=>ctrl.abort(),ms);
  try{
    const r=await fetch(BRAIN+path,{method:'POST',headers:{'content-type':'application/json'},
      body:JSON.stringify({userId,...body}),signal:ctrl.signal});
    if(!r.ok)throw Error('HTTP '+r.status);return await r.json();
  }finally{clearTimeout(t);}
}

const cache=new Map();let audio=null,seq=0,speakingUntil=0,muted=false,lastLine='';
function urlFor(text){
  if(!cache.has(text))cache.set(text,brain('/say',{text},7000).then(r=>r.audioUrl||null).catch(()=>null));
  return cache.get(text);
}
export function prefetch(text){if(text&&!muted)urlFor(text);}
export function setMuted(m){muted=m;if(m)hush();}
export function isMuted(){return muted;}
export function hush(){seq++;try{audio?.pause();}catch{}audio=null;try{speechSynthesis.cancel();}catch{}native?.stopAudio?.();speakingUntil=0;}
export function isSpeaking(){return performance.now()<speakingUntil;}
// Speak and resolve roughly when finished. A newer say() cancels an older one.
export async function say(text){
  if(!text)return;
  const my=++seq;hush();seq=my;lastLine=text.toLowerCase();
  const words=text.split(/\s+/).length,est=900+words*390;
  speakingUntil=performance.now()+est+3000;
  if(muted)return;
  const url=await urlFor(text);
  if(my!==seq)return;
  if(url){
    if(native?.playUrl){native.playUrl(url);speakingUntil=performance.now()+est;return wait(est);}
    return new Promise(res=>{
      audio=new Audio(url);
      audio.onended=()=>{speakingUntil=performance.now()+400;res();};
      audio.onerror=()=>{speakingUntil=0;res();};
      audio.play().catch(()=>{fallback(text).then(res);});
    });
  }
  return fallback(text);
}
function fallback(text){
  return new Promise(res=>{
    try{
      const u=new SpeechSynthesisUtterance(text);u.rate=1;u.pitch=1;
      const v=speechSynthesis.getVoices().find(v=>/female|samantha|zira|google uk english female/i.test(v.name));if(v)u.voice=v;
      u.onend=()=>{speakingUntil=performance.now()+400;res();};u.onerror=()=>res();
      speechSynthesis.speak(u);
    }catch{res();}
  });
}
const wait=ms=>new Promise(r=>setTimeout(r,ms));

// ---------------- listening ----------------
let handler=()=>{},partialHandler=()=>{},stateHandler=()=>{},rec=null,want=false;
export function onHeard(fn){handler=fn;}
export function onPartial(fn){partialHandler=fn;}
export function onState(fn){stateHandler=fn;}
// In the laptop preview the mic can hear the speakers: drop text that is just the coach's own line.
function echo(t){if(!isSpeaking())return false;const w=t.toLowerCase().match(/[a-z']+/g)||[];if(w.length<3)return false;
  return w.filter(x=>lastLine.includes(x)).length/w.length>.7;}
export function heard(text){const t=(text||'').trim();if(!t)return;if(!native&&echo(t))return;handler(t);}
export function partial(t){partialHandler(t);}
export function nativeState(s){stateHandler(s);}
export const browserMic=!native&&!!(window.SpeechRecognition||window.webkitSpeechRecognition);
export function listen(on){
  if(native){if(on)native.enableVoice?.();stateHandler(on?'STARTED':'OFF');return;}
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){stateHandler('UNAVAILABLE');return;}
  want=on;
  if(!on){try{rec?.stop();}catch{}stateHandler('OFF');return;}
  if(rec)return;
  rec=new SR();rec.lang='en-US';rec.continuous=true;rec.interimResults=true;
  rec.onresult=e=>{for(let i=e.resultIndex;i<e.results.length;i++){const r=e.results[i];
    if(r.isFinal)heard(r[0].transcript);else if(!isSpeaking())partialHandler(r[0].transcript);}};
  rec.onstart=()=>stateHandler('STARTED');
  rec.onerror=e=>{if(e.error==='not-allowed'){want=false;stateHandler('DENIED');}};
  rec.onend=()=>{rec=null;if(want)setTimeout(()=>listen(true),250);else stateHandler('OFF');};
  try{rec.start();}catch{rec=null;}
}

import {build} from 'esbuild';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root=new URL('../android/app/src/main/assets/web/',import.meta.url).pathname;
const output=await build({entryPoints:[root+'app.mjs'],bundle:true,format:'iife',write:false,
  plugins:[{name:'no-gpu-unit-adapter',setup(b){
    b.onResolve({filter:/^\.\/spider\.mjs$/},()=>({path:'spider',namespace:'unit'}));
    b.onLoad({filter:/.*/,namespace:'unit'},()=>({contents:
      'export class SpiderScene{constructor(){this.visible=false;} clear(){this.visible=false;} dot(){this.visible=true;} show(p){this.plan=p;this.visible=true;} render(){} motionLabel(){return "";} capture(){return "frame";} diagnostics(){return {webgl:true,visible:this.visible,legCount:8,spiderCount:this.plan?.count||0};}}',loader:'js'}));
  }}]});
class Element{
  constructor(id){this.id=id;this.value='';this.dataset={};this.children=[];this.hidden=false;this.disabled=false;this.textContent='';this.classList={toggle(){}};}
  append(...items){this.children.push(...items);}
  replaceChildren(...items){this.children=items;}
  setAttribute(name,value){this[name]=value;}
  addEventListener(){} scrollIntoView(){}
}
const html=readFileSync(root+'index.html','utf8'),elements=new Map();
for(const [,id]of html.matchAll(/id="([^"]+)"/g))elements.set(id,new Element(id));
elements.get('duration').value='60';elements.get('before').value='3';elements.get('after').value='3';
const callbacks={},calls=[],storage=new Map();let time=1000;
const native={};for(const key of ['connect','register','disconnect','arm','stop','playPrompt','stopAudio','neutral','submitFrame'])
  native[key]=(...args)=>{calls.push([key,...args]);return key==='submitFrame'?true:undefined;};
const document={hidden:false,getElementById(id){assert(elements.has(id),'Missing HTML id '+id);return elements.get(id);},
  createElement(){return new Element();},querySelectorAll(){return elements.get('levels').children;},
  addEventListener(name,fn){callbacks[name]=fn;}};
const window={StepCloserNative:native,scrollTo(){},addEventListener(name,fn){callbacks[name]=fn;}};
vm.runInNewContext(output.outputFiles[0].text,{window,document,
  performance:{now:()=>time},requestAnimationFrame(fn){callbacks.raf=fn;},
  localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
  Audio:class{play(){return Promise.resolve();}pause(){}},console});
const diag=()=>window.StepCloserDiagnostics(),event=e=>window.StepCloserCallbacks.event(e);
const checks=[];
assert.equal(diag().mode,'display');assert.equal(elements.get('quickWalk').disabled,false);
elements.get('quickWalk').onclick();assert.equal(diag().pendingStart,true);
assert.equal(calls.filter(c=>c[0]==='connect').length,1);
event({type:'lens',status:'READY',message:'Connected'});
assert.equal(diag().state,'starting');assert.equal(diag().level,4);assert.equal(diag().model.visible,true);
assert.equal(calls.filter(c=>c[0]==='neutral').length,0);
assert.equal(calls.some(c=>c[0]==='playPrompt'&&c[1]==='test'),false);
checks.push('One tap connects and starts walking without tests or review');
event({type:'armed',token:diag().token});
time=1000;callbacks.raf(time);
const sent=calls.filter(c=>c[0]==='submitFrame');assert.equal(sent.length,1);
time=1100;callbacks.raf(time);assert.equal(calls.filter(c=>c[0]==='submitFrame').length,1);
time=1200;event({type:'lens',status:'FRAME',token:diag().token});
event({type:'frameResult',token:diag().token,sequence:1,accepted:true,bytes:16000});
assert.equal(diag().delivery.accepted,1);
checks.push('Frame producer waits for SDK ACK rather than queueing frames');
assert.equal(diag().state,'active');
elements.get('stop').onclick();assert.equal(diag().model.visible,false);
elements.get('quickJump').onclick();assert.equal(diag().level,6);assert.equal(diag().model.visible,true);
checks.push('Circling and jumps start directly after STOP');
elements.get('stop').onclick();event({type:'lens',status:'LOST',message:'Disconnected'});
const arms=calls.filter(c=>c[0]==='arm').length;
elements.get('quickJump').onclick();assert.equal(diag().pendingStart,true);
elements.get('stop').onclick();event({type:'lens',status:'READY',message:'Late ready'});
assert.equal(diag().model.visible,false);assert.equal(calls.filter(c=>c[0]==='arm').length,arms);
checks.push('STOP cancels pending auto-start; late READY cannot show a spider');
elements.get('drill').onclick();assert.equal(diag().state,'drill');
elements.get('stop').onclick();assert.equal(diag().ready,true);
elements.get('quickWalk').onclick();assert.equal(diag().model.visible,true);
checks.push('Optional dot test never becomes a prerequisite');
elements.get('stop').onclick();elements.get('phoneMode').onclick();
const connections=calls.filter(c=>c[0]==='connect').length;
elements.get('quickWalk').onclick();assert.equal(diag().state,'active');
assert.equal(calls.filter(c=>c[0]==='connect').length,connections);
checks.push('Phone preview starts in one tap without a glasses connection');
assert(!html.includes('reviewDialog')&&!html.includes('audioConfirmed')&&!html.includes('id="consent"'));
checks.push('Mandatory checkboxes and review dialog are absent');

elements.get('stop').onclick();elements.get('spiderCount').value='20';elements.get('motionSpeed').value='2';elements.get('spiderCount').onchange();
elements.get('quickWalk').onclick();assert.equal(diag().count,20);assert.equal(diag().speed,2);assert.equal(diag().model.spiderCount,20);
checks.push('Crowd and speed selection reach the scene');
console.log(JSON.stringify({adapter:'DOM/native/GPU test doubles; actual app logic',passed:checks.length,checks},null,2));

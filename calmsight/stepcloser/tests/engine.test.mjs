import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Practice,LEVELS} from '../android/app/src/main/assets/web/engine.mjs';
function ready(){const p=new Practice();p.renderReady=true;return p;}
test('one tap starts phone practice without audio, rehearsal or review',()=>{
  const p=ready();assert.equal(p.visible,false);assert.equal(p.canStart,true);
  assert.equal(p.audioChecked,false);assert.equal(p.drillPassed,false);assert.equal(p.consent,false);
  p.start();assert.equal(p.visible,true);assert.equal(p.state,'starting');
});
test('default motion is walking toward the viewer',()=>{
  const p=ready();assert.equal(p.level,4);assert.equal(p.plan.behavior,'approach');
});
test('display needs a real connection but no audio or rehearsal gate',()=>{
  const p=ready();p.setMode('display');assert.equal(p.canStart,false);assert.throws(()=>p.start());
  p.lensReady=true;assert.equal(p.canStart,true);p.start();assert.equal(p.visible,true);
});
test('a failed renderer cannot present a spider',()=>{const p=new Practice();assert.throws(()=>p.start());assert.equal(p.visible,false);});
test('stopping an optional dot test never blocks direct start',()=>{
  const p=ready();p.beginDrill();p.stop();assert.equal(p.drillPassed,false);
  assert.equal(p.canStart,true);p.start();assert.equal(p.visible,true);
});
test('timer waits for output acknowledgement and late frames cannot restart',()=>{
  const p=ready(),token=p.start();assert.equal(p.remaining(999999),60);
  p.shown(token,2000);assert.equal(p.remaining(3000),59);
  p.stop('stopped',3000);assert.equal(p.shown(token,4000),false);assert.equal(p.visible,false);
});
test('stale frames cannot start a later direct-start session',()=>{
  const p=ready(),old=p.start();p.stop('paused',100);const next=p.start();
  assert.notEqual(old,next);assert.equal(p.shown(old,200),false);assert.equal(p.shown(next,250),true);
});
test('timer ends presentation without advancing the chosen difficulty',()=>{
  const p=ready();p.configure(4,30,5);const token=p.start();p.shown(token,100);
  assert.equal(p.tick(30099),false);assert.equal(p.tick(30100),true);
  assert.equal(p.visible,false);assert.equal(p.level,4);assert.equal(p.lastResult.seconds,30);
});
test('changing a running plan or output is rejected until STOP',()=>{
  const p=ready();p.start();assert.throws(()=>p.configure(6,30,4));assert.throws(()=>p.setMode('display'));
});
test('phone can directly restart after interruption, display must reconnect',()=>{
  const p=ready(),token=p.start();p.shown(token,100);p.interrupted(1100);
  assert.equal(p.visible,false);assert.equal(p.canStart,true);
  p.setMode('display');assert.equal(p.canStart,false);p.lensReady=true;assert.equal(p.canStart,true);
});
test('invalid plans are rejected',()=>{
  const p=ready();
  for(const args of [[0,30,0],[7,30,0],[2,1,0],[2,60,11],[2,60,-1]])assert.throws(()=>p.configure(...args));
  assert.equal(LEVELS[5].behavior,'orbitJump');
});
test('pause and STOP clear tokens and permit a fresh explicit start',()=>{
  for(const reason of ['paused','stopped','interrupted']){
    const p=ready(),token=p.start();p.shown(token,100);p.stop(reason,2100);
    assert.equal(p.visible,false);assert.equal(p.token,'');assert.equal(p.lastResult.seconds,2);
    assert.equal(p.canStart,true);
  }
});

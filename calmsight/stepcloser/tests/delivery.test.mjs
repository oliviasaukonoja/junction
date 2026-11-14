import {test} from 'node:test';
import assert from 'node:assert/strict';
import {FrameDelivery} from '../android/app/src/main/assets/web/delivery.mjs';
test('only one unacknowledged frame is produced',()=>{
  const d=new FrameDelivery();d.reset('run');
  const first=d.begin(0);assert(first);
  for(let now=1;now<2000;now+=20)assert.equal(d.begin(now),null);
  d.acknowledge({token:'run',sequence:first.sequence,accepted:'true',bytes:12000},2000);
  assert(d.begin(2001));
});
test('late old-session ACKs cannot release the current frame',()=>{
  const d=new FrameDelivery();d.reset('old');d.begin(0);
  d.reset('new');const current=d.begin(100);
  assert.equal(d.acknowledge({token:'old',sequence:1,accepted:true},150),false);
  assert.equal(d.ready(500),false);assert.equal(d.inFlight.sequence,current.sequence);
});
test('a rejected local bridge request can be replaced without a queue',()=>{
  const d=new FrameDelivery();d.reset('run');const first=d.begin(0);
  d.rejected(first.sequence);assert.equal(d.inFlight,null);assert(d.begin(100));
});
test('failure ACK releases the producer without counting a displayed frame',()=>{
  const d=new FrameDelivery();d.reset('run');const frame=d.begin(0);
  assert.equal(d.acknowledge({token:'run',sequence:frame.sequence,accepted:false},100),false);
  assert.equal(d.stats().accepted,0);assert(d.ready(101));
});
test('slow link lowers Auto frame resolution without changing motion speed',()=>{
  const d=new FrameDelivery();d.reset('run');let now=0;
  for(let i=0;i<12;i++){
    const frame=d.begin(now);assert(frame);now+=300;
    d.acknowledge({token:'run',sequence:frame.sequence,accepted:true,bytes:20000},now);now+=1;
  }
  assert.equal(d.options.size,256);assert.equal(d.stats().accepted,12);
  assert.equal(d.options.fps,15);
});
test('fast link restores quality and latency prediction stays bounded',()=>{
  const d=new FrameDelivery();d.reset('run');let now=0;
  for(let i=0;i<6;i++){const f=d.begin(now);now+=1000;d.acknowledge({token:'run',sequence:f.sequence,accepted:true},now);now+=100;}
  assert.equal(d.options.size,320);assert(d.predictionSeconds()<=.25);
  for(let i=0;i<24;i++){const f=d.begin(now);assert(f);now+=50;d.acknowledge({token:'run',sequence:f.sequence,accepted:true},now);now+=20;}
  assert.equal(d.options.size,384);
});
test('frame rate cap applies when SDK replies immediately',()=>{
  const d=new FrameDelivery('balanced');d.reset('run');const f=d.begin(0);
  d.acknowledge({token:'run',sequence:f.sequence,accepted:true},1);
  assert.equal(d.begin(20),null);assert(d.begin(84));
});
test('profiles and session reset retain no obsolete packet',()=>{
  const d=new FrameDelivery('fast');assert.equal(d.options.size,256);
  d.reset('run');d.begin(0);d.reset('');assert.equal(d.inFlight,null);assert.equal(d.begin(1000),null);
  assert.throws(()=>d.setProfile('unknown'));
});

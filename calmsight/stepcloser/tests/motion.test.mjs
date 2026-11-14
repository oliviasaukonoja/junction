import {test} from 'node:test';
import assert from 'node:assert/strict';
import {LEVELS} from '../android/app/src/main/assets/web/engine.mjs';
import {PROMPTS} from '../android/app/src/main/assets/web/prompts.mjs';
import {sampleMotion,jumpClock,guideCue,FIRST_JUMP,JUMP_DURATION,JUMP_PERIOD} from '../android/app/src/main/assets/web/motion.mjs';
globalThis.document={createElement:()=>({width:0,height:0,getContext:()=>({
  createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),putImageData:()=>{}
})})};
const THREE=await import('../android/app/src/main/assets/web/vendor/three.module.js');
const {createSpider}=await import('../android/app/src/main/assets/web/spider.mjs');
test('all models are larger and the advanced action is explicitly labelled',()=>{
  const previous=[.30,.47,.47,.58,.82,.54];
  LEVELS.forEach((p,i)=>assert(p.scale>previous[i]));
  assert.equal(LEVELS[5].behavior,'orbitJump');
  assert.match(LEVELS[5].detail,/jump.*toward/);
});
test('earlier steps cannot suddenly jump',()=>{
  for(const plan of LEVELS.slice(0,5))for(let t=0;t<300;t+=.5)
    assert.equal(sampleMotion(t,plan).airborne,0);
});
test('circling sweeps both sides and moves vertically within the view',()=>{
  const p=LEVELS[4],a=sampleMotion(0,p),b=sampleMotion(4,p),c=sampleMotion(12,p);
  assert(b.x>.10&&c.x<-.10);
  assert(Math.abs(a.y-c.y)>.10);
  assert.equal(a.airborne,0);
});
test('jumps approach the viewer, tuck the legs and return without teleporting',()=>{
  const plan=LEVELS[5],takeoff=sampleMotion(FIRST_JUMP,plan);
  const peak=sampleMotion(FIRST_JUMP+JUMP_DURATION/2,plan);
  assert(peak.airborne>.99&&peak.z>takeoff.z+.35&&peak.y>takeoff.y+.18);
  assert(Math.abs(peak.x)<.001);
  const camera=new THREE.Vector3(0,1.55,2.5);
  assert(camera.distanceTo(new THREE.Vector3(peak.x,peak.y,peak.z))<
    camera.distanceTo(new THREE.Vector3(takeoff.x,takeoff.y,takeoff.z))-.35);
  for(const boundary of [FIRST_JUMP,FIRST_JUMP+JUMP_DURATION,FIRST_JUMP+JUMP_PERIOD]){
    const a=sampleMotion(boundary-1e-5,plan),b=sampleMotion(boundary+1e-5,plan);
    assert(Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z)<1e-4);
  }
  assert.equal(jumpClock(FIRST_JUMP-1).jumping,false);
});
test('jump cue is spoken before every jump throughout a five minute session',()=>{
  for(let t=FIRST_JUMP;t<300;t+=JUMP_PERIOD){
    assert.equal(guideCue(t-2,LEVELS[5]).key,'jump_cue');
    assert.equal(guideCue(t+4.1,LEVELS[5]).key,'jump_recover');
  }
});
test('calming speech repeats and every scheduled clip exists',()=>{
  const ids=new Set();
  for(const plan of LEVELS.slice(4))for(let t=0;t<300;t+=.25){
    const cue=guideCue(t,plan);if(!cue)continue;
    ids.add(cue.id);assert(PROMPTS[cue.key]);assert.match(cue.key,/^[a-z0-9_-]{1,32}$/);
  }
  assert(ids.size>40);
});
test('walking, circling and jumping meshes remain in the viewing area',()=>{
  const spider=createSpider(true);
  const camera=new THREE.PerspectiveCamera(34,1,.05,50);
  camera.position.set(0,1.55,2.5);camera.lookAt(0,.08,0);camera.updateMatrixWorld(true);
  const v=new THREE.Vector3();let maxX=0,maxY=0;
  for(const plan of LEVELS.slice(3))for(let t=0;t<36;t+=.4){
    const pose=sampleMotion(t,plan);
    spider.update(t,plan.motion,pose.airborne);
    spider.root.position.set(pose.x,pose.y,pose.z);
    spider.root.rotation.set(pose.pitch,pose.yaw,0);spider.root.scale.setScalar(pose.scale);
    spider.root.updateMatrixWorld(true);
    spider.root.traverse(node=>{
      const positions=node.geometry?.getAttribute('position');if(!positions)return;
      for(let i=0;i<positions.count;i++){
        v.fromBufferAttribute(positions,i).applyMatrix4(node.matrixWorld).project(camera);
        assert([v.x,v.y,v.z].every(Number.isFinite));
        maxX=Math.max(maxX,Math.abs(v.x));maxY=Math.max(maxY,Math.abs(v.y));
        assert(v.z<1&&v.z>-1);
      }
    });
  }
  assert(maxX<1.06&&maxY<1.06,'Projected mesh '+maxX.toFixed(2)+' x '+maxY.toFixed(2));
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
globalThis.document={createElement:()=>({width:0,height:0,getContext:()=>({
  createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),putImageData:()=>{}
})})};
const {SpiderCrowd}=await import('../android/app/src/main/assets/web/crowd.mjs');
const {LEVELS,Practice}=await import('../android/app/src/main/assets/web/engine.mjs');
const {crowdPose,sampleMotion,jumpClock,FIRST_JUMP}=await import('../android/app/src/main/assets/web/motion.mjs');
const THREE=await import('../android/app/src/main/assets/web/vendor/three.module.js');
test('20 fully articulated spiders use a bounded set of shared batches',()=>{
  const crowd=new SpiderCrowd(true);
  crowd.update(5,{...LEVELS[3],count:20},1.5);
  assert.equal(crowd.count,20);assert(crowd.batches.length<=12);
  assert.equal(crowd.prototype.legs.length,8);
  for(const batch of crowd.batches){
    assert.equal(batch.mesh.count,batch.sources.length*20);
    for(const value of batch.mesh.instanceMatrix.array)assert(Number.isFinite(value));
  }
});
test('crowd actors have distinct locations and move independently',()=>{
  const plan={...LEVELS[3],count:10};
  const a=crowdPose(3,plan,0),b=crowdPose(3,plan,1),later=crowdPose(8,plan,0);
  assert(Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z)>.1);
  assert(Math.hypot(a.x-later.x,a.y-later.y,a.z-later.z)>.005);
});
test('crowd count and speed are explicit options and cannot change during playback',()=>{
  const p=new Practice();p.renderReady=true;p.configureOptions(20,2);assert.equal(p.plan.count,20);
  p.start();assert.throws(()=>p.configureOptions(1,1));
  p.stop();assert.throws(()=>p.configureOptions(21,1));assert.throws(()=>p.configureOptions(0,1));
});
test('speed changes walking phase while jump timing stays with the guide',()=>{
  assert.deepEqual(sampleMotion(4,LEVELS[3],0,2),sampleMotion(8,LEVELS[3],0,1));
  for(const speed of [.5,1,1.5,2])
    assert.equal(sampleMotion(FIRST_JUMP+1,LEVELS[5],0,speed).airborne,jumpClock(FIRST_JUMP+1).airborne);
});
test('crowd geometry remains inside the camera view for supported counts',()=>{
  const crowd=new SpiderCrowd(true),camera=new THREE.PerspectiveCamera(34,1,.05,50);
  camera.position.set(0,1.55,2.5);camera.lookAt(0,.08,0);camera.updateMatrixWorld(true);
  const matrix=new THREE.Matrix4(),point=new THREE.Vector3();let max=0;
  for(const count of [3,5,10,20])for(const time of [0,5,15.6,24]){
    crowd.update(time,{...LEVELS[5],count},1);
    for(const batch of crowd.batches){
      const positions=batch.mesh.geometry.getAttribute('position');
      for(let actor=0;actor<batch.mesh.count;actor++){
        batch.mesh.getMatrixAt(actor,matrix);
        for(let j=0;j<positions.count;j++){
          point.fromBufferAttribute(positions,j).applyMatrix4(matrix).project(camera);
          assert([point.x,point.y,point.z].every(Number.isFinite));
          assert(point.z>-1&&point.z<1);max=Math.max(max,Math.abs(point.x),Math.abs(point.y));
        }
      }
    }
  }
  assert(max<1.04,'Crowd projected bound '+max.toFixed(3));
});

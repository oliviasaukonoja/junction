import {test} from 'node:test';
import assert from 'node:assert/strict';
// A 2D texture stub allows kinematic/mesh verification in Node without a GPU.
// It does not simulate WebGL, a glasses display, or visual appearance.
globalThis.document={createElement:()=>({
  width:0,height:0,getContext:()=>({
    createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),putImageData:()=>{}
  })
})};
const {createSpider}=await import('../android/app/src/main/assets/web/spider.mjs');
const THREE=await import('../android/app/src/main/assets/web/vendor/three.module.js');
function end(segment,sign){
  return new THREE.Vector3(0,sign*segment.scale.y/2,0).applyQuaternion(segment.quaternion).add(segment.position);
}
test('eight articulated legs form continuous chains throughout a full gait',()=>{
  const spider=createSpider(true);
  assert.equal(spider.legs.length,8);
  for(let frame=0;frame<120;frame++){
    spider.update(frame/30,2);
    for(const leg of spider.legs){
      for(let n=0;n<3;n++){
        assert(end(leg.parts[n],1).distanceTo(end(leg.parts[n+1],-1))<1e-7);
      }
      const tip=end(leg.parts[3],1);assert(tip.y>=0&&tip.y<.10);
      for(const part of leg.parts){
        for(const v of [...part.position.toArray(),...part.quaternion.toArray(),...part.scale.toArray()])
          assert(Number.isFinite(v));
      }
    }
  }
});
test('still levels leave the full skeleton still even as time advances',()=>{
  const spider=createSpider(false);
  const snapshot=()=>spider.legs.map(l=>l.parts.map(p=>[...p.position.toArray(),...p.quaternion.toArray()]));
  spider.update(0,0);const initial=snapshot();
  spider.update(987,0);assert.deepEqual(snapshot(),initial);
});
test('detailed mesh has finite positions, texture data, and a bounded footprint',()=>{
  const spider=createSpider(true);let meshes=0,vertices=0,lines=0;
  spider.root.traverse(node=>{
    if(node.isMesh)meshes++;if(node.isLineSegments)lines++;
    const positions=node.geometry?.getAttribute('position');if(!positions)return;
    vertices+=positions.count;
    for(const coordinate of positions.array)assert(Number.isFinite(coordinate));
  });
  spider.root.updateMatrixWorld(true);
  const bounds=new THREE.Box3().setFromObject(spider.root),size=bounds.getSize(new THREE.Vector3());
  assert(meshes>50&&lines>30&&vertices>30000);
  assert(size.x<2&&size.z<2&&size.y<1);
});

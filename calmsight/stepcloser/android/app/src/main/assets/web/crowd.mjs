import * as THREE from './vendor/three.module.js';
import {createSpider} from './model.mjs';
import {crowdPose} from './motion.mjs';
export const MAX_SPIDERS=20;
// One animated prototype supplies matrices to shared GPU instance buffers.
// Crowd mode omits individual hairs and uses lower polygon spheres.
export class SpiderCrowd {
  constructor(realistic=true){
    this.root=new THREE.Group();this.root.visible=false;
    this.prototype=createSpider(realistic,7,{hair:false,lowPoly:true});
    const groups=new Map();
    this.prototype.root.traverse(mesh=>{
      if(!mesh.isMesh)return;
      const key=mesh.geometry.uuid+':'+mesh.material.uuid;
      if(!groups.has(key))groups.set(key,{sources:[],geometry:mesh.geometry,material:mesh.material});
      groups.get(key).sources.push(mesh);
    });
    this.batches=[...groups.values()].map(group=>{
      const mesh=new THREE.InstancedMesh(group.geometry,group.material,MAX_SPIDERS*group.sources.length);
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);mesh.frustumCulled=false;mesh.count=0;
      this.root.add(mesh);return {mesh,sources:group.sources};
    });
    this.count=0;
  }
  update(time,plan,speed=1){
    const count=plan.count||1;
    if(!Number.isInteger(count)||count<1||count>MAX_SPIDERS)throw Error('Spider count must be 1–20');
    for(let i=0;i<count;i++){
      const pose=crowdPose(time,plan,i,speed);
      const model=this.prototype;
      model.update(time*speed+i*.17,plan.motion,pose.airborne);
      model.root.position.set(pose.x,pose.y,pose.z);
      model.root.rotation.set(pose.pitch,pose.yaw,0);model.root.scale.setScalar(pose.scale);
      model.root.updateMatrixWorld(true);
      for(const batch of this.batches)
        batch.sources.forEach((source,j)=>batch.mesh.setMatrixAt(i*batch.sources.length+j,source.matrixWorld));
    }
    for(const batch of this.batches){
      batch.mesh.count=count*batch.sources.length;batch.mesh.instanceMatrix.needsUpdate=true;
    }
    this.count=count;this.root.visible=true;
  }
}

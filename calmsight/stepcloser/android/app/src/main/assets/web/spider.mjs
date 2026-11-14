import * as THREE from './vendor/three.module.js';
import {createSpider} from './model.mjs';
import {SpiderCrowd} from './crowd.mjs';
import {sampleMotion} from './motion.mjs';
import {NeedleScene} from './needle.mjs';
export {createSpider} from './model.mjs';

export class SpiderScene {
  constructor(canvas){
    this.canvas=canvas;
    this.renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false,preserveDrawingBuffer:true});
    this.renderer.setSize(600,600,false);this.renderer.setPixelRatio(1);
    this.renderer.setClearColor(0x000000,1);
    this.renderer.outputColorSpace=THREE.SRGBColorSpace;
    this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.4;
    this.scene=new THREE.Scene();
    this.camera=new THREE.PerspectiveCamera(34,1,.05,50);
    this.camera.position.set(0,1.55,2.5);this.camera.lookAt(0,.08,0);
    this.scene.add(new THREE.HemisphereLight(0xf7f0de,0x34291d,2.4));
    const key=new THREE.DirectionalLight(0xffebd1,4);key.position.set(-2,3,2);this.scene.add(key);
    const rim=new THREE.DirectionalLight(0xc1dbe8,2);rim.position.set(2,1,-2);this.scene.add(rim);
    this.instances=[];this.plan=null;this.visible=false;this.rotation=0;
    this.crowds=new Map();this.activeCrowd=null;
    this.transferCanvas=document.createElement('canvas');
    this.transferContext=this.transferCanvas.getContext('2d',{alpha:false});
    this.simple=createSpider(false),this.real=createSpider(true);
    for(const item of [this.simple,this.real]){item.root.visible=false;this.scene.add(item.root);}
    this.neutral=new THREE.Mesh(new THREE.CircleGeometry(.047,48),new THREE.MeshBasicMaterial({color:0xb6e0bd}));
    this.neutral.position.set(0,.08,0);this.neutral.lookAt(this.camera.position);this.neutral.visible=false;this.scene.add(this.neutral);
    this.needles=new NeedleScene(this.scene);
    this.clear();
  }
  clear(){this.needles?.clear();this.visible=false;this.neutral.visible=false;for(const i of [this.simple,this.real])i.root.visible=false;for(const c of this.crowds.values())c.root.visible=false;this.activeCrowd=null;this.renderer.render(this.scene,this.camera);}
  dot(){this.clear();this.neutral.visible=true;this.renderer.render(this.scene,this.camera);}
  show(plan){
    this.clear();this.plan=plan;this.visible=true;this.rotation=0;
    if(plan.fear==='needles'){this.instances=[];this.activeCrowd=null;this.needles.show(plan);this.render(0);return;}
    if(plan.count>1){
      const key=plan.realistic?'real':'simple';
      if(!this.crowds.has(key)){const crowd=new SpiderCrowd(plan.realistic);this.crowds.set(key,crowd);this.scene.add(crowd.root);}
      this.activeCrowd=this.crowds.get(key);this.instances=[];this.render(0);return;
    }
    this.instances=[plan.realistic?this.real:this.simple];
    this.instances.forEach((item,i)=>{
      item.root.visible=true;item.root.scale.setScalar(plan.scale);
      item.root.position.set(plan.count===2?(i===0?-.43:.43):0,0,i===1?-.18:0);
    });
    this.render(0);
  }
  render(time,speed=1){
    if(!this.visible)return;
    if(this.plan?.fear==='needles'){this.needles.render(time,this.plan,speed);this.renderer.render(this.scene,this.camera);return;}
    if(this.activeCrowd){
      this.activeCrowd.update(time,this.plan,speed);
      this.renderer.render(this.scene,this.camera);return;
    }
    this.instances.forEach((item,i)=>{
      const pose=sampleMotion(time,this.plan,i,speed);
      item.update(time*speed+i*.31,this.plan.motion,pose.airborne);
      item.root.position.set(pose.x,pose.y,pose.z);
      item.root.scale.setScalar(pose.scale);
      item.root.rotation.set(pose.pitch,this.rotation+pose.yaw,0);
    });
    this.renderer.render(this.scene,this.camera);
  }
  motionLabel(time,speed=1){if(this.plan?.fear==='needles')return (this.plan.count>1?this.plan.count+' needles · ':'')+this.needles.label(time*speed,this.plan);return this.plan?(this.plan.count>1?this.plan.count+' spiders · ':'')+sampleMotion(time,this.plan,0,speed).label:'';}
  capture(size=384,quality=.76){
    if(this.transferCanvas.width!==size){this.transferCanvas.width=size;this.transferCanvas.height=size;}
    this.transferContext.drawImage(this.canvas,0,0,size,size);
    return this.transferCanvas.toDataURL('image/jpeg',quality).split(',')[1];
  }
  diagnostics(){
    return {webgl:true,legCount:this.real.legs.length,triangles:this.renderer.info.render.triangles,
      geometries:this.renderer.info.memory.geometries,drawCalls:this.renderer.info.render.calls,
      spiderCount:this.plan?.count||0,instanced:!!this.activeCrowd,visible:this.visible};
  }
}

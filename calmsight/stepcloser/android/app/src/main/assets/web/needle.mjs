import * as THREE from './vendor/three.module.js';
import {crowdPose} from './motion.mjs';
// 3D syringe for graded needle exposure. Axis runs along +Z, needle tip at +Z
// (towards the viewer). Side views rotate it; approach steps keep the tip forward.
const Y=.26;
function cyl(r1,r2,len,seg,mat){const m=new THREE.Mesh(new THREE.CylinderGeometry(r2,r1,len,seg),mat);m.rotation.x=Math.PI/2;return m;}
export function createSyringe(detailed=true){
  const root=new THREE.Group(),body=new THREE.Group();root.add(body);body.position.y=Y;
  const glass=new THREE.MeshPhysicalMaterial({color:detailed?0xeaf6ff:0xcfe9df,transparent:true,opacity:detailed?.32:.55,
    roughness:.05,metalness:0,clearcoat:1,side:THREE.DoubleSide});
  const liquid=new THREE.MeshStandardMaterial({color:detailed?0x8fd3ff:0xa8e0c6,transparent:true,opacity:.75,roughness:.2});
  const plastic=new THREE.MeshStandardMaterial({color:0xf4f4ee,roughness:.5});
  const rubber=new THREE.MeshStandardMaterial({color:0x2b2b2b,roughness:.8});
  const steel=new THREE.MeshStandardMaterial({color:0xdfe5ea,metalness:1,roughness:.18});
  const hubMat=new THREE.MeshStandardMaterial({color:detailed?0x2f9e5b:0x8cc9a3,roughness:.4});
  const capMat=new THREE.MeshStandardMaterial({color:detailed?0xf08a24:0xf3c08f,roughness:.5});
  // barrel z in [-.30,.20]
  const barrel=cyl(.065,.065,.5,40,glass);barrel.position.z=-.05;body.add(barrel);
  const fluid=cyl(.057,.057,1,32,liquid);body.add(fluid);
  const stopper=cyl(.058,.058,.03,32,rubber);body.add(stopper);
  const rod=cyl(.018,.018,.32,16,plastic);body.add(rod);
  const thumb=cyl(.07,.07,.015,32,plastic);body.add(thumb);
  const flange=new THREE.Mesh(new THREE.BoxGeometry(.24,.012,.035),plastic);flange.position.z=-.3;body.add(flange);
  const nose=cyl(.065,.022,.05,32,glass);nose.position.z=.225;body.add(nose);
  const hub=cyl(.024,.017,.06,24,hubMat);hub.position.z=.28;body.add(hub);
  const needle=cyl(.0045,.0045,.32,12,steel);needle.position.z=.47;body.add(needle);
  const tip=new THREE.Mesh(new THREE.ConeGeometry(.0045,.03,12),steel);tip.rotation.x=Math.PI/2;tip.position.z=.645;body.add(tip);
  const cap=cyl(.02,.017,.34,20,capMat);cap.position.z=.48;body.add(cap);
  const drop=new THREE.Mesh(new THREE.SphereGeometry(1,16,12),liquid);drop.position.z=.66;drop.visible=false;body.add(drop);
  if(detailed){ // graduation marks
    const markMat=new THREE.MeshBasicMaterial({color:0x2c3e50});
    for(let i=0;i<9;i++){const m=new THREE.Mesh(new THREE.BoxGeometry(.003,.03,.004),markMat);
      m.position.set(0,.066,-.24+i*.05);body.add(m);}
  }
  const setPlunger=f=>{ // f: 0 full .. 1 empty
    const front=.19,back=-.29,stopZ=back+(front-back)*f;
    stopper.position.z=stopZ;rod.position.z=stopZ-.175;thumb.position.z=stopZ-.34;
    const len=Math.max(.001,front-stopZ-.016);fluid.scale.y=len;fluid.position.z=stopZ+.016+len/2;
  };
  const setNeedle=k=>{ // k: visible fraction of the needle (1 = all, smaller = inside the skin)
    const L=.32*k;needle.scale.y=k;needle.position.z=.31+L/2;tip.position.z=.31+L+.015;tip.visible=k>.95;
  };
  setPlunger(.05);
  return {root,body,cap,drop,setPlunger,setNeedle};
}
function arm(){
  const g=new THREE.Group();
  const skin=new THREE.MeshStandardMaterial({color:0xd9a98b,roughness:.75});
  const fore=new THREE.Mesh(new THREE.CapsuleGeometry(.13,1.3,8,24),skin);fore.rotation.z=Math.PI/2;g.add(fore);
  const sleeve=new THREE.Mesh(new THREE.CylinderGeometry(.16,.16,.35,24),new THREE.MeshStandardMaterial({color:0x3b5c7a,roughness:.9}));
  sleeve.rotation.z=Math.PI/2;sleeve.position.x=-.75;g.add(sleeve);
  const swab=new THREE.Mesh(new THREE.CircleGeometry(.05,24),new THREE.MeshStandardMaterial({color:0xf2e6dc,roughness:.9}));
  swab.position.set(.05,.131,0);swab.rotation.x=-Math.PI/2;g.add(swab);
  g.position.set(0,.02,.05);return g;
}

export class NeedleScene {
  constructor(scene){
    this.scene=scene;this.items=[];this.arm=arm();this.arm.visible=false;scene.add(this.arm);
    this.group=new THREE.Group();this.group.visible=false;scene.add(this.group);
  }
  clear(){this.group.visible=false;this.arm.visible=false;}
  show(plan){
    const n=plan.count||1;
    while(this.items.length<n){const s=createSyringe(true),f=createSyringe(false);this.group.add(s.root,f.root);this.items.push({real:s,simple:f});}
    this.items.forEach((it,i)=>{it.real.root.visible=i<n&&plan.realistic;it.simple.root.visible=i<n&&!plan.realistic;});
    this.group.visible=true;this.arm.visible=plan.view==='inject'&&n===1;this.plan=plan;
  }
  render(time,plan,speed=1){
    const n=plan.count||1,t=time*speed;
    for(let i=0;i<n;i++){
      const it=this.items[i],s=plan.realistic?it.real:it.simple;
      const pose=n>1?crowdPose(time,{...plan,behavior:plan.behavior==='inject'?'approach':plan.behavior},i,speed):
        {x:0,y:0,z:0,scale:plan.scale,yaw:0,pitch:0};
      let x=pose.x,y=pose.y,z=pose.z,yaw=0,pitch=0,roll=0,sc=pose.scale;
      s.cap.visible=!!plan.cap;s.drop.visible=false;s.setPlunger(.05);s.setNeedle(1);
      const v=plan.view;
      if(v==='side'){yaw=Math.PI/2;}
      else if(v==='turn'){yaw=Math.PI/2+Math.sin(t*.35+i)*.9;pitch=Math.sin(t*.27+i)*.12;}
      else if(v==='front'){ // approach handled by crowdPose/sampleMotion for crowds; single: own loop
        if(n===1){const ph=(t%20)/20,d=.5-.5*Math.cos(ph*Math.PI*2);z=d*.85;y=d*.25;}
        yaw=.35+Math.sin(t*.3+i)*.08;pitch=-.15;
      }
      else if(v==='tip'){yaw=.55+Math.sin(t*.3)*.18;pitch=-.25+Math.sin(t*.22)*.06;z=.35;y=-.08;
        const g=(t%6)/6;s.drop.visible=true;s.drop.scale.setScalar(.004+.01*Math.min(1,g*1.4));}
      else if(v==='inject'&&n===1){
        // 10 s loop: approach (0-3), enter (3-4), push (4-7), withdraw (7-9), pause
        const c=t%10;let enter=0,push=0,away=1;
        if(c<3)away=1-c/3;else if(c<4){away=0;enter=c-3;}else if(c<7){away=0;enter=1;push=(c-4)/3;}
        else if(c<9){enter=1-(c-7)/2;away=0;push=1;}else{away=(c-9);push=1;}
        yaw=-Math.PI/2*.55;pitch=.62; // tip down-left toward the arm
        x=.2+away*.35;y=.27+away*.25;z=.05+away*.1;
        s.setPlunger(.05+.9*push);s.setNeedle(1-.6*enter);
      }
      s.root.position.set(x,y,z);s.root.rotation.set(pitch,yaw,roll,'YXZ');s.root.scale.setScalar(sc);
    }
  }
  label(time,plan){
    const v=plan.view,c=time%10;
    if(v==='inject')return c<3?'Needle moving to the arm':c<4?'Needle goes in':c<7?'Medicine going in':c<9?'Needle comes out':'Done · repeating';
    return {side:'Still syringe',turn:'Slowly turning',front:'Coming closer, then back',tip:'Close-up · a drop forms'}[v]||'';
  }
}

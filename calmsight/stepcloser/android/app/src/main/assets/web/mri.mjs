import * as THREE from './vendor/three.module.js';
// MRI rehearsal: the scanner from across the room, at the opening, and lying inside
// the bore, plus synthesized scanner knocking (VR-with-MRI-sounds style rehearsal).
export class MriScene {
  constructor(scene){
    this.group=new THREE.Group();this.group.visible=false;scene.add(this.group);
    const white=new THREE.MeshStandardMaterial({color:0xe9eef2,roughness:.45});
    const grey=new THREE.MeshStandardMaterial({color:0x8fa3b3,roughness:.6});
    const blue=new THREE.MeshStandardMaterial({color:0x2d6ea3,roughness:.5});
    const inner=new THREE.MeshStandardMaterial({color:0x5d6870,roughness:.8,side:THREE.BackSide});
    // housing: a thick ring with a bore, along Z
    const housing=new THREE.Mesh(new THREE.TorusGeometry(1.05,.55,24,64),white);
    housing.scale.set(1,1,1.6);this.group.add(housing);
    const face=new THREE.Mesh(new THREE.RingGeometry(.5,1.55,64),white);face.position.z=.9;this.group.add(face);
    const trim=new THREE.Mesh(new THREE.TorusGeometry(.52,.035,12,64),blue);trim.position.z=.92;this.group.add(trim);
    const bore=new THREE.Mesh(new THREE.CylinderGeometry(.5,.5,2.4,48,1,true),inner);bore.rotation.x=Math.PI/2;this.group.add(bore);
    // rings and a light strip inside the bore, so movement and closeness read clearly
    for(let i=0;i<9;i++){const r=new THREE.Mesh(new THREE.TorusGeometry(.5,.006,6,48),grey);r.position.z=-1.1+i*.27;this.group.add(r);}
    const strip=new THREE.Mesh(new THREE.BoxGeometry(.02,.01,2.2),new THREE.MeshBasicMaterial({color:0x9a8f78}));
    strip.position.set(0,.49,0);this.group.add(strip);
    const table=new THREE.Mesh(new THREE.BoxGeometry(.7,.08,3.2),grey);table.position.set(0,-.4,1.6);this.group.add(table);
    const base=new THREE.Mesh(new THREE.BoxGeometry(.6,.6,1.8),white);base.position.set(0,-.78,2.3);this.group.add(base);
    this.light=new THREE.PointLight(0xfff1d8,1.2,4);this.group.add(this.light);
    this.saved=null;this.plan=null;this.audio=null;
  }
  show(plan,camera){
    this.plan=plan;this.group.visible=true;
    if(!this.saved)this.saved={pos:camera.position.clone(),fov:camera.fov};
    this.sound(plan.sound||0);
  }
  clear(camera){
    this.group.visible=false;this.sound(0);
    if(this.saved&&camera){camera.position.copy(this.saved.pos);camera.fov=this.saved.fov;camera.updateProjectionMatrix();camera.lookAt(0,.08,0);}
    this.saved=null;
  }
  render(t,camera){
    const v=this.plan?.view||'outside',tilt=this.plan?.tilt||0;
    this.group.position.set(0,0,0);this.group.rotation.set(0,0,0);
    camera.fov=v==='inside'?70:45;camera.updateProjectionMatrix();
    if(v==='outside'){
      const drift=Math.sin(t*.15)*.3;
      camera.position.set(1.6+drift,.5,6.2);camera.lookAt(0,0,0);this.group.rotation.y=-.5+tilt;
    }else if(v==='entrance'){
      const k=.5-.5*Math.cos(Math.min(1,t/14)*Math.PI);
      camera.position.set(.15,.05,3.4-1.6*k);camera.lookAt(0,0,0);
    }else{
      // lying on the table, sliding in, looking up at the bore ceiling
      const k=Math.min(1,t/10);
      camera.position.set(0,-.18,1.4-1.6*k);
      camera.lookAt(0,.6+tilt,camera.position.z-.9);
    }
    this.light.position.set(0,.3,camera.position.z);
    if(this.audio)this.audio.tick(t);
  }
  label(t){
    const v=this.plan?.view;
    if(v==='outside')return 'The scanner, from across the room';
    if(v==='entrance')return 'Moving closer to the opening';
    return (t<10?'Sliding in':'Inside the tunnel')+(this.plan?.sound?' · scanner sounds':'');
  }
  sound(level){
    if(this.audio){this.audio.stop();this.audio=null;}
    if(!level)return;
    try{this.audio=new Knocker(level);}catch{this.audio=null;}
  }
}
// MRI-like knocking: blocks of fast tonal knocks with short pauses between sequences.
class Knocker{
  constructor(level){
    const AC=window.AudioContext||window.webkitAudioContext;this.ctx=new AC();
    this.gain=this.ctx.createGain();this.gain.gain.value=level>1?.22:.12;this.gain.connect(this.ctx.destination);
    this.level=level;this.next=this.ctx.currentTime+.6;this.stopped=false;
    this.timer=setInterval(()=>this.schedule(),120);
  }
  schedule(){
    if(this.stopped)return;
    const ctx=this.ctx,now=ctx.currentTime;
    while(this.next<now+.4){
      const block=Math.floor(this.next/6)%3,inBlock=(this.next%6)<4.6;
      if(inBlock){
        const o=ctx.createOscillator(),g=ctx.createGain();
        o.type=block===1?'sawtooth':'square';o.frequency.value=[440,880,620][block];
        g.gain.setValueAtTime(0,this.next);g.gain.linearRampToValueAtTime(1,this.next+.004);
        g.gain.exponentialRampToValueAtTime(.001,this.next+.05);
        o.connect(g);g.connect(this.gain);o.start(this.next);o.stop(this.next+.06);
      }
      this.next+=[.24,.12,.36][block];
    }
  }
  tick(){if(this.ctx.state==='suspended')this.ctx.resume().catch(()=>{});}
  stop(){this.stopped=true;clearInterval(this.timer);try{this.ctx.close();}catch{}}
}

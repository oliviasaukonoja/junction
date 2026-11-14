import * as THREE from './vendor/three.module.js';

function random(seed){return ()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};}
function bodyTexture(seed){
  const c=document.createElement('canvas');c.width=256;c.height=128;
  const ctx=c.getContext('2d'),img=ctx.createImageData(256,128),rnd=random(seed);
  for(let y=0;y<128;y++)for(let x=0;x<256;x++){
    const u=x/256,v=y/128;
    const stripe=Math.pow(Math.max(0,Math.sin(u*Math.PI*12+Math.sin(v*11)*1.3)),7);
    const band=Math.exp(-Math.pow((v-.5)*7,2));
    const n=rnd()*25,base=43+25*band-17*stripe+n,i=(y*256+x)*4;
    img.data[i]=base*1.35;img.data[i+1]=base*.91;img.data[i+2]=base*.60;img.data[i+3]=255;
  }
  ctx.putImageData(img,0,0);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;
}
function furEllipsoid(rx,ry,rz,count,seed){
  const rnd=random(seed),vertices=[],colors=[];
  for(let i=0;i<count;i++){
    const y=rnd()*1.8-.7,a=rnd()*Math.PI*2,k=Math.sqrt(Math.max(0,1-y*y));
    const n=new THREE.Vector3(k*Math.cos(a),y,k*Math.sin(a)).normalize();
    const p=new THREE.Vector3(n.x*rx,n.y*ry,n.z*rz);
    const len=.009+rnd()*.021;
    vertices.push(p.x,p.y,p.z,p.x+n.x*len,p.y+n.y*len,p.z+n.z*len);
    const color=new THREE.Color().setHSL(.075+rnd()*.025,.25,.18+rnd()*.17);
    colors.push(color.r,color.g,color.b,color.r,color.g,color.b);
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));
  g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));
  return new THREE.LineSegments(g,new THREE.LineBasicMaterial({vertexColors:true,transparent:true,opacity:.65}));
}
const sphere=new THREE.SphereGeometry(1,36,24);
const crowdSphere=new THREE.SphereGeometry(1,14,10);
const boneGeometry=new Map();
const up=new THREE.Vector3(0,1,0);

function ellipsoid(parent,material,position,scale,fur=false,seed=2,geometry=sphere){
  const group=new THREE.Group();group.position.set(...position);parent.add(group);
  const mesh=new THREE.Mesh(geometry,material);mesh.scale.set(...scale);
  mesh.castShadow=true;group.add(mesh);
  if(fur)group.add(furEllipsoid(...scale,seed===2?1300:800,seed));
  return group;
}
function segment(parent,material,r1,r2,seed,hairy){
  const root=new THREE.Group();parent.add(root);
  const key=r1+':'+r2;
  if(!boneGeometry.has(key))boneGeometry.set(key,new THREE.CylinderGeometry(r2,r1,1,10));
  const mesh=new THREE.Mesh(boneGeometry.get(key),material);
  mesh.castShadow=true;root.add(mesh);
  if(hairy){
    const rnd=random(seed),pos=[];
    for(let i=0;i<85;i++){
      const a=rnd()*Math.PI*2,y=rnd()-.5,r=(r1+r2)/2;
      const x=Math.cos(a),z=Math.sin(a),l=.009+rnd()*.012;
      pos.push(x*r,y,z*r,x*(r+l),y+.006,z*(r+l));
    }
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
    root.add(new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:0x9d7f60,transparent:true,opacity:.5})));
  }
  return root;
}
function placeSegment(group,a,b){
  const d=new THREE.Vector3().subVectors(b,a);
  group.position.copy(a).add(b).multiplyScalar(.5);
  group.quaternion.setFromUnitVectors(up,d.clone().normalize());
  group.scale.set(1,d.length(),1);
}
export function createSpider(realistic=true,seed=7,options={}){
  const root=new THREE.Group(),body=new THREE.Group();root.add(body);
  const withHair=realistic&&options.hair!==false;
  const modelSphere=options.lowPoly?crowdSphere:sphere;
  const part=(material,position,scale,hairy=false,partSeed=2)=>
    ellipsoid(body,material,position,scale,hairy&&withHair,partSeed,modelSphere);
  const coat=new THREE.MeshStandardMaterial({
    color:realistic?0xe2d3c0:0xc4dcc9,roughness:.91,metalness:0,
    map:realistic?bodyTexture(seed):null
  });
  const legMaterial=new THREE.MeshStandardMaterial({color:realistic?0x66503b:0xc4dcc9,roughness:.86});
  const jointMaterial=new THREE.MeshStandardMaterial({color:realistic?0x403127:0xa2b7ad,roughness:.9});
  const eyeMaterial=new THREE.MeshPhysicalMaterial({color:0x090b09,roughness:.12,clearcoat:1});
  part(coat,[0,.285,-.28],[.185,.15,.27],true,2);
  part(coat,[0,.285,.045],[.165,.105,.19],true,9);
  part(coat,[0,.27,.215],[.113,.085,.095],true,11);
  if(realistic){
    for(let i=0;i<8;i++){
      const row=i<4?0:1,j=i%4,x=(j-1.5)*.039;
      part(eyeMaterial,[x,.309+row*.022,.291-row*.013],[.012,.013,.010]);
    }
    for(const s of [-1,1]){
      part(jointMaterial,[s*.043,.217,.298],[.026,.047,.043],true,13);
      const fang=new THREE.Mesh(new THREE.ConeGeometry(.012,.055,12),eyeMaterial);
      fang.rotation.x=Math.PI*.72;fang.position.set(s*.04,.19,.323);body.add(fang);
      const palp=segment(body,coat,.018,.010,9,withHair);
      placeSegment(palp,new THREE.Vector3(s*.085,.26,.25),new THREE.Vector3(s*.16,.15,.38));
    }
  }
  const legs=[];
  for(let s=0;s<2;s++)for(let i=0;i<4;i++){
    const side=s===0?-1:1,z=[.19,.075,-.055,-.18][i];
    const parts=[
      segment(body,jointMaterial,.032,.025,seed+i,withHair),
      segment(body,coat,.027,.019,seed+i+20,withHair),
      segment(body,legMaterial,.021,.013,seed+i+50,withHair),
      segment(body,legMaterial,.014,.005,seed+i+80,withHair)
    ];
    const joints=[0,1,2].map(()=>{const m=new THREE.Mesh(modelSphere,jointMaterial);m.scale.setScalar(.022);body.add(m);return m;});
    legs.push({side,index:i,z,parts,joints,phase:(i%2)*.5+s*.5});
  }
  root.userData.legCount=legs.length;
  const tip=new THREE.Vector3(),hip=new THREE.Vector3(),coxa=new THREE.Vector3();
  const knee=new THREE.Vector3(),ankle=new THREE.Vector3();
  const update=(time,motion,airborne=0)=>{
    const moving=motion>0,t=time*(motion===1?.8:1.25);
    body.position.y=(moving?Math.sin(t*Math.PI*4)*.004:0)*(1-airborne)+.025*airborne;
    for(const leg of legs){
      const phase=(t+leg.phase)%1,stance=.64,stride=motion>=2?.14:.035;
      let swingZ=0,lift=0;
      if(moving){
        if(phase<stance)swingZ=stride*(.5-phase/stance);
        else {const q=(phase-stance)/(1-stance);swingZ=stride*(-.5+q);lift=Math.sin(q*Math.PI)*.055;}
      }
      const footX=[.51,.61,.60,.49][leg.index],footZ=[.63,.29,-.26,-.64][leg.index];
      hip.set(leg.side*.125,.275,leg.z);
      coxa.set(leg.side*.20,.29,leg.z+(leg.index<2?.04:-.035));
      tip.set(leg.side*footX*(1-.20*airborne),.018+lift+.12*airborne,(footZ+swingZ)*(1-.15*airborne));
      ankle.copy(tip).add(new THREE.Vector3(-leg.side*.034,.06,-.025));
      // Two-bone IK keeps the planted foot stable during each stance.
      const d=new THREE.Vector3().subVectors(ankle,coxa),distance=d.length();
      const a=.39,b=.45,unit=d.clone().normalize(),along=(a*a-b*b+distance*distance)/(2*distance);
      const normal=new THREE.Vector3(0,1,0).addScaledVector(unit,-unit.y).normalize();
      knee.copy(coxa).addScaledVector(unit,along).addScaledVector(normal,Math.sqrt(Math.max(.001,a*a-along*along)));
      placeSegment(leg.parts[0],hip,coxa);
      placeSegment(leg.parts[1],coxa,knee);
      placeSegment(leg.parts[2],knee,ankle);
      placeSegment(leg.parts[3],ankle,tip);
      leg.joints[0].position.copy(coxa);leg.joints[1].position.copy(knee);leg.joints[2].position.copy(ankle);
    }
  };
  update(0,0);return {root,update,legs};
}

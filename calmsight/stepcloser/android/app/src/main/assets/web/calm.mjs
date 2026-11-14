// Real-life coach view for the lens: no virtual object, just a calm breathing guide,
// your fear number and one short coach line. Black = transparent on Meta Ray-Ban Display.
const IN=4, OUT=6; // seconds: breathe in 4, out 6
export class CalmScene {
  constructor(canvas){
    this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});
    this.transferCanvas=document.createElement('canvas');
    this.transferContext=this.transferCanvas.getContext('2d',{alpha:false});
    this.visible=false;this.rating=null;this.line='';this.label='';this.place='';this.visual='breath';
    this.clear();
  }
  clear(){this.visible=false;this.ctx.fillStyle='#000';this.ctx.fillRect(0,0,600,600);}
  dot(){this.clear();}
  show(plan,place=''){this.visible=true;this.place=place;this.rating=null;this.label='';this.visual='text';
    this.line='How scared are you? Tap 0–10 on your phone.';this.render(0);}
  set(update){Object.assign(this,update);}
  breath(t){
    const p=t%(IN+OUT);
    return p<IN?{phase:'Breathe in',u:p/IN}:{phase:'Breathe out',u:1-(p-IN)/OUT};
  }
  render(time){
    if(!this.visible)return;
    const c=this.ctx,b=this.breath(time),ease=.5-.5*Math.cos(Math.PI*b.u),v=this.visual||'breath';
    c.fillStyle='#000';c.fillRect(0,0,600,600);c.textAlign='center';
    const teal='rgba(120,220,200,.95)',soft='rgba(120,220,200,.3)';
    const ring=(r,w,col)=>{c.lineWidth=w;c.strokeStyle=col;c.beginPath();c.arc(300,240,r,0,Math.PI*2);c.stroke();};
    // fear number, small, top
    if(this.rating!==null&&this.rating!==undefined){c.font='600 26px system-ui,sans-serif';c.fillStyle='#9fe7d6';c.fillText('FEAR '+this.rating+' / 10',300,46);}
    let center='',sub='';
    if(v==='breath'){ring(110+70*ease,10,teal);ring(185,2,soft);center=b.phase;}
    else if(v==='squeeze'){
      const p=time%20,hold=p<10,u=hold?p/10:(p-10)/10;
      ring(170,4,soft);c.lineWidth=14;c.strokeStyle=hold?'rgba(255,190,120,.95)':teal;
      c.beginPath();c.arc(300,240,170,-Math.PI/2,-Math.PI/2+Math.PI*2*u);c.stroke();
      center=hold?String(10-Math.floor(p)):'Release';sub=hold?'Squeeze & hold':'Let go';
    }
    else if(v==='spot'){
      const pulse=6+3*Math.sin(time*2);c.fillStyle='#fff';c.beginPath();c.arc(300,240,pulse,0,Math.PI*2);c.fill();
      ring(60,2,soft);sub='Eyes here';
    }
    else if(v==='count'){ring(170,4,soft);center=String(Math.max(0,20-Math.floor(time/1.6)%21));sub='Count with me';}
    else if(v==='list'){
      const step=Math.floor(time/9)%5,labels=['5 see','4 touch','3 hear','2 smell','1 taste'];
      c.font='600 30px system-ui,sans-serif';
      labels.forEach((l,i)=>{c.fillStyle=i===step?'#ffffff':'rgba(160,220,210,.45)';c.fillText(l,300,150+i*48);});
    }
    else {ring(150+6*Math.sin(time),3,soft);}
    if(center){c.fillStyle='#fff';c.font=(center.length<3?'700 110px':'600 46px')+' system-ui,sans-serif';c.fillText(center,300,center.length<3?278:258);}
    if(sub){c.font='600 26px system-ui,sans-serif';c.fillStyle='#9fe7d6';c.fillText(sub,300,v==='spot'?330:322);}
    if(this.label){c.font='700 24px system-ui,sans-serif';c.fillStyle='#9fe7d6';c.fillText(this.label.toUpperCase(),300,450);}
    c.font='500 27px system-ui,sans-serif';c.fillStyle='#f2f2f2';
    wrap(c,this.line,300,494,550,34,3);
  }
  motionLabel(time){return this.breath(time).phase+(this.place?' · '+this.place:'');}
  capture(size=384,quality=.76){
    if(this.transferCanvas.width!==size){this.transferCanvas.width=size;this.transferCanvas.height=size;}
    this.transferContext.drawImage(this.canvas,0,0,size,size);
    return this.transferCanvas.toDataURL('image/jpeg',quality).split(',')[1];
  }
  diagnostics(){return {webgl:false,calm:true,visible:this.visible};}
}
function wrap(c,text,x,y,max,lh,lines){
  const words=(text||'').split(/\s+/);let line='',out=[];
  for(const w of words){const t=line?line+' '+w:w;if(c.measureText(t).width>max&&line){out.push(line);line=w;}else line=t;}
  if(line)out.push(line);
  if(out.length>lines){out=out.slice(0,lines);out[lines-1]=out[lines-1].replace(/\s*\S*$/,'')+'…';}
  out.forEach((l,i)=>c.fillText(l,x,y+i*lh));
}

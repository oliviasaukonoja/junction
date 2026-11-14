// Everything the glasses show is drawn here, 600×600. Black is transparent on
// Meta Ray-Ban Display, so all text is bright and nothing fills the background.
const TEAL='#8fe3cf',WARM='#ffc27a',WHITE='#f4f4f4';
export class Lens {
  constructor(canvas){
    this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});
    this.out=document.createElement('canvas');this.outCtx=this.out.getContext('2d',{alpha:false});
    this.s={mode:'off'};this.visible=false;this.clear();
  }
  set(state){this.s={...this.s,...state};this.visible=this.s.mode!=='off';}
  clear(){this.s={mode:'off'};this.visible=false;const c=this.ctx;c.fillStyle='#000';c.fillRect(0,0,600,600);}
  render(t){
    const c=this.ctx,s=this.s;c.fillStyle='#000';c.fillRect(0,0,600,600);
    if(s.mode==='off')return;
    c.textAlign='center';c.textBaseline='alphabetic';
    if(s.mode==='stim'&&s.source)c.drawImage(s.source,0,0,600,600);
    if(s.mode==='tension')this.tension(t);
    if(s.mode==='calm')this.calm(t);
    if(s.mode==='prompt')this.prompt();
    // header: where you are + your fear number
    c.font='600 22px system-ui,sans-serif';c.fillStyle=TEAL;
    if(s.title){c.textAlign='left';c.fillText(s.title.toUpperCase(),24,40);}
    if(s.fear!=null){c.textAlign='right';c.fillStyle=s.fear>=7?WARM:TEAL;c.fillText('FEAR '+s.fear,576,40);}
    if(s.timer){c.textAlign='right';c.fillStyle=TEAL;c.font='600 20px system-ui,sans-serif';c.fillText(s.timer,576,68);}
    c.textAlign='center';
    if(s.mode!=='prompt'&&s.line){c.font='600 27px system-ui,sans-serif';c.fillStyle=WHITE;shadowed(c,()=>wrap(c,s.line,300,500,540,34,3));}
    if(s.heard){c.font='italic 20px system-ui,sans-serif';c.fillStyle='rgba(143,227,207,.8)';wrap(c,'“'+s.heard+'”',300,s.mode==='prompt'?560:470,540,24,1);}
  }
  prompt(){
    const c=this.ctx,s=this.s;
    c.font='600 34px system-ui,sans-serif';c.fillStyle=WHITE;
    const lines=wrap(c,s.line||'',300,150,540,42,4);
    let y=150+lines*42+20;
    if(s.options?.length){
      c.font='500 26px system-ui,sans-serif';
      s.options.slice(0,4).forEach((o,i)=>{c.fillStyle=i===s.highlight?WARM:TEAL;wrap(c,o,300,y+i*44,540,30,1);});
      y+=s.options.slice(0,4).length*44;
    }
    if(s.hint){c.font='500 22px system-ui,sans-serif';c.fillStyle='rgba(143,227,207,.75)';c.fillText(s.hint,300,Math.min(y+26,540));}
  }
  tension(t){
    const c=this.ctx,s=this.s,p=s.phaseLeft??0,tense=s.phase==='tense',total=tense?s.tenseSec:s.releaseSec;
    ring(c,170,4,'rgba(143,227,207,.3)');
    c.lineWidth=16;c.strokeStyle=tense?WARM:TEAL;c.beginPath();
    c.arc(300,250,170,-Math.PI/2,-Math.PI/2+Math.PI*2*(1-p/Math.max(1,total)));c.stroke();
    c.fillStyle=WHITE;c.font='700 110px system-ui,sans-serif';c.fillText(String(Math.ceil(p)),300,290);
    c.font='700 30px system-ui,sans-serif';c.fillStyle=tense?WARM:TEAL;c.fillText(tense?'TENSE & HOLD':'RELEASE',300,340);
    c.font='500 22px system-ui,sans-serif';c.fillStyle=TEAL;c.fillText('Round '+s.round+' of '+s.rounds,300,445);
  }
  calm(t){
    const c=this.ctx,u=.5+.5*Math.sin(t*.9);
    ring(c,120+18*u,6,'rgba(143,227,207,.85)');ring(c,170,2,'rgba(143,227,207,.25)');
    c.fillStyle=WHITE;c.font='600 40px system-ui,sans-serif';c.fillText(this.s.big||'With you',300,265);
    if(this.s.sub){c.font='500 24px system-ui,sans-serif';c.fillStyle=TEAL;c.fillText(this.s.sub,300,305);}
  }
  capture(size=384,quality=.76){
    if(this.out.width!==size){this.out.width=size;this.out.height=size;}
    this.outCtx.drawImage(this.canvas,0,0,size,size);
    return this.out.toDataURL('image/jpeg',quality).split(',')[1];
  }
}
function ring(c,r,w,col){c.lineWidth=w;c.strokeStyle=col;c.beginPath();c.arc(300,250,r,0,Math.PI*2);c.stroke();}
function shadowed(c,fn){c.save();c.shadowColor='#000';c.shadowBlur=8;fn();c.restore();}
function wrap(c,text,x,y,max,lh,maxLines){
  const words=String(text||'').split(/\s+/).filter(Boolean);let line='',out=[];
  for(const w of words){const t=line?line+' '+w:w;if(c.measureText(t).width>max&&line){out.push(line);line=w;}else line=t;}
  if(line)out.push(line);
  if(out.length>maxLines){out=out.slice(0,maxLines);out[maxLines-1]=out[maxLines-1].replace(/\s*\S*$/,'')+'…';}
  out.forEach((l,i)=>c.fillText(l,x,y+i*lh));return out.length;
}

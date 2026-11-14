// Motion is camera-relative inside the lens panel, without world tracking.
export const FIRST_JUMP=14;
export const JUMP_PERIOD=18;
export const JUMP_DURATION=3.2;
const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));
export function jumpClock(seconds){
  const t=Math.max(0,seconds);
  if(t<FIRST_JUMP)return {airborne:0,arc:0,until:FIRST_JUMP-t,jumping:false};
  const phase=(t-FIRST_JUMP)%JUMP_PERIOD;
  const jumping=phase<JUMP_DURATION;
  const u=clamp(phase/JUMP_DURATION,0,1);
  return {airborne:jumping?Math.sin(Math.PI*u)**2:0,
    arc:jumping?Math.sin(Math.PI*u)**2:0,
    until:jumping?0:JUMP_PERIOD-phase,jumping};
}
export function sampleMotion(seconds,plan,index=0,speed=1){
  const elapsed=Math.max(0,seconds),t=elapsed*speed,orbit=plan.behavior==='orbit'||plan.behavior==='orbitJump';
  const jump=plan.behavior==='orbitJump'?jumpClock(elapsed):{airborne:0,arc:0,until:Infinity,jumping:false};
  const p=jump.airborne;
  if(plan.behavior==='approach'){
    const phase=(t+index*1.7)%20,depth=.60*(.5-.5*Math.cos(phase*Math.PI/10));
    return {x:Math.sin(t*.3)*.035,y:depth*.50,z:depth*.862,
      yaw:Math.sin(t*.3)*.08,pitch:0,scale:plan.scale,airborne:0,
      label:phase<10?'Walking toward your view':'Walking back · repeating'};
  }
  if(orbit){
    const angle=t*.39+index*2.399963;
    const baseYaw=-angle+.4;
    const faceViewer=Math.atan2(Math.sin(-baseYaw),Math.cos(-baseYaw));
    return {
      x:Math.sin(angle)*.12*(1-p),
      y:Math.cos(angle)*.14-.05+.21*p,
      z:-Math.cos(angle)*.06-.15+.42*p,
      yaw:baseYaw+faceViewer*p,pitch:-.20*p,
      scale:plan.scale*(1+.06*p),airborne:p,
      label:jump.jumping?'Jumping toward your view':
        plan.behavior==='orbitJump'?(jump.until<=3?'Jump in '+Math.ceil(jump.until)+'…':
          'Circling · next jump in '+Math.ceil(jump.until)+'s'):'Circling within your view'
    };
  }
  const walking=plan.motion===2;
  return {x:walking?Math.sin(t*.28+index)*.11:0,y:0,
    z:walking?Math.sin(t*.37+index)*.09:0,
    yaw:walking?Math.sin(t*.28+index)*.22:0,pitch:0,
    scale:plan.scale,airborne:0,label:walking?'Slow walking':plan.motion===1?'Gentle leg movement':'Still model'};
}
export function crowdPose(seconds,plan,index,speed=1){
  const count=plan.count||1;
  const pose=sampleMotion(seconds,plan,index,speed);
  if(count===1)return pose;
  const cols=Math.ceil(Math.sqrt(count)),rows=Math.ceil(count/cols);
  const row=Math.floor(index/cols),col=index%cols,factor=1.1/Math.max(cols,rows);
  const slotsInRow=Math.min(cols,count-row*cols);
  const x=(col-(slotsInRow-1)/2)*1.55*plan.scale*factor;
  const up=((rows-1)/2-row)*1.25*plan.scale*factor;
  return {...pose,x:x+pose.x*factor,y:-.12+up*.862+pose.y*factor,
    z:-.10-up*.507+pose.z*factor,scale:pose.scale*factor};
}
// Repeating support continues throughout long sessions. Upcoming jumps are
// announced through the glasses' selected media output, without loud effects.
export function guideCue(seconds,plan){
  if(!['approach','orbit','orbitJump'].includes(plan.behavior))return null;
  const t=Math.max(0,seconds);
  if(plan.behavior==='orbit'||plan.behavior==='approach'){
    if(t<6)return null;
    const n=Math.floor((t-6)/8);
    return {id:'orbit-'+n,key:['circle_breathe','circle_notice','circle_choice'][n%3]};
  }
  const cycle=Math.max(0,Math.floor((t-6)/JUMP_PERIOD)),base=6+cycle*JUMP_PERIOD;
  if(t<base)return null;
  const offset=t-base;
  if(offset>=12)return {id:'recover-'+cycle,key:'jump_recover'};
  if(offset>=5)return {id:'jump-'+cycle,key:'jump_cue'};
  return {id:'breathe-'+cycle,key:'circle_breathe'};
}

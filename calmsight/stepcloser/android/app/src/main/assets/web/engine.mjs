export const LEVELS = Object.freeze([
  {id:1,name:'A gentle start',detail:'Larger simplified 3D spider · still',scale:0.48,motion:0,realistic:false,count:1},
  {id:2,name:'Look at the detail',detail:'Large detailed 3D spider · still',scale:0.78,motion:0,realistic:true,count:1},
  {id:3,name:'A little movement',detail:'Large detailed spider · gentle leg movement',scale:0.82,motion:1,realistic:true,count:1},
  {id:4,name:'Walking toward you',detail:'Large spider · walks closer, then retreats · calming guide',scale:0.86,motion:2,behavior:'approach',realistic:true,count:1},
  {id:5,name:'Circling your view',detail:'Large spider · circles within the lens view · calming guide',scale:0.95,motion:2,behavior:'orbit',realistic:true,count:1},
  {id:6,name:'Circling & jumps',detail:'Advanced · large spider circles and jumps toward your view · spoken jump cues',scale:0.95,motion:3,behavior:'orbitJump',realistic:true,count:1}
]);
export const NEEDLE_LEVELS=Object.freeze([
  {id:1,name:'A friendly syringe',detail:'Simple soft-coloured syringe · cap on · still',scale:.95,motion:0,realistic:false,count:1,fear:'needles',cap:true,view:'side'},
  {id:2,name:'A real syringe',detail:'Realistic syringe · cap on · slowly turning',scale:.8,motion:1,realistic:true,count:1,fear:'needles',cap:true,view:'turn'},
  {id:3,name:'Cap comes off',detail:'Needle uncovered · slowly turning',scale:.85,motion:1,realistic:true,count:1,fear:'needles',cap:false,view:'turn'},
  {id:4,name:'Needle coming closer',detail:'Tip points at you · comes closer, then backs away',scale:.9,motion:2,behavior:'approach',realistic:true,count:1,fear:'needles',cap:false,view:'front'},
  {id:5,name:'Close-up of the tip',detail:'Large needle tip · a drop forms · gentle tilt',scale:1.35,motion:1,realistic:true,count:1,fear:'needles',cap:false,view:'tip'},
  {id:6,name:'The injection',detail:'Advanced · needle goes into an arm · plunger pushed · repeats',scale:.95,motion:3,behavior:'inject',realistic:true,count:1,fear:'needles',cap:false,view:'inject'}
]);
export const SIZES=[.75,1,1.5,2];
export class Practice {
  constructor() {
    this.mode='phone'; this.level=4; this.duration=60; this.before=3;
    this.spiderCount=1;this.motionSpeed=1;this.fear='spiders';this.sizeFactor=1;
    this.consent=false; this.audioChecked=false; this.drillPassed=false;
    this.lensReady=false; this.renderReady=false; this.state='setup';
    this.serial=0; this.token=''; this.startedAt=null; this.lastResult=null;
    this.clearConfirmed=false; this.neutralShown=false;
  }
  get levels(){return this.fear==='needles'?NEEDLE_LEVELS:LEVELS;}
  get plan(){const b=this.levels[this.level-1];return {...b,fear:this.fear,count:this.spiderCount,scale:b.scale*this.sizeFactor};}
  configureFear(fear,size=this.sizeFactor){
    if(this.visible)throw Error('Stop before changing what you practise');
    if(!['spiders','needles'].includes(fear))throw Error('Unknown fear');
    if(!SIZES.includes(size))throw Error('Invalid size');
    this.fear=fear;this.sizeFactor=size;
  }
  get visible(){return ['starting','active'].includes(this.state);}
  get canStart(){
    return this.renderReady && (this.mode==='phone' || this.lensReady) &&
      ['setup','reflection','drillClear'].includes(this.state);
  }
  setMode(mode){
    if(!['phone','display'].includes(mode)) throw Error('Unknown output mode');
    if(this.visible) throw Error('Stop the activity before changing output');
    this.mode=mode; this.drillPassed=false; this.audioChecked=false; this.state='setup';
  }
  configure(level,duration,before){
    if(this.visible) throw Error('Stop before changing the plan');
    if(!Number.isInteger(level)||level<1||level>6) throw Error('Invalid level');
    if(![30,60,120,300].includes(duration)) throw Error('Invalid duration');
    if(!Number.isInteger(before)||before<0||before>10) throw Error('Invalid distress rating');
    this.level=level;this.duration=duration;this.before=before;
  }
  configureOptions(count,speed){
    if(this.visible)throw Error('Stop before changing the spider count or speed');
    if(!Number.isInteger(count)||count<1||count>20)throw Error('Spider count must be 1–20');
    if(![.5,1,1.5,2].includes(speed))throw Error('Invalid walking speed');
    this.spiderCount=count;this.motionSpeed=speed;
  }
  beginDrill(){
    if(this.mode==='display'&&!this.lensReady) throw Error('Connect the display first');
    if(this.visible) throw Error('Stop the activity first');
    this.drillPassed=false;this.neutralShown=this.mode==='phone';
    this.clearConfirmed=false;this.state='drill';
  }
  acknowledgeNeutral(){if(this.state==='drill')this.neutralShown=true;}
  acknowledgeClear(){if(this.state==='drillClear')this.clearConfirmed=true;}
  confirmDrill(){
    if(this.state!=='drillClear'||!this.neutralShown||!this.clearConfirmed)
      throw Error('Show the neutral dot, press STOP, and confirm it disappeared');
    this.drillPassed=true;this.state='setup';
  }
  start(){
    if(!this.canStart)throw Error('The 3D renderer and chosen display must be ready');
    this.token=String(++this.serial);this.startedAt=null;this.state='starting';return this.token;
  }
  shown(token,now){
    if(token!==this.token||this.state!=='starting')return false;
    this.startedAt=now;this.state='active';return true;
  }
  remaining(now){return this.startedAt===null?this.duration:Math.max(0,this.duration-(now-this.startedAt)/1000);}
  tick(now){
    if(this.state==='active'&&this.remaining(now)<=0){this.stop('completed',now);return true;}return false;
  }
  stop(reason='stopped',now=0){
    ++this.serial;this.token='';
    if(this.state==='drill'){
      this.state='drillClear';this.clearConfirmed=this.mode==='phone';return null;
    }
    if(this.visible){
      this.lastResult={
        date:new Date().toISOString(),level:this.level,mode:this.mode,before:this.before,
        count:this.spiderCount,motionSpeed:this.motionSpeed,
        after:null,plannedSeconds:this.duration,
        seconds:this.startedAt===null?0:Math.round(Math.max(0,Math.min(this.duration,(now-this.startedAt)/1000))),
        reason,shown:this.startedAt!==null
      };
      this.startedAt=null;this.state='reflection';return this.lastResult;
    }
    return null;
  }
  interrupted(now){this.lensReady=false;this.drillPassed=false;return this.stop('interrupted',now);}
}

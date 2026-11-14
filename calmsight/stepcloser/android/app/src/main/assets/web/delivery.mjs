export const PROFILES=Object.freeze({
  auto:{size:384,quality:.76,fps:15},
  fast:{size:256,quality:.66,fps:15},
  balanced:{size:384,quality:.78,fps:12},
  sharp:{size:512,quality:.86,fps:8}
});
// One outstanding frame. Capture a current pose only when the transport is
// available; never build a queue of historical animation frames.
export class FrameDelivery {
  constructor(profile='auto'){this.setProfile(profile);this.reset('');}
  setProfile(profile){
    if(!PROFILES[profile])throw Error('Unknown delivery profile');
    this.profile=profile;this.options={...PROFILES[profile]};this.sampleCount=0;
  }
  reset(token){
    this.token=token;this.sequence=0;this.inFlight=null;this.lastSend=-Infinity;
    this.averageMs=0;this.accepted=0;this.firstAck=null;this.lastAck=null;
    this.lastBytes=0;this.sampleCount=0;this.options={...PROFILES[this.profile]};
  }
  ready(now){return !!this.token&&!this.inFlight&&now-this.lastSend>=1000/this.options.fps;}
  begin(now){
    if(!this.ready(now))return null;
    const request={token:this.token,sequence:++this.sequence,capturedAtMs:now};
    this.inFlight=request;this.lastSend=now;return request;
  }
  rejected(sequence){
    if(this.inFlight?.sequence===sequence)this.inFlight=null;
  }
  acknowledge(event,now){
    const pending=this.inFlight;
    if(!pending||event.token!==this.token||Number(event.sequence)!==pending.sequence)return false;
    this.inFlight=null;
    if(String(event.accepted)!=='true')return false;
    const ms=Math.max(1,now-pending.capturedAtMs);
    this.averageMs=this.averageMs?this.averageMs*.75+ms*.25:ms;
    this.accepted++;this.sampleCount++;this.lastAck=now;
    if(this.firstAck===null)this.firstAck=now;
    this.lastBytes=Number(event.bytes)||0;
    if(this.profile==='auto'&&this.sampleCount>=6){
      const tiers=[256,320,384];
      const current=tiers.indexOf(this.options.size);
      if(this.averageMs>190&&current>0)this.options.size=tiers[current-1];
      else if(this.averageMs<80&&current<tiers.length-1)this.options.size=tiers[current+1];
      this.sampleCount=0;
    }
    return true;
  }
  predictionSeconds(){return Math.min(.25,this.averageMs*.5/1000);}
  stats(){
    return {accepted:this.accepted,inFlight:!!this.inFlight,
      sdkFps:this.accepted>1?(this.accepted-1)*1000/Math.max(1,this.lastAck-this.firstAck):0,
      averageAckMs:this.averageMs,bytes:this.lastBytes,size:this.options.size,
      quality:this.options.quality,profile:this.profile};
  }
}

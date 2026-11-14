// Calmsight clinical protocol.
// Built on what therapists actually do for specific phobia:
//  - graded exposure along a personal fear hierarchy (Öst one-session treatment, CBT)
//  - inhibitory learning (Craske et al. 2014): test a specific fear prediction,
//    drop safety behaviours, vary the stimulus, name the feeling, check what happened
//  - blood-injection-injury phobia: applied tension first, then graded exposure (Öst; Pitkin & Malouff 2014)
//  - MRI: information before the scan + rehearsal with scanner sounds
//  - spiders: AR exposure at home works (Zimmer 2021; Jurcik 2024 RCT)

export const PHOBIAS = {
  spiders: {
    id:'spiders', icon:'🕷', name:'Spiders', short:'spiders',
    blurb:'3D spiders in your glasses, from still and small to moving and close.',
    expectancies:[
      {id:'jump', text:'It will run or jump at me'},
      {id:'panic', text:'I will panic and lose control'},
      {id:'endless', text:'The fear will keep growing and never stop'},
      {id:'look', text:'I won’t be able to keep looking'}
    ],
    safety:'Keep your eyes on it. No looking away, no squinting.',
    steps:[
      {name:'A small, simple spider', kind:'virtual', plan:{fear:'spiders',realistic:false,motion:0,scale:.45,count:1}, detail:'Cartoon-like · still · small'},
      {name:'A real-looking spider', kind:'virtual', plan:{fear:'spiders',realistic:true,motion:0,scale:.7,count:1}, detail:'Realistic · still'},
      {name:'Its legs move', kind:'virtual', plan:{fear:'spiders',realistic:true,motion:1,scale:.85,count:1}, detail:'Realistic · legs moving'},
      {name:'It walks around', kind:'virtual', plan:{fear:'spiders',realistic:true,motion:2,scale:.85,count:1}, detail:'Walks in your view'},
      {name:'It walks toward you', kind:'virtual', plan:{fear:'spiders',realistic:true,motion:2,behavior:'approach',scale:.9,count:1}, detail:'Comes close, then backs off'},
      {name:'Several spiders', kind:'virtual', plan:{fear:'spiders',realistic:true,motion:2,scale:.9,count:4}, detail:'Three to five spiders at once'},
      {name:'Circling and jumping', kind:'virtual', plan:{fear:'spiders',realistic:true,motion:3,behavior:'orbitJump',scale:.95,count:1}, detail:'Sudden jumps toward you'},
      {name:'A real spider', kind:'real', place:'look at a real spider, in a glass or in a corner', detail:'Real life · coach in your ear'}
    ]
  },
  needles: {
    id:'needles', icon:'💉', name:'Needles & blood', short:'needles',
    blurb:'Injections and blood tests. Starts with the anti-fainting skill, then a 3D syringe step by step.',
    expectancies:[
      {id:'faint', text:'I will faint'},
      {id:'pain', text:'It will hurt more than I can take'},
      {id:'panic', text:'I will panic or have to run'},
      {id:'look', text:'I won’t be able to look at it'}
    ],
    safety:'Keep looking at the needle. If you feel faint, tense your muscles instead of looking away.',
    steps:[
      {name:'Learn applied tension', kind:'skill', detail:'The anti-fainting skill · 5 rounds'},
      {name:'A friendly syringe', kind:'virtual', plan:{fear:'needles',realistic:false,motion:0,scale:.95,count:1,cap:true,view:'side'}, detail:'Cap on · still'},
      {name:'A real syringe', kind:'virtual', plan:{fear:'needles',realistic:true,motion:1,scale:.8,count:1,cap:true,view:'turn'}, detail:'Cap on · turning'},
      {name:'The cap comes off', kind:'virtual', plan:{fear:'needles',realistic:true,motion:1,scale:.85,count:1,cap:false,view:'turn'}, detail:'Needle uncovered'},
      {name:'The needle comes closer', kind:'virtual', plan:{fear:'needles',realistic:true,motion:2,behavior:'approach',scale:.9,count:1,cap:false,view:'front'}, detail:'Tip toward you, then back'},
      {name:'Close-up of the tip', kind:'virtual', plan:{fear:'needles',realistic:true,motion:1,scale:1.35,count:1,cap:false,view:'tip'}, detail:'A drop forms on the tip'},
      {name:'Watch an injection', kind:'virtual', plan:{fear:'needles',realistic:true,motion:3,behavior:'inject',scale:.95,count:1,cap:false,view:'inject'}, detail:'Needle into an arm, repeats'},
      {name:'The real thing', kind:'real', place:'get the real injection or blood test', detail:'Real life · coach in your ear'}
    ]
  },
  spaces: {
    id:'spaces', icon:'🛗', name:'Lifts & small spaces', short:'lifts',
    blurb:'Claustrophobia. A real-life ladder for lifts, with your coach in your ear at every step.',
    expectancies:[
      {id:'stuck', text:'I will get stuck'},
      {id:'air', text:'I will run out of air'},
      {id:'panic', text:'I will panic and can’t get out'},
      {id:'faint', text:'I will faint'}
    ],
    safety:'Don’t hold the door button or keep a hand on the exit. Let the doors do their thing.',
    steps:[
      {name:'Stand in front of the lift', kind:'real', place:'stand in front of a lift and watch the doors open and close', detail:'Watch the doors open and close'},
      {name:'Inside, doors open', kind:'real', place:'step inside a lift and stay there with the doors open', detail:'Stand inside for a minute'},
      {name:'One floor with someone', kind:'real', place:'ride the lift one floor with someone', detail:'Doors close, one floor'},
      {name:'One floor alone', kind:'real', place:'ride the lift one floor on your own', detail:'Doors close, just you'},
      {name:'Several floors alone', kind:'real', place:'ride the lift several floors on your own', detail:'All the way up'},
      {name:'A busy lift', kind:'real', place:'take a busy lift with other people', detail:'Other people, less space'}
    ]
  },
  mri: {
    id:'mri', icon:'🩻', name:'MRI scan', short:'the scan',
    blurb:'Get ready for a scan: know what happens, rehearse the tunnel and the noise, then do it.',
    expectancies:[
      {id:'trapped', text:'I will feel trapped and have to get out'},
      {id:'air', text:'I won’t get enough air'},
      {id:'panic', text:'I will panic in the tube'},
      {id:'still', text:'I won’t be able to lie still'}
    ],
    safety:'Keep your eyes open and notice the space. No counting down the seconds.',
    steps:[
      {name:'What happens in an MRI', kind:'info', detail:'2 minutes · knowing reduces fear'},
      {name:'See the scanner', kind:'virtual', plan:{fear:'mri',view:'outside',sound:0}, detail:'From across the room'},
      {name:'At the opening', kind:'virtual', plan:{fear:'mri',view:'entrance',sound:0}, detail:'Close to the tunnel'},
      {name:'Inside the tunnel', kind:'virtual', plan:{fear:'mri',view:'inside',sound:0}, detail:'Quiet · the ceiling above you'},
      {name:'Inside, with the sounds', kind:'virtual', plan:{fear:'mri',view:'inside',sound:1}, detail:'The real knocking sounds'},
      {name:'A longer scan', kind:'virtual', plan:{fear:'mri',view:'inside',sound:2,minutes:3}, detail:'3 minutes · loud sequences'},
      {name:'The real scan', kind:'real', place:'go in for the real scan', detail:'Real life · coach before and after'}
    ]
  }
};
export const PHOBIA_IDS=Object.keys(PHOBIAS);

// What happens in an MRI, spoken in short chunks (information reduces MRI anxiety).
export const MRI_INFO=[
  'An MRI takes pictures with a magnet. It does not hurt, and there is no radiation.',
  'You lie on a padded table that slides into a tunnel. Both ends of the tunnel are open, and air flows through it.',
  'You get a call button in your hand. Squeeze it and the staff hear you straight away. They can see you the whole time.',
  'It is loud: knocking, buzzing and beeping, in blocks of a few minutes. You get earplugs or headphones. The noise means it is working.',
  'Most scans take 15 to 45 minutes. You can ask for a mirror, a blanket, or to go in feet first for some scans.',
  'You can tell the staff you are nervous before you start. They help people with this every day.'
];

// Applied tension (Öst & Sterner): tense arms, legs and torso 10–15 s until the face
// feels warm, release 20–30 s, five rounds. Raises blood pressure to prevent fainting.
export const TENSION={rounds:5,tense:12,release:20};

// ---------- local voice/text understanding (fast, no network) ----------
const NUM={zero:0,none:0,nothing:0,one:1,two:2,to:null,too:null,three:3,four:4,for:null,five:5,six:6,seven:7,eight:8,ate:8,nine:9,ten:10};
export function phobiaFrom(text){
  const t=(text||'').toLowerCase();
  if(/\bspider|arachn/.test(t))return 'spiders';
  if(/\bmri\b|\bm\.?r\.?i\b|scan|scanner|\btube\b/.test(t))return 'mri';
  if(/needle|inject|vaccin|blood|jab|\bshot\b|syringe|nurse|doctor/.test(t))return 'needles';
  if(/\blift|elevator|small space|closed space|tight space|claustro|confined|cupboard|tunnel/.test(t))return 'spaces';
  return null;
}
export function realNow(text){
  const t=(text||'').toLowerCase();
  return !!phobiaFrom(t)&&/\b(now|about to|i'?m (in|at|getting|having|standing|going|inside|waiting)|i am (in|at|getting|having|inside|waiting)|in front of|on my way)\b/.test(t);
}
export function numberFrom(text,max=10){
  const t=(text||'').toLowerCase().replace(/%/g,' percent');
  const m=t.match(/\b(100|[1-9]?[0-9])\b/);
  if(m){const v=Number(m[1]);return v<=max?v:null;}
  if(max>=100){
    const tens={ten:10,twenty:20,thirty:30,forty:40,fifty:50,sixty:60,seventy:70,eighty:80,ninety:90,hundred:100};
    for(const [w,v] of Object.entries(tens))if(new RegExp('\\b'+w+'\\b').test(t))return v;
    if(/\bhalf\b/.test(t))return 50;
  }
  for(const [w,v] of Object.entries(NUM))if(v!==null&&new RegExp('\\b'+w+'\\b').test(t))return max>=100&&v<=10&&!/out of ten/.test(t)?v*10:v;
  return null;
}
export function yesNo(text){
  const t=(text||'').toLowerCase();
  if(/\b(partly|a bit|a little|kind of|sort of|half)\b/.test(t))return 'partly';
  if(/\b(no|nope|didn'?t|did not|not really|never|nothing happened)\b/.test(t))return 'no';
  if(/\b(yes|yeah|yep|it did|happened|true)\b/.test(t))return 'yes';
  return null;
}
export function command(text){
  const t=(text||'').toLowerCase();
  if(/\b(stop|end|quit|finish|enough|get me out|take it away)\b/.test(t))return 'stop';
  if(/\b(too much|easier|step back|go back|smaller)\b/.test(t))return 'easier';
  if(/\b(harder|next step|step up|next level|bigger|move on)\b/.test(t))return 'harder';
  if(/\b(again|repeat|one more|same)\b/.test(t))return 'again';
  if(/\b(start|begin|let'?s go|ready|go)\b/.test(t))return 'start';
  return null;
}
export function expectancyFrom(text,phobia){
  const t=(text||'').toLowerCase(),e=PHOBIAS[phobia].expectancies;
  const keys={jump:/jump|run|crawl|on me|attack|bite/,panic:/panic|lose control|freak|run away|scream/,endless:/never|forever|keep growing|won'?t stop/,
    look:/look|watch|see it|eyes/,faint:/faint|pass out|black out|dizzy/,pain:/hurt|pain/,stuck:/stuck|trapped|stop between|break down/,
    air:/air|breathe|suffocat/,trapped:/trapped|get out|escape/,still:/still|move|fidget/};
  for(const x of e)if(keys[x.id]?.test(t))return x.id;
  return null;
}

// ---------- the ladder and what comes next ----------
export function newProgress(phobia){return {phobia,step:0,faint:false,ratings:null,trials:[],started:Date.now()};}
// Personal hierarchy: start at the first step the person rates as at least a 3 —
// challenging but manageable (therapists start where fear is real but tolerable).
export function startStep(phobia,ratings,faint){
  const steps=PHOBIAS[phobia].steps;
  if(phobia==='needles'&&faint)return 0;               // fainting history: applied tension first
  if(!ratings)return 0;
  for(let i=0;i<steps.length;i++){if(steps[i].kind==='skill'||steps[i].kind==='info')continue;if((ratings[i]??0)>=3)return i;}
  return Math.max(0,steps.length-1);
}
// After a round. Inhibitory learning: success is "what I feared didn't happen",
// not "my fear went to zero". Move up when the prediction was disproven and fear
// was tolerable; otherwise repeat the same step with a new variation.
export function nextAfter(trial,stepIndex,phobia){
  const steps=PHOBIAS[phobia].steps,last=stepIndex>=steps.length-1;
  if(trial.stoppedEarly&&(trial.fearPeak??10)>=9)return {advice:'easier',step:Math.max(0,stepIndex-1),
    why:'That was a lot. Going one step back is fine; you will come back to this one.'};
  const disproven=trial.happened==='no'||(trial.happened==='partly'&&trial.sureAfter!=null&&trial.sureBefore!=null&&trial.sureAfter<=trial.sureBefore-20);
  if(disproven&&!trial.stoppedEarly&&!last)return {advice:'harder',step:stepIndex+1,
    why:'Your prediction didn’t come true and you stayed with it. Ready for the next step.'};
  if(disproven&&last)return {advice:'again',step:stepIndex,
    why:'You’ve reached the top of your ladder. Repeat it in new places to make it stick.'};
  return {advice:'again',step:stepIndex,
    why:'Same step, but different: a new size, place or angle teaches your brain more than repeating it identically.'};
}
// Variability (Craske strategy 5): every round shows the step in a different way.
export function vary(plan,seed=Math.random()){
  const r=(i)=>{const x=Math.sin((seed+1)*9301+i*49297)*233280;return x-Math.floor(x);};
  if(!plan)return plan;
  if(plan.fear==='mri')return {...plan,tilt:(r(1)-.5)*.2,light:r(2)};
  const v={...plan};
  v.scale=+(plan.scale*(.8+r(1)*.5)).toFixed(3);
  v.ox=+((r(2)-.5)*.35).toFixed(3);
  v.oz=+((r(3)-.5)*.2).toFixed(3);
  v.yaw0=+((r(4)-.5)*1.6).toFixed(3);
  v.speed=+(.75+r(5)*.6).toFixed(2);
  if(plan.fear==='spiders'&&plan.count>1)v.count=3+Math.floor(r(6)*3);
  return v;
}
export function describeVariation(v,base){
  if(!v||!base||v.fear==='mri')return '';
  const k=v.scale/base.scale;
  return (k>1.12?'bigger':k<.92?'smaller':'normal size')+(Math.abs(v.ox)>.1?(v.ox>0?', to the right':', to the left'):', in the middle')+(v.speed>1.1?', faster':v.speed<.85?', slower':'');
}

// Coach lines for an exposure round. Short, spoken, one instruction at a time.
export function script(phobia,step,phase,ctx={}){
  const p=PHOBIAS[phobia],s=p.steps[step];
  const exp=p.expectancies.find(x=>x.id===ctx.expect)?.text?.toLowerCase();
  switch(phase){
    case 'predict':return s.kind==='real'
      ?`Before you ${s.place}: what are you most afraid will happen?`
      :`Step ${step+1}: ${s.name.toLowerCase()}. Before it appears, what are you most afraid will happen?`;
    case 'sure':return `How sure are you that ${exp||'it'} will happen? Say a number from 0 to 100.`;
    case 'fear0':return 'And how scared are you right now, from 0 to 10?';
    case 'expose':return s.kind==='real'
      ?`Okay. Go and ${s.place} now. I’m with you. Tell me your fear number any time, and say done when you’re through.`
      :`Here it comes. ${p.safety}`;
    case 'label':return 'Say out loud what you feel. For example: I feel scared, my heart is racing.';
    case 'check':return 'Fear from 0 to 10, right now?';
    case 'stay':return 'Stay with it. You don’t need the fear to go away. Just notice what actually happens.';
    case 'tension':return 'Tense your legs, stomach and arms now. Hold it until your face feels warm.';
    case 'release':return 'And release. Let your body go back to normal, but keep looking.';
    case 'happened':return `Time. Did it happen: ${exp||'what you feared'}? Yes, no, or partly?`;
    case 'sureAfter':return `So how sure are you now that ${exp||'it'} would happen next time? 0 to 100.`;
    case 'learn':return 'What did you learn? Say it in one sentence.';
    default:return '';
  }
}
export const EXPOSE_SECONDS=90;

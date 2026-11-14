import {writeFileSync,mkdirSync,mkdtempSync,rmSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {PROMPTS} from '../android/app/src/main/assets/web/prompts.mjs';
const output=new URL('../android/app/src/main/assets/web/audio/',import.meta.url);
mkdirSync(output,{recursive:true});
const scratch=mkdtempSync(join(tmpdir(),'stepcloser3d-audio-'));
try{
  for(const [key,text] of Object.entries(PROMPTS)){
    const input=join(scratch,key+'.txt');writeFileSync(input,text);
    execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-f','lavfi','-i',
      'flite=textfile='+input+':voice=slt','-filter:a','atempo=0.90','-ar','22050',
      '-b:a','64k','-y',new URL(key+'.mp3',output).pathname]);
  }
  console.log('Generated '+Object.keys(PROMPTS).length+' bundled guide clips.');
}finally{rmSync(scratch,{recursive:true,force:true});}

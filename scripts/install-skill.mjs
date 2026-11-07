import {cp,mkdir,readFile,writeFile,access} from 'node:fs/promises';
import {homedir} from 'node:os';
import {resolve,join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const target=resolve(process.argv[2]??join(homedir(),'.codex','skills','archi-made-easy'));
let exists=false;try{await access(target);exists=true}catch{}
if(exists)throw new Error(`Installation already exists: ${target}; choose a new destination to preserve it.`);
await mkdir(target,{recursive:true});await cp(join(root,'skills','archi-made-easy'),target,{recursive:true});
const runtime=join(target,'runtime');await mkdir(runtime,{recursive:true});
for(const name of ['dist','schemas','catalogs','examples','package.json','LICENSE','NOTICE'])await cp(join(root,name),join(runtime,name),{recursive:true});
for(const name of ['npm-shrinkwrap.json','package-lock.json']){try{await access(join(root,name));await cp(join(root,name),join(runtime,name));break}catch{}}
let skill=await readFile(join(target,'SKILL.md'),'utf8');skill=skill.replace('Resolve the package root two directories above this file.','Resolve the package root as the `runtime/` directory beside this file.');await writeFile(join(target,'SKILL.md'),skill);
const npm=process.platform==='win32'?'npm.cmd':'npm';const result=spawnSync(npm,['ci','--omit=dev','--ignore-scripts'],{cwd:runtime,stdio:'inherit',shell:process.platform==='win32'});if(result.status!==0)throw new Error('Runtime dependency installation failed; partial installation retained for diagnosis.');
console.log(JSON.stringify({installed:target,runtime,launch:'Restart the agent session to discover the skill.'},null,2));

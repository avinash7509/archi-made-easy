#!/usr/bin/env node
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {structural} from './validation.js';
import {assess} from './assessment.js';
import {simulate,availability,latency} from './simulation.js';
import {deliver,writeJSON} from './export.js';
import {fromDrawio} from './drawio.js';
import {diff,type CASG} from './model.js';
import {discover} from './discovery.js';
const args=process.argv.slice(2);const command=args[0],file=args[1];
const flag=(key:string,defaultValue?:string)=>{const i=args.indexOf('--'+key);return i<0?defaultValue:args[i+1];};
const read=async(path:string)=>JSON.parse(await readFile(path,'utf8'));
const print=(value:unknown)=>process.stdout.write(JSON.stringify(value,null,2)+'\n');
async function main(){
 if(command==='assets'){const {acquireIcons}=await import('./assets.js');print(await acquireIcons(file));return;}
 if(command==='review'){const {hash}=await import('./model.js');const path=resolve(file);const receipt=await read(join(path,'receipt.json'));const status=flag('status');if(!['passed','failed'].includes(status??'')||!flag('reviewer')||!flag('note'))throw new Error('review requires --status passed|failed --reviewer identity --note observations');const artifactHashes:Record<string,string>={};for(const f of receipt.files)artifactHashes[f]=hash((await readFile(f)).toString('base64'));await writeJSON(join(path,'visual-review.json'),{status,reviewer:flag('reviewer'),note:flag('note'),reviewedAt:new Date().toISOString(),artifactHashes});receipt.exports.visualReview=status;await writeJSON(join(path,'receipt.json'),receipt);print({status,reviewer:flag('reviewer'),artifacts:Object.keys(artifactHashes).length});return;}
 if(!command||['--help','help'].includes(command)){print({name:'Archi-Made-Easy',version:'0.1.0',commands:{validate:'validate model.json [--repo-root path]',simulate:'simulate model.json --type node|az|region|timeout|traffic|availability|latency [--target id] [--rps 100] [--path a,b]',render:'render model.json --out directory [--no-raster] [--repo-root path]',export:'export model.json --out directory',inspect:'inspect model.json [--id component]',import:'import diagram.drawio --out directory [--current model.json] [--page id]',diff:'diff baseline.json candidate.json',discover:'discover repository --out directory',benchmark:'benchmark manifest.json --out directory'}});return;}
 if(command==='discover'){const result=await discover(resolve(file));const out=resolve(flag('out','artifacts/discovery')!);await mkdir(out,{recursive:true});await writeJSON(join(out,'architecture.casg.json'),result.model);await writeJSON(join(out,'discovery-report.json'),result);print({out,components:result.model.components.length,unsupported:result.unsupported});return;}
 if(command==='import'){const source=await readFile(file,'utf8');const result=fromDrawio(source,flag('current')?await read(flag('current')!):undefined,flag('page'));const out=resolve(flag('out','artifacts/import')!);await mkdir(out,{recursive:true});await writeFile(join(out,'original.drawio'),source);await writeJSON(join(out,'candidate.casg.json'),result.candidate);await writeJSON(join(out,'import-report.json'),{...result,validation:structural(result.candidate),assessment:structural(result.candidate).passed?assess(result.candidate):null});print({out,conflicts:result.conflicts,unsupported:result.unsupported});return;}
 if(command==='benchmark'){const {runBenchmark}=await import('./benchmark.js');print(await runBenchmark(file,flag('out','artifacts/benchmark')!));return;}
 const model=await read(file) as CASG;const check=structural(model,flag('repo-root'));if(!check.passed){print({structural:check});process.exitCode=2;return;}
 switch(command){
 case 'validate':{const report=assess(model);print({structural:check,assessment:report});process.exitCode=report.critical?1:0;break;}
 case 'render':case 'export':print(await deliver(model,resolve(flag('out','artifacts/output')!),{repoRoot:flag('repo-root'),raster:!args.includes('--no-raster')}));break;
 case 'inspect':{const id=flag('id');print(id?{component:model.components.find(n=>n.id===id),relationships:model.relationships.filter(e=>e.from===id||e.to===id),findings:assess(model).findings.filter(f=>f.componentId===id),evidence:model.evidence.filter(e=>model.components.find(n=>n.id===id)?.evidence?.includes(e.id))}:{model,assessment:assess(model)});break;}
 case 'simulate':{const type=flag('type','node')!;print(type==='availability'?availability(model):type==='latency'?latency(model,flag('path','')!.split(','),Number(flag('seed','42'))):simulate(model,{type:type as any,target:flag('target'),rps:Number(flag('rps','100'))}));break;}
 case 'diff':print(diff(model,await read(args[2])));break;
 default:throw new Error(`Unknown command ${command}; use --help`);
 }
}
main().catch(e=>{print({error:e instanceof Error?e.message:String(e),generated:false});process.exitCode=2;});

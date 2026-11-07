import {readFile,mkdir} from 'node:fs/promises';
import {dirname,resolve,join} from 'node:path';
import {assess} from './assessment.js';
import {structural} from './validation.js';
import {layout} from './layout.js';
import {writeJSON} from './export.js';
export async function runBenchmark(manifestPath:string,out:string){
 const manifest=JSON.parse(await readFile(manifestPath,'utf8'));const results=[];
 for(const c of manifest.cases){const m=JSON.parse(await readFile(resolve(dirname(manifestPath),c.file),'utf8'));const valid=structural(m);const report=valid.passed?assess(m):null;const found=new Set(report?.findings.filter(f=>f.status==='fail').map(f=>f.ruleId));const missed=(c.expectedFailures??[]).filter((r:string)=>!found.has(r));const falsePositives=(c.expectedPasses??[]).filter((r:string)=>found.has(r));let geometry:string[]=[];
 if(valid.passed){const scene=await layout(m,{id:'test',label:c.id,type:'deployment'});geometry=scene.diagnostics;}
 results.push({id:c.id,passed:valid.passed&&!missed.length&&!falsePositives.length&&!geometry.length,missed,falsePositives,structural:valid,geometry});}
 const result={kind:'deterministic-fixture-evaluation',cases:results,passRate:results.filter(r=>r.passed).length/results.length,agentBenchmark:{status:'not-run',required:'30 cases × 3 repetitions × 3 model configurations; isolated prompts and retained transcripts'},blindComparison:{status:'not-run',baselines:['diagram-design','archify']},superiorityClaim:false};await mkdir(out,{recursive:true});await writeJSON(join(out,'results.json'),result);return result;
}

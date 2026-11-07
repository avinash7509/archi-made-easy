import {Ajv2020} from 'ajv/dist/2020.js';
import {readFileSync,existsSync} from 'node:fs';
import {resolve,relative,isAbsolute} from 'node:path';
import type {CASG} from './model.js';
const schema=JSON.parse(readFileSync(new URL('../schemas/casg.schema.json',import.meta.url),'utf8'));
const validate=new Ajv2020({allErrors:true,strict:false}).compile(schema);
export function structural(input:unknown,repoRoot?:string) {
 const errors:string[]=[]; const warnings:string[]=[];
 if(!validate(input)) return {passed:false,errors:validate.errors?.map(e=>`${e.instancePath}: ${e.message}`)??[],warnings};
 const m=input as CASG; const ids=new Set<string>();
 for(const n of [...m.components,...m.relationships,...m.evidence,...m.views??[],...m.capabilities??[]]) {if(ids.has(n.id))errors.push(`Duplicate ID: ${n.id}`);ids.add(n.id);}
 const components=new Map(m.components.map(n=>[n.id,n])); const evidence=new Set(m.evidence.map(e=>e.id));
 for(const n of m.components) {
  if(n.parent&&!components.has(n.parent))errors.push(`Unknown parent ${n.parent} for ${n.id}`);
  const visited=new Set([n.id]);let p=n.parent;
  while(p&&components.has(p)){if(visited.has(p)){errors.push(`Containment cycle at ${n.id}`);break;}visited.add(p);p=components.get(p)?.parent;}
 }
 for(const e of m.relationships){if(!components.has(e.from)||!components.has(e.to))errors.push(`Dangling relationship ${e.id}`);if(e.dependency==='quorum'&&(!e.group||!e.quorum))errors.push(`Quorum requires group and threshold: ${e.id}`);}
 for(const n of [...m.components,...m.relationships])for(const e of n.evidence??[])if(!evidence.has(e))errors.push(`Unknown evidence ${e} on ${n.id}`);
 for(const v of m.views??[])for(const id of v.nodes??[])if(!components.has(id))errors.push(`Unknown view node ${id}`);
 for(const c of m.capabilities??[])for(const id of c.entrypoints)if(!components.has(id))errors.push(`Unknown capability entrypoint ${id}`);
 for(const e of m.evidence)if(e.source.startsWith('repo:')){
  if(!repoRoot){warnings.push(`Repository evidence not verified: ${e.id}`);continue;}
  const file=e.source.slice(5).replace(/:\d+(?::\d+)?$/,'');const path=resolve(repoRoot,file);const rel=relative(resolve(repoRoot),path);
  if(rel.startsWith('..')||isAbsolute(rel)||!existsSync(path))errors.push(`Unverifiable repository evidence ${e.id}: ${file}`);
 }
 if(m.mode==='as-is')for(const n of m.components)if(!n.evidence?.some(id=>m.evidence.some(e=>e.id===id&&e.kind==='observed')))warnings.push(`As-is component lacks observed evidence: ${n.id}`);
 return {passed:errors.length===0,errors,warnings};
}

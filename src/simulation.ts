import type {CASG} from './model.js';
export interface Scenario {type:'node'|'az'|'region'|'timeout'|'traffic';target?:string;rps?:number;durationSeconds?:number;}
export function failure(m:CASG,initial:string[]){
 const failed=new Set(initial);const causes:Record<string,string[]>={};
 // Monotone fixed point handles cyclic dependencies without recursion.
 for(let step=0;step<=m.components.length;step++){
  let changed=false;
  for(const n of m.components){if(failed.has(n.id))continue;
   if(n.parent&&failed.has(n.parent)){failed.add(n.id);causes[n.id]=[n.parent];changed=true;continue;}
   const deps=m.relationships.filter(e=>e.from===n.id&&['sync','async'].includes(e.kind)&&e.dependency!=='optional');
   const required=deps.filter(e=>!e.dependency||e.dependency==='required');
   const broken=required.filter(e=>failed.has(e.to)&&!(e.kind==='async'&&n.controls?.buffered===true));
   const groups=new Map<string,typeof deps>();for(const e of deps.filter(e=>e.dependency==='fallback'||e.dependency==='quorum')){const k=e.group??'fallback';groups.set(k,[...groups.get(k)??[],e]);}
   for(const group of groups.values()){const threshold=group[0].dependency==='quorum'?(group[0].quorum??1):1;if(group.filter(e=>!failed.has(e.to)).length<threshold)broken.push(...group);}
   if(broken.length){failed.add(n.id);causes[n.id]=broken.map(e=>e.to);changed=true;}
  }if(!changed)break;
 }
 const degraded=m.components.filter(n=>!failed.has(n.id)&&m.relationships.some(e=>e.from===n.id&&failed.has(e.to))).map(n=>n.id);
 return {failed:[...failed].sort(),degraded,causes,capabilities:(m.capabilities??[]).map(c=>({id:c.id,label:c.label,status:c.entrypoints.every(id=>failed.has(id))?'unavailable':c.entrypoints.some(id=>failed.has(id)||degraded.includes(id))?'degraded':'available'})),survivingPaths:m.relationships.filter(e=>!failed.has(e.from)&&!failed.has(e.to)).map(e=>e.id)};
}
export function simulate(m:CASG,s:Scenario){
 const initial=m.components.filter(n=>s.type==='az'?n.az===s.target:s.type==='region'?n.region===s.target:n.id===s.target).map(n=>n.id);
 if(s.type==='traffic'){
  const rps=s.rps??100;const duration=s.durationSeconds??60;
  const queues=m.components.filter(n=>n.kind==='queue'||n.kind==='broker').map(n=>{
   const missing=['capacityRps','buffer','retryFactor','scaleDelaySeconds'].filter(k=>n[k as keyof typeof n]===undefined);
   if(missing.length)return {id:n.id,status:'unknown',missing};
   const excess=Math.max(0,rps*n.retryFactor!-n.capacityRps!);return {id:n.id,status:'estimated-scenario',backlog:Math.min(n.buffer!,excess*duration),overflowAfterSeconds:excess?n.buffer!/excess:null,autoscaleDelaySeconds:n.scaleDelaySeconds,assumptions:['Arrival rate applied to each queue; no traffic split data supplied.','Constant pre-scaling service rate over the scenario duration.']};
  });
  return {scenario:s,confidence:'estimated-scenario',queues,overloaded:m.components.filter(n=>n.capacityRps!==undefined&&n.capacityRps<rps).map(n=>n.id),missing:m.components.filter(n=>!n.capacityRps).map(n=>`${n.id}.capacityRps`),assumptions:['No live load test was executed.','Capacity and routing are modeled, not measured by this command.']};
 }
 return {scenario:s,confidence:'structural-analysis',...failure(m,initial),missing:initial.length?[]:[`No component matched ${s.target}`],assumptions:['Required synchronous failure propagates; optional dependency failure degrades.','Buffered async callers degrade rather than immediately fail; exhaustion needs a traffic model.','Failover capacity and recovery timing require separate evidence.']};
}
export function availability(m:CASG){
 const nodes=m.components.filter(n=>!['actor','boundary','capability'].includes(n.kind));
 if(!nodes.length)return {status:'unknown',missing:['At least one service component is required'],reason:'Empty system has no availability estimate.'};
 const missing=nodes.filter(n=>n.availability===undefined).map(n=>`${n.id}.availability`);
 const grouped=nodes.filter(n=>n.failureDomain);const inconsistent=grouped.some(n=>nodes.some(o=>o.failureDomain===n.failureDomain&&o.availability!==n.availability));
 if(missing.length||inconsistent)return {status:'unknown',missing,reason:inconsistent?'Components in a perfectly correlated failure domain must have equal availability.': 'Availability inputs are incomplete.'};
 const domains=new Map<string,{p:number;ids:string[]}>();for(const n of nodes){const key=n.failureDomain??n.id;const d=domains.get(key)??{p:n.availability!,ids:[]};d.ids.push(n.id);domains.set(key,d);}
 if(domains.size>18)return {status:'unknown',missing:[],reason:'Exact enumeration is limited to 18 independent failure domains; use a scoped capability view.'};
 const values=[...domains.values()];const entries=m.capabilities?.length?m.capabilities:[{id:'system',label:'System',entrypoints:[nodes[0]?.id].filter(Boolean)}];
 const totals=Object.fromEntries(entries.map(c=>[c.id,0]));
 for(let mask=0;mask<2**values.length;mask++){
  let p=1;const down:string[]=[];for(let i=0;i<values.length;i++){const failed=(mask&(1<<i))!==0;p*=failed?1-values[i].p:values[i].p;if(failed)down.push(...values[i].ids);}
  if(p===0)continue;const state=failure(m,down);for(const c of entries)if(c.entrypoints.some(id=>!state.failed.includes(id)))totals[c.id]+=p;
 }
 return {status:'evidence-backed-calculation',label:'Modeled availability, not contractual SLA',capabilities:totals,target:m.constraints?.targetAvailability??null,violations:Object.entries(totals).filter(([,p])=>m.constraints?.targetAvailability!==undefined&&p<m.constraints.targetAvailability).map(([id])=>id),assumptions:['Distinct failure domains are statistically independent.','Components in an explicit shared domain fail together.','Instant failover; recovery delays and insufficient surviving capacity are not included.'],method:'Exact state enumeration; shared components counted once.'};
}
export function latency(m:CASG,path:string[],seed=42,samples=10000){
 let state=seed>>>0;const random=()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return state/4294967296;};
 const missing=path.filter(id=>!m.components.find(n=>n.id===id)?.latencyMs?.length);if(missing.length)return {status:'unknown',missing};
 for(let i=1;i<path.length;i++)if(!m.relationships.some(e=>e.from===path[i-1]&&e.to===path[i]&&e.kind==='sync'))return {status:'unknown',missing:[],reason:'Path is not a contiguous synchronous chain'};
 const draws=Array.from({length:samples},()=>path.reduce((sum,id)=>{const d=m.components.find(n=>n.id===id)!.latencyMs!;return sum+d[Math.floor(random()*d.length)];},0)).sort((a,b)=>a-b);
 return {status:'estimated-scenario',p50:draws[Math.floor(samples*.5)],p99:draws[Math.floor(samples*.99)],seed,samples,assumptions:['Independent empirical resampling of supplied component latency arrays.','No queueing, network latency or correlation added unless included in inputs.']};
}
export function defaultSimulations(m:CASG){return {availability:availability(m),traffic:[100,1000,5000].map(rps=>simulate(m,{type:'traffic',rps})),failures:m.components.filter(n=>n.kind!=='actor').map(n=>simulate(m,{type:'node',target:n.id}))};}

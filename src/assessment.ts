import {pillars,profile,type CASG,type Component,type Finding,type Pillar,type Status} from './model.js';
interface Rule {id:string;pillar:Pillar;severity:Finding['severity'];control:string;message:string;applies:(n:Component,m:CASG)=>boolean;source:string;}
const framework='https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html';
const workload=(n:Component)=>!['boundary','actor','capability','identity'].includes(n.kind);
const compute=(n:Component)=>['compute','service','api','container','function','agent'].includes(n.kind);
const rule=(id:string,pillar:Pillar,severity:Finding['severity'],control:string,message:string,applies:Rule['applies'],source=framework):Rule=>({id,pillar,severity,control,message,applies,source});
export const rules:Rule[]=[
 rule('SEC-EDGE','security','critical','edgeWaf','Public HTTP ingress requires applicable edge inspection',n=>n.public===true&&['api','gateway','loadbalancer','cdn','service'].includes(n.kind)),
 rule('SEC-ORIGIN','security','critical','originRestricted','Edge-protected origins must prevent direct bypass',n=>n.controls?.edgeWaf===true),
 rule('SEC-DDOS','security','high','ddos','Public ingress needs a DDoS protection strategy',n=>n.public===true),
 rule('SEC-AUTH','security','high','authentication','Non-anonymous interfaces need authentication',n=>n.public===true&&n.controls?.anonymousAllowed!==true),
 rule('SEC-IDENTITY','security','high','workloadIdentity','Use scoped workload identity rather than static compute credentials',compute),
 rule('SEC-TLS','security','high','tls','Protect application communication in transit',workload),
 rule('SEC-DATA','security','critical','privateAccess','Stateful stores must have controlled network exposure',n=>n.stateful===true),
 rule('SEC-ENCRYPT','security','high','encryptionAtRest','Protect stored data at rest',n=>n.stateful===true),
 rule('SEC-CMEK','security','high','customerManagedKeys','Customer-managed keys required by declared policy',n=>n.controls?.requiresCmek===true),
 rule('REL-REDUNDANCY','reliability','critical','redundancy','Tier-1 production paths need tested redundancy', (n,m)=>workload(n)&&n.tier===1&&profile(m)!=='mvp'),
 rule('REL-RECOVERY','reliability','high','recoveryTested','Stateful production services need recovery verification',(n,m)=>n.stateful===true&&profile(m)!=='mvp'),
 rule('REL-POISON','reliability','high','poisonHandling','Async consumers need poison-message recovery',n=>n.kind==='queue'||n.kind==='broker'),
 rule('REL-RETRY','reliability','medium','boundedRetries','Remote callers need bounded retries with jitter', (n,m)=>m.relationships.some(e=>e.from===n.id&&e.kind==='sync')),
 rule('REL-IDEMPOTENCY','reliability','high','idempotency','Retried mutations need idempotency',n=>n.controls?.mutatingRetries===true),
 rule('REL-CONSISTENCY','reliability','high','consistencyStrategy','Distributed writes need an explicit consistency strategy',n=>n.controls?.distributedWrites===true),
 rule('PERF-POOL','performance','medium','connectionPooling','Database clients need a pooling strategy',(n,m)=>m.relationships.some(e=>e.from===n.id&&m.components.some(t=>t.id===e.to&&t.stateful))),
 rule('PERF-SCALE','performance','medium','autoscaleBounds','Autoscaled workloads need bounded scaling',n=>n.controls?.autoscaling===true),
 rule('PERF-PARTITION','performance','medium','partitionStrategy','Partitioned stores need a workload-aligned key',n=>n.controls?.partitioned===true),
 rule('OPS-OBS','operations','high','observability','Workloads need linked traces, logs, metrics and alerts',workload),
 rule('OPS-IAC','operations','medium','iac','Production resources need reproducible configuration',(n,m)=>workload(n)&&profile(m)!=='mvp'),
 rule('OPS-ROLLOUT','operations','medium','safeDeployment','Production workloads need rollback-safe delivery',(n,m)=>compute(n)&&profile(m)!=='mvp'),
 rule('COST-LIFECYCLE','cost','medium','lifecycle','Persistent storage needs retention and lifecycle policy',n=>n.stateful===true),
 rule('COST-NAT','cost','medium','endpointEvaluated','NAT paths to cloud services need endpoint cost evaluation',n=>n.kind==='nat'),
 rule('SUS-IDLE','sustainability','medium','idleScaling','Bursty workloads should reduce idle capacity',n=>n.controls?.bursty===true),
 rule('SUS-RETENTION','sustainability','medium','retentionJustified','Storage retention needs a business justification',n=>n.stateful===true),
 rule('AI-GUARD','security','high','aiGuardrails','AI ingress and output need contextual guardrails',n=>['llm','agent','model'].includes(n.kind)),
 rule('AI-TOOLS','security','critical','toolBoundaries','Agents need explicit tool permissions and execution boundaries',n=>n.kind==='agent'),
 rule('AI-RAG','security','high','retrievalAuthorization','RAG retrieval must enforce document authorization',n=>n.kind==='vector')
];
export function assess(m:CASG){
 const findings:Finding[]=[];
 for(const n of m.components)for(const r of rules){const val=n.controls?.[r.control];const status:Status=!r.applies(n,m)?'not-applicable':val===undefined?'unknown':val===true?'pass':'fail';findings.push({ruleId:r.id,version:'1.0.0',componentId:n.id,pillar:r.pillar,severity:r.severity,status,message:r.message,source:r.source,remediation:status==='fail'||status==='unknown'?{control:r.control,value:true}:undefined});}
 const extra=(ruleId:string,n:string,pillar:Pillar,severity:Finding['severity'],message:string,status:Status='fail')=>findings.push({ruleId,componentId:n,pillar,severity,status,message,version:'1.0.0',source:framework});
 for(const n of m.components){
  if(n.public===true&&n.stateful)extra('SEC-PUBLIC-STORE',n.id,'security','critical','Stateful store is publicly exposed');
  if(m.constraints?.allowedRegions?.length&&n.region&&!m.constraints.allowedRegions.includes(n.region))extra('SEC-RESIDENCY',n.id,'security','critical',`Region ${n.region} violates allowed regions`);
  if(n.controls?.edgeWaf===true&&!n.controls?.edgeWafProduct)extra('SEC-EDGE-COMPAT',n.id,'security','high','WAF product/attachment compatibility lacks evidence','unknown');
  if(n.controls?.edgeWafProduct){const products:Record<string,string[]>={'aws-wafv2':['cloudfront','alb','api-gateway-rest'],'azure-waf-v2':['application-gateway'],'azure-front-door-waf':['front-door'],'gcp-cloud-armor':['global-external-application-load-balancer']};const product=String(n.controls.edgeWafProduct);const supported=products[product];if(!supported||!n.service)extra('SEC-EDGE-COMPAT',n.id,'security','high','Unknown WAF product or service association; verify provider support','unknown');else if(!supported.includes(n.service))extra('SEC-EDGE-COMPAT',n.id,'security','critical',`${product} is not supported by this catalog for ${n.service}`);}
  if(n.controls?.originRestricted===true&&n.provider==='aws'&&n.controls?.restrictionMethod==='prefix-list-only')extra('SEC-ORIGIN-DISTRIBUTION',n.id,'security','critical','CloudFront prefix list alone does not restrict access to your distribution');
 }
 for(const e of m.relationships){const a=m.components.find(n=>n.id===e.from)!;const b=m.components.find(n=>n.id===e.to)!;if(!a||!b)continue;
  if(e.dependency!=='optional'&&e.kind==='sync')for(const key of ['rtoSeconds','rpoSeconds'] as const)if(a[key]!==undefined&&b[key]!==undefined&&a[key]!<b[key]!)extra(`REL-${key}`,a.id,'reliability','high',`${key} ${a[key]}s is tighter than required dependency ${b.id}: ${b[key]}s`);
  if(e.kind==='sync'&&a.az&&b.az&&a.az!==b.az)extra('COST-CROSS-AZ',e.id,'cost','medium','Cross-AZ synchronous traffic: quantify volume, resilience benefit and transfer costs','unknown');
 }
 // Long paths are advisory risks, not universal architecture failures.
 for(const n of m.components){const visit=(id:string,seen:Set<string>):number=>{if(seen.has(id))return 0;const next=new Set([...seen,id]);return Math.max(0,...m.relationships.filter(e=>e.from===id&&e.kind==='sync').map(e=>1+visit(e.to,next)));};if(visit(n.id,new Set())>3)extra('PERF-CHAIN',n.id,'performance','medium','More than three synchronous hops: measure latency budget before decoupling','unknown');}
 const scores=Object.fromEntries(pillars.map(p=>{const applicable=findings.filter(f=>f.pillar===p&&f.status!=='not-applicable');const known=applicable.filter(f=>f.status!=='unknown');return [p,{score:known.length?Math.round(100*known.filter(f=>f.status==='pass').length/known.length):null,coverage:applicable.length?known.length/applicable.length:1,applicable:applicable.length,unknown:applicable.length-known.length}];}));
 return {profile:profile(m),findings,scores,critical:findings.filter(f=>f.status==='fail'&&f.severity==='critical').length,readiness:findings.some(f=>f.status==='fail'&&f.severity==='critical')?'critical-risks':findings.some(f=>f.status==='unknown')?'incomplete-evidence':'checks-passed',certification:false};
}
export function remediate(m:CASG){
 const candidate=structuredClone(m);candidate.mode='target';candidate.id=m.id+'-target';candidate.title=m.title+' — Proposed target';
 const changes:{componentId:string;ruleId:string;proposal:string}[]=[];
 if(m.constraints?.allowProposals===false)return {candidate,changes,report:assess(candidate)};
 for(let cycle=0;cycle<3;cycle++){
  let changed=false;for(const f of assess(candidate).findings){if(!['fail','unknown'].includes(f.status)||!f.remediation)continue;
   if(m.constraints?.forbiddenControls?.includes(f.remediation.control))continue;
   const n=candidate.components.find(n=>n.id===f.componentId);if(!n)continue;
   // Evidence of testing and structural redundancy cannot be manufactured by changing a boolean.
   if(['recoveryTested','redundancy'].includes(f.remediation.control))continue;
   const eid=`proposal-${n.id}-${f.ruleId}`;n.controls??={};n.controls[f.remediation.control]=f.remediation.value;
   n.evidence=[...n.evidence??[],eid];candidate.evidence.push({id:eid,kind:'proposed',source:`rule:${f.ruleId}`,conditions:'Design requirement only; not a deployed or empirically verified control.'});
   changes.push({componentId:n.id,ruleId:f.ruleId,proposal:f.message});changed=true;
   if(f.ruleId==='SEC-EDGE'){
    const match:Record<string,string>={'aws:cloudfront':'aws-wafv2','aws:alb':'aws-wafv2','aws:api-gateway-rest':'aws-wafv2','azure:application-gateway':'azure-waf-v2','azure:front-door':'azure-front-door-waf','gcp:global-external-application-load-balancer':'gcp-cloud-armor'};
    const product=match[`${n.provider}:${n.service}`];if(product){n.controls.edgeWafProduct=product;const id=`${n.id}-waf-policy`;if(!candidate.components.some(c=>c.id===id)){candidate.components.push({id,label:product==='azure-waf-v2'?'Application Gateway WAF policy':product==='aws-wafv2'?'AWS WAFv2 policy':product==='gcp-cloud-armor'?'Cloud Armor policy':'Front Door WAF policy',kind:'security',provider:n.provider,service:'waf',parent:n.parent,evidence:[eid],controls:{managedRules:true,preventionMode:true}});candidate.relationships.push({id:`${id}-attachment`,from:id,to:n.id,kind:'control',label:'Inspect ingress',dependency:'optional',evidence:[eid]});}}
   }
   if(f.ruleId==='REL-POISON'&&!candidate.components.some(c=>c.id===`${n.id}-dlq`)){
    candidate.components.push({id:`${n.id}-dlq`,label:`${n.label} — recovery queue`,kind:'recovery-queue',provider:n.provider,parent:n.parent,evidence:[eid],controls:{retentionJustified:true}});candidate.relationships.push({id:`${n.id}-poison-route`,from:n.id,to:`${n.id}-dlq`,kind:'async',dependency:'optional',label:'Poison messages',evidence:[eid]});
   }
  }
  for(const n of candidate.components)if(n.stateful&&n.public===true&&!m.constraints?.forbiddenControls?.includes('privateAccess')){n.public=false;changes.push({componentId:n.id,ruleId:'SEC-PUBLIC-STORE',proposal:'Restrict public exposure; plan private client connectivity before migration.'});changed=true;}
  if(!changed)break;
 }
 candidate.assumptions=[...candidate.assumptions??[],'Target controls are proposed requirements, not evidence of deployment. Compatibility, cost and migration feasibility still need verification.'];
 return {candidate,changes,report:assess(candidate)};
}

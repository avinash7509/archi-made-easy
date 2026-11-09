import {createHash} from 'node:crypto';
export type Status = 'pass'|'fail'|'unknown'|'not-applicable';
export type Pillar = 'reliability'|'security'|'cost'|'performance'|'operations'|'sustainability';
export const pillars: Pillar[] = ['reliability','security','cost','performance','operations','sustainability'];
export interface Evidence {id:string; kind:'observed'|'user-specified'|'vendor-published'|'inferred'|'proposed'; source:string; revision?:string; retrievedAt?:string; conditions?:string;}
export interface Component {
 id:string; label:string; kind:string; role?:string; provider?:string; service?:string; parent?:string; region?:string; az?:string;
 public?:boolean; tier?:number; stateful?:boolean; controls?:Record<string,boolean|number|string>; evidence?:string[];
 availability?:number; failureDomain?:string; capacityRps?:number; buffer?:number; retryFactor?:number; scaleDelaySeconds?:number;
 rtoSeconds?:number; rpoSeconds?:number; latencyMs?:number[]; attributes?:{name:string;type:string;key?:string}[];
 position?:{x:number;y:number}; size?:{width:number;height:number};
}
export interface Relationship {protocol?:string;port?:number;auth?:string;plane?:'request'|'data'|'async'|'security'|'operations';controls?:Record<string,boolean|number|string>;id:string;from:string;to:string;label?:string;kind:'sync'|'async'|'replication'|'control'|'telemetry'; dependency?:'required'|'optional'|'fallback'|'quorum';group?:string;quorum?:number;evidence?:string[];waypoints?:{x:number;y:number}[];}
export interface View {id:string;label:string;type:'context'|'container'|'component'|'deployment'|'network'|'sequence'|'dataflow'|'capability'|'erd'|'class'|'state'|'activity';nodes?:string[];}
export interface CASG {schemaVersion:1;id:string;title:string;mode:'as-is'|'target';profile?:'mvp'|'standard-production'|'enterprise-critical';description?:string;components:Component[];relationships:Relationship[];evidence:Evidence[];views?:View[];capabilities?:{id:string;label:string;entrypoints:string[]}[];constraints?:{allowedRegions?:string[];allowProposals?:boolean;forbiddenControls?:string[];targetAvailability?:number};assumptions?:string[];}
export interface Finding {ruleId:string;version:string;componentId:string;pillar:Pillar;severity:'critical'|'high'|'medium';status:Status;message:string;source:string;remediation?:{control:string;value:boolean|number|string};}
export const hash = (v:unknown) => createHash('sha256').update(JSON.stringify(v)).digest('hex');
export function profile(m:CASG): NonNullable<CASG['profile']> {return m.profile ?? (/mission.critical|tier.?1|enterprise|bank|regulated/i.test(m.description??'')?'enterprise-critical':/prototype|mvp|demo/i.test(m.description??'')?'mvp':'standard-production');}
export function diff(a:CASG,b:CASG) {
 const compare=(x:{id:string}[],y:{id:string}[])=>({added:y.filter(n=>!x.some(v=>v.id===n.id)),removed:x.filter(n=>!y.some(v=>v.id===n.id)),changed:y.filter(n=>x.some(v=>v.id===n.id&&hash(v)!==hash(n))).map(n=>({before:x.find(v=>v.id===n.id),after:n}))});
 return {baselineHash:hash(a),candidateHash:hash(b),components:compare(a.components,b.components),relationships:compare(a.relationships,b.relationships)};
}

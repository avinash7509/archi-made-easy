import {XMLParser} from 'fast-xml-parser';
import {inflateRawSync} from 'node:zlib';
import {hash,diff,type CASG,type Component,type Relationship} from './model.js';
import type {Scene} from './layout.js';
import {icon} from './assets.js';
export const xml=(s:unknown)=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&apos;');
const list=(x:any):any[]=>x===undefined?[]:Array.isArray(x)?x:[x];
export function toDrawio(m:CASG,scenes:Scene[]){
 const pages=scenes.map(s=>{
  const cells=s.boxes.map(b=>{const parent=s.boxes.find(p=>p.id===b.parent);const image=icon(m.components.find(n=>n.id===b.id)!);return `<mxCell id="${xml(b.id)}" value="${xml(b.label)}" vertex="1" parent="${xml(parent?.id??'1')}" style="${b.boundary?'swimlane;startSize=42;fillColor=#f1f5f9;':'rounded=1;fillColor=#ffffff;'}${image?`shape=label;image=${'data:image/svg+xml,'+encodeURIComponent(Buffer.from(image.split(',')[1],'base64').toString())};imageWidth=40;imageHeight=40;spacingLeft=48;`:""}strokeColor=#94a3b8;fontSize=16;whiteSpace=wrap;html=0;" ameKind="${xml(b.kind)}"><mxGeometry x="${b.x-(parent?.x??0)}" y="${b.y-(parent?.y??0)}" width="${b.width}" height="${b.height}" as="geometry"/></mxCell>`;});
  cells.push(...s.routes.map(r=>`<mxCell id="${xml(r.id)}" value="${xml(r.label)}" edge="1" parent="1" source="${xml(r.from)}" target="${xml(r.to)}" ameKind="${xml(r.kind)}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;fontSize=16;${r.kind==='async'?'dashed=1;':''}"><mxGeometry relative="1" as="geometry"><Array as="points">${r.points.slice(1,-1).map(p=>`<mxPoint x="${p.x}" y="${p.y}"/>`).join('')}</Array></mxGeometry></mxCell>`));
  return `<diagram id="${xml(s.id)}" name="${xml(s.title)}"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>${cells.join('')}</root></mxGraphModel></diagram>`;
 });
 return `<?xml version="1.0" encoding="UTF-8"?><mxfile host="Archi-Made-Easy" ameBaseline="${Buffer.from(JSON.stringify(m)).toString('base64')}" ameHash="${hash(m)}">${pages.join('')}</mxfile>`;
}
export function fromDrawio(source:string,current?:CASG,pageId?:string){
 if(/<!DOCTYPE|<!ENTITY/i.test(source))throw new Error('DTD/entity declarations are not supported');
 const parser=new XMLParser({ignoreAttributes:false,attributeNamePrefix:'',parseAttributeValue:false,processEntities:true});const doc=parser.parse(source);const file=doc.mxfile;
 if(!file)throw new Error('Expected mxfile');
 const baseline:CASG=file.ameBaseline?JSON.parse(Buffer.from(file.ameBaseline,'base64').toString()):{schemaVersion:1,id:'imported',title:'Imported architecture',mode:'as-is',components:[],relationships:[],evidence:[]};
 if(file.ameHash&&hash(baseline)!==file.ameHash)throw new Error('Embedded baseline hash mismatch');
 const pages=list(file.diagram);const page=pageId?pages.find(p=>p.id===pageId):pages[0];if(!page)throw new Error('Diagram page not found');
 let graph=page.mxGraphModel;if(!graph){const encoded=typeof page==='string'?page:page['#text'];if(typeof encoded!=='string')throw new Error('Diagram contains no graph');const inflated=inflateRawSync(Buffer.from(encoded,'base64'),{maxOutputLength:20*1024*1024}).toString();graph=parser.parse(decodeURIComponent(inflated)).mxGraphModel;}
 const root=graph?.root;if(!root)throw new Error('Diagram contains no root');
 const unsupported:string[]=[];if(root.object||root.UserObject)unsupported.push('UserObject wrappers preserved in source; not interpreted');
 const cells=list(root.mxCell);const view=baseline.views?.find(v=>v.id===page.id);const visible=new Set(view?.nodes??baseline.components.map(n=>n.id));
 const candidate=structuredClone(baseline);const touched=new Set<string>();
 const positions=new Map<string,{x:number;y:number}>();
 const point=(cell:any,seen=new Set<string>()):{x:number;y:number}=>{if(positions.has(cell.id))return positions.get(cell.id)!;if(seen.has(cell.id))throw new Error('Cyclic XML parent');seen.add(cell.id);const p=cells.find(c=>c.id===cell.parent&&c.vertex==='1');const origin=p?point(p,seen):{x:0,y:0};const result={x:Number(cell.mxGeometry?.x??0)+origin.x,y:Number(cell.mxGeometry?.y??0)+origin.y};positions.set(cell.id,result);return result;};
 for(const cell of cells){if(cell.vertex==='1'){
  if(!cell.id||!cell.mxGeometry){unsupported.push(`Missing geometry: ${cell.id}`);continue;}
  const old=candidate.components.find(n=>n.id===cell.id);const n:Component=old??{id:cell.id,label:cell.value??cell.id,kind:cell.ameKind??'service'};
  n.label=String(cell.value??n.label);n.position=point(cell);n.size={width:Number(cell.mxGeometry.width??260),height:Number(cell.mxGeometry.height??104)};n.parent=['0','1',undefined].includes(cell.parent)?undefined:cell.parent;
  if(!old)candidate.components.push(n);touched.add(n.id);
 }else if(cell.edge==='1'){
  const old=candidate.relationships.find(e=>e.id===cell.id);const e:Relationship=old??{id:cell.id,from:cell.source,to:cell.target,kind:cell.ameKind??'sync'};e.from=cell.source;e.to=cell.target;e.label=String(cell.value??'');
  const points=list(cell.mxGeometry?.Array?.mxPoint).map(p=>({x:Number(p.x),y:Number(p.y)}));
  const from=cells.find(c=>c.id===e.from),to=cells.find(c=>c.id===e.to);
  if(points.length&&from&&to){const a=point(from),b=point(to);e.waypoints=[{x:a.x+Number(from.mxGeometry.width),y:a.y+Number(from.mxGeometry.height)/2},...points,{x:b.x,y:b.y+Number(to.mxGeometry.height)/2}];}
  if(!old)candidate.relationships.push(e);touched.add(e.id);
 }}
 candidate.components=candidate.components.filter(n=>!visible.has(n.id)||touched.has(n.id));
 candidate.relationships=candidate.relationships.filter(e=>!(visible.has(e.from)&&visible.has(e.to))||touched.has(e.id));
 const conflicts=current&&hash(current)!==hash(baseline)?['Current model differs from exported baseline; imported candidate is separate. No automatic merge performed.']:[];
 return {candidate,baselineHash:hash(baseline),diff:diff(baseline,candidate),conflicts,unsupported,sourcePreserved:true,pageId:page.id};
}

import {readFileSync} from 'node:fs';
import type {CASG} from './model.js';
const catalog=JSON.parse(readFileSync(new URL('../catalogs/providers.json',import.meta.url),'utf8'));
export function catalogFacts(m:CASG,now=new Date()){
 const ageDays=Math.floor((now.getTime()-Date.parse(catalog.retrievedAt))/86400000);
 return {retrievedAt:catalog.retrievedAt,ageDays,stale:ageDays>catalog.maxAgeDays,facts:m.components.flatMap(n=>catalog.facts.filter((f:any)=>f.provider===n.provider&&f.service===n.service).map((f:any)=>({componentId:n.id,...f,applicability:Object.entries(f.conditions).every(([k,v])=>n.controls?.[k]===v)?'matched':'conditions-unconfirmed',override:n.controls?.[f.property]??null}))),missing:catalog.missing};
}

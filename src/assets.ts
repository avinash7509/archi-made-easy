import {mkdir,writeFile} from 'node:fs/promises';
import {readFileSync,existsSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {unzipSync} from 'fflate';
import type {Component} from './model.js';
const sha=(s:Uint8Array|string)=>createHash('sha256').update(s).digest('hex');
const root=resolve(process.env.ARCHI_MADE_EASY_ASSETS??fileURLToPath(new URL('../.cache/icons',import.meta.url)));
const catalogs:Record<string,{url:string;source:string;terms:string}>={
 azure:{url:'https://arch-center.azureedge.net/icons/Azure_Public_Service_Icons_V25.zip',source:'https://learn.microsoft.com/en-us/azure/architecture/icons/',terms:'Microsoft architecture icon terms; use for diagrams, preserve shape, do not imply endorsement. Local cache not redistributed in npm package.'},
 aws:{url:'https://d1.awsstatic.com/onedam/marketing-channels/website/public/shared/architecture-icon-release/Icon-package_07312026.5846e92413caa21490223536cc97f1269e44fa92.zip',source:'https://aws.amazon.com/architecture/icons/',terms:'AWS architecture icon terms apply. Local cache not redistributed in npm package.'},
 gcp:{url:'https://services.google.com/fh/files/misc/core-products-icons.zip',source:'https://cloud.google.com/icons',terms:'Google Cloud product icon guidelines apply. Local cache not redistributed in npm package.'}
};
export async function acquireIcons(provider:string){const pack=catalogs[provider];if(!pack)throw new Error('Supported icon providers: azure, aws, gcp');const response=await fetch(pack.url);if(!response.ok)throw new Error(`Icon download failed: ${response.status}`);const bytes=new Uint8Array(await response.arrayBuffer());const archive=unzipSync(bytes);const dir=join(root,provider);await mkdir(dir,{recursive:true});const entries=[];
 for(const [name,data] of Object.entries(archive)){if(!name.toLowerCase().endsWith('.svg')||name.includes('__MACOSX'))continue;let svg=Buffer.from(data).toString();svg=svg.replace(/<\?xml[^>]*>/g,'').replace(/<!DOCTYPE[^>]*>/g,'');if(/<script|<foreignObject|\bon\w+\s*=|(?:href|src)\s*=\s*["'](?:https?:|javascript:)/i.test(svg))continue;const id=sha(name).slice(0,16)+'.svg';await writeFile(join(dir,id),svg);entries.push({name,file:id,sha256:sha(svg)});}
 const manifest={provider,source:pack.source,archiveUrl:pack.url,archiveSha256:sha(bytes),retrievedAt:new Date().toISOString(),terms:pack.terms,entries};await writeFile(join(dir,'manifest.json'),JSON.stringify(manifest,null,2));return {provider,icons:entries.length,path:dir,source:pack.source};}
const aliases:Record<string,string[]>={'application-gateway':['Application-Gateways'],'front-door':['Front-Doors'],'aks':['Kubernetes-Services'],'sql-database':['SQL-Database'],'service-bus':['Service-Bus'],'cloud-run':['cloud_run','cloud run'],'cloud-armor':['cloud_armor','cloud armor'],'s3':['Simple-Storage-Service'],'cloudfront':['CloudFront'],'waf':['WAF'],'lambda':['Lambda'],'rds':['RDS'],'eks':['Elastic-Kubernetes-Service']};
const manifests=new Map<string,any>();
export function icon(n:Component):string|undefined{if(!n.provider||!n.service)return;const dir=join(root,n.provider);if(!manifests.has(dir)){const p=join(dir,'manifest.json');manifests.set(dir,existsSync(p)?JSON.parse(readFileSync(p,'utf8')):null);}const manifest=manifests.get(dir);if(!manifest)return;const normalize=(s:string)=>s.toLowerCase().replace(/[^a-z0-9]/g,'');const keys=(aliases[n.service]??[n.service]).map(normalize);const entry=manifest.entries.find((e:any)=>keys.some(k=>normalize(e.name).includes(k)));if(!entry)return;const data=readFileSync(join(dir,entry.file));if(sha(data)!==entry.sha256)return;return 'data:image/svg+xml;base64,'+data.toString('base64');}

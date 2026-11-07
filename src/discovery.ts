import {readFile,readdir,stat} from 'node:fs/promises';
import {join,relative,extname} from 'node:path';
import YAML from 'yaml';
import ts from 'typescript';
import type {CASG,Component} from './model.js';
const skip=new Set(['node_modules','.git','.venv','venv','dist','build','.terraform','.next']);
export async function discover(root:string):Promise<{model:CASG;unsupported:string[]}>{
 const m:CASG={schemaVersion:1,id:'repository',title:'Repository architecture',mode:'as-is',components:[],relationships:[],evidence:[],assumptions:['Repository discovery is partial static evidence, not a deployed infrastructure inventory.']};const unsupported:string[]=[];let count=0;
 const walk=async(dir:string)=>{for(const entry of await readdir(dir,{withFileTypes:true})){if(skip.has(entry.name)||entry.isSymbolicLink())continue;const path=join(dir,entry.name);if(entry.isDirectory()){await walk(path);continue;}if(++count>2000){unsupported.push('Repository scan limited to 2000 files');return;}if((await stat(path)).size>1024*1024)continue;const ext=extname(path);if(!['.json','.yaml','.yml','.tf','.bicep','.ts','.tsx','.js','.mjs'].includes(ext))continue;
 const source=relative(root,path).replaceAll('\\','/');const raw=await readFile(path,'utf8');const evidenceId='file-'+m.evidence.length;let used=false;
 const add=(label:string,kind:string,provider?:string,service?:string)=>{const id='resource-'+m.components.length;const n:Component={id,label,kind,provider,service,evidence:[evidenceId]};m.components.push(n);used=true;return n;};
 try{
 if(ext==='.tf'||ext==='.bicep'){
  const expression=ext==='.tf'?/resource\s+"([^"]+)"\s+"([^"]+)"/g:/resource\s+(\w+)\s+'([^']+)'/g;
  for(const match of raw.matchAll(expression)){const service=ext==='.tf'?match[1]:match[2];const provider=/^aws_/.test(service)?'aws':/^azurerm_|^Microsoft\./.test(service)?'azure':/^google_/.test(service)?'gcp':undefined;add(ext==='.tf'?match[2]:match[1],'service',provider,service);}
  if(used)unsupported.push(`${source}: resource declarations only; expressions, modules and control settings require agent interpretation`);
 }else if(['.ts','.tsx','.js','.mjs'].includes(ext)){
  const ast=ts.createSourceFile(source,raw,ts.ScriptTarget.Latest,true);const imports:string[]=[];ast.forEachChild(node=>{if(ts.isImportDeclaration(node)&&ts.isStringLiteral(node.moduleSpecifier))imports.push(node.moduleSpecifier.text);});
  if(imports.length){const n=add(source,'module');n.controls={staticImportCount:imports.length};unsupported.push(`${source}: imports recorded as source evidence, not runtime calls`);}
 }else{
  const docs=ext==='.json'?[JSON.parse(raw)]:YAML.parseAllDocuments(raw).map(d=>d.toJSON());
  for(const d of docs){if(!d||typeof d!=='object')continue;
   if(d.apiVersion&&d.kind&&d.metadata?.name){const kind=/Deployment|StatefulSet|DaemonSet|Pod/.test(d.kind)?'compute':/Service|Ingress|Gateway/.test(d.kind)?'gateway':'service';const n=add(d.metadata.name,kind,'kubernetes',d.kind);if(d.kind==='StatefulSet')n.stateful=true;if(d.spec?.replicas!==undefined)n.controls={redundancy:d.spec.replicas>1};if(d.kind==='Service'&&d.spec?.type==='LoadBalancer')n.public=true;}
   if(d.Resources)for(const [name,r] of Object.entries(d.Resources) as [string,any][]){if(r.Type)add(name,'service','aws',r.Type);}
   if(d.resource)for(const [type,resources] of Object.entries(d.resource))for(const name of Object.keys(resources as object))add(name,'service',type.startsWith('aws_')?'aws':type.startsWith('google_')?'gcp':'azure',type);
   if(d.resources&&Array.isArray(d.resources))for(const r of d.resources)if(r.type)add(String(r.name??r.type),'service','azure',r.type);
  }
 }
 }catch{unsupported.push(`${source}: could not parse; retained as unprocessed input`);}
 if(used)m.evidence.push({id:evidenceId,kind:'observed',source:'repo:'+source,conditions:'Static declaration; does not prove deployment or runtime connectivity.'});
 }};await walk(root);return {model:m,unsupported};
}

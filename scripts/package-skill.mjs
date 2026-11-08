import {cp,mkdir,readFile,writeFile,readdir,lstat} from 'node:fs/promises';
import {resolve,join,dirname,relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {zipSync} from 'fflate';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const pkg=JSON.parse(await readFile(join(root,'package.json'),'utf8'));
const stage=join(root,'artifacts','packages',`stage-${Date.now()}`);
const output=join(root,'artifacts','packages');
await mkdir(stage,{recursive:true});
await cp(join(root,'skills','archi-made-easy'),stage,{recursive:true});
const runtime=join(stage,'runtime');await mkdir(runtime,{recursive:true});
for(const name of ['dist','src','schemas','catalogs','examples','benchmarks','test','tsconfig.json','package.json','npm-shrinkwrap.json','LICENSE','NOTICE'])await cp(join(root,name),join(runtime,name),{recursive:true});
await cp(join(root,'docs'),join(stage,'docs'),{recursive:true});
for(const name of ['LICENSE','NOTICE','ROADMAP.md'])await cp(join(root,name),join(stage,name));
await cp(join(root,'scripts','bundle'),stage,{recursive:true});

// Install from the pinned dependency graph into an isolated release staging tree.
// npm is needed by the packager, not by the person downloading the ZIP.
const npmCli=process.env.npm_execpath;
if(!npmCli)throw new Error('Build with npm run package:skill so the npm CLI path is known.');
const install=spawnSync(process.execPath,[npmCli,'ci','--omit=dev','--ignore-scripts','--no-audit','--no-fund'],{cwd:runtime,stdio:'inherit'});
if(install.status!==0)throw new Error('Could not assemble pinned runtime dependencies');

let skill=(await readFile(join(stage,'SKILL.md'),'utf8')).replace(/\r\n/g,'\n');
// Runtime selection lives in SKILL.md, shared by source and ZIP installations.
await writeFile(join(stage,'SKILL.md'),skill);

const files={};const hashes={};
const walk=async dir=>{for(const entry of await readdir(dir,{withFileTypes:true})){
 if(entry.name==='.bin'||entry.name==='.DS_Store')continue;
 const path=join(dir,entry.name);if((await lstat(path)).isSymbolicLink())continue;
 if(entry.isDirectory())await walk(path);else {const name=relative(stage,path).replaceAll('\\','/');const bytes=await readFile(path);files[name]=new Uint8Array(bytes);hashes[name]=createHash('sha256').update(bytes).digest('hex');}
}};await walk(stage);
const manifest={name:'Archi-Made-Easy',version:pkg.version,formatVersion:1,node:'>=22',dependenciesBundled:true,browserBundled:false,vendorIconCacheBundled:false,files:hashes};
files['bundle-manifest.json']=new TextEncoder().encode(JSON.stringify(manifest,null,2)+'\n');
const zip=zipSync(files,{level:6});const name=`archi-made-easy-${pkg.version}-full.zip`;
await writeFile(join(output,name),zip);
const sha=createHash('sha256').update(zip).digest('hex');
await writeFile(join(output,'SHA256SUMS.txt'),`${sha}  ${name}\n`);
await writeFile(join(output,'package-report.json'),JSON.stringify({name,version:pkg.version,bytes:zip.length,fileCount:Object.keys(files).length,sha256:sha,stage,archive:join(output,name)},null,2));
console.log(JSON.stringify({archive:join(output,name),bytes:zip.length,files:Object.keys(files).length,sha256:sha}));

import {readFile,readdir,mkdir,writeFile} from 'node:fs/promises';
import {resolve,join,relative} from 'node:path';
import {createHash} from 'node:crypto';
import {zipSync} from 'fflate';
const root=resolve('skills/archi-made-easy');
const version=JSON.parse(await readFile('package.json','utf8')).version;
const files={};
async function walk(dir){for(const entry of await readdir(dir,{withFileTypes:true})){
 if(entry.name==='__pycache__'||entry.name.endsWith('.pyc'))continue;
 const path=join(dir,entry.name);if(entry.isDirectory())await walk(path);else if(entry.isFile())files[relative(root,path).replaceAll('\\','/')]=new Uint8Array(await readFile(path));
}}
await walk(root);
files['references/LICENSE']=new Uint8Array(await readFile('LICENSE'));
files['references/NOTICE']=new Uint8Array(await readFile('NOTICE'));
const zip=zipSync(files,{level:6});
const name=`archi-made-easy-${version}-compact.zip`;
await mkdir('artifacts/packages',{recursive:true});
await writeFile(join('artifacts/packages',name),zip);
await writeFile('artifacts/packages/COMPACT-SHA256SUMS.txt',`${createHash('sha256').update(zip).digest('hex')}  ${name}\n`);
console.log(JSON.stringify({name,bytes:zip.length,files:Object.keys(files).length,requires:'Python 3.9+ execution; no Node dependency',fullNodeEngine:false}));

import {readFile,mkdir,writeFile,mkdtemp,access} from 'node:fs/promises';
import {join,resolve,dirname} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {unzipSync} from 'fflate';
import assert from 'node:assert/strict';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const report=JSON.parse(await readFile(join(root,'artifacts/packages/package-report.json'),'utf8'));
const destination=await mkdtemp(join(tmpdir(),'Archi Made Easy bundle '));
const files=unzipSync(await readFile(report.archive));
for(const [name,data] of Object.entries(files)){
 assert(!name.startsWith('/')&&!name.split('/').includes('..'),'Unsafe ZIP path');
 assert(!/(^|\/)(\.git|\.cache|\.env)(\/|$)/.test(name),'Private state in bundle');
 const target=join(destination,name);await mkdir(dirname(target),{recursive:true});await writeFile(target,data);
}
for(const name of ['SKILL.md','START-HERE.md','runtime/dist/cli.js','runtime/node_modules/elkjs/package.json','bundle-manifest.json'])await access(join(destination,name));
// Prevent network access for the setup demo; no dependency on the checkout's modules.
const guard=join(destination,'offline-guard.cjs');
await writeFile(guard,"require('node:net').Socket.prototype.connect=function(){throw new Error('Network forbidden in offline package test');};globalThis.fetch=()=>{throw new Error('Network forbidden in offline package test');};");
const run=(args,expected=0)=>{
 const result=spawnSync(process.execPath,['--require',guard,...args],{cwd:tmpdir(),encoding:'utf8',env:{...process.env,NODE_PATH:'',NODE_OPTIONS:`--require ${JSON.stringify(guard)}`}});
 assert.equal(result.status,expected,result.stderr+'\n'+result.stdout);return result.stdout;
};
run([join(destination,'setup.mjs')]);
for(const name of ['index.html','as-is/deployment.svg','as-is/architecture.drawio'])await access(join(destination,'artifacts/demo',name));
run([join(destination,'archi-made-easy.mjs'),'--help']);
await writeFile(join(destination,'runtime/dist/cli.js'),'// intentional integrity-test modification');
run([join(destination,'setup.mjs'),'--check-only'],1);
console.log(JSON.stringify({passed:true,extractedTo:destination,files:Object.keys(files).length,offlineDemo:true,independentWorkingDirectory:true,tamperRejected:true}));

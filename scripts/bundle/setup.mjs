#!/usr/bin/env node
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {join,resolve} from 'node:path';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const root=fileURLToPath(new URL('.',import.meta.url));
if(Number(process.versions.node.split('.')[0])<22)throw new Error('Install Node.js 22+ before running this package.');
const manifest=JSON.parse(await readFile(join(root,'bundle-manifest.json'),'utf8'));
for(const [name,expected] of Object.entries(manifest.files)){
 const actual=createHash('sha256').update(await readFile(join(root,name))).digest('hex');
 if(actual!==expected)throw new Error(`Bundle integrity check failed: ${name}. Extract a fresh copy or investigate intentional local changes.`);
}
const run=args=>{const result=spawnSync(process.execPath,args,{cwd:root,stdio:'inherit'});if(result.error||result.status!==0)throw new Error(`Setup command failed (${result.status}): ${result.error?.message??args[0]}`);};
if(process.argv.includes('--browser'))run([join(root,'runtime','node_modules','playwright','cli.js'),'install','chromium']);
const cli=join(root,'runtime','dist','cli.js');
run([cli,'--help']);
if(!process.argv.includes('--check-only'))run([cli,'render',join(root,'runtime','examples','hybrid.json'),'--out',resolve(root,'artifacts','demo'),...(process.argv.includes('--browser')?[]:['--no-raster'])]);
console.log(JSON.stringify({ready:true,version:manifest.version,integrity:'passed',browserRequested:process.argv.includes('--browser'),demo:resolve(root,'artifacts','demo','index.html'),note:'This validates runtime operation, not architectural correctness or agent-host compatibility.'},null,2));

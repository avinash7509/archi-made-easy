import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtemp,writeFile,readFile,mkdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
import {failure} from '../dist/simulation.js';
import {deliver} from '../dist/export.js';
const script=resolve('skills/archi-made-easy/scripts/render_workbench.py');
const python=process.platform==='win32'?'python':'python3';
const model={schemaVersion:1,id:'restricted',title:'Restricted-host regression',mode:'as-is',components:[{id:'api',label:'API </script><script>throw 42</script>',kind:'api'},{id:'db',label:'Primary database',kind:'database',stateful:true},{id:'backup',label:'Fallback database',kind:'database'}],relationships:[{id:'a',from:'api',to:'db',kind:'sync',dependency:'fallback',group:'database'},{id:'b',from:'api',to:'backup',kind:'sync',dependency:'fallback',group:'database'}],evidence:[]};

test('Python fallback delivers offline interactive artifacts, preserves target, and shares failure semantics',async()=>{
 const root=await mkdtemp(join(tmpdir(),'archi restricted '));const input=join(root,'model.json'),target=join(root,'target.json'),out=join(root,'output');await writeFile(input,JSON.stringify(model));await writeFile(target,JSON.stringify({...model,mode:'target'}));
 const result=spawnSync(python,['-I','-S',script,input,'--target',target,'--out',out],{encoding:'utf8'});assert.equal(result.status,0,result.stderr);const receipt=JSON.parse(result.stdout);assert.equal(receipt.checks.WAF,'not-performed');assert(receipt.files.includes('archi-workbench.html'));
 assert.deepEqual(JSON.parse(await readFile(join(out,'as-is-casg-model.json'),'utf8')),model);
 const scene=JSON.parse(await readFile(join(out,'scene.json'),'utf8'));
 for(const route of scene.routes)for(let i=1;i<route.points.length;i++){const a=route.points[i-1],b=route.points[i];assert(a[0]===b[0]||a[1]===b[1]);for(const box of scene.boxes){const minX=Math.min(a[0],b[0]),maxX=Math.max(a[0],b[0]),minY=Math.min(a[1],b[1]),maxY=Math.max(a[1],b[1]);assert(!(minX<box.x+box.width&&maxX>box.x&&minY<box.y+box.height&&maxY>box.y));}}
 const browser=await chromium.launch();try{const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('http**',route=>route.abort());await page.goto(pathToFileURL(join(out,'archi-workbench.html')).href);assert.equal(await page.locator('#view option').count(),2);await page.locator('#failure').check();await page.locator('[data-id="db"]').click();const detail=JSON.parse(await page.locator('#detail').textContent());assert.deepEqual(detail.simulation.failed,failure(model,['db']).failed);assert.deepEqual(detail.simulation.degraded,failure(model,['db']).degraded);await page.locator('#view').selectOption('1');assert.match(await page.locator('#drawing').innerText(),/target/i);assert.deepEqual(errors,[]);await mkdir('artifacts',{recursive:true});await page.screenshot({path:'artifacts/restricted-host-preview.png'});}finally{await browser.close();}
 // Existing artifacts are never silently overwritten.
 assert.notEqual(spawnSync(python,['-I','-S',script,input,'--out',out],{encoding:'utf8'}).status,0);
});

test('Node no-raster delivery exposes workbench and editable links without claiming PNG',async()=>{
 const out=await mkdtemp(join(tmpdir(),'archi manifest '));const receipt=await deliver(model,out,{raster:false});const links=await readFile(join(out,'DELIVERABLES.md'),'utf8');for(const name of ['archi-workbench.html','architecture.drawio','architecture.svg','casg-model.json']){assert(links.includes(`](${name})`));assert(receipt.files.includes(resolve(out,name)));}assert(!links.includes('](architecture.png)'));assert.equal(receipt.exports.raster,'not-requested');
});

test('Python simulation matches Node for cycles, quorum, optional and buffered dependencies',()=>{
 const cases=[
  {components:[{id:'a',kind:'service'},{id:'b',kind:'service'},{id:'c',kind:'database'}],relationships:[{id:'ab',from:'a',to:'b',kind:'sync'},{id:'ba',from:'b',to:'a',kind:'sync'},{id:'bc',from:'b',to:'c',kind:'sync'}]},
  {components:[{id:'a',kind:'service'},{id:'b',kind:'database'},{id:'c',kind:'database'}],relationships:[{id:'ab',from:'a',to:'b',kind:'sync',dependency:'quorum',quorum:2,group:'q'},{id:'ac',from:'a',to:'c',kind:'sync',dependency:'quorum',quorum:2,group:'q'}]},
  {components:[{id:'a',kind:'service',controls:{buffered:true}},{id:'b',kind:'queue'},{id:'c',kind:'service',parent:'b'}],relationships:[{id:'ab',from:'a',to:'b',kind:'async'}]},
  {components:[{id:'a',kind:'service'},{id:'b',kind:'service'}],relationships:[{id:'ab',from:'a',to:'b',kind:'sync',dependency:'optional'}]}
 ];
 const code="import importlib.util,json,sys; s=importlib.util.spec_from_file_location('renderer',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); cases=json.load(sys.stdin); print(json.dumps([[m.failure(c,[n['id']]) for n in c['components']] for c in cases]))";
 const result=spawnSync(python,['-B','-S','-c',code,script],{input:JSON.stringify(cases),encoding:'utf8'});assert.equal(result.status,0,result.stderr);const results=JSON.parse(result.stdout);
 cases.forEach((c,i)=>c.components.forEach((n,j)=>{const expected=failure(c,[n.id]);assert.deepEqual(results[i][j].failed,expected.failed);assert.deepEqual(results[i][j].degraded,expected.degraded)}));
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,mkdir,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';
import {unzipSync} from 'fflate';
import {chromium} from 'playwright';
test('compact master retains all nodes under lenses, nested containment, exports and routing',async()=>{
 const built=spawnSync(process.execPath,['scripts/package-compact.mjs'],{encoding:'utf8'});assert.equal(built.status,0,built.stderr);
 const {name}=JSON.parse(built.stdout),zip=unzipSync(await readFile(join('artifacts/packages',name)));
 assert(Object.keys(zip).every(k=>k==='SKILL.md'||['agents','scripts','references'].includes(k.split('/')[0])));
 assert.deepEqual(Buffer.from(zip['references/casg.schema.json']),await readFile('schemas/casg.schema.json'));
 const dir=await mkdtemp(join(tmpdir(),'compact MCP skill '));for(const [name,bytes] of Object.entries(zip)){const path=join(dir,name);await mkdir(dirname(path),{recursive:true});await writeFile(path,bytes);}
 const result=spawnSync(process.platform==='win32'?'python':'python3',['-I','-S',join(dir,'scripts/render_workbench.py'),join(dir,'references/mcp-enterprise.casg.json'),'--out',join(dir,'output')],{cwd:tmpdir(),encoding:'utf8'});assert.equal(result.status,0,result.stderr);
 const model=JSON.parse(await readFile(join(dir,'references/mcp-enterprise.casg.json'),'utf8'));
 const scenes=JSON.parse(await readFile(join(dir,'output/view-scenes.json'),'utf8'));
 assert.equal(scenes.length,1);assert.deepEqual(new Set(scenes.flatMap(s=>s.routes.map(r=>r.id))),new Set(model.relationships.map(e=>e.id)));
 assert.deepEqual(new Set(scenes.flatMap(s=>s.boxes.map(b=>b.id))),new Set(model.components.map(n=>n.id)));
 for(const scene of scenes){assert(new Set(scene.boxes.map(b=>b.x)).size>1);assert.equal(scene.boxes.length,model.components.length);
  for(const route of scene.routes)for(let i=1;i<route.points.length;i++){const a=route.points[i-1],b=route.points[i];assert(a[0]===b[0]||a[1]===b[1]);for(const n of scene.boxes.filter(n=>!n.boundary))assert(!(Math.min(a[0],b[0])<n.x+n.width&&Math.max(a[0],b[0])>n.x&&Math.min(a[1],b[1])<n.y+n.height&&Math.max(a[1],b[1])>n.y));}
 }
 await readFile(join(dir,'output/architecture-master.svg'));await readFile(join(dir,'output/architecture-artifacts.zip'));for(const scene of scenes){for(const box of scene.boxes.filter(b=>b.parent)){const parent=scene.boxes.find(b=>b.id===box.parent);assert(box.x>=parent.x&&box.y>=parent.y&&box.x+box.width<=parent.x+parent.width&&box.y+box.height<=parent.y+parent.height);}assert(scene.routes.every(r=>!r.labelWarning));}
 const browser=await chromium.launch();try{const page=await browser.newPage({viewport:{width:1600,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('http**',r=>r.abort());await page.goto(pathToFileURL(join(dir,'output/archi-workbench.html')).href);assert.equal(await page.locator('#view option').count(),1);const nodeCount=await page.locator('#drawing .node').count();await page.getByRole('button',{name:'Identity / security',exact:true}).click();assert.equal(await page.locator('#drawing .node').count(),nodeCount);assert(await page.locator('#drawing .dim').count()>0);await page.getByRole('button',{name:'Reset filter',exact:true}).click();assert.equal(await page.locator('#drawing .dim').count(),0);await page.getByRole('button',{name:'Minimap',exact:true}).click();assert(await page.locator('#minimap svg').count());
  for(let i=0;i<1;i++){await page.locator('#view').selectOption(String(i));const overflow=await page.locator('.node').evaluateAll(nodes=>nodes.flatMap(g=>{const r=g.querySelector('rect').getBBox();return [...g.querySelectorAll('text')].filter(t=>{const b=t.getBBox();return b.x<r.x||b.x+b.width>r.x+r.width||b.y+b.height>r.y+r.height;}).map(t=>t.textContent)}));assert.deepEqual(overflow,[]);}
  await page.locator('#view').selectOption('0');await mkdir('artifacts',{recursive:true});await page.screenshot({path:'artifacts/mcp-compact-preview.png'});await page.locator('#failure').check();await page.locator('#drawing [data-id="server"]').click();assert.match(await page.locator('#summary').innerText(),/agent/);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
});

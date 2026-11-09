import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFile,mkdtemp} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
import {structural} from '../dist/validation.js';
test('regional deployment preserves semantic edges, aggregates telemetry, and exposes honest recovery',async()=>{
 const source='skills/archi-made-easy/references/azure-enterprise.casg.json',model=JSON.parse(await readFile(source,'utf8'));
 assert.equal(structural(model).passed,true,JSON.stringify(structural(model)));
 const out=join(await mkdtemp(join(tmpdir(),'ame regional ')),'out');
 const run=spawnSync(process.platform==='win32'?'python':'python3',['-I','-S','skills/archi-made-easy/scripts/render_workbench.py',source,'--out',out],{encoding:'utf8'});assert.equal(run.status,0,run.stderr);
 const scene=JSON.parse(await readFile(join(out,'scene.json'),'utf8'));
 assert.deepEqual(new Set(scene.routes.map(r=>r.id)),new Set(model.relationships.map(e=>e.id)));
 const bus=scene.routes.filter(r=>r.busId);assert.equal(bus.length,8);assert.equal(new Set(bus.map(r=>r.busId)).size,1);assert.equal(bus.filter(r=>!r.sharedTail).length,1);
 assert(scene.routes.every(r=>!r.labelWarning));assert(scene.routes.every(r=>r.protocol!=='HTTPS'));
 for(const suffix of ['a','b']){const region=scene.boxes.find(b=>b.id==='region-'+suffix),vault=scene.boxes.find(b=>b.id==='vault-'+suffix);assert(vault.x>region.x&&vault.y>region.y);assert(!scene.planes.some(p=>p.members.includes(vault.id)));}
 for(const r of scene.routes)for(let i=1;i<r.points.length;i++){const a=r.points[i-1],b=r.points[i];for(const n of scene.titleObstacles)assert(!(Math.min(a[0],b[0])<n.x+n.width&&Math.max(a[0],b[0])>n.x&&Math.min(a[1],b[1])<n.y+n.height&&Math.max(a[1],b[1])>n.y));}
 const browser=await chromium.launch();try{const page=await browser.newPage({viewport:{width:1800,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('http**',r=>r.abort());await page.goto(pathToFileURL(join(out,'archi-workbench.html')).href);
 await page.locator('#drawing [data-id="frontdoor"]').click();await page.getByRole('tab',{name:'IaC Skeleton'}).click();assert.match(await page.locator('#readiness').innerText(),/Microsoft.Cdn\/profiles/);
 await page.locator('#failure').check();await page.locator('#drawing [data-id="region-a"]').click();assert(await page.locator('#drawing .edge.failover').count()>0);assert.match(await page.locator('#summary').innerText(),/240 s/);assert.match(await page.locator('#summary').innerText(),/5 s/);
 assert.equal(await page.evaluate(()=>recoveryEstimate({}).rtoSeconds),null);
 await page.locator('#failure').uncheck();await page.screenshot({path:'artifacts/azure-overhaul-preview.png'});assert.deepEqual(errors,[]);
 }finally{await browser.close()}
});

